"""
حلقهٔ عامل بازرس (Inspector Agent Loop)
=========================================

برخلاف pipeline تک‌شات قدیمی (scan → ۲۵ فایل کورکورانه → یک prompt غول →
یک پاسخ)، این ماژول یک حلقهٔ tool-calling واقعی اجرا می‌کند (مثل Claude Code):

    مدل خودش تصمیم می‌گیرد چه فایلی بخواند → محتوا را می‌بیند → تصمیم بعدی
    را می‌گیرد → … → وقتی کافی فهمید، action_plan تولید می‌کند.

این کار سه مشکل بنیادی pipeline قدیمی را حل می‌کند:
  1. دیگر ۲۵ فایل را کورکورانه نمی‌خواند و به token limit / truncate نمی‌خورد
  2. context را on-demand می‌سازد (فقط چیزی که لازم است)
  3. مدل بر اساس چیزی که یاد می‌گیرد قدم بعدی را انتخاب می‌کند (نه خط لولهٔ ثابت)

فقط با مدل‌هایی که tool-calling دارند کار می‌کند (فعلاً Claude). فراخوان باید
قبل از استفاده، پشتیبانی مدل را با supports_tool_calling() چک کند.

این تابع یک async generator است که tupleهای (event_type, payload) yield می‌کند:
  - ("progress", {...})          → پیام پیشرفت برای نمایش به کاربر
  - ("agent_result", {...})      → نتیجهٔ نهایی (content, action_plan_text, ...)
فراخوان (render_logs) این‌ها را با sse() خودش به کلاینت forward می‌کند.
"""

from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import json as _json

from .ai_base import Message
from ..core.logging_utils import StructuredLogger

slog = StructuredLogger(__name__, "INSPECTOR-AGENT")


# providerهایی که سرویس‌شان tool-calling پیاده شده است (claude/openai/deepseek/gemini).
_TOOL_CALLING_PROVIDER_PREFIXES = ("claude-", "gpt-", "deepseek-", "gemini-")

# مدل‌هایی که قطعاً tool-calling ندارند (image-generators یا مدل‌هایی که provider
# صریحاً اعلام کرده tools را نمی‌پذیرند، مثل deepseek-reasoner و sonar).
_NO_TOOL_CALLING_HINTS = (
    "dall-e", "imagen",            # image generators
    "deepseek-reasoner",           # طبق مستندات DeepSeek از tools پشتیبانی نمی‌کند
    "sonar",                       # Perplexity (سرویس‌اش هم tool-calling پیاده نشده)
)


def supports_tool_calling(model_id: str) -> bool:
    """آیا این مدل tool-calling دارد؟ (برای gate کردن استفاده از agent loop)

    بر اساس prefix provider (که سرویس‌اش پیاده شده) با استثناهای صریح برای مدل‌هایی
    که قطعاً پشتیبانی نمی‌کنند. alias ها هم از طریق registry حل می‌شوند تا "claude"
    تنها هم با "claude-sonnet-4-6" یکسان رفتار شود.
    """
    if not model_id:
        return False
    # حل alias از طریق registry (مثلاً "claude" → "claude-sonnet-4-6")
    try:
        from ..core.models_registry import get_model
        _obj = get_model(model_id)
        if _obj and _obj.id:
            model_id = _obj.id
    except Exception:
        pass
    m = model_id.lower()
    if any(h in m for h in _NO_TOOL_CALLING_HINTS):
        return False
    return any(m.startswith(p) for p in _TOOL_CALLING_PROVIDER_PREFIXES)


