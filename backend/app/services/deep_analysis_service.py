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
from typing import Dict, List, Optional, Any, Tuple
import logging
import re
import os

logger = logging.getLogger(__name__)


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

    def __init__(self, ai_manager=None):
        """
        مقداردهی اولیه

        Args:
            ai_manager: مدیر مدل‌های AI (برای فراخوانی مدل‌ها)
        """
        self.ai_manager = ai_manager
        self.analysis_factors = DEFAULT_ANALYSIS_FACTORS.copy()

    async def run_full_analysis(
        self,
        project_id: str,
        files: List[Dict],
        roadmap_content: str = "",
        readme_content: str = "",
        model_ids: List[str] = None,
        instruction: str = "",
        db_session=None
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

        Returns:
            نتایج کامل تحلیل
        """
        analysis_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        logger.info(f"[{analysis_id}] شروع تحلیل عمیق پروژه {project_id}")

        # اگر مدل مشخص نشده، از مدل‌های پیش‌فرض استفاده کن
        if not model_ids:
            model_ids = await self._get_available_models()

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

            logger.info(f"[{analysis_id}] تحلیل کامل شد. نمره کلی: {final_results['overall_scores'].get('total', 0):.1f}")

        except Exception as e:
            logger.error(f"[{analysis_id}] خطا در تحلیل: {str(e)}")
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
        """
        results = {
            "files": {},
            "summary": {
                "total_files": len(files),
                "analyzed": 0,
                "issues_found": 0
            }
        }

        # تحلیل موازی فایل‌ها با چند مدل
        tasks = []
        for file_data in files:
            file_path = file_data.get("path", file_data.get("file_path", ""))
            content = file_data.get("content", "")

            if not content or len(content) < 10:
                continue

            # برای هر فایل، تحلیل با همه مدل‌ها
            task = self._analyze_single_file_with_models(
                file_path=file_path,
                content=content,
                roadmap_content=roadmap_content,
                model_ids=model_ids,
                instruction=instruction
            )
            tasks.append(task)

        # اجرای موازی
        if tasks:
            file_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in file_results:
                if isinstance(result, Exception):
                    logger.error(f"خطا در تحلیل فایل: {result}")
                    continue

                if result and result.get("file_path"):
                    results["files"][result["file_path"]] = result
                    results["summary"]["analyzed"] += 1
                    results["summary"]["issues_found"] += len(result.get("issues", []))

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

        # تحلیل با هر مدل
        model_tasks = []
        for model_id in model_ids:
            task = self._call_ai_model(model_id, prompt)
            model_tasks.append((model_id, task))

        # اجرای موازی
        for model_id, task in model_tasks:
            try:
                response = await task
                analysis = self._parse_model_response(response)
                result["model_analyses"][model_id] = analysis
            except Exception as e:
                logger.error(f"خطا در تحلیل {file_path} با مدل {model_id}: {e}")
                result["model_analyses"][model_id] = {"error": str(e)}

        # میانگین‌گیری نمرات
        result["aggregated_scores"] = self._aggregate_scores(result["model_analyses"])
        result["issues"] = self._collect_issues(result["model_analyses"], file_path)

        return result

    def _build_micro_analysis_prompt(
        self,
        file_path: str,
        content: str,
        roadmap_content: str,
        instruction: str
    ) -> str:
        """ساخت پرامپت تحلیل جزئی"""

        prompt = f"""# تحلیل جزئی فایل (Micro Analysis)

## فایل: {file_path}

## دستورات:
{instruction if instruction else "تحلیل کامل و دقیق فایل را انجام بده."}

## محتوای فایل:
```
{content[:15000]}  # محدودیت برای مدل‌ها
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

## فرمت خروجی (JSON):
```json
{{
    "scores": {{
        "code_quality": 0-100,
        "documentation": 0-100,
        "roadmap_compliance": 0-100,
        "security": 0-100,
        "efficiency": 0-100,
        "standards_compliance": 0-100
    }},
    "issues": [
        {{
            "line": شماره خط,
            "severity": "critical|high|medium|low",
            "type": "bug|security|quality|performance",
            "message": "توضیح مشکل",
            "suggestion": "پیشنهاد رفع"
        }}
    ],
    "summary": "خلاصه یک خطی وضعیت فایل",
    "strengths": ["نقاط قوت"],
    "weaknesses": ["نقاط ضعف"]
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

        file_list = "\n".join([f"- {f.get('path', f.get('file_path', ''))}" for f in files[:100]])

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
        "description": "توضیح ساختار ایده‌آل"
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

        # دسته‌بندی فایل‌ها
        categories = {
            "backend": [],
            "frontend": [],
            "config": [],
            "tests": [],
            "docs": [],
            "other": []
        }

        for file_data in files:
            path = file_data.get("path", file_data.get("file_path", "")).lower()

            if any(x in path for x in ["api", "routes", "services", "models", "backend"]):
                categories["backend"].append(path)
            elif any(x in path for x in ["components", "pages", "frontend", "src/app"]):
                categories["frontend"].append(path)
            elif any(x in path for x in ["config", ".env", "settings", "package.json", "requirements"]):
                categories["config"].append(path)
            elif "test" in path:
                categories["tests"].append(path)
            elif any(x in path for x in ["readme", "doc", ".md"]):
                categories["docs"].append(path)
            else:
                categories["other"].append(path)

        for cat, cat_files in categories.items():
            if cat_files:
                overview.append(f"\n### {cat.upper()} ({len(cat_files)} فایل):")
                for f in cat_files[:20]:
                    micro = micro_results.get("files", {}).get(f, {})
                    score = micro.get("aggregated_scores", {}).get("total", "?")
                    overview.append(f"  - {f} (نمره: {score})")

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

    async def _call_ai_model(self, model_id: str, prompt: str) -> str:
        """فراخوانی مدل AI"""
        if self.ai_manager:
            try:
                result = await self.ai_manager.call_model(
                    model_id=model_id,
                    prompt=prompt,
                    max_tokens=4000
                )
                return result.get("content", result.get("response", ""))
            except Exception as e:
                logger.error(f"خطا در فراخوانی مدل {model_id}: {e}")
                raise
        else:
            # برای تست بدون AI manager
            return "{}"

    async def _get_available_models(self) -> List[str]:
        """دریافت لیست مدل‌های در دسترس"""
        if self.ai_manager:
            try:
                models = await self.ai_manager.get_available_models()
                return [m["id"] for m in models if m.get("available")][:3]
            except:
                pass
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
        all_scores = {}

        for model_id, analysis in model_analyses.items():
            if isinstance(analysis, dict) and "scores" in analysis:
                for key, value in analysis["scores"].items():
                    if key not in all_scores:
                        all_scores[key] = []
                    if isinstance(value, (int, float)):
                        all_scores[key].append(value)

        aggregated = {}
        for key, values in all_scores.items():
            if values:
                aggregated[key] = sum(values) / len(values)

        # محاسبه نمره کلی
        if aggregated:
            aggregated["total"] = sum(aggregated.values()) / len(aggregated)

        return aggregated

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
        # پیاده‌سازی ساده - میانگین نمرات
        scores = {"cooperation_score": [], "roadmap_score": [], "overall_health": []}

        for model_id, result in model_results.items():
            if isinstance(result, dict):
                if "roadmap_compliance" in result:
                    rc = result["roadmap_compliance"]
                    if isinstance(rc, dict) and "overall_score" in rc:
                        scores["roadmap_score"].append(rc["overall_score"])
                if "overall_health" in result:
                    scores["overall_health"].append(result["overall_health"])

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

        # ساخت file_health_map با رنگ‌بندی
        file_health_map = {}
        for file_path, file_data in micro_results.get("files", {}).items():
            scores = file_data.get("aggregated_scores", {})
            total_score = scores.get("total", 50)

            color_info = get_health_color(total_score)

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
                "issues_count": len(file_data.get("issues", [])),
                "analyzed_at": file_data.get("analyzed_at")
            }

        # نمرات کلی
        micro_score = micro_results.get("summary", {}).get("analyzed", 0)
        macro_score = macro_results.get("aggregated", {}).get("overall_health", 50)
        structural_score = structural_results.get("aggregated", {}).get("overall_score", 50)

        # میانگین نمرات فایل‌ها
        file_scores = [f["score"] for f in file_health_map.values()]
        avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 50

        overall_scores = {
            "micro": avg_file_score,
            "macro": macro_score,
            "structural": structural_score,
            "total": (avg_file_score * 0.4 + macro_score * 0.3 + structural_score * 0.3)
        }

        # جمع‌آوری همه مشکلات
        all_issues = []
        for file_path, file_data in micro_results.get("files", {}).items():
            all_issues.extend(file_data.get("issues", []))

        # مرتب‌سازی بر اساس شدت
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))

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

        # حالت ایده‌آل
        ideal_state = ""
        for model_id, result in structural_results.get("model_analyses", {}).items():
            if isinstance(result, dict) and "ideal_structure" in result:
                ideal = result["ideal_structure"]
                if isinstance(ideal, dict):
                    ideal_state = ideal.get("description", "")
                    break

        return {
            "file_health_map": file_health_map,
            "overall_scores": overall_scores,
            "issues": all_issues[:100],  # محدود به 100 مشکل
            "recommendations": recommendations,
            "ideal_state": ideal_state
        }

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


# =====================================
# Singleton Instance
# =====================================

_deep_analysis_service = None

def get_deep_analysis_service(ai_manager=None) -> DeepAnalysisService:
    """دریافت instance سرویس تحلیل عمیق"""
    global _deep_analysis_service
    if _deep_analysis_service is None:
        _deep_analysis_service = DeepAnalysisService(ai_manager)
    return _deep_analysis_service
