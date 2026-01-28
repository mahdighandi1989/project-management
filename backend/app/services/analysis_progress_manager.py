# -*- coding: utf-8 -*-
"""
مدیر پیشرفت تحلیل - Analysis Progress Manager

این سرویس وضعیت تحلیل را در دیتابیس ذخیره می‌کند تا:
1. با جابجایی صفحه قطع نشود
2. قابلیت Pause/Resume داشته باشد
3. بعد از خطا بتواند ادامه دهد
"""

import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AnalysisProgressManager:
    """
    مدیر پیشرفت تحلیل

    این کلاس وضعیت تحلیل را در دیتابیس ذخیره و بازیابی می‌کند
    """

    def __init__(self, project_id: str, db_session=None):
        self.project_id = project_id
        self.db_session = db_session
        self._progress = {
            "status": "idle",  # idle, running, paused, completed, failed
            "analysis_id": None,
            "phase": "preparing",
            "total_files": 0,
            "analyzed_files": 0,
            "completed_files": [],
            "current_file": "",
            "current_model": "",
            "model_statuses": {},
            "started_at": None,
            "last_update": None,
            "elapsed_time": 0,
            "issues_found": 0,
            "partial_results": {},
            "error": None,
            "message": ""
        }
        self._pause_requested = False
        self._stop_requested = False
        self._last_save_time = 0
        self._save_interval = 2  # ذخیره هر 2 ثانیه

    def load_progress(self) -> Dict:
        """بارگذاری وضعیت از دیتابیس"""
        if not self.db_session:
            return self._progress

        try:
            from ..models.project import Project
            project = self.db_session.query(Project).filter(Project.id == self.project_id).first()
            if project and project.analysis_progress:
                saved = json.loads(project.analysis_progress)
                self._progress.update(saved)
                logger.info(f"Loaded analysis progress for {self.project_id}: status={self._progress['status']}")
        except Exception as e:
            logger.error(f"Error loading progress: {e}")

        return self._progress

    def save_progress(self, force: bool = False):
        """ذخیره وضعیت در دیتابیس"""
        if not self.db_session:
            return

        # ذخیره فقط اگر زمان کافی گذشته یا force=True
        current_time = time.time()
        if not force and (current_time - self._last_save_time) < self._save_interval:
            return

        try:
            from ..models.project import Project
            project = self.db_session.query(Project).filter(Project.id == self.project_id).first()
            if project:
                self._progress["last_update"] = datetime.now().isoformat()
                project.analysis_progress = json.dumps(self._progress, ensure_ascii=False, default=str)
                self.db_session.commit()
                self._last_save_time = current_time
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
            try:
                self.db_session.rollback()
            except:
                pass

    def start_analysis(self, analysis_id: str, total_files: int, model_ids: List[str]):
        """شروع تحلیل جدید"""
        self._progress = {
            "status": "running",
            "analysis_id": analysis_id,
            "phase": "preparing",
            "total_files": total_files,
            "analyzed_files": 0,
            "completed_files": [],
            "current_file": "",
            "current_model": "",
            "model_statuses": {m: "waiting" for m in model_ids},
            "started_at": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "elapsed_time": 0,
            "issues_found": 0,
            "partial_results": {
                "micro_analysis": {"files": {}},
                "macro_analysis": {},
                "structural_analysis": {}
            },
            "error": None,
            "message": f"شروع تحلیل {total_files} فایل با {len(model_ids)} مدل"
        }
        self._pause_requested = False
        self._stop_requested = False
        self.save_progress(force=True)

    def can_resume(self) -> bool:
        """آیا می‌توان تحلیل را ادامه داد؟"""
        return self._progress["status"] in ["paused", "failed"] and len(self._progress["completed_files"]) > 0

    def get_remaining_files(self, all_files: List[str]) -> List[str]:
        """دریافت فایل‌هایی که هنوز تحلیل نشده‌اند"""
        completed = set(self._progress["completed_files"])
        return [f for f in all_files if f not in completed]

    def update_phase(self, phase: str, message: str = ""):
        """به‌روزرسانی فاز تحلیل"""
        self._progress["phase"] = phase
        self._progress["message"] = message or f"فاز {phase}"
        self.save_progress()

    def start_file(self, file_path: str):
        """شروع تحلیل یک فایل"""
        self._progress["current_file"] = file_path
        self._progress["message"] = f"شروع تحلیل: {file_path.split('/')[-1]}"
        self.save_progress()

    def start_model(self, model_id: str):
        """شروع کار یک مدل"""
        self._progress["current_model"] = model_id
        self._progress["model_statuses"][model_id] = "working"
        self._progress["message"] = f"مدل {model_id.split('/')[-1]} در حال کار..."
        self.save_progress()

    def complete_model(self, model_id: str, success: bool = True):
        """اتمام کار یک مدل"""
        self._progress["model_statuses"][model_id] = "completed" if success else "failed"
        self.save_progress()

    def complete_file(self, file_path: str, result: Dict = None, issues: int = 0):
        """اتمام تحلیل یک فایل"""
        if file_path not in self._progress["completed_files"]:
            self._progress["completed_files"].append(file_path)
        self._progress["analyzed_files"] = len(self._progress["completed_files"])
        self._progress["issues_found"] += issues

        # ذخیره نتیجه جزئی
        if result:
            self._progress["partial_results"]["micro_analysis"]["files"][file_path] = result

        self._progress["message"] = f"تکمیل: {file_path.split('/')[-1]} ({self._progress['analyzed_files']}/{self._progress['total_files']})"
        self.save_progress()

    def save_macro_results(self, results: Dict):
        """ذخیره نتایج تحلیل Macro"""
        self._progress["partial_results"]["macro_analysis"] = results
        self.save_progress(force=True)

    def save_structural_results(self, results: Dict):
        """ذخیره نتایج تحلیل Structural"""
        self._progress["partial_results"]["structural_analysis"] = results
        self.save_progress(force=True)

    def complete_analysis(self, overall_score: float = 0, total_issues: int = 0):
        """اتمام تحلیل"""
        self._progress["status"] = "completed"
        self._progress["phase"] = "completed"
        self._progress["message"] = f"تحلیل کامل شد! نمره: {overall_score:.0f}"
        self._progress["elapsed_time"] = self._calculate_elapsed()
        self.save_progress(force=True)

    def fail_analysis(self, error: str):
        """خطا در تحلیل"""
        self._progress["status"] = "failed"
        self._progress["error"] = error
        self._progress["message"] = f"خطا: {error}"
        self.save_progress(force=True)

    def pause_analysis(self):
        """درخواست توقف موقت"""
        self._pause_requested = True
        self._progress["status"] = "paused"
        self._progress["message"] = "تحلیل متوقف شد"
        self.save_progress(force=True)

    def resume_analysis(self):
        """ادامه تحلیل"""
        self._pause_requested = False
        self._progress["status"] = "running"
        self._progress["message"] = "ادامه تحلیل..."
        self.save_progress(force=True)

    def stop_analysis(self):
        """توقف کامل"""
        self._stop_requested = True
        self._progress["status"] = "stopped"
        self._progress["message"] = "تحلیل متوقف شد"
        self.save_progress(force=True)

    def clear_progress(self):
        """پاک کردن وضعیت"""
        self._progress = {
            "status": "idle",
            "analysis_id": None,
            "phase": "preparing",
            "total_files": 0,
            "analyzed_files": 0,
            "completed_files": [],
            "current_file": "",
            "current_model": "",
            "model_statuses": {},
            "started_at": None,
            "last_update": None,
            "elapsed_time": 0,
            "issues_found": 0,
            "partial_results": {},
            "error": None,
            "message": ""
        }
        self._pause_requested = False
        self._stop_requested = False
        self.save_progress(force=True)

    def should_pause(self) -> bool:
        """آیا باید متوقف شود؟"""
        return self._pause_requested

    def should_stop(self) -> bool:
        """آیا باید کاملاً متوقف شود؟"""
        return self._stop_requested

    def get_progress(self) -> Dict:
        """دریافت وضعیت فعلی"""
        self._progress["elapsed_time"] = self._calculate_elapsed()
        return self._progress.copy()

    def get_progress_percentage(self) -> float:
        """محاسبه درصد پیشرفت"""
        total = self._progress["total_files"]
        if total == 0:
            return 0

        analyzed = self._progress["analyzed_files"]
        phase = self._progress["phase"]

        # وزن‌دهی به فازها
        if phase == "micro":
            return (analyzed / total) * 60
        elif phase == "macro":
            return 60 + 20
        elif phase == "structural":
            return 80 + 15
        elif phase == "completed":
            return 100

        return (analyzed / total) * 100

    def _calculate_elapsed(self) -> float:
        """محاسبه زمان سپری شده"""
        if not self._progress["started_at"]:
            return 0
        try:
            started = datetime.fromisoformat(self._progress["started_at"])
            return (datetime.now() - started).total_seconds()
        except:
            return 0


# =====================================
# توابع کمکی
# =====================================

def get_analysis_progress(project_id: str, db_session=None) -> Dict:
    """دریافت وضعیت تحلیل یک پروژه"""
    manager = AnalysisProgressManager(project_id, db_session)
    return manager.load_progress()


def pause_analysis(project_id: str, db_session=None):
    """توقف موقت تحلیل"""
    manager = AnalysisProgressManager(project_id, db_session)
    manager.load_progress()
    manager.pause_analysis()


def resume_analysis(project_id: str, db_session=None):
    """ادامه تحلیل"""
    manager = AnalysisProgressManager(project_id, db_session)
    manager.load_progress()
    manager.resume_analysis()


def stop_analysis(project_id: str, db_session=None):
    """توقف کامل تحلیل"""
    manager = AnalysisProgressManager(project_id, db_session)
    manager.load_progress()
    manager.stop_analysis()
