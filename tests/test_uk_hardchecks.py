"""Comprehensive offline regression suite for Legal Mind Module 2 hard checks.

v2.4: NEIGHBOR expectation now verifies the stop reason mentions сосед.
"""

import _bootstrap  # noqa: F401

import json
from modules.uk.hardchecks import (
    hard_pre_check,
    emergency_signal,
    neighbor_behavior_signal,
    specific_object_signal,
)

BASE = {
    "адрес": "г. Москва, ул. Тестовая, 1",
    "дата_начала": "недавно",
    "обращались_ранее": "нет",
}


def check(problem, expected, label):
    data = dict(BASE)
    data["проблема"] = problem
    result = hard_pre_check(data)
    if expected == "OK":
        ok = result is None
    elif expected == "EMERGENCY":
        ok = result is not None and result["emergency"] is True and result["stop"] is True
    elif expected == "NEIGHBOR":
        ok = (
            result is not None
            and result["emergency"] is False
            and result["stop"] is True
            and "сосед" in (result["stop_reason"] or "").lower()
        )
    elif expected == "STOP":
        ok = result is not None and result["stop"] is True
    else:
        raise ValueError(expected)
    return {
        "label": label,
        "expected": expected,
        "ok": ok,
        "input": problem,
        "result": result,
    }


