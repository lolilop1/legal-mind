from pathlib import Path
import re
DOCS = ["README.md","STATUS.md","ROADMAP.md","docs/MODULES.md","docs/ARCHITECTURE.md",
        "docs/DECISIONS.md","docs/SETUP.md","web/README.md"]
print("=== Не 810 ===")
for f in DOCS:
    p = Path(f)
    if not p.exists(): continue
    t = p.read_text(encoding="utf-8")
    bad = [m.group(1) for m in re.finditer(r'\b(\d{3})\s*(?:провер|тест)', t) if m.group(1) != "810"]
    if bad: print(f"  {f}: {bad}")

print()
print("=== Мониторинг упомянут ===")
for f in ["README.md","STATUS.md","docs/ARCHITECTURE.md"]:
    p = Path(f)
    t = p.read_text(encoding="utf-8").lower()
    has = "health-check" in t or "cloud function" in t or "мониторинг" in t
    print(f"  {f}: {'OK' if has else 'НЕТ'}")