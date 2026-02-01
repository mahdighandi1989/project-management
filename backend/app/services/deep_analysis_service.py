# -*- coding: utf-8 -*-
"""
سرویس تحلیل عمیق پروژه - Deep Analysis Service
تحلیل سه‌مرحله‌ای: Micro, Macro, Structural

این سرویس هسته اصلی سیستم تحلیل سلامت پروژه است و:
1. هر فایل را به صورت جداگانه و کامل بررسی می‌کند (Micro)
2. همکاری و جایگاه فایل‌ها را بررسی می‌کند (Macro)
3. سیم‌کشی و ساختار کلی را تحلیل می‌کند (Structural)
"""

import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
import time
import logging
import re
import os

from .ai_base import Message

logger = logging.getLogger(__name__)


# =====================================
# کلاس رصد پیشرفت (Progress Tracker)
# =====================================

class AnalysisProgressTracker:
    """
    رصد و گزارش پیشرفت تحلیل در لحظه

    این کلاس اطلاعات پیشرفت را به callback ارسال می‌کند
    برای استفاده در API streaming
    """

    def __init__(self, callback: Optional[Callable[[Dict], None]] = None):
        self.callback = callback
        self.analysis_id = ""
        self.phase = "preparing"
        self.total_files = 0
        self.analyzed_files = 0
        self.total_models = 0
        self.current_file = ""
        self.current_model = ""
        self.model_statuses: Dict[str, str] = {}  # model_id -> status
        self.start_time = time.time()
        self.file_times: Dict[str, float] = {}
        self.issues_found = 0
        self.last_message = ""
        self._lock = asyncio.Lock()

    async def emit(self, event_type: str, data: Dict = None):
        """ارسال رویداد پیشرفت"""
        if not self.callback:
            return

        async with self._lock:
            progress_data = {
                "event": event_type,
                "analysis_id": self.analysis_id,
                "phase": self.phase,
                "total_files": self.total_files,
                "analyzed_files": self.analyzed_files,
                "total_models": self.total_models,
                "current_file": self.current_file,
                "current_model": self.current_model,
                "model_statuses": self.model_statuses.copy(),
                "elapsed_time": round(time.time() - self.start_time, 1),
                "issues_found": self.issues_found,
                "progress_percentage": self._calculate_progress(),
                "message": self.last_message,
                "timestamp": datetime.now().isoformat(),
                **(data or {})
            }

            try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(progress_data)
                else:
                    self.callback(progress_data)
            except Exception as e:
                logger.warning(f"Error in progress callback: {e}")

    def _calculate_progress(self) -> float:
        """محاسبه درصد پیشرفت"""
        if self.total_files == 0:
            return 0

        # وزن‌دهی به فازها
        phase_weights = {
            "preparing": 0,
            "micro": 60,  # 60% زمان برای micro
            "macro": 20,  # 20% برای macro
            "structural": 15,  # 15% برای structural
            "finalizing": 5,  # 5% برای نهایی‌سازی
            "completed": 100
        }

        base = 0
        if self.phase == "micro":
            file_progress = (self.analyzed_files / self.total_files) * 60
            return file_progress
        elif self.phase == "macro":
            return 60 + (20 * 0.5)  # نیمه راه macro
        elif self.phase == "structural":
            return 80 + (15 * 0.5)  # نیمه راه structural
        elif self.phase == "finalizing":
            return 95
        elif self.phase == "completed":
            return 100

        return 0

    async def start_analysis(self, analysis_id: str, total_files: int, model_ids: List[str]):
        """شروع تحلیل"""
        self.analysis_id = analysis_id
        self.total_files = total_files
        self.total_models = len(model_ids)
        self.phase = "preparing"
        self.start_time = time.time()
        self.model_statuses = {m: "waiting" for m in model_ids}
        self.last_message = f"شروع تحلیل {total_files} فایل با {len(model_ids)} مدل"
        await self.emit("analysis_started")

    async def start_phase(self, phase: str, message: str = ""):
        """شروع فاز جدید"""
        self.phase = phase
        self.last_message = message or f"فاز {phase} شروع شد"
        await self.emit("phase_started", {"phase_name": phase})

    async def start_file(self, file_path: str):
        """شروع تحلیل فایل"""
        self.current_file = file_path
        self.file_times[file_path] = time.time()
        self.last_message = f"شروع تحلیل: {os.path.basename(file_path)}"
        await self.emit("file_started", {"file_path": file_path})

    async def start_model(self, model_id: str, file_path: str = None):
        """شروع کار مدل"""
        self.current_model = model_id
        self.model_statuses[model_id] = "working"
        self.last_message = f"مدل {model_id} در حال کار..."
        await self.emit("model_started", {"model_id": model_id, "file_path": file_path})

    async def complete_model(self, model_id: str, success: bool = True, message: str = ""):
        """اتمام کار مدل"""
        self.model_statuses[model_id] = "completed" if success else "failed"
        self.last_message = message or f"مدل {model_id} {'تکمیل' if success else 'خطا'}"
        await self.emit("model_completed", {
            "model_id": model_id,
            "success": success,
            "message": message
        })

    async def complete_file(self, file_path: str, issues: int = 0, score: float = 0):
        """اتمام تحلیل فایل"""
        self.analyzed_files += 1
        self.issues_found += issues
        elapsed = time.time() - self.file_times.get(file_path, time.time())
        self.last_message = f"فایل {os.path.basename(file_path)} تکمیل (نمره: {score:.0f})"
        await self.emit("file_completed", {
            "file_path": file_path,
            "issues": issues,
            "score": score,
            "file_time": round(elapsed, 1)
        })

    async def complete_analysis(self, overall_score: float = 0, total_issues: int = 0):
        """اتمام تحلیل"""
        self.phase = "completed"
        elapsed = time.time() - self.start_time
        self.last_message = f"تحلیل کامل شد! نمره: {overall_score:.0f}"
        await self.emit("analysis_completed", {
            "overall_score": overall_score,
            "total_issues": total_issues,
            "total_time": round(elapsed, 1)
        })


# =====================================
# ثابت‌ها و تنظیمات
# =====================================

# فاکتورهای بررسی و وزن‌های پیش‌فرض
DEFAULT_ANALYSIS_FACTORS = {
    "roadmap_compliance": {"weight": 0.15, "label": "تطابق با نقشه‌راه"},
    "code_quality": {"weight": 0.20, "label": "کیفیت کد"},
    "position_appropriateness": {"weight": 0.15, "label": "مناسب بودن جایگاه"},
    "wiring_correctness": {"weight": 0.15, "label": "صحت سیم‌کشی"},
    "completeness": {"weight": 0.10, "label": "کامل بودن"},
    "efficiency": {"weight": 0.10, "label": "کارایی"},
    "documentation": {"weight": 0.10, "label": "مستندسازی"},
    "standards_compliance": {"weight": 0.05, "label": "انطباق با استانداردها"},
}

# رنگ‌بندی بر اساس نمره
def get_health_color(score: float) -> Dict[str, str]:
    """محاسبه رنگ بر اساس نمره سلامت (0-100)"""
    if score >= 90:
        return {"color": "green", "hex": "#22c55e", "label": "عالی"}
    elif score >= 75:
        return {"color": "lime", "hex": "#84cc16", "label": "خوب"}
    elif score >= 60:
        return {"color": "yellow", "hex": "#eab308", "label": "متوسط"}
    elif score >= 40:
        return {"color": "orange", "hex": "#f97316", "label": "ضعیف"}
    elif score >= 20:
        return {"color": "red", "hex": "#ef4444", "label": "بد"}
    else:
        return {"color": "darkred", "hex": "#991b1b", "label": "بحرانی"}


# =====================================
# کلاس تحلیل‌گر عمیق
# =====================================

