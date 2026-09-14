# -*- coding: utf-8 -*-
"""Собирает _CONTEXT_*.md для нового чата. Автосплит по размеру."""

import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MAX_PART_KB = 700
ROOT = Path.cwd()

SKIP_DIRS = {".git", "_archive", "__pycache__", "venv", ".venv",
             "node_modules", "logs", ".idea", ".vscode",
             "smoke_output", "screenshots"}

BIN_EXTS = {".pdf", ".db", ".pyc", ".pyo", ".so", ".pyd", ".png", ".jpg", ".jpeg",
            ".gif", ".ico", ".woff", ".woff2", ".ttf", ".zip", ".tar", ".gz",
            ".exe", ".dll", ".bin", ".mp3", ".mp4", ".avi", ".mov"}

SKIP_NAMES = {".env", "ALL_FILES_DUMP.txt", "_CONTEXT_FOR_CHAT.md",
              "embeddings.json", "adversarial_results.json",
              "results_module2_hardchecks_v2.json", "results_module3_offline.json",
              "noise_laws.db", "cases.db", "make_context.ps1", "make_context.py",
              "IDEAS.md"}

PROMPT = '''Шалом! Проект Legal Mind. Контекст разбит на части.
Прочитай ВСЕ части целиком.

## Стиль работы
- Готовые PowerShell-скрипты -> я вставляю -> коммит+push. Неформально.
- Скрипты КОРОТКИЕ, по одному файлу за раз (длинные ломают UI чата).
- Патчи через _patch.py (временный Python-скрипт), потом Remove-Item.
- После каждой записи проверять BOM.
- Перед коммитом: python tests/run_all.py -> ждём N/N.
- git commit с коротким русским сообщением + git push.
- Если неясно — спрашивай, не гадай.

## Тесты
- Ищи корень слова (недостат, просроч), не целую форму.
- Счётчик тестов — в STATUS.md (обновлять при добавлении).
- CI: push -> Tests -> если зелёные -> Deploy через workflow_run.

## Деплой
- Автодеплой через GitHub Actions: git push -> Tests + Deploy ~ 1.5 минуты.
- Deploy НЕ запускается пока Tests не пройдут (workflow_run).
- Откат — автоотката нет: git revert + push, либо
  ssh root@201.24.49.121 "cd /opt/legal_mind && git reset --hard <hash>".
- RACE CONDITION: между push и завершением деплоя файлы на сервере
  на секунду пропадают (git reset --hard).

## Работа с контекстом
- Дамп разбит на части (_CONTEXT_1.md, _CONTEXT_2.md, ...). Если
  увидел, что часть 2 обрезана или нужного файла нет — СКАЖИ явно,
  какой файл или секцию дослать.
- Длинные списки (напр. 181 конфиг) в дампе могут быть обрезаны —
  если нужен конкретный конфиг, попроси его отдельно.

## При работе над задачей
- Если задача большая — разбивай на короткие шаги (1-2 файла за раз).
  Не пиши скрипты на 200+ строк — они ломают UI чата.
- Если задача ясна и это стандартное действие (скрипт, патч, фикс) —
  ДЕЛАЙ без переспросов. Спрашивай только если есть реальная развилка.
- Если пользователь написал "не понял" или ошибся раскладкой —
  переспроси коротко, не гадай.

## Не делать
- Не обещать исходов дела.
- Не использовать LLM для выбора законов (whitelist).
- Не вызывать LLM без hard-check.
- Не генерировать PDF, если pre-check заблокировал.
- Не хранить ПДн без HTTPS/шифрования.
'''

DOCS = ["README.md", "STATUS.md", "ROADMAP.md",
        "docs/MODULES.md", "docs/ARCHITECTURE.md", "docs/DECISIONS.md"]


def is_text(path: Path) -> bool:
    try:
        data = path.read_bytes()[:8192]
        return b"\x00" not in data
    except Exception:
        return False


def collect_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in BIN_EXTS:
            continue
        if p.name in SKIP_NAMES:
            continue
        if p.name.startswith(".env"):
            continue
        if p.name.startswith("_CONTEXT_"):
            continue
        if not is_text(p):
            continue
        out.append(p)
    return sorted(out)


def main():
    # Чистим старые части
    for old in ROOT.glob("_CONTEXT_*.md"):
        old.unlink()

    files = collect_files()
    max_bytes = MAX_PART_KB * 1024

    part = 1
    buf = []
    size = 0
    files_written = []

    def flush(reason: str):
        nonlocal buf, size, part
        if not buf:
            return
        fname = f"_CONTEXT_{part}.md"
        header = (
            f"# Legal Mind — контекст (часть {part})\n\n"
            f"**Сгенерировано:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Причина новой части:** {reason}\n"
            f"**Файлов в этой части:** {len(buf)}\n\n---\n\n"
        )
        Path(fname).write_text(header + "".join(buf), encoding="utf-8", newline="\n")
        files_written.append(Path(fname))
        part += 1
        buf = []
        size = 0

    # Часть 1: промт + доки
    head = (
        "# Legal Mind — контекст для нового чата (часть 1)\n\n"
        f"**Сгенерировано:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**Всего файлов:** {len(files)}\n\n"
        "> Счётчик тестов — в STATUS.md ниже.\n\n---\n\n"
        f"{PROMPT}\n\n---\n# ДОКУМЕНТЫ\n"
    )
    buf.append(head)
    size += len(head.encode("utf-8"))

    for doc in DOCS:
        p = Path(doc)
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        block = f"\n## FILE: {doc}\n\n{text}\n"
        bsize = len(block.encode("utf-8"))
        if size + bsize > max_bytes:
            flush("доки не влезли")
            buf.append(f"# ДОКУМЕНТЫ (продолжение)\n")
            size += len(buf[-1].encode("utf-8"))
        buf.append(block)
        size += bsize

    buf.append("\n\n---\n# ВЕСЬ КОД\n")
    size += len(buf[-1].encode("utf-8"))

    for f in files:
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            text = "[read error]"
        block = f"\n\n=== FILE: {rel} ({f.stat().st_size} bytes) ===\n{text}"
        bsize = len(block.encode("utf-8"))
        if size + bsize > max_bytes:
            flush(f"файл {rel} не влез")
        buf.append(block)
        size += bsize

    flush("конец")

    print(f"OK: частей: {len(files_written)}")
    for fn in files_written:
        kb = fn.stat().st_size / 1024
        print(f"  {fn.name} — {kb:.1f} KB")


if __name__ == "__main__":
    main()