def main():
    tests = [
        # ─── Neighbor mention is not a neighbor complaint. ───
        ("Сосед сообщил о проблеме общего имущества: в подъезде не убирают", "OK", "neighbor reported UK issue"),
        ("Сосед пожаловался, что в подъезде не убирают", "OK", "neighbor is reporter"),
        ("Сосед помог открыть дверь подъезда", "OK", "neutral neighbor mention"),
        ("Домофон сломан, но сосед помог мне попасть домой", "OK", "neighbor mention in UK complaint"),
        ("соседка сообщила, что в подъезде не убирают", "OK", "female neighbor is reporter"),
        ("сосед из кв. 5 тоже жалуется на холодные батареи", "OK", "neighbor reports utility issue"),

        # ─── Neighbor behavior. ───
        ("соседи шумят ночью, невозможно спать", "NEIGHBOR", "obvious neighbor behavior"),
        ("соседи громко слушают музыку по ночам", "NEIGHBOR", "neighbor music"),
        ("сосед курит на лестничной площадке", "NEIGHBOR", "neighbor smoking"),
        ("сосед кричит и мешает спать", "NEIGHBOR", "neighbor shouting"),
        ("квартира соседа — источник постоянного шума", "NEIGHBOR", "neighbor apartment source of noise"),
        ("из квартиры №45 постоянно громкая музыка", "NEIGHBOR", "apartment number behavior"),
        ("соседи из кв. 45 постоянно шумят по ночам, невозможно спать", "NEIGHBOR", "кв. with dot"),
        ("из кв. 12 громкая музыка по ночам", "NEIGHBOR", "кв. before number"),
        ("кв. 45 шумит", "NEIGHBOR", "bare кв. + number"),
        ("соседка сверху громко топает", "NEIGHBOR", "female neighbor, tопает"),
        ("сосед сверху сверлит стену весь день", "NEIGHBOR", "сверлит"),
        ("соседи грохочет мебелью ночью", "NEIGHBOR", "грохочет"),
        ("квартира №45 затапливает мою квартиру из-за протечки", "OK", "neighbor apartment is not noise complaint"),

        # ─── Emergency, current. ───
        ("в подъезде сильно пахнет газом", "EMERGENCY", "current gas"),
        ("прямо сейчас пахнет газом", "EMERGENCY", "current gas explicit"),
        ("сейчас снова сильно пахнет газом", "EMERGENCY", "renewed gas"),
        ("сейчас воняет газом", "EMERGENCY", "current gas colloquial"),
        ("запах газа не проходит", "EMERGENCY", "gas persists"),
        ("утечка газа продолжается", "EMERGENCY", "leak continues"),
        ("сейчас искрит проводка", "EMERGENCY", "current sparking"),
        ("сейчас снова искрит проводка", "EMERGENCY", "renewed sparking"),
        ("в электрощитке короткое замыкание", "EMERGENCY", "short circuit"),
        ("горит проводка в подъезде", "EMERGENCY", "burning wiring"),
        ("появилась большая трещина в несущей стене", "EMERGENCY", "load-bearing crack"),
        ("в подъезде обрушивается потолок", "EMERGENCY", "collapsing ceiling"),
        ("прорвало трубу, затапливает подъезд", "EMERGENCY", "flooding"),
        ("в подъезде пожар", "EMERGENCY", "fire"),

        # ─── Resolved / historical. ───
        ("вчера пахло газом, сейчас запаха нет", "OK", "gas resolved"),
        ("запах газа исчез, сейчас всё нормально", "OK", "gas disappeared"),
        ("утечка газа устранена, сейчас безопасно", "OK", "gas leak resolved"),
        ("раньше пахло газом, но сейчас снова сильно пахнет газом", "EMERGENCY", "old then renewed gas"),
        ("вчера искрила проводка, сейчас всё нормально", "OK", "sparking resolved"),
        ("пожар был вчера, его потушили", "OK", "past fire"),
        ("пожар снова начался", "EMERGENCY", "restarted fire"),
        ("раньше был пожар, сейчас снова горит", "EMERGENCY", "historical then current fire"),
        ("утечка газа была вчера, сегодня всё устранено", "OK", "historical leak resolved"),
        ("вчера была авария с газом, сейчас запаха нет, но в подъезде не убирают", "OK", "resolved emergency plus UK issue"),
        ("на прошлой неделе пахло газом, сейчас всё нормально", "OK", "historical week marker"),
        ("пару дней назад пахло газом, сейчас нет", "OK", "historical paar days"),

        # ─── Ongoing overrides historical. ───
        ("несколько дней назад появился запах газа, до сих пор не устранили", "EMERGENCY", "ongoing leak"),
        ("вчера началась утечка газа, до сих пор пахнет", "EMERGENCY", "ongoing after historical"),
        ("позавчера искрила проводка, всё ещё искрит", "EMERGENCY", "ongoing sparking"),

        # ─── Ordinary UK cases. ───
        ("в подъезде не убирают уже две недели, грязь и мусор", "OK", "ordinary cleaning"),
        ("батареи еле тёплые, дома холодно", "OK", "heating"),
        ("лифт не работает уже неделю", "OK", "elevator"),
        ("снег во дворе не убирают пятый день", "OK", "snow"),
        ("после дождя с потолка течёт вода", "OK", "roof leak"),
        ("домофон сломан, дверь подъезда не закрывается", "OK", "intercom"),

        # ─── Vague descriptions. ───
        ("что-то не работает в доме", "STOP", "vague description"),
        ("в доме проблемы", "STOP", "vague description"),
        ("ужас что творится", "STOP", "vague description"),
        ("кошмар просто", "STOP", "vague description"),

        # ─── Short. ───
        ("плохо", "STOP", "short description"),
    ]

    results = [check(*t) for t in tests]

    # Address / length cases.
    no_address = dict(BASE, проблема="в подъезде не убирают мусор уже неделю", адрес="")
    no_address_result = hard_pre_check(no_address)
    results.append({
        "label": "missing address",
        "expected": "STOP",
        "ok": no_address_result is not None and not no_address_result["emergency"],
        "result": no_address_result,
    })

    neighbor_no_address = dict(
        BASE,
        проблема="соседи шумят по ночам, невозможно спать",
        адрес="",
    )
    neighbor_no_address_result = hard_pre_check(neighbor_no_address)
    results.append({
        "label": "neighbor priority over address",
        "expected": "NEIGHBOR",
        "ok": neighbor_no_address_result is not None
              and not neighbor_no_address_result["emergency"]
              and "сосед" in neighbor_no_address_result["stop_reason"].lower(),
        "result": neighbor_no_address_result,
    })

    # ─── Utility checks ───
    utility = {
        "neighbor_noise": neighbor_behavior_signal("соседи шумят ночью"),
        "neighbor_reporter": neighbor_behavior_signal("сосед сообщил о проблеме общего имущества"),
        "neighbor_kv_dot": neighbor_behavior_signal("соседи из кв. 45 постоянно шумят по ночам"),
        "neighbor_female_case": neighbor_behavior_signal("соседка сверху громко топает"),
        "neighbor_sverlit": neighbor_behavior_signal("сосед сверху сверлит стену"),
        "current_gas_category": emergency_signal("сейчас снова сильно пахнет газом"),
        "resolved_gas": emergency_signal("вчера пахло газом, сейчас запаха нет"),
        "ongoing_gas": emergency_signal("несколько дней назад появился запах газа, до сих пор не устранили"),
        "specific_cleaning": specific_object_signal("в подъезде не убирают уже две недели"),
        "specific_vague": specific_object_signal("что-то не работает в доме"),
    }
    utility_ok = (
        utility["neighbor_noise"] is True
        and utility["neighbor_reporter"] is False
        and utility["neighbor_kv_dot"] is True
        and utility["neighbor_female_case"] is True
        and utility["neighbor_sverlit"] is True
        and utility["current_gas_category"] is not None
        and utility["resolved_gas"] is None
        and utility["ongoing_gas"] is not None
        and utility["specific_cleaning"] is True
        and utility["specific_vague"] is False
    )
    results.append({"label": "utility checks", "ok": utility_ok, "utility": utility})

    passed = sum(bool(r["ok"]) for r in results)
    failed = len(results) - passed
    report = {"total": len(results), "passed": passed, "failed": failed, "results": results}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    with open("results_module2_hardchecks_v2.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()