class DeepAnalysisService:
    """
    سرویس تحلیل عمیق پروژه

    این سرویس سه مرحله تحلیل را انجام می‌دهد:
    1. Micro Analysis: بررسی تک‌تک فایل‌ها
    2. Macro Analysis: بررسی همکاری و جایگاه
    3. Structural Analysis: بررسی سیم‌کشی و ساختار
    """

    def __init__(self, ai_manager=None, progress_callback: Optional[Callable[[Dict], None]] = None):
        """
        مقداردهی اولیه

        Args:
            ai_manager: مدیر مدل‌های AI (برای فراخوانی مدل‌ها)
            progress_callback: callback برای گزارش پیشرفت (برای streaming)
        """
        self.ai_manager = ai_manager
        self.analysis_factors = DEFAULT_ANALYSIS_FACTORS.copy()
        self.progress = AnalysisProgressTracker(progress_callback)

    async def run_full_analysis(
        self,
        project_id: str,
        files: List[Dict],
        roadmap_content: str = "",
        readme_content: str = "",
        model_ids: List[str] = None,
        instruction: str = "",
        db_session=None,
        progress_manager=None,
        depth: str = "standard"  # 🆕 quick, standard, deep, thorough
    ) -> Dict[str, Any]:
        """
        اجرای تحلیل کامل سه‌مرحله‌ای

        Args:
            project_id: شناسه پروژه
            files: لیست فایل‌های پروژه
            roadmap_content: محتوای فایل Roadmap
            readme_content: محتوای فایل README
            model_ids: لیست مدل‌های AI برای تحلیل
            instruction: دستورات اضافی
            db_session: session دیتابیس
            progress_manager: مدیر پیشرفت برای ذخیره وضعیت و pause/resume/stop
            depth: عمق تحلیل (quick, standard, deep, thorough)

        Returns:
            نتایج کامل تحلیل
        """
        self._progress_manager = progress_manager

        # 🆕 تنظیمات عمق تحلیل
        depth_config = {
            "quick": {
                "batch_size": 10,       # بزرگتر = سریعتر
                "batch_delay": 0,       # بدون تاخیر
                "max_files": 30,        # حداکثر فایل
                "content_limit": 5000,  # محدودیت محتوا
                "models_limit": 1,      # فقط یک مدل
                "prompt_detail": "minimal",
                "skip_macro": False,
                "skip_structural": True,
            },
            "standard": {
                "batch_size": 5,
                "batch_delay": 0.5,
                "max_files": 100,
                "content_limit": 10000,
                "models_limit": 2,
                "prompt_detail": "standard",
                "skip_macro": False,
                "skip_structural": False,
            },
            "deep": {
                "batch_size": 2,        # کوچکتر = دقیق‌تر
                "batch_delay": 1.0,     # تاخیر برای جلوگیری از rate limit
                "max_files": 500,
                "content_limit": 15000,
                "models_limit": 3,
                "prompt_detail": "detailed",
                "skip_macro": False,
                "skip_structural": False,
            },
            "thorough": {
                "batch_size": 1,        # هر فایل جداگانه
                "batch_delay": 2.0,     # تاخیر بیشتر
                "max_files": 1000,
                "content_limit": 20000,
                "models_limit": None,   # همه مدل‌ها
                "prompt_detail": "comprehensive",
                "skip_macro": False,
                "skip_structural": False,
            }
        }

        self._depth_config = depth_config.get(depth, depth_config["standard"])
        logger.info(f"🔬 Analysis depth: {depth} - config: {self._depth_config}")
        analysis_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        start_time_unix = time.time()

        logger.info(f"=" * 60)
        logger.info(f"🔬 [{analysis_id}] STARTING DEEP ANALYSIS for project {project_id}")
        logger.info(f"📁 [{analysis_id}] Files count: {len(files)}")
        logger.info(f"🤖 [{analysis_id}] AI Manager available: {self.ai_manager is not None}")

        if self.ai_manager:
            try:
                available = self.ai_manager.get_available_models(task_type="analysis")
                providers = self.ai_manager.get_available_providers()
                logger.info(f"🤖 [{analysis_id}] Available providers: {providers}")
                logger.info(f"🤖 [{analysis_id}] Available models (for analysis): {[m.id for m in available]}")
            except Exception as e:
                logger.error(f"❌ [{analysis_id}] Error getting models: {e}")
        else:
            logger.error(f"❌ [{analysis_id}] AI Manager is None! Analysis will return empty results!")

        # اگر مدل مشخص نشده، از مدل‌های پیش‌فرض استفاده کن
        if not model_ids:
            model_ids = await self._get_available_models()

        logger.info(f"🤖 [{analysis_id}] Models to use: {model_ids}")

        # شروع رصد پیشرفت
        await self.progress.start_analysis(analysis_id, len(files), model_ids)

        results = {
            "analysis_id": analysis_id,
            "project_id": project_id,
            "started_at": start_time.isoformat(),
            "models_used": model_ids,
            "instruction": instruction,

            # نتایج هر مرحله
            "micro_analysis": {},
            "macro_analysis": {},
            "structural_analysis": {},

            # نتایج نهایی
            "file_health_map": {},
            "overall_scores": {},
            "issues": [],
            "recommendations": [],
            "ideal_state": "",

            # متادیتا
            "total_files": len(files),
            "analyzed_files": 0,
            "status": "running"
        }

        try:
            # =====================================
            # مرحله 1: Micro Analysis (بررسی جزئی)
            # =====================================
            logger.info(f"[{analysis_id}] مرحله 1: شروع Micro Analysis")
            await self.progress.start_phase("micro", "بررسی جزئی فایل‌ها (Micro Analysis)")

            micro_results = await self._run_micro_analysis(
                files=files,
                roadmap_content=roadmap_content,
                model_ids=model_ids,
                instruction=instruction
            )
            results["micro_analysis"] = micro_results
            results["analyzed_files"] = len(micro_results.get("files", {}))

            # =====================================
            # مرحله 2: Macro Analysis (بررسی کلی)
            # =====================================
            logger.info(f"[{analysis_id}] مرحله 2: شروع Macro Analysis")
            await self.progress.start_phase("macro", "بررسی همکاری و جایگاه (Macro Analysis)")

            macro_results = await self._run_macro_analysis(
                files=files,
                micro_results=micro_results,
                roadmap_content=roadmap_content,
                readme_content=readme_content,
                model_ids=model_ids,
                instruction=instruction
            )
            results["macro_analysis"] = macro_results

            # =====================================
            # مرحله 3: Structural Analysis (بررسی ساختاری)
            # =====================================
            logger.info(f"[{analysis_id}] مرحله 3: شروع Structural Analysis")
            await self.progress.start_phase("structural", "بررسی ساختار و وابستگی‌ها (Structural Analysis)")

            structural_results = await self._run_structural_analysis(
                files=files,
                micro_results=micro_results,
                macro_results=macro_results,
                roadmap_content=roadmap_content,
                model_ids=model_ids,
                instruction=instruction
            )
            results["structural_analysis"] = structural_results

            # =====================================
            # محاسبه نتایج نهایی
            # =====================================
            logger.info(f"[{analysis_id}] محاسبه نتایج نهایی")
            await self.progress.start_phase("finalizing", "محاسبه نتایج نهایی")

            # ترکیب نتایج و محاسبه نمرات نهایی
            final_results = self._calculate_final_results(
                micro_results=micro_results,
                macro_results=macro_results,
                structural_results=structural_results,
                model_ids=model_ids
            )

            results["file_health_map"] = final_results["file_health_map"]
            results["overall_scores"] = final_results["overall_scores"]
            results["issues"] = final_results["issues"]
            results["recommendations"] = final_results["recommendations"]
            results["ideal_state"] = final_results["ideal_state"]

            results["status"] = "completed"
            results["completed_at"] = datetime.now().isoformat()

            # ذخیره در دیتابیس
            if db_session:
                await self._save_analysis_results(project_id, results, db_session)

            # ⭐ به‌روزرسانی پروفایل مدل‌ها
            await self._update_model_profiles(
                model_ids=model_ids,
                micro_results=micro_results,
                analysis_id=analysis_id,
                total_issues=len(final_results.get("issues", []))
            )

            elapsed_total = time.time() - start_time_unix
            logger.info(f"=" * 60)
            logger.info(f"✅ [{analysis_id}] ANALYSIS COMPLETE in {elapsed_total:.2f}s")
            logger.info(f"📊 [{analysis_id}] Overall score: {final_results['overall_scores'].get('total', 0):.1f}")
            logger.info(f"📊 [{analysis_id}] Files analyzed: {results['analyzed_files']}")
            logger.info(f"📊 [{analysis_id}] Issues found: {len(final_results.get('issues', []))}")
            logger.info(f"=" * 60)

            # گزارش اتمام تحلیل
            await self.progress.complete_analysis(
                overall_score=final_results['overall_scores'].get('total', 0),
                total_issues=len(final_results.get('issues', []))
            )

        except Exception as e:
            elapsed_total = time.time() - start_time_unix
            logger.error(f"❌ [{analysis_id}] ANALYSIS FAILED after {elapsed_total:.2f}s: {str(e)}", exc_info=True)
            results["status"] = "failed"
            results["error"] = str(e)

        return results

    # =====================================
    # مرحله 1: Micro Analysis
    # =====================================

    async def _run_micro_analysis(
        self,
        files: List[Dict],
        roadmap_content: str,
        model_ids: List[str],
        instruction: str
    ) -> Dict[str, Any]:
        """
        بررسی جزئی (Micro): هر فایل به صورت جداگانه

        - بررسی تک‌تک فایل‌ها
        - تحلیل تمام خطوط کد
        - بررسی جزئیات کامل
        - پشتیبانی از pause/resume/stop
        """
        start_time = time.time()
        logger.info(f"🔍 [MICRO ANALYSIS] Starting with {len(files)} files and {len(model_ids)} models")
        logger.info(f"🔍 [MICRO ANALYSIS] Models: {model_ids}")

        results = {
            "files": {},
            "summary": {
                "total_files": len(files),
                "analyzed": 0,
                "issues_found": 0
            }
        }

        # آماده‌سازی لیست فایل‌ها
        files_to_analyze = []
        skipped_files = []
        for file_data in files:
            file_path = file_data.get("path", file_data.get("file_path", ""))
            content = file_data.get("content", "")

            if not content or len(content) < 10:
                skipped_files.append(file_path)
                continue

            files_to_analyze.append({
                "file_path": file_path,
                "content": content
            })

        logger.info(f"🔍 [MICRO ANALYSIS] {len(files_to_analyze)} files to analyze, {len(skipped_files)} skipped")

        if skipped_files and len(skipped_files) <= 10:
            logger.info(f"🔍 [MICRO ANALYSIS] Skipped files: {skipped_files}")

        # تحلیل فایل‌ها (با پشتیبانی pause/stop)
        # استفاده از تنظیمات عمق تحلیل
        batch_size = getattr(self, '_depth_config', {}).get('batch_size', 3)
        batch_delay = getattr(self, '_depth_config', {}).get('batch_delay', 0.5)
        max_files = getattr(self, '_depth_config', {}).get('max_files', 100)

        # محدود کردن تعداد فایل‌ها بر اساس عمق
        if len(files_to_analyze) > max_files:
            logger.info(f"🔍 [MICRO ANALYSIS] Limiting files from {len(files_to_analyze)} to {max_files} based on depth settings")
            files_to_analyze = files_to_analyze[:max_files]

        logger.info(f"🔍 [MICRO ANALYSIS] Batch size: {batch_size}, Delay: {batch_delay}s, Max files: {max_files}")

        for i in range(0, len(files_to_analyze), batch_size):
            # بررسی درخواست توقف
            if self._progress_manager:
                if self._progress_manager.should_stop():
                    logger.info(f"⏹️ [MICRO ANALYSIS] Stop requested at file {i}/{len(files_to_analyze)}")
                    results["summary"]["stopped"] = True
                    break

                # بررسی درخواست pause
                while self._progress_manager.should_pause():
                    logger.info(f"⏸️ [MICRO ANALYSIS] Paused at file {i}/{len(files_to_analyze)}")
                    await asyncio.sleep(2)  # چک کردن هر 2 ثانیه
                    if self._progress_manager.should_stop():
                        break

            batch = files_to_analyze[i:i + batch_size]
            tasks = []

            for file_data in batch:
                task = self._analyze_single_file_with_models(
                    file_path=file_data["file_path"],
                    content=file_data["content"],
                    roadmap_content=roadmap_content,
                    model_ids=model_ids,
                    instruction=instruction
                )
                tasks.append(task)

            # اجرای موازی این دسته
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"❌ [MICRO ANALYSIS] Task exception: {result}")
                        continue

                    if result and result.get("file_path"):
                        file_path = result["file_path"]
                        results["files"][file_path] = result
                        results["summary"]["analyzed"] += 1
                        results["summary"]["issues_found"] += len(result.get("issues", []))

                        # به‌روزرسانی progress manager
                        if self._progress_manager:
                            total_score = result.get('aggregated_scores', {}).get('total', 0)
                            self._progress_manager.complete_file(
                                file_path=file_path,
                                result=result,
                                issues=len(result.get("issues", []))
                            )

                        logger.info(f"✅ [MICRO ANALYSIS] File {file_path}: score={result.get('aggregated_scores', {}).get('total', 'N/A')}")

            # 🆕 تاخیر بین دسته‌ها برای جلوگیری از rate limit و تحلیل عمیق‌تر
            if batch_delay > 0 and i + batch_size < len(files_to_analyze):
                logger.info(f"⏳ [MICRO ANALYSIS] Batch delay: {batch_delay}s")
                await asyncio.sleep(batch_delay)

        elapsed = time.time() - start_time
        logger.info(f"🔍 [MICRO ANALYSIS] Completed in {elapsed:.2f}s. Analyzed {results['summary']['analyzed']} files, found {results['summary']['issues_found']} issues")

        return results

    async def _analyze_single_file_with_models(
        self,
        file_path: str,
        content: str,
        roadmap_content: str,
        model_ids: List[str],
        instruction: str
    ) -> Dict[str, Any]:
        """تحلیل یک فایل با چند مدل به صورت موازی"""
        import time
        start_time = time.time()

        logger.info(f"📄 [MICRO] Starting analysis of {file_path} with models: {model_ids}")

        # گزارش شروع تحلیل فایل
        await self.progress.start_file(file_path)

        result = {
            "file_path": file_path,
            "file_type": self._get_file_type(file_path),
            "line_count": len(content.split('\n')),
            "model_analyses": {},
            "aggregated_scores": {},
            "issues": [],
            "analyzed_at": datetime.now().isoformat()
        }

        # پرامپت تحلیل جزئی
        prompt = self._build_micro_analysis_prompt(file_path, content, roadmap_content, instruction)
        logger.info(f"📄 [MICRO] Built prompt for {file_path}, length: {len(prompt)} chars")

        # ایجاد تسک‌های موازی با asyncio.gather
        async def analyze_with_model(model_id: str) -> Tuple[str, Dict]:
            """تحلیل با یک مدل خاص"""
            try:
                # گزارش شروع کار مدل
                await self.progress.start_model(model_id, file_path)
                logger.info(f"📄 [MICRO] Calling model {model_id} for {file_path}...")
                response = await self._call_ai_model(model_id, prompt)
                analysis = self._parse_model_response(response)
                logger.info(f"📄 [MICRO] Got response from {model_id} for {file_path}: {list(analysis.keys()) if isinstance(analysis, dict) else 'not dict'}")
                # گزارش اتمام موفق مدل
                await self.progress.complete_model(model_id, success=True)
                return (model_id, analysis)
            except Exception as e:
                logger.error(f"❌ [MICRO] Error analyzing {file_path} with {model_id}: {e}")
                # گزارش خطای مدل
                await self.progress.complete_model(model_id, success=False, message=str(e))
                return (model_id, {"error": str(e)})

        # اجرای واقعاً موازی با asyncio.gather
        tasks = [analyze_with_model(model_id) for model_id in model_ids]
        logger.info(f"📄 [MICRO] Running {len(tasks)} model tasks in parallel for {file_path}...")

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # پردازش نتایج
        for item in results_list:
            if isinstance(item, Exception):
                logger.error(f"❌ [MICRO] Task exception: {item}")
                continue
            if isinstance(item, tuple) and len(item) == 2:
                model_id, analysis = item
                result["model_analyses"][model_id] = analysis

        elapsed = time.time() - start_time
        logger.info(f"📄 [MICRO] Completed {file_path} in {elapsed:.2f}s, got {len(result['model_analyses'])} model responses")

        # میانگین‌گیری نمرات
        result["aggregated_scores"] = self._aggregate_scores(result["model_analyses"])
        result["issues"] = self._collect_issues(result["model_analyses"], file_path)

        logger.info(f"📄 [MICRO] Final scores for {file_path}: {result['aggregated_scores']}")

        # گزارش اتمام تحلیل فایل
        total_score = result["aggregated_scores"].get("total", 0)
        await self.progress.complete_file(
            file_path=file_path,
            issues=len(result["issues"]),
            score=total_score
        )

        return result

    def _build_micro_analysis_prompt(
        self,
        file_path: str,
        content: str,
        roadmap_content: str,
        instruction: str
    ) -> str:
        """ساخت پرامپت تحلیل جزئی"""

        # 🆕 تشخیص نوع فایل برای تحلیل هدفمند
        file_type = self._get_file_type(file_path)
        is_frontend = file_type in ["typescript-react", "javascript-react", "typescript", "javascript", "css"]
        is_backend = file_type in ["python", "golang", "java", "rust"]

        # 🆕 دستورات اضافی بر اساس نوع فایل
        type_specific_instructions = ""
        if is_frontend:
            type_specific_instructions = """
### 📱 بررسی‌های خاص فرانت‌اند:
- **ساختار کامپوننت**: آیا از الگوهای صحیح React/Vue/Angular استفاده شده؟
- **State Management**: آیا state به درستی مدیریت شده؟ (useState, useReducer, Context, Redux)
- **Props و TypeScript**: آیا تایپ‌ها به درستی تعریف شده‌اند؟
- **Hooks**: استفاده صحیح از useEffect, useMemo, useCallback
- **Performance**: آیا re-render های غیرضروری وجود دارد؟
- **Accessibility (a11y)**: آیا ARIA labels و semantic HTML رعایت شده؟
- **Styling**: آیا استایل‌ها modular و قابل نگهداری هستند؟
- **ارتباط با Backend**: آیا API calls به درستی انجام می‌شوند؟ Error handling؟
- **Loading States**: آیا حالت‌های loading و error به کاربر نمایش داده می‌شوند؟
"""
        elif is_backend:
            type_specific_instructions = """
### 🖥️ بررسی‌های خاص بک‌اند:
- **معماری**: آیا از اصول SOLID و Clean Architecture پیروی شده؟
- **امنیت**: بررسی SQL injection, XSS, CSRF, authentication
- **Validation**: آیا ورودی‌ها به درستی اعتبارسنجی می‌شوند؟
- **Error Handling**: آیا خطاها به درستی مدیریت می‌شوند؟
- **Database**: آیا کوئری‌ها بهینه هستند؟ N+1 problem؟
- **Logging**: آیا لاگ‌گذاری مناسب انجام شده؟
- **Testing**: آیا کد قابل تست است؟
"""

        content_limit = getattr(self, '_depth_config', {}).get('content_limit', 15000)

        prompt = f"""# تحلیل جزئی فایل (Micro Analysis)

## فایل: {file_path}
## نوع فایل: {file_type} {'(فرانت‌اند)' if is_frontend else '(بک‌اند)' if is_backend else ''}

## دستورات:
{instruction if instruction else "تحلیل کامل و دقیق فایل را انجام بده."}

{type_specific_instructions}

## محتوای فایل:
```
{content[:content_limit]}
```

{f'''## نقشه‌راه پروژه (برای تطبیق):
{roadmap_content[:3000]}
''' if roadmap_content else ''}

## وظیفه تو:
1. **بررسی کامل کد**: هر خط را بررسی کن (نه خلاصه!)
2. **شناسایی مشکلات**: باگ‌ها، آسیب‌پذیری‌ها، کد بد
3. **بررسی کیفیت**: نام‌گذاری، ساختار، خوانایی
4. **تطبیق با نقشه‌راه**: آیا این فایل با نقشه‌راه همخوانی دارد؟
5. **نمره‌دهی دقیق**: برای هر فاکتور نمره 0-100 بده
{f'6. **بررسی ارتباط فرانت-بک**: آیا ارتباط با API صحیح است؟' if is_frontend else ''}

## فرمت خروجی (JSON):
```json
{{
    "scores": {{
        "code_quality": 0-100,
        "documentation": 0-100,
        "roadmap_compliance": 0-100,
        "security": 0-100,
        "efficiency": 0-100,
        "standards_compliance": 0-100{', "component_structure": 0-100' if is_frontend else ''}{', "api_integration": 0-100' if is_frontend else ''}
    }},
    "issues": [
        {{
            "line": شماره خط,
            "severity": "critical|high|medium|low",
            "type": "bug|security|quality|performance|accessibility|api",
            "message": "توضیح مشکل",
            "suggestion": "پیشنهاد رفع"
        }}
    ],
    "summary": "خلاصه یک خطی وضعیت فایل",
    "strengths": ["نقاط قوت"],
    "weaknesses": ["نقاط ضعف"]{', "api_calls": ["لیست API endpoints استفاده شده"]' if is_frontend else ''}
}}
```

مهم: فقط JSON برگردان، بدون توضیح اضافی!
"""
        return prompt

    # =====================================
    # مرحله 2: Macro Analysis
    # =====================================

    async def _run_macro_analysis(
        self,
        files: List[Dict],
        micro_results: Dict,
        roadmap_content: str,
        readme_content: str,
        model_ids: List[str],
        instruction: str
    ) -> Dict[str, Any]:
        """
        بررسی کلی (Macro): همکاری و جایگاه فایل‌ها

        - بررسی کیفیت کار نسبت به همکاری در کل مجموعه
        - بررسی جایگاه در ساختار پروژه
        - تطبیق با فایل نقشه‌راه
        - مقایسه با README
        """
        results = {
            "cooperation_analysis": {},
            "position_analysis": {},
            "roadmap_compliance": {},
            "readme_compliance": {},
            "summary": {}
        }

        # ساخت نمای کلی پروژه
        project_overview = self._build_project_overview(files, micro_results)

        # پرامپت تحلیل کلی
        prompt = self._build_macro_analysis_prompt(
            project_overview=project_overview,
            roadmap_content=roadmap_content,
            readme_content=readme_content,
            instruction=instruction
        )

        # تحلیل با هر مدل
        model_results = {}
        for model_id in model_ids:
            try:
                response = await self._call_ai_model(model_id, prompt)
                model_results[model_id] = self._parse_model_response(response)
            except Exception as e:
                logger.error(f"خطا در Macro Analysis با مدل {model_id}: {e}")

        # ترکیب نتایج
        results["model_analyses"] = model_results
        results["aggregated"] = self._aggregate_macro_results(model_results)

        return results

    def _build_macro_analysis_prompt(
        self,
        project_overview: str,
        roadmap_content: str,
        readme_content: str,
        instruction: str
    ) -> str:
        """ساخت پرامپت تحلیل کلی"""

        prompt = f"""# تحلیل کلی پروژه (Macro Analysis)

## دستورات:
{instruction if instruction else "تحلیل کامل همکاری و جایگاه فایل‌ها را انجام بده."}

## نمای کلی پروژه:
{project_overview}

{f'''## نقشه‌راه پروژه:
{roadmap_content[:5000]}
''' if roadmap_content else ''}

{f'''## README پروژه:
{readme_content[:3000]}
''' if readme_content else ''}

## وظیفه تو:
1. **همکاری فایل‌ها**: آیا فایل‌ها با هم به درستی کار می‌کنند؟
2. **جایگاه فایل‌ها**: آیا هر فایل در جای درست قرار دارد؟
3. **تطبیق با نقشه‌راه**: پروژه چقدر با نقشه‌راه مطابقت دارد؟
4. **تطبیق با README**: آیا README دقیق است؟
5. **نیازها و کمبودها**: چه چیزهایی کم است؟

## فرمت خروجی (JSON):
```json
{{
    "cooperation_scores": {{
        "فایل1": {{"score": 0-100, "issues": [], "cooperates_well_with": [], "conflicts_with": []}},
        ...
    }},
    "position_scores": {{
        "فایل1": {{"score": 0-100, "current_position": "مسیر", "suggested_position": "مسیر پیشنهادی یا null"}},
        ...
    }},
    "roadmap_compliance": {{
        "overall_score": 0-100,
        "completed_items": [],
        "missing_items": [],
        "extra_items": []
    }},
    "readme_accuracy": {{
        "score": 0-100,
        "outdated_sections": [],
        "missing_info": []
    }},
    "project_needs": {{
        "missing_files": ["فایل‌هایی که باید ایجاد شوند"],
        "files_to_remove": ["فایل‌های اضافی"],
        "refactoring_needed": ["موارد نیاز به بازنویسی"]
    }},
    "overall_health": 0-100,
    "summary": "خلاصه وضعیت کلی"
}}
```

مهم: فقط JSON برگردان!
"""
        return prompt

    # =====================================
    # مرحله 3: Structural Analysis
    # =====================================

    async def _run_structural_analysis(
        self,
        files: List[Dict],
        micro_results: Dict,
        macro_results: Dict,
        roadmap_content: str,
        model_ids: List[str],
        instruction: str
    ) -> Dict[str, Any]:
        """
        بررسی ساختاری (Structural): سیم‌کشی و ارتباطات

        - بررسی سیم‌کشی بین فایل‌ها
        - تحلیل همه فایل‌ها به صورت کلی
        - ارزیابی مناسب بودن جایگاه
        - گزارش کمبودها و نیازها
        """
        results = {
            "wiring_analysis": {},
            "dependency_graph": {},
            "structure_issues": [],
            "ideal_structure": {},
            "summary": {}
        }

        # استخراج import ها و وابستگی‌ها
        dependency_graph = self._extract_dependencies(files)

        # ساخت پرامپت تحلیل ساختاری
        prompt = self._build_structural_analysis_prompt(
            files=files,
            dependency_graph=dependency_graph,
            micro_summary=self._summarize_micro_results(micro_results),
            macro_summary=self._summarize_macro_results(macro_results),
            roadmap_content=roadmap_content,
            instruction=instruction
        )

        # تحلیل با هر مدل
        model_results = {}
        for model_id in model_ids:
            try:
                response = await self._call_ai_model(model_id, prompt)
                model_results[model_id] = self._parse_model_response(response)
            except Exception as e:
                logger.error(f"خطا در Structural Analysis با مدل {model_id}: {e}")

        # ترکیب نتایج
        results["model_analyses"] = model_results
        results["dependency_graph"] = dependency_graph
        results["aggregated"] = self._aggregate_structural_results(model_results)

        return results

    def _build_structural_analysis_prompt(
        self,
        files: List[Dict],
        dependency_graph: Dict,
        micro_summary: str,
        macro_summary: str,
        roadmap_content: str,
        instruction: str
    ) -> str:
        """ساخت پرامپت تحلیل ساختاری"""

        file_list = "\n".join([f"- {f.get('path', f.get('file_path', ''))}" for f in files])

        prompt = f"""# تحلیل ساختاری پروژه (Structural Analysis)

## دستورات:
{instruction if instruction else "تحلیل کامل ساختار و سیم‌کشی پروژه را انجام بده."}

## لیست فایل‌ها:
{file_list}

## گراف وابستگی‌ها:
{json.dumps(dependency_graph, ensure_ascii=False, indent=2)[:5000]}

## خلاصه تحلیل جزئی (Micro):
{micro_summary}

## خلاصه تحلیل کلی (Macro):
{macro_summary}

{f'''## نقشه‌راه:
{roadmap_content[:3000]}
''' if roadmap_content else ''}

## وظیفه تو:
1. **سیم‌کشی**: آیا import ها و وابستگی‌ها درست هستند؟
2. **معماری**: آیا ساختار پروژه منطقی است؟
3. **circular dependencies**: آیا وابستگی دایره‌ای وجود دارد؟
4. **کمبودها**: چه فایل‌هایی باید ایجاد شوند؟
5. **اضافات**: چه فایل‌هایی اضافی هستند؟
6. **حالت ایده‌آل**: ساختار ایده‌آل چیست؟

## فرمت خروجی (JSON):
```json
{{
    "wiring_scores": {{
        "فایل1": {{"score": 0-100, "issues": [], "imports_from": [], "imported_by": []}},
        ...
    }},
    "architecture": {{
        "type": "monolith|microservice|modular|...",
        "score": 0-100,
        "issues": []
    }},
    "circular_dependencies": [
        {{"files": ["فایل1", "فایل2"], "severity": "high|medium|low"}}
    ],
    "missing_files": [
        {{"path": "مسیر پیشنهادی", "purpose": "هدف", "priority": "high|medium|low"}}
    ],
    "unnecessary_files": [
        {{"path": "مسیر", "reason": "دلیل"}}
    ],
    "ideal_structure": {{
        "folders": ["لیست پوشه‌های ایده‌آل"],
        "key_files": ["فایل‌های کلیدی"],
        "description": "توضیح جامع و مفصل ساختار ایده‌آل پروژه (حداقل 500 کاراکتر)",
        "architecture_overview": "معماری کلی سیستم چگونه باید باشد",
        "components": [
            {{"name": "نام کامپوننت", "purpose": "وظیفه", "files": ["فایل‌ها"], "depends_on": ["وابستگی‌ها"]}}
        ],
        "wiring": {{
            "data_flow": "جریان داده در سیستم چگونه باید باشد",
            "communication": "ارتباط بین بخش‌ها چگونه باید باشد"
        }},
        "current_gaps": ["کمبود 1", "کمبود 2"],
        "roadmap_to_ideal": ["قدم 1 برای رسیدن به حالت ایده‌آل", "قدم 2"]
    }},
    "overall_score": 0-100,
    "summary": "خلاصه وضعیت ساختار"
}}
```

مهم: فقط JSON برگردان!
"""
        return prompt

    # =====================================
    # توابع کمکی
    # =====================================

    def _extract_dependencies(self, files: List[Dict]) -> Dict[str, List[str]]:
        """استخراج وابستگی‌ها از فایل‌ها"""
        dependencies = {}

        for file_data in files:
            file_path = file_data.get("path", file_data.get("file_path", ""))
            content = file_data.get("content", "") or ""

            imports = []

            # Python imports
            imports.extend(re.findall(r'^import\s+([\w.]+)', content, re.MULTILINE))
            imports.extend(re.findall(r'^from\s+([\w.]+)\s+import', content, re.MULTILINE))

            # JavaScript/TypeScript imports
            imports.extend(re.findall(r'import\s+.*?\s+from\s+[\'"]([^"\']+)[\'"]', content))
            imports.extend(re.findall(r'require\([\'"]([^"\']+)[\'"]\)', content))

            # Go imports
            imports.extend(re.findall(r'import\s+[\'"]([^"\']+)[\'"]', content))

            dependencies[file_path] = list(set(imports))

        return dependencies

    def _build_project_overview(self, files: List[Dict], micro_results: Dict) -> str:
        """ساخت نمای کلی پروژه"""
        overview = []

        # دسته‌بندی فایل‌ها - با تشخیص بهتر فرانت‌اند
        categories = {
            "backend": [],
            "frontend_components": [],  # 🆕 کامپوننت‌های UI
            "frontend_pages": [],       # 🆕 صفحات
            "frontend_hooks": [],       # 🆕 hooks و contexts
            "frontend_other": [],       # 🆕 سایر فایل‌های فرانت‌اند
            "config": [],
            "tests": [],
            "docs": [],
            "other": []
        }

        for file_data in files:
            path = file_data.get("path", file_data.get("file_path", "")).lower()
            ext = os.path.splitext(path)[1]

            # تشخیص دقیق‌تر فایل‌های فرانت‌اند
            is_react = ext in [".tsx", ".jsx"]
            is_frontend_file = is_react or ext in [".ts", ".js", ".css", ".scss"] and any(
                x in path for x in ["frontend/", "src/", "components/", "pages/", "app/"]
            )

            if any(x in path for x in ["api", "routes", "services", "models", "backend", "controllers"]) and not is_react:
                categories["backend"].append(path)
            elif is_frontend_file:
                if any(x in path for x in ["components/", "/ui/", "component"]):
                    categories["frontend_components"].append(path)
                elif any(x in path for x in ["pages/", "app/", "/page."]):
                    categories["frontend_pages"].append(path)
                elif any(x in path for x in ["hooks/", "contexts/", "context/", "store/", "use"]):
                    categories["frontend_hooks"].append(path)
                else:
                    categories["frontend_other"].append(path)
            elif any(x in path for x in ["config", ".env", "settings", "package.json", "requirements", "tsconfig"]):
                categories["config"].append(path)
            elif "test" in path or "spec" in path:
                categories["tests"].append(path)
            elif any(x in path for x in ["readme", "doc", ".md"]):
                categories["docs"].append(path)
            else:
                categories["other"].append(path)

        # نمایش با نام‌های فارسی بهتر
        category_labels = {
            "backend": "🖥️ بک‌اند",
            "frontend_components": "📱 کامپوننت‌های فرانت‌اند",
            "frontend_pages": "📄 صفحات فرانت‌اند",
            "frontend_hooks": "🔗 Hooks و Contexts",
            "frontend_other": "🎨 سایر فایل‌های فرانت‌اند",
            "config": "⚙️ تنظیمات",
            "tests": "🧪 تست‌ها",
            "docs": "📚 مستندات",
            "other": "📁 سایر"
        }

        for cat, cat_files in categories.items():
            if cat_files:
                label = category_labels.get(cat, cat.upper())
                overview.append(f"\n### {label} ({len(cat_files)} فایل):")
                for f in cat_files[:20]:
                    # جستجوی case-insensitive در micro_results
                    micro = None
                    for key in micro_results.get("files", {}).keys():
                        if key.lower() == f.lower():
                            micro = micro_results["files"][key]
                            break
                    score = micro.get("aggregated_scores", {}).get("total", "?") if micro else "?"
                    overview.append(f"  - {f} (نمره: {score})")

        # 🆕 خلاصه آماری
        total_frontend = len(categories["frontend_components"]) + len(categories["frontend_pages"]) + len(categories["frontend_hooks"]) + len(categories["frontend_other"])
        total_backend = len(categories["backend"])

        overview.insert(0, f"""
## 📊 خلاصه آماری پروژه
- **فایل‌های بک‌اند:** {total_backend}
- **فایل‌های فرانت‌اند:** {total_frontend}
  - کامپوننت‌ها: {len(categories["frontend_components"])}
  - صفحات: {len(categories["frontend_pages"])}
  - Hooks/Contexts: {len(categories["frontend_hooks"])}
- **تست‌ها:** {len(categories["tests"])}
- **مستندات:** {len(categories["docs"])}
""")

        return "\n".join(overview)

    def _get_file_type(self, file_path: str) -> str:
        """تشخیص نوع فایل"""
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript-react",
            ".jsx": "javascript-react",
            ".go": "golang",
            ".rs": "rust",
            ".java": "java",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
        }
        return type_map.get(ext, "other")

    async def _call_ai_model(self, model_id: str, prompt: str, fallback_models: List[str] = None) -> str:
        """
        فراخوانی مدل AI با قابلیت fallback

        اگر مدل اصلی fail کنه، مدل‌های دیگه امتحان میشن
        """
        import time

        if not self.ai_manager:
            logger.error("❌ [AI CALL] AI Manager is None! Cannot make AI calls!")
            return "{}"

        # لیست مدل‌ها برای امتحان
        models_to_try = [model_id]
        if fallback_models:
            models_to_try.extend([m for m in fallback_models if m != model_id])
        else:
            # اگر fallback داده نشده، از همه مدل‌های موجود برای analysis استفاده کن
            try:
                all_models = self.ai_manager.get_available_models(task_type="analysis")
                models_to_try.extend([m.id for m in all_models if m.id != model_id])
            except:
                pass

        last_error = None
        for try_model in models_to_try:
            start_time = time.time()
            logger.info(f"🚀 [AI CALL] Trying model {try_model}...")

            try:
                messages = [
                    Message(role="system", content="تو یک تحلیل‌گر حرفه‌ای کد هستی. فقط خروجی JSON برگردان."),
                    Message(role="user", content=prompt)
                ]

                response = await self.ai_manager.generate(
                    model_id=try_model,
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.3
                )

                elapsed = time.time() - start_time
                logger.info(f"✅ [AI CALL] Got response from {try_model} in {elapsed:.2f}s")

                # استخراج محتوا
                if hasattr(response, 'content') and response.content:
                    logger.info(f"📦 [AI CALL] Response length: {len(response.content)} chars")
                    return response.content
                elif isinstance(response, dict):
                    content = response.get("content", response.get("response", "{}"))
                    return content
                else:
                    return str(response)

            except Exception as e:
                elapsed = time.time() - start_time
                last_error = e
                logger.warning(f"⚠️ [AI CALL] Model {try_model} failed after {elapsed:.2f}s: {e}")

                # اگه quota یا billing error هست، سریع مدل بعدی
                error_str = str(e).lower()
                if "quota" in error_str or "billing" in error_str or "rate" in error_str:
                    logger.info(f"🔄 [AI CALL] Quota/billing issue, trying next model...")
                    continue
                # برای خطاهای دیگه هم ادامه بده
                continue

        # اگه هیچ مدلی جواب نداد
        logger.error(f"❌ [AI CALL] All models failed! Last error: {last_error}")
        return "{}"

    async def _get_available_models(self) -> List[str]:
        """دریافت لیست مدل‌های در دسترس برای تحلیل"""
        if self.ai_manager:
            try:
                # get_available_models یک متد sync است
                # 🔴 فقط مدل‌های مجاز برای analysis
                models = self.ai_manager.get_available_models(task_type="analysis")
                # AIModel objects have .id attribute
                # بدون محدودیت - همه مدل‌ها
                return [m.id for m in models]
            except Exception as e:
                logger.warning(f"خطا در دریافت مدل‌ها: {e}")

        return ["gpt-4", "claude-3-opus"]

    def _parse_model_response(self, response: str) -> Dict:
        """پارس پاسخ مدل"""
        if not response:
            return {}

        # تلاش برای استخراج JSON
        try:
            # پیدا کردن JSON در پاسخ
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        return {"raw_response": response}

    def _aggregate_scores(self, model_analyses: Dict) -> Dict[str, float]:
        """میانگین‌گیری نمرات از چند مدل"""
        logger.info(f"📊 [AGGREGATE] Starting aggregation for {len(model_analyses)} model analyses")

        all_scores = {}
        successful_models = 0
        error_models = []

        for model_id, analysis in model_analyses.items():
            logger.info(f"📊 [AGGREGATE] Processing {model_id}: {type(analysis)}")

            if isinstance(analysis, dict):
                # اگر error داره، skip کن
                if analysis.get("error"):
                    error_models.append(model_id)
                    logger.warning(f"📊 [AGGREGATE] Model {model_id} has error: {analysis.get('error')}")
                    continue

                successful_models += 1

                if "scores" in analysis:
                    logger.info(f"📊 [AGGREGATE] Model {model_id} has scores: {analysis['scores']}")
                    for key, value in analysis["scores"].items():
                        if key not in all_scores:
                            all_scores[key] = []
                        if isinstance(value, (int, float)):
                            all_scores[key].append(value)

                # اگر scores نبود ولی overall_score یا code_quality بود
                elif "overall_score" in analysis:
                    logger.info(f"📊 [AGGREGATE] Model {model_id} has overall_score: {analysis['overall_score']}")
                    if "code_quality" not in all_scores:
                        all_scores["code_quality"] = []
                    all_scores["code_quality"].append(analysis["overall_score"])

                # اگر raw_response داره، سعی کن از متن نمره استخراج کنی
                elif "raw_response" in analysis:
                    logger.info(f"📊 [AGGREGATE] Model {model_id} has raw_response, trying to extract score")
                    extracted = self._extract_score_from_text(analysis["raw_response"])
                    if extracted > 0:
                        if "code_quality" not in all_scores:
                            all_scores["code_quality"] = []
                        all_scores["code_quality"].append(extracted)
                        logger.info(f"📊 [AGGREGATE] Extracted score {extracted} from raw_response")
                    else:
                        logger.warning(f"📊 [AGGREGATE] Could not extract score from raw_response for {model_id}")
                else:
                    logger.warning(f"📊 [AGGREGATE] Model {model_id} returned dict but no scores/raw_response. Keys: {list(analysis.keys())}")
            else:
                logger.warning(f"📊 [AGGREGATE] Model {model_id} returned non-dict: {type(analysis)}")

        logger.info(f"📊 [AGGREGATE] Collected scores from {successful_models} successful models, {len(error_models)} errors")
        logger.info(f"📊 [AGGREGATE] All scores: {all_scores}")

        aggregated = {}
        for key, values in all_scores.items():
            if values:
                aggregated[key] = sum(values) / len(values)

        # محاسبه نمره کلی
        if aggregated:
            aggregated["total"] = sum(aggregated.values()) / len(aggregated)
            logger.info(f"📊 [AGGREGATE] Final aggregated scores: {aggregated}")
        elif successful_models > 0:
            # اگر مدل‌ها پاسخ دادن ولی نمره قابل استخراج نبود
            aggregated["total"] = 0
            aggregated["parse_failed"] = True
            aggregated["_debug_successful_models"] = successful_models
            aggregated["_debug_error_models"] = error_models
            logger.warning(f"📊 [AGGREGATE] No scores extracted despite {successful_models} successful models!")
        else:
            aggregated["_debug_all_failed"] = True
            aggregated["_debug_error_models"] = error_models
            logger.error(f"📊 [AGGREGATE] ALL models failed or returned errors!")

        return aggregated

    def _extract_score_from_text(self, text: str) -> float:
        """استخراج نمره از متن پاسخ AI"""
        import re
        # جستجوی الگوهای معمول نمره‌دهی
        patterns = [
            r'(?:score|نمره|امتیاز)[:\s]*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:out of|از)\s*100',
            r'(\d+(?:\.\d+)?)\s*%',
            r'(?:rating|رتبه)[:\s]*(\d+(?:\.\d+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                if 0 <= score <= 100:
                    return score
                elif 0 <= score <= 10:
                    return score * 10
        return 0

    def _collect_issues(self, model_analyses: Dict, file_path: str) -> List[Dict]:
        """جمع‌آوری مشکلات از همه مدل‌ها"""
        all_issues = []
        seen = set()

        for model_id, analysis in model_analyses.items():
            if isinstance(analysis, dict) and "issues" in analysis:
                for issue in analysis["issues"]:
                    if isinstance(issue, dict):
                        issue["model"] = model_id
                        issue["file"] = file_path

                        # جلوگیری از تکرار
                        key = f"{issue.get('line', 0)}-{issue.get('message', '')}"
                        if key not in seen:
                            seen.add(key)
                            all_issues.append(issue)

        return all_issues

    def _summarize_micro_results(self, micro_results: Dict) -> str:
        """خلاصه نتایج Micro Analysis"""
        summary = micro_results.get("summary", {})
        return f"""
تعداد فایل‌ها: {summary.get('total_files', 0)}
تحلیل شده: {summary.get('analyzed', 0)}
مشکلات یافت شده: {summary.get('issues_found', 0)}
"""

    def _summarize_macro_results(self, macro_results: Dict) -> str:
        """خلاصه نتایج Macro Analysis"""
        agg = macro_results.get("aggregated", {})
        return f"""
نمره همکاری: {agg.get('cooperation_score', '?')}
نمره تطبیق با نقشه‌راه: {agg.get('roadmap_score', '?')}
"""

    def _aggregate_macro_results(self, model_results: Dict) -> Dict:
        """ترکیب نتایج Macro از چند مدل"""
        # پیاده‌سازی کامل - میانگین تمام نمرات
        scores = {
            "cooperation_score": [],
            "roadmap_score": [],
            "overall_health": [],
            "readme_accuracy": [],  # 🆕 اضافه شد
            "position_score": [],   # 🆕 اضافه شد
        }

        for model_id, result in model_results.items():
            if isinstance(result, dict):
                # نمره roadmap_compliance
                if "roadmap_compliance" in result:
                    rc = result["roadmap_compliance"]
                    if isinstance(rc, dict) and "overall_score" in rc:
                        scores["roadmap_score"].append(rc["overall_score"])

                # نمره overall_health
                if "overall_health" in result:
                    scores["overall_health"].append(result["overall_health"])

                # 🆕 نمره readme_accuracy (مستندات)
                if "readme_accuracy" in result:
                    ra = result["readme_accuracy"]
                    if isinstance(ra, dict) and "score" in ra:
                        scores["readme_accuracy"].append(ra["score"])
                    elif isinstance(ra, (int, float)):
                        scores["readme_accuracy"].append(ra)

                # 🆕 نمره cooperation از cooperation_scores
                if "cooperation_scores" in result:
                    cs = result["cooperation_scores"]
                    if isinstance(cs, dict):
                        # میانگین نمرات همکاری فایل‌ها
                        file_scores = []
                        for file_data in cs.values():
                            if isinstance(file_data, dict) and "score" in file_data:
                                file_scores.append(file_data["score"])
                        if file_scores:
                            scores["cooperation_score"].append(sum(file_scores) / len(file_scores))

                # 🆕 نمره position از position_scores
                if "position_scores" in result:
                    ps = result["position_scores"]
                    if isinstance(ps, dict):
                        file_scores = []
                        for file_data in ps.values():
                            if isinstance(file_data, dict) and "score" in file_data:
                                file_scores.append(file_data["score"])
                        if file_scores:
                            scores["position_score"].append(sum(file_scores) / len(file_scores))

        return {k: (sum(v)/len(v) if v else 0) for k, v in scores.items()}

    def _aggregate_structural_results(self, model_results: Dict) -> Dict:
        """ترکیب نتایج Structural از چند مدل"""
        aggregated = {
            "overall_score": 0,
            "missing_files": [],
            "unnecessary_files": [],
            "circular_dependencies": []
        }

        scores = []
        for model_id, result in model_results.items():
            if isinstance(result, dict):
                if "overall_score" in result:
                    scores.append(result["overall_score"])
                if "missing_files" in result:
                    aggregated["missing_files"].extend(result["missing_files"])
                if "unnecessary_files" in result:
                    aggregated["unnecessary_files"].extend(result["unnecessary_files"])
                if "circular_dependencies" in result:
                    aggregated["circular_dependencies"].extend(result["circular_dependencies"])

        if scores:
            aggregated["overall_score"] = sum(scores) / len(scores)

        return aggregated

    def _calculate_final_results(
        self,
        micro_results: Dict,
        macro_results: Dict,
        structural_results: Dict,
        model_ids: List[str]
    ) -> Dict[str, Any]:
        """محاسبه نتایج نهایی"""
        logger.info(f"📈 [FINAL] Calculating final results from {len(micro_results.get('files', {}))} files")

        # ساخت file_health_map با رنگ‌بندی
        file_health_map = {}
        files_with_real_scores = 0
        files_with_default_scores = 0

        for file_path, file_data in micro_results.get("files", {}).items():
            scores = file_data.get("aggregated_scores", {})
            total_score = scores.get("total")

            # بررسی آیا نمره واقعی است یا پیش‌فرض
            has_real_score = total_score is not None and not scores.get("_debug_all_failed")

            if total_score is None:
                total_score = 50  # Default value
                files_with_default_scores += 1
                logger.warning(f"📈 [FINAL] File {file_path} has NO score, using default 50")
            else:
                files_with_real_scores += 1

            if scores.get("parse_failed"):
                logger.warning(f"📈 [FINAL] File {file_path} parse failed, score: {total_score}")

            color_info = get_health_color(total_score)

            # 🆕 استخراج issues با اطلاعات کامل
            file_issues = file_data.get("issues", [])

            file_health_map[file_path] = {
                "score": total_score,
                "scores_detail": scores,
                "color": color_info["color"],
                "hex": color_info["hex"],
                "label": color_info["label"],
                "models_analyzed": len(file_data.get("model_analyses", {})),
                "model_scores": {
                    m: a.get("scores", {}).get("total", a.get("scores", {}).get("code_quality", 50))
                    for m, a in file_data.get("model_analyses", {}).items()
                    if isinstance(a, dict) and not a.get("error")
                },
                "issues_count": len(file_issues),
                "issues": file_issues,  # 🔴 رفع محدودیت - تمام issues بدون محدودیت ذخیره می‌شوند
                "analyzed_by": list(file_data.get("model_analyses", {}).keys()),  # 🆕 مدل‌های تحلیل‌کننده
                "analyzed_at": file_data.get("analyzed_at")
            }

        # Log summary
        logger.info(f"📈 [FINAL] Files with REAL AI scores: {files_with_real_scores}")
        logger.info(f"📈 [FINAL] Files with DEFAULT (50) scores: {files_with_default_scores}")

        if files_with_default_scores > 0 and files_with_real_scores == 0:
            logger.error(f"❌ [FINAL] ALL files have default scores! AI calls likely failed!")

        # میانگین نمرات فایل‌ها
        file_scores = [f["score"] for f in file_health_map.values()]
        avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0

        logger.info(f"📈 [FINAL] Average file score: {avg_file_score:.1f}")

        # نمرات از هر مرحله
        macro_score = macro_results.get("aggregated", {}).get("overall_health", 0)
        structural_score = structural_results.get("aggregated", {}).get("overall_score", 0)

        # محاسبه نمره ساختاری بر اساس ایرادات
        total_issues = sum(len(f.get("issues", [])) for f in micro_results.get("files", {}).values())
        total_files = len(file_health_map)
        if total_issues > 0 and total_files > 0:
            # کاهش نمره بر اساس تعداد ایرادات
            issues_penalty = min(total_issues * 2, 50)  # حداکثر 50 نمره کم میشه
            structural_score = max(0, 100 - issues_penalty)
        elif total_files > 0:
            structural_score = 70  # اگر ایرادی نبود

        # محاسبه نمره کلی
        if avg_file_score > 0 or macro_score > 0 or structural_score > 0:
            total_score = (
                avg_file_score * 0.4 +
                macro_score * 0.3 +
                structural_score * 0.3
            )
        else:
            total_score = 0

        # 🆕 استخراج صحیح نمرات از macro aggregated
        macro_aggregated = macro_results.get("aggregated", {})
        documentation_score = macro_aggregated.get("readme_accuracy", 0)
        cooperation_score = macro_aggregated.get("cooperation_score", 0)
        position_score = macro_aggregated.get("position_score", 0)
        roadmap_score = macro_aggregated.get("roadmap_score", 0)

        # اگر نمره مستندات 0 بود، محاسبه بر اساس وجود README
        if documentation_score == 0:
            # بررسی وجود فایل‌های مستندات در پروژه
            has_readme = any('readme' in f.lower() for f in file_health_map.keys())
            has_docs = any('doc' in f.lower() or '.md' in f.lower() for f in file_health_map.keys())
            if has_readme and has_docs:
                documentation_score = 60  # پایه اگر README موجود باشد
            elif has_readme:
                documentation_score = 40
            elif has_docs:
                documentation_score = 30
            # اگر هیچکدام نبود، 0 می‌ماند

        # محاسبه نمره امنیت بر اساس ایرادات امنیتی
        security_issues = sum(
            1 for f in micro_results.get("files", {}).values()
            for issue in f.get("issues", [])
            if issue.get("type") == "security" or "security" in str(issue.get("message", "")).lower()
        )
        if security_issues == 0:
            security_score = avg_file_score
        else:
            security_penalty = min(security_issues * 10, 50)
            security_score = max(0, avg_file_score - security_penalty)

        logger.info(f"📈 [FINAL] Score breakdown: micro={avg_file_score:.1f}, macro={macro_score:.1f}, structural={structural_score:.1f}")
        logger.info(f"📈 [FINAL] Detailed: docs={documentation_score:.1f}, coop={cooperation_score:.1f}, roadmap={roadmap_score:.1f}, security={security_score:.1f}")

        overall_scores = {
            "micro": avg_file_score,
            "macro": macro_score,
            "structural": structural_score,
            "total": total_score,
            # اضافه کردن نمرات جزئی‌تر
            "code_quality": avg_file_score,
            "documentation": documentation_score,  # 🆕 استفاده از نمره واقعی
            "security": security_score,
            "cooperation": cooperation_score,      # 🆕 نمره همکاری
            "roadmap_compliance": roadmap_score,
        }

        # جمع‌آوری همه مشکلات
        all_issues = []
        for file_path, file_data in micro_results.get("files", {}).items():
            all_issues.extend(file_data.get("issues", []))

        # مرتب‌سازی بر اساس شدت
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        # 🔴 تبدیل امن برای جلوگیری از خطای NoneType comparison
        def safe_severity(x):
            sev = x.get("severity") if x.get("severity") else "low"
            return severity_order.get(sev, 4)
        all_issues.sort(key=safe_severity)

        # پیشنهادات
        recommendations = []
        structural_agg = structural_results.get("aggregated", {})

        for missing in structural_agg.get("missing_files", [])[:10]:
            if isinstance(missing, dict):
                recommendations.append({
                    "type": "create_file",
                    "priority": missing.get("priority", "medium"),
                    "message": f"ایجاد فایل: {missing.get('path', '?')} - {missing.get('purpose', '')}"
                })

        for unnecessary in structural_agg.get("unnecessary_files", [])[:5]:
            if isinstance(unnecessary, dict):
                recommendations.append({
                    "type": "remove_file",
                    "priority": "low",
                    "message": f"حذف فایل اضافی: {unnecessary.get('path', '?')} - {unnecessary.get('reason', '')}"
                })

        # حالت ایده‌آل - جامع و مفصل
        ideal_state = ""
        ideal_structure_data = {}

        # جمع‌آوری اطلاعات از نتایج structural
        for model_id, result in structural_results.get("model_analyses", {}).items():
            if isinstance(result, dict) and "ideal_structure" in result:
                ideal = result["ideal_structure"]
                if isinstance(ideal, dict):
                    # ترکیب اطلاعات از همه مدل‌ها
                    if not ideal_structure_data:
                        ideal_structure_data = ideal
                    else:
                        # ادغام کامپوننت‌ها و gaps
                        if "components" in ideal:
                            ideal_structure_data.setdefault("components", []).extend(ideal.get("components", []))
                        if "current_gaps" in ideal:
                            ideal_structure_data.setdefault("current_gaps", []).extend(ideal.get("current_gaps", []))

        # 🆕 تولید حالت ایده‌آل جامع
        def build_comprehensive_ideal_state():
            sections = []

            # 1. معماری کلی
            sections.append("## معماری کلی سیستم")
            if ideal_structure_data.get("architecture_overview"):
                sections.append(ideal_structure_data["architecture_overview"])
            elif ideal_structure_data.get("description"):
                sections.append(ideal_structure_data["description"])
            else:
                # تولید بر اساس ساختار پروژه
                file_types = set()
                for fp in file_health_map.keys():
                    if "frontend" in fp.lower() or ".tsx" in fp or ".jsx" in fp:
                        file_types.add("frontend")
                    if "backend" in fp.lower() or "api" in fp.lower() or ".py" in fp:
                        file_types.add("backend")
                    if "test" in fp.lower():
                        file_types.add("test")
                    if "config" in fp.lower() or ".env" in fp or "setting" in fp.lower():
                        file_types.add("config")

                if "frontend" in file_types and "backend" in file_types:
                    sections.append("""این پروژه یک سیستم Full-Stack است با جداسازی کامل frontend و backend.
معماری ایده‌آل: Monorepo با ساختار لایه‌ای
- Backend: معماری لایه‌ای (routes → controllers → services → models → database)
- Frontend: معماری کامپوننت‌محور (pages → components → hooks → services → utils)
- ارتباط: REST API یا GraphQL با مستندات OpenAPI/Swagger""")
                elif "frontend" in file_types:
                    sections.append("""این پروژه یک اپلیکیشن Frontend است.
معماری ایده‌آل: Component-Based Architecture با State Management مرکزی
- ساختار پوشه‌ای: components/, pages/, hooks/, services/, utils/, contexts/
- هر کامپوننت در پوشه مجزا با فایل‌های .tsx، .css، .test.tsx""")
                elif "backend" in file_types:
                    sections.append("""این پروژه یک سیستم Backend است.
معماری ایده‌آل: Clean Architecture یا Layered Architecture
- لایه‌ها: API Routes → Controllers → Services → Repositories → Models
- جداسازی concerns: auth, validation, business logic, data access""")

            # 2. کمبودها و نواقص
            sections.append("\n## کمبودها و نواقص فعلی")
            gaps = ideal_structure_data.get("current_gaps", [])

            # اضافه کردن کمبودها از issues
            severity_groups = {"critical": [], "high": [], "medium": []}
            for issue in all_issues[:30]:
                sev = issue.get("severity", "medium")
                if sev in severity_groups:
                    msg = issue.get("message", issue.get("description", str(issue)))[:100]
                    severity_groups[sev].append(msg)

            if severity_groups["critical"]:
                gaps.append(f"⛔ {len(severity_groups['critical'])} ایراد بحرانی: {', '.join(severity_groups['critical'][:3])}")
            if severity_groups["high"]:
                gaps.append(f"🔴 {len(severity_groups['high'])} ایراد با اولویت بالا")
            if severity_groups["medium"]:
                gaps.append(f"🟡 {len(severity_groups['medium'])} ایراد متوسط")

            # بررسی کمبودهای ساختاری
            if not any("test" in f.lower() for f in file_health_map.keys()):
                gaps.append("❌ پوشش تست: هیچ فایل تستی یافت نشد")
            if not any("readme" in f.lower() for f in file_health_map.keys()):
                gaps.append("❌ مستندات: فایل README.md وجود ندارد")
            if documentation_score < 50:
                gaps.append(f"⚠️ نمره مستندات پایین: {documentation_score:.0f}%")

            if gaps:
                sections.append("\n".join([f"- {g}" for g in gaps[:15]]))
            else:
                sections.append("- کمبود خاصی شناسایی نشده")

            # 3. ساختار کامپوننت‌ها
            sections.append("\n## ساختار کامپوننت‌ها و سیم‌کشی")
            components = ideal_structure_data.get("components", [])
            if components:
                for comp in components[:10]:
                    if isinstance(comp, dict):
                        sections.append(f"**{comp.get('name', '?')}**: {comp.get('purpose', '')}")
                        if comp.get("files"):
                            sections.append(f"  فایل‌ها: {', '.join(comp['files'][:5])}")
                        if comp.get("depends_on"):
                            sections.append(f"  وابسته به: {', '.join(comp['depends_on'][:5])}")
            else:
                # تولید پیشنهاد ساختار بر اساس فایل‌های موجود
                sections.append("پیشنهاد ساختار بر اساس فایل‌های موجود:")
                folder_groups = {}
                for fp in file_health_map.keys():
                    parts = fp.split("/")
                    if len(parts) > 1:
                        folder = parts[0]
                        folder_groups.setdefault(folder, []).append(fp)
                for folder, files in list(folder_groups.items())[:8]:
                    sections.append(f"- **{folder}/**: {len(files)} فایل")

            # 4. سیم‌کشی
            wiring = ideal_structure_data.get("wiring", {})
            if wiring:
                sections.append("\n## جریان داده و ارتباطات")
                if wiring.get("data_flow"):
                    sections.append(f"**جریان داده:** {wiring['data_flow']}")
                if wiring.get("communication"):
                    sections.append(f"**ارتباط بین بخش‌ها:** {wiring['communication']}")

            # 5. نقشه راه به حالت ایده‌آل
            sections.append("\n## نقشه راه رسیدن به حالت ایده‌آل")
            roadmap_steps = ideal_structure_data.get("roadmap_to_ideal", [])

            # اضافه کردن پیشنهادات از recommendations
            for rec in recommendations[:10]:
                if isinstance(rec, dict):
                    roadmap_steps.append(rec.get("message", ""))

            if total_issues > 20:
                roadmap_steps.insert(0, f"🔴 فوری: رفع {len(severity_groups.get('critical', []))} ایراد بحرانی")
            if total_issues > 5:
                roadmap_steps.insert(1, f"🟡 کوتاه‌مدت: رفع ایرادات با اولویت بالا و متوسط")
            if not any("test" in f.lower() for f in file_health_map.keys()):
                roadmap_steps.append("📝 افزودن تست‌های واحد برای بخش‌های اصلی")
            if documentation_score < 50:
                roadmap_steps.append("📖 بهبود مستندات و افزودن README کامل")

            if roadmap_steps:
                for i, step in enumerate(roadmap_steps[:10], 1):
                    sections.append(f"{i}. {step}")
            else:
                sections.append("1. ادامه توسعه با رعایت استانداردها")

            # 6. خلاصه امتیازات
            sections.append(f"\n## خلاصه وضعیت فعلی")
            sections.append(f"- نمره کیفیت کد: {avg_file_score:.0f}%")
            sections.append(f"- نمره مستندات: {documentation_score:.0f}%")
            sections.append(f"- نمره ساختار: {structural_score:.0f}%")
            sections.append(f"- تعداد ایرادات: {total_issues}")
            sections.append(f"- فایل‌های تحلیل شده: {total_files}")

            return "\n".join(sections)

        ideal_state = build_comprehensive_ideal_state()

        # 🔴 رفع محدودیت - تمام ایرادات ذخیره می‌شوند (ادغام موارد مشابه قبل از ذخیره)
        merged_issues = self._merge_similar_issues(all_issues)

        return {
            "file_health_map": file_health_map,
            "overall_scores": overall_scores,
            "issues": merged_issues,  # بدون محدودیت - همه ایرادات
            "issues_count": len(merged_issues),
            "original_issues_count": len(all_issues),
            "recommendations": recommendations,
            "ideal_state": ideal_state
        }

    def _merge_similar_issues(self, issues: List[Dict]) -> List[Dict]:
        """
        ادغام ایرادات مشابه برای جلوگیری از تکرار

        قوانین ادغام پایدار:
        - ایرادات با فایل، نوع و پیام مشابه ادغام می‌شوند
        - severity بالاتر حفظ می‌شود
        - شناسه یکتا و پایدار برای هر issue تولید می‌شود
        - مدل‌های منبع جمع‌آوری می‌شوند
        """
        if not issues:
            return []

        import hashlib

        merged = {}
        for issue in issues:
            # استخراج اطلاعات پایدار
            file_path = issue.get("file", issue.get("file_path", "unknown"))
            issue_type = issue.get("type", "general")
            line = issue.get("line", 0)
            message = issue.get("message", issue.get("description", ""))

            # نرمال‌سازی پیام برای مقایسه پایدار
            normalized_message = message.lower().strip()[:100] if message else ""

            # ساخت کلید پایدار با hash
            # استفاده از file + type + normalized_message برای ادغام پایدارتر
            key_parts = f"{file_path}:{issue_type}:{normalized_message}"
            stable_key = hashlib.md5(key_parts.encode()).hexdigest()[:16]

            if stable_key in merged:
                # ادغام با موجود
                existing = merged[stable_key]
                # حفظ severity بالاتر
                severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                # 🔴 تبدیل امن برای جلوگیری از خطای NoneType comparison
                issue_sev = issue.get("severity") if issue.get("severity") else "low"
                existing_sev = existing.get("severity") if existing.get("severity") else "low"
                if severity_order.get(issue_sev, 3) < severity_order.get(existing_sev, 3):
                    existing["severity"] = issue.get("severity")

                # ادغام خطوط (در صورت تفاوت)
                existing_lines = existing.get("lines", [existing.get("line", 0)])
                if line and line not in existing_lines:
                    existing_lines.append(line)
                existing["lines"] = existing_lines
                existing["line"] = min(existing_lines) if existing_lines else 0

                # اضافه کردن منبع
                if "source_models" not in existing:
                    existing["source_models"] = [existing.get("model", "unknown")]
                model = issue.get("model", issue.get("source_model", "unknown"))
                if model not in existing["source_models"]:
                    existing["source_models"].append(model)

                # افزایش تعداد تأیید
                existing["confirmation_count"] = existing.get("confirmation_count", 1) + 1
            else:
                # ایجاد ایراد جدید با شناسه پایدار
                new_issue = issue.copy()
                new_issue["stable_id"] = stable_key
                new_issue["file"] = file_path
                new_issue["confirmation_count"] = 1
                model = issue.get("model", issue.get("source_model", "unknown"))
                new_issue["source_models"] = [model] if model else []
                merged[stable_key] = new_issue

        # مرتب‌سازی بر اساس تعداد تأیید (بیشترین تأیید = مهم‌تر) و severity
        result = list(merged.values())
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        # 🔴 تبدیل امن برای جلوگیری از خطای NoneType comparison
        def safe_sort_key(x):
            conf_count = x.get("confirmation_count") if x.get("confirmation_count") is not None else 1
            sev = x.get("severity") if x.get("severity") else "low"
            file_path = x.get("file") if x.get("file") else ""
            line_num = x.get("line") if x.get("line") is not None else 0
            return (-conf_count, severity_order.get(sev, 3), file_path, line_num)
        result.sort(key=safe_sort_key)

        logger.info(f"🔀 [MERGE] Merged {len(issues)} issues into {len(result)} unique issues")

        return result

    async def _save_analysis_results(self, project_id: str, results: Dict, db_session) -> None:
        """ذخیره نتایج در دیتابیس"""
        try:
            from ..models.project import Project

            project = db_session.query(Project).filter(Project.id == project_id).first()
            if project:
                project.health_scores = json.dumps(results.get("overall_scores", {}))
                project.file_health_map = json.dumps(results.get("file_health_map", {}))
                project.issues_found = json.dumps(results.get("issues", []))
                project.ideal_state = results.get("ideal_state", "")
                project.last_analysis_id = results.get("analysis_id")
                project.last_analysis_at = datetime.now()
                project.last_analysis_models = json.dumps(results.get("models_used", []))

                db_session.commit()
                logger.info(f"نتایج تحلیل برای پروژه {project_id} ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره نتایج: {e}")

    async def _update_model_profiles(
        self,
        model_ids: List[str],
        micro_results: Dict,
        analysis_id: str,
        total_issues: int
    ) -> None:
        """
        به‌روزرسانی پروفایل مدل‌ها بر اساس نتایج تحلیل

        این تابع نمرات واقعی هر مدل را از نتایج تحلیل استخراج
        و در پروفایل مدل‌ها ذخیره می‌کند
        """
        try:
            from .model_profiler import get_model_profiler
            profiler = get_model_profiler()

            # استخراج نمرات هر مدل از نتایج micro analysis
            for model_id in model_ids:
                model_scores = []
                correct_findings = 0
                response_times = []

                # جمع‌آوری داده‌های هر مدل از همه فایل‌ها
                for file_path, file_data in micro_results.get("files", {}).items():
                    model_analysis = file_data.get("model_analyses", {}).get(model_id)
                    if model_analysis and isinstance(model_analysis, dict):
                        # نمره
                        if not model_analysis.get("error"):
                            scores = model_analysis.get("scores", {})
                            if scores:
                                total_score = scores.get("total", scores.get("code_quality", 0))
                                if total_score > 0:
                                    model_scores.append(total_score)

                            # ایرادات یافت شده
                            issues = model_analysis.get("issues", [])
                            correct_findings += len(issues)

                # محاسبه نمره میانگین این مدل
                avg_score = sum(model_scores) / len(model_scores) if model_scores else 0

                if avg_score > 0:
                    # به‌روزرسانی پروفایل
                    await profiler.update_profile(
                        model_id=model_id,
                        task_type="health_analysis",
                        correct_findings=correct_findings,
                        total_expected=total_issues,
                        false_positives=0,  # فعلاً قابل محاسبه نیست
                        response_time=sum(response_times) / len(response_times) if response_times else 0,
                        tokens_used=0,
                        cost=0,
                        analysis_report_id=analysis_id,
                        details={
                            "files_analyzed": len(micro_results.get("files", {})),
                            "avg_score": avg_score,
                            "issues_found": correct_findings
                        }
                    )
                    logger.info(f"پروفایل مدل {model_id} به‌روزرسانی شد - نمره: {avg_score:.1f}")

        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی پروفایل مدل‌ها: {e}")


# =====================================
# Singleton Instance
# =====================================

_deep_analysis_service = None

def get_deep_analysis_service(ai_manager=None) -> DeepAnalysisService:
    """دریافت instance سرویس تحلیل عمیق"""
    global _deep_analysis_service

    # اگر instance وجود نداره، ایجاد کن
    if _deep_analysis_service is None:
        logger.info(f"🔧 Creating new DeepAnalysisService, ai_manager provided: {ai_manager is not None}")
        _deep_analysis_service = DeepAnalysisService(ai_manager)
    elif ai_manager is not None:
        # همیشه ai_manager را به‌روزرسانی کن اگر داده شده (ممکنه مدل‌های جدیدی در دسترس باشن)
        old_has_manager = _deep_analysis_service.ai_manager is not None
        _deep_analysis_service.ai_manager = ai_manager
        logger.info(f"🔧 Updated AI Manager on DeepAnalysisService (had manager before: {old_has_manager})")

    # لاگ وضعیت فعلی
    current_manager = _deep_analysis_service.ai_manager
    if current_manager:
        try:
            models = current_manager.get_available_models()
            logger.info(f"🔧 DeepAnalysisService has {len(models)} available models")
        except Exception as e:
            logger.warning(f"🔧 Error checking available models: {e}")
    else:
        logger.warning(f"🔧 DeepAnalysisService has NO ai_manager!")

    return _deep_analysis_service
