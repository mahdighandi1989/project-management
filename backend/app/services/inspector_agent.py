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

from .ai_base import Message
from ..core.logging_utils import StructuredLogger

slog = StructuredLogger(__name__, "INSPECTOR-AGENT")


# مدل‌هایی که tool-calling پشتیبانی می‌کنند (فعلاً فقط Claude پیاده‌سازی دارد).
_TOOL_CALLING_MODEL_PREFIXES = ("claude",)


def supports_tool_calling(model_id: str) -> bool:
    """آیا این مدل tool-calling دارد؟ (برای gate کردن استفاده از agent loop)"""
    if not model_id:
        return False
    m = model_id.lower()
    return any(m.startswith(p) or p in m for p in _TOOL_CALLING_MODEL_PREFIXES)


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
                "قدم است و حلقه را تمام می‌کند. اگر واقعاً نمی‌توانی fix را "
                "تشخیص دهی، files را خالی [] بگذار و در analysis دلیلش را بنویس."
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
            slog.warning(f"[agent] generate failed at iter {_iter}: {e}")
            yield ("progress", {
                "step": "agent_error",
                "message": f"⚠️ خطا در فراخوان مدل (تلاش {_iter}): {str(e)[:120]}",
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

        # پیام assistant را با بلوک‌های خام (شامل tool_use) echo برگردان
        messages.append(Message(
            role="assistant",
            content=resp.content or "",
            raw_content=resp.raw_assistant_content,
        ))

        tool_results: List[Dict[str, Any]] = []
        _submitted = False

        for call in resp.tool_calls:
            name = call.get("name", "")
            cid = call.get("id", "")
            args = call.get("input", {}) or {}

            if name == "read_file":
                path = (args.get("path") or "").strip().lstrip("/")
                if path not in file_set:
                    # شاید نزدیک باشد — کمک کن خودش را اصلاح کند
                    _suggest = [p for p in file_list if path.split("/")[-1] in p][:5]
                    _msg = f"فایل '{path}' در پروژه یافت نشد."
                    if _suggest:
                        _msg += " شاید منظورت یکی از این‌ها بود:\n" + "\n".join(_suggest)
                    tool_results.append({"type": "tool_result", "tool_use_id": cid, "content": _msg, "is_error": True})
                    yield ("progress", {"step": "agent_read_miss", "message": f"⚠️ فایل ناموجود: {path}"})
                    continue
                if path in files_read:
                    _content = files_read[path]
                else:
                    yield ("progress", {"step": "agent_read", "message": f"📖 [agent] خواندن {path}...", "file": path})
                    try:
                        res = await github_svc.get_file_content(owner, repo, path, branch=branch, token=token)
                    except Exception as re:
                        tool_results.append({"type": "tool_result", "tool_use_id": cid, "content": f"خطا در خواندن: {str(re)[:120]}", "is_error": True})
                        continue
                    if not res.get("success"):
                        tool_results.append({"type": "tool_result", "tool_use_id": cid, "content": f"خطا: {res.get('error', 'unknown')}", "is_error": True})
                        continue
                    _content = res.get("content", "") or ""
                    files_read[path] = _content
                _truncated = _content
                if len(_truncated) > max_file_chars:
                    _truncated = _truncated[:max_file_chars] + "\n... [بریده شد به دلیل اندازه]"
                _nlines = _content.count("\n") + 1
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": cid,
                    "content": f"محتوای {path} ({_nlines} خط):\n```\n{_truncated}\n```",
                })

            elif name == "list_files":
                _filter = (args.get("filter") or "").strip()
                _matched = [p for p in file_list if _filter in p] if _filter else file_list
                _shown = _matched[:200]
                _txt = "\n".join(_shown)
                if len(_matched) > len(_shown):
                    _txt += f"\n... و {len(_matched) - len(_shown)} فایل دیگر"
                tool_results.append({"type": "tool_result", "tool_use_id": cid, "content": _txt or "موردی یافت نشد"})
                yield ("progress", {"step": "agent_list", "message": f"📂 [agent] فهرست فایل‌ها (فیلتر: '{_filter or 'همه'}') — {len(_matched)} مورد"})

            elif name == "submit_action_plan":
                final_analysis = (args.get("analysis") or final_analysis or "").strip()
                action_plan = {
                    "files": args.get("files", []) or [],
                    "commit_message": args.get("commit_message", "") or "",
                }
                _submitted = True
                stop_reason = "submitted"
                _nf = len(action_plan["files"])
                yield ("progress", {"step": "agent_submit", "message": f"✅ [agent] action_plan ثبت شد — {_nf} فایل"})
                tool_results.append({"type": "tool_result", "tool_use_id": cid, "content": "action_plan دریافت شد. تمام."})

            else:
                tool_results.append({"type": "tool_result", "tool_use_id": cid, "content": f"ابزار ناشناخته: {name}", "is_error": True})

        # نتایج ابزار را به‌عنوان یک پیام user برگردان
        messages.append(Message(role="user", content="", raw_content=tool_results))

        if _submitted:
            break
    else:
        stop_reason = "max_iterations"
        yield ("progress", {
            "step": "agent_max_iter",
            "message": f"⚠️ [agent] به سقف {max_iterations} مرحله رسید — جمع‌بندی با آخرین یافته‌ها",
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
