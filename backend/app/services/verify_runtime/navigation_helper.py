"""Phase 4 — Smart Navigation Helper.

برای AC هایی که اشاره صریح به `/path` ندارند و keyword matching هم
نتوانست route را پیدا کند، این helper:

1. nav menu صفحه home را با Playwright می‌خواند (لینک‌های nav/header/aside)
2. AI تصمیم می‌گیرد کدام لینک به feature این AC مرتبط است
3. اگر confidence بالا بود → لینک را return می‌کند تا probe روی آن کلیک کند

API: pick_nav_link_for_ac(ac_text, links, verify_model_id)
     extract_nav_links_from_page(page)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# محدودیت‌ها
_MAX_LINKS_CONSIDERED = 30
_AI_TIMEOUT_S = 15


async def extract_nav_links_from_page(page: Any) -> List[Dict[str, str]]:
    """لینک‌های nav menu را از صفحه استخراج کن.

    selectorها سعی می‌کنند به متداول‌ترین مکان‌های nav دسترسی پیدا کنند:
    nav, [role=navigation], header, aside, .sidebar, .menu, [data-testid*=nav]

    خروجی: لیست dict های {text, href}
    """
    try:
        # selector یک locator combined
        nav_selector = (
            'nav a, [role="navigation"] a, header a, aside a, '
            '.sidebar a, .menu a, [data-testid*="nav"] a, '
            '[class*="navbar"] a, [class*="sidebar"] a, [class*="menu"] a'
        )
        # همه‌ی locator ها را بگیر
        locator = page.locator(nav_selector)
        count = await locator.count()
        out: List[Dict[str, str]] = []
        seen_hrefs: set = set()
        for i in range(min(count, _MAX_LINKS_CONSIDERED * 2)):
            try:
                el = locator.nth(i)
                text = (await el.text_content() or "").strip()
                href = await el.get_attribute("href") or ""
                if not text or not href:
                    continue
                # filter بیرونی‌ها و mailto/tel/anchors
                if href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                    # absolute http می‌تواند به همان host بازگردد
                    if href.startswith(("mailto:", "tel:", "#")):
                        continue
                # dedup
                if href in seen_hrefs:
                    continue
                seen_hrefs.add(href)
                # truncate text
                out.append({"text": text[:80], "href": href[:200]})
                if len(out) >= _MAX_LINKS_CONSIDERED:
                    break
            except Exception:
                continue
        return out
    except Exception as e:
        logger.debug(f"navigation_helper: extract_nav_links failed: {e}")
        return []


async def pick_nav_link_for_ac(
    ac_text: str,
    links: List[Dict[str, str]],
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """AI انتخاب می‌کند کدام لینک به AC مرتبط است.

    Returns:
      {
        "chosen_idx": int یا None,
        "chosen_text": str یا None,
        "chosen_href": str یا None,
        "confidence": "high" | "medium" | "low" | "none",
        "reason": str,
      }
    """
    default_none = {
        "chosen_idx": None, "chosen_text": None, "chosen_href": None,
        "confidence": "none",
        "reason": "no links available or AI unavailable",
    }

    if not links:
        return default_none
    if not ac_text or not ac_text.strip():
        return default_none

    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception:
        return default_none

    if not verify_model_id:
        try:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            pass
    if not verify_model_id:
        return default_none

    links_block = "\n".join(
        f"{i}. text=\"{l.get('text', '')}\" href=\"{l.get('href', '')}\""
        for i, l in enumerate(links[:_MAX_LINKS_CONSIDERED])
    )

    prompt = (
        "تو در حال بررسی یک پروژه نرم‌افزاری هستی. یک ویژگی (AC) تعریف شده،\n"
        "و باید از لینک‌های منوی ناوبری انتخاب کنی کدام یکی احتمالاً به\n"
        "صفحه‌ی این ویژگی می‌رود.\n\n"
        f"📋 AC: {ac_text[:500]}\n\n"
        f"📍 لینک‌های nav menu موجود:\n{links_block}\n\n"
        "⚠️ راهنما:\n"
        "- فقط لینکی را انتخاب کن که با احتمال بالا به صفحه‌ی feature این\n"
        "  AC می‌رود (نه شباهت ظاهری اسم).\n"
        "- اگر متن AC از یک «صفحه» یا «پنل» خاص حرف می‌زند و لینکی با همان\n"
        "  نام دیدی، confidence=high.\n"
        "- اگر کلی‌ست و شاید چند کاندیدا دارد، یکی را با confidence=medium\n"
        "  انتخاب کن.\n"
        "- اگر مطمئن نیستی یا هیچ لینکی مرتبط نیست، confidence=none.\n"
        "- ⛔ نگذار AC متن تو را گیج کند که در منو نیست — اگر نیست، none.\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "chosen_idx": int یا null,\n'
        '  "chosen_text": str یا null,\n'
        '  "chosen_href": str یا null,\n'
        '  "confidence": "high|medium|low|none",\n'
        '  "reason": "یک جمله توضیح"\n'
        "}"
    )

    try:
        mgr = get_ai_manager()
        resp = await asyncio.wait_for(
            mgr.generate(
                model_id=verify_model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=600,
                temperature=0.1,
                allow_fallback=True,
            ),
            timeout=_AI_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
    except asyncio.TimeoutError:
        return {**default_none, "reason": "AI timeout"}
    except Exception as e:
        logger.warning(f"navigation_helper AI failed: {e}")
        return {**default_none, "reason": f"AI error: {str(e)[:100]}"}

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return {**default_none, "reason": "AI returned non-JSON"}
    try:
        data = json.loads(raw[start:end + 1])
    except Exception:
        return {**default_none, "reason": "AI JSON parse failed"}

    # normalize
    chosen_idx_raw = data.get("chosen_idx")
    chosen_idx: Optional[int] = None
    if isinstance(chosen_idx_raw, int) and 0 <= chosen_idx_raw < len(links):
        chosen_idx = chosen_idx_raw
    confidence = str(data.get("confidence") or "none").strip().lower()
    if confidence not in ("high", "medium", "low", "none"):
        confidence = "none"
    reason = str(data.get("reason") or "")[:400]

    # اگر confidence none یا idx ندارد → return none
    if confidence == "none" or chosen_idx is None:
        return {
            "chosen_idx": None, "chosen_text": None, "chosen_href": None,
            "confidence": "none", "reason": reason or "no match",
        }

    return {
        "chosen_idx": chosen_idx,
        "chosen_text": links[chosen_idx].get("text"),
        "chosen_href": links[chosen_idx].get("href"),
        "confidence": confidence,
        "reason": reason,
    }


async def try_smart_navigation_for_step(
    ac_text: str,
    base_url: str,
    storage_state: Optional[Dict[str, Any]] = None,
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """تابع high-level — برای orchestration: یک browser session سبک باز
    می‌کند، nav menu را می‌خواند، AI لینک مرتبط را انتخاب می‌کند.

    Returns:
      {
        "href": str یا None,        # href انتخاب‌شده (مرتبط)
        "confidence": str,
        "reason": str,
        "links_count": int,
        "duration_ms": int,
      }
    """
    import time as _time_lc
    start = _time_lc.monotonic()
    result_none = {
        "href": None, "confidence": "none",
        "reason": "smart navigation unavailable", "links_count": 0,
        "duration_ms": 0,
    }

    if not base_url:
        return result_none

    try:
        from .browser_pool import get_browser_pool
    except Exception as e:
        return {**result_none, "reason": f"browser_pool import failed: {e}"}

    pool = get_browser_pool()
    browser = await pool.get_browser()
    if browser is None:
        return {**result_none, "reason": "browser unavailable"}

    context = None
    try:
        _ctx_kwargs: Dict[str, Any] = {"viewport": {"width": 1280, "height": 800}}
        if isinstance(storage_state, dict) and storage_state:
            _ctx_kwargs["storage_state"] = storage_state
        context = await browser.new_context(**_ctx_kwargs)
        page = await context.new_page()
        page.set_default_timeout(15000)
        # navigate به home
        try:
            await asyncio.wait_for(
                page.goto(
                    base_url, wait_until="domcontentloaded", timeout=10000,
                ),
                timeout=15,
            )
        except Exception as e:
            return {
                **result_none,
                "reason": f"home navigate failed: {str(e)[:100]}",
                "duration_ms": int((_time_lc.monotonic() - start) * 1000),
            }
        # کمی صبر برای SPA render
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass

        # extract nav links
        links = await extract_nav_links_from_page(page)
        if not links:
            return {
                **result_none, "reason": "no nav links found",
                "links_count": 0,
                "duration_ms": int((_time_lc.monotonic() - start) * 1000),
            }

        # AI link picker
        pick = await pick_nav_link_for_ac(
            ac_text=ac_text, links=links,
            verify_model_id=verify_model_id,
        )

        confidence = pick.get("confidence", "none")
        # فقط high/medium قابل قبول است
        if confidence not in ("high", "medium"):
            return {
                "href": None, "confidence": confidence,
                "reason": pick.get("reason", "low confidence"),
                "links_count": len(links),
                "duration_ms": int((_time_lc.monotonic() - start) * 1000),
            }

        href = pick.get("chosen_href")
        if not href:
            return {
                "href": None, "confidence": confidence,
                "reason": "AI did not pick valid href",
                "links_count": len(links),
                "duration_ms": int((_time_lc.monotonic() - start) * 1000),
            }

        # absolute → relative اگر بشود
        if href.startswith(base_url):
            href = href[len(base_url):]
            if not href.startswith("/"):
                href = "/" + href

        return {
            "href": href, "confidence": confidence,
            "reason": pick.get("reason", ""),
            "links_count": len(links),
            "chosen_text": pick.get("chosen_text"),
            "duration_ms": int((_time_lc.monotonic() - start) * 1000),
        }
    except Exception as e:
        logger.warning(f"try_smart_navigation_for_step crashed: {e}")
        return {
            **result_none, "reason": f"crashed: {str(e)[:100]}",
            "duration_ms": int((_time_lc.monotonic() - start) * 1000),
        }
    finally:
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass
        pool.touch()
