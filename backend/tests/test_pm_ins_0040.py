"""PM-INS-0040 — «موتور خالق پرامپتِ پروژهٔ قبلی را می‌سازد».

مالک شرحِ «تبدیلِ تاریخِ شمسی» داد و پرامپتِ «ماشین‌حساب» گرفت. این تست‌ها قفل می‌کنند که:
۱) پرامپت فقط از ورودیِ همان درخواست ساخته می‌شود و همان ورودی برگردانده می‌شود (دیدنی در فرم)؛
۲) خودسنجی پرامپتِ ناهم‌موضوع را می‌گیرد و endpoint ِ ساخت آن را نمی‌سازد (۴۰۹).
"""
import asyncio
import json

import pytest
from fastapi import HTTPException

from app.services.creator_idea_to_prompt import idea_to_strong_prompt_for_creator, topic_check

SHAMSI = ("صفحهٔ وب تک‌فایلی HTML/CSS/JS برای تبدیل تاریخ شمسی↔میلادی، نام روز هفته، "
          "اعتبارسنجی ۳۰ اسفند، تست‌های ۱۴۰۳/۱/۱=2024-03-20")
CALC = ("ماشین‌حساب تک‌صفحه‌ای با تاریخچهٔ محاسبات و حالت تاریک، فقط HTML/CSS/JS بدون بک‌اند، "
        "پیام خطای فارسی برای تقسیم بر صفر")

CALC_JSON = {
    "title": "ماشین‌حساب تک‌صفحه‌ای با تاریخچه و حالت تاریک",
    "structured_description": "یک ماشین‌حساب مرورگری با چهار عمل اصلی، تاریخچهٔ محاسبات و حالت تاریک؛ تقسیم بر صفر پیام خطا می‌دهد.",
    "tech_stack": ["HTML", "CSS", "JavaScript"],
    "key_features": ["چهار عمل اصلی", "تاریخچهٔ محاسبات", "حالت تاریک", "پیام خطای تقسیم بر صفر"],
    "user_stories": ["به‌عنوان کاربر می‌خواهم محاسبات قبلی را در تاریخچه ببینم"],
    "architecture_summary": "یک فایل index.html و ماژول calculator.js",
    "file_structure_hint": ["index.html", "calculator.js", "style.css"],
    "endpoints_or_routes": [], "data_models": [],
    "non_functional_requirements": ["بدون بک‌اند"], "warnings": [], "constraints": [],
}
SHAMSI_JSON = {
    "title": "مبدل تاریخ شمسی ↔ میلادی (تک‌فایلی)",
    "structured_description": "صفحه‌ای تک‌فایلی که تاریخ شمسی را به میلادی و برعکس تبدیل می‌کند، نام روز هفته را نشان می‌دهد و ۳۰ اسفندِ سالِ غیرکبیسه را رد می‌کند.",
    "tech_stack": ["HTML", "CSS", "JavaScript"],
    "key_features": ["تبدیل شمسی به میلادی", "تبدیل میلادی به شمسی", "نام روز هفته", "اعتبارسنجی ۳۰ اسفند"],
    "user_stories": ["به‌عنوان کاربر می‌خواهم تاریخ شمسی را وارد کنم تا معادل میلادی را ببینم"],
    "architecture_summary": "همه‌چیز در index.html",
    "file_structure_hint": ["index.html"],
    "endpoints_or_routes": [], "data_models": [],
    "non_functional_requirements": ["تست‌های درون‌صفحه"], "warnings": [], "constraints": [],
}


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _gen_returning(payload, seen=None):
    async def gen(prompt, model_ids=None):
        if seen is not None:
            seen.append(prompt)
        return json.dumps(payload, ensure_ascii=False)
    return gen


@pytest.fixture(autouse=True)
def _no_knowledge_center(monkeypatch):
    async def none(*a, **k):
        return {"block": "", "line": "", "entries": []}
    import app.services.knowledge_center_service as kc
    monkeypatch.setattr(kc, "experience_context", none)


def _text(payload):
    """متنی که مدل نوشته (مقدارها، نه نامِ کلیدهای JSON)."""
    out = []
    for v in payload.values():
        out.extend(str(x) for x in v) if isinstance(v, list) else out.append(str(v))
    return "\n".join(out)


# ------------------------------------------------------------------ topic_check
def test_same_topic_is_ok():
    t = topic_check(SHAMSI, _text(SHAMSI_JSON))
    assert t["status"] == "ok" and t["ok"] and t["coverage"] >= 0.8


def test_the_owners_case_calculator_prompt_for_a_shamsi_idea_is_a_mismatch():
    t = topic_check(SHAMSI, _text(CALC_JSON))
    assert t["status"] == "mismatch" and not t["ok"]
    assert "شمس" in t["missing"]
    # «تاریخچه» نباید به‌جای «تاریخ» قبول شود — تطبیق واژه‌ای است نه زیررشته‌ای
    assert "تاریخ" in t["missing"]


def test_generic_words_alone_do_not_make_a_match():
    # هر دو «صفحهٔ وب، HTML/CSS/JS، تست» دارند؛ همین اشتراکِ عمومی نباید کافی باشد
    assert topic_check(CALC, _text(SHAMSI_JSON))["status"] == "mismatch"


def test_cannot_check_is_not_reported_as_ok_or_mismatch():
    assert topic_check("یک اپ", "هر چیزی")["status"] == "unchecked"
    en = "A todo list web app with drag and drop reordering, due dates, tags and local storage persistence"
    t = topic_check(en, _text(CALC_JSON))
    assert t["status"] == "unchecked" and t["note"]