# ── تعریف ابزارها (Anthropic tools schema) ──────────────────────────────────
def _build_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "read_file",
            "description": (
                "محتوای کامل یک فایل را از مخزن می‌خواند. قبل از پیشنهاد هر "
                "تغییری، فایل‌های مرتبط را با این ابزار بخوان — هرگز محتوای فایل "
                "را حدس نزن. مسیر باید دقیقاً از فهرست فایل‌های پروژه باشد."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "مسیر کامل فایل نسبت به ریشهٔ مخزن، مثلاً 'backend/app/main.py'",
                    }
                },
                "required": ["path"],
            },
        },
        {
            "name": "list_files",
            "description": (
                "فهرست فایل‌های پروژه را برمی‌گرداند، اختیاری با فیلتر زیررشته. "
                "وقتی مطمئن نیستی فایل کجاست یا نام دقیقش چیست استفاده کن."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "زیررشته برای فیلتر مسیرها (اختیاری). خالی = همهٔ فایل‌ها",
                    }
                },
                "required": [],
            },
        },
        {
            "name": "submit_action_plan",
            "description": (
                "وقتی علت ریشه‌ای را فهمیدی و فایل‌های لازم را خوانده‌ای، این "
                "ابزار را صدا بزن تا تحلیل و راه‌حل نهایی را ثبت کنی. این آخرین "
                "قدم است و حلقه را تمام می‌کند.\n\n"
                "🔴 قبل از فراخوانی این ابزار، **حتماً** این چک‌لیست را در ذهن انجام بده:\n"
                "1. یک‌بار دیگر متن خطا/لاگ اصلی که کاربر داد را بخوان.\n"
                "2. فیکس پیشنهادی‌ات دقیقاً همان چیزی را که در error log آمده هدف می‌گیرد؟ "
                "(مثلاً: اگر لاگ می‌گوید 'pip install ... Python 3.14.3' و pydantic-core fail شد، "
                "فیکس باید مربوط به Python version یا requirements باشد — نه frontend deps.)\n"
                "3. اگر دیدی فایل config (مثل render.yaml) می‌گوید X ولی لاگ‌های واقعی می‌گویند Y، "
                "**به لاگ اعتماد کن، نه config** — config ممکن است override شده باشد.\n"
                "4. اگر فیکست در واقع موضوع *دیگری* را حل می‌کند (مثلاً frontend وقتی خطا backend است)، "
                "آن را در analysis صریحاً بگو و در commit_message علامت بزن.\n\n"
                "اگر بعد از این چک واقعاً نمی‌توانی fix قطعی بدهی، files را خالی [] بگذار و در analysis "
                "دلیلش را بنویس — هرگز فیکس نامرتبط را به‌جای fix واقعی ارائه نکن."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "analysis": {
                        "type": "string",
                        "description": "تحلیل کوتاه و دقیق علت ریشه‌ای و راه‌حل (فارسی، حداکثر ۱۵ خط)",
                    },
                    "files": {
                        "type": "array",
                        "description": "فایل‌هایی که باید تغییر کنند",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "operation": {
                                    "type": "string",
                                    "enum": ["modify", "create", "modify_sections", "delete"],
                                },
                                "description": {"type": "string"},
                                "content": {
                                    "type": "string",
                                    "description": "محتوای کامل فایل (برای modify/create فایل‌های <۲۰۰ خط)",
                                },
                                "sections": {
                                    "type": "array",
                                    "description": "برای modify_sections: لیست {find, replace}",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "find": {"type": "string"},
                                            "replace": {"type": "string"},
                                        },
                                    },
                                },
                            },
                            "required": ["path", "operation"],
                        },
                    },
                    "commit_message": {"type": "string"},
                },
                "required": ["analysis", "files"],
            },
        },
        # ────────────────────────────────────────────────────────────────────
        # ابزارهای Render — برای زمانی که مشکل از طرف plat پلتفرم است (نه کد):
        # env vars، runtime version، redeploy. agent باید فقط روی سرویسی کار
        # کند که به repo فعلی (owner/repo) متعلق است.
        # ────────────────────────────────────────────────────────────────────
        {
            "name": "render_list_services",
            "description": (
                "فهرست تمام سرویس‌های Render که با کلید API در دسترس است را برمی‌گرداند. "
                "ابتدا این را صدا بزن تا service_id مربوط به repo فعلی (owner/repo) را پیدا کنی. "
                "خروجی: لیست {id, name, type, branch, repo}."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "render_get_service",
            "description": (
                "جزئیات کامل یک سرویس Render: runtime (python/docker/static_site)، "
                "buildCommand، startCommand، branch، repo، dashboard_url. این برای "
                "فهمیدن «این سرویس واقعاً چطور تنظیم شده» ضروری است — مخصوصاً وقتی "
                "فایل config (مثل runtime.txt / render.yaml) با رفتار واقعی تضاد دارد."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"service_id": {"type": "string"}},
                "required": ["service_id"],
            },
        },
        {
            "name": "render_get_env_vars",
            "description": (
                "لیست environment variables تنظیم‌شده روی سرویس Render. "
                "🔴 اگر PYTHON_VERSION یا NODE_VERSION در env vars باشد، runtime.txt را "
                "**override می‌کند** — وقتی Python/Node version مشکل دارد و runtime.txt "
                "نادیده گرفته می‌شود، **اول این را چک کن**."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"service_id": {"type": "string"}},
                "required": ["service_id"],
            },
        },
        {
            "name": "render_set_env_var",
            "description": (
                "یک env var روی سرویس Render set می‌کند (اگر بود update، اگر نبود create). "
                "مثلاً برای رفع مشکل Python version: PYTHON_VERSION=3.12.7 (مطمئن‌تر از "
                "runtime.txt چون Render ممکن است runtime.txt را به دلایلی نادیده بگیرد). "
                "بعد از این، باید render_trigger_deploy صدا بزنی تا تغییر اعمال شود. "
                "⚠️ فقط روی سرویسی که به repo فعلی ({owner}/{repo}) تعلق دارد عمل کن."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["service_id", "key", "value"],
            },
        },
        {
            "name": "render_trigger_deploy",
            "description": (
                "یک deploy جدید روی سرویس Render اجرا می‌کند. اگر تغییرات env var یا "
                "dependency داشتی، clear_cache=true بگذار تا cache قدیمی استفاده نشود. "
                "⚠️ فقط روی سرویسی که به repo فعلی ({owner}/{repo}) تعلق دارد عمل کن."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "clear_cache": {"type": "boolean", "default": False},
                },
                "required": ["service_id"],
            },
        },
        {
            "name": "render_get_deploys",
            "description": (
                "فهرست deploy های اخیر یک سرویس Render با وضعیت (live/build_failed/...) "
                "و commit. برای فهمیدن «آیا آخرین deploy موفق بود؟» یا «چند deploy "
                "اخیر همه fail شدند؟» این را صدا بزن."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["service_id"],
            },
        },
        {
            "name": "render_get_deploy_logs",
            "description": (
                "🔴 **مهم‌ترین ابزار وقتی deploy شکست خورده**: لاگ‌های واقعی یک deploy "
                "را مستقیماً از Render می‌خواند (به‌جای اتکا به paste کاربر). "
                "از آن استفاده کن تا علت دقیق build failure را با چشم خودت ببینی — "
                "نه از روی فایل‌های config حدس بزنی. اگر deploy_id بدهی همان deploy، "
                "وگرنه آخرین لاگ‌های سرویس. log_type می‌تواند 'build' یا 'app' باشد."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "deploy_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 200},
                    "log_type": {"type": "string", "enum": ["build", "app"]},
                },
                "required": ["service_id"],
            },
        },
    ]


