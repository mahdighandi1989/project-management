# -*- coding: utf-8 -*-
"""
سرویس تحلیل سلامت پروژه و مدیریت Roadmap/README
Project Health Analyzer & Roadmap Manager

قابلیت‌ها:
1. بررسی و ایجاد/به‌روزرسانی فایل roadmap
2. بررسی و ایجاد/به‌روزرسانی فایل README
3. تحلیل کامل ساختار پروژه
4. تحلیل موازی توسط چند مدل AI
5. نمره‌دهی و رنگ‌بندی سلامت
6. شناسایی حالت ایده‌آل
"""

import asyncio
import json
import uuid
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..core.database import SessionLocal
from ..models.project import Project, ProjectFile
from .ai_manager import get_ai_manager
from .ai_base import Message
from .model_profiler import get_model_profiler

logger = logging.getLogger(__name__)


# =====================================================
# تنظیمات و ثابت‌ها
# =====================================================

ROADMAP_FILENAMES = ['ROADMAP.md', 'roadmap.md', 'ROADMAP.MD', 'Roadmap.md', 'نقشه_راه.md']
README_FILENAMES = ['README.md', 'readme.md', 'README.MD', 'Readme.md']

DEFAULT_ANALYSIS_SETTINGS = {
    "instruction": "تمام پروژه را از ریز تا درشت بررسی کن و ساختار کامل آن را استخراج کن",
    "target_models": ["all"],
    "trigger_enabled": True,
    "trigger_interval_minutes": 30,
    "trigger_interval_type": "minutes",
    "auto_analyze_on_import": True,
    "criteria_weights": {
        "code_quality": 0.25,
        "documentation": 0.15,
        "security": 0.20,
        "structure": 0.20,
        "roadmap_compliance": 0.20
    }
}


# =====================================================
# کلاس اصلی تحلیل‌گر سلامت پروژه
# =====================================================

