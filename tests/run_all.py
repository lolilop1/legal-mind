"""Run all tests in tests/ with correct sys.path.

Usage (from project root):
    python tests/run_all.py
"""

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
]


def main():
    failed = []
    passed = []

    for test_file in _TESTS:
        path = _TESTS_DIR / test_file
        if not path.exists():
            print(f"[SKIP] {test_file} (не найден)")
            continue

        print(f"\n{'='*70}")
        print(f"RUN: {test_file}")
        print("=" * 70)

        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(_TESTS_DIR),
        )

        if result.returncode == 0:
            passed.append(test_file)
        else:
            failed.append(test_file)

    print(f"\n\n{'='*70}")
    print(f"ИТОГО: пройдено {len(passed)}, упало {len(failed)}")
    if failed:
        print(f"УПАЛИ: {', '.join(failed)}")
    print("=" * 70)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()