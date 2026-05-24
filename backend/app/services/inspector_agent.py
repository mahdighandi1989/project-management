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
                "🔴🔴 **قبل از این ابزار، حتماً `preflight_check` را با همان "
                "files صدا بزن**. اگر preflight هر مشکلی پیدا کرد، در همان "
                "action_plan رفع کن و دوباره preflight. بدون preflight موفق، "
                "submit نکن — این تنها راه جلوگیری از whack-a-mole deploy fail است.\n\n"
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
                "⚠️ فقط روی سرویسی که به repo فعلی ({owner}/{repo}) تعلق دارد عمل کن. "
                "⛔ برای تغییر buildCommand یا startCommand از این ابزار استفاده نکن — "
                "آن‌ها env var نیستند، در `serviceDetails` ذخیره می‌شوند. از "
                "render_update_service_settings استفاده کن."
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
            "name": "render_update_service_settings",
            "description": (
                "🔴 برای حل «frontend build نمی‌شود / placeholder نشان داده می‌شود» "
                "وقتی `buildCommand` در render_get_service خالی یا ناقص است: این "
                "ابزار `serviceDetails.buildCommand` (یا startCommand) را روی سرویس "
                "ست می‌کند — این فیلد env var نیست بلکه setting اصلی سرویس است "
                "(در Render UI > Settings > Build & Deploy). بعد از این "
                "render_trigger_deploy با clear_cache=true بزن. مثال build_command "
                "برای پروژه FastAPI+React: "
                "`cd frontend && npm install && npm run build && cd .. && pip install -r requirements.txt` "
                "⚠️ فقط روی سرویسی که به repo فعلی ({owner}/{repo}) تعلق دارد."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "build_command": {"type": "string"},
                    "start_command": {"type": "string"},
                    "auto_deploy": {"type": "boolean"},
                },
                "required": ["service_id"],
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
        {
            "name": "preflight_check",
            "description": (
                "🔴 **قبل از submit_action_plan حتماً این را صدا بزن** — این ابزار "
                "تغییرات پیشنهادی‌ات را با وضعیت فعلی repo شبیه‌سازی می‌کند و "
                "سه دسته مشکل که در گذشته whack-a-mole deploy failure تولید "
                "کرده را تشخیص می‌دهد:\n"
                "  1. **import از فایل خالی**: اگر کدت `from X import Y` دارد ولی "
                "فایل X خالی/بدون تعریف Y است (مثل notification_schema.py خالی)\n"
                "  2. **تعارض ماژول vs پوشه**: اگر هم `app/foo.py` و هم "
                "`app/foo/__init__.py` در repo وجود دارد → Python سرگردان می‌شود "
                "و `from app.foo.bar import ...` شکست می‌خورد\n"
                "  3. **پکیج خارجی بدون requirements**: مثلاً اگر کدت از `EmailStr` "
                "(نیاز email-validator) یا پکیج دیگری استفاده می‌کند که در "
                "requirements.txt نیست\n\n"
                "اگر مشکل پیدا شد، آن را در همان action_plan رفع کن (مثلاً تعاریف "
                "لازم را به فایل خالی اضافه کن، یا پکیج را به requirements.txt "
                "بیافزای) سپس دوباره preflight بزن. اگر بدون preflight موفق "
                "submit کنی، deploy احتمالاً شکست خواهد خورد و کاربر مجبور "
                "می‌شود دوباره به تو خبر دهد."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "description": "همان لیست files که قصد داری در action_plan بفرستی",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "operation": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["path"],
                        },
                    }
                },
                "required": ["files"],
            },
        },
        # ────────────────────────────────────────────────────────────────────
        # 🆕 (git-revert) — ابزارهای revert/recovery: برای زمانی که کاربر
        # می‌خواد به یک branch قدیمی برگرده یا state یک فایل رو از branch
        # دیگری بازیابی کنه. transcript کاربر نشون داد نیاز جدی به این
        # قابلیت هست.
        # ────────────────────────────────────────────────────────────────────
        {
            "name": "list_branches",
            "description": (
                "لیست branchهای repo رو برمی‌گردونه. وقتی کاربر می‌گه «برگرد به branch X» یا"
                " «من می‌خوام state branch قدیمی رو ببینم» از این استفاده کن تا اول branch"
                " مرجع رو پیدا کنی. خروجی: لیست نام branchها."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "read_file_from_branch",
            "description": (
                "محتوای یک فایل رو از یک branch مشخص (نه branch فعلی) می‌خونه. وقتی کاربر می‌گه"
                " «این فایل رو از branch X برگردون»، اول با این ابزار محتوای فایل رو از branch مرجع"
                " بخون، بعد در action_plan با operation=modify اون محتوا رو set کن."
                " مثلاً کاربر گفت «برگرد به inspector/smart-fix-1779608575» → برای هر فایل که"
                " تفاوت داره، این ابزار رو با branch=inspector/smart-fix-1779608575 صدا بزن"
                " و محتوای برگشت رو در action_plan قرار بده."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "مسیر فایل نسبت به root repo"},
                    "branch": {"type": "string", "description": "نام branch مرجع، مثلاً 'inspector/smart-fix-XXXXX' یا 'main'"},
                },
                "required": ["path", "branch"],
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
    max_iterations: int = 24,
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
            elif name == "preflight_check":
                _files_arg = args.get("files") or []
                if not isinstance(_files_arg, list) or not _files_arg:
                    tool_results.append(_tr("files (لیست) لازم است", is_error=True))
                else:
                    yield ("progress", {"step": "agent_preflight", "message": f"🛡️ {_tag} اجرای preflight (شامل اسکن repo-wide)..."})
                    # 🆕 repo-wide: قبل از چک، فایل‌های critical که agent نخوانده را
                    # هم بکش (routes/schemas/services/dependencies/models) — تا
                    # importهای broken در فایل‌های دست‌نخورده هم پیدا شوند.
                    _critical_prefixes = (
                        "app/routes/", "app/schemas/", "app/services/",
                        "app/dependencies/", "app/models/",
                        "backend/app/routes/", "backend/app/schemas/",
                        "backend/app/services/", "backend/app/dependencies/",
                        "backend/app/models/",
                    )
                    _to_fetch = [
                        p for p in file_list
                        if p.endswith(".py")
                        and p not in files_read
                        and any(p.startswith(pfx) for pfx in _critical_prefixes)
                    ][:60]  # سقف ۶۰ تا تا overhead کنترل شود
                    if _to_fetch:
                        yield ("progress", {"step": "agent_preflight_fetch", "message": f"📥 {_tag} خواندن {len(_to_fetch)} فایل critical repo برای preflight جامع (موازی)..."})
                        # 🆕 fetch موازی با bounded concurrency تا overhead ۳۰s
                        # به ~۳s کاهش یابد. semaphore=10 تا rate limit GitHub نخوریم.
                        import asyncio as _asy_pf
                        _sem = _asy_pf.Semaphore(10)
                        async def _fetch_one(_fp):
                            async with _sem:
                                try:
                                    return _fp, await github_svc.get_file_content(owner, repo, _fp, branch=branch, token=token)
                                except Exception:
                                    return _fp, {"success": False}
                        _results = await _asy_pf.gather(*[_fetch_one(p) for p in _to_fetch])
                        for _fp, _res in _results:
                            if isinstance(_res, dict) and _res.get("success"):
                                files_read[_fp] = _res.get("content", "") or ""
                    _issues = _run_preflight_check(
                        proposed_files=_files_arg,
                        files_read=files_read,
                        file_set=file_set,
                    )
                    if not _issues:
                        tool_results.append(_tr("✅ preflight جامع: هیچ مشکلی پیدا نشد — می‌توانی submit_action_plan را صدا بزنی."))
                    else:
                        _txt = "🔴 preflight جامع (شامل اسکن repo) این مشکلات را پیدا کرد — قبل از submit همه را رفع کن:\n\n"
                        # 🆕 جمع‌آوری فایل‌های مرتبط (که در issues مذکورند) تا محتوای
                        # واقعی‌شان را همراه گزارش بفرستیم — agent دیگر لازم نیست
                        # یکی‌یکی read_file بزند (صرفه‌جویی در iteration).
                        _files_in_issues = []
                        _seen = set()
                        for iss in _issues:
                            _f = iss.get("file")
                            if _f and _f not in _seen and _f in files_read:
                                _seen.add(_f)
                                _files_in_issues.append(_f)
                            # برای import errors، فایل target هم مهم است
                            _msg = iss.get("message", "")
                            import re as _re_pf
                            _m = _re_pf.search(r"from (\S+) import", _msg)
                            if _m:
                                _target_mod = _m.group(1)
                                for _candidate in (_target_mod.replace(".", "/") + ".py",
                                                   _target_mod.replace(".", "/") + "/__init__.py"):
                                    if _candidate in files_read and _candidate not in _seen:
                                        _seen.add(_candidate)
                                        _files_in_issues.append(_candidate)
                        for i, iss in enumerate(_issues, 1):
                            _txt += f"{i}. **{iss.get('severity', 'issue')}** — {iss.get('message', '')}\n"
                            if iss.get("file"):
                                _txt += f"   فایل: `{iss['file']}`\n"
                            if iss.get("hint"):
                                _txt += f"   راه‌حل: {iss['hint']}\n"
                            _txt += "\n"
                        # محتوای فایل‌های مرتبط — agent بدون read_file اضافی همه را دارد
                        if _files_in_issues:
                            _txt += "\n--- محتوای فعلی فایل‌های مرتبط (از قبل خوانده شده، نیازی به read_file مجدد نیست) ---\n"
                            for _fp in _files_in_issues[:15]:  # سقف ۱۵ تا برای کنترل توکن
                                _c = files_read.get(_fp, "") or ""
                                _c_trunc = _c if len(_c) <= 4000 else _c[:4000] + "\n...[truncated]"
                                _nlines = _c.count("\n") + 1
                                _txt += f"\n### `{_fp}` ({_nlines} خط):\n```\n{_c_trunc}\n```\n"
                        tool_results.append(_tr(_txt))

            # 🆕 (git-revert) — list branches و read from branch
            elif name == "list_branches":
                try:
                    _session = await github_svc._get_session()
                    _headers = github_svc._get_headers(token)
                    _url = f"{github_svc.GITHUB_API}/repos/{owner}/{repo}/branches?per_page=100"
                    async with _session.get(_url, headers=_headers, timeout=20) as _resp:
                        if _resp.status != 200:
                            tool_results.append(_tr(
                                f"خطا در گرفتن branches: HTTP {_resp.status}",
                                is_error=True,
                            ))
                            continue
                        _data = await _resp.json()
                    _branches = [b.get("name", "") for b in (_data or []) if b.get("name")]
                    tool_results.append(_tr(
                        f"branches موجود ({len(_branches)} مورد):\n" + "\n".join(_branches[:100])
                    ))
                    yield ("progress", {
                        "step": "agent_list_branches",
                        "message": f"🌿 {_tag} لیست branches: {len(_branches)} مورد",
                    })
                except Exception as _be:
                    tool_results.append(_tr(f"خطا: {str(_be)[:200]}", is_error=True))

            elif name == "read_file_from_branch":
                _path = (args.get("path") or "").strip().lstrip("/")
                _branch_ref = (args.get("branch") or "").strip()
                if not _path or not _branch_ref:
                    tool_results.append(_tr("path و branch هر دو لازم‌اند", is_error=True))
                    continue
                yield ("progress", {
                    "step": "agent_read_branch",
                    "message": f"📖 {_tag} خواندن {_path} از branch '{_branch_ref}'...",
                    "file": _path,
                    "branch": _branch_ref,
                })
                try:
                    _res = await github_svc.get_file_content(
                        owner, repo, _path, branch=_branch_ref, token=token
                    )
                except Exception as _re:
                    tool_results.append(_tr(f"خطا در خواندن: {str(_re)[:200]}", is_error=True))
                    continue
                if not _res.get("success"):
                    _err = _res.get("error", "unknown")
                    tool_results.append(_tr(
                        f"❌ نمی‌توان فایل '{_path}' را از branch '{_branch_ref}' خواند: {_err}. "
                        f"اول با list_branches مطمئن شو branch وجود دارد.",
                        is_error=True,
                    ))
                    continue
                _branch_content = _res.get("content", "") or ""
                # 🆕 (git-revert) — ثبت در files_read تا validator (blind-overwrite
                # check) قبول کنه که این path "خوانده شده". محتوا از branch Y
                # ست می‌شه ولی purpose اینه که commit به branch فعلی بشه با
                # محتوای branch Y (revert intent).
                files_read[_path] = _branch_content
                # برای امن بودن agent context، اگر بزرگ شد truncate کنیم
                # ولی توجه: agent باید این محتوا رو کامل در action_plan بذاره،
                # پس فقط در پاسخ tool truncate می‌کنیم با هشدار.
                _full_len = len(_branch_content)
                _shown = _branch_content
                if len(_shown) > max_file_chars:
                    _shown = _shown[:max_file_chars] + (
                        f"\n... [بریده شد به دلیل اندازه — کل فایل {_full_len} کاراکتر است؛ "
                        f"وقتی در action_plan قرار می‌دهی محتوای کامل را از branch بازخوانی کن]"
                    )
                _nlines = _branch_content.count("\n") + 1
                tool_results.append(_tr(
                    f"محتوای {_path} از branch '{_branch_ref}' ({_nlines} خط، {_full_len} کاراکتر):\n"
                    f"```\n{_shown}\n```\n"
                    f"⚠️ برای revert: این محتوا را در action_plan با operation='modify' و "
                    f"path='{_path}' قرار بده — اگر کاربر صراحتاً revert خواست، این کار درست است "
                    f"حتی اگر فایل را در branch فعلی هم نخوانده باشی."
                ))

            elif name in ("render_list_services", "render_get_service",
                          "render_get_env_vars", "render_set_env_var",
                          "render_trigger_deploy", "render_get_deploys",
                          "render_get_deploy_logs",
                          "render_update_service_settings"):
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

                    elif name == "render_update_service_settings":
                        sid = (args.get("service_id") or "").strip()
                        if not sid:
                            tool_results.append(_tr("service_id لازم است", is_error=True))
                        else:
                            ok, err = await _verify_repo_match(sid)
                            if not ok:
                                tool_results.append(_tr(f"❌ ایمنی: {err}", is_error=True))
                            else:
                                _bc = args.get("build_command")
                                _sc = args.get("start_command")
                                _ad = args.get("auto_deploy")
                                _summary = []
                                if _bc is not None:
                                    _summary.append(f"buildCommand={_bc[:80]}")
                                if _sc is not None:
                                    _summary.append(f"startCommand={_sc[:80]}")
                                if _ad is not None:
                                    _summary.append(f"autoDeploy={_ad}")
                                yield ("progress", {"step": "agent_render_patch", "message": f"⚙️ {_tag} به‌روزرسانی تنظیمات سرویس {sid}: {', '.join(_summary) or '(empty)'}..."})
                                res = await _rds.update_service_settings(
                                    sid,
                                    build_command=_bc,
                                    start_command=_sc,
                                    auto_deploy=_ad,
                                )
                                if res.get("success"):
                                    tool_results.append(_tr(f"✅ تنظیمات سرویس به‌روز شد: {res.get('updated')}. حالا render_trigger_deploy با clear_cache=true بزن تا اعمال شود."))
                                else:
                                    tool_results.append(_tr(f"خطا: {res.get('error')}", is_error=True))

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
        # 🆕 (review-gate) — تشخیص severity از notes. اگر notes شامل
        # کلیدواژه‌های critical (بازنویسی مخرب، کد ناقص، حذف فایل بدون
        # بررسی، blind overwrite، ...) باشد، plan را برای apply-all
        # blocked می‌کنیم. این جلوی کاربر transcript ۲۳-فایلی با bug
        # شناخته‌شده از commit شدن رو می‌گیره.
        _notes_lower = (notes or "").lower()
        _critical_signals = [
            "بازنویسی مخرب", "کد ناقص", "ناقص است", "کد در وسط",
            "قطع شده", "قطع‌شده", "blind overwrite", "overwrite کور",
            "deploy می‌شکند", "deploy فیل", "crash می‌کند",
            "import شکست", "importerror", "syntaxerror",
            "nullable=false", "nullable false",  # شایع در گزارش‌های schema
            "بدون بررسی وابستگی", "بدون بررسی", "بدون اطمینان از",
            "اشتباه است", "fail می‌کند", "fail می کند",
            "endpoint غایب", "endpoint وجود ندارد", "endpoint ذکر نشده",
            "حدسی است", "حدسی‌اند",
            # 🆕 (audit 2) — کلیدواژه‌های اضافی بعد از تست با ۱۰ note از transcript
            "خراب کند", "خراب می‌کند", "خراب می کند",
            "خطرناک است", "خطرناک",
            "بازنویسی می‌شود", "بازنویسی شده",
            "از صفر بازنویسی", "کامل بازنویسی",
            "رشته باز", "string باز",
            "حذف می‌شود بدون", "حذف می شود بدون",
        ]
        _matched_signals = [s for s in _critical_signals if s in _notes_lower]
        _is_critical = verdict == "concerns" and len(_matched_signals) >= 1
        return {
            "reviewer_model": reviewer_model,
            "verdict": verdict,
            "notes": notes,
            "tokens_used": resp.tokens_used or 0,
            "self_review": _is_self_review,
            "has_critical_issues": _is_critical,
            "critical_signals": _matched_signals[:5],
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


# ════════════════════════════════════════════════════════════════════════════
# preflight check — جلوگیری از whack-a-mole deploy failure
# ════════════════════════════════════════════════════════════════════════════

_PY_STDLIB = {
    "os", "sys", "re", "json", "time", "datetime", "typing", "pathlib",
    "collections", "itertools", "functools", "asyncio", "logging",
    "subprocess", "tempfile", "shutil", "hashlib", "hmac", "base64",
    "uuid", "random", "math", "enum", "dataclasses", "contextlib",
    "urllib", "http", "socket", "email", "csv", "xml", "html",
    "io", "struct", "array", "copy", "pickle", "sqlite3",
    "warnings", "traceback", "inspect", "importlib", "gc", "abc",
    "threading", "multiprocessing", "concurrent", "queue", "string",
    "unicodedata", "codecs", "locale", "argparse", "platform",
    "errno", "signal", "secrets", "ssl", "getpass", "decimal",
    "calendar", "zoneinfo", "statistics",
}

_PY_PACKAGE_ALIASES = {
    "PIL": "pillow", "cv2": "opencv-python", "sklearn": "scikit-learn",
    "jose": "python-jose", "jwt": "pyjwt", "bs4": "beautifulsoup4",
    "yaml": "pyyaml", "dotenv": "python-dotenv", "magic": "python-magic",
    "multipart": "python-multipart",
}

_PYDANTIC_EXTRAS_REQUIRED = {
    "EmailStr": ("email-validator", "pydantic[email]"),
    "NameEmail": ("email-validator", "pydantic[email]"),
}


def _run_preflight_check(*, proposed_files, files_read, file_set):
    """چک‌های preflight قبل از submit:
    1. import از فایل خالی (فایل در repo هست ولی نماد لازم را ندارد)
    2. تعارض module.py vs module/__init__.py
    3. پکیج خارجی import شده ولی در requirements.txt نیست
    خروجی: list of {severity, message, file?, hint?}
    """
    import ast as _ast
    issues = []

    # ساخت view مجازی بعد از اعمال action_plan
    _virtual = {}
    for f in (proposed_files or []):
        if not isinstance(f, dict):
            continue
        p = (f.get("path") or "").strip()
        if not p:
            continue
        op = (f.get("operation") or "modify").lower()
        if op == "delete":
            _virtual[p] = "__DELETED__"
        else:
            _virtual[p] = f.get("content") or ""

    _all_files_after = dict(files_read or {})
    for p, c in _virtual.items():
        if c == "__DELETED__":
            _all_files_after.pop(p, None)
        else:
            _all_files_after[p] = c

    _repo_after = set(file_set or [])
    for p, c in _virtual.items():
        if c == "__DELETED__":
            _repo_after.discard(p)
        else:
            _repo_after.add(p)

    # چک ۲: تعارض module.py vs module/__init__.py
    for p in _repo_after:
        if not p.endswith(".py") or p.endswith("__init__.py"):
            continue
        _mod_path = p[:-3]
        _pkg_init = _mod_path + "/__init__.py"
        if _pkg_init in _repo_after:
            issues.append({
                "severity": "critical",
                "message": "تعارض ماژول/پوشه: هم `" + p + "` و هم `" + _pkg_init + "` وجود دارد — Python سرگردان می‌شود.",
                "file": p,
                "hint": "یکی را حذف کن. معمولاً پوشه (`" + _pkg_init + "`) را نگه دار و فایل تک (`" + p + "`) را delete کن.",
            })

    # requirements.txt
    _req_text = _all_files_after.get("requirements.txt", "")
    _req_packages = set()
    for line in (_req_text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].split("[")[0].strip().lower()
        if name:
            _req_packages.add(name)

    _project_roots = set()
    for p in _repo_after:
        if p.endswith(".py"):
            _project_roots.add(p.split("/")[0])

    _external_imports = set()

    # ساخت لیست همهٔ فایل‌های Python که باید imports آن‌ها چک شود:
    # 1) فایل‌های proposed (که agent قصد commit دارد)
    # 2) فایل‌های read-only repo (که از قبل در repo هستند) — تا importهای broken
    #    در فایل‌های دست‌نخورده هم پیدا شوند (whack-a-mole کشف ریشه‌ای).
    _files_to_check = []
    _proposed_paths = set()
    for f in (proposed_files or []):
        if not isinstance(f, dict):
            continue
        p = (f.get("path") or "").strip()
        if not p.endswith(".py"):
            continue
        op = (f.get("operation") or "modify").lower()
        if op == "delete":
            continue
        _proposed_paths.add(p)
        _files_to_check.append({"path": p, "content": f.get("content") or "", "_source": "proposed"})
    # فایل‌های read-only (در files_read ولی در proposed نیستند)
    for p, c in (files_read or {}).items():
        if p.endswith(".py") and p not in _proposed_paths and c and c.strip():
            _files_to_check.append({"path": p, "content": c, "_source": "repo"})

    for f in _files_to_check:
        p = f["path"]
        content = f["content"]
        if not content.strip():
            continue
        try:
            tree = _ast.parse(content)
        except SyntaxError as se:
            issues.append({
                "severity": "critical",
                "message": "خطای syntax در `" + p + "`: " + str(se)[:150],
                "file": p,
                "hint": "syntax کد را اصلاح کن.",
            })
            continue

        for node in _ast.walk(tree):
            if isinstance(node, _ast.ImportFrom):
                target_mod = node.module or ""
                if not target_mod:
                    continue
                root = target_mod.split(".")[0]
                if root in _project_roots:
                    target_path = target_mod.replace(".", "/") + ".py"
                    target_init = target_mod.replace(".", "/") + "/__init__.py"
                    target_content = _all_files_after.get(target_path)
                    if target_content is None:
                        target_content = _all_files_after.get(target_init)
                    if target_content is None:
                        if target_path not in _repo_after and target_init not in _repo_after:
                            issues.append({
                                "severity": "critical",
                                "message": "`from " + target_mod + " import ...` — ماژول در repo وجود ندارد.",
                                "file": p,
                                "hint": "یا path import را اصلاح کن یا فایل `" + target_path + "` را create کن.",
                            })
                        continue
                    try:
                        _t_tree = _ast.parse(target_content)
                    except Exception:
                        continue
                    _defs = set()
                    for _n in _ast.walk(_t_tree):
                        if isinstance(_n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                            _defs.add(_n.name)
                        elif isinstance(_n, _ast.Assign):
                            for t in _n.targets:
                                if isinstance(t, _ast.Name):
                                    _defs.add(t.id)
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        if alias.name not in _defs:
                            issues.append({
                                "severity": "critical",
                                "message": "`from " + target_mod + " import " + alias.name + "` — `" + alias.name + "` در ماژول تعریف نشده.",
                                "file": p,
                                "hint": "فایل `" + target_path + "` خالی یا ناقص است. کلاس/تابع `" + alias.name + "` را به آن اضافه کن، یا import را حذف کن.",
                            })
                else:
                    _external_imports.add(root)
                    if root == "pydantic":
                        for alias in node.names:
                            if alias.name in _PYDANTIC_EXTRAS_REQUIRED:
                                pkg, extra = _PYDANTIC_EXTRAS_REQUIRED[alias.name]
                                if pkg not in _req_packages and "pydantic[email]" not in _req_text.lower():
                                    issues.append({
                                        "severity": "critical",
                                        "message": "`" + alias.name + "` از pydantic نیاز به `" + pkg + "` دارد ولی در requirements.txt نیست.",
                                        "file": p,
                                        "hint": "`" + pkg + ">=2.0.0` را به requirements.txt اضافه کن (یا `" + extra + "`).",
                                    })
            elif isinstance(node, _ast.Import):
                for alias in node.names:
                    target_mod = alias.name
                    root = target_mod.split(".")[0]
                    if root not in _project_roots:
                        _external_imports.add(root)

    # چک ۳: external imports vs requirements
    for ext in _external_imports:
        if ext in _PY_STDLIB:
            continue
        canonical = _PY_PACKAGE_ALIASES.get(ext, ext).lower()
        if canonical in _req_packages or ext.lower() in _req_packages:
            continue
        issues.append({
            "severity": "warning",
            "message": "پکیج خارجی `" + ext + "` import شده ولی در requirements.txt نیست.",
            "hint": "احتمالاً باید `" + canonical + "` را به requirements.txt اضافه کنی (یا اگر مطمئنی stdlib است، نادیده بگیر).",
        })

    return issues

