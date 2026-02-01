# -*- coding: utf-8 -*-
"""
🔒 سرویس تحلیل امنیتی پروژه
Security Analyzer Service

قابلیت‌ها:
1. Secret Detection - شناسایی رازها (API Key, Password, Token)
2. License Analysis - تحلیل مجوز و وابستگی‌ها
3. Vulnerability Scan - اسکن آسیب‌پذیری‌ها
"""

import re
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# =====================================================
# الگوهای شناسایی رازها
# =====================================================

SECRET_PATTERNS = {
    # API Keys
    "aws_access_key": {
        "pattern": r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}",
        "severity": "critical",
        "description": "AWS Access Key شناسایی شد",
        "recommendation": "این کلید را فوراً از کد حذف کرده و rotate کنید"
    },
    "aws_secret_key": {
        "pattern": r"(?i)aws[_\-]?secret[_\-]?(?:access)?[_\-]?key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})",
        "severity": "critical",
        "description": "AWS Secret Key شناسایی شد",
        "recommendation": "این کلید را فوراً از کد حذف کرده و rotate کنید"
    },
    "openai_api_key": {
        "pattern": r"sk-[a-zA-Z0-9]{20,}T3BlbkFJ[a-zA-Z0-9]{20,}",
        "severity": "critical",
        "description": "OpenAI API Key شناسایی شد",
        "recommendation": "کلید را rotate کنید و از environment variable استفاده کنید"
    },
    "anthropic_api_key": {
        "pattern": r"sk-ant-[a-zA-Z0-9\-_]{90,}",
        "severity": "critical",
        "description": "Anthropic API Key شناسایی شد",
        "recommendation": "کلید را rotate کنید و از environment variable استفاده کنید"
    },
    "github_token": {
        "pattern": r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
        "severity": "critical",
        "description": "GitHub Token شناسایی شد",
        "recommendation": "توکن را revoke کرده و جدید بسازید"
    },
    "google_api_key": {
        "pattern": r"AIza[0-9A-Za-z\-_]{35}",
        "severity": "high",
        "description": "Google API Key شناسایی شد",
        "recommendation": "کلید را محدود کرده یا rotate کنید"
    },
    "stripe_key": {
        "pattern": r"(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}",
        "severity": "critical",
        "description": "Stripe API Key شناسایی شد",
        "recommendation": "کلید را فوراً rotate کنید"
    },
    "firebase_key": {
        "pattern": r"AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}",
        "severity": "high",
        "description": "Firebase Server Key شناسایی شد",
        "recommendation": "کلید را rotate کنید"
    },

    # Generic Secrets
    "generic_api_key": {
        "pattern": r"(?i)(?:api[_\-]?key|apikey)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-_]{20,})['\"]?",
        "severity": "high",
        "description": "API Key احتمالی شناسایی شد",
        "recommendation": "بررسی کنید و از environment variable استفاده کنید"
    },
    "generic_secret": {
        "pattern": r"(?i)(?:secret|password|passwd|pwd)[_\-]?(?:key)?['\"]?\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
        "severity": "high",
        "description": "رمز عبور یا secret احتمالی شناسایی شد",
        "recommendation": "از environment variable یا secret manager استفاده کنید"
    },
    "private_key": {
        "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "severity": "critical",
        "description": "کلید خصوصی شناسایی شد",
        "recommendation": "کلید را فوراً از کد حذف کنید"
    },
    "jwt_token": {
        "pattern": r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
        "severity": "medium",
        "description": "JWT Token شناسایی شد",
        "recommendation": "بررسی کنید این توکن hardcoded نباشد"
    },

    # Database URLs
    "database_url": {
        "pattern": r"(?:postgres|mysql|mongodb|redis)://[^\s]+:[^\s]+@[^\s]+",
        "severity": "critical",
        "description": "Database URL با credentials شناسایی شد",
        "recommendation": "از environment variable استفاده کنید"
    },

    # Slack/Discord
    "slack_webhook": {
        "pattern": r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+",
        "severity": "high",
        "description": "Slack Webhook URL شناسایی شد",
        "recommendation": "این URL را از کد حذف کنید"
    },
    "discord_webhook": {
        "pattern": r"https://discord(?:app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9\-_]+",
        "severity": "high",
        "description": "Discord Webhook URL شناسایی شد",
        "recommendation": "این URL را از کد حذف کنید"
    },
}

