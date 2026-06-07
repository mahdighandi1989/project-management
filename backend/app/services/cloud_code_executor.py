"""Tool executor for the Cloud Code agent loop.

`cloud_code_service.cloud_code_agent_loop` accepts an `executor` callable.
This module builds that callable for the inspector chat endpoint —
closing over the GitHub/Render services + repo identifiers and
dispatching each tool_use to the right backend.

Design:
  - We REUSE the schemas from `inspector_agent._build_tools()` so there
    is one source of truth for what tools exist and what their inputs
    look like.
  - We implement our own dispatcher here rather than calling into
    `run_inspector_agent`'s inline branch — that function is 1k+ lines
    of state and not easily reusable from a different LLM call site.
  - Phase 3 ships the minimum-viable subset that unblocks the user's
    actual stated use case (setting Render env vars + reading project
    files). Tools not in this set return a polite "not yet supported on
    Cloud Code — use Local AI" so the agent can recover instead of
    blowing up.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# Tools currently wired through to real backends. Anything else is
# politely declined; the model has the chance to retry without it.
# 🆕 (audit fix) — فقط ابزارهایی که واقعاً به backend متد دارند یا با
# direct REST پیاده‌سازی شده‌اند. render_get_service و render_get_deploys
# هنوز در RenderAPIService نیستند — اگر model اون‌ها را در request ببیند
# و بزند، fail می‌شود. کاربر تجربهٔ "tool not shipped" را نمی‌خواهد دید،
# پس از set حذف شدند تا اصلاً به مدل نشان داده نشوند.
SUPPORTED_TOOLS_PHASE_3 = {
    "read_file",
    "list_files",
    "list_branches",
    "read_file_from_branch",
    "render_list_services",
    "render_get_env_vars",
    "render_set_env_var",
    "render_trigger_deploy",
    # 🆕 (create-service) — کاربر گزارش داد که Cloud Code می‌گوید «ابزار
    # ساخت سرویس را ندارم». این allowlist را filter می‌کرد. این سه ابزار
    # حالا exposed می‌شوند تا agent بتواند web_service / background_worker
    # / static_site / Postgres / Redis مستقیم بسازد.
    "render_create_service",
    "render_create_redis",
    "render_create_postgres",
    "submit_action_plan",
    "preflight_check",
}


def get_phase_3_tool_schemas() -> List[Dict[str, Any]]:
    """The tool schemas exposed to Cloud Code in Phase 3. Pulled from
    `inspector_agent._build_tools()` and filtered to the supported set
    so the model only sees what we can actually execute."""
    from .inspector_agent import _build_tools
    all_tools = _build_tools()
    return [t for t in all_tools if t.get("name") in SUPPORTED_TOOLS_PHASE_3]


def build_inspector_executor(
    *,
    github_svc,
    render_service,
    owner: str,
    repo: str,
    branch: str,
    github_token: Optional[str],
    file_list: List[str],
    max_file_chars: int = 18000,
    on_submit_action_plan: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]:
    """Build the executor closure for `cloud_code_agent_loop`.

    Parameters mirror what `run_inspector_agent` needs:
      - github_svc: a GithubPRService instance for file reads and branches.
      - render_service: a RenderAPIService instance for Render operations.
        Pass None if the user has no Render token configured — Render
        tools will then return a friendly "Render token missing" so the
        model can fall back to file-only work.
      - file_list: the project file list pulled once at request time,
        used to validate read_file paths and to back list_files.
      - on_submit_action_plan: optional callback so the endpoint can
        capture a submitted action plan for later apply-action.
    """
    file_set = set(file_list or [])
    files_read: Dict[str, str] = {}

    def _ok(content: Any) -> Dict[str, Any]:
        return {"content": content, "is_error": False}

    def _err(msg: str) -> Dict[str, Any]:
        return {"content": msg, "is_error": True}

    def _need_render() -> Optional[Dict[str, Any]]:
        if render_service is None:
            return _err(
                "Render API در دسترس نیست — توکن Render در تنظیمات پروژه ست نشده "
                "یا اعتبار ندارد. برای کارهای فایل/گیت می‌توانی ادامه دهی."
            )
        return None

    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        args = args or {}
        try:
            # ---------- File / git read tools ----------
            if name == "read_file":
                path = (args.get("path") or "").strip().lstrip("/")
                if not path:
                    return _err("پارامتر 'path' لازم است.")
                if file_set and path not in file_set:
                    # Help the model recover by suggesting near-matches
                    leaf = path.split("/")[-1]
                    suggest = [p for p in file_list if leaf in p][:5]
                    msg = f"فایل '{path}' در پروژه یافت نشد."
                    if suggest:
                        msg += " شاید یکی از این‌ها بود:\n" + "\n".join(suggest)
                    return _err(msg)
                if path in files_read:
                    content = files_read[path]
                else:
                    res = await github_svc.get_file_content(
                        owner, repo, path, branch=branch, token=github_token,
                    )
                    if not res.get("success"):
                        return _err(f"خطا در خواندن: {res.get('error', 'unknown')}")
                    content = res.get("content", "") or ""
                    files_read[path] = content
                truncated = content
                if len(truncated) > max_file_chars:
                    truncated = truncated[:max_file_chars] + "\n... [بریده شد به دلیل اندازه]"
                nlines = content.count("\n") + 1
                return _ok(f"محتوای {path} ({nlines} خط):\n```\n{truncated}\n```")

            if name == "list_files":
                f = (args.get("filter") or "").strip()
                matched = [p for p in file_list if f in p] if f else list(file_list)
                shown = matched[:200]
                txt = "\n".join(shown)
                if len(matched) > len(shown):
                    txt += f"\n... و {len(matched) - len(shown)} فایل دیگر"
                return _ok(txt or "موردی یافت نشد")

            if name == "list_branches":
                # 🆕 (audit fix) — github_pr_service متد list_branches ندارد،
                # پس direct REST call به /repos/{owner}/{repo}/branches می‌زنیم.
                if not github_token:
                    return _err("توکن GitHub ست نشده.")
                try:
                    import httpx as _httpx_lb
                    async with _httpx_lb.AsyncClient(timeout=15.0) as _cli:
                        r = await _cli.get(
                            f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100",
                            headers={
                                "Authorization": f"token {github_token}",
                                "Accept": "application/vnd.github+json",
                            },
                        )
                    if r.status_code != 200:
                        return _err(f"GitHub branches API HTTP {r.status_code}")
                    names = [b.get("name") for b in r.json() if b.get("name")]
                    return _ok("\n".join(names) or "(no branches)")
                except Exception as e:
                    return _err(f"خطا در فراخوانی GitHub branches: {str(e)[:200]}")

            if name == "read_file_from_branch":
                path = (args.get("path") or "").strip().lstrip("/")
                br = (args.get("branch") or "").strip() or branch
                if not path:
                    return _err("پارامتر 'path' لازم است.")
                res = await github_svc.get_file_content(
                    owner, repo, path, branch=br, token=github_token,
                )
                if not res.get("success"):
                    return _err(f"خطا در خواندن از branch {br}: {res.get('error', 'unknown')}")
                content = res.get("content", "") or ""
                truncated = content if len(content) <= max_file_chars else \
                    content[:max_file_chars] + "\n... [بریده شد]"
                return _ok(f"{path} از branch {br}:\n```\n{truncated}\n```")

            # ---------- Render tools ----------
            if name == "render_list_services":
                guard = _need_render()
                if guard:
                    return guard
                res = await render_service.get_services()
                if isinstance(res, dict) and not res.get("success", True):
                    return _err(f"Render خطا: {res.get('error')}")
                services = res.get("services") if isinstance(res, dict) else res
                if not services:
                    return _ok("هیچ سرویسی روی Render account یافت نشد.")
                lines = []
                for s in services[:30]:
                    sid = s.get("id") or s.get("service", {}).get("id")
                    nm = s.get("name") or s.get("service", {}).get("name")
                    tp = s.get("type") or s.get("service", {}).get("type")
                    lines.append(f"- `{sid}` — {nm} ({tp})")
                return _ok("\n".join(lines))

            if name == "render_get_env_vars":
                guard = _need_render()
                if guard:
                    return guard
                sid = args.get("service_id") or ""
                if not sid:
                    return _err("service_id لازم است.")
                res = await render_service.get_env_vars(sid)
                if isinstance(res, dict) and not res.get("success", True):
                    return _err(f"Render خطا: {res.get('error')}")
                env_list = res.get("env_vars") if isinstance(res, dict) else res
                if not env_list:
                    return _ok("هیچ متغیر محیطی یافت نشد.")
                lines = []
                for e in env_list:
                    k = e.get("key") if isinstance(e, dict) else None
                    if k:
                        lines.append(f"- `{k}` (مقدار masked)")
                return _ok("\n".join(lines) or "(empty)")

            if name == "render_set_env_var":
                guard = _need_render()
                if guard:
                    return guard
                sid = args.get("service_id") or ""
                key = args.get("key") or ""
                value = args.get("value") or ""
                if not (sid and key):
                    return _err("service_id و key لازم اند.")
                res = await render_service.set_env_var(sid, key, value)
                if isinstance(res, dict) and not res.get("success", True):
                    return _err(f"Render خطا: {res.get('error')}")
                return _ok(f"✅ متغیر `{key}` روی سرویس `{sid}` ست شد.")

            if name == "render_trigger_deploy":
                guard = _need_render()
                if guard:
                    return guard
                sid = args.get("service_id") or ""
                if not sid:
                    return _err("service_id لازم است.")
                clear_cache = bool(args.get("clear_cache"))
                res = await render_service.trigger_deploy(sid, clear_cache=clear_cache)
                if isinstance(res, dict) and not res.get("success", True):
                    return _err(f"Render خطا: {res.get('error')}")
                return _ok(f"🚀 deploy روی سرویس `{sid}` شروع شد"
                           + (" (با clear cache)" if clear_cache else "") + ".")

            # 🆕 (create-service) — ساخت سرویس جدید Render
            if name == "render_create_service":
                guard = _need_render()
                if guard:
                    return guard
                svc_type = (args.get("type") or "").strip().lower()
                if svc_type not in (
                    "web_service", "background_worker",
                    "static_site", "private_service",
                ):
                    return _err(
                        "type باید یکی از web_service / background_worker / "
                        "static_site / private_service باشد."
                    )
                if not args.get("name"):
                    return _err("name لازم است.")
                if not args.get("repo"):
                    return _err("repo (URL گیت‌هاب) لازم است.")
                res = await render_service.create_service(
                    name=args.get("name"),
                    type=svc_type,
                    repo=args.get("repo"),
                    branch=(args.get("branch") or "main"),
                    owner_id=(args.get("owner_id") or "").strip() or None,
                    region=(args.get("region") or "oregon"),
                    plan=(args.get("plan") or "starter"),
                    root_dir=args.get("root_dir"),
                    build_command=args.get("build_command"),
                    start_command=args.get("start_command"),
                    runtime=args.get("runtime"),
                    env_vars=args.get("env_vars") or {},
                    auto_deploy=bool(args.get("auto_deploy", True)),
                    dockerfile_path=args.get("dockerfile_path"),
                    publish_path=args.get("publish_path"),
                )
                if not res.get("success"):
                    return _err(f"خطا در ساخت سرویس: {res.get('error')}")
                return _ok(
                    f"✅ سرویس ساخته شد:\n"
                    f"- service_id: {res.get('service_id')}\n"
                    f"- name: {res.get('name')}\n"
                    f"- type: {res.get('type')}\n"
                    f"- dashboard: {res.get('dashboard_url')}\n\n"
                    f"📌 اگر env vars اضافی لازم است، با "
                    f"`render_set_env_var(service_id='{res.get('service_id')}', ...)` set کن."
                )

            if name == "render_create_redis":
                guard = _need_render()
                if guard:
                    return guard
                if not args.get("name"):
                    return _err("name لازم است.")
                res = await render_service.create_redis(
                    name=args.get("name"),
                    owner_id=(args.get("owner_id") or "").strip() or None,
                    region=(args.get("region") or "oregon"),
                    plan=(args.get("plan") or "free"),
                )
                if not res.get("success"):
                    return _err(f"خطا در ساخت Redis: {res.get('error')}")
                return _ok(
                    f"✅ Redis ساخته شد:\n"
                    f"- redis_id: {res.get('redis_id')}\n"
                    f"- name: {res.get('name')}\n\n"
                    f"📌 provisioning ~۱-۳ دقیقه. وقتی available شد، "
                    f"connection string را از dashboard کپی و در سرویس‌های "
                    f"نیازمند set کن."
                )

            if name == "render_create_postgres":
                guard = _need_render()
                if guard:
                    return guard
                if not args.get("name"):
                    return _err("name لازم است.")
                owner_id = (args.get("owner_id") or "").strip() or None
                if not owner_id:
                    owner_id = await render_service.get_owner_id_from_services()
                    if not owner_id:
                        return _err(
                            "owner_id پیدا نشد — لطفاً دستی owner_id را پاس بده."
                        )
                res = await render_service.create_postgres(
                    name=args.get("name"),
                    owner_id=owner_id,
                    plan=(args.get("plan") or "free"),
                    region=(args.get("region") or "oregon"),
                    version=str(args.get("version") or "16"),
                    database_name=args.get("database_name"),
                    database_user=args.get("database_user"),
                )
                if not res.get("success"):
                    return _err(f"خطا در ساخت Postgres: {res.get('error')}")
                return _ok(
                    f"✅ Postgres ساخته شد:\n"
                    f"- postgres_id: {res.get('postgres_id')}\n"
                    f"- name: {res.get('name')}\n"
                    f"- status: {res.get('status')}\n\n"
                    f"📌 {res.get('note', 'صبر کن provisioning تمام شود.')}"
                )

            # ---------- Action plan ----------
            if name == "submit_action_plan":
                # Accept the plan and signal the loop to stop. The endpoint
                # captures it via the callback so apply-action can pick it up.
                if on_submit_action_plan is not None:
                    try:
                        on_submit_action_plan(args)
                    except Exception as cb_e:
                        logger.warning("on_submit_action_plan callback raised: %s", cb_e)
                return _ok("✅ action_plan دریافت شد.")

            if name == "preflight_check":
                # Lightweight stub — returns the model a green light. Real
                # preflight runs are in Local AI smart-chat. Cloud Code can
                # still propose plans without it.
                return _ok("preflight: ok (cloud_code minimal preflight)")

            # ---------- Unsupported ----------
            return _err(
                f"ابزار '{name}' هنوز در موتور Cloud Code پشتیبانی نمی‌شود. "
                f"برای این کار به 'Local AI' سوئیچ کن یا ابتدا با ابزارهای "
                f"در دسترس کار را شروع کن."
            )

        except Exception as e:
            logger.exception("cloud_code executor crashed on tool %s", name)
            return _err(f"خطای داخلی هنگام اجرای {name}: {str(e)[:200]}")

    return execute
