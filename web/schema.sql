-- Legal Mind — схема БД для CASE
-- SQLite. Хранение: web/cases.db (права 600)

PRAGMA foreign_keys = ON;

-- ─── Основная таблица: CASE ───
CREATE TABLE IF NOT EXISTS cases (
    -- Идентификация
    case_number     TEXT PRIMARY KEY,          -- LM-20260911-4821
    case_uuid       TEXT UNIQUE NOT NULL,      -- 32 hex-символа

    -- Временные метки
    created_at      TEXT NOT NULL,             -- ISO 8601
    updated_at      TEXT NOT NULL,

    -- DNA: тип и сущности
    problem_type    TEXT NOT NULL,             -- uk / noise / consumer
    subject         TEXT,                      -- покупатель / арендатор
    object          TEXT,                      -- товар / услуга / квартира
    event           TEXT,                      -- недостаток / отказ
    dates           TEXT,                      -- JSON: {начало, срок, обращение}
    amount          REAL,                      -- сумма (может быть NULL)
    counterparty    TEXT,                      -- продавец / УК / работодатель
    jurisdiction    TEXT,                      -- регион
    demand          TEXT,                      -- требование

    -- JSON-поля
    evidence        TEXT,                      -- JSON: список доказательств
    confidence      TEXT,                      -- JSON: {known: [...], unknown: [...]}
    trace           TEXT,                      -- JSON: цепочка норма→источник

    -- Версии (snapshot на момент генерации)
    engine_version  TEXT,                      -- uk-01 / noise-01 / consumer-defect-01
    rules_version   TEXT,                      -- 2026.09
    template_version TEXT,                     -- 1.0

    -- Исходные данные
    source_text     TEXT,                      -- что написал пользователь
    user_data       TEXT                       -- JSON: все поля формы
);

CREATE INDEX IF NOT EXISTS idx_cases_uuid ON cases(case_uuid);
CREATE INDEX IF NOT EXISTS idx_cases_created ON cases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_type ON cases(problem_type);

-- ─── Сгенерированные документы ───
CREATE TABLE IF NOT EXISTS case_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number     TEXT NOT NULL,
    doc_type        TEXT NOT NULL,             -- claim / lawsuit / complaint / calc
    file_path       TEXT,                      -- путь (если храним файлом)
    content         BLOB,                      -- либо содержимое прямо в БД
    generated_at    TEXT NOT NULL,
    template_version TEXT,
    engine_version  TEXT,
    FOREIGN KEY (case_number) REFERENCES cases(case_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_docs_case ON case_documents(case_number);

-- ─── События (история) ───
CREATE TABLE IF NOT EXISTS case_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number     TEXT NOT NULL,
    event_type      TEXT NOT NULL,             -- created / generated / updated / viewed
    event_data      TEXT,                      -- JSON: детали
    created_at      TEXT NOT NULL,
    FOREIGN KEY (case_number) REFERENCES cases(case_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_case ON case_events(case_number);
CREATE INDEX IF NOT EXISTS idx_events_type ON case_events(event_type);