# فایل‌هایی که باید ignore شوند
IGNORE_FILES = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    'dist', 'build', '.next', '.nuxt', '.cache',
    '*.pyc', '*.pyo', '*.min.js', '*.min.css',
    'package-lock.json', 'yarn.lock', 'poetry.lock'
}

# فایل‌های حساس
SENSITIVE_FILES = {
    '.env', '.env.local', '.env.production', '.env.development',
    'config.json', 'secrets.json', 'credentials.json',
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    '.htpasswd', '.htaccess',
    'wp-config.php', 'config.php',
    'database.yml', 'secrets.yml'
}


class SecurityAnalyzer:
    """
    تحلیل‌گر امنیتی پروژه
    """

    def __init__(self):
        self.compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """کامپایل الگوهای regex برای performance بهتر"""
        for name, config in SECRET_PATTERNS.items():
            try:
                self.compiled_patterns[name] = {
                    "regex": re.compile(config["pattern"]),
                    **config
                }
            except re.error as e:
                logger.error(f"Invalid regex pattern for {name}: {e}")

    # =================================================
    # 1. Secret Detection
    # =================================================

    def scan_for_secrets(
        self,
        files: List[Dict[str, Any]],
        include_low_confidence: bool = False
    ) -> Dict[str, Any]:
        """
        اسکن فایل‌ها برای شناسایی رازها

        Returns:
            {
                "total_files_scanned": int,
                "secrets_found": [
                    {
                        "file_path": str,
                        "line_number": int,
                        "secret_type": str,
                        "severity": str,
                        "description": str,
                        "recommendation": str,
                        "masked_value": str,
                        "context": str
                    }
                ],
                "sensitive_files": [str],
                "summary": {
                    "critical": int,
                    "high": int,
                    "medium": int,
                    "low": int
                },
                "score": int  # 0-100, higher is better (less secrets)
            }
        """
        result = {
            "total_files_scanned": 0,
            "secrets_found": [],
            "sensitive_files": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "score": 100,
            "scanned_at": datetime.utcnow().isoformat()
        }

        for file_data in files:
            file_path = file_data.get("path", file_data.get("file_path", ""))
            content = file_data.get("content", "")

            # Skip ignored files
            if self._should_ignore_file(file_path):
                continue

            result["total_files_scanned"] += 1

            # Check for sensitive file names
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            if filename in SENSITIVE_FILES or any(file_path.endswith(sf) for sf in SENSITIVE_FILES):
                result["sensitive_files"].append({
                    "path": file_path,
                    "reason": "نام فایل حساس",
                    "severity": "high",
                    "recommendation": "این فایل نباید در git باشد - به .gitignore اضافه کنید"
                })

            # Scan content
            if content:
                secrets = self._scan_content(file_path, content, include_low_confidence)
                result["secrets_found"].extend(secrets)

        # Calculate summary
        for secret in result["secrets_found"]:
            severity = secret.get("severity", "medium")
            result["summary"][severity] = result["summary"].get(severity, 0) + 1

        for sf in result["sensitive_files"]:
            result["summary"]["high"] = result["summary"].get("high", 0) + 1

        # Calculate score (100 - penalties)
        penalties = (
            result["summary"]["critical"] * 25 +
            result["summary"]["high"] * 15 +
            result["summary"]["medium"] * 5 +
            result["summary"]["low"] * 2
        )
        result["score"] = max(0, 100 - penalties)

        logger.info(f"Secret scan complete: {len(result['secrets_found'])} secrets found in {result['total_files_scanned']} files")

        return result

    def _scan_content(
        self,
        file_path: str,
        content: str,
        include_low_confidence: bool
    ) -> List[Dict]:
        """اسکن محتوای یک فایل"""
        secrets = []
        lines = content.split('\n')

        for pattern_name, config in self.compiled_patterns.items():
            regex = config["regex"]

            for line_num, line in enumerate(lines, 1):
                # Skip comments and empty lines
                stripped = line.strip()
                if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                    continue

                matches = regex.findall(line)
                if matches:
                    for match in matches:
                        # Get the actual secret value
                        if isinstance(match, tuple):
                            secret_value = match[0] if match else ""
                        else:
                            secret_value = match

                        # Filter low confidence matches
                        if not include_low_confidence:
                            # Skip very short matches or common false positives
                            if len(str(secret_value)) < 10:
                                continue
                            if secret_value.lower() in ['true', 'false', 'null', 'none', 'example', 'test']:
                                continue

                        secrets.append({
                            "file_path": file_path,
                            "line_number": line_num,
                            "secret_type": pattern_name,
                            "severity": config["severity"],
                            "description": config["description"],
                            "recommendation": config["recommendation"],
                            "masked_value": self._mask_secret(str(secret_value)),
                            "context": self._get_context(lines, line_num, 2),
                            "hash": hashlib.sha256(str(secret_value).encode()).hexdigest()[:16]
                        })

        return secrets

    def _mask_secret(self, value: str) -> str:
        """پنهان‌سازی بخشی از راز برای نمایش"""
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    def _get_context(self, lines: List[str], line_num: int, context_lines: int) -> str:
        """گرفتن context اطراف خط"""
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)

        context_parts = []
        for i in range(start, end):
            prefix = ">>>" if i == line_num - 1 else "   "
            context_parts.append(f"{prefix} {i+1}: {lines[i][:100]}")

        return "\n".join(context_parts)

    def _should_ignore_file(self, file_path: str) -> bool:
        """آیا فایل باید ignore شود"""
        for ignore in IGNORE_FILES:
            if ignore in file_path:
                return True
        return False

    # =================================================
    # 2. License Analysis
    # =================================================

    def analyze_licenses(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تحلیل مجوز پروژه و وابستگی‌ها

        Returns:
            {
                "project_license": {
                    "found": bool,
                    "type": str,
                    "file_path": str
                },
                "dependency_licenses": [
                    {
                        "package": str,
                        "version": str,
                        "license": str,
                        "compatible": bool
                    }
                ],
                "recommendations": [str],
                "score": int
            }
        """
        result = {
            "project_license": {
                "found": False,
                "type": None,
                "file_path": None,
                "content_preview": None
            },
            "dependency_licenses": [],
            "potential_issues": [],
            "recommendations": [],
            "score": 0,
            "analyzed_at": datetime.utcnow().isoformat()
        }

        # Find LICENSE file
        license_files = ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING', 'LICENSE-MIT', 'LICENSE-APACHE']

        for file_data in files:
            file_path = file_data.get("path", file_data.get("file_path", ""))
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            content = file_data.get("content", "")

            # Check for LICENSE file
            if filename.upper() in [lf.upper() for lf in license_files]:
                result["project_license"]["found"] = True
                result["project_license"]["file_path"] = file_path
                result["project_license"]["type"] = self._detect_license_type(content)
                result["project_license"]["content_preview"] = content[:500] if content else None

            # Parse package.json for npm dependencies
            if filename == "package.json" and content:
                npm_deps = self._parse_package_json_licenses(content)
                result["dependency_licenses"].extend(npm_deps)

            # Parse requirements.txt for Python dependencies
            if filename in ["requirements.txt", "Pipfile", "pyproject.toml"] and content:
                py_deps = self._parse_python_dependencies(content, filename)
                result["dependency_licenses"].extend(py_deps)

        # Generate recommendations
        if not result["project_license"]["found"]:
            result["recommendations"].append("پروژه فاقد فایل LICENSE است - افزودن مجوز توصیه می‌شود")
            result["potential_issues"].append({
                "type": "missing_license",
                "severity": "high",
                "description": "پروژه فاقد مجوز است. بدون مجوز، دیگران نمی‌توانند از کد استفاده کنند."
            })

        # Check for copyleft licenses in dependencies
        copyleft_licenses = ['GPL', 'LGPL', 'AGPL', 'MPL']
        for dep in result["dependency_licenses"]:
            license_type = dep.get("license", "").upper()
            for copyleft in copyleft_licenses:
                if copyleft in license_type:
                    result["potential_issues"].append({
                        "type": "copyleft_dependency",
                        "severity": "medium",
                        "package": dep["package"],
                        "license": dep["license"],
                        "description": f"وابستگی {dep['package']} دارای مجوز {dep['license']} است که ممکن است تعهداتی ایجاد کند"
                    })

        # Calculate score
        score = 50  # Base score
        if result["project_license"]["found"]:
            score += 30
        if len(result["potential_issues"]) == 0:
            score += 20
        else:
            score -= len(result["potential_issues"]) * 5

        result["score"] = max(0, min(100, score))

        return result

    def _detect_license_type(self, content: str) -> str:
        """تشخیص نوع مجوز از محتوا"""
        content_lower = content.lower()

        license_indicators = {
            "MIT": ["mit license", "permission is hereby granted, free of charge"],
            "Apache-2.0": ["apache license", "version 2.0"],
            "GPL-3.0": ["gnu general public license", "version 3"],
            "GPL-2.0": ["gnu general public license", "version 2"],
            "BSD-3-Clause": ["bsd 3-clause", "redistribution and use"],
            "BSD-2-Clause": ["bsd 2-clause"],
            "ISC": ["isc license"],
            "MPL-2.0": ["mozilla public license"],
            "LGPL": ["lesser general public license"],
            "AGPL": ["affero general public license"],
            "Unlicense": ["unlicense", "public domain"],
            "CC0": ["cc0", "creative commons zero"],
        }

        for license_type, indicators in license_indicators.items():
            if all(ind in content_lower for ind in indicators[:1]):  # Check first indicator
                return license_type

        return "Unknown"

    def _parse_package_json_licenses(self, content: str) -> List[Dict]:
        """استخراج اطلاعات وابستگی‌ها از package.json"""
        deps = []
        try:
            data = json.loads(content)

            for dep_type in ["dependencies", "devDependencies"]:
                if dep_type in data:
                    for pkg, version in data[dep_type].items():
                        deps.append({
                            "package": pkg,
                            "version": version,
                            "source": "npm",
                            "license": "Unknown",  # Would need npm API to get actual license
                            "dev_dependency": dep_type == "devDependencies"
                        })
        except json.JSONDecodeError:
            pass

        return deps

    def _parse_python_dependencies(self, content: str, filename: str) -> List[Dict]:
        """استخراج وابستگی‌های پایتون"""
        deps = []

        if filename == "requirements.txt":
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Parse package==version or package>=version
                    match = re.match(r'^([a-zA-Z0-9\-_]+)(?:[=<>!~]+(.*))?', line)
                    if match:
                        deps.append({
                            "package": match.group(1),
                            "version": match.group(2) or "any",
                            "source": "pypi",
                            "license": "Unknown"  # Would need PyPI API
                        })

        return deps

    # =================================================
    # 3. Vulnerability Summary
    # =================================================

    def generate_security_report(
        self,
        files: List[Dict[str, Any]],
        include_low_confidence: bool = False
    ) -> Dict[str, Any]:
        """
        تولید گزارش امنیتی جامع
        """
        secrets_result = self.scan_for_secrets(files, include_low_confidence)
        license_result = self.analyze_licenses(files)

        # Overall security score
        overall_score = int((secrets_result["score"] * 0.6 + license_result["score"] * 0.4))

        # Determine status
        if overall_score >= 80:
            status = "good"
            status_text = "وضعیت امنیتی خوب"
        elif overall_score >= 50:
            status = "warning"
            status_text = "نیاز به بهبود امنیتی"
        else:
            status = "critical"
            status_text = "مشکلات امنیتی بحرانی"

        return {
            "overall_score": overall_score,
            "status": status,
            "status_text": status_text,
            "secrets": secrets_result,
            "licenses": license_result,
            "total_issues": (
                len(secrets_result["secrets_found"]) +
                len(secrets_result["sensitive_files"]) +
                len(license_result["potential_issues"])
            ),
            "critical_count": secrets_result["summary"]["critical"],
            "recommendations": [
                *[f"🔴 {s['description']}: {s['file_path']}:{s['line_number']}"
                  for s in secrets_result["secrets_found"] if s["severity"] == "critical"],
                *license_result["recommendations"]
            ],
            "generated_at": datetime.utcnow().isoformat()
        }


# =====================================================
# Singleton Instance
# =====================================================

_security_analyzer_instance: Optional[SecurityAnalyzer] = None

def get_security_analyzer() -> SecurityAnalyzer:
    """دریافت نمونه SecurityAnalyzer"""
    global _security_analyzer_instance
    if _security_analyzer_instance is None:
        _security_analyzer_instance = SecurityAnalyzer()
    return _security_analyzer_instance
