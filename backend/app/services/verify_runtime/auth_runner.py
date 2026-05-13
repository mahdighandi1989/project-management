"""Phase 3 — Auth recipe executor + encrypted storage_state caching.

این ماژول قبل از هر verify run که watched.runtime_auth_recipe دارد،
یک login flow اجرا می‌کند و storage_state (cookies + localStorage)
را برای استفاده‌ی probe ها در همان run ذخیره می‌کند.

ذخیره‌سازی:
- runtime_storage_state[`encrypted_blob`] = AES-GCM encrypted JSON
- کلید مشتق از env OVERSIGHT_AUTH_KEY (یا auto-generated اگر نبود)
- بعد از session_ttl_minutes منقضی می‌شود
- بعد از ۳ شکست متوالی login، recipe موقت disable می‌شود

API اصلی:
    obtain_or_refresh_storage_state(watched, force=False) -> Optional[Dict]
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# محدودیت‌های ایمنی
_LOGIN_TIMEOUT_S = 30
_STEP_TIMEOUT_MS = 15_000  # ۱۵ ثانیه per-step
_MAX_FAILED_LOGINS = 3
_DEFAULT_TTL_MINUTES = 30

# سمافور: تنها یک login concurrent (chromium سنگین است)
_LOGIN_SEM = asyncio.Semaphore(1)


# ---------------------------------------------------------------------------
# Encryption helpers (AES-GCM)
# ---------------------------------------------------------------------------

def _get_or_create_key() -> bytes:
    """دریافت یا ایجاد کلید encryption از env.

    اولویت: env OVERSIGHT_AUTH_KEY (base64 32 byte)
    اگر نبود: یک کلید تصادفی بساز و در env فعلی ست کن (warning log).
    این کلید فقط در حافظهٔ process زنده می‌ماند تا restart بعدی.
    """
    raw = (os.environ.get("OVERSIGHT_AUTH_KEY") or "").strip()
    if raw:
        try:
            key = base64.b64decode(raw)
            if len(key) == 32:
                return key
        except Exception:
            pass
        logger.warning("OVERSIGHT_AUTH_KEY invalid — generating ephemeral key")
    # ephemeral — restart کلید را عوض می‌کند، storage_state قبلی unreadable می‌شود
    new_key = os.urandom(32)
    os.environ["OVERSIGHT_AUTH_KEY"] = base64.b64encode(new_key).decode("ascii")
    logger.warning(
        "OVERSIGHT_AUTH_KEY not set — generated ephemeral key (storage_state "
        "won't survive process restart)"
    )
    return new_key


def _encrypt_storage(data: Dict[str, Any]) -> Optional[str]:
    """AES-GCM encrypt یک dict — خروجی base64 string."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception as e:
        logger.warning(f"cryptography not available, cannot encrypt: {e}")
        return None
    try:
        key = _get_or_create_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        plain = json.dumps(data, ensure_ascii=False).encode("utf-8")
        ct = aesgcm.encrypt(nonce, plain, None)
        blob = base64.b64encode(nonce + ct).decode("ascii")
        return blob
    except Exception as e:
        logger.warning(f"encrypt_storage failed: {e}")
        return None


