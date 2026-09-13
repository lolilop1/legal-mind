# Legal Mind — Changelog

## 2026-09-13 (Модуль 1: невозвратные товары — Пост. 2463)

### Добавлено
- modules/consumer/hardchecks.py: список невозвратных категорий
  (Постановление Правительства РФ от 31.12.2020 № 2463):
  лекарства, предметы личной гигиены, парфюмерия, ткани, бельё и
  чулочно-носочные, ювелирка, авто/мото, оружие, растения, книги,
  бытовая химия, пестициды
- hard_pre_check(user_data, scenario=None) — принимает сценарий;
  блокирует возврат невозвратного ТОЛЬКО для return14 (ст. 25),
  для defect (ст. 18) работает как раньше
- Category-маркер "non_returnable" в стопе — app.py пропускает
  pre-check для этого случая (это юридическая блокировка, а не UNKNOWN)

### Изменено
- web/app.py: process_consumer_module пробрасывает scenario в hardcheck
- web/app.py: pre-check на стопе не запускается для category=non_returnable

### Тесты
- test_consumer_hardchecks.py: +15 кейсов (невозвратные + return14,
  невозвратные + defect, legacy-вызов без scenario)
- Всего: 15 файлов, 320 проверок (было 305)

---

## 2026-09-13 (security round 2: cookie flags, ProxyFix, ПДн в логах)

### Добавлено
- web/app.py: cookie flags — SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE=Lax,
  SESSION_COOKIE_SECURE (включается через .env когда появится HTTPS)
- web/app.py: ProxyFix — правильный request.remote_addr из X-Forwarded-For

### Исправлено
- web/app.py: логирование ПДн — убран адрес из log.info,
  теперь пишется только длина (addr_len) вместо значения

---

## 2026-09-13 (security: IDOR, атомарность CASE, SECRET_KEY, openai)

### Исправлено
- IDOR: /case/<ref>/pdf/<doc_id> отдавал документ по глобальному id
  без проверки принадлежности делу — теперь фильтр по (id, case_number)
- core/case_db.py: create_case — атомарная генерация case_number
  (BEGIN IMMEDIATE + retry на IntegrityError); раньше была гонка
  между воркерами gunicorn
- web/app.py: SECRET_KEY обязателен — сервис не стартует с
  небезопасным дефолтом вместо явной ошибки
- web/requirements.txt: openai>=1.50 → openai>=1.66
  (client.responses.create требует 1.66+)

### Тесты
- test_case_db.py: +1 регресс-проверка на IDOR
  (get_document_content с чужим case_number → None)
- Всего: 15 файлов, 305 проверок (по факту прогона run_all.py).
  Сразу после фикса IDOR run_all.py показывал 281 — test_case_db.py
  падал с TypeError до своей финальной строки "Total: ...", и все
  24 его проверки не попадали в агрегат. После фикса теста (передача
  case_number в get_document_content) файл долистывает до конца,
  агрegat корректный: 305. Ранее в доках заявлялось 304 — было
  до IDOR-регресс-проверки, не перепроверялось прогоном.

---

## 2026-09-12 (Модуль 1: умная шапка, валидация, нормализация)

### Добавлено
- modules/consumer/pdf.py: _format_addressee — умная шапка PDF
  - ООО/АО/ПАО → «Директору X», ИП/самозанятый → «X»
  - ФИО физлица → «Гражданину/Гражданке X» (по полу, дательный)
  - Ники → «Продавцу X»
- core/name_declension.py: decline_fio_dative, detect_gender_by_name
- core/phone_check.py: normalize_phone → «+7 (XXX) XXX-XX-XX»
- Физлица-продавцы: адрес НЕ обязателен, но нужен адрес ИЛИ ссылка
- Поле «Ссылка на профиль/объявление» в форме
- Inline-валидация: lmValidateStep, lmShowFieldError, lmMapServerErrors
- Перехват submit — проверка всех шагов, маппинг серверных ошибок в поля

### Исправлено
- Regex одинаковых цифр в телефоне
- deploy.yml: find для рекурсивного chmod

### Тесты
- test_consumer_addressee.py — 13
- test_phone_check.py — 30 (нормализация + РФ-валидация)
- Всего: 15 файлов, 304 проверки

---

## 2026-09-12 (Модуль 1: Потребитель)

### Добавлено
- modules/consumer/ — engine, hardchecks, pre_checks, pdf, scenario_detect
- 4 конфига: defect (ст. 18), return14 (ст. 25), marketplace (ст. 26.1), service (ст. 29)
- Авто-определение сценария по тексту (scenario_detect.py)
- Gender detection в PDF (проживающий/проживающей, вынужден/вынуждена)
- Wizard-форма (3 шага): проблема → детали → контакты
- Air Datepicker для даты покупки (mobile-friendly, bottom sheet)
- Авто-скачивание PDF + редирект в карточку дела (?just_created=1)
- Pre-check на STOP работает для consumer

