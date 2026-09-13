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


def _fake_llm_consumer(instructions, user_input):
    import json as _json
    payload = _json.loads(user_input) if isinstance(user_input, str) else {}
    text = str(payload.get("проблема", "")).lower()
    if "ozon" in text or "маркетплейс" in text or "wildberries" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Заказан товар на маркетплейсе, при доставке обнаружен недостаток.",
            "требование": "Возвратить уплаченную за товар сумму",
            "применимые_нормы": [
                "Статья 26.1 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
                "Статья 18 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
                "Статья 22 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
            ],
        }}
    if "не подош" in text or "куртк" in text or "размер" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Приобретён товар, не подошедший по размеру. Товар не был в употреблении.",
            "требование": "Расторгнуть договор купли-продажи и возвратить уплаченную сумму",
            "применимые_нормы": [
                "Статья 25 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
                "Статья 22 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
            ],
        }}
    if "ремонт" in text or "срок" in text or "услуг" in text:
        return {"parsed": {
            "описание_проблемы_формальное": "Оплачена услуга, срок выполнения нарушен.",
            "требование": "Выполнить работу в установленный срок",
            "применимые_нормы": [
                "Статья 27 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
                "Статья 28 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
                "Статья 31 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
            ],
        }}
    # defect
    return {"parsed": {
        "описание_проблемы_формальное": "Приобретён смартфон, выявлен недостаток — устройство перестало работать.",
        "требование": "Возвратить уплаченную за товар сумму",
        "применимые_нормы": [
            "Статья 18 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
            "Статья 22 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
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


def _submit_and_get_pdf(client, form: dict) -> str:
    """POST /submit -> GET /case/<ref> -> находим doc_id -> скачиваем PDF."""
    import re as _re

    r = client.post("/submit", data=form, follow_redirects=False)
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