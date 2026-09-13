# -*- coding: utf-8 -*-
"""E2E: генерация PDF через Flask + проверка содержимого через pypdf.

LLM замокан. Бесплатно, быстро, ловит:
- пустые PDF (шапка есть, тело пропало)
- кривую шапку (ООО без кавычек, ФИО без склонения)
- пропавший блок РАСЧЁТ НЕУСТОЙКИ
- неправильные нормы (ст. 18 vs ст. 25 vs ст. 26.1)
- потерю marketplace-специфики (Владелец агрегатора, номер заказа)
"""

import _bootstrap  # noqa: F401

import io
import os
import sys
import tempfile


_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["CASE_DB_PATH"] = _TMP_DB
os.environ["SECRET_KEY"] = "test-pdf-content"
os.environ["SESSION_COOKIE_SECURE"] = "false"

import web.app as app_module
import modules.consumer.engine as consumer_engine


# ─── Мок LLM ───
def _fake_llm_uk_noise(instructions, user_input):
    if "тишин" in instructions or "участковому" in instructions.lower():
        return {"parsed": {
            "описание_проблемы_формальное": (
                "Из квартиры, расположенной выше, систематически в ночное "
                "время доносится громкая музыка."
            ),
        }}
    return {"parsed": {
        "описание_проблемы_формальное": (
            "В подъезде многоквартирного дома не производится уборка "
            "мест общего пользования."
        ),
        "упоминание_повторного_обращения": "",
        "применимые_нормы": [
            "Статья 161 Жилищного кодекса РФ",
            "Постановление Правительства РФ от 13.08.2006 № 491",
            "Постановление Госстроя РФ от 27.09.2003 № 170",
        ],
    }}


_ZPP = "Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»"


