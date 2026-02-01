# -*- coding: utf-8 -*-
"""
📊 سرویس تحلیل کیفیت کد
Code Quality Analyzer Service

قابلیت‌ها:
1. Test Coverage Analysis - تحلیل پوشش تست
2. Sandbox Testing - تست کد در محیط ایزوله
3. Dry Run / Diff View - پیش‌نمایش تغییرات
"""

import os
import re
import json
import difflib
import tempfile
import subprocess
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TestCoverageAnalyzer:
    """
    تحلیل‌گر پوشش تست
    """

    # الگوهای فایل تست
    TEST_FILE_PATTERNS = [
        r'test_.*\.py$',
        r'.*_test\.py$',
        r'.*\.test\.(ts|tsx|js|jsx)$',
        r'.*\.spec\.(ts|tsx|js|jsx)$',
        r'__tests__/.*\.(ts|tsx|js|jsx)$',
        r'tests?/.*\.(py|ts|tsx|js|jsx)$',
    ]

    # الگوهای مهم برای تشخیص تست
    TEST_INDICATORS = {
        'python': {
            'imports': ['pytest', 'unittest', 'nose', 'mock', 'faker'],
            'decorators': ['@pytest', '@unittest', '@mock', '@patch', '@fixture'],
            'functions': ['def test_', 'def setUp', 'def tearDown', 'assert'],
            'classes': ['TestCase', 'Test']
        },
        'javascript': {
            'imports': ['jest', 'mocha', 'chai', 'vitest', '@testing-library', 'enzyme'],
            'functions': ['describe(', 'it(', 'test(', 'expect(', 'beforeEach(', 'afterEach('],
            'assertions': ['toEqual', 'toBe', 'toHaveBeenCalled', 'toThrow']
        }
    }

    def analyze_test_coverage(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تحلیل پوشش تست پروژه

        Returns:
            {
                "has_tests": bool,
                "test_framework": str,
                "test_files": [
                    {"path": str, "type": str, "test_count": int}
                ],
                "source_files": [str],
                "coverage_estimate": {
                    "test_file_ratio": float,  # نسبت فایل‌های تست به کل
                    "covered_modules": [str],  # ماژول‌هایی که تست دارند
                    "uncovered_modules": [str],  # ماژول‌هایی که تست ندارند
                    "estimated_percentage": int
                },
                "recommendations": [str],
                "score": int
            }
        """
        result = {
            "has_tests": False,
            "test_frameworks": [],
            "test_files": [],
            "source_files": [],
            "coverage_estimate": {
                "test_file_ratio": 0.0,
                "covered_modules": [],
                "uncovered_modules": [],
                "estimated_percentage": 0
            },
            "recommendations": [],
            "score": 0,
            "analyzed_at": datetime.utcnow().isoformat()
        }

        source_files = []
        test_files = []
        modules_with_tests = set()
        all_modules = set()

        for file_data in files:
            file_path = file_data.get("path", file_data.get("file_path", ""))
            content = file_data.get("content", "")

            # Identify file type
            is_test_file = self._is_test_file(file_path, content)

            if is_test_file:
                test_info = self._analyze_test_file(file_path, content)
                test_files.append(test_info)

                # Track frameworks
                for fw in test_info.get("frameworks", []):
                    if fw not in result["test_frameworks"]:
                        result["test_frameworks"].append(fw)

                # Track which module this tests
                tested_module = self._get_tested_module(file_path)
                if tested_module:
                    modules_with_tests.add(tested_module)

            elif self._is_source_file(file_path):
                source_files.append(file_path)
                module = self._get_module_name(file_path)
                if module:
                    all_modules.add(module)

        # Calculate coverage estimate
        result["has_tests"] = len(test_files) > 0
        result["test_files"] = test_files
        result["source_files"] = source_files[:50]  # Limit for response size

        if source_files:
            result["coverage_estimate"]["test_file_ratio"] = round(
                len(test_files) / len(source_files) * 100, 1
            )

        # Determine covered/uncovered modules
        result["coverage_estimate"]["covered_modules"] = list(modules_with_tests)[:20]
        result["coverage_estimate"]["uncovered_modules"] = list(
            all_modules - modules_with_tests
        )[:20]

        # Estimate percentage based on heuristics
        if test_files:
            # Base on test-to-source ratio + framework presence
            base_coverage = min(100, len(test_files) / max(1, len(source_files)) * 200)
            framework_bonus = 10 if result["test_frameworks"] else 0
            result["coverage_estimate"]["estimated_percentage"] = int(
                min(100, base_coverage + framework_bonus)
            )
        else:
            result["coverage_estimate"]["estimated_percentage"] = 0

        # Generate recommendations
        if not result["has_tests"]:
            result["recommendations"].append(
                "🔴 پروژه فاقد تست است - ایجاد تست‌های واحد و یکپارچه‌سازی ضروری است"
            )
        elif result["coverage_estimate"]["estimated_percentage"] < 30:
            result["recommendations"].append(
                "⚠️ پوشش تست کم است - افزایش تعداد تست‌ها توصیه می‌شود"
            )

        if result["coverage_estimate"]["uncovered_modules"]:
            result["recommendations"].append(
                f"📝 ماژول‌های بدون تست: {', '.join(result['coverage_estimate']['uncovered_modules'][:5])}"
            )

        if not result["test_frameworks"]:
            result["recommendations"].append(
                "💡 استفاده از فریم‌ورک تست (pytest, jest) توصیه می‌شود"
            )

        # Calculate score
        result["score"] = min(100, max(0, result["coverage_estimate"]["estimated_percentage"]))

        return result

    def _is_test_file(self, file_path: str, content: str) -> bool:
        """آیا فایل یک فایل تست است"""
        # Check path patterns
        for pattern in self.TEST_FILE_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True

        # Check content for test indicators
        if content:
            # Python tests
            py_indicators = self.TEST_INDICATORS['python']
            for imp in py_indicators['imports']:
                if f"import {imp}" in content or f"from {imp}" in content:
                    return True
            for func in py_indicators['functions']:
                if func in content:
                    return True

            # JavaScript tests
            js_indicators = self.TEST_INDICATORS['javascript']
            for imp in js_indicators['imports']:
                if imp in content:
                    return True
            for func in js_indicators['functions']:
                if func in content:
                    return True

        return False

    def _is_source_file(self, file_path: str) -> bool:
        """آیا فایل یک فایل سورس است"""
        source_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java'}
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in source_extensions:
            return False

        # Exclude certain paths
        exclude_paths = ['node_modules', '__pycache__', '.git', 'dist', 'build']
        for exc in exclude_paths:
            if exc in file_path:
                return False

        return True

    def _analyze_test_file(self, file_path: str, content: str) -> Dict:
        """تحلیل یک فایل تست"""
        info = {
            "path": file_path,
            "type": self._get_file_type(file_path),
            "test_count": 0,
            "frameworks": [],
            "test_functions": []
        }

        if not content:
            return info

        # Count test functions
        if info["type"] == "python":
            info["test_count"] = len(re.findall(r'def test_\w+', content))
            info["test_functions"] = re.findall(r'def (test_\w+)', content)[:10]

            # Detect framework
            if "import pytest" in content or "from pytest" in content:
                info["frameworks"].append("pytest")
            if "import unittest" in content or "from unittest" in content:
                info["frameworks"].append("unittest")

        elif info["type"] in ["javascript", "typescript"]:
            # Count test/it blocks
            info["test_count"] = len(re.findall(r"(?:test|it)\s*\(['\"]", content))
            test_names = re.findall(r"(?:test|it)\s*\(['\"]([^'\"]+)['\"]", content)
            info["test_functions"] = test_names[:10]

            # Detect framework
            if "jest" in content.lower():
                info["frameworks"].append("jest")
            if "vitest" in content.lower():
                info["frameworks"].append("vitest")
            if "mocha" in content.lower():
                info["frameworks"].append("mocha")

        return info

    def _get_file_type(self, file_path: str) -> str:
        """تشخیص نوع فایل"""
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java'
        }
        return type_map.get(ext, 'unknown')

    def _get_tested_module(self, test_file_path: str) -> Optional[str]:
        """استخراج نام ماژولی که تست می‌شود"""
        # test_foo.py -> foo
        # foo_test.py -> foo
        # foo.test.ts -> foo
        # foo.spec.ts -> foo

        filename = os.path.basename(test_file_path)

        patterns = [
            (r'^test_(.+)\.py$', 1),
            (r'^(.+)_test\.py$', 1),
            (r'^(.+)\.(test|spec)\.(ts|tsx|js|jsx)$', 1),
        ]

        for pattern, group in patterns:
            match = re.match(pattern, filename)
            if match:
                return match.group(group)

        return None

    def _get_module_name(self, file_path: str) -> Optional[str]:
        """استخراج نام ماژول از مسیر فایل"""
        filename = os.path.basename(file_path)
        name = os.path.splitext(filename)[0]
        return name if name not in ['__init__', 'index'] else None


class DiffGenerator:
    """
    تولید کننده Diff برای پیش‌نمایش تغییرات
    """

    def generate_diff(
        self,
        original_content: str,
        new_content: str,
        file_path: str = "file"
    ) -> Dict[str, Any]:
        """
        تولید diff بین دو محتوا

        Returns:
            {
                "has_changes": bool,
                "unified_diff": str,
                "html_diff": str,
                "stats": {
                    "additions": int,
                    "deletions": int,
                    "changes": int
                },
                "changed_lines": [int]
            }
        """
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        # Generate unified diff
        unified = list(difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        ))

        # Count changes
        additions = sum(1 for line in unified if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in unified if line.startswith('-') and not line.startswith('---'))

        # Generate HTML diff for better visualization
        html_diff = self._generate_html_diff(original_lines, new_lines)

        # Find changed line numbers
        changed_lines = self._get_changed_line_numbers(original_lines, new_lines)

        return {
            "has_changes": len(unified) > 0,
            "unified_diff": '\n'.join(unified),
            "html_diff": html_diff,
            "stats": {
                "additions": additions,
                "deletions": deletions,
                "changes": additions + deletions
            },
            "changed_lines": changed_lines,
            "file_path": file_path
        }

    def _generate_html_diff(self, original: List[str], new: List[str]) -> str:
        """تولید HTML diff برای نمایش بهتر"""
        differ = difflib.HtmlDiff()
        html = differ.make_table(
            original,
            new,
            fromdesc="قبل",
            todesc="بعد",
            context=True,
            numlines=3
        )
        return html

    def _get_changed_line_numbers(
        self,
        original: List[str],
        new: List[str]
    ) -> List[int]:
        """شناسایی شماره خطوط تغییر یافته"""
        matcher = difflib.SequenceMatcher(None, original, new)
        changed_lines = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ['replace', 'delete']:
                changed_lines.extend(range(i1 + 1, i2 + 1))
            if tag in ['replace', 'insert']:
                changed_lines.extend(range(j1 + 1, j2 + 1))

        return sorted(set(changed_lines))


class SandboxValidator:
    """
    اعتبارسنج Sandbox برای تست کد قبل از commit
    """

    def __init__(self):
        self.temp_dir = None

    async def validate_code(
        self,
        files: Dict[str, str],
        project_type: str = "python"
    ) -> Dict[str, Any]:
        """
        اعتبارسنجی کد در محیط ایزوله

        Args:
            files: {file_path: content}
            project_type: python | nodejs | typescript

        Returns:
            {
                "valid": bool,
                "syntax_errors": [...],
                "import_errors": [...],
                "type_errors": [...],
                "warnings": [...],
                "execution_result": {...}
            }
        """
        result = {
            "valid": True,
            "syntax_errors": [],
            "import_errors": [],
            "type_errors": [],
            "warnings": [],
            "checks_performed": [],
            "validated_at": datetime.utcnow().isoformat()
        }

        try:
            if project_type == "python":
                await self._validate_python(files, result)
            elif project_type in ["nodejs", "javascript"]:
                await self._validate_javascript(files, result)
            elif project_type == "typescript":
                await self._validate_typescript(files, result)

        except Exception as e:
            logger.error(f"Sandbox validation error: {e}")
            result["valid"] = False
            result["syntax_errors"].append({
                "file": "validation",
                "error": str(e)
            })

        return result

    async def _validate_python(
        self,
        files: Dict[str, str],
        result: Dict
    ):
        """اعتبارسنجی کد پایتون"""
        import ast

        result["checks_performed"].append("python_syntax")

        for file_path, content in files.items():
            if not file_path.endswith('.py'):
                continue

            # Syntax check using AST
            try:
                ast.parse(content)
            except SyntaxError as e:
                result["valid"] = False
                result["syntax_errors"].append({
                    "file": file_path,
                    "line": e.lineno,
                    "column": e.offset,
                    "message": str(e.msg),
                    "text": e.text
                })
                continue

            # Check for common issues
            warnings = self._check_python_common_issues(content, file_path)
            result["warnings"].extend(warnings)

        # Try to run flake8 if available
        try:
            flake8_result = await self._run_flake8(files)
            result["checks_performed"].append("flake8")
            result["warnings"].extend(flake8_result)
        except FileNotFoundError:
            pass  # flake8 not installed

    def _check_python_common_issues(
        self,
        content: str,
        file_path: str
    ) -> List[Dict]:
        """بررسی مشکلات رایج پایتون"""
        warnings = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # Check for eval/exec usage
            if 'eval(' in line or 'exec(' in line:
                warnings.append({
                    "file": file_path,
                    "line": i,
                    "type": "security",
                    "message": "استفاده از eval/exec خطرناک است"
                })

            # Check for hardcoded passwords
            if re.search(r'password\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                warnings.append({
                    "file": file_path,
                    "line": i,
                    "type": "security",
                    "message": "رمز عبور hardcoded شناسایی شد"
                })

            # Check for very long lines
            if len(line) > 120:
                warnings.append({
                    "file": file_path,
                    "line": i,
                    "type": "style",
                    "message": f"خط خیلی طولانی است ({len(line)} کاراکتر)"
                })

        return warnings

    async def _run_flake8(self, files: Dict[str, str]) -> List[Dict]:
        """اجرای flake8 روی فایل‌ها"""
        warnings = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Write files to temp directory
            for file_path, content in files.items():
                if not file_path.endswith('.py'):
                    continue

                full_path = os.path.join(temp_dir, os.path.basename(file_path))
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Run flake8
            process = await asyncio.create_subprocess_exec(
                'flake8', temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            # Parse output
            if stdout:
                for line in stdout.decode().split('\n'):
                    match = re.match(r'([^:]+):(\d+):(\d+): (\w+) (.+)', line)
                    if match:
                        warnings.append({
                            "file": match.group(1),
                            "line": int(match.group(2)),
                            "column": int(match.group(3)),
                            "code": match.group(4),
                            "message": match.group(5),
                            "type": "lint"
                        })

        return warnings

    async def _validate_javascript(
        self,
        files: Dict[str, str],
        result: Dict
    ):
        """اعتبارسنجی کد JavaScript"""
        result["checks_performed"].append("javascript_basic")

        for file_path, content in files.items():
            if not file_path.endswith(('.js', '.jsx')):
                continue

            # Basic syntax checks
            issues = self._check_js_common_issues(content, file_path)
            result["warnings"].extend(issues)

    async def _validate_typescript(
        self,
        files: Dict[str, str],
        result: Dict
    ):
        """اعتبارسنجی کد TypeScript"""
        result["checks_performed"].append("typescript_basic")

        for file_path, content in files.items():
            if not file_path.endswith(('.ts', '.tsx')):
                continue

            # Basic checks (full TS check requires tsc)
            issues = self._check_js_common_issues(content, file_path)
            result["warnings"].extend(issues)

    def _check_js_common_issues(
        self,
        content: str,
        file_path: str
    ) -> List[Dict]:
        """بررسی مشکلات رایج JavaScript/TypeScript"""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # Check for console.log in production code
            if 'console.log' in line:
                issues.append({
                    "file": file_path,
                    "line": i,
                    "type": "warning",
                    "message": "console.log در کد تولید - باید حذف شود"
                })

            # Check for debugger statements
            if 'debugger' in line:
                issues.append({
                    "file": file_path,
                    "line": i,
                    "type": "error",
                    "message": "debugger statement باید حذف شود"
                })

            # Check for any type usage in TypeScript
            if file_path.endswith('.ts') or file_path.endswith('.tsx'):
                if ': any' in line or 'as any' in line:
                    issues.append({
                        "file": file_path,
                        "line": i,
                        "type": "warning",
                        "message": "استفاده از نوع any توصیه نمی‌شود"
                    })

        return issues


# =====================================================
# Singleton Instances
# =====================================================

_test_coverage_instance: Optional[TestCoverageAnalyzer] = None
_diff_generator_instance: Optional[DiffGenerator] = None
_sandbox_validator_instance: Optional[SandboxValidator] = None


def get_test_coverage_analyzer() -> TestCoverageAnalyzer:
    """دریافت نمونه TestCoverageAnalyzer"""
    global _test_coverage_instance
    if _test_coverage_instance is None:
        _test_coverage_instance = TestCoverageAnalyzer()
    return _test_coverage_instance


def get_diff_generator() -> DiffGenerator:
    """دریافت نمونه DiffGenerator"""
    global _diff_generator_instance
    if _diff_generator_instance is None:
        _diff_generator_instance = DiffGenerator()
    return _diff_generator_instance


def get_sandbox_validator() -> SandboxValidator:
    """دریافت نمونه SandboxValidator"""
    global _sandbox_validator_instance
    if _sandbox_validator_instance is None:
        _sandbox_validator_instance = SandboxValidator()
    return _sandbox_validator_instance