class ProjectHealthAnalyzer:
    """
    تحلیل‌گر جامع سلامت پروژه

    - بررسی ساختار کامل
    - مدیریت roadmap و readme
    - تحلیل موازی با چند مدل
    - نمره‌دهی و رنگ‌بندی
    """

    def __init__(self):
        self.ai_manager = None
        self.model_profiler = None

    def initialize(self):
        """راه‌اندازی سرویس"""
        self.ai_manager = get_ai_manager()
        self.model_profiler = get_model_profiler()
        logger.info("ProjectHealthAnalyzer initialized")

    # =================================================
    # بخش ۱: مدیریت Roadmap و README
    # =================================================

    async def check_and_manage_roadmap(
        self,
        project_id: str,
        files: List[Dict],
        project_info: Dict,
        model_id: str = None
    ) -> Dict[str, Any]:
        """
        بررسی و مدیریت فایل roadmap

        - اگر وجود دارد: بررسی مطابقت و ارتقا
        - اگر وجود ندارد: ایجاد
        """
        if not self.ai_manager:
            self.initialize()

        # جستجوی فایل roadmap
        roadmap_file = None
        roadmap_content = ""

        for f in files:
            path = f.get("path", f.get("file_path", ""))
            filename = os.path.basename(path)
            if filename in ROADMAP_FILENAMES:
                roadmap_file = f
                roadmap_content = f.get("content", "")
                break

        result = {
            "roadmap_exists": roadmap_file is not None,
            "roadmap_path": roadmap_file.get("path") if roadmap_file else None,
            "action_taken": None,
            "roadmap_content": None,
            "issues_found": [],
            "ideal_state": None
        }

        # انتخاب مدل
        if not model_id:
            available = self.ai_manager.get_available_models()
            model_id = available[0].id if available else "claude"

        # آنالیز ساختار پروژه برای تولید roadmap
        project_structure = self._analyze_project_structure(files)

        if roadmap_file and roadmap_content:
            # بررسی مطابقت و ارتقا
            result["action_taken"] = "verify_and_upgrade"
            upgraded = await self._verify_and_upgrade_roadmap(
                roadmap_content,
                project_structure,
                project_info,
                files,
                model_id
            )
            result["roadmap_content"] = upgraded["content"]
            result["issues_found"] = upgraded.get("issues", [])
            result["ideal_state"] = upgraded.get("ideal_state", "")
            result["compliance_score"] = upgraded.get("compliance_score", 0)
        else:
            # ایجاد roadmap جدید
            result["action_taken"] = "create_new"
            new_roadmap = await self._create_roadmap(
                project_structure,
                project_info,
                files,
                model_id
            )
            result["roadmap_content"] = new_roadmap["content"]
            result["roadmap_path"] = "ROADMAP.md"
            result["ideal_state"] = new_roadmap.get("ideal_state", "")
            result["issues_found"] = new_roadmap.get("issues", [])

        return result

    async def check_and_manage_readme(
        self,
        project_id: str,
        files: List[Dict],
        project_info: Dict,
        roadmap_content: str = None,
        model_id: str = None
    ) -> Dict[str, Any]:
        """
        بررسی و مدیریت فایل README
        """
        if not self.ai_manager:
            self.initialize()

        # جستجوی فایل README
        readme_file = None
        readme_content = ""

        for f in files:
            path = f.get("path", f.get("file_path", ""))
            filename = os.path.basename(path)
            if filename in README_FILENAMES:
                readme_file = f
                readme_content = f.get("content", "")
                break

        result = {
            "readme_exists": readme_file is not None,
            "readme_path": readme_file.get("path") if readme_file else None,
            "action_taken": None,
            "readme_content": None
        }

        if not model_id:
            available = self.ai_manager.get_available_models()
            model_id = available[0].id if available else "claude"

        project_structure = self._analyze_project_structure(files)

        if readme_file and readme_content:
            # ارتقای README موجود
            result["action_taken"] = "upgrade"
            upgraded = await self._upgrade_readme(
                readme_content,
                project_structure,
                project_info,
                roadmap_content,
                model_id
            )
            result["readme_content"] = upgraded["content"]
        else:
            # ایجاد README جدید
            result["action_taken"] = "create_new"
            new_readme = await self._create_readme(
                project_structure,
                project_info,
                roadmap_content,
                model_id
            )
            result["readme_content"] = new_readme["content"]
            result["readme_path"] = "README.md"

        return result

    async def _verify_and_upgrade_roadmap(
        self,
        current_roadmap: str,
        structure: Dict,
        project_info: Dict,
        files: List[Dict],
        model_id: str
    ) -> Dict[str, Any]:
        """بررسی مطابقت و ارتقای roadmap"""

        prompt = f"""تو یک معمار نرم‌افزار متخصص هستی. این فایل نقشه راه (ROADMAP) را با ساختار واقعی پروژه مقایسه کن.

## نقشه راه فعلی:
```markdown
{current_roadmap[:8000]}
```

## ساختار واقعی پروژه:
- **نام**: {project_info.get('name', 'نامشخص')}
- **نوع**: {project_info.get('type', 'نامشخص')}
- **زبان اصلی**: {structure.get('language', 'نامشخص')}
- **فریم‌ورک‌ها**: {', '.join(structure.get('frameworks', []))}
- **تعداد فایل**: {structure.get('file_count', 0)}

## فایل‌های موجود:
{chr(10).join(['- ' + f.get('path', '') for f in files[:50]])}

## وظیفه تو:
1. بررسی کن آیا نقشه راه با وضعیت واقعی پروژه مطابقت دارد
2. ایرادات و عدم تطابق‌ها را شناسایی کن
3. نقشه راه را ارتقا بده و کامل‌تر کن
4. حالت ایده‌آل برنامه را توضیح بده

پاسخ را به صورت JSON بده:
{{
    "compliance_score": 0-100,
    "issues": [
        {{"type": "missing|outdated|incorrect", "description": "توضیح"}}
    ],
    "ideal_state": "توضیح کامل حالت ایده‌آل برنامه (۵۰۰+ کاراکتر)",
    "content": "متن کامل ROADMAP ارتقا یافته به فرمت Markdown"
}}"""

        try:
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000,
                temperature=0.5
            )

            result = self._extract_json(response.content)
            return result

        except Exception as e:
            logger.error(f"Error upgrading roadmap: {e}", exc_info=True)
            return {
                "content": current_roadmap,
                "issues": [{"type": "error", "description": str(e)}],
                "ideal_state": "",
                "compliance_score": 50
            }

    async def _create_roadmap(
        self,
        structure: Dict,
        project_info: Dict,
        files: List[Dict],
        model_id: str
    ) -> Dict[str, Any]:
        """ایجاد فایل ROADMAP جدید"""

        # نمونه‌ای از محتوای فایل‌های مهم
        important_files_content = ""
        for f in files[:10]:
            content = f.get("content", "")
            if content:
                important_files_content += f"\n### {f.get('path', 'unknown')}\n```\n{content[:1000]}\n```\n"

        prompt = f"""تو یک معمار نرم‌افزار متخصص هستی. برای این پروژه یک فایل ROADMAP.md جامع و کامل بساز.

## اطلاعات پروژه:
- **نام**: {project_info.get('name', 'نامشخص')}
- **توضیحات**: {project_info.get('description', 'ندارد')}
- **نوع**: {project_info.get('type', 'نامشخص')}
- **زبان اصلی**: {structure.get('language', 'نامشخص')}
- **فریم‌ورک‌ها**: {', '.join(structure.get('frameworks', []))}

## فایل‌های موجود:
{chr(10).join(['- ' + f.get('path', '') for f in files[:50]])}

## نمونه محتوای فایل‌ها:
{important_files_content[:6000]}

## ROADMAP باید شامل این بخش‌ها باشد:
1. **خلاصه اجرایی** - معرفی کوتاه پروژه
2. **وضعیت فعلی** - چه چیزی پیاده‌سازی شده
3. **ایرادات و باگ‌ها** - مشکلات شناسایی شده
4. **حالت ایده‌آل** (مهم!) - برنامه در حالت ایده‌آل چطور باید باشد
5. **فازهای توسعه** - مراحل بعدی
6. **معیارهای موفقیت** - KPIها

پاسخ را به صورت JSON بده:
{{
    "content": "متن کامل ROADMAP.md به فرمت Markdown (حداقل ۲۰۰۰ کاراکتر)",
    "issues": [{{"type": "bug|missing|improvement", "description": "توضیح", "severity": "high|medium|low"}}],
    "ideal_state": "توضیح کامل و جامع حالت ایده‌آل برنامه"
}}"""

        try:
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000,
                temperature=0.6
            )

            result = self._extract_json(response.content)
            return result

        except Exception as e:
            logger.error(f"Error creating roadmap: {e}")
            return self._create_fallback_roadmap(project_info, structure)

    async def _create_readme(
        self,
        structure: Dict,
        project_info: Dict,
        roadmap_content: str,
        model_id: str
    ) -> Dict[str, Any]:
        """ایجاد فایل README جدید"""

        prompt = f"""تو یک توسعه‌دهنده ارشد هستی. برای این پروژه یک فایل README.md حرفه‌ای بساز.

## اطلاعات پروژه:
- **نام**: {project_info.get('name', 'نامشخص')}
- **توضیحات**: {project_info.get('description', 'ندارد')}
- **نوع**: {project_info.get('type', 'نامشخص')}
- **زبان**: {structure.get('language', 'نامشخص')}
- **فریم‌ورک‌ها**: {', '.join(structure.get('frameworks', []))}

## نقشه راه (اگر موجود است):
{roadmap_content[:3000] if roadmap_content else 'ندارد'}

README باید شامل این بخش‌ها باشد:
1. معرفی پروژه با آیکون/بنر
2. قابلیت‌ها (Features)
3. پیش‌نیازها (Prerequisites)
4. نصب و راه‌اندازی (Installation)
5. نحوه استفاده (Usage)
6. ساختار پروژه (Project Structure)
7. مشارکت (Contributing)
8. مجوز (License)

پاسخ فقط متن README.md به فرمت Markdown باشد (بدون JSON)."""

        try:
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=3000,
                temperature=0.6
            )

            return {"content": response.content}

        except Exception as e:
            logger.error(f"Error creating readme: {e}")
            return {"content": self._create_fallback_readme(project_info, structure)}

    async def _upgrade_readme(
        self,
        current_readme: str,
        structure: Dict,
        project_info: Dict,
        roadmap_content: str,
        model_id: str
    ) -> Dict[str, Any]:
        """ارتقای README موجود"""

        prompt = f"""این README.md موجود را بررسی و ارتقا بده:

## README فعلی:
```markdown
{current_readme[:5000]}
```

## اطلاعات پروژه:
- نام: {project_info.get('name')}
- زبان: {structure.get('language')}
- فریم‌ورک‌ها: {', '.join(structure.get('frameworks', []))}

موارد زیر را بهبود بده:
- بخش‌های ناقص را کامل کن
- اطلاعات قدیمی را به‌روز کن
- بخش‌های مفقود را اضافه کن

پاسخ فقط متن README.md ارتقا یافته به فرمت Markdown باشد."""

        try:
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=3000,
                temperature=0.5
            )

            return {"content": response.content}

        except Exception as e:
            logger.error(f"Error upgrading readme: {e}")
            return {"content": current_readme}

    # =================================================
    # بخش ۲: تحلیل موازی با چند مدل
    # =================================================

    async def analyze_project_parallel(
        self,
        project_id: str,
        files: List[Dict],
        project_info: Dict,
        model_ids: List[str],
        roadmap_content: str = None,
        full_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        تحلیل موازی پروژه توسط چندین مدل (نه همکاری)

        هر مدل به صورت مستقل تحلیل می‌کند و نتایج ترکیب می‌شوند
        """
        if not self.ai_manager:
            self.initialize()

        analysis_id = f"health_{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow()

        result = {
            "analysis_id": analysis_id,
            "project_id": project_id,
            "status": "running",
            "started_at": start_time.isoformat(),
            "models_used": model_ids,
            "file_analyses": [],
            "structure_analysis": {},
            "overall_scores": {},
            "color_map": {},  # رنگ‌بندی برای دیاگرام
            "recommendations": [],
            "ideal_state": "",
            "model_results": {}
        }

        try:
            # ۱. تحلیل موازی هر فایل توسط همه مدل‌ها
            if full_analysis:
                file_analyses = await self._analyze_files_parallel(
                    files, model_ids, roadmap_content
                )
                result["file_analyses"] = file_analyses

                # ساخت color_map برای دیاگرام
                result["color_map"] = self._build_color_map(file_analyses)

            # ۲. تحلیل ساختار کلی و سیم‌کشی
            structure_analysis = await self._analyze_structure_parallel(
                files, model_ids, roadmap_content
            )
            result["structure_analysis"] = structure_analysis

            # ۳. محاسبه نمرات کلی
            result["overall_scores"] = self._calculate_overall_scores(
                result["file_analyses"],
                structure_analysis
            )

            # ۴. تولید پیشنهادات
            result["recommendations"] = self._generate_recommendations(
                result["file_analyses"],
                structure_analysis,
                result["overall_scores"]
            )

            # ۵. استخراج حالت ایده‌آل
            result["ideal_state"] = structure_analysis.get("ideal_state", "")

            result["status"] = "completed"
            result["completed_at"] = datetime.utcnow().isoformat()

            # به‌روزرسانی پروفایل مدل‌ها
            await self._update_model_profiles(analysis_id, model_ids, result)

        except Exception as e:
            logger.error(f"Parallel analysis failed: {e}", exc_info=True)
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    async def _analyze_files_parallel(
        self,
        files: List[Dict],
        model_ids: List[str],
        roadmap_content: str
    ) -> List[Dict]:
        """تحلیل موازی همه فایل‌ها"""

        file_analyses = []

        # فیلتر فایل‌های قابل تحلیل
        analyzable_files = [
            f for f in files
            if self._is_analyzable_file(f.get("path", ""))
        ]

        for file in analyzable_files[:50]:  # حداکثر 50 فایل
            file_path = file.get("path", file.get("file_path", ""))
            file_content = file.get("content", "")

            if not file_content or len(file_content) < 10:
                continue

            # تحلیل موازی این فایل توسط همه مدل‌ها
            tasks = []
            for model_id in model_ids:
                task = self._analyze_single_file(
                    file_path, file_content, model_id, roadmap_content
                )
                tasks.append((model_id, task))

            # اجرای موازی
            model_results = {}
            results = await asyncio.gather(
                *[t[1] for t in tasks],
                return_exceptions=True
            )

            for i, (model_id, _) in enumerate(tasks):
                res = results[i]
                if isinstance(res, Exception):
                    logger.error(f"File analysis error for {model_id}: {res}")
                    model_results[model_id] = {"error": str(res), "score": 0}
                else:
                    model_results[model_id] = res

            # میانگین نمرات مدل‌ها
            avg_scores = self._calculate_average_scores(model_results)

            file_analysis = {
                "file_path": file_path,
                "model_results": model_results,
                "average_scores": avg_scores,
                "overall_score": avg_scores.get("overall", 0),
                "color": self._score_to_color(avg_scores.get("overall", 0)),
                "analyzed_at": datetime.utcnow().isoformat(),
                "models_count": len(model_ids)
            }

            file_analyses.append(file_analysis)

        return file_analyses

    async def _analyze_single_file(
        self,
        file_path: str,
        content: str,
        model_id: str,
        roadmap_content: str
    ) -> Dict:
        """تحلیل یک فایل توسط یک مدل"""

        prompt = f"""تو یک متخصص تحلیل کد هستی. این فایل را با دقت تمام بررسی کن.

## فایل: {file_path}
```
{content[:8000]}
```

## نقشه راه پروژه (برای مقایسه):
{roadmap_content[:2000] if roadmap_content else 'ندارد'}

## معیارهای بررسی:
1. **کیفیت کد** (0-100): خوانایی، استانداردها، DRY، SOLID
2. **مستندسازی** (0-100): کامنت‌ها، docstrings
3. **امنیت** (0-100): آسیب‌پذیری‌ها، hardcoded secrets
4. **همکاری با پروژه** (0-100): آیا در جای درست قرار دارد؟ سیم‌کشی درست است؟
5. **مطابقت با roadmap** (0-100): آیا با نقشه راه هماهنگ است؟

پاسخ را به صورت JSON بده:
{{
    "code_quality": 85,
    "documentation": 70,
    "security": 90,
    "cooperation": 80,
    "roadmap_compliance": 75,
    "overall": 80,
    "issues": [
        {{"severity": "high|medium|low", "line": 10, "message": "توضیح مشکل"}}
    ],
    "suggestions": ["پیشنهاد ۱", "پیشنهاد ۲"]
}}"""

        try:
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=1500,
                temperature=0.3
            )

            return self._extract_json(response.content)

        except Exception as e:
            logger.error(f"Error analyzing file {file_path} with {model_id}: {e}")
            return {"error": str(e), "overall": 0}

    async def _analyze_structure_parallel(
        self,
        files: List[Dict],
        model_ids: List[str],
        roadmap_content: str
    ) -> Dict:
        """تحلیل ساختار کلی و سیم‌کشی"""

        structure = self._analyze_project_structure(files)
        file_list = [f.get("path", "") for f in files[:100]]

        prompt = f"""تو یک معمار نرم‌افزار متخصص هستی. ساختار کلی این پروژه را بررسی کن.

## ساختار پروژه:
- زبان: {structure.get('language')}
- فریم‌ورک‌ها: {', '.join(structure.get('frameworks', []))}
- معماری: {structure.get('architecture')}
- تعداد فایل: {len(files)}

## فایل‌های موجود:
{chr(10).join(file_list)}

## نقشه راه:
{roadmap_content[:3000] if roadmap_content else 'ندارد'}

## وظایف بررسی:
1. **سیم‌کشی بین فایل‌ها**: آیا imports و exports درست هستند؟
2. **جایگاه فایل‌ها**: آیا هر فایل در جای مناسب قرار دارد؟
3. **فایل‌های کم**: چه فایل‌هایی باید اضافه شوند؟
4. **فایل‌های اضافی**: چه فایل‌هایی زائد هستند؟
5. **حالت ایده‌آل**: ساختار ایده‌آل این پروژه چگونه باید باشد؟

پاسخ JSON:
{{
    "wiring_score": 85,
    "structure_score": 80,
    "organization_score": 75,
    "overall_score": 80,
    "missing_files": [
        {{"path": "مسیر", "description": "توضیح", "priority": "high|medium|low"}}
    ],
    "redundant_files": [
        {{"path": "مسیر", "reason": "چرا زائد است"}}
    ],
    "wiring_issues": [
        {{"source": "فایل مبدا", "target": "فایل مقصد", "issue": "توضیح مشکل"}}
    ],
    "ideal_state": "توضیح کامل و جامع حالت ایده‌آل ساختار و سیم‌کشی (حداقل ۵۰۰ کاراکتر)",
    "recommendations": ["پیشنهاد ۱", "پیشنهاد ۲"]
}}"""

        # تحلیل توسط اولین مدل (ساختار یکبار تحلیل میشه)
        try:
            response = await self.ai_manager.generate(
                model_id=model_ids[0] if model_ids else "claude",
                messages=[Message(role="user", content=prompt)],
                max_tokens=2500,
                temperature=0.4
            )

            return self._extract_json(response.content)

        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return {
                "wiring_score": 50,
                "structure_score": 50,
                "overall_score": 50,
                "ideal_state": "",
                "error": str(e)
            }

    # =================================================
    # بخش ۳: محاسبه نمرات و رنگ‌بندی
    # =================================================

    def _calculate_average_scores(self, model_results: Dict) -> Dict:
        """محاسبه میانگین نمرات از چند مدل"""
        score_keys = ['code_quality', 'documentation', 'security', 'cooperation', 'roadmap_compliance', 'overall']
        averages = {}

        for key in score_keys:
            values = []
            for model_id, result in model_results.items():
                if isinstance(result, dict) and key in result:
                    values.append(result[key])

            if values:
                averages[key] = sum(values) / len(values)
            else:
                averages[key] = 0

        return averages

    def _calculate_overall_scores(
        self,
        file_analyses: List[Dict],
        structure_analysis: Dict
    ) -> Dict:
        """محاسبه نمرات کلی پروژه"""

        # میانگین نمرات فایل‌ها
        if file_analyses:
            file_scores = {
                'code_quality': sum(f.get('average_scores', {}).get('code_quality', 0) for f in file_analyses) / len(file_analyses),
                'documentation': sum(f.get('average_scores', {}).get('documentation', 0) for f in file_analyses) / len(file_analyses),
                'security': sum(f.get('average_scores', {}).get('security', 0) for f in file_analyses) / len(file_analyses),
                'cooperation': sum(f.get('average_scores', {}).get('cooperation', 0) for f in file_analyses) / len(file_analyses),
                'roadmap_compliance': sum(f.get('average_scores', {}).get('roadmap_compliance', 0) for f in file_analyses) / len(file_analyses),
            }
        else:
            file_scores = {'code_quality': 0, 'documentation': 0, 'security': 0, 'cooperation': 0, 'roadmap_compliance': 0}

        # نمره ساختار
        structure_score = structure_analysis.get('overall_score', 0)

        # میانگین وزن‌دار کلی
        weights = DEFAULT_ANALYSIS_SETTINGS['criteria_weights']
        overall = (
            file_scores['code_quality'] * weights['code_quality'] +
            file_scores['documentation'] * weights['documentation'] +
            file_scores['security'] * weights['security'] +
            file_scores['roadmap_compliance'] * weights['roadmap_compliance'] +
            structure_score * weights['structure']
        )

        return {
            'file_scores': file_scores,
            'structure_score': structure_score,
            'overall': overall,
            'overall_color': self._score_to_color(overall)
        }

    def _build_color_map(self, file_analyses: List[Dict]) -> Dict:
        """ساخت نقشه رنگی برای دیاگرام"""
        color_map = {}

        for fa in file_analyses:
            file_path = fa.get('file_path', '')
            score = fa.get('overall_score', 0)
            color = self._score_to_color(score)

            color_map[file_path] = {
                'score': score,
                'color': color,
                'hex': self._score_to_hex(score),
                'models_analyzed': fa.get('models_count', 0),
                'analyzed_at': fa.get('analyzed_at'),
                'model_scores': {
                    model_id: result.get('overall', 0)
                    for model_id, result in fa.get('model_results', {}).items()
                    if isinstance(result, dict)
                }
            }

        return color_map

    def _score_to_color(self, score: float) -> str:
        """تبدیل نمره به نام رنگ"""
        if score >= 90:
            return "green"
        elif score >= 70:
            return "yellow"
        elif score >= 50:
            return "orange"
        else:
            return "red"

    def _score_to_hex(self, score: float) -> str:
        """تبدیل نمره به رنگ HEX برای دیاگرام"""
        if score >= 90:
            return "#22c55e"  # green-500
        elif score >= 80:
            return "#84cc16"  # lime-500
        elif score >= 70:
            return "#eab308"  # yellow-500
        elif score >= 60:
            return "#f97316"  # orange-500
        elif score >= 50:
            return "#ef4444"  # red-500
        else:
            return "#dc2626"  # red-600

    # =================================================
    # توابع کمکی
    # =================================================

    def _analyze_project_structure(self, files: List[Dict]) -> Dict:
        """تحلیل ساختار پروژه"""
        structure = {
            "file_count": len(files),
            "language": "Unknown",
            "frameworks": [],
            "architecture": "Unknown",
            "directories": set(),
        }

        extensions = {}
        for f in files:
            path = f.get("path", f.get("file_path", ""))

            # شمارش پسوندها
            if "." in path:
                ext = path.split(".")[-1].lower()
                extensions[ext] = extensions.get(ext, 0) + 1

            # پوشه‌ها
            if "/" in path:
                dir_path = "/".join(path.split("/")[:-1])
                structure["directories"].add(dir_path)

            # تشخیص فریم‌ورک از محتوا
            content = f.get("content", "")
            if "from fastapi" in content or "FastAPI" in content:
                structure["frameworks"].append("FastAPI")
            if "import React" in content or "useState" in content:
                structure["frameworks"].append("React")
            if "from django" in content:
                structure["frameworks"].append("Django")
            if "express" in content.lower():
                structure["frameworks"].append("Express")

        # زبان اصلی
        lang_map = {"py": "Python", "js": "JavaScript", "ts": "TypeScript", "tsx": "TypeScript/React", "go": "Go", "rs": "Rust"}
        if extensions:
            top_ext = max(extensions, key=extensions.get)
            structure["language"] = lang_map.get(top_ext, top_ext.upper())

        structure["frameworks"] = list(set(structure["frameworks"]))
        structure["directories"] = list(structure["directories"])

        return structure

    def _is_analyzable_file(self, path: str) -> bool:
        """آیا فایل قابل تحلیل است"""
        analyzable_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.cpp', '.c', '.h'}
        for ext in analyzable_extensions:
            if path.endswith(ext):
                return True
        return False

    def _extract_json(self, text: str) -> Dict:
        """استخراج JSON از متن"""
        try:
            return json.loads(text)
        except:
            pass

        # جستجوی JSON در متن
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        return {"error": "Could not parse JSON", "raw": text[:500]}

    def _generate_recommendations(
        self,
        file_analyses: List[Dict],
        structure_analysis: Dict,
        overall_scores: Dict
    ) -> List[str]:
        """تولید پیشنهادات بهبود"""
        recommendations = []

        scores = overall_scores.get('file_scores', {})

        if scores.get('code_quality', 0) < 70:
            recommendations.append("بهبود کیفیت کد: رعایت استانداردها و اصول SOLID")
        if scores.get('documentation', 0) < 70:
            recommendations.append("افزودن مستندات: docstrings و کامنت‌های توضیحی")
        if scores.get('security', 0) < 70:
            recommendations.append("بررسی امنیتی: رفع آسیب‌پذیری‌های شناسایی‌شده")
        if overall_scores.get('structure_score', 0) < 70:
            recommendations.append("بهبود ساختار: سازماندهی بهتر فایل‌ها و پوشه‌ها")
        if scores.get('roadmap_compliance', 0) < 70:
            recommendations.append("هماهنگی با نقشه راه: تکمیل آیتم‌های باقی‌مانده")

        # از تحلیل ساختار
        if structure_analysis.get('missing_files'):
            recommendations.append(f"ایجاد {len(structure_analysis['missing_files'])} فایل مفقود")
        if structure_analysis.get('redundant_files'):
            recommendations.append(f"حذف {len(structure_analysis['redundant_files'])} فایل زائد")

        return recommendations

    async def _update_model_profiles(
        self,
        analysis_id: str,
        model_ids: List[str],
        result: Dict
    ):
        """به‌روزرسانی پروفایل مدل‌ها بر اساس تحلیل"""
        if not self.model_profiler:
            return

        for model_id in model_ids:
            try:
                # شمارش نتایج هر مدل
                findings_count = 0
                for fa in result.get('file_analyses', []):
                    model_result = fa.get('model_results', {}).get(model_id, {})
                    if isinstance(model_result, dict):
                        findings_count += len(model_result.get('issues', []))

                await self.model_profiler.update_profile(
                    model_id=model_id,
                    task_type="health_analysis",
                    correct_findings=findings_count,
                    total_expected=findings_count,
                    analysis_report_id=analysis_id
                )
            except Exception as e:
                logger.error(f"Error updating profile for {model_id}: {e}")

    def _create_fallback_roadmap(self, project_info: Dict, structure: Dict) -> Dict:
        """ایجاد roadmap پیش‌فرض"""
        content = f"""# نقشه راه پروژه - {project_info.get('name', 'پروژه')}

## خلاصه
{project_info.get('description', 'توضیحات پروژه')}

## وضعیت فعلی
- زبان: {structure.get('language', 'نامشخص')}
- فریم‌ورک: {', '.join(structure.get('frameworks', ['نامشخص']))}
- تعداد فایل: {structure.get('file_count', 0)}

## ایرادات شناسایی شده
- نیاز به بررسی بیشتر

## حالت ایده‌آل
- مستندسازی کامل
- تست‌های جامع
- ساختار استاندارد

## فازهای توسعه
1. بررسی و مستندسازی
2. رفع باگ‌ها
3. بهینه‌سازی
"""
        return {
            "content": content,
            "issues": [],
            "ideal_state": "نیاز به بررسی توسط AI"
        }

    def _create_fallback_readme(self, project_info: Dict, structure: Dict) -> str:
        """ایجاد README پیش‌فرض"""
        return f"""# {project_info.get('name', 'پروژه')}

{project_info.get('description', '')}

## نصب

```bash
# دستورات نصب
```

## استفاده

```bash
# دستورات اجرا
```

## ساختار پروژه

- زبان: {structure.get('language', 'نامشخص')}
- فریم‌ورک: {', '.join(structure.get('frameworks', []))}

## مجوز

MIT
"""


# =====================================================
# Singleton Instance
# =====================================================

_health_analyzer_instance: Optional[ProjectHealthAnalyzer] = None

def get_project_health_analyzer() -> ProjectHealthAnalyzer:
    """دریافت نمونه ProjectHealthAnalyzer"""
    global _health_analyzer_instance
    if _health_analyzer_instance is None:
        _health_analyzer_instance = ProjectHealthAnalyzer()
    return _health_analyzer_instance