def _fake_llm_consumer(instructions, user_input):
    """Имитация «правильного LLM» — выбирает нормы по подтипу текста."""
    import json as _json
    payload = _json.loads(user_input) if isinstance(user_input, str) else {}
    text = str(payload.get("проблема", "")).lower()

    # ─── Marketplace: просрочка доставки (ст. 23.1) ───
    if ("ozon" in text or "wildberries" in text or "маркетплейс" in text) and (
        "не доставил" in text or "не пришл" in text or "просроч" in text
        or "задерж" in text or "не привезл" in text
    ):
        return {"parsed": {
            "описание_проблемы_формальное": "Заказан товар на маркетплейсе, "
                "срок передачи нарушен.",
            "требование": "Уплатить неустойку за нарушение срока передачи "
                "предварительно оплаченного товара",
            "применимые_нормы": [
                f"Статья 23.1 {_ZPP}",
                f"Статья 26.1 {_ZPP}",
                f"Статья 22 {_ZPP}",
            ],
        }}

    # ─── Marketplace: недостоверная инфа (ст. 12) ───
    if ("ozon" in text or "wildberries" in text or "маркетплейс" in text) and (
        "недостовер" in text or "ввёл в заблужд" in text
        or "не соответствует описан" in text
    ):
        return {"parsed": {
            "описание_проблемы_формальное": "Информация о товаре на "
                "маркетплейсе недостоверна.",
            "требование": "Возместить убытки, причинённые недостоверной "
                "информацией о товаре",
            "применимые_нормы": [
                f"Статья 12 {_ZPP}",
                f"Статья 26.1 {_ZPP}",
                f"Статья 18 {_ZPP}",
            ],
        }}

    # ─── Marketplace: обычный брак ───
    if "ozon" in text or "маркетплейс" in text or "wildberries" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Заказан товар на маркетплейсе, "
                "при доставке обнаружен недостаток.",
            "требование": "Возвратить уплаченную за товар сумму",
            "применимые_нормы": [
                f"Статья 26.1 {_ZPP}",
                f"Статья 18 {_ZPP}",
                f"Статья 22 {_ZPP}",
            ],
        }}

    # ─── return14 ───
    if "не подош" in text or "куртк" in text or "размер" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Приобретён товар, не подошедший "
                "по размеру. Товар не был в употреблении.",
            "требование": "Расторгнуть договор купли-продажи и возвратить "
                "уплаченную сумму",
            "применимые_нормы": [
                f"Статья 25 {_ZPP}",
                f"Статья 22 {_ZPP}",
            ],
        }}

    # ─── Defect: отказ в ремонте (ст. 20, 21) ───
    if "отказ" in text and "ремонт" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Продавец отказал в приёме товара "
                "на гарантийный ремонт.",
            "требование": "Принять товар в безвозмездный гарантийный ремонт",
            "применимые_нормы": [
                f"Статья 20 {_ZPP}",
                f"Статья 21 {_ZPP}",
                f"Статья 18 {_ZPP}",
            ],
        }}

    # ─── Defect: просрочка ГАРАНТИЙНОГО ремонта >45 дней (ст. 20, 23) ───
    # Только для ремонта ТОВАРА (телефон, техника, устройство),
    # не для ремонта квартиры (это услуга — ниже)
    if ("гарантийн" in text or "сервис" in text or "мастерск" in text
        or "телефон" in text or "устройств" in text) and (
        "ремонт" in text
    ) and (
        "третий месяц" in text or "длится" in text
        or "45" in text or "свыше" in text
    ):
        return {"parsed": {
            "описание_проблемы_формальное": "Гарантийный ремонт длится свыше "
                "45 дней.",
            "требование": "Уплатить неустойку за нарушение срока устранения "
                "недостатков",
            "применимые_нормы": [
                f"Статья 20 {_ZPP}",
                f"Статья 23 {_ZPP}",
            ],
        }}

    # ─── Service: смета превышена (ст. 33) ───
    if "смет" in text or "дороже" in text or "доплати" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Исполнитель превысил смету без "
                "согласования с потребителем.",
            "требование": "Привести расчёты в соответствие с согласованной сметой",
            "применимые_нормы": [
                f"Статья 33 {_ZPP}",
                f"Статья 29 {_ZPP}",
            ],
        }}

    # ─── Service: отказ от услуги (ст. 32) ───
    if "отказ" in text or "передумал" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Потребитель отказался от услуги "
                "до её завершения.",
            "требование": "Возвратить уплаченную сумму за вычетом фактических "
                "расходов",
            "применимые_нормы": [
                f"Статья 32 {_ZPP}",
                f"Статья 22 {_ZPP}",
            ],
        }}

    # ─── Service: банк ───
    if "банк" in text or "кредит" in text or "навязали страховку" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Банк навязал дополнительную услугу "
                "при оформлении кредита.",
            "требование": "Возместить убытки, причинённые навязанной услугой",
            "применимые_нормы": [
                f"Статья 16 {_ZPP}",
                f"Статья 29 {_ZPP}",
            ],
        }}

    # ─── Service: страховка ───
    if "страхов" in text or "осаго" in text or "каско" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Страховая компания нарушила срок "
                "выплаты страхового возмещения.",
            "требование": "Выплатить страховое возмещение и неустойку",
            "применимые_нормы": [
                f"Статья 28 {_ZPP}",
                f"Статья 29 {_ZPP}",
            ],
        }}

    # ─── Service: нарушен срок (стандарт) ───
    if "ремонт" in text or "срок" in text or "услуг" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Оплачена услуга, срок выполнения "
                "нарушен.",
            "требование": "Выполнить работу в установленный срок",
            "применимые_нормы": [
                f"Статья 27 {_ZPP}",
                f"Статья 28 {_ZPP}",
                f"Статья 31 {_ZPP}",
            ],
        }}

    # ─── Defect: по умолчанию ───
    return {"parsed": {
        "описание_проблемы_формальное": "Приобретён смартфон, выявлен "
            "недостаток — устройство перестало работать.",
        "требование": "Возвратить уплаченную за товар сумму",
        "применимые_нормы": [
            f"Статья 18 {_ZPP}",
            f"Статья 22 {_ZPP}",
        ],
    }}


