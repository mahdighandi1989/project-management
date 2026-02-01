# -*- coding: utf-8 -*-
"""
سرویس اسکن امنیتی - Security Scanner Service
تشخیص داده‌های حساس، لایسنس، و آسیب‌پذیری وابستگی‌ها
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityScanner:
    """
    اسکنر امنیتی برای تشخیص:
    1. Secrets (API keys, passwords, tokens)
    2. License detection
    3. Dependency vulnerabilities
    """

    # الگوهای regex برای تشخیص secrets
    SECRET_PATTERNS = {
        # API Keys
        "aws_access_key": r"(?i)(AKIA[0-9A-Z]{16})",
        "aws_secret_key": r"(?i)(aws_secret_access_key|aws_secret_key)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        "github_token": r"(?i)(ghp_[A-Za-z0-9]{36}|github_token\s*[=:]\s*['\"]?[A-Za-z0-9_-]+['\"]?)",
        "gitlab_token": r"(?i)(glpat-[A-Za-z0-9_-]{20,})",
        "google_api_key": r"(?i)(AIza[0-9A-Za-z_-]{35})",
        "stripe_key": r"(?i)(sk_live_[0-9a-zA-Z]{24,}|pk_live_[0-9a-zA-Z]{24,})",
        "slack_token": r"(?i)(xox[baprs]-[0-9A-Za-z-]{10,})",
        "telegram_token": r"(?i)(\d{8,10}:[A-Za-z0-9_-]{35})",
        "openai_key": r"(?i)(sk-[A-Za-z0-9]{48,})",
        "anthropic_key": r"(?i)(sk-ant-[A-Za-z0-9-]{90,})",

        # Generic patterns
        "generic_api_key": r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]?([A-Za-z0-9_-]{20,})['\"]?",
        "generic_secret": r"(?i)(secret[_-]?key|secretkey|client[_-]?secret)\s*[=:]\s*['\"]?([A-Za-z0-9_-]{16,})['\"]?",
        "generic_token": r"(?i)(access[_-]?token|auth[_-]?token|bearer[_-]?token)\s*[=:]\s*['\"]?([A-Za-z0-9_.-]{20,})['\"]?",

        # Passwords
        "password_assignment": r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{6,})['\"]",
        "db_password": r"(?i)(db_password|database_password|mysql_password|postgres_password)\s*[=:]\s*['\"]?([^'\"\s]{6,})['\"]?",

        # Connection strings
        "connection_string": r"(?i)(mongodb(\+srv)?://[^\s'\"]+|mysql://[^\s'\"]+|postgres(ql)?://[^\s'\"]+|redis://[^\s'\"]+)",

        # Private keys
        "private_key": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",

        # JWT tokens
        "jwt_token": r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    }

    # الگوهای لایسنس
    LICENSE_PATTERNS = {
        "MIT": r"(?i)(MIT License|Permission is hereby granted, free of charge)",
        "Apache-2.0": r"(?i)(Apache License|Licensed under the Apache License, Version 2\.0)",
        "GPL-3.0": r"(?i)(GNU GENERAL PUBLIC LICENSE|Version 3, 29 June 2007)",
        "GPL-2.0": r"(?i)(GNU GENERAL PUBLIC LICENSE|Version 2, June 1991)",
        "BSD-3-Clause": r"(?i)(BSD 3-Clause|Redistribution and use in source and binary forms)",
        "BSD-2-Clause": r"(?i)(BSD 2-Clause|Simplified BSD License)",
        "ISC": r"(?i)(ISC License|Permission to use, copy, modify)",
        "MPL-2.0": r"(?i)(Mozilla Public License|Version 2\.0)",
        "LGPL-3.0": r"(?i)(GNU LESSER GENERAL PUBLIC LICENSE|Version 3)",
        "Unlicense": r"(?i)(This is free and unencumbered software|UNLICENSE)",
        "CC0-1.0": r"(?i)(CC0 1\.0|Creative Commons Zero)",
    }

    # فایل‌های حساس که نباید commit شوند
    SENSITIVE_FILES = [
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "credentials.json",
        "secrets.json",
        "config.local.json",
        "service-account.json",
        "google-credentials.json",
        "firebase-adminsdk.json",
        ".npmrc",
        ".pypirc",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
    ]

    # وابستگی‌های آسیب‌پذیر شناخته شده (نمونه - باید از منبع خارجی آپدیت شود)
    KNOWN_VULNERABILITIES = {
        "python": {
            "django": {"vulnerable_versions": ["<3.2.19", "<4.1.9", "<4.2.1"], "cve": "CVE-2023-31047"},
            "flask": {"vulnerable_versions": ["<2.2.5", "<2.3.2"], "cve": "CVE-2023-30861"},
            "requests": {"vulnerable_versions": ["<2.31.0"], "cve": "CVE-2023-32681"},
            "pillow": {"vulnerable_versions": ["<9.5.0"], "cve": "CVE-2023-44271"},
            "cryptography": {"vulnerable_versions": ["<41.0.0"], "cve": "CVE-2023-38325"},
        },
        "javascript": {
            "lodash": {"vulnerable_versions": ["<4.17.21"], "cve": "CVE-2021-23337"},
            "axios": {"vulnerable_versions": ["<1.6.0"], "cve": "CVE-2023-45857"},
            "express": {"vulnerable_versions": ["<4.18.2"], "cve": "CVE-2022-24999"},
            "jsonwebtoken": {"vulnerable_versions": ["<9.0.0"], "cve": "CVE-2022-23529"},
            "minimatch": {"vulnerable_versions": ["<3.0.5"], "cve": "CVE-2022-3517"},
        }
    }

    def __init__(self):
        self.scan_results: Dict[str, Any] = {}

    def scan_content_for_secrets(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """
        اسکن محتوای فایل برای یافتن secrets
        """
        findings = []
        lines = content.split('\n')

        for pattern_name, pattern in self.SECRET_PATTERNS.items():
            try:
                for line_num, line in enumerate(lines, 1):
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        # فیلتر کردن false positives
                        if self._is_false_positive(match.group(), pattern_name, line):
                            continue

                        # ماسک کردن مقدار واقعی
                        masked_value = self._mask_secret(match.group())

                        findings.append({
                            "type": "secret",
                            "category": pattern_name,
                            "severity": self._get_secret_severity(pattern_name),
                            "file": file_path,
                            "line": line_num,
                            "message": f"احتمال وجود {self._get_persian_name(pattern_name)}: {masked_value}",
                            "matched_pattern": pattern_name,
                            "recommendation": self._get_recommendation(pattern_name),
                        })
            except re.error as e:
                logger.warning(f"Regex error for pattern {pattern_name}: {e}")

        return findings

    def _is_false_positive(self, value: str, pattern_name: str, line: str) -> bool:
        """تشخیص false positive"""
        # اگر در کامنت باشد
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('*'):
            return True

        # اگر مقدار placeholder باشد
        placeholders = ['xxx', 'your_', 'example', 'placeholder', 'changeme', 'TODO', 'FIXME', '<', '>']
        for ph in placeholders:
            if ph.lower() in value.lower():
                return True

        # اگر در .example یا .template باشد
        if '.example' in line or '.template' in line or '.sample' in line:
            return True

        return False

    def _mask_secret(self, value: str) -> str:
        """ماسک کردن secret برای نمایش امن"""
        if len(value) <= 8:
            return '*' * len(value)
        return value[:4] + '*' * (len(value) - 8) + value[-4:]

    def _get_secret_severity(self, pattern_name: str) -> str:
        """تعیین شدت بر اساس نوع secret"""
        critical = ["aws_access_key", "aws_secret_key", "private_key", "connection_string", "db_password"]
        high = ["github_token", "openai_key", "anthropic_key", "stripe_key", "password_assignment"]
        medium = ["generic_api_key", "generic_secret", "generic_token", "jwt_token"]

        if pattern_name in critical:
            return "critical"
        elif pattern_name in high:
            return "high"
        elif pattern_name in medium:
            return "medium"
        return "low"

    def _get_persian_name(self, pattern_name: str) -> str:
        """نام فارسی نوع secret"""
        names = {
            "aws_access_key": "کلید دسترسی AWS",
            "aws_secret_key": "کلید محرمانه AWS",
            "github_token": "توکن GitHub",
            "openai_key": "کلید API OpenAI",
            "anthropic_key": "کلید API Anthropic",
            "generic_api_key": "کلید API",
            "generic_secret": "کلید محرمانه",
            "generic_token": "توکن دسترسی",
            "password_assignment": "رمز عبور",
            "db_password": "رمز عبور دیتابیس",
            "connection_string": "رشته اتصال دیتابیس",
            "private_key": "کلید خصوصی",
            "jwt_token": "توکن JWT",
            "stripe_key": "کلید Stripe",
            "slack_token": "توکن Slack",
        }
        return names.get(pattern_name, "داده حساس")

    def _get_recommendation(self, pattern_name: str) -> str:
        """توصیه برای رفع مشکل"""
        recommendations = {
            "aws_access_key": "از AWS IAM roles یا متغیرهای محیطی استفاده کنید",
            "aws_secret_key": "کلید را در فایل .env قرار دهید و .env را به .gitignore اضافه کنید",
            "github_token": "از GitHub Secrets یا متغیرهای محیطی استفاده کنید",
            "openai_key": "کلید را در متغیرهای محیطی قرار دهید",
            "password_assignment": "از secret manager یا متغیرهای محیطی استفاده کنید",
            "connection_string": "رشته اتصال را از فایل‌های کانفیگ حذف کنید",
            "private_key": "کلید خصوصی را از مخزن حذف کنید و git history را پاکسازی کنید",
        }
        return recommendations.get(pattern_name, "این داده حساس را از کد حذف کرده و از متغیرهای محیطی استفاده کنید")

    def detect_license(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تشخیص لایسنس پروژه
        """
        license_files = ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"]
        detected_licenses = []

        for file_info in files:
            file_name = file_info.get("name", "").upper()
            file_path = file_info.get("path", "")

            # بررسی فایل‌های لایسنس
            if any(lf in file_name for lf in license_files):
                content = file_info.get("content", "")
                if content:
                    for license_name, pattern in self.LICENSE_PATTERNS.items():
                        if re.search(pattern, content):
                            detected_licenses.append({
                                "license": license_name,
                                "file": file_path,
                                "confidence": "high"
                            })
                            break
                else:
                    detected_licenses.append({
                        "license": "unknown",
                        "file": file_path,
                        "confidence": "low",
                        "message": "فایل لایسنس موجود است اما محتوا قابل خواندن نیست"
                    })

        # بررسی package.json برای لایسنس
        for file_info in files:
            if file_info.get("name") == "package.json":
                try:
                    content = file_info.get("content", "{}")
                    pkg = json.loads(content)
                    if "license" in pkg:
                        detected_licenses.append({
                            "license": pkg["license"],
                            "file": file_info.get("path"),
                            "source": "package.json",
                            "confidence": "high"
                        })
                except:
                    pass

        # بررسی setup.py یا pyproject.toml
        for file_info in files:
            if file_info.get("name") in ["setup.py", "pyproject.toml"]:
                content = file_info.get("content", "")
                license_match = re.search(r"license\s*[=:]\s*['\"]([^'\"]+)['\"]", content, re.IGNORECASE)
                if license_match:
                    detected_licenses.append({
                        "license": license_match.group(1),
                        "file": file_info.get("path"),
                        "source": file_info.get("name"),
                        "confidence": "high"
                    })

        return {
            "has_license": len(detected_licenses) > 0,
            "licenses": detected_licenses,
            "recommendation": None if detected_licenses else "پروژه فاقد لایسنس است. یک فایل LICENSE با لایسنس مناسب اضافه کنید.",
            "severity": "info" if detected_licenses else "medium"
        }

    def check_sensitive_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        بررسی وجود فایل‌های حساس که نباید commit شوند
        """
        findings = []

        for file_info in files:
            file_name = file_info.get("name", "")
            file_path = file_info.get("path", "")

            for sensitive in self.SENSITIVE_FILES:
                if sensitive.startswith("*"):
                    # wildcard matching
                    if file_name.endswith(sensitive[1:]):
                        findings.append({
                            "type": "sensitive_file",
                            "severity": "critical",
                            "file": file_path,
                            "message": f"فایل حساس {file_name} نباید در مخزن باشد",
                            "recommendation": f"این فایل را حذف کرده و به .gitignore اضافه کنید"
                        })
                elif file_name == sensitive or file_path.endswith("/" + sensitive):
                    findings.append({
                        "type": "sensitive_file",
                        "severity": "critical",
                        "file": file_path,
                        "message": f"فایل حساس {sensitive} در مخزن شناسایی شد",
                        "recommendation": f"این فایل را از git history حذف کنید و به .gitignore اضافه کنید"
                    })

        return findings

    def scan_dependencies(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        بررسی آسیب‌پذیری وابستگی‌ها
        """
        vulnerabilities = []
        dependencies_found = {"python": [], "javascript": []}

        for file_info in files:
            file_name = file_info.get("name", "")
            content = file_info.get("content", "")

            # بررسی requirements.txt
            if file_name == "requirements.txt":
                deps = self._parse_requirements(content)
                dependencies_found["python"].extend(deps)
                vulns = self._check_python_vulnerabilities(deps)
                vulnerabilities.extend(vulns)

            # بررسی package.json
            elif file_name == "package.json":
                deps = self._parse_package_json(content)
                dependencies_found["javascript"].extend(deps)
                vulns = self._check_js_vulnerabilities(deps)
                vulnerabilities.extend(vulns)

        return {
            "total_dependencies": {
                "python": len(dependencies_found["python"]),
                "javascript": len(dependencies_found["javascript"])
            },
            "vulnerabilities": vulnerabilities,
            "vulnerability_count": len(vulnerabilities),
            "severity_summary": self._summarize_severity(vulnerabilities)
        }

    def _parse_requirements(self, content: str) -> List[Dict[str, str]]:
        """پارس کردن requirements.txt"""
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # حذف کامنت‌های inline
            line = line.split('#')[0].strip()

            # پارس نسخه
            match = re.match(r'^([a-zA-Z0-9_-]+)([<>=!~]+)?(.+)?$', line)
            if match:
                deps.append({
                    "name": match.group(1).lower(),
                    "version": (match.group(2) or "") + (match.group(3) or ""),
                    "raw": line
                })
        return deps

    def _parse_package_json(self, content: str) -> List[Dict[str, str]]:
        """پارس کردن package.json"""
        deps = []
        try:
            pkg = json.loads(content)
            for dep_type in ["dependencies", "devDependencies"]:
                if dep_type in pkg:
                    for name, version in pkg[dep_type].items():
                        deps.append({
                            "name": name.lower(),
                            "version": version,
                            "type": dep_type
                        })
        except:
            pass
        return deps

    def _check_python_vulnerabilities(self, deps: List[Dict]) -> List[Dict]:
        """بررسی آسیب‌پذیری وابستگی‌های پایتون"""
        vulns = []
        for dep in deps:
            name = dep["name"]
            if name in self.KNOWN_VULNERABILITIES.get("python", {}):
                vuln_info = self.KNOWN_VULNERABILITIES["python"][name]
                vulns.append({
                    "type": "dependency_vulnerability",
                    "severity": "high",
                    "package": name,
                    "current_version": dep.get("version", "unknown"),
                    "vulnerable_versions": vuln_info["vulnerable_versions"],
                    "cve": vuln_info["cve"],
                    "message": f"وابستگی {name} دارای آسیب‌پذیری شناخته شده است",
                    "recommendation": f"به آخرین نسخه امن آپدیت کنید"
                })
        return vulns

    def _check_js_vulnerabilities(self, deps: List[Dict]) -> List[Dict]:
        """بررسی آسیب‌پذیری وابستگی‌های JavaScript"""
        vulns = []
        for dep in deps:
            name = dep["name"]
            if name in self.KNOWN_VULNERABILITIES.get("javascript", {}):
                vuln_info = self.KNOWN_VULNERABILITIES["javascript"][name]
                vulns.append({
                    "type": "dependency_vulnerability",
                    "severity": "high",
                    "package": name,
                    "current_version": dep.get("version", "unknown"),
                    "vulnerable_versions": vuln_info["vulnerable_versions"],
                    "cve": vuln_info["cve"],
                    "message": f"وابستگی {name} دارای آسیب‌پذیری شناخته شده است",
                    "recommendation": f"به آخرین نسخه امن آپدیت کنید"
                })
        return vulns

    def _summarize_severity(self, items: List[Dict]) -> Dict[str, int]:
        """خلاصه شدت‌ها"""
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for item in items:
            sev = item.get("severity", "low")
            if sev in summary:
                summary[sev] += 1
        return summary

    def full_security_scan(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        اسکن امنیتی کامل پروژه
        """
        all_secrets = []
        for file_info in files:
            content = file_info.get("content", "")
            if content:
                secrets = self.scan_content_for_secrets(content, file_info.get("path", ""))
                all_secrets.extend(secrets)

        license_info = self.detect_license(files)
        sensitive_files = self.check_sensitive_files(files)
        dependency_vulns = self.scan_dependencies(files)

        # محاسبه امتیاز امنیتی
        security_score = 100
        security_score -= len(all_secrets) * 10  # هر secret: -10
        security_score -= len(sensitive_files) * 15  # هر فایل حساس: -15
        security_score -= dependency_vulns["vulnerability_count"] * 5  # هر آسیب‌پذیری: -5
        if not license_info["has_license"]:
            security_score -= 5
        security_score = max(0, security_score)

        return {
            "security_score": security_score,
            "secrets": {
                "count": len(all_secrets),
                "findings": all_secrets,
                "severity_summary": self._summarize_severity(all_secrets)
            },
            "license": license_info,
            "sensitive_files": {
                "count": len(sensitive_files),
                "findings": sensitive_files
            },
            "dependencies": dependency_vulns,
            "summary": {
                "total_issues": len(all_secrets) + len(sensitive_files) + dependency_vulns["vulnerability_count"],
                "critical_issues": sum(1 for s in all_secrets if s.get("severity") == "critical") + len(sensitive_files),
                "recommendation": self._get_overall_recommendation(all_secrets, sensitive_files, dependency_vulns, license_info)
            },
            "scan_date": datetime.utcnow().isoformat()
        }

    def _get_overall_recommendation(self, secrets, sensitive_files, dep_vulns, license_info) -> str:
        """توصیه کلی"""
        if len(sensitive_files) > 0:
            return "فوری: فایل‌های حساس را از مخزن حذف کنید"
        if any(s.get("severity") == "critical" for s in secrets):
            return "فوری: secrets بحرانی شناسایی شده - فوراً حذف کنید و کلیدها را rotate کنید"
        if dep_vulns["vulnerability_count"] > 0:
            return "وابستگی‌های آسیب‌پذیر را آپدیت کنید"
        if not license_info["has_license"]:
            return "یک فایل LICENSE به پروژه اضافه کنید"
        return "وضعیت امنیتی خوب است"


# نمونه singleton
_scanner_instance = None

def get_security_scanner() -> SecurityScanner:
    """دریافت نمونه اسکنر امنیتی"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = SecurityScanner()
    return _scanner_instance