async def run_inspector_agent(
    *,
    ai_manager,
    github_svc,
    model_id: str,
    owner: str,
    repo: str,
    token: Optional[str],
    branch: Optional[str],
    system_prompt: str,
    user_prompt: str,
    file_list: List[str],
    max_iterations: int = 14,
    max_file_chars: int = 18000,
    max_tokens: int = 8000,
) -> AsyncIterator[Tuple[str, Dict[str, Any]]]:
    """
    حلقهٔ عامل را اجرا می‌کند و رویدادها را yield می‌کند.

    آخرین رویداد همیشه ("agent_result", {...}) است با کلیدهای:
      - content: str (متن تحلیل برای نمایش)
      - action_plan: Optional[dict] (خام، باید بعداً validate شود)
      - files_read: Dict[str, str] (فایل‌هایی که agent واقعاً خواند — برای validator)
      - model_used: str
      - tokens_used: int
      - iterations: int
      - stop_reason: str ('submitted' | 'max_iterations' | 'natural_stop' | 'error')
    """
    tools = _build_tools()
    file_set = set(file_list)
    files_read: Dict[str, str] = {}
    total_tokens = 0
    # 🆕 شفافیت: نام مدل در همهٔ پیام‌های progress تا کاربر بداند کدام مدل
    # دارد کار می‌کند (به‌جای «{_tag}» مبهم).
    _tag = f"[{model_id}]"

    # تاریخچهٔ مکالمهٔ agent (فقط user/assistant — system جدا پاس می‌شود)
    messages: List[Message] = [Message(role="user", content=user_prompt)]

    final_analysis = ""
    action_plan: Optional[Dict[str, Any]] = None
    stop_reason = "natural_stop"

    for _iter in range(1, max_iterations + 1):
        try:
            resp = await ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="system", content=system_prompt)] + messages,
                max_tokens=max_tokens,
                temperature=0.2,
                tools=tools,
                tool_choice={"type": "auto"},
                allow_fallback=False,
            )
        except Exception as e:
            slog.warning(f"{_tag} generate failed at iter {_iter}: {e}")
            yield ("progress", {
                "step": "agent_error",
                "message": f"⚠️ {_tag} خطا در فراخوان (تلاش {_iter}): {str(e)[:120]}",
            })
            stop_reason = "error"
            break

        total_tokens += resp.tokens_used or 0
        if resp.content and resp.content.strip():
            final_analysis = resp.content.strip()

        # مدل ابزاری صدا نزد → کارش تمام است
        if not resp.tool_calls:
            stop_reason = "natural_stop"
            break

        # پیام assistant را با tool_calls کانونیکال echo برگردان (provider-agnostic).
        # هر سرویس این را به فرمت native خود (Anthropic blocks / OpenAI tool_calls /
        # Gemini functionCall) ترجمه می‌کند.
        messages.append(Message(
            role="assistant",
            content=resp.content or "",
            tool_calls=resp.tool_calls,
        ))

        tool_results: List[Dict[str, Any]] = []
        _submitted = False

        for call in resp.tool_calls:
            name = call.get("name", "")
            cid = call.get("id", "")
            args = call.get("input", {}) or {}

            # helper برای ساخت tool_result با name (Gemini با name match می‌کند)
            def _tr(content, is_error=False):
                d = {"tool_use_id": cid, "name": name, "content": content}
                if is_error:
                    d["is_error"] = True
                return d

            if name == "read_file":
                path = (args.get("path") or "").strip().lstrip("/")
                if path not in file_set:
                    # شاید نزدیک باشد — کمک کن خودش را اصلاح کند
                    _suggest = [p for p in file_list if path.split("/")[-1] in p][:5]
                    _msg = f"فایل '{path}' در پروژه یافت نشد."
                    if _suggest:
                        _msg += " شاید منظورت یکی از این‌ها بود:\n" + "\n".join(_suggest)
                    tool_results.append(_tr(_msg, is_error=True))
                    yield ("progress", {"step": "agent_read_miss", "message": f"⚠️ فایل ناموجود: {path}"})
                    continue
                if path in files_read:
                    _content = files_read[path]
                else:
                    yield ("progress", {"step": "agent_read", "message": f"📖 {_tag} خواندن {path}...", "file": path})
                    try:
                        res = await github_svc.get_file_content(owner, repo, path, branch=branch, token=token)
                    except Exception as re:
                        tool_results.append(_tr(f"خطا در خواندن: {str(re)[:120]}", is_error=True))
                        continue
                    if not res.get("success"):
                        tool_results.append(_tr(f"خطا: {res.get('error', 'unknown')}", is_error=True))
                        continue
                    _content = res.get("content", "") or ""
                    files_read[path] = _content
                _truncated = _content
                if len(_truncated) > max_file_chars:
                    _truncated = _truncated[:max_file_chars] + "\n... [بریده شد به دلیل اندازه]"
                _nlines = _content.count("\n") + 1
                tool_results.append(_tr(f"محتوای {path} ({_nlines} خط):\n```\n{_truncated}\n```"))

            elif name == "list_files":
                _filter = (args.get("filter") or "").strip()
                _matched = [p for p in file_list if _filter in p] if _filter else file_list
                _shown = _matched[:200]
                _txt = "\n".join(_shown)
                if len(_matched) > len(_shown):
                    _txt += f"\n... و {len(_matched) - len(_shown)} فایل دیگر"
                tool_results.append(_tr(_txt or "موردی یافت نشد"))
                yield ("progress", {"step": "agent_list", "message": f"📂 {_tag} فهرست فایل‌ها (فیلتر: '{_filter or 'همه'}') — {len(_matched)} مورد"})

            elif name == "submit_action_plan":
                final_analysis = (args.get("analysis") or final_analysis or "").strip()
                action_plan = {
                    "files": args.get("files", []) or [],
                    "commit_message": args.get("commit_message", "") or "",
                }
                _submitted = True
                stop_reason = "submitted"
                _nf = len(action_plan["files"])
                yield ("progress", {"step": "agent_submit", "message": f"✅ {_tag} action_plan ثبت شد — {_nf} فایل"})
                tool_results.append(_tr("action_plan دریافت شد. تمام."))

            # ────────────────────────────────────────────────────────────────
            # ابزارهای Render (پلتفرم) — اگر RENDER_API_KEY در env باشد، agent
            # می‌تواند خودش env vars را بخواند/تنظیم کند و deploy بزند.
            # ────────────────────────────────────────────────────────────────
            elif name in ("render_list_services", "render_get_service",
                          "render_get_env_vars", "render_set_env_var",
                          "render_trigger_deploy", "render_get_deploys",
                          "render_get_deploy_logs"):
                try:
                    from .deploy_service import RenderDeployService
                except Exception as _ie:
                    tool_results.append(_tr(f"deploy_service در دسترس نیست: {_ie}", is_error=True))
                    continue
                _rds = RenderDeployService()  # کلید از env (RENDER_API_KEY)
                if not _rds.is_configured():
                    tool_results.append(_tr(
                        "❌ RENDER_API_KEY در env تنظیم نشده. بازرس برای کار با Render نیاز به کلید دارد.",
                        is_error=True,
                    ))
                    continue
                try:
                    # ── helper: ایمنی نوشتنی — service باید به repo فعلی متعلق باشد
                    async def _verify_repo_match(sid: str):
                        if not (owner and repo):
                            return True, ""
                        info = await _rds.get_service(sid)
                        if not info.get("success"):
                            return False, info.get("error", "service not found")
                        _svc = info.get("service") or {}
                        # repo ممکن است در svc یا در svc.repo یا در svc.serviceDetails باشد
                        _repo_url = (
                            _svc.get("repo") or _svc.get("repoUrl")
                            or (_svc.get("serviceDetails", {}) or {}).get("repo", "")
                            or ""
                        )
                        target = f"{owner}/{repo}".lower()
                        if target not in (_repo_url or "").lower():
                            return False, f"repo سرویس ({_repo_url}) با repo فعلی ({target}) مطابقت ندارد"
                        return True, ""

                    if name == "render_list_services":
                        yield ("progress", {"step": "agent_render_list", "message": f"☁️ {_tag} گرفتن لیست سرویس‌های Render..."})
                        svcs = await _rds.list_services()
                        # خلاصه‌سازی فیلدها — فقط مهم‌ها
                        _summary = []
                        for entry in (svcs or []):
                            s = entry.get("service") if isinstance(entry, dict) and "service" in entry else entry
                            if not isinstance(s, dict):
                                continue
                            _summary.append({
                                "id": s.get("id", ""),
                                "name": s.get("name", ""),
                                "type": s.get("type", ""),
                                "branch": s.get("branch", ""),
                                "repo": s.get("repo", ""),
                                "suspended": s.get("suspended", ""),
                            })
                        tool_results.append(_tr(_json.dumps(_summary, ensure_ascii=False, indent=2)[:max_file_chars]))

                    elif name == "render_get_service":
                        sid = (args.get("service_id") or "").strip()
                        if not sid:
                            tool_results.append(_tr("service_id لازم است", is_error=True))
                        else:
                            yield ("progress", {"step": "agent_render_get", "message": f"☁️ {_tag} گرفتن جزئیات سرویس {sid}..."})
                            res = await _rds.get_service(sid)
                            if not res.get("success"):
                                tool_results.append(_tr(f"خطا: {res.get('error')}", is_error=True))
                            else:
                                _svc = res.get("service") or {}
                                _details = _svc.get("serviceDetails") or {}
                                _info = {
                                    "id": _svc.get("id"),
                                    "name": _svc.get("name"),
                                    "type": _svc.get("type"),
                                    "branch": _svc.get("branch"),
                                    "repo": _svc.get("repo"),
                                    "autoDeploy": _svc.get("autoDeploy"),
                                    "suspended": _svc.get("suspended"),
                                    "dashboardUrl": _svc.get("dashboardUrl") or _svc.get("dashboard_url"),
                                    "buildCommand": _details.get("buildCommand"),
                                    "startCommand": _details.get("startCommand"),
                                    "env": _details.get("env"),
                                    "region": _details.get("region"),
                                    "rootDir": _svc.get("rootDir") or _details.get("rootDir"),
                                    "runtime": _details.get("runtime") or _svc.get("type"),
                                }
                                tool_results.append(_tr(_json.dumps(_info, ensure_ascii=False, indent=2)))

                    elif name == "render_get_env_vars":
                        sid = (args.get("service_id") or "").strip()
                        if not sid:
                            tool_results.append(_tr("service_id لازم است", is_error=True))
                        else:
                            yield ("progress", {"step": "agent_render_env", "message": f"☁️ {_tag} خواندن env vars سرویس {sid}..."})
                            res = await _rds.get_env_vars(sid)
                            if not res.get("success"):
                                tool_results.append(_tr(f"خطا: {res.get('error')}", is_error=True))
                            else:
                                _secret_hints = ("key", "secret", "token", "password", "pass", "dsn", "cert")
                                _items = []
                                for ev in res.get("env_vars", []):
                                    k = ev.get("key", "")
                                    v = ev.get("value", "")
                                    if k and any(h in k.lower() for h in _secret_hints):
                                        v = f"<REDACTED ({len(v)} chars)>"
                                    _items.append({"key": k, "value": v})
                                tool_results.append(_tr(_json.dumps(_items, ensure_ascii=False, indent=2)))

                    elif name == "render_set_env_var":
                        sid = (args.get("service_id") or "").strip()
                        k = (args.get("key") or "").strip()
                        v = args.get("value", "")
                        if not (sid and k):
                            tool_results.append(_tr("service_id و key لازم‌اند", is_error=True))
                        else:
                            ok, err = await _verify_repo_match(sid)
                            if not ok:
                                tool_results.append(_tr(f"❌ ایمنی: {err}", is_error=True))
                            else:
                                yield ("progress", {"step": "agent_render_set_env", "message": f"☁️ {_tag} تنظیم {k} روی سرویس {sid}..."})
                                res = await _rds.set_env_var(sid, k, v)
                                if res.get("success"):
                                    tool_results.append(_tr(f"✅ {k} تنظیم شد. برای اعمال، render_trigger_deploy را با clear_cache=true صدا بزن."))
                                else:
                                    tool_results.append(_tr(f"خطا: {res.get('error')}", is_error=True))

                    elif name == "render_trigger_deploy":
                        sid = (args.get("service_id") or "").strip()
                        cc = bool(args.get("clear_cache", False))
                        if not sid:
                            tool_results.append(_tr("service_id لازم است", is_error=True))
                        else:
                            ok, err = await _verify_repo_match(sid)
                            if not ok:
                                tool_results.append(_tr(f"❌ ایمنی: {err}", is_error=True))
                            else:
                                yield ("progress", {"step": "agent_render_deploy", "message": f"🚀 {_tag} اجرای deploy جدید روی {sid} (clear_cache={cc})..."})
                                res = await _rds.trigger_deploy(sid, clear_cache=cc)
                                if res.get("success"):
                                    tool_results.append(_tr(f"✅ deploy آغاز شد — deploy_id: {res.get('deploy_id')}, status: {res.get('status')}"))
                                else:
                                    tool_results.append(_tr(f"خطا: {res.get('error')}", is_error=True))

                    elif name == "render_get_deploys":
                        sid = (args.get("service_id") or "").strip()
                        lim = int(args.get("limit") or 10)
                        if not sid:
                            tool_results.append(_tr("service_id لازم است", is_error=True))
                        else:
                            yield ("progress", {"step": "agent_render_deploys", "message": f"☁️ {_tag} فهرست deploy های اخیر سرویس {sid}..."})
                            res = await _rds.get_deploys(sid, limit=lim)
                            if not res.get("success"):
                                tool_results.append(_tr(f"خطا: {res.get('error')}", is_error=True))
                            else:
                                tool_results.append(_tr(_json.dumps(res.get("deploys", []), ensure_ascii=False, indent=2)[:max_file_chars]))

                    elif name == "render_get_deploy_logs":
                        sid = (args.get("service_id") or "").strip()
                        did = (args.get("deploy_id") or "").strip() or None
                        lim = int(args.get("limit") or 200)
                        lt = (args.get("log_type") or "").strip() or None
                        if not sid:
                            tool_results.append(_tr("service_id لازم است", is_error=True))
                        else:
                            yield ("progress", {"step": "agent_render_logs", "message": f"📜 {_tag} خواندن لاگ‌های deploy از Render (sid={sid}, deploy={did or 'latest'})..."})
                            res = await _rds.get_deploy_logs(sid, deploy_id=did, limit=lim, log_type=lt)
                            if not res.get("success"):
                                tool_results.append(_tr(f"خطا: {res.get('error')}", is_error=True))
                            else:
                                _lines = res.get("logs", []) or []
                                # خلاصه‌سازی به فرمت timestamp message برای خواندن natural
                                _txt = "\n".join(
                                    f"{ln.get('timestamp','')} [{ln.get('level','')}] {ln.get('message','')}"
                                    for ln in _lines
                                )
                                if not _txt:
                                    _txt = "(هیچ لاگی برگشت نکرد)"
                                tool_results.append(_tr(_txt[:max_file_chars]))
                finally:
                    try:
                        await _rds.close()
                    except Exception:
                        pass

            else:
                tool_results.append(_tr(f"ابزار ناشناخته: {name}", is_error=True))

        # نتایج ابزار را با فیلد کانونیکال tool_results برمی‌گردانیم (provider-agnostic).
        messages.append(Message(role="user", content="", tool_results=tool_results))

        if _submitted:
            break
    else:
        stop_reason = "max_iterations"
        yield ("progress", {
            "step": "agent_max_iter",
            "message": f"⚠️ {_tag} به سقف {max_iterations} مرحله رسید — جمع‌بندی با آخرین یافته‌ها",
        })

    yield ("agent_result", {
        "content": final_analysis,
        "action_plan": action_plan,
        "files_read": files_read,
        "model_used": model_id,
        "tokens_used": total_tokens,
        "iterations": _iter,
        "stop_reason": stop_reason,
    })


