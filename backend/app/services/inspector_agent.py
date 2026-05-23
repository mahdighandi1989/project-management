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
                    yield ("progress", {"step": "agent_read", "message": f"📖 [agent] خواندن {path}...", "file": path})
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
                tool_results.append(_tr("action_plan دریافت شد. تمام."))

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
            "(action_plan) نسبت به مشکل کاربر است. این موارد را چک کن:\n"
            "1) آیا تغییرات واقعاً مشکل را حل می‌کنند؟\n"
            "2) آیا قابلیت موجودی را می‌شکنند یا حذف می‌کنند (بازنویسی مخرب)؟\n"
            "3) آیا چیزی جا افتاده (edge case، فایل وابسته، import)؟\n"
            "فقط یک JSON معتبر برگردان (بدون متن اضافه):\n"
            '{"verdict":"approve" یا "concerns","notes":"توضیح کوتاه فارسی، حداکثر ۸ خط"}'
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
