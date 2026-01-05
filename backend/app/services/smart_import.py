"""
🔍 Smart Import Service - تحلیل و وارد کردن هوشمند فایل‌ها
سیستم بررسی، تحلیل و دسته‌بندی خودکار فایل‌ها و کدها
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ImportDecision(str, Enum):
    """تصمیم نهایی درباره فایل"""
    INTEGRATE = "integrate"  # ادغام در پروژه
    MODIFY_AND_INTEGRATE = "modify_and_integrate"  # اصلاح و ادغام
    ARCHIVE = "archive"  # بایگانی (بی‌ربط)
    NEEDS_REVIEW = "needs_review"  # نیاز به بررسی انسانی


@dataclass
class FileAnalysisResult:
    """نتیجه تحلیل فایل"""
    file_name: str
    file_type: str
    decision: ImportDecision
    relevance_score: int  # 0-100
    target_phase: Optional[str] = None
    target_folder: Optional[str] = None
    suggested_path: Optional[str] = None
    modifications_needed: List[str] = field(default_factory=list)
    modified_content: Optional[str] = None
    analysis_summary: str = ""
    warnings: List[str] = field(default_factory=list)
    model_votes: Dict[str, Dict] = field(default_factory=dict)  # هر مدل چی گفته
    consensus: bool = False  # آیا مدل‌ها توافق دارند


class SmartImportService:
    """
    سرویس وارد کردن هوشمند فایل‌ها

    قابلیت‌ها:
    - تحلیل فایل توسط چند مدل نخبه
    - تشخیص ارتباط با فازهای پروژه
    - اعتبارسنجی کد
    - اصلاح خودکار در صورت نیاز
    - انتقال به پوشه مناسب
    - بروزرسانی پیشرفت پروژه
    """

    def __init__(self):
        self.ai_manager = None
        self.project_service = None
        self.github_storage = None
        self.orchestrator = None
        self._sync_interval = 300  # 5 دقیقه
        self._sync_task = None
        self._processed_files: Dict[str, List[str]] = {}  # project_id -> list of processed file paths

    def initialize(self, ai_manager, project_service, github_storage, orchestrator=None):
        """مقداردهی اولیه"""
        self.ai_manager = ai_manager
        self.project_service = project_service
        self.github_storage = github_storage
        self.orchestrator = orchestrator
        logger.info("SmartImportService initialized")

    def is_initialized(self) -> bool:
        return self.ai_manager is not None and self.project_service is not None

    async def analyze_and_import_file(
        self,
        project_id: str,
        file_content: bytes,
        file_name: str,
        user_prompt: Optional[str] = None,
        auto_apply: bool = True
    ) -> Dict:
        """
        تحلیل فایل و وارد کردن به پروژه

        Args:
            project_id: شناسه پروژه
            file_content: محتوای فایل
            file_name: نام فایل
            user_prompt: توضیحات اختیاری کاربر
            auto_apply: اعمال خودکار تغییرات
        """
        if not self.is_initialized():
            return {"success": False, "error": "سرویس مقداردهی نشده"}

        # دریافت اطلاعات پروژه
        project_data = self.project_service.get_project(project_id)
        if not project_data.get("success"):
            return {"success": False, "error": "پروژه یافت نشد"}

        project = project_data["project"]

        # تبدیل محتوا به متن
        try:
            content_text = file_content.decode('utf-8')
        except:
            content_text = file_content.decode('latin-1', errors='replace')

        # تحلیل با چند مدل نخبه
        analysis = await self._analyze_with_elite_models(
            project=project,
            file_name=file_name,
            content=content_text,
            user_prompt=user_prompt
        )

        result = {
            "success": True,
            "project_id": project_id,
            "file_name": file_name,
            "analysis": analysis.__dict__ if isinstance(analysis, FileAnalysisResult) else analysis
        }

        # اگر auto_apply فعال است و تصمیم ادغام است
        if auto_apply and analysis.decision in [ImportDecision.INTEGRATE, ImportDecision.MODIFY_AND_INTEGRATE]:
            apply_result = await self._apply_import_decision(
                project_id=project_id,
                file_name=file_name,
                content=analysis.modified_content or content_text,
                analysis=analysis
            )
            result["applied"] = apply_result

        return result

    async def _analyze_with_elite_models(
        self,
        project: Dict,
        file_name: str,
        content: str,
        user_prompt: Optional[str] = None
    ) -> FileAnalysisResult:
        """تحلیل فایل با چند مدل نخبه"""

        from .ai_base import Message

        # ساخت پرامپت تحلیل
        analysis_prompt = self._build_analysis_prompt(project, file_name, content, user_prompt)

        # مدل‌های نخبه برای تحلیل
        elite_models = [
            "claude-3-5-sonnet-20241022",
            "gpt-4o",
            "deepseek-chat"
        ]

        # اجرای موازی تحلیل با هر مدل
        tasks = []
        for model_id in elite_models:
            task = self._analyze_with_model(model_id, analysis_prompt)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # جمع‌آوری و ترکیب نتایج
        model_votes = {}
        for model_id, result in zip(elite_models, results):
            if isinstance(result, Exception):
                logger.warning(f"Model {model_id} failed: {result}")
                continue
            if result:
                model_votes[model_id] = result

        # تصمیم‌گیری نهایی بر اساس اجماع
        final_analysis = self._aggregate_analysis(file_name, content, model_votes)

        return final_analysis

    def _build_analysis_prompt(
        self,
        project: Dict,
        file_name: str,
        content: str,
        user_prompt: Optional[str] = None
    ) -> str:
        """ساخت پرامپت تحلیل"""

        phases_info = ""
        for i, phase in enumerate(project.get("phases", [])):
            status = phase.get("status", "pending")
            steps = ", ".join(phase.get("steps", []))
            phases_info += f"\n{i+1}. {phase.get('name')} [{status}]: {steps}"

        prompt = f"""
