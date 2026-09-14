# -*- coding: utf-8 -*-
"""Финальная добивка: перебор ВСЕХ URL, не только приоритетных."""
import sys, json, re, sqlite3, requests
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB = Path("region/data/noise_laws.db")
OUT = Path("region/data/noise_articles.json")

REGIONS = ["Забайкальский край", "Калининградская область",
           "Пензенская область", "Республика Татарстан"]

def strip_html(html):
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()

# Более агрессивный паттерн: "статья N" (одно число) рядом с "тишин"
ST_RE = re.compile(
    r"[Сс]тать[яи]\s+(\d+(?:\.\d+)*)\s*[\.\s]?\s*([А-ЯЁA-Z][^.]{5,150}?)(?=\s+\d+\.|\s+[Сс]тать|\s+Глава|\Z)"
)
NOISE_CTX = re.compile(r"тишин|покой|поко[йя]\s+граждан", re.IGNORECASE)

def find_article(text):
    # Ищем все упоминания "тишин/покой"
    noise_positions = [m.start() for m in NOISE_CTX.finditer(text)]
    if not noise_positions:
        return None

    # Все "Статья N ..." с их позициями
    articles = [(m.start(), m.group(1), m.group(2).strip()[:200]) for m in ST_RE.finditer(text)]
    if not articles:
        return None

    # Для каждой "тишин" — ближайший заголовок СЛЕВА в пределах 3000
    best = None
    best_dist = 10**9
    for np in noise_positions:
        for apos, anum, atitle in articles:
            if apos < np:
                dist = np - apos
                if dist < best_dist and dist < 3000:
                    best_dist = dist
                    best = (apos, anum, atitle)

    if not best:
        return None

    apos, anum, atitle = best
    article = f"Статья {anum}. {atitle}"

    # Цитата: 400 символов от позиции
    quote = text[max(0, apos):apos + 500].strip()[:500]
    return {
        "article": article,
        "quote": quote,
        "confidence": "средняя (regex, из обзорной статьи)",
    }

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

results = json.loads(OUT.read_text(encoding="utf-8"))

for region in REGIONS:
    print(f"\n{'='*70}\n{region}\n{'='*70}")
    # ВСЕ URL включая v3-hardcoded и publication
    rows = conn.execute("""
        SELECT DISTINCT law_url FROM noise_laws
        WHERE region = ? AND law_url IS NOT NULL AND law_url != ''
    """, (region,)).fetchall()
    urls = list({r[0] for r in rows})

    # Сортируем: garant > cntd > publication > остальные
    def rank(u):
        if "garant.ru" in u: return 1
        if "cntd.ru" in u: return 2
        if "publication.pravo.gov.ru" in u: return 3
        if "consultant.ru" in u: return 4
        if "pravo.gov.ru" in u: return 5
        return 99
    urls.sort(key=rank)

    text, used_url = None, None
    for url in urls:
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200: 
                print(f"  skip HTTP {r.status_code}: {url[:70]}")
                continue
            t = strip_html(r.text)
            if len(t) < 2000:
                print(f"  skip short ({len(t)}): {url[:70]}")
                continue
            if "тишин" not in t.lower() and "поко" not in t.lower():
                print(f"  skip no-noise: {url[:70]}")
                continue
            text, used_url = t[:30000], url
            print(f"  ✅ text OK: {url[:70]} ({len(text)})")
            break
        except Exception as e:
            print(f"  err {type(e).__name__}: {url[:70]}")
            continue

    if not text:
        print(f"  [нет источника]")
        continue

    extracted = find_article(text)
    if not extracted:
        print(f"  [regex не нашёл статью]")
        continue

    extracted["url"] = used_url
    extracted["quote_verified"] = extracted["article"].lower()[:40] in text.lower()
    print(f"  → {extracted['article'][:100]}")

    # Перезаписываем только если лучше (article есть, а раньше не было)
    old = results.get(region, {})
    if not old.get("article"):
        results[region] = extracted
        print(f"     [ЗАПИСАНО]")
    else:
        print(f"     [уже есть, пропуск]")

conn.close()
OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

ok_count = sum(1 for v in results.values() if v.get("article"))
print(f"\n{'='*60}")
print(f"Всего с article: {ok_count} / 85")
from collections import Counter
confs = Counter(v.get("confidence", "?").split(" ")[0] for v in results.values() if v.get("article"))
print("По confidence:")
for c, n in confs.most_common():
    print(f"  {c:<10} {n}")