def _decrypt_storage(blob: str) -> Optional[Dict[str, Any]]:
    """معکوس _encrypt_storage — اگر کلید نخواند، None."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:
        return None
    try:
        key = _get_or_create_key()
        aesgcm = AESGCM(key)
        raw = base64.b64decode(blob)
        nonce, ct = raw[:12], raw[12:]
        plain = aesgcm.decrypt(nonce, ct, None)
        return json.loads(plain.decode("utf-8"))
    except Exception as e:
        logger.debug(f"decrypt_storage failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Recipe execution (Playwright)
# ---------------------------------------------------------------------------

def _resolve_value(step: Dict[str, Any]) -> str:
    """مقدار یک step را resolve کن. اولویت: value > value_env (WATCHED_AUTH_*).

    فقط env vars با prefix WATCHED_AUTH_* قابل reference هستند تا leak
    تصادفی credentials از env های دیگر اتفاق نیفتد.
    """
    if "value" in step:
        return str(step.get("value") or "")
    env_name = str(step.get("value_env") or "").strip()
    if not env_name:
        return ""
    if not env_name.startswith("WATCHED_AUTH_"):
        logger.warning(
            f"auth_runner: value_env '{env_name}' ignored — must start with "
            f"WATCHED_AUTH_*"
        )
        return ""
    return os.environ.get(env_name, "") or ""


async def _execute_login_recipe(
    recipe: Dict[str, Any],
    frontend_base_url: str,
) -> Dict[str, Any]:
    """recipe.steps را اجرا کن و storage_state بگیر.

    Returns: {
      "success": bool,
      "storage_state": Optional[Dict],  # raw dict from Playwright
      "error": Optional[str],
      "duration_ms": int,
    }
    """
    start = time.monotonic()
    result: Dict[str, Any] = {
        "success": False, "storage_state": None,
        "error": None, "duration_ms": 0,
    }

    if not recipe or not isinstance(recipe, dict):
        result["error"] = "recipe missing"
        return result
    steps = recipe.get("steps") or []
    if not isinstance(steps, list) or not steps:
        result["error"] = "recipe.steps empty"
        return result

    login_url = recipe.get("login_url") or "/login"
    if not login_url.startswith("http"):
        login_url = frontend_base_url.rstrip("/") + (
            "" if login_url.startswith("/") else "/"
        ) + login_url

    # browser pool reuse
    try:
        from .browser_pool import get_browser_pool
    except Exception as e:
        result["error"] = f"browser_pool import failed: {e}"
        return result

    pool = get_browser_pool()
    browser = await pool.get_browser()
    if browser is None:
        result["error"] = "browser unavailable"
        return result

    context = None
    page = None
    try:
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        page.set_default_timeout(_STEP_TIMEOUT_MS)

        # navigate به login_url
        await page.goto(login_url, wait_until="domcontentloaded", timeout=_STEP_TIMEOUT_MS)

        # اجرای steps
        for step_idx, step in enumerate(steps):
            action = str(step.get("action") or "").strip().lower()
            timeout = int(step.get("timeout_ms") or _STEP_TIMEOUT_MS)
            try:
                if action == "fill":
                    sel = step.get("selector") or ""
                    val = _resolve_value(step)
                    if not sel:
                        raise ValueError(f"step {step_idx}: selector required for fill")
                    await page.locator(sel).first.fill(val, timeout=timeout)
                elif action == "click":
                    sel = step.get("selector") or ""
                    if not sel:
                        raise ValueError(f"step {step_idx}: selector required for click")
                    await page.locator(sel).first.click(timeout=timeout)
                elif action == "press_key":
                    key = str(step.get("key") or "Enter")
                    await page.keyboard.press(key)
                elif action == "wait_for":
                    sel = step.get("selector") or ""
                    state = step.get("state", "visible")
                    await page.wait_for_selector(sel, timeout=timeout, state=state)
                elif action == "wait_for_url":
                    contains = step.get("contains") or ""
                    try:
                        await page.wait_for_url(f"**{contains}**", timeout=timeout)
                    except Exception:
                        deadline = time.monotonic() + (timeout / 1000.0)
                        while time.monotonic() < deadline:
                            if contains in (page.url or ""):
                                break
                            await asyncio.sleep(0.2)
                        if contains not in (page.url or ""):
                            raise
                elif action == "navigate":
                    url = step.get("url") or "/"
                    if not url.startswith("http"):
                        url = frontend_base_url.rstrip("/") + (
                            "" if url.startswith("/") else "/"
                        ) + url
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                else:
                    logger.warning(f"auth_runner: unknown action '{action}' in step {step_idx}")
                    # ادامه — sequence نباید برای action ناشناخته fail شود
                    continue
            except Exception as step_err:
                result["error"] = f"step {step_idx} ({action}) failed: {str(step_err)[:200]}"
                return result

        # چک کردن success_indicator
        success_ind = recipe.get("success_indicator") or {}
        if isinstance(success_ind, dict) and success_ind.get("selector"):
            sel = success_ind["selector"]
            must_exist = success_ind.get("must_exist", True)
            try:
                el = await page.wait_for_selector(sel, timeout=5000, state="visible")
                found = el is not None
            except Exception:
                found = False
            if must_exist and not found:
                result["error"] = f"success_indicator '{sel}' not found"
                return result

        # دریافت storage_state
        try:
            storage = await context.storage_state()
            result["storage_state"] = storage
            result["success"] = True
        except Exception as e:
            result["error"] = f"storage_state retrieval failed: {e}"
            return result

    except Exception as e:
        result["error"] = f"login flow crashed: {str(e)[:200]}"
    finally:
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass
        pool.touch()

    result["duration_ms"] = int((time.monotonic() - start) * 1000)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def obtain_or_refresh_storage_state(
    watched: Any,
    force: bool = False,
) -> Optional[Dict[str, Any]]:
    """دریافت storage_state معتبر برای watched.

    اگر cached و معتبر است → decrypt و برگردان.
    اگر منقضی یا force=True → execute recipe → encrypt → save → return.

    Returns:
      storage_state dict (قابل پاس به Playwright new_context)
      یا None اگر recipe نیست یا login شکست خورد.
    """
    if watched is None:
        return None
    recipe = getattr(watched, "runtime_auth_recipe", None)
    if not isinstance(recipe, dict) or not recipe:
        return None

    cached = getattr(watched, "runtime_storage_state", None) or {}
    if isinstance(cached, dict):
        # چک شکست‌های متوالی
        failed_count = int(cached.get("login_failed_count") or 0)
        if failed_count >= _MAX_FAILED_LOGINS and not force:
            logger.warning(
                f"auth_runner: recipe disabled for watched={getattr(watched, 'id', '?')} "
                f"after {failed_count} consecutive failures"
            )
            return None
        # چک معتبر بودن cache
        if not force and cached.get("encrypted_blob") and cached.get("expires_at"):
            try:
                exp = datetime.fromisoformat(cached["expires_at"].replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp > datetime.now(timezone.utc):
                    decoded = _decrypt_storage(cached["encrypted_blob"])
                    if decoded is not None:
                        return decoded
            except Exception as e:
                logger.debug(f"auth_runner: cached state unreadable: {e}")

    # نیاز به login تازه
    frontend_url = getattr(watched, "frontend_base_url", None)
    if not frontend_url:
        logger.warning("auth_runner: no frontend_base_url, cannot run recipe")
        return None

    async with _LOGIN_SEM:
        try:
            run_result = await asyncio.wait_for(
                _execute_login_recipe(recipe, frontend_url),
                timeout=_LOGIN_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            run_result = {
                "success": False,
                "error": f"login timeout > {_LOGIN_TIMEOUT_S}s",
                "storage_state": None,
            }
        except Exception as e:
            run_result = {
                "success": False,
                "error": f"login crashed: {str(e)[:200]}",
                "storage_state": None,
            }

    # update watched.runtime_storage_state
    if run_result.get("success") and run_result.get("storage_state"):
        encrypted = _encrypt_storage(run_result["storage_state"])
        if encrypted is None:
            logger.warning("auth_runner: encryption failed — not caching")
            return run_result["storage_state"]
        ttl_minutes = int(recipe.get("session_ttl_minutes") or _DEFAULT_TTL_MINUTES)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        ).isoformat()
        new_state = {
            "encrypted_blob": encrypted,
            "expires_at": expires_at,
            "obtained_at": datetime.now(timezone.utc).isoformat(),
            "login_failed_count": 0,
        }
        await _save_storage_state(watched, new_state)
        return run_result["storage_state"]
    else:
        # شکست — increment failed counter
        existing = getattr(watched, "runtime_storage_state", None) or {}
        new_failed = int((existing.get("login_failed_count") or 0)) + 1
        new_state = {
            "encrypted_blob": existing.get("encrypted_blob"),
            "expires_at": existing.get("expires_at"),
            "obtained_at": existing.get("obtained_at"),
            "login_failed_count": new_failed,
            "last_error": run_result.get("error"),
            "last_attempt_at": datetime.now(timezone.utc).isoformat(),
        }
        await _save_storage_state(watched, new_state)
        logger.warning(
            f"auth_runner: login failed (try #{new_failed}): {run_result.get('error')}"
        )
        return None


async def _save_storage_state(watched: Any, state: Dict[str, Any]) -> None:
    """ذخیره runtime_storage_state روی watched (با service._lock)."""
    try:
        from ..oversight_service import get_oversight_service
        service = get_oversight_service()
        async with service._lock:
            watched.runtime_storage_state = state
            try:
                watched.updated_at = datetime.now(timezone.utc).isoformat()
            except Exception:
                pass
            service._save_watched()
    except Exception as e:
        logger.debug(f"auth_runner: save_storage_state failed: {e}")


async def test_login_recipe(watched: Any) -> Dict[str, Any]:
    """endpoint helper — recipe را test کن بدون cache.

    Returns: {
      "success": bool, "duration_ms": int, "error": Optional[str],
      "success_indicator_found": bool,
    }
    """
    recipe = getattr(watched, "runtime_auth_recipe", None)
    if not isinstance(recipe, dict) or not recipe:
        return {"success": False, "error": "no recipe configured"}
    frontend_url = getattr(watched, "frontend_base_url", None)
    if not frontend_url:
        return {"success": False, "error": "no frontend_base_url"}

    async with _LOGIN_SEM:
        try:
            result = await asyncio.wait_for(
                _execute_login_recipe(recipe, frontend_url),
                timeout=_LOGIN_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            return {"success": False, "error": f"timeout > {_LOGIN_TIMEOUT_S}s"}
        except Exception as e:
            return {"success": False, "error": str(e)[:300]}

    # remove storage_state from response (sensitive)
    storage = result.pop("storage_state", None)
    result["success_indicator_found"] = bool(storage)
    return result


async def invalidate_storage_state(watched: Any) -> Dict[str, Any]:
    """force-refresh — runtime_storage_state را clear کن تا verify بعدی recipe
    را دوباره اجرا کند."""
    try:
        from ..oversight_service import get_oversight_service
        service = get_oversight_service()
        async with service._lock:
            watched.runtime_storage_state = None
            try:
                watched.updated_at = datetime.now(timezone.utc).isoformat()
            except Exception:
                pass
            service._save_watched()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
