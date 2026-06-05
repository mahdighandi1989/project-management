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
        # 🆕 (Phase 4 fix) — html_excerpt را برای keyword-overlap از DOM
        # واقعی (نه از OCR vision که قابل fake است) به bridge بدهیم
        html_excerpt = str(context.get("html_excerpt") or "")[:8000]
        result = await describe_screenshot_with_vision(
            b64, user_ctx, page_url, dom_text=html_excerpt,
        )
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


# ---------------------------------------------------------------------------
# 🆕 (Phase 3) — Before/After screenshot pair analysis
# ---------------------------------------------------------------------------

async def analyze_screenshot_pair(
    before_path: str,
    after_path: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """آنالیز یک جفت screenshot قبل/بعد از interaction.

    دو تصویر را همزمان به multimodal model می‌فرستد و می‌پرسد:
    «قبل از تعامل، صفحه X بود. بعد از تعامل، Y شد. آیا تعامل کار کرد
    و feature واقعاً عمل کرد؟»

    اگر vision در دسترس نباشد → source="none" + توصیف‌های خالی.

    Returns:
      {
        "before_description": str,
        "after_description": str,
        "diff_description": str,
        "interaction_succeeded": "yes" | "no" | "unclear",
        "feature_present": "yes" | "no" | "unclear",
        "source": str,
        "raw": dict | None,
      }
    """
    none_pair = {
        "before_description": "",
        "after_description": "",
        "diff_description": "",
        "interaction_succeeded": "unclear",
        "feature_present": "unclear",
        "source": "none",
        "raw": None,
    }
    try:
        from pathlib import Path as _Path
        bp = _Path(before_path)
        ap = _Path(after_path)
        if not bp.is_file() or not ap.is_file():
            return none_pair
        with bp.open("rb") as f:
            b64_before = base64.b64encode(f.read()).decode("ascii")
        with ap.open("rb") as f:
            b64_after = base64.b64encode(f.read()).decode("ascii")
    except Exception as e:
        logger.debug(f"vision_helper pair: file read failed: {e}")
        return none_pair

    # تلاش vision multimodal (با ۲ تصویر)
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
        from ...core.models_registry import get_vision_models
        import os as _os
    except Exception as e:
        logger.debug(f"vision_helper pair: imports failed: {e}")
        return none_pair

    try:
        vision_models = get_vision_models() or []
        env_keys = {
            "openai": ["OPENAI_API_KEY"],
            "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            # 🆕 cloud_code: vision via OAuth image content blocks
            "cloud_code": ["CLAUDE_CODE_OAUTH_TOKEN"],
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
            return none_pair
    except Exception as e:
        logger.debug(f"vision_helper pair: model pick failed: {e}")
        return none_pair

    ac_text = str(context.get("ac_text") or "")[:500]
    actions = context.get("actions_taken") or []
    actions_summary = "\n".join(
        f"  - {a.get('action', '')}: {a.get('message', '')[:80]}"
        for a in (actions or [])[:10]
        if isinstance(a, dict)
    ) or "(none)"

    prompt = (
        "دو screenshot به ترتیب می‌بینی: «قبل» و «بعد» از یک سری تعامل\n"
        "روی صفحه. وظیفه‌ات:\n\n"
        "1) توصیف قبل: scene فعلی\n"
        "2) توصیف بعد: scene تغییر یافته\n"
        "3) diff_description: چه تغییری ظاهر شد؟ (یک جمله)\n"
        "4) interaction_succeeded: آیا interaction واقعاً کار کرد؟\n"
        "   - yes: تغییر مرئی رخ داد (modal باز شد، فرم submit شد، …)\n"
        "   - no: هیچ تغییری نبود یا error ظاهر شد\n"
        "   - unclear: نمی‌توان از مقایسه قطعی گفت\n"
        "5) feature_present: آیا ویژگی AC در نهایت روی صفحه دیده می‌شود؟\n\n"
        f"📋 ویژگی AC مورد بررسی:\n{ac_text}\n\n"
        f"🎬 اقدامات انجام‌شده بین «قبل» و «بعد»:\n{actions_summary}\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "before_description": "...",\n'
        '  "after_description": "...",\n'
        '  "diff_description": "...",\n'
        '  "interaction_succeeded": "yes|no|unclear",\n'
        '  "feature_present": "yes|no|unclear"\n'
        "}"
    )

    try:
        ai_mgr = get_ai_manager()
        msg = Message(
            role="user",
            content=prompt,
            images=[b64_before, b64_after],
        )
        resp = await ai_mgr.generate(
            model_id=picked.id,
            messages=[msg],
            max_tokens=2000,
            temperature=0.2,
        )
        txt = (resp.content or "").strip()
        if txt.startswith("```"):
            txt = txt.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start = txt.find("{")
        end = txt.rfind("}")
        if start == -1 or end <= start:
            return none_pair
        try:
            import json as _json
            parsed = _json.loads(txt[start:end + 1])
        except Exception as je:
            logger.debug(f"vision_helper pair: JSON parse failed: {je}")
            return none_pair

        def _norm_verdict(v: Any) -> str:
            s = str(v or "unclear").strip().lower()
            return s if s in ("yes", "no", "unclear") else "unclear"

        return {
            "before_description": str(parsed.get("before_description") or "")[:2000],
            "after_description": str(parsed.get("after_description") or "")[:2000],
            "diff_description": str(parsed.get("diff_description") or "")[:1500],
            "interaction_succeeded": _norm_verdict(parsed.get("interaction_succeeded")),
            "feature_present": _norm_verdict(parsed.get("feature_present")),
            "source": f"vision_pair_{picked.id}",
            "raw": parsed,
        }
    except Exception as e:
        logger.debug(f"vision_helper pair: call failed: {e}")
        return none_pair


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
