# -*- coding: utf-8 -*-
"""
سرویس تحلیل پوشش تست - Test Coverage Analyzer
تحلیل فایل‌های تست و پوشش کد
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class TestCoverageAnalyzer:
    """
    تحلیلگر پوشش تست برای:
    1. شناسایی فایل‌های تست
    2. تحلیل توابع و کلاس‌های تست شده
    3. محاسبه درصد پوشش
    """

    # الگوهای نام فایل تست
    TEST_FILE_PATTERNS = [
        r"test_.*\.py$",           # test_*.py (Python)
        r".*_test\.py$",           # *_test.py (Python)
        r"tests?\.py$",            # test.py or tests.py
        r".*\.test\.[jt]sx?$",     # *.test.js, *.test.ts, *.test.jsx, *.test.tsx
        r".*\.spec\.[jt]sx?$",     # *.spec.js, *.spec.ts, *.spec.jsx, *.spec.tsx
        r"__tests__/.*\.[jt]sx?$", # __tests__/*.js
        r".*Test\.java$",          # *Test.java
        r".*_test\.go$",           # *_test.go
        r".*_test\.rb$",           # *_test.rb
        r".*_spec\.rb$",           # *_spec.rb
    ]

    # الگوهای دایرکتوری تست
    TEST_DIR_PATTERNS = [
        "tests/",
        "test/",
        "__tests__/",
        "spec/",
        "specs/",
    ]

    # الگوهای تعریف تست در زبان‌های مختلف
    TEST_FUNCTION_PATTERNS = {
        "python": [
            r"def\s+(test_\w+)\s*\(",
            r"async\s+def\s+(test_\w+)\s*\(",
            r"class\s+(Test\w+)",
        ],
        "javascript": [
            r"(it|test)\s*\(\s*['\"](.+?)['\"]",
            r"describe\s*\(\s*['\"](.+?)['\"]",
            r"(beforeEach|afterEach|beforeAll|afterAll)\s*\(",
        ],
        "java": [
            r"@Test\s+.*?void\s+(\w+)\s*\(",
            r"public\s+void\s+(test\w+)\s*\(",
        ],
        "go": [
            r"func\s+(Test\w+)\s*\(",
            r"func\s+(Benchmark\w+)\s*\(",
        ],
    }

    # الگوهای تعریف تابع/کلاس در کد اصلی
    CODE_PATTERNS = {
        "python": [
            (r"def\s+(\w+)\s*\(", "function"),
            (r"async\s+def\s+(\w+)\s*\(", "async_function"),
            (r"class\s+(\w+)", "class"),
        ],
        "javascript": [
            (r"function\s+(\w+)\s*\(", "function"),
            (r"const\s+(\w+)\s*=\s*(?:async\s+)?\(", "arrow_function"),
            (r"const\s+(\w+)\s*=\s*(?:async\s+)?function", "function"),
            (r"class\s+(\w+)", "class"),
            (r"export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)", "function"),
        ],
        "java": [
            (r"(?:public|private|protected)?\s*(?:static\s+)?(?:\w+)\s+(\w+)\s*\(", "method"),
            (r"class\s+(\w+)", "class"),
        ],
        "go": [
            (r"func\s+(\w+)\s*\(", "function"),
            (r"func\s+\([^)]+\)\s+(\w+)\s*\(", "method"),
            (r"type\s+(\w+)\s+struct", "struct"),
        ],
    }

    def __init__(self):
        self.analysis_results: Dict[str, Any] = {}

    def is_test_file(self, file_path: str) -> bool:
        """تشخیص فایل تست"""
        path = file_path.lower()

        # بررسی دایرکتوری
        for dir_pattern in self.TEST_DIR_PATTERNS:
            if dir_pattern in path:
                return True

        # بررسی نام فایل
        for pattern in self.TEST_FILE_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return True

        return False

    def get_file_language(self, file_path: str) -> str:
        """تشخیص زبان فایل"""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "javascript",
            ".tsx": "javascript",
            ".java": "java",
            ".go": "go",
            ".rb": "ruby",
        }
        return lang_map.get(ext, "unknown")

    def extract_test_names(self, content: str, language: str) -> List[Dict[str, Any]]:
        """استخراج نام تست‌ها از فایل تست"""
        tests = []
        patterns = self.TEST_FUNCTION_PATTERNS.get(language, [])

        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                if language == "javascript":
                    # برای describe/it نام در گروه دوم است
                    test_name = match.group(2) if len(match.groups()) > 1 else match.group(1)
                else:
                    test_name = match.group(1)

                tests.append({
                    "name": test_name,
                    "line": content[:match.start()].count('\n') + 1,
                    "type": "test"
                })

        return tests

    def extract_code_entities(self, content: str, language: str) -> List[Dict[str, Any]]:
        """استخراج توابع و کلاس‌ها از کد اصلی"""
        entities = []
        patterns = self.CODE_PATTERNS.get(language, [])

        for pattern, entity_type in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                name = match.group(1)
                # فیلتر کردن توابع خصوصی یا internal
                if not name.startswith('_') or name.startswith('__') and name.endswith('__'):
                    entities.append({
                        "name": name,
                        "type": entity_type,
                        "line": content[:match.start()].count('\n') + 1
                    })

        return entities

    def find_tested_entities(self, test_content: str, source_entities: List[Dict]) -> List[str]:
        """یافتن موجودیت‌هایی که در تست‌ها پوشش داده شده‌اند"""
        tested = []
        test_lower = test_content.lower()

        for entity in source_entities:
            name = entity["name"]
            # بررسی وجود نام در فایل تست
            if name.lower() in test_lower:
                tested.append(name)

        return tested

    def analyze_project(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تحلیل کامل پوشش تست پروژه
        """
        test_files = []
        source_files = []
        all_entities = []
        tested_entities = set()
        test_count = 0

        # دسته‌بندی فایل‌ها
        for file_info in files:
            path = file_info.get("path", "")
            content = file_info.get("content", "")
            language = self.get_file_language(path)

            if language == "unknown":
                continue

            if self.is_test_file(path):
                tests = self.extract_test_names(content, language)
                test_count += len(tests)
                test_files.append({
                    "path": path,
                    "language": language,
                    "tests": tests,
                    "test_count": len(tests)
                })
            else:
                entities = self.extract_code_entities(content, language)
                if entities:
                    source_files.append({
                        "path": path,
                        "language": language,
                        "entities": entities,
                        "entity_count": len(entities)
                    })
                    all_entities.extend([{"file": path, **e} for e in entities])

        # تحلیل پوشش
        for test_file in test_files:
            test_content = ""
            for f in files:
                if f.get("path") == test_file["path"]:
                    test_content = f.get("content", "")
                    break

            for source in source_files:
                tested = self.find_tested_entities(test_content, source["entities"])
                tested_entities.update(tested)

        # محاسبه آمار
        total_entities = len(all_entities)
        covered_count = len(tested_entities)
        coverage_percent = (covered_count / total_entities * 100) if total_entities > 0 else 0

        # فایل‌های بدون تست
        untested_files = []
        for source in source_files:
            # بررسی آیا فایل تست متناظر وجود دارد
            source_path = source["path"]
            has_test = False

            for test_file in test_files:
                test_path = test_file["path"]
                # بررسی تناظر نام
                source_name = Path(source_path).stem.lower()
                test_name = Path(test_path).stem.lower()

                if source_name in test_name or f"test_{source_name}" == test_name or f"{source_name}_test" == test_name:
                    has_test = True
                    break

            if not has_test:
                untested_files.append({
                    "path": source_path,
                    "entity_count": source["entity_count"],
                    "entities": [e["name"] for e in source["entities"][:5]]  # 5 نمونه اول
                })

        # توصیه‌ها
        recommendations = []
        if coverage_percent < 50:
            recommendations.append({
                "type": "low_coverage",
                "severity": "high",
                "message": f"پوشش تست کمتر از 50% است ({coverage_percent:.1f}%)",
                "recommendation": "فایل‌های تست بیشتری اضافه کنید"
            })

        if len(untested_files) > len(source_files) / 2:
            recommendations.append({
                "type": "many_untested",
                "severity": "medium",
                "message": f"{len(untested_files)} فایل بدون تست وجود دارد",
                "recommendation": "برای فایل‌های اصلی تست بنویسید"
            })

        if test_count == 0:
            recommendations.append({
                "type": "no_tests",
                "severity": "critical",
                "message": "هیچ تستی در پروژه وجود ندارد",
                "recommendation": "فوراً شروع به نوشتن تست کنید"
            })

        return {
            "summary": {
                "total_test_files": len(test_files),
                "total_source_files": len(source_files),
                "total_tests": test_count,
                "total_entities": total_entities,
                "covered_entities": covered_count,
                "coverage_percent": round(coverage_percent, 2),
                "untested_file_count": len(untested_files)
            },
            "test_files": test_files,
            "source_files": [{
                "path": s["path"],
                "entity_count": s["entity_count"]
            } for s in source_files],
            "untested_files": untested_files[:20],  # حداکثر 20 فایل
            "coverage_by_language": self._coverage_by_language(source_files, test_files),
            "recommendations": recommendations,
            "health_score": self._calculate_health_score(coverage_percent, test_count, len(untested_files))
        }

    def _coverage_by_language(self, sources: List, tests: List) -> Dict[str, Dict]:
        """پوشش به تفکیک زبان"""
        result = {}

        languages = set(s["language"] for s in sources)
        for lang in languages:
            lang_sources = [s for s in sources if s["language"] == lang]
            lang_tests = [t for t in tests if t["language"] == lang]

            source_count = sum(s["entity_count"] for s in lang_sources)
            test_count = sum(t["test_count"] for t in lang_tests)

            result[lang] = {
                "source_files": len(lang_sources),
                "test_files": len(lang_tests),
                "total_entities": source_count,
                "total_tests": test_count,
                "ratio": f"{test_count}:{source_count}"
            }

        return result

    def _calculate_health_score(self, coverage: float, test_count: int, untested: int) -> int:
        """محاسبه امتیاز سلامت تست"""
        score = 100

        # کاهش براساس پوشش
        if coverage < 80:
            score -= (80 - coverage) * 0.5
        if coverage < 50:
            score -= 20
        if coverage < 20:
            score -= 20

        # کاهش براساس فایل‌های بدون تست
        score -= min(untested * 2, 20)

        # پاداش برای تعداد تست
        if test_count > 50:
            score += 5
        if test_count > 100:
            score += 5

        return max(0, min(100, int(score)))


# نمونه singleton
_analyzer_instance = None


def get_test_coverage_analyzer() -> TestCoverageAnalyzer:
    """دریافت نمونه تحلیلگر پوشش تست"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = TestCoverageAnalyzer()
    return _analyzer_instance
