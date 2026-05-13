"""Inspector → Oversight bridge.

این سرویس درخواست‌های آمده از ویجت «بازرس ویژه» (در `/projects/[id]`) را
به تسک‌های مرکز نظارت تبدیل می‌کند.

ویژگی‌ها:
- پرامپت غنی (strong prompt) با همهٔ context (متن، URL، logs، screenshots)
- توصیف بصری screenshots با vision model (در صورت موجود) → متن قابل خواندن
  برای مدل‌های غیر بصری مرکز نظارت
- ذخیره inspector_context کامل (screenshots base64 + logs) در فایل جداگانه
- بدون محدودیت طول پرامپت (می‌تواند ۲۵٬۰۰۰+ کاراکتر باشد)
- ساخت OversightTask با `source="inspector_chat"` یا `"inspector_visual"`
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# storage path
try:
    from .oversight_service import STORAGE_DIR
    _INSPECTOR_CTX_DIR = STORAGE_DIR / "inspector_context"
    _INSPECTOR_CTX_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    _INSPECTOR_CTX_DIR = Path("/tmp/inspector_context")
    _INSPECTOR_CTX_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Vision describe — توصیف screenshot با vision model
# ============================================================

async def describe_screenshot_with_vision(
    base64_img: str,
    user_context: str,
    page_url: str = "",
    dom_text: str = "",
) -> Dict[str, Any]:
    """با vision model عکس را به متن غنی تبدیل می‌کند.

    خروجی JSON: {scene, ocr_text, ui_elements, error_signals, layout_hints}
    اگر هیچ vision model در دسترس نباشد، fallback با مقادیر empty + پیام.
    """
    try:
        from .ai_manager import get_ai_manager
        from ..core.models_registry import get_vision_models
        from .ai_base import Message
        import os as _os

        vision_models = get_vision_models() or []
        env_keys = {
            "openai": ["OPENAI_API_KEY"],
            "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        }
        with_key = set()
        for p, ks in env_keys.items():
            if any((_os.environ.get(k) or "").strip() for k in ks):
                with_key.add(p.lower())

        picked = None
        for m in vision_models:
            prov = m.provider
            prov_str = (prov.value if hasattr(prov, "value") else str(prov)).lower()
            if prov_str in with_key:
                picked = m
                break
        if not picked:
            return {
                "scene": "(vision model در دسترس نیست — مدل اجراکننده می‌تواند مستقیم به inspector_context_id مراجعه کند تا عکس را ببیند)",
                "ocr_text": "",
                "ui_elements": "",
                "error_signals": "",
                "layout_hints": "",
                "vision_model_used": None,
            }

        # 🆕 (Phase 3 fix) — vision prompt با هشدار صریح در برابر hallucination
        prompt_text = (
            "این یک screenshot از صفحهٔ یک پروژهٔ نرم‌افزاری است. وظیفهٔ تو این است\n"
            "که محتوای آن را به‌صورت متن غنی توصیف کنی، تا یک مدل غیر بصری بتواند\n"
            "بدون دیدن عکس بفهمد چه چیزی روی صفحه است.\n\n"
            f"📋 ویژگی/AC مورد بررسی: {user_context[:500]}\n"
            f"URL صفحه: {page_url}\n\n"
            "علاوه بر توصیف، **بسنج که آیا ویژگی فوق در screenshot دیده می‌شود یا نه**.\n\n"
            "⚠️ هشدار بسیار مهم — جلوگیری از hallucination:\n"
            "- متن AC را به‌عنوان «راهنمای جست‌وجو» در نظر بگیر، **نه به‌عنوان حقیقت**.\n"
            "- فقط چیزی را که **قطعاً در عکس می‌بینی** گزارش کن.\n"
            "- اگر AC از یک «صفحه‌ی X»، «دکمه‌ی Y»، یا «پنل Z» حرف می‌زند، ببین\n"
            "  **آن نام و آن المان دقیقاً در screenshot نوشته شده یا قابل مشاهده است یا نه**.\n"
            "- اگر فقط دارای یک dashboard عمومی یا homepage هستی و AC از یک\n"
            "  feature خاص حرف می‌زند که ندیدی، **حتماً 'no' بده** — حتی اگر\n"
            "  صفحه «شاید» چیزی شبیه به آن داشته باشد.\n"
            "- 'yes' فقط زمانی که المان دقیق AC را در عکس **به طور صریح** می‌بینی.\n\n"
            "خروجی فقط JSON خالص (بدون ``` یا توضیح اضافی):\n"
            "{\n"
            '  "scene": "توصیف کلی صحنه در ۲-۴ جمله — فقط چیزی که می‌بینی",\n'
            '  "ocr_text": "متن کامل قابل مشاهده در عکس (همهٔ کلمات، دکمه‌ها، label ها)",\n'
            '  "ui_elements": "لیست عناصر UI (دکمه‌ها، فرم‌ها، nav، panel ها) — فقط واقعی",\n'
            '  "error_signals": "هر گونه نشانهٔ خطا، warning، یا state غیرعادی",\n'
            '  "layout_hints": "ساختار کلی صفحه",\n'
            '  "feature_present": "yes|no|unclear",\n'
            '  "feature_reason": "یک جمله: چه المان مشخصی دیدی یا ندیدی"\n'
            "}\n\n"
            "📐 معیار سخت‌گیر feature_present:\n"
            '- "yes": **نام دقیق** المان AC در صفحه نوشته شده، یا المان واضح\n'
            "  و قابل تشخیص است (مثلاً دکمه‌ای با همان label که AC ذکر کرده).\n"
            '- "no": صفحه homepage / dashboard عمومی است و چیزی شبیه AC نیست،\n'
            "  یا صفحه ۴۰۴ یا خطا است، یا یک صفحه‌ی نامرتبط است.\n"
            '- "unclear": فقط در ابهام واقعی — مثلاً ممکن است feature پشت scroll\n'
            "  باشد، یا نام مشابه ولی نه دقیق دیدی.\n\n"
            "🛑 مثال ضد-hallucination (بسیار مهم — این الگو را اشتباه نکن):\n"
            "  AC: «تولید verify_plan توسط AI»\n"
            "  صفحه: یک dashboard با عنوان «پروژه‌ها» و چند کارت پروژه\n"
            "  پاسخ غلط: yes («پنل با عنوان و دکمه دیده می‌شود») ❌\n"
            "  پاسخ درست: no («کلمات کلیدی verify_plan/AI generator در صفحه\n"
            "                   نوشته نشده — فقط dashboard کلی است») ✓\n\n"
            "🔍 الزام keyword: اگر AC شامل اسم خاصی مثل\n"
            "   verify_plan, smart_nav, backend_log, RoutingDiagram, …\n"
            "   است، آن **رشتهٔ دقیق** باید در ocr_text یا ui_elements\n"
            "   دیده شود تا feature_present=yes بدهی. اگر این رشته در\n"
            "   متن صفحه نیست، **یا 'no' یا 'unclear'** بده — نه 'yes'.\n\n"
            "‼️ پیش‌فرض ایمن: اگر شک داری، 'no' بده، نه 'yes'."
        )

        ai_mgr = get_ai_manager()
        msg = Message(role="user", content=prompt_text, images=[base64_img])
        try:
            response = await ai_mgr.generate(
                model_id=picked.id,
                messages=[msg],
                max_tokens=2500,
                temperature=0.2,
            )
            txt = (response.content or "").strip()
            if txt.startswith("```"):
                txt = txt.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end > start:
                try:
                    parsed = json.loads(txt[start:end + 1])
                    fp_raw = str(parsed.get("feature_present", "") or "").strip().lower()
                    if fp_raw not in ("yes", "no", "unclear"):
                        fp_raw = "unclear"
                    _ocr = str(parsed.get("ocr_text", ""))[:4000]
                    _ui_elems = str(parsed.get("ui_elements", ""))[:2000]
                    _fp_reason = str(parsed.get("feature_reason", ""))[:600]

                    # 🆕 (Phase 4 fix) — keyword-overlap override: اگر AI گفت
                    # feature_present=yes ولی هیچ یک از کلیدواژه‌های «ویژه»
                    # AC (CamelCase / snake_case) در DOM واقعی (html source
                    # از Playwright) دیده نمی‌شود، احتمالاً hallucination است
                    # و باید override به unclear شود. **مهم:** ما اینجا
                    # روی dom_text (zاد حقیقت Playwright) چک می‌کنیم،
                    # نه روی ocr_text/ui_elements که خود AI تولید کرده —
                    # چون AI می‌تواند کلمات AC را در OCR fake کند.
                    if fp_raw == "yes" and user_context:
                        import re as _re
                        _ac_specific = set(_re.findall(
                            r"\b([A-Z][a-zA-Z0-9]{3,}|[a-z][a-z0-9_]{4,}_[a-z0-9_]+)\b",
                            user_context,
                        ))
                        _generic = {
                            "AI", "API", "URL", "JSON", "HTML", "CSS", "true",
                            "false", "None", "self", "data", "page", "step",
                            "probe", "Stage", "stage",
                        }
                        _ac_specific = {
                            k for k in _ac_specific if k not in _generic
                        } - {"step_probe", "auto_verify"}
                        if _ac_specific:
                            # zاد حقیقت: DOM واقعی + OCR vision به عنوان
                            # fallback (اگر dom_text در دسترس نباشد)
                            _dom_low = (dom_text or "").lower()
                            _ocr_low = (_ocr + " " + _ui_elems).lower()
                            # match در DOM (اعتماد بالا) یا fallback به OCR
                            _matched_dom = [
                                k for k in _ac_specific
                                if k.lower() in _dom_low
                            ]
                            _matched_ocr_only = [
                                k for k in _ac_specific
                                if k.lower() in _ocr_low
                                and k.lower() not in _dom_low
                            ]
                            if not _matched_dom and not (_matched_ocr_only and not dom_text):
                                # هیچ keyword در DOM نیست و یا dom_text داریم
                                # و در آن هم نیست → hallucination
                                fp_raw = "unclear"
                                _ocr_hint = (
                                    f" (OCR ادعا کرد {_matched_ocr_only} ولی DOM نه — "
                                    f"احتمال OCR fake)" if _matched_ocr_only else ""
                                )
                                _fp_reason = (
                                    f"⚠️ keyword-override (DOM): AI گفت yes ولی هیچ "
                                    f"از {sorted(list(_ac_specific))[:5]} در DOM واقعی "
                                    f"دیده نمی‌شود{_ocr_hint}. "
                                    f"اصلی: {_fp_reason[:160]}"
                                )

                    return {
                        "scene": str(parsed.get("scene", ""))[:2000],
                        "ocr_text": _ocr,
                        "ui_elements": _ui_elems,
                        "error_signals": str(parsed.get("error_signals", ""))[:1500],
                        "layout_hints": str(parsed.get("layout_hints", ""))[:1500],
                        "feature_present": fp_raw,
                        "feature_reason": _fp_reason,
                        "vision_model_used": picked.id,
                    }
                except Exception as je:
                    logger.warning(f"vision JSON parse failed: {je}")
            return {
                "scene": txt[:2000],
                "ocr_text": "",
                "ui_elements": "",
                "error_signals": "",
                "layout_hints": "",
                "vision_model_used": picked.id,
                "_raw_parse_failed": True,
            }
        except Exception as e:
            logger.warning(f"vision call failed: {e}")
            return {
                "scene": f"(خطا در vision call: {str(e)[:200]})",
                "ocr_text": "",
                "ui_elements": "",
                "error_signals": "",
                "layout_hints": "",
                "vision_model_used": None,
            }
    except Exception as e:
        logger.warning(f"describe_screenshot setup failed: {e}")
        return {
            "scene": "",
            "ocr_text": "",
            "ui_elements": "",
            "error_signals": "",
            "layout_hints": "",
            "vision_model_used": None,
        }


# ============================================================
# Strong prompt builder
# ============================================================

def _truncate(s: Optional[str], n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[:n] + "…"


def build_inspector_strong_prompt(
    *,
    user_request: str,
    enhanced_prompt: Optional[str] = None,
    mode: str = "chat",
    project_full_name: str = "",
    page_url: str = "",
    frontend_url: str = "",
    backend_url: str = "",
    console_logs: Optional[List[Dict[str, Any]]] = None,
    backend_logs: Optional[List[Dict[str, Any]]] = None,
    related_urls: Optional[List[str]] = None,
    api_paths: Optional[List[str]] = None,
    screenshots_with_descriptions: Optional[List[Dict[str, Any]]] = None,
    captured_at: Optional[str] = None,
    core_only: bool = True,
) -> str:
    """پرامپت اصلی برای ساخت task.prompt — clean و قابل copy.

    اگر core_only=True (پیش‌فرض):
      - meta خاص inspector (URL inspector، timestamps screenshot، یادداشت
        «از بازرس ویژه» و ...) خارج می‌شود
      - فقط چیزهایی که یک سیستم بیرونی برای انجام کار نیاز دارد، باقی می‌ماند:
        * هدف کاربر
        * توصیف visual صفحه (محتوای OCR + UI + error signals)
        * logs (مفید برای debug)
        * api_paths
        * AC

    اگر core_only=False:
      - مثل قبل، همه meta هم درون پرامپت می‌آیند (برای نمایش full)
    """
    from .oversight_strong_prompt import EXECUTOR_DISCLAIMER

    parts: List[str] = []
    parts.append(EXECUTOR_DISCLAIMER)
    parts.append("")
    parts.append("---")
    parts.append("")

    parts.append("# 🎯 هدف کاربر")
    parts.append("")
    parts.append(user_request.strip())
    if enhanced_prompt and enhanced_prompt.strip() != user_request.strip():
        parts.append("")
        parts.append("## نسخهٔ ساختارمند شده (enhanced)")
        parts.append(enhanced_prompt.strip())

    # محل وقوع فقط در حالت non-core
    if not core_only:
        parts.append("")
        parts.append("## 📍 محل وقوع")
        if project_full_name:
            parts.append(f"- **پروژه**: `{project_full_name}`")
        if page_url:
            parts.append(f"- **URL صفحه**: `{page_url}`")
        if frontend_url:
            parts.append(f"- **Frontend URL**: `{frontend_url}`")
        if backend_url:
            parts.append(f"- **Backend URL**: `{backend_url}`")

    # api_paths (همیشه — مفید برای کار)
    if api_paths:
        parts.append("")
        parts.append("## 🔗 API endpoints مرتبط")
        for p in api_paths[:15]:
            parts.append(f"- `{p}`")

    # محتوای بصری — همیشه شامل (محتوا، نه meta عکس)
    screenshots = screenshots_with_descriptions or []
    if screenshots:
        parts.append("")
        parts.append("## 📸 محتوای بصری صفحه (تحلیل عکس‌ها)")
        parts.append("")
        parts.append(
            "*این بخش حاصل تحلیل visual توسط مدل بصری است — "
            "تا یک مدل غیر بصری هم بتواند بدون دیدن عکس بفهمد روی صفحه چه چیزی است.*"
        )
        for i, ss in enumerate(screenshots, start=1):
            d = ss.get("description") or {}
            # meta عکس (URL/timestamp/مدل) فقط در non-core
            if not core_only:
                parts.append("")
                parts.append(f"### 📸 عکس #{i}")
                if ss.get("page_url"):
                    parts.append(f"- **موقعیت**: `{ss['page_url']}`")
                if ss.get("timestamp"):
                    parts.append(f"- **زمان**: {ss['timestamp']}")
                vm = d.get("vision_model_used")
                if vm:
                    parts.append(f"- **توصیف با**: `{vm}`")
            else:
                # core_only: فقط یک شماره بدون meta
                if len(screenshots) > 1:
                    parts.append("")
                    parts.append(f"### بخش #{i}")
            if d.get("scene"):
                parts.append("")
                parts.append("**📝 توصیف صحنه:**")
                parts.append(d["scene"])
            if d.get("ocr_text"):
                parts.append("")
                parts.append("**🔤 متن داخل تصویر (OCR):**")
                parts.append("```")
                parts.append(d["ocr_text"])
                parts.append("```")
            if d.get("ui_elements"):
                parts.append("")
                parts.append("**🎨 عناصر UI:**")
                parts.append(d["ui_elements"])
            if d.get("error_signals"):
                parts.append("")
                parts.append("**⚠️ نشانه‌های خطا (visual):**")
                parts.append(d["error_signals"])
            if d.get("layout_hints"):
                parts.append("")
                parts.append("**🗺 layout:**")
                parts.append(d["layout_hints"])

    cl = [l for l in (console_logs or []) if isinstance(l, dict)]
    cl_err = [l for l in cl if (l.get("level") or "").lower() in ("error", "warn", "warning")]
    cl_other = [l for l in cl if l not in cl_err]
    cl_show = (cl_err + cl_other)[:25]
    if cl_show:
        parts.append("")
        parts.append(f"## 📋 لاگ‌های Console ({len(cl)} کل، {len(cl_show)} نمایش)")
        parts.append("```")
        for l in cl_show:
            lvl = (l.get("level") or "info").upper()
            ts = l.get("timestamp") or ""
            msg = _truncate(l.get("message") or "", 500)
            src = l.get("source") or ""
            parts.append(f"[{lvl}] {ts} {src}: {msg}")
        parts.append("```")

    bl = [l for l in (backend_logs or []) if isinstance(l, dict)]
    bl_err = [l for l in bl if (l.get("level") or "").lower() in ("error", "warn", "warning", "critical")]
    bl_other = [l for l in bl if l not in bl_err]
    bl_show = (bl_err + bl_other)[:25]
    if bl_show:
        parts.append("")
        parts.append(f"## 🖥 لاگ‌های Backend ({len(bl)} کل، {len(bl_show)} نمایش)")
        parts.append("```")
        for l in bl_show:
            lvl = (l.get("level") or "info").upper()
            ts = l.get("timestamp") or ""
            msg = _truncate(l.get("message") or "", 500)
            svc = l.get("service_id") or l.get("service_name") or ""
            parts.append(f"[{lvl}] {ts} {svc}: {msg}")
        parts.append("```")

    if related_urls and not core_only:
        parts.append("")
        parts.append("## 🔗 URLs مرتبط")
        for u in related_urls[:20]:
            parts.append(f"- `{u}`")

    parts.append("")
    parts.append("## 🚧 معیار پذیرش")
    parts.append("- [ ] مشکل توصیف‌شده بالا حل شود و در محیط واقعی قابل تأیید باشد")
    parts.append("- [ ] هیچ regression روی عملکرد فعلی صفحه/feature ها رخ ندهد")
    parts.append("- [ ] لاگ‌های خطای موجود (در صورت وجود) برطرف شوند یا توضیح داده شوند")
    parts.append("- [ ] اگر تغییر UI لازم بود، تطبیق با تم dark mode حفظ شود")
    parts.append("- [ ] تست‌های موجود pass شوند (npm test / pytest)")

    if not core_only:
        parts.append("")
        parts.append("## ⚠️ یادداشت")
        parts.append(f"- این تسک از طریق **بازرس ویژه** ارسال شده — حالت: `{mode}`")
        if captured_at:
            parts.append(f"- لاگ/عکس‌ها در زمان `{captured_at}` گرفته شده‌اند")
        if screenshots:
            parts.append(
                "- screenshots اصلی به‌صورت base64 در `inspector_context_id` "
                "ذخیره شده‌اند."
            )

    return "\n".join(parts)


def build_inspector_meta_summary(
    *,
    mode: str,
    project_full_name: str,
    page_url: str,
    frontend_url: str,
    backend_url: str,
    captured_at: str,
    screenshots: Optional[List[Dict[str, Any]]] = None,
    related_urls: Optional[List[str]] = None,
    inspector_session_id: Optional[str] = None,
) -> str:
    """متن meta جدا — نمایش در UI مرکز نظارت در کنار پرامپت اصلی، نه داخلش.

    شامل: page_url، timestamps، session id، توصیف اینکه این تسک از کجا آمده.
    این بخش‌ها به‌درد سیستم بیرونی نمی‌خورند ولی برای trace/audit مفیدند.
    """
    lines: List[str] = []
    lines.append(f"📥 از بازرس ویژه — حالت `{mode}`")
    if captured_at:
        lines.append(f"🕒 زمان گرفتن: `{captured_at}`")
    if page_url:
        lines.append(f"📍 URL صفحه: `{page_url}`")
    if frontend_url:
        lines.append(f"🌐 Frontend URL: `{frontend_url}`")
    if backend_url:
        lines.append(f"🖥 Backend URL: `{backend_url}`")
    if inspector_session_id:
        lines.append(f"🔖 Session ID: `{inspector_session_id}`")
    if screenshots:
        lines.append("")
        lines.append(f"📸 Screenshots ({len(screenshots)} عکس):")
        for i, ss in enumerate(screenshots, start=1):
            bits: List[str] = []
            if ss.get("page_url"):
                bits.append(f"URL: `{ss['page_url']}`")
            if ss.get("timestamp"):
                bits.append(f"زمان: `{ss['timestamp']}`")
            lines.append(f"  • عکس #{i} — {' · '.join(bits) if bits else '—'}")
    if related_urls:
        lines.append("")
        lines.append("🔗 URLs مرتبط (در inspector لاگ شده):")
        for u in related_urls[:15]:
            lines.append(f"  • `{u}`")
    return "\n".join(lines)


# ============================================================
# Inspector context storage
# ============================================================

def save_inspector_context(
    *,
    task_id: str,
    project_id: str,
    project_full_name: str,
    mode: str,
    user_request: str,
    enhanced_prompt: Optional[str],
    screenshots: Optional[List[Dict[str, Any]]],
    vision_descriptions: Optional[List[Dict[str, Any]]],
    console_logs: Optional[List[Dict[str, Any]]],
    backend_logs: Optional[List[Dict[str, Any]]],
    related_urls: Optional[List[str]],
    api_paths: Optional[List[str]],
    frontend_url: Optional[str],
    backend_url: Optional[str],
    page_url: Optional[str],
    inspector_session_id: Optional[str],
    meta_summary: Optional[str] = None,
) -> str:
    """ذخیرهٔ context کامل (شامل screenshots base64) در فایل جداگانه."""
    ctx_id = task_id
    path = _INSPECTOR_CTX_DIR / f"{ctx_id}.json"
    data: Dict[str, Any] = {
        "context_id": ctx_id,
        "task_id": task_id,
        "project_id": project_id,
        "project_full_name": project_full_name,
        "mode": mode,
        "user_request": user_request,
        "enhanced_prompt": enhanced_prompt,
        "meta_summary": meta_summary or "",
        "screenshots": screenshots or [],
        "vision_descriptions": vision_descriptions or [],
        "console_logs": console_logs or [],
        "backend_logs": backend_logs or [],
        "related_urls": related_urls or [],
        "api_paths": api_paths or [],
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "page_url": page_url,
        "inspector_session_id": inspector_session_id,
        "captured_at": _now_iso(),
    }
    try:
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as e:
        logger.warning(f"save_inspector_context failed: {e}")
    return ctx_id


def read_inspector_context(context_id: str) -> Optional[Dict[str, Any]]:
    path = _INSPECTOR_CTX_DIR / f"{context_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"read_inspector_context failed: {e}")
        return None


# ============================================================
# Resolve project_full_name
# ============================================================

def resolve_project_full_name_for_inspector(
    project_id: str, hint_full_name: Optional[str] = None,
) -> Optional[str]:
    """تلاش برای پیدا کردن project_full_name واقعی از روی project_id/hint."""
    if hint_full_name and "/" in hint_full_name:
        return hint_full_name
    if "/" in project_id:
        return project_id
    if project_id.startswith("gh_"):
        try:
            from .oversight_service import get_oversight_service
            svc = get_oversight_service()
            for w in svc.watched:
                if not w.repo_full_name or "/" not in w.repo_full_name:
                    continue
                normalized = "gh_" + w.repo_full_name.replace("/", "_").replace("-", "_")
                if normalized == project_id:
                    return w.repo_full_name
                normalized2 = "gh_" + w.repo_full_name.replace("/", "_")
                if normalized2 == project_id:
                    return w.repo_full_name
        except Exception:
            pass
    return None


# ============================================================
# Main: process from inspector
# ============================================================

async def process_from_inspector(
    *,
    project_id: str,
    project_full_name: Optional[str],
    mode: str,
    user_request: str,
    enhanced_prompt: Optional[str],
    screenshots: Optional[List[Dict[str, Any]]],
    console_logs: Optional[List[Dict[str, Any]]],
    backend_logs: Optional[List[Dict[str, Any]]],
    related_urls: Optional[List[str]],
    api_paths: Optional[List[str]],
    frontend_url: Optional[str],
    backend_url: Optional[str],
    page_url: Optional[str],
    priority: str,
    task_type: str,
    inspector_session_id: Optional[str],
) -> Dict[str, Any]:
    """تابع اصلی — پردازش کامل request inspector و ساخت OversightTask."""
    from .oversight_service import get_oversight_service, OversightTask

    svc = get_oversight_service()

    # 1. resolve watched_id
    resolved_full_name = resolve_project_full_name_for_inspector(project_id, project_full_name)
    watched = None
    if resolved_full_name:
        watched = next(
            (w for w in svc.watched if w.repo_full_name == resolved_full_name), None,
        )
    if watched is None:
        for w in svc.watched:
            if w.repo_full_name and w.repo_full_name.replace("/", "_").replace("-", "_") in project_id:
                watched = w
                resolved_full_name = w.repo_full_name
                break

    if watched is None:
        raise ValueError(
            f"این پروژه ({project_id}) به مرکز نظارت اضافه نشده است. "
            f"از پنل /oversight ابتدا آن را add watched کنید."
        )

    watched_id = watched.id
    project_full_name_final = watched.repo_full_name

    # 2. vision describe (فقط visual_debug) — موازی برای جلوگیری از timeout
    screenshots_with_descriptions: List[Dict[str, Any]] = []
    vision_descriptions: List[Dict[str, Any]] = []
    if mode == "visual_debug" and screenshots:
        import asyncio as _asyncio
        # فیلتر فقط screenshot هایی با base64
        valid_screenshots = [ss for ss in screenshots if ss.get("base64")]

        async def _safe_describe(ss):
            try:
                return await describe_screenshot_with_vision(
                    ss.get("base64") or "",
                    user_request or "",
                    ss.get("page_url") or "",
                )
            except Exception as e:
                logger.warning(f"vision describe failed for one screenshot: {e}")
                return {
                    "scene": f"(خطا در توصیف: {str(e)[:150]})",
                    "ocr_text": "", "ui_elements": "", "error_signals": "",
                    "layout_hints": "", "vision_model_used": None,
                }

        # موازی اجرا — تا 5 screenshot هم در ~30s تمام شوند
        results = await _asyncio.gather(
            *[_safe_describe(ss) for ss in valid_screenshots],
            return_exceptions=True,
        )
        for ss, d in zip(valid_screenshots, results):
            if isinstance(d, Exception):
                d = {
                    "scene": f"(exception: {str(d)[:150]})",
                    "ocr_text": "", "ui_elements": "", "error_signals": "",
                    "layout_hints": "", "vision_model_used": None,
                }
            vision_descriptions.append(d)
            screenshots_with_descriptions.append({
                "page_url": ss.get("page_url"),
                "timestamp": ss.get("timestamp"),
                "description": d,
            })

    # 3. ساخت پرامپت اصلی (core_only=True — clean برای copy/export)
    #    + meta summary جدا برای نمایش در UI
    captured_at = _now_iso()
    strong_prompt = build_inspector_strong_prompt(
        user_request=user_request,
        enhanced_prompt=enhanced_prompt,
        mode=mode,
        project_full_name=project_full_name_final,
        page_url=page_url or "",
        frontend_url=frontend_url or "",
        backend_url=backend_url or "",
        console_logs=console_logs,
        backend_logs=backend_logs,
        related_urls=related_urls,
        api_paths=api_paths,
        screenshots_with_descriptions=screenshots_with_descriptions or None,
        captured_at=captured_at,
        core_only=True,
    )
    meta_summary = build_inspector_meta_summary(
        mode=mode,
        project_full_name=project_full_name_final,
        page_url=page_url or "",
        frontend_url=frontend_url or "",
        backend_url=backend_url or "",
        captured_at=captured_at,
        screenshots=screenshots,
        related_urls=related_urls,
        inspector_session_id=inspector_session_id,
    )

    # 4. title
    title_src = (user_request or "").strip()
    if enhanced_prompt and len(enhanced_prompt.strip()) > 0 and len(title_src) < 20:
        title_src = enhanced_prompt.strip()
    first_line = (title_src.split("\n", 1)[0]).strip()
    title = first_line[:80] if first_line else "تسک از بازرس ویژه"
    if mode == "visual_debug":
        title = f"[بصری] {title}"
    elif mode == "chat":
        title = f"[چت] {title}"

    # 5. ساخت تسک مستقیم (بدون محدودیت طول prompt)
    new_task = OversightTask(
        id=str(uuid.uuid4()),
        watched_id=watched_id,
        project_full_name=project_full_name_final,
        title=title,
        prompt=strong_prompt,
        raw_idea=user_request,
        type=task_type,
        priority=priority,
        status="pending",
        source=("inspector_visual" if mode == "visual_debug" else "inspector_chat"),
        execution_mode=getattr(watched, "default_execution_mode", "manual") or "manual",
        target_files=[],
        acceptance_criteria=[],
        inspector_mode=mode,
        inspector_context_id=None,
        # 🆕 meta_summary مستقیم در task ذخیره می‌شود — UI سبک و قابل دسترسی
        inspector_meta_summary=meta_summary,
    )

    # 6. ذخیره context
    try:
        ctx_id = save_inspector_context(
            task_id=new_task.id,
            project_id=project_id,
            project_full_name=project_full_name_final,
            mode=mode,
            user_request=user_request,
            enhanced_prompt=enhanced_prompt,
            screenshots=screenshots,
            vision_descriptions=vision_descriptions,
            console_logs=console_logs,
            backend_logs=backend_logs,
            related_urls=related_urls,
            api_paths=api_paths,
            frontend_url=frontend_url,
            backend_url=backend_url,
            page_url=page_url,
            inspector_session_id=inspector_session_id,
            meta_summary=meta_summary,
        )
        new_task.inspector_context_id = ctx_id
    except Exception as e:
        logger.warning(f"save inspector context failed: {e}")

    # 7. ذخیره در tasks
    async with svc._lock:
        svc.tasks.append(new_task)
        svc._save_tasks()

    # 8. notify (best-effort) — از event task_from_inspector که default_enabled=True
    try:
        from .notification_service import notification_service
        await notification_service.notify_event(
            "task_from_inspector",
            (
                f"📥 *تسک جدید از بازرس ویژه*\n\n"
                f"📁 `{project_full_name_final}`\n"
                f"🎯 _{title[:100]}_\n"
                f"🔖 حالت: `{mode}`{(' · ' + str(len(screenshots)) + ' عکس' if screenshots else '')}\n"
                f"🔁 priority: `{priority}`"
            ),
            subject="تسک از بازرس ویژه",
            priority=priority,
            project_name=project_full_name_final,
            watched_id=watched_id,
        )
    except Exception as _e:
        logger.debug(f"inspector task notify failed: {_e}")

    return {
        "ok": True,
        "task_id": new_task.id,
        "watched_id": watched_id,
        "project_full_name": project_full_name_final,
        "oversight_url": f"/oversight?tab=tasks&watched={watched_id}#{new_task.id}",
        "prompt_length": len(strong_prompt),
        "prompt_excerpt": strong_prompt[:400] + ("…" if len(strong_prompt) > 400 else ""),
        "vision_descriptions_count": len(vision_descriptions),
        "inspector_context_id": new_task.inspector_context_id,
    }