### Изменено
- app.py: process_consumer_module + ветка consumer в submit
- core/name_declension.py: detect_gender работает и с родительным падежом
- index.html: 3-шаговый wizard вместо одной длинной формы

### Тесты
- test_consumer_hardchecks.py — 18
- test_consumer_pre_checks.py — 15
- test_consumer_scenario.py — 27
- Всего: 15 файлов, 289 проверок

---

## 2026-09-11 (доки: раздел Безопасность в README)

### Добавлено
- README.md: раздел «🔒 Безопасность» — секреты, права, деплой, CI/CD

### Удалено
- _archive/old_VPS/.env (архивный файл с ключами)

---

## 2026-09-11 (этап 5: Legal Trace)

### Добавлено
- core/trace.py — модель LegalTrace + build_trace()
- Цепочка: Факт → Квалификация → Норма → Источник
- _build_trace_dict() в app.py — собирает trace в DNA
- Блок «Как система пришла к норме» в карточке дела
- Стили .trace-chain в CSS

### Что показывает
- Модуль 2 (УК): источник — «Федеральное законодательство РФ · consultant.ru»
- Модуль 3 (шум): источник — ссылка на garant.ru (из БД регионов)

### Тесты
- test_trace.py — 16 проверок

---

## 2026-09-11 (этап 6: Версионность)

### Добавлено
- RULES_DATE = "2026.09" и TEMPLATE_VERSION = "1.0" в app.py
- Версии прокинуты в normalized для модулей 2 и 3
- PDF: подвал внизу с движком, правилами, шаблоном (серый, 8pt)
- case.html: блок «Версия документа»

---

## 2026-09-11 (этап 4: Confidence / UNKNOWN)

### Добавлено
- core/pre_checks.py — универсальная модель CheckItem/PreCheckReport
- modules/uk/pre_checks.py — проверки для жалобы в УК
- modules/noise/pre_checks.py — проверки для жалобы на шум
- Экран pre_check_blocked.html — «Что знаем / Чего не хватает»
- case.html — блок «Что знаем» в карточке дела
- Pre-check при стопе: если hard-check дал vague-стоп, но pre-check
  собрал полезный отчёт — показываем его вместо сухого stop.html

### Тесты
- test_pre_checks.py — 17 проверок

---

## 2026-09-11 (автодеплой)

### Добавлено
- GitHub репозиторий lolilop1/legal-mind (приватный)
- SSH Deploy Key на сервере
- .github/workflows/deploy.yml — GitHub Actions
- Три секрета: SSH_HOST, SSH_USER, SSH_PRIVATE_KEY
- git push → 30 секунд до прода

---

## 2026-09-11 (модульность)

### Изменено
- Переехали с плоской структуры на модульную
- core/, region/, modules/, web/, scripts/, tests/, docs/, deploy/
- 12 файлов тестов, 229 проверок
- systemd + nginx обновлены
- Старые плоские файлы удалены (архив в /root/)

### Тесты
- run_all.py теперь считает общее число проверок
- UTF-8 для дочерних процессов (Windows compat)

---

## 2026-09-11 (этап 3: CASE)

### Добавлено
- core/case_db.py — абстракция доступа к БД
- core/case_id.py — генератор LM-YYYYMMDD-NNNN + UUID
- core/labels.py — русские названия типов
- web/schema.sql — схема (cases, case_documents, case_events)
- Экран /my — список дел через session
- Экран /case/... — карточка дела
- Сохранение CASE после генерации PDF

### Тесты
- test_case_id.py — 17 проверок
- test_case_db.py — 23 проверки

---

## 2026-09-10 (фиксы по фидбеку тестеров)

### Исправлено
- Форма сохраняет данные при ошибке валидации
- Все ошибки показываются разом, не по одной
- Emergency-экран с кнопкой «Позвонить 112»
- Единый стиль стоп-страниц (топ-бар, кнопки)
- Нормализация адреса: «д1» → «д. 1», запятые
- Entity check: маркеры угроз (убивают, избивают, грабят)
- Промпт модуля 3: «соседи сверху» не путается с квартирой заявителя

### Тесты
- test_address.py — 7 проверок

---

## 2026-09-10 (исходная версия)

### Модуль 2 (УК)
- Hard-check (62 кейса)
- Entity recall + retry
- Три федеральные нормы
- PDF на fpdf2

### Модуль 3 (шум)
- Hard-check (19 кейсов)
- Региональные законы (85 субъектов)
- Гибридное определение региона (regex + embeddings)

### Инфраструктура
- Переход YandexGPT Pro → Alice AI Flash
- База 85 регионов
- Adversarial тесты (29/29)