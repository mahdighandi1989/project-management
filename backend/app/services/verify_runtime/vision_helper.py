"""Vision helper for inspector_probe — تحلیل screenshot با fallback chain.

سه‌مرحله‌ای:
1. Vision multimodal موجود (همان منطق تب بازرسی، از describe_screenshot_with_vision)
2. اگر در دسترس نبود یا fail کرد → text-only fallback با verify_model روی
   لاگ‌ها/HTML/URL (بدون دیدن تصویر، حداقل یک توضیح زمینه‌ای)
3. اگر هر دو fail کردند → خروجی source="none"

این ماژول mستقل است و هیچ exception ای بیرون نمی‌اندازد.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def analyze_screenshot(
    screenshot_path: str,
    context: Dict[str, Any],
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """تحلیل screenshot با fallback chain.

    Args:
      screenshot_path: مسیر فایل png روی دیسک
      context: dict شامل {url, console_logs, backend_logs, html_excerpt, ac_text}
              برای fallback متنی استفاده می‌شود
      verify_model_id: مدل verifier برای fallback متنی (در صورت نبود vision)

    Returns:
      {
        "description": str,        # متن آزاد توصیف صفحه
        "ui_elements": str,        # opcional
        "error_signals": str,      # opcional
        "ocr_text": str,           # opcional (فقط در vision موجود)
        "source": str,             # "vision_<model>" | "fallback_text_only_<model>" | "none"
        "raw": dict | None,        # خروجی خام برای debug
      }
    """
    p = Path(screenshot_path)
    if not p.exists() or not p.is_file():
        return _none_result(f"screenshot not found: {screenshot_path}")

    # --- 1) تلاش vision multimodal ---
    vision_result = await _try_vision(p, context)
    if vision_result is not None and vision_result.get("description"):
        return vision_result

    # --- 2) fallback متنی با verify model ---
    if verify_model_id:
        text_result = await _try_text_fallback(context, verify_model_id)
        if text_result is not None and text_result.get("description"):
            return text_result

    # --- 3) هیچ‌کدام موفق نشد ---
    return _none_result("vision unavailable + text fallback unavailable or failed")


async def _try_vision(
    screenshot_path: Path,
    context: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """با describe_screenshot_with_vision موجود، اگر vision model در دسترس است."""
    try:
        with screenshot_path.open("rb") as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode("ascii")
    except Exception as e:
        logger.debug(f"vision_helper: read file failed: {e}")
        return None

    try:
        from ..oversight_inspector_bridge import describe_screenshot_with_vision
        user_ctx = str(context.get("ac_text") or context.get("user_context") or "")[:500]
        page_url = str(context.get("url") or "")[:500]
        result = await describe_screenshot_with_vision(b64, user_ctx, page_url)
    except Exception as e:
        logger.debug(f"vision_helper: describe_screenshot_with_vision call failed: {e}")
        return None

    if not isinstance(result, dict):
        return None
    vision_model = result.get("vision_model_used")
    scene = str(result.get("scene") or "").strip()
    if not vision_model or not scene or scene.startswith("(vision model در دسترس نیست"):
        # vision موجود نبود — اجازه بده fallback تلاش کند
        return None
    if scene.startswith("(خطا در vision call"):
        # خطای vision — اجازه بده fallback تلاش کند
        return None

    # 🆕 (Phase 2 fix 3) — feature_present از vision (yes/no/unclear)
    fp = str(result.get("feature_present") or "unclear").strip().lower()
    if fp not in ("yes", "no", "unclear"):
        fp = "unclear"
    return {
        "description": scene,
        "ui_elements": str(result.get("ui_elements") or ""),
        "error_signals": str(result.get("error_signals") or ""),
        "ocr_text": str(result.get("ocr_text") or ""),
        "layout_hints": str(result.get("layout_hints") or ""),
        "feature_present": fp,
        "feature_reason": str(result.get("feature_reason") or ""),
        "source": f"vision_{vision_model}",
        "raw": result,
    }


async def _try_text_fallback(
    context: Dict[str, Any],
    verify_model_id: str,
) -> Optional[Dict[str, Any]]:
    """fallback متنی — به مدل verify می‌گوییم بر اساس لاگ‌ها/URL یک توصیف بسازد."""
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception as e:
        logger.debug(f"vision_helper: ai_manager import failed: {e}")
        return None

    url = str(context.get("url") or "")[:500]
    ac_text = str(context.get("ac_text") or context.get("user_context") or "")[:500]
    console_logs = context.get("console_logs") or []
    backend_logs = context.get("backend_logs") or []
    html_excerpt = str(context.get("html_excerpt") or "")[:3000]

    cons_str = "\n".join(
        f"  [{(l.get('level') or 'log').upper()}] {(l.get('message') or '')[:200]}"
        for l in (console_logs or [])[:30]
        if isinstance(l, dict)
    ) or "(none)"
    be_str = "\n".join(
        f"  [{(l.get('level') or 'info').upper()}] {(l.get('message') or '')[:200]}"
        for l in (backend_logs or [])[:30]
        if isinstance(l, dict)
    ) or "(none)"

    prompt = (
        "بر اساس اطلاعات زیر، یک توصیف کوتاه (۲-۴ جمله) بنویس از این که در این لحظه "
        "احتمالاً روی صفحهٔ کاربر چه چیزی دیده می‌شود و آیا خطایی به‌نظر می‌رسد یا نه. "
        "خروجی فقط متن آزاد (نه JSON).\n\n"
        f"URL صفحه: {url}\n"
        f"AC مرجع: {ac_text}\n\n"
        f"Console logs:\n{cons_str}\n\n"
        f"Backend logs:\n{be_str}\n\n"
        f"HTML excerpt (شاید کوتاه‌شده):\n{html_excerpt[:1500]}"
    )

    try:
        mgr = get_ai_manager()
        resp = await mgr.generate(
            model_id=verify_model_id,
            messages=[Message(role="user", content=prompt)],
            max_tokens=600,
            temperature=0.2,
            allow_fallback=True,
        )
        desc = (resp.content or "").strip()
        if not desc:
            return None
        return {
            "description": desc[:2000],
            "ui_elements": "",
            "error_signals": "",
            "ocr_text": "",
            "layout_hints": "",
            # text-only fallback نمی‌تواند feature_present بصری بدهد
            "feature_present": "unclear",
            "feature_reason": "",
            "source": f"fallback_text_only_{verify_model_id}",
            "raw": None,
        }
    except Exception as e:
        logger.debug(f"vision_helper: text fallback failed: {e}")
        return None


def _none_result(reason: str) -> Dict[str, Any]:
    return {
        "description": "",
        "ui_elements": "",
        "error_signals": "",
        "ocr_text": "",
        "layout_hints": "",
        "feature_present": "unclear",
        "feature_reason": "",
        "source": "none",
        "raw": {"reason": reason},
    }