# ────────────────────────────────────────────────────────────────────────────
# قدم ۲ (multi-agent) — نقش بازبین (reviewer)
# ────────────────────────────────────────────────────────────────────────────

def is_complex_plan(action_plan: Optional[Dict[str, Any]]) -> bool:
    """آیا این action_plan آن‌قدر پیچیده هست که بازبینی دومدلی ارزش داشته باشد؟

    معیار: ≥۲ فایل، یا هر تغییر روی فایلی که محتوای کاملش بازنویسی می‌شود
    (operation=modify با content بزرگ → ریسک بازنویسی مخرب).
    """
    if not action_plan:
        return False
    files = action_plan.get("files") or []
    if len(files) >= 2:
        return True
    for f in files:
        if f.get("operation") == "modify" and len((f.get("content") or "")) > 4000:
            return True
    return False


def _summarize_plan_for_review(action_plan: Dict[str, Any], files_read: Dict[str, str]) -> str:
    """خلاصهٔ تغییرات پیشنهادی برای بازبین (بدون فرستادن کل محتوای فایل‌ها)."""
    lines = []
    for f in (action_plan.get("files") or []):
        path = f.get("path", "?")
        op = f.get("operation", "?")
        if op == "modify_sections":
            secs = f.get("sections") or []
            lines.append(f"### {path} — modify_sections ({len(secs)} بخش)")
            for i, s in enumerate(secs[:6]):
                _find = (s.get("find") or "")[:300]
                _rep = (s.get("replace") or "")[:300]
                lines.append(f"  [بخش {i+1}] FIND:\n{_find}\n  REPLACE:\n{_rep}")
        elif op in ("modify", "create"):
            content = (f.get("content") or "")
            _preview = content[:1500]
            lines.append(f"### {path} — {op} ({content.count(chr(10))+1} خط)\n{_preview}")
        else:
            lines.append(f"### {path} — {op}")
    return "\n\n".join(lines) or "(بدون فایل)"


