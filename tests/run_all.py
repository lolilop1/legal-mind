"""Run all tests in tests/ with correct sys.path + summary.

Usage (from project root):
    python tests/run_all.py
"""

import os
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass
import re
import subprocess
import sys
from pathlib import Path


_TESTS_DIR = Path(__file__).resolve().parent
_TESTS = [
    "test_uk_hardchecks.py",
    "test_noise_hardchecks.py",
    "test_entity_check.py",
    "test_name_declension.py",
    "test_phone_check.py",
    "test_region_extractor.py",
    "test_pdf_generation.py",
    "test_case_id.py",
    "test_case_db.py",
    "test_address.py",
    "test_pre_checks.py",
    "test_trace.py",
    # Модуль 1 (Потребитель)
    "test_consumer_hardchecks.py",
    "test_consumer_pre_checks.py",
    "test_consumer_scenario.py",
    "test_marketplaces.py",
    "test_calculators.py",
    "test_app_routes.py",
    "test_app_security.py",
    "test_llm.py",
    "test_pdf_addressee.py",
]

# Паттерны для извлечения "Total: X Passed: Y Failed: Z"
_TOTAL_RE = re.compile(r'(?:Total:|"total"\s*:)\s*(\d+)')
_PASSED_RE = re.compile(r'(?:Passed:|"passed"\s*:)\s*(\d+)')
_FAILED_RE = re.compile(r'(?:Failed:|"failed"\s*:)\s*(\d+)')


def _parse_result(output: str) -> tuple[int, int, int]:
    """Возвращает (total, passed, failed). 0/0/0 если не нашли."""
    total_m = _TOTAL_RE.search(output)
    passed_m = _PASSED_RE.search(output)
    failed_m = _FAILED_RE.search(output)
    total = int(total_m.group(1)) if total_m else 0
    passed = int(passed_m.group(1)) if passed_m else 0
    failed = int(failed_m.group(1)) if failed_m else 0
    return total, passed, failed


def main():
    failed_files = []
    passed_files = []
    grand_total = 0
    grand_passed = 0
    grand_failed = 0

    for test_file in _TESTS:
        path = _TESTS_DIR / test_file
        if not path.exists():
            print(f"[SKIP] {test_file} (не найден)")
            continue

        print(f"\n{'='*70}")
        print(f"RUN: {test_file}")
        print("=" * 70)

        # Принудительно UTF-8 для дочернего процесса,
        # иначе на Windows cp1251 не сможет закодировать "→" и "⚠"
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(_TESTS_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        # Печатаем вывод как есть
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        total, passed, failed = _parse_result(result.stdout)
        grand_total += total
        grand_passed += passed
        grand_failed += failed

        if result.returncode == 0:
            passed_files.append(test_file)
        else:
            failed_files.append(test_file)

    print(f"\n\n{'='*70}")
    print(f"FILES:   passed {len(passed_files)}, failed {len(failed_files)}")
    print(f"CHECKS:  total {grand_total}, passed {grand_passed}, "
          f"failed {grand_failed}")
    if failed_files:
        print(f"FAILED FILES: {', '.join(failed_files)}")
    print("=" * 70)

    sys.exit(1 if failed_files else 0)


if __name__ == "__main__":
    main()