def test_arabic_letter_forms_and_half_space_do_not_break_matching():
    t = topic_check("تبديل تاريخ شمسي به ميلادي و نام روز هفته", "تبدیل تاریخ‌های شمسی به میلادی؛ روزِ هفته")
    assert t["status"] == "ok"


# ------------------------------------------------------------------ the prompt comes from THIS request only
def test_prompt_is_built_only_from_the_current_input_and_echoes_it():
    seen = []
    r = _run(idea_to_strong_prompt_for_creator(
        idea=SHAMSI, name="test-shamsi-date-converter", ai_generate=_gen_returning(SHAMSI_JSON, seen),
        model_ids=["m"], user_idea=SHAMSI))
    assert SHAMSI in seen[0] and "ماشین" not in seen[0]            # چیزی جز ورودیِ فعلی به مدل نمی‌رود
    assert r["source_idea"] == SHAMSI and r["source_name"] == "test-shamsi-date-converter"
    assert "شمسی" in r["full_prompt_text"] and "ماشین‌حساب" not in r["full_prompt_text"]
    assert r["topic_check"]["status"] == "ok"


def test_two_consecutive_requests_do_not_leak_into_each_other():
    _run(idea_to_strong_prompt_for_creator(
        idea=CALC, name="test-calculator", ai_generate=_gen_returning(CALC_JSON), model_ids=["m"], user_idea=CALC))
    seen = []
    r = _run(idea_to_strong_prompt_for_creator(
        idea=SHAMSI, name="test-shamsi-date-converter", ai_generate=_gen_returning(SHAMSI_JSON, seen),
        model_ids=["m"], user_idea=SHAMSI))
    assert "ماشین" not in seen[0] and "ماشین" not in r["full_prompt_text"]


def test_model_drifting_to_another_topic_is_flagged_with_a_warning():
    r = _run(idea_to_strong_prompt_for_creator(
        idea=SHAMSI, name="test-shamsi-date-converter", ai_generate=_gen_returning(CALC_JSON),
        model_ids=["m"], user_idea=SHAMSI))
    assert r["topic_check"]["status"] == "mismatch"
    assert r["warnings"] and r["warnings"][0].startswith("⛔")


def test_topic_is_checked_against_the_users_own_words_not_reference_context():
    ref = SHAMSI + "\n\n---\n## 📚 پروژه‌های مرجع\n" + ("ماشین‌حساب تاریخچه حالت تاریک محاسبات " * 40)
    r = _run(idea_to_strong_prompt_for_creator(
        idea=ref, name="x", ai_generate=_gen_returning(CALC_JSON), model_ids=["m"], user_idea=SHAMSI))
    assert r["topic_check"]["status"] == "mismatch" and r["source_idea"] == SHAMSI


# ------------------------------------------------------------------ the create endpoint refuses (server-side boundary)
def _create(description, structured, **kw):
    from app.api.routes import simple_projects as sp
    req = sp.CreateProjectRequest(name="test-shamsi-date-converter", description=description, model_ids=["m"],
                                  structured_prompt=structured, **kw)
    return _run(sp.create_project(req))


def test_create_refuses_a_prompt_that_is_not_about_the_form_description():
    stale = _run(idea_to_strong_prompt_for_creator(
        idea=CALC, name="test-calculator", ai_generate=_gen_returning(CALC_JSON), model_ids=["m"], user_idea=CALC))
    with pytest.raises(HTTPException) as e:
        _create(SHAMSI, stale)
    assert e.value.status_code == 409
    assert e.value.detail["error"] == "prompt_topic_mismatch"
    assert e.value.detail["topic_check"]["status"] == "mismatch"


def test_create_lets_a_matching_prompt_through_the_topic_gate(monkeypatch):
    from app.api.routes import simple_projects as sp
    good = _run(idea_to_strong_prompt_for_creator(
        idea=SHAMSI, name="test-shamsi-date-converter", ai_generate=_gen_returning(SHAMSI_JSON),
        model_ids=["m"], user_idea=SHAMSI))

    class Reached(Exception):
        pass

    def boom(*a, **k):
        raise Reached()
    # از دروازهٔ هم‌موضوعی که گذشت، به مرحلهٔ بعد (ساخت) می‌رسد — همان‌جا متوقفش می‌کنیم
    import app.services.simple_creator as sc
    monkeypatch.setattr(sc, "get_simple_creator", lambda: type("C", (), {"create_project": boom, "__getattr__": lambda s, n: boom})())
    try:
        _create(SHAMSI, good)
    except HTTPException as e:
        assert e.status_code != 409, e.detail
    except Exception:
        pass


def test_explicit_override_passes_the_gate(monkeypatch):
    stale = _run(idea_to_strong_prompt_for_creator(
        idea=CALC, name="test-calculator", ai_generate=_gen_returning(CALC_JSON), model_ids=["m"], user_idea=CALC))
    import app.services.simple_creator as sc

    def boom(*a, **k):
        raise RuntimeError("reached")
    monkeypatch.setattr(sc, "get_simple_creator", lambda: type("C", (), {"__getattr__": lambda s, n: boom})())
    try:
        _create(SHAMSI, stale, topic_override=True)
    except HTTPException as e:
        assert e.status_code != 409, e.detail
    except Exception:
        pass
