# -*- coding: utf-8 -*-
"""
🧠 سرویس ایجاد هوشمند فیلدها و آیتم‌های نقشه راه

این سرویس:
1. قبل از ایجاد فیلد، چک می‌کنه آیا قابلیت مشابه وجود داره
2. فیلدها رو با وابستگی و اولویت صحیح می‌سازه
3. آیتم‌های مناسب رو به نقشه راه اضافه می‌کنه
"""

import json
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from ..core.logging_utils import StructuredLogger

slog = StructuredLogger(__name__, "FIELD-CREATOR")


class IntelligentFieldCreator:
    """سرویس ایجاد هوشمند فیلدها"""

    def __init__(self, project_id: str, db_session=None):
        self.project_id = project_id
        self.db = db_session
        self.existing_fields = []
        self.roadmap_items = []
        self.project = None

    def load_project_context(self):
        """بارگذاری context پروژه"""
        if not self.db:
            return

        from ..models.project import Project
        self.project = self.db.query(Project).filter(Project.id == self.project_id).first()

        if self.project:
            # بارگذاری فیلدهای موجود
            try:
                self.existing_fields = json.loads(self.project.dynamic_fields) if self.project.dynamic_fields else []
                self.existing_fields = [f for f in self.existing_fields if not f.get("archived")]
            except:
                self.existing_fields = []

            # پارس کردن آیتم‌های نقشه راه
            self.roadmap_items = self._parse_roadmap_items(self.project.roadmap_content or "")

            slog.info("Project context loaded",
                existing_fields=len(self.existing_fields),
                roadmap_items=len(self.roadmap_items)
            )

    def _parse_roadmap_items(self, roadmap_content: str) -> List[Dict]:
        """استخراج آیتم‌های نقشه راه"""
        items = []
        lines = roadmap_content.split('\n')
        current_phase = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # تشخیص فاز/مرحله
            if stripped.startswith('##'):
                current_phase = stripped.replace('#', '').strip()
                continue

            # تشخیص آیتم‌های لیست
            if stripped.startswith(('- ', '* ')) or re.match(r'^\d+\.', stripped):
                # چک کردن وضعیت تکمیل
                is_completed = '[x]' in stripped.lower() or '✅' in stripped or '✓' in stripped

                # تمیز کردن متن
                text = stripped
                text = re.sub(r'^[-*]\s*', '', text)
                text = re.sub(r'^\d+\.\s*', '', text)
                text = text.replace('[x]', '').replace('[X]', '').replace('[ ]', '')
                text = text.replace('✅', '').replace('✓', '').strip()

                items.append({
                    "line_index": i,
                    "text": text,
                    "phase": current_phase,
                    "completed": is_completed,
                    "raw_line": line
                })

        return items

    def check_existing_capability(self, capability_description: str) -> Dict[str, Any]:
        """
        🔍 بررسی آیا قابلیت درخواستی قبلاً وجود دارد

        Returns:
            {
                "exists": bool,
                "type": "field" | "roadmap" | "none",
                "match": {...},  # فیلد یا آیتم مشابه
                "similarity": float,
                "suggestion": str  # پیشنهاد به کاربر
            }
        """
        slog.info("Checking existing capability",
            description=capability_description[:100]
        )

        best_match = {
            "exists": False,
            "type": "none",
            "match": None,
            "similarity": 0.0,
            "suggestion": None
        }

        # 1. بررسی در فیلدهای موجود
        for field in self.existing_fields:
            field_name = field.get("name", "")
            field_value = field.get("value", "")

            # محاسبه شباهت
            name_sim = self._calculate_similarity(capability_description, field_name)
            value_sim = self._calculate_similarity(capability_description, field_value[:200])

            # ترکیب امتیازات
            combined_sim = max(name_sim, value_sim * 0.8)

            if combined_sim > best_match["similarity"] and combined_sim > 0.5:
                best_match = {
                    "exists": True,
                    "type": "field",
                    "match": field,
                    "similarity": combined_sim,
                    "suggestion": f"فیلد مشابه وجود دارد: '{field_name}'. می‌خواهید این فیلد را بروزرسانی کنید؟"
                }

        # 2. بررسی در نقشه راه
        for item in self.roadmap_items:
            item_text = item.get("text", "")
            sim = self._calculate_similarity(capability_description, item_text)

            if sim > best_match["similarity"] and sim > 0.4:
                status = "تکمیل شده" if item.get("completed") else "در انتظار"
                phase = item.get("phase", "نامشخص")
                best_match = {
                    "exists": True,
                    "type": "roadmap",
                    "match": item,
                    "similarity": sim,
                    "suggestion": f"آیتم مشابه در نقشه راه وجود دارد (فاز: {phase}, وضعیت: {status}): '{item_text[:80]}...'"
                }

        slog.info("Capability check result",
            exists=best_match["exists"],
            type=best_match["type"],
            similarity=round(best_match["similarity"], 2)
        )

        return best_match

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """محاسبه شباهت دو متن"""
        if not text1 or not text2:
            return 0.0

        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        if text1 == text2:
            return 1.0

        # شباهت کلمات (Jaccard)
        words1 = set(re.findall(r'\w+', text1))
        words2 = set(re.findall(r'\w+', text2))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        jaccard = len(intersection) / len(union) if union else 0

        # شباهت n-gram
        def get_ngrams(s, n=3):
            s = s.replace(' ', '')
            return set(s[i:i+n] for i in range(max(0, len(s)-n+1)))

        ngrams1 = get_ngrams(text1)
        ngrams2 = get_ngrams(text2)

        if ngrams1 and ngrams2:
            ngram_sim = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
        else:
            ngram_sim = 0

        # ترکیب امتیازات
        return (jaccard * 0.6 + ngram_sim * 0.4)

    def analyze_dependencies(self, field_description: str, all_fields: List[Dict]) -> List[str]:
        """
        🔗 تحلیل وابستگی‌های یک فیلد به فیلدهای دیگر

        Returns:
            لیست ID فیلدهایی که این فیلد به آنها وابسته است
        """
        dependencies = []
        desc_lower = field_description.lower()

        # کلمات کلیدی وابستگی
        dependency_keywords = [
            ("بعد از", "after"),
            ("پس از", "following"),
            ("نیاز به", "requires"),
            ("وابسته به", "depends on"),
            ("ابتدا", "first"),
            ("قبل از این", "before this"),
        ]

        for field in all_fields:
            if field.get("archived"):
                continue

            field_name = field.get("name", "").lower()
            field_id = field.get("id")

            # بررسی اشاره مستقیم به نام فیلد
            if field_name in desc_lower:
                # چک کنیم آیا در context وابستگی هست
                for fa_kw, en_kw in dependency_keywords:
                    if fa_kw in desc_lower or en_kw in desc_lower:
                        # احتمالاً وابستگی وجود دارد
                        # بررسی دقیق‌تر موقعیت
                        name_pos = desc_lower.find(field_name)
                        for kw in [fa_kw, en_kw]:
                            kw_pos = desc_lower.find(kw)
                            if kw_pos != -1 and kw_pos < name_pos:
                                dependencies.append(field_id)
                                break

            # بررسی وابستگی‌های منطقی (مثلاً setup قبل از deploy)
            logical_deps = {
                "deploy": ["setup", "config", "build", "test"],
                "test": ["implement", "code", "develop"],
                "optimize": ["implement", "test"],
                "document": ["implement", "test"],
            }

            for target_kw, prereq_kws in logical_deps.items():
                if target_kw in desc_lower:
                    for prereq in prereq_kws:
                        if prereq in field_name and field_id not in dependencies:
                            dependencies.append(field_id)

        slog.debug("Dependencies analyzed",
            field_desc=field_description[:50],
            dependencies_count=len(dependencies)
        )

        return dependencies

    def calculate_priority(
        self,
        field_data: Dict,
        ai_response_context: str = "",
        dependencies: List[str] = None
    ) -> int:
        """
        📊 محاسبه اولویت هوشمند فیلد

        Priority levels: 1 (highest) to 10 (lowest)
        """
        priority = 5  # پیش‌فرض

        name = field_data.get("name", "").lower()
        value = field_data.get("value", "").lower()
        action_type = field_data.get("action_type", "display")
        combined = f"{name} {value}"

        # 1. کلمات کلیدی اولویت بالا
        high_priority_keywords = [
            ("بحرانی", 1), ("critical", 1), ("فوری", 1), ("urgent", 1),
            ("امنیتی", 1), ("security", 1), ("vulnerability", 1),
            ("باگ", 2), ("bug", 2), ("خطا", 2), ("error", 2),
            ("مهم", 3), ("important", 3), ("اصلاح", 3), ("fix", 3),
        ]

        for keyword, prio in high_priority_keywords:
            if keyword in combined:
                priority = min(priority, prio)
                break

        # 2. کلمات کلیدی اولویت پایین
        low_priority_keywords = [
            ("بهینه‌سازی", 7), ("optimization", 7), ("refactor", 6),
            ("مستند", 8), ("document", 8), ("readme", 8),
            ("تست", 6), ("test", 6),
        ]

        for keyword, prio in low_priority_keywords:
            if keyword in combined:
                priority = max(priority, prio)
                break

        # 3. تنظیم بر اساس action_type
        action_priority_boost = {
            "github_commit": -1,  # کمی مهم‌تر
            "github_multi_commit": -1,
            "display": 0,
        }
        priority += action_priority_boost.get(action_type, 0)

        # 4. تنظیم بر اساس وابستگی‌ها
        if dependencies:
            # اگر وابستگی داره، یکم اولویتش رو پایین‌تر ببر
            # چون اول باید وابستگی‌هاش انجام بشه
            priority = min(priority + 1, 10)

        # 5. بررسی context پاسخ AI
        if ai_response_context:
            ctx_lower = ai_response_context.lower()
            if "اولویت بالا" in ctx_lower or "high priority" in ctx_lower:
                priority = min(priority, 2)
            elif "اولویت پایین" in ctx_lower or "low priority" in ctx_lower:
                priority = max(priority, 7)

        # محدود کردن به بازه معتبر
        priority = max(1, min(10, priority))

        slog.debug("Priority calculated",
            field_name=name[:30],
            priority=priority
        )

        return priority

    def determine_roadmap_placement(
        self,
        item_text: str,
        item_type: str = "task"
    ) -> Dict[str, Any]:
        """
        📍 تعیین موقعیت مناسب در نقشه راه

        Returns:
            {
                "phase": str,  # فاز مناسب
                "position": int,  # شماره خط برای insert
                "format": str  # فرمت آیتم
            }
        """
        text_lower = item_text.lower()

        # تشخیص فاز مناسب
        phase_keywords = {
            "فاز 1": ["setup", "راه‌اندازی", "init", "شروع", "پایه"],
            "فاز 2": ["توسعه", "develop", "implement", "پیاده‌سازی", "کد"],
            "فاز 3": ["تست", "test", "بررسی", "review", "qa"],
            "فاز 4": ["بهینه‌سازی", "optimize", "refactor", "بهبود"],
            "فاز 5": ["مستند", "document", "deploy", "انتشار", "release"],
        }

        best_phase = "فاز 2"  # پیش‌فرض
        best_score = 0

        for phase, keywords in phase_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_phase = phase

        # پیدا کردن موقعیت در نقشه راه
        position = 0
        for item in self.roadmap_items:
            if item.get("phase") == best_phase:
                position = item.get("line_index", 0) + 1

        # اگر آیتمی در این فاز نبود، آخر نقشه راه اضافه کن
        if position == 0 and self.roadmap_items:
            position = self.roadmap_items[-1].get("line_index", 0) + 1

        return {
            "phase": best_phase,
            "position": position,
            "format": f"- [ ] {item_text}"
        }

    async def create_intelligent_field(
        self,
        name: str,
        value: str,
        source_prompt: str = "",
        ai_response_context: str = "",
        force_create: bool = False
    ) -> Dict[str, Any]:
        """
        🧠 ایجاد هوشمند فیلد با تمام بررسی‌ها

        Returns:
            {
                "success": bool,
                "action": "created" | "updated" | "skipped" | "merged",
                "field": {...},
                "existing_match": {...},
                "roadmap_item_added": bool,
                "message": str
            }
        """
        slog.start("Creating intelligent field",
            name=name[:50],
            force=force_create
        )

        result = {
            "success": False,
            "action": "skipped",
            "field": None,
            "existing_match": None,
            "roadmap_item_added": False,
            "message": ""
        }

        # بارگذاری context اگر نشده
        if not self.project:
            self.load_project_context()

        # 1. بررسی وجود قابلیت مشابه
        if not force_create:
            existing = self.check_existing_capability(f"{name} {value}")
            if existing["exists"] and existing["similarity"] > 0.7:
                result["existing_match"] = existing
                result["message"] = existing["suggestion"]
                slog.info("Skipped - similar capability exists",
                    type=existing["type"],
                    similarity=existing["similarity"]
                )
                return result

        # 2. ساخت فیلد پایه
        field = {
            "id": f"field_{uuid.uuid4().hex[:8]}",
            "name": name,
            "value": value,
            "target_models": ["all"],
            "action_type": "display",
            "trigger": {"enabled": False, "interval_minutes": 60, "interval_type": "minutes"},
            "field_type": "temporary",
            "archived": False,
            "archive_after_run": True,
            "created_at": datetime.utcnow().isoformat(),
            "source": "ai_query_intelligent",
            "source_prompt": source_prompt[:500] if source_prompt else None,
        }

        # 3. تشخیص نوع اکشن
        combined_text = f"{name} {value}".lower()
        if any(kw in combined_text for kw in ["باگ", "خطا", "bug", "error", "fix", "اصلاح"]):
            field["action_type"] = "github_commit"
        elif any(kw in combined_text for kw in ["چند فایل", "multi", "refactor", "بازنویسی"]):
            field["action_type"] = "github_multi_commit"

        # 4. استخراج مسیر فایل
        file_patterns = [
            r'(?:فایل|file|path|مسیر)[:\s]+[`"]?([^\s\n`"]+\.\w+)[`"]?',
            r'`([a-zA-Z0-9_/\\.-]+\.\w{2,4})`',
            r'([a-zA-Z0-9_/\\-]+/[a-zA-Z0-9_/\\-]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md))',
        ]
        for pattern in file_patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                field["target_path"] = match.group(1)
                break

        # اگر action کامیت ولی target_path نداریم
        if field["action_type"] in ["github_commit"] and not field.get("target_path"):
            field["action_type"] = "display"

        # 5. تحلیل وابستگی‌ها
        dependencies = self.analyze_dependencies(value, self.existing_fields)
        if dependencies:
            field["depends_on"] = dependencies

        # 6. محاسبه اولویت
        field["priority"] = self.calculate_priority(field, ai_response_context, dependencies)

        # 7. ذخیره فیلد
        if self.project:
            all_fields = self.existing_fields.copy()
            all_fields.append(field)

            # مرتب‌سازی بر اساس اولویت
            active_fields = [f for f in all_fields if not f.get("archived")]
            archived_fields = [f for f in all_fields if f.get("archived")]
            active_fields.sort(key=lambda x: int(x.get("priority", 5)))
            all_fields = active_fields + archived_fields

            self.project.dynamic_fields = json.dumps(all_fields, ensure_ascii=False)

            # 8. بررسی اضافه کردن به نقشه راه
            roadmap_added = False
            roadmap_keywords = ["feature", "ویژگی", "قابلیت", "milestone", "مرحله", "فاز"]
            if any(kw in combined_text for kw in roadmap_keywords):
                placement = self.determine_roadmap_placement(name)
                roadmap_added = self._add_to_roadmap(name, placement)

            if self.db:
                self.db.commit()

            result["success"] = True
            result["action"] = "created"
            result["field"] = field
            result["roadmap_item_added"] = roadmap_added
            result["message"] = f"فیلد '{name}' با اولویت {field['priority']} ایجاد شد"

            if dependencies:
                result["message"] += f" (وابسته به {len(dependencies)} فیلد)"
            if roadmap_added:
                result["message"] += " + به نقشه راه اضافه شد"

        slog.end("Intelligent field creation",
            success=result["success"],
            field_action=result["action"],
            priority=field.get("priority"),
            dependencies=len(dependencies) if dependencies else 0
        )

        return result

    def _add_to_roadmap(self, item_text: str, placement: Dict) -> bool:
        """اضافه کردن آیتم به نقشه راه"""
        if not self.project:
            return False

        try:
            roadmap = self.project.roadmap_content or ""
            lines = roadmap.split('\n')

            # پیدا کردن یا ایجاد فاز
            phase = placement.get("phase", "فاز 2")
            phase_exists = False

            for i, line in enumerate(lines):
                if phase in line:
                    phase_exists = True
                    # پیدا کردن آخرین آیتم این فاز
                    insert_pos = i + 1
                    while insert_pos < len(lines):
                        next_line = lines[insert_pos].strip()
                        if next_line.startswith('##'):
                            break
                        if next_line.startswith(('- ', '* ')):
                            insert_pos += 1
                        else:
                            insert_pos += 1
                            if not next_line:
                                break

                    # اضافه کردن آیتم
                    new_item = f"- [ ] {item_text}"
                    lines.insert(insert_pos, new_item)
                    break

            # اگر فاز وجود نداشت، در انتها اضافه کن
            if not phase_exists:
                lines.append(f"\n## {phase}")
                lines.append(f"- [ ] {item_text}")

            self.project.roadmap_content = '\n'.join(lines)

            slog.info("Added to roadmap",
                item=item_text[:50],
                phase=phase
            )
            return True

        except Exception as e:
            slog.error("Failed to add to roadmap", exception=e)
            return False


def get_intelligent_field_creator(project_id: str, db_session=None) -> IntelligentFieldCreator:
    """دریافت instance از سرویس"""
    creator = IntelligentFieldCreator(project_id, db_session)
    creator.load_project_context()
    return creator