async def run_reviewer_pass(
    *,
    ai_manager,
    user_message: str,
    analysis: str,
    action_plan: Dict[str, Any],
    files_read: Dict[str, str],
    exclude_model: Optional[str] = None,
    max_tokens: int = 1800,
) -> Optional[Dict[str, Any]]:
    """نقش «بازبین»: یک مدل (ترجیحاً متفاوت از orchestrator) تغییرات پیشنهادی را
    از نظر صحت/کامل‌بودن/ریسک بازنویسی مخرب بررسی می‌کند.

    مدل reviewer را خودش resolve و در صورت لزوم موقتاً فعال/revert می‌کند.
    خروجی: {reviewer_model, verdict ("approve"|"concerns"), notes} یا None
    اگر بازبینی ممکن/لازم نبود.
    """
    try:
        from .inspector_roles import (
            resolve_role_assignments,
            apply_temp_enables,
            revert_temp_enables,
        )
    except Exception:
        return None

    try:
        # اول یک مدلِ متفاوت از orchestrator (cross-model review). اگر نبود،
        # به self-review با همان مدل برمی‌گردیم.
        asg = None
        if exclude_model:
            asg = resolve_role_assignments(
                ai_manager, roles=["reviewer"], exclude=[exclude_model]
            ).get("reviewer")
        if not asg or not asg.model_id:
            asg = resolve_role_assignments(ai_manager, roles=["reviewer"]).get("reviewer")
    except Exception as e:
        slog.warning(f"[reviewer] resolve failed: {e}")
        return None
    if not asg or not asg.model_id:
        return None

    reviewer_model = asg.model_id
    _is_self_review = bool(exclude_model and reviewer_model == exclude_model)

    _revert = apply_temp_enables([reviewer_model]) if asg.needs_temp_enable else []
    try:
        sys_prompt = (
            "تو یک بازبین کد ارشد و سخت‌گیر هستی. وظیفه‌ات بررسی یک راه‌حل پیشنهادی "
            "(action_plan) نسبت به مشکل کاربر است. این موارد را به ترتیب چک کن:\n"
            "1) 🎯 **انطباق با خطای واقعی**: متن خطا/لاگ کاربر را با دقت بخوان. آیا فیکس "
            "پیشنهادی دقیقاً همان چیزی را که در error log آمده هدف می‌گیرد؟ "
            "اگر مثلاً log می‌گوید 'pip install pydantic-core Python 3.14 fail' ولی "
            "فیکس روی frontend deps است → این concern جدی است (موضوع متفاوت!).\n"
            "2) 🛡 **صحت فنی**: آیا تغییرات واقعاً درست‌اند؟ syntax/import/typeها سالم‌اند؟\n"
            "3) 🚫 **بازنویسی مخرب**: قابلیت موجودی حذف نمی‌شود؟\n"
            "4) 🧩 **کامل بودن**: edge case، فایل وابسته، import جا افتاده نیست؟\n"
            "فقط یک JSON معتبر برگردان (بدون متن اضافه):\n"
            '{"verdict":"approve" یا "concerns","notes":"توضیح کوتاه فارسی، حداکثر ۸ خط؛ اگر concern داری حتماً مشخص کن کدام مورد ۱-۴"}'
        )
        user_prompt = (
            f"## مشکل/درخواست کاربر:\n{user_message[:2000]}\n\n"
            f"## تحلیل و راه‌حل پیشنهادی (orchestrator):\n{(analysis or '')[:2500]}\n\n"
            f"## تغییرات پیشنهادی روی فایل‌ها:\n{_summarize_plan_for_review(action_plan, files_read)}\n\n"
            "حالا بازبینی کن و فقط JSON را برگردان."
        )
        resp = await ai_manager.generate(
            model_id=reviewer_model,
            messages=[Message(role="system", content=sys_prompt), Message(role="user", content=user_prompt)],
            max_tokens=max_tokens,
            temperature=0.1,
            allow_fallback=False,
        )
        raw = (resp.content or "").strip()
        verdict, notes = "approve", ""
        try:
            _s = raw.find("{")
            _e = raw.rfind("}")
            if _s != -1 and _e != -1 and _e > _s:
                parsed = _json.loads(raw[_s:_e + 1])
                verdict = (parsed.get("verdict") or "approve").strip().lower()
                if verdict not in ("approve", "concerns"):
                    verdict = "concerns" if "concern" in verdict else "approve"
                notes = (parsed.get("notes") or "").strip()
        except Exception:
            # JSON نبود — متن خام را به‌عنوان notes نگه دار
            notes = raw[:800]
            verdict = "concerns" if any(w in raw.lower() for w in ("مشکل", "نمی", "concern", "break", "خراب", "حذف")) else "approve"
        return {
            "reviewer_model": reviewer_model,
            "verdict": verdict,
            "notes": notes,
            "tokens_used": resp.tokens_used or 0,
            "self_review": _is_self_review,
        }
    except Exception as e:
        slog.warning(f"[reviewer] pass failed: {e}")
        return None
    finally:
        if _revert:
            try:
                revert_temp_enables(_revert)
            except Exception:
                pass