app_module._call_llm = _fake_llm_uk_noise
consumer_engine._call_llm = _fake_llm_consumer


app = app_module.app
app.config["TESTING"] = True


# ─── Хелпер: читаем текст PDF ───
def _pdf_text(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


# ─── Формы ───
UK_FORM = {
    "problem_type": "uk",
    "проблема": "в подъезде не убирают две недели, мусор и грязь",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "дата_начала": "две недели",
    "обращались_ранее": "нет",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
    "organization": "ООО «УК Тестовая»",
}

NOISE_FORM = {
    "problem_type": "noise",
    "проблема": "сосед сверху громко слушает музыку по ночам, не даёт спать",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "дата_начала": "месяц",
    "обращались_ранее": "нет",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
    "organization": "Начальнику ОВД по Тверскому району",
}

DEFECT_FORM = {
    "problem_type": "consumer",
    "проблема": "купил смартфон Samsung, через неделю перестал работать",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «М.Видео»",
    "адрес_продавца": "125167, г. Москва, Ленинградский пр-т, д. 76А",
    "дата_покупки": "10.08.2026",
    "цена": "50000",
    "дата_обращения": "01.09.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

RETURN14_FORM = {
    "problem_type": "consumer",
    "проблема": "купила куртку, не подошёл размер, хочу вернуть деньги",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «Модный Магазин»",
    "адрес_продавца": "г. Москва, ул. Тверская, д. 1",
    "дата_покупки": "10.09.2026",
    "фио": "Иванова Мария Петровна",
    "телефон": "+7 999 123-45-67",
}

MARKETPLACE_FORM = {
    "problem_type": "consumer",
    "проблема": "заказал на Ozon телефон, пришёл с трещиной, хочу вернуть деньги",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "Ozon",
    "номер_заказа": "12345678-1234",
    "дата_покупки": "01.09.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

SERVICE_FORM = {
    "problem_type": "consumer",
    "проблема": "заказал ремонт квартиры, обещали за 2 недели, делают третий месяц, сроки нарушены",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «РемСтрой»",
    "адрес_продавца": "г. Москва, ул. Строителей, д. 5",
    "цена": "80000",
    "дата_обращения": "01.08.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}


_DOC_RE = None  # ленивая инициализация re


# ═══ Формы для подтипов ═══
DELIVERY_DELAY_FORM = {
    "problem_type": "consumer",
    "проблема": "заказал на Ozon смартфон, не доставили уже 3 недели, просрочка",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "Ozon",
    "номер_заказа": "98765432-1111",
    "цена": "50000",
    "дата_обращения": "01.08.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

MARKETPLACE_MISINFO_FORM = {
    "problem_type": "consumer",
    "проблема": "на Ozon купил телефон, в описании написано 256 ГБ, "
                "а пришёл 128 ГБ, недостоверная информация",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "Ozon",
    "номер_заказа": "12345678-9999",
    "дата_покупки": "01.09.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

REPAIR_REFUSE_FORM = {
    "problem_type": "consumer",
    "проблема": "отнёс телефон в сервис, отказ в ремонте, "
                "говорят не гарантийный случай",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «М.Видео»",
    "адрес_продавца": "125167, г. Москва, Ленинградский пр-т, д. 76А",
    "дата_покупки": "10.08.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

REPAIR_DELAY_FORM = {
    "problem_type": "consumer",
    "проблема": "сдал телефон в гарантийный ремонт в сервис, "
                "ремонт длится уже третий месяц",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «Сервис-Центр»",
    "адрес_продавца": "г. Москва, ул. Мастеров, д. 1",
    "цена": "40000",
    "дата_обращения": "01.06.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

SERVICE_ESTIMATE_FORM = {
    "problem_type": "consumer",
    "проблема": "заказал ремонт квартиры, сказали 50 тысяч, "
                "теперь требуют 120 тысяч, смету не согласовывали",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «РемСтрой»",
    "адрес_продавца": "г. Москва, ул. Строителей, д. 5",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

SERVICE_REFUSE_FORM = {
    "problem_type": "consumer",
    "проблема": "оплатил курсы английского, передумал учиться, хочу отказаться",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «Лингва-Школа»",
    "адрес_продавца": "г. Москва, ул. Пушкина, д. 10",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

SERVICE_BANK_FORM = {
    "problem_type": "consumer",
    "проблема": "взял кредит в банке, навязали страховку",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ПАО «Банк»",
    "адрес_продавца": "г. Москва, ул. Банковская, д. 1",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}

SERVICE_INSURANCE_FORM = {
    "problem_type": "consumer",
    "проблема": "страховая не выплачивает по ОСАГО, просрочка",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «СтрахКомпания»",
    "адрес_продавца": "г. Москва, ул. Страховая, д. 5",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}


def _submit_and_get_pdf(client, form: dict) -> str:
    """POST /submit (с CSRF) -> GET /case/<ref> -> находим doc_id -> скачиваем PDF."""
    import re as _re

    # CSRF-токен из формы главной
    r_home = client.get("/")
    html_home = r_home.get_data(as_text=True)
    m_csrf = _re.search(r'name="_csrf_token"\s+value="([^"]+)"', html_home)
    csrf = m_csrf.group(1) if m_csrf else ""

    form_data = dict(form)
    form_data["_csrf_token"] = csrf
    form_data["privacy_consent"] = "1"
    r = client.post("/submit", data=form_data, follow_redirects=False)
    if r.status_code != 302:
        return f"[НЕ 302: {r.status_code}]"
    loc = r.headers.get("Location", "")
    if "/case/" not in loc:
        return f"[нет /case в Location: {loc[:80]}]"

    case_ref = loc.split("/case/")[-1].split("?")[0]

    # GET карточку и парсим первый /case/<ref>/pdf/<N>
    r_card = client.get(f"/case/{case_ref}")
    if r_card.status_code != 200:
        return f"[карточка {r_card.status_code}]"

    html = r_card.get_data(as_text=True)
    m = _re.search(rf"/case/{_re.escape(case_ref)}/pdf/(\d+)", html)
    if not m:
        return f"[в карточке нет ссылки на PDF]"

    doc_id = m.group(1)
    r2 = client.get(f"/case/{case_ref}/pdf/{doc_id}")
    if r2.status_code != 200:
        return f"[PDF {r2.status_code}]"
    return _pdf_text(r2.data)


def main():
    passed = 0
    failed = 0

    def check(cond, label, snippet=""):
        nonlocal passed, failed
        if cond:
            print(f"[PASS] {label}")
            passed += 1
        else:
            print(f"[FAIL] {label}")
            if snippet:
                print(f"       snippet: {snippet[:200]}")
            failed += 1

    client = app.test_client()

    # ═══ 1. UK PDF ═══
    txt = _submit_and_get_pdf(client, UK_FORM)
    check("ЗАЯВЛЕНИЕ" in txt, "UK: заголовок ЗАЯВЛЕНИЕ")
    check("содержание общего имущества" in txt or "уборк" in txt.lower(),
          "UK: тема — содержание/уборка", txt[:200])
    check("161" in txt and "Жилищн" in txt, "UK: ст. 161 ЖК РФ")
    check("491" in txt, "UK: Постановление 491")
    check("170" in txt, "UK: Постановление 170")
    check("ПРОШУ" in txt, "UK: блок ПРОШУ")
    # pypdf может по-разному извлекать кавычки — проверяем часть без них
    check("УК Тестовая" in txt or "Тестовая" in txt,
          "UK: название УК в шапке")

    # ═══ 2. Noise PDF ═══
    txt = _submit_and_get_pdf(client, NOISE_FORM)
    check("ЗАЯВЛЕНИЕ" in txt, "шум: заголовок ЗАЯВЛЕНИЕ")
    check("тишин" in txt.lower() or "покоя" in txt.lower(),
          "шум: тема — тишина/покой")
    check("Москв" in txt, "шум: регион Москва в PDF (закон)")
    check("ПРОШУ" in txt, "шум: блок ПРОШУ")

    # ═══ 3. Defect + расчёт ═══
    txt = _submit_and_get_pdf(client, DEFECT_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "defect: заголовок ПРЕТЕНЗИЯ")
    check("возврате стоимости" in txt.lower() or "ненадлежащего качества" in txt.lower(),
          "defect: подзаголовок")
    check("18" in txt and "ЗоЗПП" in txt, "defect: ст. 18 ЗоЗПП")
    check("М.Видео" in txt or "М.Видео" in txt.replace(" ", ""),
          "defect: продавец в шапке")
    check("РАСЧЁТ" in txt and "НЕУСТОЙК" in txt,
          "defect: блок РАСЧЁТ НЕУСТОЙКИ")
    check("50 000" in txt or "50000" in txt or "50\u00a0000" in txt,
          "defect: цена 50 000 в расчёте")
    check("1.0%" in txt or "1,0%" in txt or "1 %" in txt or "1.0 %" in txt,
          "defect: ставка 1% в расчёте")

    # ═══ 4. Return14 (ФИО женщины в дательном) ═══
    txt = _submit_and_get_pdf(client, RETURN14_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "return14: заголовок ПРЕТЕНЗИЯ")
    check("надлежащего качества" in txt.lower(), "return14: подзаголовок")
    check("25" in txt and "ЗоЗПП" in txt, "return14: ст. 25 ЗоЗПП")
    # Покупатель пишется в родительном: «от гр. Ивановой Марии Петровны»
    # («Гражданке» — только для адресата-физлица, а тут продавец ООО)
    check("Ивановой" in txt, "return14: фамилия в родительном (Ивановой)")
    check("Марии" in txt, "return14: имя в родительном (Марии)")
    check("Петровны" in txt, "return14: отчество в родительном (Петровны)")
    # В return14 не должно быть расчёта (нет цены+даты обращения)
    check("РАСЧЁТ НЕУСТОЙКИ" not in txt,
          "return14: без блока расчёта (нет данных)")

    # ═══ 5. Marketplace ═══
    txt = _submit_and_get_pdf(client, MARKETPLACE_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "marketplace: заголовок ПРЕТЕНЗИЯ")
    check("Владельцу агрегатора" in txt,
          "marketplace: 'Владельцу агрегатора'", txt[:300])
    check("Интернет Решения" in txt,
          "marketplace: ООО «Интернет Решения» (Ozon)")
    check("Номер заказа" in txt, "marketplace: строка 'Номер заказа'")
    check("12345678-1234" in txt, "marketplace: сам номер заказа")
    check("26.1" in txt, "marketplace: ст. 26.1 ЗоЗПП")

    # ═══ 6. Service (срок) ═══
    txt = _submit_and_get_pdf(client, SERVICE_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "service: заголовок ПРЕТЕНЗИЯ")
    check("27" in txt and "ЗоЗПП" in txt, "service: ст. 27 ЗоЗПП")
    check("28" in txt, "service: ст. 28 ЗоЗПП")
    check("РемСтрой" in txt, "service: исполнитель в шапке")
    check("РАСЧЁТ НЕУСТОЙК" in txt, "service: блок расчёта")
    check("80 000" in txt or "80000" in txt or "80\u00a0000" in txt,
          "service: цена 80 000")
    check("3.0%" in txt or "3,0%" in txt or "3 %" in txt or "3.0 %" in txt,
          "service: ставка 3%")

    # ═══ 6б. Компенсация морального вреда во всех consumer-сценариях ═══
    for label, form in [
        ("defect", DEFECT_FORM),
        ("return14", RETURN14_FORM),
        ("marketplace", MARKETPLACE_FORM),
        ("service", SERVICE_FORM),
    ]:
        txt_c = _submit_and_get_pdf(client, form)
        check("Компенсировать моральный вред" in txt_c,
              f"PDF {label}: пункт 'Компенсировать моральный вред'")
        check("ст. 15" in txt_c,
              f"PDF {label}: упоминание ст. 15 ЗоЗПП")

    # ═══ 6в. Подтипы — нормы и блоки ═══

    # delivery_delay (просрочка доставки, ст. 23.1)
    txt = _submit_and_get_pdf(client, DELIVERY_DELAY_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "delivery_delay: заголовок")
    check("23.1" in txt, "delivery_delay: ст. 23.1")
    check("26.1" in txt, "delivery_delay: ст. 26.1")
    check("РАСЧЁТ НЕУСТОЙК" in txt, "delivery_delay: блок расчёта")
    check("0.5%" in txt or "0,5%" in txt or "0.5 %" in txt,
          "delivery_delay: ставка 0.5%")
    check("98765432-1111" in txt, "delivery_delay: номер заказа в шапке")

    # marketplace_misinfo (недостоверная, ст. 12)
    txt = _submit_and_get_pdf(client, MARKETPLACE_MISINFO_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "misinfo: заголовок")
    check("12" in txt, "misinfo: ст. 12 ЗоЗПП")
    check("26.1" in txt, "misinfo: ст. 26.1")
    check("Владельцу агрегатора" in txt, "misinfo: шапка агрегатора")

    # repair_refuse (отказ в ремонте, ст. 20, 21)
    txt = _submit_and_get_pdf(client, REPAIR_REFUSE_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "repair_refuse: заголовок")
    check("20" in txt and "ЗоЗПП" in txt, "repair_refuse: ст. 20")
    check("21" in txt, "repair_refuse: ст. 21")

    # repair_delay (просрочка ремонта, ст. 20, 23)
    txt = _submit_and_get_pdf(client, REPAIR_DELAY_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "repair_delay: заголовок")
    check("20" in txt and "23" in txt, "repair_delay: ст. 20, 23")
    check("РАСЧЁТ НЕУСТОЙК" in txt, "repair_delay: блок расчёта")

    # service_estimate (смета, ст. 33)
    txt = _submit_and_get_pdf(client, SERVICE_ESTIMATE_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "estimate: заголовок")
    check("33" in txt and "ЗоЗПП" in txt, "estimate: ст. 33")

    # service_refuse (отказ от услуги, ст. 32)
    txt = _submit_and_get_pdf(client, SERVICE_REFUSE_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "refuse_service: заголовок")
    check("32" in txt and "ЗоЗПП" in txt, "refuse_service: ст. 32")

    # service_bank (навязанная услуга, ст. 16)
    txt = _submit_and_get_pdf(client, SERVICE_BANK_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "bank: заголовок")
    check("16" in txt and "ЗоЗПП" in txt, "bank: ст. 16")

    # service_insurance (страховая, ст. 28)
    txt = _submit_and_get_pdf(client, SERVICE_INSURANCE_FORM)
    check("ПРЕТЕНЗИЯ" in txt, "insurance: заголовок")
    check("28" in txt and "ЗоЗПП" in txt, "insurance: ст. 28")

    # ═══ 7. Правовые нормы не выдуманы ═══
    # (проверка что LLM не выдумала ФЗ «О полиции» для UK, например)
    # Уже проверено выше — здесь просто sanity
    txt = _submit_and_get_pdf(client, UK_FORM)
    check("О полиции" not in txt, "нормы: нет ФЗ «О полиции» в UK")

    # cleanup
    try:
        os.unlink(_TMP_DB)
    except OSError:
        pass

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()