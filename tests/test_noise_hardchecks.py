"""Offline regression for Module 3. No API calls. Tests hard checks and PDF."""

import _bootstrap  # noqa: F401
import json
from pathlib import Path

from modules.noise.hardchecks import hard_pre_check
from modules.noise.pdf import generate_pdf


BASE = {"адрес": "г. Москва, ул. Тестовая, 1", "дата_начала": "недавно", "обращались_ранее": "нет"}


def check(problem, expected, label):
    data = dict(BASE)
    data["проблема"] = problem
    r = hard_pre_check(data)
    if expected == "OK":
        ok = r is None
    elif expected == "EMERGENCY":
        ok = r is not None and r["emergency"] and r["stop"]
    elif expected == "STOP":
        ok = r is not None and r["stop"] and not r["emergency"]
    else:
        raise ValueError(expected)
    return {"label": label, "ok": ok, "expected": expected, "result": r}


def main():
    tests = [
        # OK — типовые жалобы
        ("соседи из кв. 45 постоянно слушают громкую музыку по ночам", "OK", "music at night"),
        ("сосед сверху делает ремонт каждый день, перфоратор слышно", "OK", "repairs"),
        ("у соседей снизу постоянно лает собака, особенно по ночам", "OK", "dog"),
        ("за стеной соседи постоянно кричат и скандалят по вечерам", "OK", "shouting"),
        ("соседи устраивают вечеринки каждые выходные, музыка до трёх ночи", "OK", "parties"),
        ("сверху постоянно топают, особенно поздно вечером", "OK", "tопот"),
        ("соседка сверху сверлит стену весь день", "OK", "сверлит"),

        # EMERGENCY — угроза жизни
        ("сосед из кв. 45 угрожает убить, кричит и стучит в дверь по ночам", "EMERGENCY", "threat to kill"),
        ("сосед сверху пришёл с ножом и угрожал", "EMERGENCY", "knife"),
        ("сосед нападает по ночам, избивает", "EMERGENCY", "attack"),
        ("сосед ломает дверь и угрожает мне", "EMERGENCY", "breaking door"),

        # STOP — не про шум
        ("в подъезде не убирают уже две недели, грязь и мусор", "STOP", "not noise"),
        ("протекает крыша после дождя", "STOP", "not noise"),
        ("батареи еле тёплые, дома холодно", "STOP", "not noise"),

        # STOP — короткое
        ("шумно", "STOP", "short"),
        ("плохо", "STOP", "short"),

        # STOP — не ясно, кто шумит
        ("в доме постоянный громкий шум и музыка", "STOP", "no neighbor"),

        # STOP — нет адреса
        ("__no_address__", "STOP", "missing address"),
    ]

    results = []
    for problem, expected, label in tests:
        if problem == "__no_address__":
            data = dict(BASE, проблема="сосед сверху громко слушает музыку", адрес="")
            r = hard_pre_check(data)
            ok = r is not None and r["stop"] and not r["emergency"]
            results.append({"label": label, "ok": ok, "result": r})
        else:
            results.append(check(problem, expected, label))

    # PDF test
    outdir = Path("test_module3_output")
    outdir.mkdir(exist_ok=True)
    req = {
        "адресат": "Начальнику ОВД по Центральному району г. Москвы",
        "фио": "Иванов Иван Иванович",
        "адрес": "г. Москва, ул. Ленина, 15, кв. 44",
        "телефон": "+7 (999) 123-45-67",
    }
    norm = {
        "описание_проблемы_формальное": (
            "Из квартиры №45 многоквартирного дома систематически в ночное "
            "время доносится громкая музыка. Нарушение тишины и покоя "
            "граждан фиксируется на протяжении месяца."
        ),
        "применимая_норма": "Федеральный закон от 07.02.2011 № 3-ФЗ «О полиции»",
    }
    pdf_ok = False
    try:
        out = str(outdir / "noise_test.pdf")
        generate_pdf(out, req, norm)
        p = Path(out)
        pdf_ok = p.exists() and p.stat().st_size > 1000 and p.read_bytes()[:5] == b"%PDF-"
    except Exception as e:
        print(f"PDF FAIL: {type(e).__name__}: {e}")
    results.append({"label": "PDF generation", "ok": pdf_ok})

    passed = sum(bool(r["ok"]) for r in results)
    failed = len(results) - passed
    for r in results:
        print(f"[{'PASS' if r['ok'] else 'FAIL'}] {r['label']}")
        if not r["ok"]:
            print(f"       got: {r.get('result')}")
    print(f"\nTotal: {len(results)}  Passed: {passed}  Failed: {failed}")

    with open("results_module3_offline.json", "w", encoding="utf-8") as f:
        json.dump({"passed": passed, "failed": failed, "results": results},
                  f, ensure_ascii=False, indent=2)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()