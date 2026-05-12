"""Auto-detect Render service URLs for a watched repo.

اگر `RENDER_API_KEY` تنظیم شده باشد، می‌توانیم سرویس‌های Render را
list کنیم و آن‌هایی که به یک repo خاص متصل هستند را پیدا کنیم. بر اساس
type (web_service / static_site)، frontend و backend URL را تشخیص می‌دهیم.

این ماژول هیچ exception ای بیرون نمی‌اندازد — اگر API key نباشد یا
Render شکست بخورد، خروجی dict خالی است.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _normalize_repo_url(s: str) -> str:
    """`https://github.com/owner/repo.git` → `owner/repo` (lowercase)."""
    if not s:
        return ""
    s = s.strip().lower()
    s = s.removesuffix(".git")
    if "github.com" in s:
        # take everything after the host
        parts = s.split("github.com", 1)[-1].lstrip(":/").split("/", 2)
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    if "/" in s and not s.startswith("http"):
        # already owner/repo
        return s
    return s


def _service_repo_full_name(svc: Dict[str, Any]) -> str:
    """از یک Render service dict، repo_full_name (owner/repo) را استخراج کن."""
    # ساختار Render API می‌تواند {service: {...}} باشد یا flat
    s = svc.get("service") if isinstance(svc.get("service"), dict) else svc
    if not isinstance(s, dict):
        return ""
    # repo URL در محل‌های مختلف
    repo_url = (
        s.get("repo")
        or (s.get("serviceDetails", {}) or {}).get("repo")
        or ""
    )
    return _normalize_repo_url(str(repo_url))


def _service_url(svc: Dict[str, Any]) -> Optional[str]:
    """URL عمومی سرویس Render (https://...) را برمی‌گرداند."""
    s = svc.get("service") if isinstance(svc.get("service"), dict) else svc
    if not isinstance(s, dict):
        return None
    # web service: serviceDetails.url
    sd = s.get("serviceDetails") or {}
    if isinstance(sd, dict):
        url = sd.get("url") or sd.get("publicUrl")
        if url:
            return str(url).rstrip("/")
    # static site: rootDir? No — static sites have same url field
    url = s.get("url") or s.get("publicUrl") or s.get("serviceUrl")
    if url:
        return str(url).rstrip("/")
    return None


def _service_type(svc: Dict[str, Any]) -> str:
    """نوع سرویس Render: 'web_service', 'static_site', 'background_worker', ..."""
    s = svc.get("service") if isinstance(svc.get("service"), dict) else svc
    if not isinstance(s, dict):
        return ""
    return str(s.get("type") or s.get("serviceDetails", {}).get("env") or "").lower()


async def detect_render_urls_for_repo(
    repo_full_name: str,
) -> Dict[str, Any]:
    """برای یک repo (owner/repo)، URL های frontend و backend را از Render
    استخراج می‌کند.

    خروجی:
      {
        "frontend_base_url": "https://...",  # یا None
        "backend_base_url": "https://...",   # یا None
        "matched_services": [{name, type, url}, ...],
        "source": "render_api" | "not_configured" | "error",
        "error": "..."  # فقط اگر source=error
      }

    منطق ساده:
    - سرویس‌های type=static_site یا env=static → frontend
    - سرویس‌های type=web_service → backend
    - اگر دو web_service پیدا شد، اولی backend می‌گیریم (heuristic)
    - اگر دو static_site پیدا شد، اولی frontend
    """
    out: Dict[str, Any] = {
        "frontend_base_url": None,
        "backend_base_url": None,
        "matched_services": [],
        "source": "not_configured",
    }
    if not os.environ.get("RENDER_API_KEY", "").strip():
        return out

    try:
        from ..deploy_service import RenderDeployService
    except Exception as e:
        out["source"] = "error"
        out["error"] = f"import RenderDeployService: {e}"
        return out

    target = _normalize_repo_url(repo_full_name)
    if not target:
        out["source"] = "error"
        out["error"] = "repo_full_name نامعتبر"
        return out

    svc_client = RenderDeployService()
    try:
        services = await svc_client.list_services()
    except Exception as e:
        out["source"] = "error"
        out["error"] = f"list_services: {e}"
        return out
    finally:
        try:
            await svc_client.close()
        except Exception:
            pass

    if not services:
        out["source"] = "render_api"
        return out

    matched: List[Dict[str, Any]] = []
    frontend_candidates: List[str] = []
    backend_candidates: List[str] = []
    for svc in services:
        repo_norm = _service_repo_full_name(svc)
        if repo_norm != target:
            continue
        url = _service_url(svc)
        if not url:
            continue
        stype = _service_type(svc)
        s_inner = svc.get("service") if isinstance(svc.get("service"), dict) else svc
        name = (s_inner.get("name") or "") if isinstance(s_inner, dict) else ""
        matched.append({"name": name, "type": stype, "url": url})
        # heuristic frontend vs backend
        if "static" in stype:
            frontend_candidates.append(url)
        elif "web" in stype:
            # تشخیص با اسم: اگر "frontend"/"front"/"web"/"ui" داشت → frontend
            lower_name = name.lower()
            if any(k in lower_name for k in ("frontend", "front", "ui", "web-ui")):
                frontend_candidates.append(url)
            else:
                backend_candidates.append(url)
        else:
            backend_candidates.append(url)

    if frontend_candidates:
        out["frontend_base_url"] = frontend_candidates[0]
    if backend_candidates:
        out["backend_base_url"] = backend_candidates[0]
    # اگر فقط یک URL پیدا شد و نتوانستیم تشخیص دهیم، آن را backend بگذاریم
    if not out["frontend_base_url"] and not out["backend_base_url"] and matched:
        out["backend_base_url"] = matched[0]["url"]
    out["matched_services"] = matched
    out["source"] = "render_api"
    return out


def detect_repo_url(repo_full_name: str) -> str:
    """clone URL یک repo را برمی‌گرداند (بدون نیاز به API call).

    اگر GITHUB_TOKEN هست، authenticated URL را ترجیح بده.
    """
    if not repo_full_name or "/" not in repo_full_name:
        return ""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return f"https://{token}@github.com/{repo_full_name}.git"
    return f"https://github.com/{repo_full_name}.git"
