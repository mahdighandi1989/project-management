"""
Task Merge Service
==================
ادغام هوشمند تسک‌های مشابه — هم برای ایجاد دستی (manual + telegram) و هم
برای merge های پیشنهادی AI.

ویژگی‌ها:
- preview_merge: مقایسهٔ side-by-side هر فیلد (existing vs candidate) + پیشنهاد AI
- apply_merge: اعمال انتخاب کاربر روی فیلدهای موجود
- apply_merge_simple: ادغام سادهٔ heuristic (بدون AI) — وقتی کاربر سریع
  تأیید می‌کند فقط فیلدهای خالی پر شوند یا candidate.AC جدیدها به existing.AC
  اضافه شوند.

کاربر می‌تواند برای هر فیلد یکی از سه حالت را انتخاب کند:
  - "existing": مقدار قبلی نگه داشته شود
  - "candidate": مقدار جدید جایگزین شود
  - "ai_merged": متن ادغام‌شدهٔ AI به‌کار رود

این سرویس روی in-memory store اپ کار می‌کند و فقط task های موجود را به‌روز می‌کند —
هیچ تسک جدیدی نمی‌سازد و هیچ تسکی را پاک نمی‌کند.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class FieldDiff:
    """تفاوت یک فیلد بین existing و candidate."""
    name: str
    existing_value: Any
    candidate_value: Any
    ai_merged_value: Optional[Any] = None
    recommendation: str = "existing"  # existing | candidate | ai_merged
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MergePreview:
    existing_task_id: str
    candidate_title: str
    field_diffs: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    similarity_score: float = 0.0
    new_seen_count: int = 0
    raw_idea_history_append: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# Service
# ============================================================

class TaskMergeService:
    """سرویس ادغام تسک‌های مشابه."""

    # cache برای preview ها (key: existing_id + hash(candidate_raw_idea), TTL 600s)
    _preview_cache: Dict[str, Dict[str, Any]] = {}
    _PREVIEW_TTL_SECONDS = 600

    # ---------------- internal helpers ----------------

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _texts_equivalent(a: str, b: str) -> bool:
        """دو متن «تقریباً یکسان» هستند؟ (case + whitespace insensitive)."""
        a = (a or "").strip().lower()
        b = (b or "").strip().lower()
        if not a or not b:
            return False
        # نرمال‌سازی whitespace
        import re as _re
        a = _re.sub(r"\s+", " ", a)
        b = _re.sub(r"\s+", " ", b)
        return a == b

    @staticmethod
    def _is_subset_of(needle: str, haystack: str) -> bool:
        """آیا needle (متن کوتاه) درون haystack موجود است (بدون تفاوت big)?"""
        if not needle or not haystack:
            return False
        return needle.strip().lower() in haystack.strip().lower()

    def _cache_key(self, existing_id: str, candidate_raw_idea: str) -> str:
        import hashlib
        h = hashlib.md5(candidate_raw_idea.encode("utf-8")).hexdigest()[:12]
        return f"{existing_id}:{h}"

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        item = self._preview_cache.get(key)
        if not item:
            return None
        if time.time() - item.get("_ts", 0) > self._PREVIEW_TTL_SECONDS:
            self._preview_cache.pop(key, None)
            return None
        return item.get("data")

    def _cache_set(self, key: str, data: Dict[str, Any]) -> None:
        self._preview_cache[key] = {"_ts": time.time(), "data": data}

    # ---------------- merge heuristics ----------------

    @staticmethod
    def _merge_acceptance_criteria(
        existing_ac: List[Any], candidate_ac: List[Any],
    ) -> List[Any]:
        """ادغام دو لیست AC: AC های candidate که با AC های existing شباهت زیادی
        ندارند (Jaccard < 0.6) به انتها append می‌شوند.

        🔬 (Runtime Verify Stage 1) — AC می‌تواند str قدیمی یا dict جدید باشد.
        برای dedup فقط متن (`text`) مقایسه می‌شود، ولی ساختار اصلی AC حفظ می‌گردد.
        """
        if not candidate_ac:
            return list(existing_ac or [])
        from .oversight_service import OversightService as _OS
        out = list(existing_ac or [])
        for c in candidate_ac:
            cs = _OS._ac_text(c)
            if not cs:
                continue
            is_dup = False
            for e in out:
                e_text = _OS._ac_text(e)
                try:
                    if _OS._jaccard(cs, e_text) >= 0.6:
                        is_dup = True
                        break
                except Exception:
                    if cs.lower() == e_text.lower():
                        is_dup = True
                        break
            if not is_dup:
                out.append(c)  # حفظ ساختار اصلی (str یا dict)
        return out

    @staticmethod
    def _merge_target_files(
        existing_tf: List[str], candidate_tf: List[str],
    ) -> List[str]:
        """ادغام دو لیست target_files — union با حفظ ترتیب existing سپس candidate."""
        seen = set()
        out: List[str] = []
        for x in (existing_tf or []) + (candidate_tf or []):
            xs = (x or "").strip()
            if xs and xs not in seen:
                seen.add(xs)
                out.append(xs)
        return out

    # ---------------- preview ----------------

    async def preview_merge(
        self,
        existing: Any,  # OversightTask
        candidate_title: str,
        candidate_raw_idea: str,
        candidate_prompt: str = "",
        candidate_acceptance_criteria: Optional[List[str]] = None,
        candidate_target_files: Optional[List[str]] = None,
        similarity_score: float = 0.0,
        *,
        model_id: Optional[str] = None,
        use_ai: bool = False,
    ) -> MergePreview:
        """تولید پیش‌نمایش ادغام — heuristic + اختیاراً AI merge برای متن‌های بلند.

        خروجی شامل field_diffs برای هر فیلد قابل ادغام. کاربر در UI انتخاب می‌کند
        کدام recommendation اعمال شود.

        نتیجه برای ۶۰۰ ثانیه cache می‌شود تا کلیک‌های پیاپی روی همان merge هزینهٔ
        AI تکراری نداشته باشد (کلید: hash(existing_id + candidate_raw_idea + use_ai)).
        """
        # cache hit?
        cache_key = self._cache_key(
            existing.id, f"{candidate_raw_idea}|ai={int(bool(use_ai))}",
        )
        cached = self._cache_get(cache_key)
        if cached:
            try:
                # بازسازی MergePreview از dict ذخیره‌شده
                return MergePreview(**cached)
            except Exception:
                # اگر struct تغییر کرده، cache را بی‌خیال شو
                self._preview_cache.pop(cache_key, None)

        cand_ac = list(candidate_acceptance_criteria or [])
        cand_tf = list(candidate_target_files or [])

        existing_title = existing.title or ""
        existing_idea = existing.raw_idea or ""
        existing_prompt = existing.prompt or ""
        existing_ac = list(existing.acceptance_criteria or [])
        existing_tf = list(existing.target_files or [])

        diffs: List[FieldDiff] = []
        change_count = 0

        # ── title ──────────────────────────────────────────────────
        if candidate_title and not self._texts_equivalent(existing_title, candidate_title):
            # عنوان وجود دارد و متفاوت است
            # heuristic: عنوان بلندتر/توصیفی‌تر اولویت دارد
            recommend = (
                "candidate"
                if len(candidate_title) > len(existing_title) + 5
                else "existing"
            )
            diffs.append(FieldDiff(
                name="title",
                existing_value=existing_title,
                candidate_value=candidate_title,
                ai_merged_value=None,
                recommendation=recommend,
                notes="عنوان بلندتر معمولاً اطلاعات بیشتری دارد",
            ))
            if recommend != "existing":
                change_count += 1

        # ── raw_idea ───────────────────────────────────────────────
        if candidate_raw_idea and not self._texts_equivalent(existing_idea, candidate_raw_idea):
            ai_merged = None
            if self._is_subset_of(candidate_raw_idea, existing_idea):
                # candidate درون existing است → existing کافی است
                recommend = "existing"
                notes = "ایدهٔ جدید زیرمجموعهٔ ایدهٔ موجود است"
            elif self._is_subset_of(existing_idea, candidate_raw_idea):
                # existing درون candidate است → candidate کامل‌تر است
                recommend = "candidate"
                notes = "ایدهٔ جدید کامل‌تر و شامل ایدهٔ موجود است"
                change_count += 1
            else:
                # دو ایده مکمل هستند → AI merge (یا concat ساده)
                ai_merged = self._concat_with_separator(existing_idea, candidate_raw_idea)
                recommend = "ai_merged"
                notes = "دو ایده مکمل هستند — ترکیب پیشنهاد می‌شود"
                change_count += 1
                if use_ai:
                    try:
                        ai_merged = await self._ai_merge_text(
                            existing_idea,
                            candidate_raw_idea,
                            label="ایده/توضیح تسک",
                            model_id=model_id,
                        ) or ai_merged
                    except Exception as e:
                        logger.debug(f"AI merge for raw_idea failed: {e}")
            diffs.append(FieldDiff(
                name="raw_idea",
                existing_value=existing_idea,
                candidate_value=candidate_raw_idea,
                ai_merged_value=ai_merged,
                recommendation=recommend,
                notes=notes,
            ))

        # ── acceptance_criteria ────────────────────────────────────
        if cand_ac:
            merged_ac = self._merge_acceptance_criteria(existing_ac, cand_ac)
            new_items = [x for x in merged_ac if x not in existing_ac]
            if new_items:
                diffs.append(FieldDiff(
                    name="acceptance_criteria",
                    existing_value=existing_ac,
                    candidate_value=cand_ac,
                    ai_merged_value=merged_ac,
                    recommendation="ai_merged",
                    notes=f"{len(new_items)} AC جدید به موجود اضافه می‌شود",
                ))
                change_count += 1

        # ── target_files ───────────────────────────────────────────
        if cand_tf:
            merged_tf = self._merge_target_files(existing_tf, cand_tf)
            new_files = [x for x in merged_tf if x not in existing_tf]
            if new_files:
                diffs.append(FieldDiff(
                    name="target_files",
                    existing_value=existing_tf,
                    candidate_value=cand_tf,
                    ai_merged_value=merged_tf,
                    recommendation="ai_merged",
                    notes=f"{len(new_files)} فایل جدید اضافه می‌شود",
                ))
                change_count += 1

        # ── prompt ──────────────────────────────────────────────────
        # پرامپت معمولاً نباید override شود مگر اینکه existing خالی/خیلی کوتاه باشد
        if candidate_prompt and not existing_prompt:
            diffs.append(FieldDiff(
                name="prompt",
                existing_value=existing_prompt,
                candidate_value=candidate_prompt,
                ai_merged_value=None,
                recommendation="candidate",
                notes="پرامپت موجود خالی است",
            ))
            change_count += 1
        elif candidate_prompt and len(existing_prompt) < 200 and len(candidate_prompt) > 400:
            diffs.append(FieldDiff(
                name="prompt",
                existing_value=existing_prompt,
                candidate_value=candidate_prompt,
                ai_merged_value=None,
                recommendation="candidate",
                notes="پرامپت موجود خیلی کوتاه است — پیشنهاد جایگزینی",
            ))
            change_count += 1
        # در حالت کلی پرامپت تغییر داده نمی‌شود (می‌توان بعداً با
        # regenerate_prompt_for_task کاربر این کار را خواست).

        summary_parts = [
            f"شباهت: {int(similarity_score * 100)}٪",
            f"{change_count} فیلد قابل به‌روزرسانی",
        ]
        existing_seen = (
            getattr(existing, "scan_seen_count", 1) or 1
        ) + (getattr(existing, "manual_seen_count", 0) or 0)

        preview = MergePreview(
            existing_task_id=existing.id,
            candidate_title=candidate_title,
            field_diffs=[d.to_dict() for d in diffs],
            summary=" | ".join(summary_parts),
            similarity_score=round(similarity_score, 4),
            new_seen_count=existing_seen + 1,
            raw_idea_history_append=(candidate_raw_idea or candidate_title)[:300],
        )
        # ذخیره در cache برای کلیک‌های پیاپی
        try:
            self._cache_set(cache_key, preview.to_dict())
        except Exception:
            pass
        return preview

    @staticmethod
    def _concat_with_separator(a: str, b: str) -> str:
        a = (a or "").rstrip()
        b = (b or "").lstrip()
        if not a:
            return b
        if not b:
            return a
        return f"{a}\n---\n{b}"

    async def _ai_merge_text(
        self,
        existing: str,
        candidate: str,
        label: str,
        model_id: Optional[str] = None,
    ) -> str:
        """با AI دو متن را ادغام می‌کند. اگر AI fail شد، concat ساده برمی‌گردد."""
        prompt = (
            f"دو نسخه از همین «{label}» تسک هستند. وظیفهٔ تو این است که هر دو را در "
            f"یک متن واحد ادغام کنی. قوانین:\n"
            f"1. فقط بخش‌های مکمل کاندید را به موجود اضافه کن.\n"
            f"2. هیچ بخشی از متن موجود را حذف نکن، مگر اینکه با کاندید تناقض صریح داشته باشد.\n"
            f"3. خروجی فقط متن نهایی است — هیچ توضیح اضافی نده.\n\n"
            f"--- موجود ---\n{existing}\n\n"
            f"--- کاندید ---\n{candidate}\n\n"
            f"--- متن نهایی ---\n"
        )
        try:
            from ..api.routes.simple_projects import ai_generate
            model_ids = [model_id] if model_id else None
            out = await ai_generate(prompt, model_ids=model_ids)
            return (out or "").strip() or self._concat_with_separator(existing, candidate)
        except Exception as e:
            logger.debug(f"_ai_merge_text fallback: {e}")
            return self._concat_with_separator(existing, candidate)

    # ---------------- apply ----------------

    async def apply_merge(
        self,
        existing_task_id: str,
        candidate_title: str,
        candidate_raw_idea: str,
        candidate_prompt: str = "",
        candidate_acceptance_criteria: Optional[List[str]] = None,
        candidate_target_files: Optional[List[str]] = None,
        chosen_fields: Optional[Dict[str, str]] = None,
        source: str = "manual",
        similarity_score: float = 0.0,
        ai_merged_values: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """اعمال انتخاب کاربر روی تسک موجود.

        ai_merged_values: dict[field_name -> ai_merged_value] که از preview آمده.
        اگر کاربر choice='ai_merged' برای فیلدی انتخاب کرده باشد، از این مقدار
        استفاده می‌شود (نه concat ساده). اگر None باشد، fallback به heuristic.
        """
        from .oversight_service import get_oversight_service
        service = get_oversight_service()
        chosen = chosen_fields or {}
        ai_vals = ai_merged_values or {}

        async with service._lock:
            existing = next(
                (t for t in service.tasks if t.id == existing_task_id), None,
            )
            if existing is None:
                return None

            merged_fields_applied: List[str] = []
            old_prompt = existing.prompt

            # 1) title
            choice = chosen.get("title", "existing")
            if choice == "candidate" and candidate_title:
                existing.title = candidate_title
                merged_fields_applied.append("title")
            elif choice == "ai_merged" and ai_vals.get("title"):
                existing.title = str(ai_vals["title"])
                merged_fields_applied.append("title")

            # 2) raw_idea
            choice = chosen.get("raw_idea", "existing")
            if choice == "candidate" and candidate_raw_idea:
                existing.raw_idea = candidate_raw_idea
                merged_fields_applied.append("raw_idea")
            elif choice == "ai_merged" and candidate_raw_idea:
                # اولویت با ai_merged_value از preview (اگر use_ai=true بود)
                ai_text = ai_vals.get("raw_idea")
                if ai_text and isinstance(ai_text, str) and ai_text.strip():
                    existing.raw_idea = ai_text.strip()[:5000]
                else:
                    # fallback: concat ساده اگر AI merge انجام نشده بود
                    existing.raw_idea = self._concat_with_separator(
                        existing.raw_idea or "", candidate_raw_idea,
                    )[:5000]
                merged_fields_applied.append("raw_idea")

            # 3) acceptance_criteria
            choice = chosen.get("acceptance_criteria", "existing")
            if choice in ("candidate", "ai_merged") and candidate_acceptance_criteria:
                if choice == "candidate":
                    existing.acceptance_criteria = list(candidate_acceptance_criteria)
                else:
                    # اولویت با ai_merged_value (لیست از preview)
                    ai_ac = ai_vals.get("acceptance_criteria")
                    if isinstance(ai_ac, list) and ai_ac:
                        existing.acceptance_criteria = [str(x) for x in ai_ac if x]
                    else:
                        existing.acceptance_criteria = self._merge_acceptance_criteria(
                            existing.acceptance_criteria or [],
                            candidate_acceptance_criteria,
                        )
                merged_fields_applied.append("acceptance_criteria")

            # 4) target_files
            choice = chosen.get("target_files", "existing")
            if choice in ("candidate", "ai_merged") and candidate_target_files:
                if choice == "candidate":
                    existing.target_files = list(candidate_target_files)
                else:
                    ai_tf = ai_vals.get("target_files")
                    if isinstance(ai_tf, list) and ai_tf:
                        existing.target_files = [str(x) for x in ai_tf if x]
                    else:
                        existing.target_files = self._merge_target_files(
                            existing.target_files or [],
                            candidate_target_files,
                        )
                merged_fields_applied.append("target_files")

            # 5) prompt (فقط اگر صراحتاً انتخاب شده باشد)
            choice = chosen.get("prompt", "existing")
            if choice == "candidate" and candidate_prompt:
                # نسخهٔ قبلی را در prompt_history ذخیره کن
                history_entry = {
                    "prompt": old_prompt,
                    "raw_idea": existing.raw_idea or "",
                    "model_id": (existing.models_used[0] if existing.models_used else "") or "",
                    "generated_at": existing.updated_at or existing.created_at,
                    "source": f"merge_from_{source}",
                }
                existing.prompt_history.insert(0, history_entry)
                existing.prompt_history = existing.prompt_history[:10]
                existing.prompt = candidate_prompt
                merged_fields_applied.append("prompt")

            # 6) شمارنده‌ها + history
            existing.merge_count = (getattr(existing, "merge_count", 0) or 0) + 1
            if source in ("manual", "telegram", "telegram_bot"):
                existing.manual_seen_count = (
                    getattr(existing, "manual_seen_count", 0) or 0
                ) + 1
            else:
                existing.scan_seen_count = (
                    getattr(existing, "scan_seen_count", 1) or 1
                ) + 1
                existing.last_seen_in_scan_at = self._now_iso()

            existing.raw_idea_history.append({
                "ts": self._now_iso(),
                "source": source,
                "raw_idea": (candidate_raw_idea or candidate_title)[:600],
                "candidate_title": candidate_title[:200],
                "merged_fields": merged_fields_applied,
                "similarity_score": round(similarity_score, 4),
            })
            # cap به 30 آیتم آخر
            existing.raw_idea_history = existing.raw_idea_history[-30:]
            existing.updated_at = self._now_iso()

            result = existing.to_dict()
            service._save_tasks()

        # notify (خارج از lock)
        try:
            from .notification_service import notification_service
            project_name = existing.project_full_name
            lines = [
                "🔀 *ادغام تسک انجام شد*",
                f"📁 پروژه: `{project_name}`",
                f"📌 تسک: «{(existing.title or '')[:80]}»",
                f"📥 منبع: `{source}`",
                f"📊 شباهت: {int(similarity_score * 100)}٪",
            ]
            if merged_fields_applied:
                lines.append(f"🛠 فیلدهای به‌روز: {', '.join(merged_fields_applied)}")
            else:
                lines.append("ℹ️ فقط شمارنده‌ها افزایش یافت")
            await notification_service.notify_event(
                "task_merged",
                "\n".join(lines),
                subject="ادغام تسک",
                priority="low",
                project_name=project_name,
                watched_id=existing.watched_id,
            )
        except Exception as e:
            logger.debug(f"task_merged notify failed: {e}")

        return result

    async def apply_merge_simple(
        self,
        existing_task_id: str,
        candidate_title: str,
        candidate_raw_idea: str,
        candidate_prompt: str = "",
        candidate_acceptance_criteria: Optional[List[str]] = None,
        candidate_target_files: Optional[List[str]] = None,
        source: str = "manual",
    ) -> Optional[Dict[str, Any]]:
        """ادغام پیش‌فرض هوشمند بدون نیاز به تأیید مرحله‌ای کاربر.

        برای فلوی «ادغام سریع» وقتی کاربر در UI روی «ادغام» (بدون preview) کلیک می‌کند
        یا در تلگرام callback را تأیید می‌کند. خط‌مشی: AC ها و target_files merge شوند،
        title فقط اگر کاندید بلندتر بود، raw_idea concat.
        """
        # شباهت را برای ثبت history محاسبه کن (best-effort)
        sim_score = 0.0
        try:
            from .oversight_service import get_oversight_service, OversightService
            service = get_oversight_service()
            existing = next(
                (t for t in service.tasks if t.id == existing_task_id), None,
            )
            if existing is not None:
                tj = OversightService._jaccard(candidate_title, existing.title or "")
                io = OversightService._ngram_overlap(
                    candidate_raw_idea or candidate_title,
                    existing.raw_idea or existing.title or "",
                )
                sim_score = round(tj * 0.5 + io * 0.5, 4)
        except Exception:
            pass

        chosen = {
            "title": "candidate" if len(candidate_title) > 8 else "existing",
            "raw_idea": "ai_merged",
            "acceptance_criteria": "ai_merged",
            "target_files": "ai_merged",
            "prompt": "existing",  # پرامپت تغییر نمی‌کند مگر صراحتاً
        }
        # برای title فقط اگر واقعاً بلندتر و توصیفی‌تر باشد
        try:
            from .oversight_service import get_oversight_service
            existing = next(
                (t for t in get_oversight_service().tasks if t.id == existing_task_id),
                None,
            )
            if existing is not None and len(candidate_title) <= len(existing.title or "") + 5:
                chosen["title"] = "existing"
        except Exception:
            pass

        return await self.apply_merge(
            existing_task_id=existing_task_id,
            candidate_title=candidate_title,
            candidate_raw_idea=candidate_raw_idea,
            candidate_prompt=candidate_prompt,
            candidate_acceptance_criteria=candidate_acceptance_criteria,
            candidate_target_files=candidate_target_files,
            chosen_fields=chosen,
            source=source,
            similarity_score=sim_score,
        )


# ============================================================
# Singleton
# ============================================================

_service: Optional[TaskMergeService] = None


def get_task_merge_service() -> TaskMergeService:
    global _service
    if _service is None:
        _service = TaskMergeService()
    return _service