تو یک تحلیلگر کد نخبه هستی. یک فایل به پروژه زیر اضافه شده و باید بررسی کنی:

📁 پروژه: {project.get('name')}
📝 توضیحات: {project.get('description', '')}
🎯 هدف: {project.get('goal', '')}
📊 نوع: {project.get('project_type', 'custom')}

📋 فازها و مراحل:
{phases_info}

---

📄 فایل جدید: {file_name}

محتوای فایل:
```
{content[:8000]}
```

{"📌 توضیحات کاربر: " + user_prompt if user_prompt else ""}

---

وظیفه تو:
1. بررسی کن این فایل به کدام فاز و مرحله پروژه مربوط می‌شود
2. کیفیت کد را ارزیابی کن (اگر کد است)
3. مشخص کن آیا نیاز به اصلاح دارد یا نه
4. پیشنهاد بده در کجای پروژه قرار بگیرد
5. اگر بی‌ربط است، دلیلش را بگو

پاسخ را به صورت JSON بده:
{{
    "decision": "integrate" | "modify_and_integrate" | "archive" | "needs_review",
    "relevance_score": 0-100,
    "target_phase": "نام فاز مرتبط یا null",
    "target_folder": "generated" | "source" | "docs" | "tests",
    "suggested_path": "مسیر پیشنهادی مثل src/components/Button.tsx",
    "modifications_needed": ["لیست اصلاحات مورد نیاز"],
    "modified_content": "محتوای اصلاح شده (اگر نیاز است) یا null",
    "analysis_summary": "خلاصه تحلیل به فارسی",
    "warnings": ["هشدارها و نکات"],
    "quality_score": 0-100,
    "code_issues": ["مشکلات کد"]
}}
"""
        return prompt

    async def _analyze_with_model(self, model_id: str, prompt: str) -> Optional[Dict]:
        """تحلیل با یک مدل خاص"""
        try:
            from .ai_base import Message

            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000,
                temperature=0.3
            )

            if response.content and not response.error:
                # استخراج JSON از پاسخ
                return self._extract_json(response.content)

        except Exception as e:
            logger.error(f"Error analyzing with {model_id}: {e}")

        return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """استخراج JSON از متن"""
        import re

        # حذف backticks
        cleaned = text.replace('```json', '').replace('```', '').strip()

        # پیدا کردن JSON
        try:
            # اول سعی کن مستقیم parse کنی
            return json.loads(cleaned)
        except:
            pass

        # پیدا کردن با regex
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass

        return None

    def _aggregate_analysis(
        self,
        file_name: str,
        content: str,
        model_votes: Dict[str, Dict]
    ) -> FileAnalysisResult:
        """ترکیب نتایج مدل‌ها و تصمیم نهایی"""

        if not model_votes:
            return FileAnalysisResult(
                file_name=file_name,
                file_type=self._get_file_type(file_name),
                decision=ImportDecision.NEEDS_REVIEW,
                relevance_score=0,
                analysis_summary="هیچ مدلی نتوانست تحلیل کند",
                model_votes={}
            )

        # شمارش رأی‌ها
        decisions = {}
        relevance_scores = []
        target_phases = {}
        target_folders = {}
        all_modifications = []
        all_warnings = []
        summaries = []

        for model_id, vote in model_votes.items():
            decision = vote.get("decision", "needs_review")
            decisions[decision] = decisions.get(decision, 0) + 1

            relevance_scores.append(vote.get("relevance_score", 50))

            if vote.get("target_phase"):
                tp = vote["target_phase"]
                target_phases[tp] = target_phases.get(tp, 0) + 1

            if vote.get("target_folder"):
                tf = vote["target_folder"]
                target_folders[tf] = target_folders.get(tf, 0) + 1

            all_modifications.extend(vote.get("modifications_needed", []))
            all_warnings.extend(vote.get("warnings", []))

            if vote.get("analysis_summary"):
                summaries.append(vote["analysis_summary"])

        # تصمیم نهایی بر اساس اکثریت
        final_decision = max(decisions, key=decisions.get)
        avg_relevance = sum(relevance_scores) // len(relevance_scores)

        # فاز و پوشه هدف
        target_phase = max(target_phases, key=target_phases.get) if target_phases else None
        target_folder = max(target_folders, key=target_folders.get) if target_folders else "generated"

        # اگر نیاز به اصلاح است، محتوای اصلاح شده را از اولین مدل بگیر
        modified_content = None
        if final_decision == "modify_and_integrate":
            for vote in model_votes.values():
                if vote.get("modified_content"):
                    modified_content = vote["modified_content"]
                    break

        # مسیر پیشنهادی
        suggested_path = None
        for vote in model_votes.values():
            if vote.get("suggested_path"):
                suggested_path = vote["suggested_path"]
                break

        # آیا اجماع وجود دارد؟
        consensus = decisions.get(final_decision, 0) >= len(model_votes) * 0.6

        return FileAnalysisResult(
            file_name=file_name,
            file_type=self._get_file_type(file_name),
            decision=ImportDecision(final_decision),
            relevance_score=avg_relevance,
            target_phase=target_phase,
            target_folder=target_folder,
            suggested_path=suggested_path,
            modifications_needed=list(set(all_modifications)),
            modified_content=modified_content,
            analysis_summary=" | ".join(summaries[:2]) if summaries else "",
            warnings=list(set(all_warnings)),
            model_votes=model_votes,
            consensus=consensus
        )

    def _get_file_type(self, file_name: str) -> str:
        """تشخیص نوع فایل"""
        ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''

        type_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript_react',
            'jsx': 'javascript_react',
            'json': 'json',
            'md': 'markdown',
            'html': 'html',
            'css': 'css',
            'sql': 'sql',
            'yaml': 'yaml',
            'yml': 'yaml',
            'sh': 'shell',
            'dockerfile': 'docker',
        }

        return type_map.get(ext, 'unknown')

    async def _apply_import_decision(
        self,
        project_id: str,
        file_name: str,
        content: str,
        analysis: FileAnalysisResult
    ) -> Dict:
        """اعمال تصمیم و انتقال فایل"""

        try:
            # تعیین مسیر نهایی
            final_path = analysis.suggested_path or file_name
            folder = analysis.target_folder or "generated"

            # ذخیره در GitHub
            if self.github_storage:
                result = await self.github_storage.save_project_file(
                    project_id,
                    content.encode('utf-8'),
                    final_path,
                    folder
                )

                if not result.get("success"):
                    return {"success": False, "error": "خطا در ذخیره فایل"}

            # بروزرسانی پیشرفت پروژه اگر فاز مشخص است
            if analysis.target_phase:
                await self._update_project_progress(project_id, analysis.target_phase)

            return {
                "success": True,
                "saved_path": f"{folder}/{final_path}",
                "github_url": result.get("url") if self.github_storage else None
            }

        except Exception as e:
            logger.error(f"Error applying import decision: {e}")
            return {"success": False, "error": str(e)}

    async def _update_project_progress(self, project_id: str, phase_name: str):
        """بروزرسانی پیشرفت پروژه"""
        try:
            project_data = self.project_service.get_project(project_id)
            if not project_data.get("success"):
                return

            project = project_data["project"]

            # پیدا کردن فاز مربوطه
            for phase in project.get("phases", []):
                if phase.get("name") == phase_name:
                    # افزایش پیشرفت
                    current_progress = phase.get("progress", 0)
                    new_progress = min(100, current_progress + 10)

                    self.project_service.update_phase_progress(
                        project_id,
                        new_progress
                    )
                    break

        except Exception as e:
            logger.warning(f"Error updating project progress: {e}")

    # =====================================
    # GitHub Sync
    # =====================================

    async def start_github_sync(self, interval: int = 300):
        """شروع sync دوره‌ای با GitHub"""
        self._sync_interval = interval
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info(f"GitHub sync started with interval {interval}s")

    async def stop_github_sync(self):
        """توقف sync"""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None
        logger.info("GitHub sync stopped")

    async def _sync_loop(self):
        """حلقه sync دوره‌ای"""
        while True:
            try:
                await self.sync_all_projects()
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")

            await asyncio.sleep(self._sync_interval)

    async def sync_all_projects(self) -> Dict:
        """بررسی همه پروژه‌ها برای فایل‌های جدید"""
        if not self.github_storage:
            return {"success": False, "error": "GitHub storage not configured"}

        results = []

        # دریافت لیست پروژه‌ها
        projects = self.project_service.list_projects()

        for project_info in projects.get("projects", []):
            project_id = project_info["project_id"]

            try:
                sync_result = await self.sync_project(project_id)
                results.append({
                    "project_id": project_id,
                    "result": sync_result
                })
            except Exception as e:
                logger.error(f"Error syncing project {project_id}: {e}")
                results.append({
                    "project_id": project_id,
                    "error": str(e)
                })

        return {
            "success": True,
            "synced_at": datetime.now().isoformat(),
            "results": results
        }

    async def sync_project(self, project_id: str) -> Dict:
        """بررسی یک پروژه برای فایل‌های جدید"""

        new_files_found = []
        processed = []

        # دریافت فایل‌های موجود در پروژه
        project_files = await self.github_storage.get_project_files(project_id)

        # بررسی همه پوشه‌ها
        for folder_type, files in project_files.get("files", {}).items():
            for file_info in files:
                file_path = f"{folder_type}/{file_info['name']}"

                # آیا قبلا پردازش شده؟
                if project_id not in self._processed_files:
                    self._processed_files[project_id] = []

                if file_path in self._processed_files[project_id]:
                    continue

                # اگر در پوشه pending یا inbox است، پردازش کن
                if folder_type in ["pending", "inbox", "imports"]:
                    new_files_found.append(file_info)

                    # دانلود و تحلیل
                    content = await self.github_storage.download_file(
                        f"projects/{project_id}/{file_path}"
                    )

                    if content:
                        result = await self.analyze_and_import_file(
                            project_id=project_id,
                            file_content=content,
                            file_name=file_info['name'],
                            auto_apply=True
                        )
                        processed.append({
                            "file": file_info['name'],
                            "result": result
                        })

                # علامت‌گذاری به عنوان پردازش شده
                self._processed_files[project_id].append(file_path)

        return {
            "new_files_found": len(new_files_found),
            "processed": processed
        }

    async def process_file_from_github(
        self,
        project_id: str,
        file_path: str,
        user_prompt: Optional[str] = None
    ) -> Dict:
        """پردازش یک فایل مشخص از GitHub"""

        if not self.github_storage:
            return {"success": False, "error": "GitHub storage not configured"}

        # دانلود فایل
        content = await self.github_storage.download_file(
            f"projects/{project_id}/{file_path}"
        )

        if not content:
            return {"success": False, "error": "فایل یافت نشد"}

        # استخراج نام فایل
        file_name = file_path.rsplit('/', 1)[-1]

        # تحلیل و وارد کردن
        return await self.analyze_and_import_file(
            project_id=project_id,
            file_content=content,
            file_name=file_name,
            user_prompt=user_prompt,
            auto_apply=True
        )


# Singleton
_smart_import_service: Optional[SmartImportService] = None


def get_smart_import_service() -> SmartImportService:
    global _smart_import_service
    if _smart_import_service is None:
        _smart_import_service = SmartImportService()
    return _smart_import_service
