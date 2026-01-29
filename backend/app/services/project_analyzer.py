"""
سرویس تحلیل خودکار پروژه
Project Auto Analysis Service

تحلیل جامع پروژه توسط چندین مدل AI به صورت موازی
"""

import asyncio
import uuid
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import json

from ..core.database import SessionLocal
from ..models.analysis_report import (
    AnalysisReport, FileAnalysis, AnalysisSchedule,
    AnalysisReportSchema, FileAnalysisSchema
)
from .ai_manager import get_ai_manager
from .model_profiler import get_model_profiler

logger = logging.getLogger(__name__)


class ProjectAnalyzer:
    """
    تحلیل‌گر پروژه

    بررسی جامع و کامل هر فایل پروژه توسط چندین مدل AI به صورت موازی
    """

    def __init__(self):
        self.ai_manager = None
        self.model_profiler = None
        self.analysis_prompts = self._get_analysis_prompts()

    def initialize(self):
        """راه‌اندازی"""
        self.ai_manager = get_ai_manager()
        self.model_profiler = get_model_profiler()
        logger.info("ProjectAnalyzer initialized")

    def _get_analysis_prompts(self) -> Dict[str, str]:
        """پرامپت‌های تحلیل برای هر معیار"""
        return {
            "code_quality": """
تو یک متخصص تحلیل کد هستی. این فایل را بررسی کن و نمره 0 تا 100 بده:

معیارها:
- خوانایی و سادگی کد
- رعایت استانداردهای نام‌گذاری
- DRY (عدم تکرار)
- SOLID principles
- مدیریت خطا
- کارایی

فایل: {file_path}
```
{content}
```

پاسخ را به این فرمت JSON بده:
{{
  "score": 85,
  "issues": [
    {{"severity": "high|medium|low", "line": 10, "message": "توضیح مشکل"}}
  ],
  "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
}}
""",

            "documentation": """
این فایل را از نظر مستندسازی بررسی کن و نمره 0 تا 100 بده:

معیارها:
- وجود docstrings
- کامنت‌های توضیحی
- توضیح توابع و پارامترها
- خوانایی مستندات

فایل: {file_path}
```
{content}
```

پاسخ JSON:
{{
  "score": 70,
  "issues": [{{"severity": "medium", "message": "تابع X بدون docstring"}}],
  "suggestions": ["پیشنهاد"]
}}
""",

            "security": """
این فایل را از نظر امنیت بررسی کن و نمره 0 تا 100 بده:

معیارها:
- آسیب‌پذیری injection
- hardcoded secrets
- مدیریت ورودی کاربر
- امنیت داده‌ها
- OWASP Top 10

فایل: {file_path}
```
{content}
```

پاسخ JSON:
{{
  "score": 90,
  "vulnerabilities": [{{"severity": "critical|high|medium|low", "type": "نوع", "description": "توضیح"}}],
  "suggestions": ["پیشنهاد"]
}}
""",

            "best_practices": """
این فایل را از نظر بهترین روش‌ها بررسی کن و نمره 0 تا 100 بده:

معیارها:
- الگوهای طراحی
- Type hints
- Error handling
- Async best practices
- Testing considerations

فایل: {file_path}
```
{content}
```

پاسخ JSON:
{{
  "score": 75,
  "issues": [{{"type": "نوع", "message": "توضیح"}}],
  "suggestions": ["پیشنهاد"]
}}
""",

            "structure": """
این پروژه را از نظر ساختار بررسی کن:

ساختار پروژه:
{structure}

فایل‌های موجود:
{files}

پاسخ JSON:
{{
  "score": 80,
  "issues": [{{"type": "نوع", "message": "توضیح"}}],
  "missing_files": ["فایل‌های پیشنهادی"],
  "redundant_files": ["فایل‌های اضافی"],
  "suggestions": ["پیشنهاد"]
}}
""",

            "roadmap_compliance": """
این پروژه را با نقشه راه مقایسه کن:

نقشه راه:
{roadmap}

وضعیت فعلی پروژه:
{current_state}

پاسخ JSON:
{{
  "score": 60,
  "completed_items": ["آیتم‌های تکمیل‌شده"],
  "pending_items": ["آیتم‌های باقی‌مانده"],
  "deviations": ["انحرافات از نقشه راه"],
  "suggestions": ["پیشنهاد"]
}}
"""
        }

    async def analyze_project(
        self,
        project_id: str,
        project_path: str,
        models: List[str] = None,
        roadmap_path: str = None
    ) -> AnalysisReportSchema:
        """
        تحلیل کامل پروژه

        Args:
            project_id: شناسه پروژه
            project_path: مسیر پروژه
            models: لیست مدل‌ها (خالی = همه فعال)
            roadmap_path: مسیر فایل نقشه راه

        Returns:
            گزارش کامل تحلیل
        """
        if not self.ai_manager:
            self.initialize()

        # ایجاد گزارش
        report_id = f"analysis_{uuid.uuid4().hex[:8]}"
        report = AnalysisReport(
            id=report_id,
            project_id=project_id,
            status="running",
            models_used=models or []
        )

        # ذخیره در دیتابیس
        db = SessionLocal()
        try:
            db.add(report)
            db.commit()

            # انتخاب مدل‌ها (فقط مدل‌های مجاز برای analysis)
            if not models:
                available = self.ai_manager.get_available_models(task_type="analysis")
                models = [m.id for m in available[:3]]  # حداکثر 3 مدل

            report.models_used = models

            # جمع‌آوری فایل‌ها
            files = self._collect_files(project_path)
            logger.info(f"Found {len(files)} files to analyze")

            # خواندن نقشه راه
            roadmap_content = None
            if roadmap_path and os.path.exists(roadmap_path):
                with open(roadmap_path, 'r', encoding='utf-8') as f:
                    roadmap_content = f.read()

            # تحلیل هر فایل با هر مدل (موازی)
            file_analyses = []
            all_issues = []

            for file_path, content in files.items():
                logger.info(f"Analyzing: {file_path}")
                file_analysis = await self._analyze_file(
                    file_path, content, models, report_id
                )
                file_analyses.append(file_analysis)
                all_issues.extend(file_analysis.get('issues', []))

            # تحلیل ساختار
            structure_analysis = await self._analyze_structure(
                project_path, files, models[0] if models else None
            )

            # مقایسه با نقشه راه
            roadmap_comparison = {}
            if roadmap_content:
                roadmap_comparison = await self._compare_with_roadmap(
                    roadmap_content,
                    self._get_project_state(files),
                    models[0] if models else None
                )

            # محاسبه نمرات کلی
            scores = self._calculate_overall_scores(file_analyses, structure_analysis, roadmap_comparison)

            # به‌روزرسانی گزارش
            report.status = "completed"
            report.completed_at = datetime.utcnow()
            report.file_analyses = file_analyses
            report.structure_analysis = structure_analysis
            report.roadmap_comparison = roadmap_comparison
            report.issues_found = all_issues

            report.overall_score = scores['overall']
            report.overall_color = self._score_to_color(scores['overall'])
            report.code_quality_score = scores['code_quality']
            report.documentation_score = scores['documentation']
            report.security_score = scores['security']
            report.structure_score = scores['structure']
            report.roadmap_compliance_score = scores['roadmap_compliance']

            # تولید خلاصه و پیشنهادات
            report.recommendations = self._generate_recommendations(all_issues, scores)
            report.summary = self._generate_summary(report)

            db.commit()

            # اعتبارسنجی مدل‌ها
            await self._validate_models(report_id, file_analyses, models)

            return AnalysisReportSchema.model_validate(report)

        except Exception as e:
            report.status = "failed"
            db.commit()
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise
        finally:
            db.close()

    def _collect_files(self, project_path: str) -> Dict[str, str]:
        """جمع‌آوری تمام فایل‌های قابل تحلیل"""
        files = {}
        extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.h'}
        ignore_dirs = {'node_modules', '__pycache__', '.git', 'venv', 'env', 'dist', 'build'}

        for root, dirs, filenames in os.walk(project_path):
            # فیلتر پوشه‌ها
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for filename in filenames:
                ext = os.path.splitext(filename)[1]
                if ext in extensions:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, project_path)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if len(content) < 50000:  # حداکثر 50KB
                                files[rel_path] = content
                    except Exception:
                        pass

        return files

    async def _analyze_file(
        self,
        file_path: str,
        content: str,
        models: List[str],
        report_id: str
    ) -> Dict[str, Any]:
        """تحلیل یک فایل توسط چند مدل به صورت موازی"""
        analysis_by_model = {}
        all_issues = []
        all_suggestions = []

        # تحلیل موازی توسط همه مدل‌ها
        tasks = []
        for model_id in models:
            for criterion in ['code_quality', 'documentation', 'security', 'best_practices']:
                task = self._analyze_file_criterion(
                    file_path, content, model_id, criterion
                )
                tasks.append((model_id, criterion, task))

        # اجرای موازی
        results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

        # پردازش نتایج
        scores_by_criterion = {
            'code_quality': [],
            'documentation': [],
            'security': [],
            'best_practices': []
        }

        for i, (model_id, criterion, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Analysis failed for {model_id}/{criterion}: {result}")
                continue

            if model_id not in analysis_by_model:
                analysis_by_model[model_id] = {}

            analysis_by_model[model_id][criterion] = result
            scores_by_criterion[criterion].append(result.get('score', 0))

            # جمع‌آوری مشکلات
            issues = result.get('issues', []) + result.get('vulnerabilities', [])
            for issue in issues:
                issue['criterion'] = criterion
                issue['model'] = model_id
                issue['file'] = file_path
                all_issues.append(issue)

            all_suggestions.extend(result.get('suggestions', []))

        # محاسبه نمره میانگین
        avg_scores = {
            k: sum(v) / len(v) if v else 0
            for k, v in scores_by_criterion.items()
        }
        overall_score = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0

        return {
            'file_path': file_path,
            'score': overall_score,
            'color': self._score_to_color(overall_score),
            'code_quality': avg_scores.get('code_quality', 0),
            'documentation': avg_scores.get('documentation', 0),
            'security': avg_scores.get('security', 0),
            'best_practices': avg_scores.get('best_practices', 0),
            'issues': all_issues,
            'suggestions': list(set(all_suggestions)),
            'analysis_by_model': analysis_by_model,
            'models_analyzed': len(models)
        }

    async def _analyze_file_criterion(
        self,
        file_path: str,
        content: str,
        model_id: str,
        criterion: str
    ) -> Dict[str, Any]:
        """تحلیل یک معیار خاص برای یک فایل"""
        prompt_template = self.analysis_prompts.get(criterion, "")
        prompt = prompt_template.format(
            file_path=file_path,
            content=content[:10000]  # محدودیت طول
        )

        try:
            start_time = time.time()
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )
            elapsed = time.time() - start_time

            # پارس JSON از پاسخ
            content = response.content
            # استخراج JSON از پاسخ
            result = self._extract_json(content)
            result['response_time'] = elapsed
            return result

        except Exception as e:
            logger.error(f"Error analyzing {file_path} with {model_id}: {e}")
            return {'score': 0, 'error': str(e)}

    def _extract_json(self, text: str) -> Dict:
        """استخراج JSON از متن"""
        try:
            # تلاش مستقیم
            return json.loads(text)
        except:
            pass

        # جستجوی JSON در متن
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        return {'score': 50, 'error': 'Could not parse response'}

    async def _analyze_structure(
        self,
        project_path: str,
        files: Dict[str, str],
        model_id: str
    ) -> Dict[str, Any]:
        """تحلیل ساختار پروژه"""
        if not model_id:
            return {'score': 0}

        # تولید ساختار درختی
        structure = self._generate_tree_structure(project_path)
        file_list = list(files.keys())

        prompt = self.analysis_prompts['structure'].format(
            structure=structure,
            files="\n".join(file_list[:100])
        )

        try:
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )
            return self._extract_json(response.content)
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return {'score': 50, 'error': str(e)}

    def _generate_tree_structure(self, project_path: str) -> str:
        """تولید ساختار درختی پروژه"""
        tree = []
        for root, dirs, files in os.walk(project_path):
            level = root.replace(project_path, '').count(os.sep)
            indent = '  ' * level
            tree.append(f"{indent}{os.path.basename(root)}/")
            for file in files[:20]:  # حداکثر 20 فایل در هر پوشه
                tree.append(f"{indent}  {file}")
            if level > 3:
                break
        return "\n".join(tree[:100])

    async def _compare_with_roadmap(
        self,
        roadmap_content: str,
        current_state: str,
        model_id: str
    ) -> Dict[str, Any]:
        """مقایسه با نقشه راه"""
        if not model_id:
            return {'score': 0}

        prompt = self.analysis_prompts['roadmap_compliance'].format(
            roadmap=roadmap_content[:5000],
            current_state=current_state[:5000]
        )

        try:
            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )
            return self._extract_json(response.content)
        except Exception as e:
            logger.error(f"Roadmap comparison failed: {e}")
            return {'score': 50, 'error': str(e)}

    def _get_project_state(self, files: Dict[str, str]) -> str:
        """دریافت وضعیت فعلی پروژه"""
        state = []
        state.append(f"تعداد فایل‌ها: {len(files)}")
        state.append("\nفایل‌های اصلی:")
        for path in list(files.keys())[:30]:
            state.append(f"  - {path}")
        return "\n".join(state)

    def _calculate_overall_scores(
        self,
        file_analyses: List[Dict],
        structure_analysis: Dict,
        roadmap_comparison: Dict
    ) -> Dict[str, float]:
        """محاسبه نمرات کلی"""
        # میانگین نمرات فایل‌ها
        if file_analyses:
            code_quality = sum(f.get('code_quality', 0) for f in file_analyses) / len(file_analyses)
            documentation = sum(f.get('documentation', 0) for f in file_analyses) / len(file_analyses)
            security = sum(f.get('security', 0) for f in file_analyses) / len(file_analyses)
        else:
            code_quality = documentation = security = 0

        structure = structure_analysis.get('score', 0)
        roadmap_compliance = roadmap_comparison.get('score', 0)

        # میانگین وزن‌دار
        weights = {
            'code_quality': 0.25,
            'documentation': 0.15,
            'security': 0.20,
            'structure': 0.20,
            'roadmap_compliance': 0.20
        }

        overall = (
            code_quality * weights['code_quality'] +
            documentation * weights['documentation'] +
            security * weights['security'] +
            structure * weights['structure'] +
            roadmap_compliance * weights['roadmap_compliance']
        )

        return {
            'overall': overall,
            'code_quality': code_quality,
            'documentation': documentation,
            'security': security,
            'structure': structure,
            'roadmap_compliance': roadmap_compliance
        }

    def _score_to_color(self, score: float) -> str:
        """تبدیل نمره به رنگ"""
        if score >= 90:
            return "green"
        elif score >= 70:
            return "yellow"
        elif score >= 50:
            return "orange"
        else:
            return "red"

    def _generate_recommendations(
        self,
        issues: List[Dict],
        scores: Dict[str, float]
    ) -> List[str]:
        """تولید پیشنهادات بهبود"""
        recommendations = []

        # بر اساس نمرات پایین
        if scores['code_quality'] < 70:
            recommendations.append("بهبود کیفیت کد: رعایت استانداردها و اصول SOLID")
        if scores['documentation'] < 70:
            recommendations.append("افزودن مستندات: docstrings و کامنت‌های توضیحی")
        if scores['security'] < 70:
            recommendations.append("بررسی امنیتی: رفع آسیب‌پذیری‌های شناسایی‌شده")
        if scores['structure'] < 70:
            recommendations.append("بهبود ساختار: سازماندهی بهتر فایل‌ها و پوشه‌ها")
        if scores['roadmap_compliance'] < 70:
            recommendations.append("هماهنگی با نقشه راه: تکمیل آیتم‌های باقی‌مانده")

        # بر اساس مشکلات بحرانی
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        if critical_issues:
            recommendations.insert(0, f"رفع فوری {len(critical_issues)} مشکل بحرانی!")

        return recommendations

    def _generate_summary(self, report: AnalysisReport) -> str:
        """تولید خلاصه گزارش"""
        return f"""
خلاصه تحلیل پروژه

نمره کلی: {report.overall_score:.1f}/100 ({report.overall_color})

نمرات جزئی:
- کیفیت کد: {report.code_quality_score:.1f}
- مستندسازی: {report.documentation_score:.1f}
- امنیت: {report.security_score:.1f}
- ساختار: {report.structure_score:.1f}
- مطابقت با نقشه راه: {report.roadmap_compliance_score:.1f}

تعداد مشکلات: {len(report.issues_found or [])}
مدل‌های استفاده‌شده: {', '.join(report.models_used or [])}
"""

    async def _validate_models(
        self,
        report_id: str,
        file_analyses: List[Dict],
        models: List[str]
    ):
        """اعتبارسنجی مدل‌ها بر اساس تحلیل"""
        if not self.model_profiler:
            return

        for model_id in models:
            # شمارش یافته‌های هر مدل
            model_issues = []
            for fa in file_analyses:
                model_analysis = fa.get('analysis_by_model', {}).get(model_id, {})
                for criterion, result in model_analysis.items():
                    issues = result.get('issues', []) + result.get('vulnerabilities', [])
                    model_issues.extend(issues)

            # به‌روزرسانی پروفایل
            await self.model_profiler.update_profile(
                model_id=model_id,
                task_type="analysis",
                correct_findings=len(model_issues),  # فعلاً همه را درست فرض می‌کنیم
                total_expected=len(model_issues),
                analysis_report_id=report_id
            )


# Singleton instance
_analyzer_instance: Optional[ProjectAnalyzer] = None


def get_project_analyzer() -> ProjectAnalyzer:
    """دریافت نمونه ProjectAnalyzer"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ProjectAnalyzer()
    return _analyzer_instance
