# -*- coding: utf-8 -*-
"""
سرویس راه‌اندازی خودکار هوشمند پروژه
تحلیل عمیق پروژه و تولید دستورات و فیلدهای اختصاصی با AI
🆕 با ثبت سطر به سطر عملیات در ژورنال
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import re

# استفاده از لاگر ساختاریافته
from ..core.logging_utils import StructuredLogger

# لاگر قدیمی برای سازگاری
logger = logging.getLogger(__name__)

# لاگر ساختاریافته جدید
slog = StructuredLogger(__name__, "AUTO-SETUP")


# =====================================
# 🆕 Helper برای ثبت عملیات جزئی در ژورنال
# =====================================

def log_auto_setup_operation(
    db_session,
    project_id: str,
    parent_log_id: str,
    operation_type: str,
    summary: str,
    details: dict = None,
    before_value: str = None,
    after_value: str = None,
    target_type: str = None,
    target_id: str = None,
    target_name: str = None,
    status: str = "completed"
):
    """
    🆕 ثبت یک عملیات جزئی auto-setup در ژورنال
    برای قابلیت کلیک و مشاهده جزئیات هر سطر
    """
    if not db_session:
        return None

    try:
        from ..api.routes.project_journal import log_detailed_operation
        return log_detailed_operation(
            db=db_session,
            project_id=project_id,
            parent_log_id=parent_log_id,
            operation_type=operation_type,
            summary=summary,
            details=details,
            before_value=before_value,
            after_value=after_value,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status=status
        )
    except Exception as e:
        logger.warning(f"Could not log detailed operation: {e}")
        return None


# =====================================
# تحلیل عمیق فایل‌های پروژه
# =====================================

def extract_project_insights(files: List[Dict]) -> Dict[str, Any]:
    """
    استخراج اطلاعات عمیق از فایل‌های پروژه
    """
    insights = {
        "technologies": [],
        "frameworks": [],
        "patterns": [],
        "dependencies": [],
        "api_endpoints": [],
        "database_models": [],
        "config_files": [],
        "test_files": [],
        "main_files": [],
        "domain": None,
        "architecture": None,
        "language": None,
        "key_features": [],
    }

    for file in files:
        path = file.get("path", file.get("file_path", "")).lower()
        content = file.get("content", "") or ""

        # --- شناسایی فایل‌های مهم ---

        # فایل‌های تنظیمات
        if any(cfg in path for cfg in ["package.json", "requirements.txt", "pyproject.toml",
                                        "cargo.toml", "go.mod", "pubspec.yaml", "composer.json"]):
            insights["config_files"].append(path)
            _parse_dependencies(path, content, insights)

        # فایل‌های اصلی
        if any(main in path for main in ["main.", "app.", "index.", "server.", "__init__"]):
            insights["main_files"].append(path)

        # فایل‌های تست
        if "test" in path or "spec" in path:
            insights["test_files"].append(path)

        # --- تحلیل محتوا ---

        # API endpoints (FastAPI/Flask/Express)
        if "@router" in content or "@app.route" in content or "app.get(" in content:
            endpoints = re.findall(r'["\']/([\w\-/{}]+)["\']', content)
            insights["api_endpoints"].extend(endpoints[:10])

        # Database models
        if "class" in content and ("Base" in content or "Model" in content or "Schema" in content):
            models = re.findall(r'class\s+(\w+)\s*\(', content)
            insights["database_models"].extend([m for m in models if not m.startswith("_")][:10])

        # Framework detection
        _detect_frameworks(content, insights)

        # Pattern detection
        _detect_patterns(path, content, insights)

    # تشخیص زبان اصلی
    insights["language"] = _detect_main_language(files)

    # تشخیص معماری
    insights["architecture"] = _detect_architecture(insights)

    # تشخیص دامنه کاری
    insights["domain"] = _detect_domain(insights, files)

    # حذف تکراری‌ها
    for key in ["technologies", "frameworks", "patterns", "api_endpoints", "database_models"]:
        insights[key] = list(set(insights[key]))

    return insights


def _parse_dependencies(path: str, content: str, insights: Dict):
    """پارس وابستگی‌ها"""
    try:
        if "package.json" in path:
            data = json.loads(content)
            deps = list(data.get("dependencies", {}).keys())
            deps += list(data.get("devDependencies", {}).keys())
            insights["dependencies"].extend(deps[:30])

            # تشخیص فریم‌ورک
            if "react" in deps or "next" in deps:
                insights["frameworks"].append("React/Next.js")
            if "vue" in deps:
                insights["frameworks"].append("Vue.js")
            if "express" in deps:
                insights["frameworks"].append("Express.js")
            if "nestjs" in str(deps):
                insights["frameworks"].append("NestJS")

        elif "requirements.txt" in path:
            deps = [line.split("==")[0].split(">=")[0].strip()
                    for line in content.split("\n") if line.strip() and not line.startswith("#")]
            insights["dependencies"].extend(deps[:30])

            # تشخیص فریم‌ورک
            if "fastapi" in deps:
                insights["frameworks"].append("FastAPI")
            if "django" in deps:
                insights["frameworks"].append("Django")
            if "flask" in deps:
                insights["frameworks"].append("Flask")
            if any("ccxt" in d or "pandas" in d for d in deps):
                insights["technologies"].append("Trading/Finance")

    except Exception:
        pass


def _detect_frameworks(content: str, insights: Dict):
    """تشخیص فریم‌ورک‌ها از محتوای کد"""
    framework_patterns = {
        "FastAPI": ["from fastapi", "FastAPI()", "@router"],
        "Django": ["from django", "django.db", "INSTALLED_APPS"],
        "Flask": ["from flask", "Flask(__name__)"],
        "React": ["import React", "useState", "useEffect", "jsx"],
        "Vue": ["createApp", "defineComponent", "<template>"],
        "Express": ["express()", "app.listen", "req, res"],
        "NestJS": ["@Controller", "@Injectable", "@Module"],
        "SQLAlchemy": ["from sqlalchemy", "Column(", "relationship("],
        "Prisma": ["@prisma/client", "PrismaClient"],
        "TypeORM": ["@Entity", "@Column", "getRepository"],
    }

    for framework, patterns in framework_patterns.items():
        if any(p in content for p in patterns):
            insights["frameworks"].append(framework)


def _detect_patterns(path: str, content: str, insights: Dict):
    """تشخیص الگوهای طراحی و معماری"""
    # Patterns
    if "service" in path or "Service" in content:
        insights["patterns"].append("Service Layer")
    if "repository" in path or "Repository" in content:
        insights["patterns"].append("Repository Pattern")
    if "controller" in path or "Controller" in content:
        insights["patterns"].append("MVC/Controller")
    if "middleware" in path:
        insights["patterns"].append("Middleware")
    if "hook" in path or "use" in path:
        insights["patterns"].append("Hooks Pattern")
    if "store" in path or "redux" in content.lower():
        insights["patterns"].append("State Management")
    if "api/routes" in path or "routes/" in path:
        insights["patterns"].append("RESTful API")
    if "graphql" in content.lower():
        insights["patterns"].append("GraphQL")
    if "websocket" in content.lower() or "socket.io" in content.lower():
        insights["patterns"].append("WebSocket/Real-time")


def _detect_main_language(files: List[Dict]) -> str:
    """تشخیص زبان اصلی پروژه"""
    extensions = {}
    for f in files:
        path = f.get("path", f.get("file_path", ""))
        if "." in path:
            ext = path.split(".")[-1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1

    lang_map = {
        "py": "Python",
        "js": "JavaScript",
        "ts": "TypeScript",
        "tsx": "TypeScript/React",
        "jsx": "JavaScript/React",
        "go": "Go",
        "rs": "Rust",
        "java": "Java",
        "kt": "Kotlin",
        "swift": "Swift",
        "dart": "Dart",
        "rb": "Ruby",
        "php": "PHP",
    }

    if extensions:
        top_ext = max(extensions, key=extensions.get)
        return lang_map.get(top_ext, top_ext.upper())
    return "Unknown"


def _detect_architecture(insights: Dict) -> str:
    """تشخیص معماری پروژه"""
    frameworks = insights.get("frameworks", [])
    patterns = insights.get("patterns", [])

    if "FastAPI" in frameworks or "Express" in frameworks or "NestJS" in frameworks:
        if "Repository Pattern" in patterns:
            return "Clean Architecture / Layered"
        return "REST API Backend"

    if "React/Next.js" in frameworks or "Vue.js" in frameworks:
        if insights.get("api_endpoints"):
            return "Full-Stack Application"
        return "Frontend SPA"

    if "Django" in frameworks:
        return "Django MTV (Model-Template-View)"

    if "Service Layer" in patterns and "Repository Pattern" in patterns:
        return "Domain-Driven Design"

    if "GraphQL" in patterns:
        return "GraphQL API"

    return "Standard Application"


def _detect_domain(insights: Dict, files: List[Dict]) -> str:
    """تشخیص دامنه کاری پروژه"""
    content_all = " ".join([f.get("content", "")[:500] for f in files[:20]])
    deps = " ".join(insights.get("dependencies", []))

    domain_keywords = {
        "Trading/Finance": ["ccxt", "trading", "backtest", "strategy", "portfolio", "stock", "crypto", "binance", "exchange"],
        "E-commerce": ["cart", "checkout", "payment", "product", "order", "shop", "stripe"],
        "Social/Chat": ["message", "chat", "notification", "friend", "follow", "post", "comment"],
        "CMS/Blog": ["article", "blog", "post", "content", "category", "tag", "wordpress"],
        "Analytics/Dashboard": ["dashboard", "chart", "analytics", "report", "metric", "statistic"],
        "Authentication/IAM": ["auth", "login", "user", "permission", "role", "jwt", "oauth"],
        "AI/ML": ["tensorflow", "pytorch", "model", "train", "predict", "neural", "nlp", "gpt"],
        "IoT/Hardware": ["sensor", "device", "mqtt", "raspberry", "arduino", "gpio"],
        "Gaming": ["game", "player", "score", "level", "sprite", "unity", "godot"],
    }

    combined = (content_all + " " + deps).lower()

    for domain, keywords in domain_keywords.items():
        matches = sum(1 for kw in keywords if kw in combined)
        if matches >= 2:
            return domain

    return "General Application"


# =====================================
# تولید دستورات هوشمند با AI
# =====================================

async def generate_intelligent_setup(
    project_name: str,
    project_description: str,
    insights: Dict[str, Any],
    sample_files: List[Dict],
    existing_fields: List[Dict] = None,
    model_id: str = "claude",
    full_review: bool = True,  # بررسی کامل و به‌روزرسانی فیلدهای موجود
    full_context: Dict[str, Any] = None  # 🔴 context کامل شامل ایرادات، گزارشات، نقشه راه
) -> Dict[str, Any]:
    """
    تولید دستورات و فیلدهای کاملاً اختصاصی با AI
    با پشتیبانی از action_type، archive_after_run، field_type و priority
    🔴 نسخه بهبودیافته: در نظر گرفتن ایرادات، گزارشات، نقشه راه و وضعیت فعلی
    """
    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message

        ai_manager = get_ai_manager()

        # 🔴 بررسی اولیه وضعیت AI
        available_providers = ai_manager.get_available_providers()
        logger.info(f"🤖 generate_intelligent_setup - Available AI providers: {available_providers}")

        if not available_providers:
            logger.error("❌ No AI providers available in generate_intelligent_setup!")
            return {"success": False, "error": "هیچ مدل AI در دسترس نیست. لطفاً API key را در تنظیمات وارد کنید."}

        # ساخت خلاصه فایل‌های نمونه با محتوا
        files_detail = []
        for f in sample_files[:10]:
            path = f.get("path", f.get("file_path", ""))
            content = f.get("content", "")
            if content:
                # نمایش بخشی از محتوای فایل
                preview = content[:800] if len(content) > 800 else content
                files_detail.append(f"### {path}\n```\n{preview}\n```")

        files_text = "\n\n".join(files_detail) if files_detail else "فایلی برای نمایش نیست"

        # لیست فایل‌های موجود برای تشخیص چه چیزی کم است
        existing_files = [f.get("path", f.get("file_path", "")) for f in sample_files]
        file_list = "\n".join([f"- {p}" for p in existing_files[:30]])

        # لیست فیلدهای موجود (غیر بایگانی) با جزئیات کامل
        existing_field_details = []
        existing_field_names = []
        if existing_fields:
            for ef in existing_fields:
                if not ef.get("archived"):
                    existing_field_names.append(ef.get("name", ""))
                    existing_field_details.append({
                        "id": ef.get("id"),
                        "name": ef.get("name"),
                        "value": ef.get("value", "")[:200],  # خلاصه
                        "field_type": ef.get("field_type", "temporary"),
                        "priority": ef.get("priority", 5),
                        "action_type": ef.get("action_type", "display"),
                        "has_attachments": len(ef.get("attachments", [])) > 0
                    })

        existing_fields_text = ", ".join(existing_field_names) if existing_field_names else "هیچ"
        existing_fields_json = json.dumps(existing_field_details, ensure_ascii=False, indent=2) if existing_field_details else "[]"

        # 🆕 تنظیم prompt براساس حالت بررسی کامل
        review_section = ""
        if full_review and existing_field_details:
            review_section = f"""
## ⚠️ بررسی و به‌روزرسانی فیلدهای موجود (مهم!)
فیلدهای فعلی:
{existing_fields_json}

**وظیفه بررسی:**
1. هر فیلد موجود را بررسی کن
2. فیلدهایی که باید **بایگانی** شوند (انجام شده یا منسوخ): در لیست `fields_to_archive` قرار بده
3. فیلدهایی که باید **ادغام** شوند (مشابه یا تکراری): در لیست `fields_to_merge` قرار بده
4. فیلدهایی که باید **به‌روزرسانی** شوند: در لیست `fields_to_update` قرار بده
5. فقط فیلدهای **واقعاً جدید** که وجود ندارند در `dynamic_fields` قرار بده
"""

        # 🔴 بخش context کامل (ایرادات، گزارشات، نقشه راه، ...)
        context_section = ""
        if full_context:
            run_count = full_context.get("auto_setup_run_count", 1)
            context_section = f"""
## 🔴 وضعیت فعلی پروژه (این بار {run_count}م است که راه‌اندازی خودکار اجرا می‌شود!)

"""
            # فیلدهای اجرا نشده
            unexecuted = full_context.get("unexecuted_fields", [])
            if unexecuted:
                context_section += f"""### ⏳ فیلدهای اجرا نشده ({len(unexecuted)} عدد) - این‌ها هنوز انجام نشده‌اند!
"""
                for uf in unexecuted[:10]:
                    context_section += f"- **{uf.get('name')}** (اولویت: {uf.get('priority', 5)}, نوع: {uf.get('action_type', 'display')})\n"
                context_section += "\n"

            # ایرادات تب سلامت
            health_issues = full_context.get("health_issues", [])
            if health_issues:
                context_section += f"""### ⚠️ ایرادات شناسایی شده در تحلیل سلامت ({len(health_issues)} مورد)
"""
                for hi in health_issues[:10]:
                    issue_text = hi.get("issue", hi.get("description", hi.get("title", str(hi))))
                    severity = hi.get("severity", "medium")
                    context_section += f"- [{severity}] {issue_text[:100]}\n"
                context_section += "\n"

            # فایل‌های مشکل‌دار
            problematic = full_context.get("problematic_files", [])
            if problematic:
                context_section += f"""### 📁 فایل‌های با امتیاز پایین ({len(problematic)} فایل)
"""
                for pf in problematic[:5]:
                    context_section += f"- **{pf.get('path')}** (امتیاز: {pf.get('score')})\n"
                context_section += "\n"

            # گزارشات اخیر
            reports = full_context.get("recent_reports", [])
            if reports:
                context_section += f"""### 📊 گزارشات اخیر ({len(reports)} گزارش)
"""
                for rp in reports[:3]:
                    context_section += f"- {rp.get('type')}: {rp.get('summary', '')[:80]}... ({rp.get('issues_found', 0)} مشکل)\n"
                context_section += "\n"

            # نقشه راه
            roadmap = full_context.get("roadmap_content", "")
            if roadmap:
                context_section += f"""### 🗺️ خلاصه نقشه راه
{roadmap[:500]}...

"""

            # حافظه فعلی
            current_memory = full_context.get("current_memory", "")
            if current_memory:
                context_section += f"""### 💾 حافظه فعلی (این را بهبود بده، نه جایگزین!)
{current_memory[:300]}...

"""

            # اطلاعات GitHub
            github = full_context.get("github_info", {})
            if github.get("source") == "github":
                context_section += f"""### 🔗 اتصال GitHub
- ریپو: {github.get('owner')}/{github.get('repo')}
- شاخه: {github.get('branch', 'main')}
(می‌توانی فیلدهایی با action_type=github_commit برای تغییر مستقیم فایل‌ها ایجاد کنی)

"""

            context_section += """
## ⚠️ نکات مهم:
1. **این بار {run_count}م است!** - فیلدهای تکراری نساز، فقط مشکلات واقعی جدید را هدف بگیر
2. **فیلدهای اجرا نشده را بایگانی نکن** - آنها هنوز کار دارند
3. **ایرادات سلامت را در اولویت بگذار** - برای هر ایراد مهم یک فیلد بساز
4. **حافظه را بهبود بده** - اطلاعات مفید بیشتری اضافه کن، چیزهای موجود را حذف نکن
5. **از نقشه راه پیروی کن** - فیلدها باید در راستای اهداف نقشه راه باشند
""".format(run_count=run_count)

        prompt = f"""تو یک معمار نرم‌افزار و DevOps متخصص هستی. این پروژه را تحلیل کن و دستورات دقیق و اختصاصی برای کار با AI تولید کن.

## اطلاعات پروژه
- **نام**: {project_name}
- **توضیحات**: {project_description or 'ندارد'}
- **زبان اصلی**: {insights.get('language', 'نامشخص')}
- **فریم‌ورک‌ها**: {', '.join(insights.get('frameworks', [])) or 'نامشخص'}
- **معماری**: {insights.get('architecture', 'نامشخص')}
- **دامنه کاری**: {insights.get('domain', 'نامشخص')}
- **الگوهای طراحی**: {', '.join(insights.get('patterns', [])) or 'نامشخص'}
- **API Endpoints**: {', '.join(insights.get('api_endpoints', [])[:5]) or 'ندارد'}
- **مدل‌های دیتابیس**: {', '.join(insights.get('database_models', [])[:5]) or 'ندارد'}
- **وابستگی‌ها**: {', '.join(insights.get('dependencies', [])[:15]) or 'نامشخص'}

## فایل‌های موجود در پروژه
{file_list}

## نمونه محتوای فایل‌ها
{files_text}
{review_section}
{context_section}
## وظیفه تو
بر اساس تحلیل دقیق این پروژه، یک JSON با این ساختار برگردان:

{{
    "memory_instructions": "🔴 محتوای دقیق و حرفه‌ای باکس حافظه (حداقل ۱۰۰۰ کاراکتر). این بخش باید شامل موارد زیر باشد:\n1. **معماری سیستم**: توضیح ساختار لایه‌ها (frontend/backend/database)\n2. **استانداردهای کدنویسی**: naming conventions، فرمت فایل‌ها، قواعد import\n3. **مسیرهای کلیدی**: مسیر models, routes, services, components\n4. **نکات امنیتی**: authentication, authorization, CORS\n5. **نحوه تست**: چگونه کد تست می‌شود\n6. **دستورات مهم**: npm/pip commands, deployment steps\n7. **وابستگی‌های کلیدی**: فریم‌ورک‌ها و کتابخانه‌های اصلی\n8. **نقاط حساس**: فایل‌هایی که تغییر آنها خطرناک است\n⚠️ محتوا باید دقیق، کاربردی و مخصوص این پروژه باشد - نه عمومی!",

    "fields_to_archive": ["id_فیلد_1", "id_فیلد_2"],

    "fields_to_merge": [
        {{"source_ids": ["id1", "id2"], "merged_name": "نام فیلد ادغام‌شده", "merged_value": "دستور ادغام‌شده"}}
    ],

    "fields_to_update": [
        {{"id": "id_فیلد", "new_value": "دستور جدید", "new_priority": 3, "reason": "چرا باید آپدیت شود"}}
    ],

    "dynamic_fields": [
        {{
            "name": "نام فیلد (فارسی، مرتبط با این پروژه)",
            "value": "دستور دقیق برای AI (فارسی) - توضیح کامل چه کدی تولید شود",
            "why": "چرا این فیلد برای این پروژه مهمه",
            "recommended_model": "claude یا openai یا deepseek",
            "action_type": "display یا github_commit یا github_multi_commit",
            "target_path": "مسیر فایل در ریپو اگر action_type=github_commit باشد",
            "archive_after_run": true/false,
            "deploy_after_commit": true/false,
            "field_type": "permanent یا temporary",
            "priority": 1-10,
            "needs_trigger": false,
            "is_one_time": true/false
        }}
    ],

    "missing_files": [
        {{"path": "مسیر فایل", "description": "توضیح", "priority": "high/medium/low"}}
    ],

    "project_summary": "خلاصه ۳-۵ خطی از ماهیت، هدف و وضعیت فعلی پروژه",
    "key_recommendations": ["توصیه ۱", "توصیه ۲", "توصیه ۳"]
}}

## راهنمای field_type:
- **permanent**: فیلدهای دائمی/تکرارشونده که باید همیشه فعال باشند (بررسی کد، تحلیل، گزارش‌گیری)
- **temporary**: فیلدهای موقت/یکبار مصرف که بعد از اجرا بایگانی می‌شوند (ایجاد فایل، setup)

## راهنمای priority (1=بالاترین، 10=پایین‌ترین):
- 1-2: بحرانی/فوری - باید ابتدا اجرا شود
- 3-4: بالا
- 5: عادی (پیش‌فرض)
- 6-7: پایین
- 8-10: خیلی پایین - در صورت فرصت

## راهنمای انتخاب action_type:
- **display**: فقط برای مشاوره، بررسی کد، سوال جواب
- **github_commit**: وقتی باید یک فایل خاص در ریپو ایجاد/بروزرسانی شود
- **github_multi_commit**: وقتی باید چند فایل مرتبط تولید شود

نکات مهم:
- حداقل ۲ و حداکثر ۶ فیلد پویای **جدید** تعریف کن (فقط اگر واقعاً نیاز باشد)
- فیلدهای تکراری با فیلدهای موجود ایجاد نکن - به‌روزرسانی یا ادغام کن
- فیلدهای permanent باید priority پایین‌تر (عدد بالاتر) داشته باشند
- فیلدهای temporary با اولویت بالا باید اول اجرا شوند"""

        messages = [
            Message(role="system", content="تو یک معمار نرم‌افزار متخصص هستی که پروژه‌ها را تحلیل می‌کنی. پاسخ را فقط به صورت JSON معتبر بده."),
            Message(role="user", content=prompt)
        ]

        # اول claude امتحان کن، بعد openai
        response = None
        last_error = None
        for try_model in [model_id, "claude", "openai", "deepseek"]:
            try:
                slog.ai_call(try_model, "generating setup",
                    prompt_length=len(prompt)
                )
                response = await ai_manager.generate(
                    model_id=try_model,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                slog.success(f"AI model responded", model=try_model)
                break
            except Exception as e:
                last_error = str(e)
                slog.warning(f"AI model failed", model=try_model, error=str(e)[:100])
                continue

        if not response:
            error_msg = f"هیچ مدل AI در دسترس نیست. آخرین خطا: {last_error}"
            slog.error("No AI model available", last_error=str(last_error)[:100])
            return {"success": False, "error": error_msg}

        # پارس JSON از پاسخ
        content = response.content

        # استخراج JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            for part in parts:
                if "{" in part and "}" in part:
                    content = part
                    break

        # پاکسازی
        content = content.strip()
        if not content.startswith("{"):
            start = content.find("{")
            if start != -1:
                content = content[start:]
        if not content.endswith("}"):
            end = content.rfind("}")
            if end != -1:
                content = content[:end + 1]

        # 🔴 تلاش برای parse با اصلاح خطاهای رایج JSON
        result = None
        parse_error = None

        # تلاش اول: parse مستقیم
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            parse_error = e
            logger.warning(f"⚠️ First JSON parse attempt failed: {e}")

        # تلاش دوم: اصلاح trailing commas
        if result is None:
            try:
                import re
                # حذف کاماهای اضافی قبل از ] یا }
                fixed = re.sub(r',\s*([}\]])', r'\1', content)
                result = json.loads(fixed)
                logger.info("✅ JSON parsed after removing trailing commas")
            except json.JSONDecodeError:
                pass

        # تلاش سوم: اصلاح newlines در strings
        if result is None:
            try:
                # جایگزینی newlines واقعی با \\n در داخل strings
                fixed = content.replace('\n', '\\n').replace('\r', '\\r')
                # اما { و } و [ و ] نباید escape بشن
                fixed = fixed.replace('\\n{', '\n{').replace('\\n}', '\n}')
                fixed = fixed.replace('\\n[', '\n[').replace('\\n]', '\n]')
                fixed = fixed.replace('}\\n', '}\n').replace(']\\n', ']\n')
                result = json.loads(fixed)
                logger.info("✅ JSON parsed after fixing newlines")
            except json.JSONDecodeError:
                pass

        # تلاش چهارم: استخراج فقط memory_instructions با regex
        if result is None:
            try:
                import re
                # استخراج memory_instructions
                mem_match = re.search(r'"memory_instructions"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', content, re.DOTALL)
                memory_content = mem_match.group(1) if mem_match else ""

                # استخراج dynamic_fields با regex ساده
                fields = []
                field_pattern = r'"name"\s*:\s*"([^"]+)"[^}]*"value"\s*:\s*"([^"]*(?:\\"[^"]*)*)"'
                for match in re.finditer(field_pattern, content):
                    fields.append({
                        "name": match.group(1),
                        "value": match.group(2).replace('\\"', '"'),
                        "priority": 5,
                        "field_type": "temporary",
                        "action_type": "display"
                    })

                if memory_content or fields:
                    result = {
                        "memory_instructions": memory_content.replace('\\"', '"').replace('\\n', '\n'),
                        "dynamic_fields": fields if fields else [],
                        "fields_to_archive": [],
                        "fields_to_merge": [],
                        "fields_to_update": []
                    }
                    logger.info(f"✅ JSON partially extracted via regex: {len(fields)} fields")
            except Exception as regex_err:
                logger.warning(f"⚠️ Regex extraction failed: {regex_err}")

        # اگه هنوز result نیست، خطا بده
        if result is None:
            raise json.JSONDecodeError(str(parse_error), content, 0) if parse_error else ValueError("Could not parse AI response")

        # اعتبارسنجی و تکمیل فیلدها
        if "dynamic_fields" in result:
            for field in result["dynamic_fields"]:
                # مقادیر پیش‌فرض برای فیلدهای جدید
                if "action_type" not in field:
                    field["action_type"] = "display"
                if "archive_after_run" not in field:
                    field["archive_after_run"] = field.get("is_one_time", False)
                if field["action_type"] == "github_commit" and not field.get("target_path"):
                    # اگه مسیر نداره، به display تغییر بده
                    field["action_type"] = "display"

        return {
            "success": True,
            "data": result,
            "tokens_used": response.tokens_used,
            "model_used": response.model_id
        }

    except json.JSONDecodeError as e:
        slog.error("JSON parse error from AI response",
            exception=e,
            content_preview=content[:200] if content else "empty"
        )
        return {"success": False, "error": f"خطا در پارس پاسخ AI: {e}"}
    except Exception as e:
        slog.error("Error generating AI instructions", exception=e)
        return {"success": False, "error": str(e)}


# =====================================
# انتخاب هوشمند مدل
# =====================================

def select_best_model(task_type: str, domain: str) -> str:
    """انتخاب بهترین مدل برای نوع کار"""
    model_strengths = {
        "code_review": "claude",  # Claude برای تحلیل کد
        "documentation": "openai",  # GPT برای نوشتن مستندات
        "analysis": "deepseek",  # DeepSeek برای تحلیل منطقی
        "trading": "deepseek",  # DeepSeek برای ترید
        "security": "claude",  # Claude برای امنیت
        "testing": "claude",  # Claude برای تست
        "api_design": "openai",  # GPT برای طراحی API
        "optimization": "deepseek",  # DeepSeek برای بهینه‌سازی
    }

    domain_overrides = {
        "Trading/Finance": "deepseek",
        "AI/ML": "claude",
        "E-commerce": "openai",
    }

    # اول بر اساس دامنه
    if domain in domain_overrides:
        return domain_overrides[domain]

    # بعد بر اساس نوع کار
    return model_strengths.get(task_type, "claude")


# =====================================
# راه‌اندازی خودکار هوشمند
# =====================================

async def auto_setup_project_memory(
    project_id: str,
    project_name: str,
    project_description: str,
    project_type: str,
    files: List[Dict],
    use_ai: bool = True,
    db_session=None,
    full_context: Dict[str, Any] = None  # 🔴 context کامل پروژه
) -> Dict[str, Any]:
    """
    راه‌اندازی خودکار هوشمند حافظه و فیلدهای پویا
    با حفظ فیلدهای بایگانی شده و به‌روزرسانی هوشمند
    🔴 نسخه بهبودیافته: در نظر گرفتن ایرادات، گزارشات، و وضعیت فعلی
    """
    try:
        # 🔴 لاگ ساختاریافته - شروع عملیات
        slog.start("intelligent auto-setup",
            project_id=project_id,
            project_name=project_name,
            files_count=len(files) if files else 0,
            use_ai=use_ai
        )

        if full_context:
            slog.info("Context loaded",
                health_issues=len(full_context.get('health_issues', [])),
                unexecuted_fields=len(full_context.get('unexecuted_fields', [])),
                run_number=full_context.get('auto_setup_run_count', 1)
            )

        # 🆕 ایجاد ActivityLog برای این عملیات auto-setup
        parent_log_id = None
        if db_session:
            try:
                from ..api.routes.project_journal import ActivityLog
                parent_log = ActivityLog(
                    id=f"log_{uuid.uuid4().hex[:12]}",
                    project_id=project_id,
                    model_id="system",
                    activity_type="auto_setup",
                    prompt=f"راه‌اندازی خودکار پروژه {project_name}",
                    tokens_used=0,
                    latency_ms=0,
                    success=True,
                    field_name="auto_setup",
                    created_at=datetime.utcnow()
                )
                db_session.add(parent_log)
                db_session.flush()  # برای دریافت id
                parent_log_id = parent_log.id

                # 🆕 ثبت شروع عملیات
                log_auto_setup_operation(
                    db_session=db_session,
                    project_id=project_id,
                    parent_log_id=parent_log_id,
                    operation_type="auto_setup_start",
                    summary=f"شروع راه‌اندازی خودکار پروژه {project_name}",
                    details={
                        "files_count": len(files) if files else 0,
                        "has_context": bool(full_context),
                        "run_count": full_context.get("auto_setup_run_count", 1) if full_context else 1
                    },
                    target_type="project",
                    target_id=project_id,
                    target_name=project_name
                )
            except Exception as e:
                logger.warning(f"Could not create parent log: {e}")

        # دریافت فیلدهای فعلی برای حفظ فیلدهای بایگانی شده
        existing_fields = []
        archived_fields = []
        if db_session:
            from ..models.project import Project
            project = db_session.query(Project).filter(Project.id == project_id).first()
            if project and project.dynamic_fields:
                try:
                    existing_fields = json.loads(project.dynamic_fields)
                    # جدا کردن فیلدهای بایگانی شده
                    archived_fields = [f for f in existing_fields if f.get("archived")]
                    existing_fields = [f for f in existing_fields if not f.get("archived")]
                except:
                    pass

        # مرحله ۱: تحلیل عمیق پروژه
        slog.step(1, "Analyzing project structure",
            existing_fields=len(existing_fields),
            archived_fields=len(archived_fields)
        )
        insights = extract_project_insights(files)
        slog.data("Project insights",
            {"domain": insights.get('domain'), "architecture": insights.get('architecture'),
             "language": insights.get('language'), "frameworks": insights.get('frameworks', [])}
        )

        # انتخاب فایل‌های مهم برای نمایش به AI
        important_files = []
        for f in files:
            path = f.get("path", f.get("file_path", "")).lower()
            # فایل‌های مهم
            if any(imp in path for imp in [
                "main.", "app.", "index.", "server.",
                "package.json", "requirements.txt",
                "readme", "config", "settings",
                "model", "schema", "route", "controller", "service"
            ]):
                important_files.append(f)

        # اگه فایل مهم کم بود، از همه استفاده کن
        if len(important_files) < 3:
            important_files = files[:15]
        else:
            important_files = important_files[:12]

        # مرحله ۲: تولید دستورات با AI
        slog.step(2, "Generating setup with AI",
            use_ai=use_ai,
            important_files_count=len(important_files)
        )
        ai_result = None
        if use_ai and important_files:
            best_model = select_best_model("analysis", insights.get("domain", ""))
            slog.ai_call(best_model, "generating intelligent setup",
                files_to_analyze=len(important_files)
            )
            ai_result = await generate_intelligent_setup(
                project_name=project_name,
                project_description=project_description,
                insights=insights,
                sample_files=important_files,
                existing_fields=existing_fields,  # ارسال فیلدهای موجود
                model_id=best_model,
                full_context=full_context  # 🔴 ارسال context کامل
            )

        # 🔴 تابع تشخیص فیلدهای محافظت شده (ایجاد شده توسط گزارش مهندسی)
        # این تابع باید قبل از if/else باشد تا در هر دو مسیر قابل دسترسی باشد
        def is_report_field(field: Dict) -> bool:
            """بررسی آیا فیلد توسط گزارش مهندسی ایجاد شده"""
            # 🆕 بررسی engineering_approval (مهم‌ترین شاخص)
            if field.get("engineering_approval", {}).get("approved"):
                return True
            if field.get("created_from_report"):
                return True
            if field.get("validation_marker") in ["validated", "pending"]:
                return True
            if field.get("validator_model"):
                return True
            if field.get("original_issue"):
                return True
            if field.get("name", "").startswith("✅"):
                return True
            # 🆕 بررسی approval_type
            approval_type = field.get("engineering_approval", {}).get("approval_type", "")
            if approval_type in ["step1_validation", "step2_validation", "health_validation_step2", "merged_health_step2"]:
                return True
            return False

        # مرحله ۳: ساخت نتیجه نهایی
        slog.step(3, "Building final result")

        if ai_result and ai_result.get("success"):
            slog.success("AI generated setup successfully",
                model=ai_result.get('model_used'),
                tokens_used=ai_result.get('tokens_used', 0)
            )
            data = ai_result["data"]
            slog.data("AI suggestions", {
                "new_fields": len(data.get('dynamic_fields', [])),
                "to_archive": len(data.get('fields_to_archive', [])),
                "to_update": len(data.get('fields_to_update', [])),
                "to_merge": len(data.get('fields_to_merge', []))
            })

            # 🔴 محاسبه تعداد دفعات اجرا
            run_count = 1
            if full_context:
                run_count = full_context.get("auto_setup_run_count", 1)

            memory_instructions = {
                "content": data.get("memory_instructions", ""),
                "target_models": ["all"],
                "auto_generated": True,
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": ai_result.get("model_used"),
                "auto_setup_run_count": run_count  # 🔴 ذخیره تعداد دفعات اجرا
            }

            # 🆕 پردازش فیلدهای موجود براساس دستورات AI
            updated_existing_fields = list(existing_fields)  # کپی از فیلدهای موجود
            fields_archived_count = 0
            fields_merged_count = 0
            fields_updated_count = 0
            fields_protected_count = 0  # 🔴 تعداد فیلدهای محافظت شده

            # 1. بایگانی فیلدهای مشخص شده (با محافظت از فیلدهای گزارش)
            fields_to_archive = data.get("fields_to_archive", [])
            for field_id in fields_to_archive:
                for field in updated_existing_fields:
                    if field.get("id") == field_id and not field.get("archived"):
                        # 🔴 بررسی محافظت - فیلدهای گزارش اجرا نشده بایگانی نشوند
                        if is_report_field(field) and not field.get("executed", False):
                            fields_protected_count += 1
                            logger.warning(f"🛡️ PROTECTED: Cannot archive report field (not executed): {field.get('name')}")
                            # 🆕 ثبت عملیات محافظت
                            log_auto_setup_operation(
                                db_session=db_session,
                                project_id=project_id,
                                parent_log_id=parent_log_id,
                                operation_type="field_protected",
                                summary=f"محافظت از فیلد گزارش: {field.get('name')}",
                                details={"reason": "فیلد توسط گزارش مهندسی ایجاد شده و هنوز اجرا نشده"},
                                target_type="field",
                                target_id=field_id,
                                target_name=field.get("name"),
                                status="skipped"
                            )
                            continue
                        # ذخیره مقدار قبلی برای ردیابی
                        before_value = json.dumps(field, ensure_ascii=False)
                        field["archived"] = True
                        field["archived_at"] = datetime.utcnow().isoformat()
                        field["archived_reason"] = "auto-setup review"
                        fields_archived_count += 1
                        logger.info(f"Auto-archived field: {field.get('name')}")
                        # 🆕 ثبت عملیات بایگانی
                        log_auto_setup_operation(
                            db_session=db_session,
                            project_id=project_id,
                            parent_log_id=parent_log_id,
                            operation_type="field_archive",
                            summary=f"بایگانی فیلد: {field.get('name')}",
                            details={"reason": "auto-setup review", "archived_at": field["archived_at"]},
                            before_value=before_value,
                            after_value=json.dumps(field, ensure_ascii=False),
                            target_type="field",
                            target_id=field_id,
                            target_name=field.get("name")
                        )

            # 2. ادغام فیلدهای مشخص شده (با محافظت از فیلدهای گزارش)
            fields_to_merge = data.get("fields_to_merge", [])
            for merge_info in fields_to_merge:
                source_ids = merge_info.get("source_ids", [])
                if len(source_ids) >= 2:
                    # 🔴 بررسی آیا هر یک از فیلدها محافظت شده است
                    has_protected = False
                    for sid in source_ids:
                        for field in updated_existing_fields:
                            if field.get("id") == sid:
                                if is_report_field(field) and not field.get("executed", False):
                                    has_protected = True
                                    logger.warning(f"🛡️ PROTECTED: Cannot merge report field (not executed): {field.get('name')}")
                                    break
                        if has_protected:
                            break

                    if has_protected:
                        fields_protected_count += 1
                        continue  # رد شدن از این ادغام

                    # پیدا کردن فیلدهای منبع و جمع‌آوری پیوست‌ها
                    merged_attachments = []
                    for sid in source_ids:
                        for field in updated_existing_fields:
                            if field.get("id") == sid:
                                # جمع‌آوری پیوست‌ها قبل از بایگانی
                                merged_attachments.extend(field.get("attachments", []))
                                # بایگانی فیلد منبع
                                field["archived"] = True
                                field["archived_at"] = datetime.utcnow().isoformat()
                                field["archived_reason"] = f"merged into new field"
                                fields_archived_count += 1

                    # ایجاد فیلد ادغام‌شده
                    merged_field = {
                        "id": f"field_{uuid.uuid4().hex[:8]}",
                        "name": merge_info.get("merged_name", "فیلد ادغام‌شده"),
                        "value": merge_info.get("merged_value", ""),
                        "target_models": ["claude"],
                        "trigger": {"enabled": False, "interval_minutes": 60, "interval_type": "minutes"},
                        "action_type": "display",
                        "field_type": "permanent",
                        "priority": 5,
                        "attachments": merged_attachments,  # حفظ پیوست‌ها
                        "created_at": datetime.utcnow().isoformat(),
                        "auto_generated": True,
                        "merged_from": source_ids,
                    }
                    updated_existing_fields.append(merged_field)
                    fields_merged_count += 1
                    logger.info(f"Merged fields {source_ids} into: {merged_field['name']}")
                    # 🆕 ثبت عملیات ادغام
                    log_auto_setup_operation(
                        db_session=db_session,
                        project_id=project_id,
                        parent_log_id=parent_log_id,
                        operation_type="field_merge",
                        summary=f"ادغام {len(source_ids)} فیلد به: {merged_field['name']}",
                        details={
                            "source_ids": source_ids,
                            "merged_field_id": merged_field["id"],
                            "merged_name": merged_field["name"],
                            "attachments_count": len(merged_attachments)
                        },
                        after_value=json.dumps(merged_field, ensure_ascii=False),
                        target_type="field",
                        target_id=merged_field["id"],
                        target_name=merged_field["name"]
                    )

            # 3. به‌روزرسانی فیلدهای مشخص شده
            fields_to_update = data.get("fields_to_update", [])
            for update_info in fields_to_update:
                field_id = update_info.get("id")
                for field in updated_existing_fields:
                    if field.get("id") == field_id and not field.get("archived"):
                        before_value = json.dumps(field, ensure_ascii=False)
                        if update_info.get("new_value"):
                            field["value"] = update_info["new_value"]
                        if update_info.get("new_priority"):
                            field["priority"] = update_info["new_priority"]
                        if update_info.get("new_field_type"):
                            field["field_type"] = update_info["new_field_type"]
                        field["updated_at"] = datetime.utcnow().isoformat()
                        field["update_reason"] = update_info.get("reason", "auto-setup review")
                        fields_updated_count += 1
                        logger.info(f"Updated field: {field.get('name')}")
                        # 🆕 ثبت عملیات به‌روزرسانی
                        log_auto_setup_operation(
                            db_session=db_session,
                            project_id=project_id,
                            parent_log_id=parent_log_id,
                            operation_type="field_update",
                            summary=f"به‌روزرسانی فیلد: {field.get('name')}",
                            details={
                                "reason": update_info.get("reason", "auto-setup review"),
                                "changed_fields": list(update_info.keys())
                            },
                            before_value=before_value,
                            after_value=json.dumps(field, ensure_ascii=False),
                            target_type="field",
                            target_id=field_id,
                            target_name=field.get("name")
                        )

            # 4. فیلدهای کاملاً جدید از AI
            new_dynamic_fields = []
            for ai_field in data.get("dynamic_fields", []):
                recommended_model = ai_field.get("recommended_model", "claude")
                action_type = ai_field.get("action_type", "display")
                target_path = ai_field.get("target_path")
                field_type = ai_field.get("field_type", "temporary")
                priority = ai_field.get("priority", 5)

                # تعیین خودکار field_type براساس archive_after_run
                if ai_field.get("archive_after_run") or ai_field.get("is_one_time"):
                    field_type = "temporary"
                elif ai_field.get("needs_trigger"):
                    field_type = "permanent"

                field = {
                    "id": f"field_{uuid.uuid4().hex[:8]}",
                    "name": ai_field.get("name", "فیلد"),
                    "value": ai_field.get("value", ""),
                    "target_models": [recommended_model] if recommended_model != "all" else ["all"],
                    "trigger": {
                        "enabled": ai_field.get("needs_trigger", False),
                        "interval_minutes": ai_field.get("trigger_hours", 24) * 60 if ai_field.get("trigger_hours") else 1440,
                        "interval_type": "minutes"
                    },
                    "action_type": action_type,
                    "target_path": target_path if action_type == "github_commit" else None,
                    "archive_after_run": ai_field.get("archive_after_run", False),
                    "deploy_after_commit": ai_field.get("deploy_after_commit", False),
                    "field_type": field_type,
                    "priority": priority,
                    "attachments": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "auto_generated": True,
                    "ai_generated": True,
                    "reason": ai_field.get("why", ""),
                    "is_one_time": ai_field.get("is_one_time", ai_field.get("archive_after_run", False))
                }
                new_dynamic_fields.append(field)
                # 🆕 ثبت عملیات ایجاد فیلد جدید
                log_auto_setup_operation(
                    db_session=db_session,
                    project_id=project_id,
                    parent_log_id=parent_log_id,
                    operation_type="field_create",
                    summary=f"ایجاد فیلد جدید: {field['name']}",
                    details={
                        "action_type": action_type,
                        "field_type": field_type,
                        "priority": priority,
                        "reason": ai_field.get("why", ""),
                        "has_trigger": ai_field.get("needs_trigger", False)
                    },
                    after_value=json.dumps(field, ensure_ascii=False),
                    target_type="field",
                    target_id=field["id"],
                    target_name=field["name"]
                )

            # ترکیب همه فیلدها و مرتب‌سازی براساس اولویت
            all_fields = updated_existing_fields + new_dynamic_fields
            # فیلدهای غیربایگانی رو مرتب کن
            active_fields = [f for f in all_fields if not f.get("archived")]
            archived_fields_final = [f for f in all_fields if f.get("archived")]
            active_fields.sort(key=lambda x: int(x.get("priority", 5)) if str(x.get("priority", 5)).isdigit() else 5)
            all_fields = active_fields + archived_fields_final

            result = {
                "success": True,
                "project_id": project_id,
                "detected_type": insights.get("domain", project_type),
                "language": insights.get("language"),
                "architecture": insights.get("architecture"),
                "frameworks": insights.get("frameworks", []),
                "memory_instructions": memory_instructions,
                "dynamic_fields": all_fields,
                "new_fields_count": len(new_dynamic_fields),
                "fields_archived": fields_archived_count,
                "fields_merged": fields_merged_count,
                "fields_updated": fields_updated_count,
                "fields_protected": fields_protected_count,  # 🔴 فیلدهای محافظت شده (از گزارش مهندسی)
                "missing_files": data.get("missing_files", []),
                "ai_insights": data.get("project_summary"),
                "recommendations": data.get("key_recommendations", []),
                "tokens_used": ai_result.get("tokens_used", 0),
                "model_used": ai_result.get("model_used")
            }

        else:
            # Fallback به حالت ساده
            ai_error_msg = ai_result.get("error", "پاسخ نامعتبر") if ai_result else "AI call failed"
            slog.warning(f"AI failed, using fallback setup",
                error=ai_error_msg[:100] if ai_error_msg else "unknown"
            )
            result = _create_fallback_setup(project_id, project_name, insights)

            # 🆕 ثبت خطای AI در ژورنال
            if db_session and parent_log_id:
                log_auto_setup_operation(
                    db_session=db_session,
                    project_id=project_id,
                    parent_log_id=parent_log_id,
                    operation_type="ai_fallback",
                    summary=f"⚠️ استفاده از حالت پیش‌فرض (AI ناموفق)",
                    details={"ai_error": ai_error_msg, "fallback_reason": "AI response was invalid or failed"},
                    status="warning"
                )

            # 🔴 اصلاح: حفظ تمام فیلدهای فعال موجود (نه فقط report fields)
            # فیلدهای موجود غیربایگانی رو حفظ کن
            active_existing = [f for f in existing_fields if not f.get("archived")]
            if active_existing:
                slog.info(f"Preserving existing active fields in fallback",
                    count=len(active_existing),
                    sample_names=[f.get('name') for f in active_existing[:3]]
                )

            # فیلدهای fallback رو فقط اگه قبلاً وجود نداشته باشن اضافه کن
            existing_names = [f.get("name", "").lower() for f in active_existing]
            fallback_fields = result.get("dynamic_fields", [])
            new_fallback_fields = []
            for ff in fallback_fields:
                ff_name = ff.get("name", "").lower()
                if ff_name not in existing_names:
                    new_fallback_fields.append(ff)
                else:
                    slog.debug(f"Skipping duplicate fallback field", field_name=ff.get('name'))

            # ترکیب: فیلدهای موجود + فیلدهای جدید fallback + بایگانی شده‌ها
            result["dynamic_fields"] = active_existing + new_fallback_fields + archived_fields
            result["fields_protected"] = len(active_existing)
            result["new_fields_count"] = len(new_fallback_fields)

        # 🆕 ثبت خلاصه پایانی عملیات
        if db_session and parent_log_id:
            log_auto_setup_operation(
                db_session=db_session,
                project_id=project_id,
                parent_log_id=parent_log_id,
                operation_type="auto_setup_complete",
                summary=f"پایان راه‌اندازی خودکار: {result.get('new_fields_count', 0)} فیلد جدید، {result.get('fields_archived', 0)} بایگانی، {result.get('fields_merged', 0)} ادغام، {result.get('fields_updated', 0)} به‌روزرسانی",
                details={
                    "new_fields_count": result.get("new_fields_count", 0),
                    "fields_archived": result.get("fields_archived", 0),
                    "fields_merged": result.get("fields_merged", 0),
                    "fields_updated": result.get("fields_updated", 0),
                    "fields_protected": result.get("fields_protected", 0),
                    "model_used": result.get("model_used"),
                    "tokens_used": result.get("tokens_used", 0)
                },
                target_type="project",
                target_id=project_id,
                target_name=project_name
            )

        # مرحله ۴: ذخیره در دیتابیس
        slog.step(4, "Saving to database")
        if db_session and result.get("success"):
            try:
                from ..models.project import Project

                project = db_session.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.memory_instructions = json.dumps(result["memory_instructions"], ensure_ascii=False)
                    project.dynamic_fields = json.dumps(result["dynamic_fields"], ensure_ascii=False)
                    db_session.commit()
                    slog.db_operation("save", "projects",
                        project_id=project_id,
                        fields_count=len(result.get("dynamic_fields", []))
                    )
            except Exception as e:
                slog.error("Failed to save auto-setup to database", exception=e)
                db_session.rollback()

        # 🔴 لاگ پایان عملیات
        slog.end("intelligent auto-setup",
            new_fields=result.get("new_fields_count", 0),
            archived=result.get("fields_archived", 0),
            merged=result.get("fields_merged", 0),
            updated=result.get("fields_updated", 0),
            protected=result.get("fields_protected", 0),
            model=result.get("model_used", "fallback"),
            tokens=result.get("tokens_used", 0)
        )
        return result

    except Exception as e:
        slog.error("Auto-setup failed with exception", exception=e)
        return {"success": False, "error": str(e)}


def _create_fallback_setup(project_id: str, project_name: str, insights: Dict) -> Dict:
    """ایجاد setup پیش‌فرض در صورت خطای AI"""
    domain = insights.get("domain", "General")
    lang = insights.get("language", "Unknown")
    frameworks = insights.get("frameworks", [])

    memory = f"""## دستورات پروژه {project_name}
- زبان: {lang}
- فریم‌ورک: {', '.join(frameworks) if frameworks else 'نامشخص'}
- کدها باید تمیز و خوانا باشند
- از best practices زبان {lang} پیروی کن
- تست‌پذیری کد مهم است
- مستندسازی توابع الزامی است"""

    return {
        "success": True,
        "project_id": project_id,
        "detected_type": domain,
        "language": lang,
        "architecture": insights.get("architecture"),
        "frameworks": frameworks,
        "memory_instructions": {
            "content": memory,
            "target_models": ["all"],
            "auto_generated": True,
            "fallback": True,
            "generated_at": datetime.utcnow().isoformat()
        },
        "dynamic_fields": [
            {
                "id": f"field_{uuid.uuid4().hex[:8]}",
                "name": "بررسی و بهبود کد",
                "value": f"کد {lang} را بررسی کن. مشکلات احتمالی، پیشنهادات بهبود و نکات امنیتی را گزارش بده.",
                "target_models": ["claude"],
                "trigger": {"enabled": False},
                "action_type": "display",
                "archive_after_run": False,
                "auto_generated": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": f"field_{uuid.uuid4().hex[:8]}",
                "name": "تولید تست",
                "value": f"برای کدهای اصلی پروژه، unit test بنویس با coverage بالا. از فریم‌ورک تست استاندارد {lang} استفاده کن.",
                "target_models": ["claude"],
                "trigger": {"enabled": False},
                "action_type": "github_multi_commit",
                "archive_after_run": True,
                "auto_generated": True,
                "is_one_time": True,
                "created_at": datetime.utcnow().isoformat()
            }
        ],
        "ai_insights": None,
        "recommendations": [
            "مستندسازی کد را تکمیل کنید",
            "تست‌های واحد بنویسید",
            "بررسی امنیتی انجام دهید"
        ],
        "new_fields_count": 2,
        "archived_fields_preserved": 0
    }


# =====================================
# اعمال روی پروژه‌های موجود
# =====================================

async def apply_auto_setup_to_existing_project(project_id: str, db_session) -> Dict[str, Any]:
    """
    اعمال راه‌اندازی خودکار روی یک پروژه موجود
    """
    try:
        from ..models.project import Project, ProjectFile

        project = db_session.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # دریافت فایل‌ها با محتوا
        files = db_session.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        files_data = [
            {
                "path": f.file_path,
                "content": f.content[:2000] if f.content else "",
                "file_type": f.file_type
            }
            for f in files
        ]

        # اجرای auto-setup
        result = await auto_setup_project_memory(
            project_id=project_id,
            project_name=project.name,
            project_description=project.description or "",
            project_type=project.project_type or "",
            files=files_data,
            use_ai=True,
            db_session=db_session
        )

        return result

    except Exception as e:
        logger.error(f"Error applying auto-setup: {e}")
        return {"success": False, "error": str(e)}


# =====================================
# راه‌اندازی خودکار پیشرفته (Advanced Auto Setup)
# =====================================

async def advanced_auto_setup(
    project_id: str,
    db_session,
    include_roadmap: bool = True,
    include_readme: bool = True,
    include_analysis: bool = True,
    model_id: str = None
) -> Dict[str, Any]:
    """
    راه‌اندازی خودکار پیشرفته با قابلیت‌های:

    1. بررسی کامل ساختار پروژه (ریز تا درشت)
    2. تطبیق با فایل نقشه‌راه موجود (Roadmap)
    3. ارتقاء و تکمیل نقشه‌راه در صورت تطابق
    4. ایجاد نقشه‌راه/README در صورت عدم وجود
    5. تحلیل وضعیت فعلی برنامه
    6. شناسایی ایرادات و باگ‌ها
    7. ارائه حالت ایده‌آل برنامه
    8. ایجاد/به‌روزرسانی/ادغام فیلدها

    خروجی‌های مورد انتظار:
    - تایید یا عدم تایید انطباق
    - مستندسازی "برنامه اینطوره"
    - مستندسازی "ایراداش اینه"
    - مستندسازی "حالت ایده‌آل باید این باشه"
    - فیلدهای پویا به‌روزرسانی شده یا ایجاد شده یا ادغام شده
    """
    from ..models.project import Project, ProjectFile
    from .ai_manager import get_ai_manager

    logger.info(f"Starting advanced auto-setup for project {project_id}")

    result = {
        "success": False,
        "project_id": project_id,
        "analysis": {
            "current_state": "",
            "issues_found": [],
            "ideal_state": "",
            "roadmap_compliance": None,
            "structure_analysis": {}
        },
        "roadmap": {
            "exists": False,
            "created": False,
            "updated": False,
            "content": ""
        },
        "readme": {
            "exists": False,
            "created": False,
            "updated": False,
            "content": ""
        },
        "fields": {
            "created": [],
            "updated": [],
            "merged": [],
            "archived": []
        },
        "model_used": None
    }

    try:
        # دریافت پروژه
        project = db_session.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # دریافت فایل‌های پروژه
        files = db_session.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        files_data = [
            {
                "path": f.file_path,
                "content": f.content or "",
                "file_type": f.file_type
            }
            for f in files
        ]

        if not files_data:
            return {"success": False, "error": "پروژه فایلی ندارد"}

        # AI Manager
        ai_manager = get_ai_manager()
        if not model_id:
            available = ai_manager.get_available_models()
            model_id = available[0].id if available else "claude"

        # =====================================
        # مرحله 1: تحلیل عمیق ساختار
        # =====================================
        logger.info(f"[{project_id}] مرحله 1: تحلیل عمیق ساختار")

        insights = extract_project_insights(files_data)

        # بررسی وجود Roadmap و README
        roadmap_file = None
        readme_file = None
        for f in files_data:
            path_lower = f.get("path", "").lower()
            if "roadmap" in path_lower and path_lower.endswith(".md"):
                roadmap_file = f
            if "readme" in path_lower and path_lower.endswith(".md"):
                readme_file = f

        result["roadmap"]["exists"] = bool(roadmap_file) or bool(project.roadmap_content)
        result["readme"]["exists"] = bool(readme_file) or bool(project.readme_content)

        # =====================================
        # مرحله 2: تحلیل وضعیت فعلی با AI
        # =====================================
        logger.info(f"[{project_id}] مرحله 2: تحلیل وضعیت فعلی")

        analysis_prompt = _build_analysis_prompt(
            project_name=project.name,
            project_description=project.description or "",
            insights=insights,
            files=files_data[:20],  # حداکثر 20 فایل
            existing_roadmap=roadmap_file.get("content") if roadmap_file else (project.roadmap_content or ""),
            existing_readme=readme_file.get("content") if readme_file else (project.readme_content or "")
        )

        try:
            from .ai_manager import Message
            messages = [
                Message(role="system", content="تو یک معمار نرم‌افزار متخصص هستی. پاسخ را فقط JSON معتبر بده."),
                Message(role="user", content=analysis_prompt)
            ]

            response = await ai_manager.generate(
                model_id=model_id,
                messages=messages,
                max_tokens=4000,
                temperature=0.3
            )

            result["model_used"] = model_id

            # پارس پاسخ
            analysis_data = _parse_json_response(response.content)

            if analysis_data:
                result["analysis"]["current_state"] = analysis_data.get("current_state", "")
                result["analysis"]["issues_found"] = analysis_data.get("issues_found", [])
                result["analysis"]["ideal_state"] = analysis_data.get("ideal_state", "")
                result["analysis"]["roadmap_compliance"] = analysis_data.get("roadmap_compliance", {})
                result["analysis"]["structure_analysis"] = analysis_data.get("structure_analysis", {})

                # ذخیره در پروژه
                project.ideal_state = analysis_data.get("ideal_state", "")
                project.issues_found = json.dumps(
                    analysis_data.get("issues_found", []),
                    ensure_ascii=False
                )

        except Exception as e:
            logger.error(f"Error in analysis phase: {e}")

        # =====================================
        # مرحله 3: بررسی/ایجاد/ارتقای Roadmap
        # =====================================
        if include_roadmap:
            logger.info(f"[{project_id}] مرحله 3: مدیریت Roadmap")

            roadmap_result = await _manage_roadmap(
                project=project,
                files_data=files_data,
                insights=insights,
                analysis=result["analysis"],
                existing_roadmap=roadmap_file,
                ai_manager=ai_manager,
                model_id=model_id
            )

            result["roadmap"].update(roadmap_result)
            if roadmap_result.get("content"):
                project.roadmap_content = roadmap_result["content"]

        # =====================================
        # مرحله 4: بررسی/ایجاد/ارتقای README
        # =====================================
        if include_readme:
            logger.info(f"[{project_id}] مرحله 4: مدیریت README")

            readme_result = await _manage_readme(
                project=project,
                files_data=files_data,
                insights=insights,
                roadmap_content=result["roadmap"].get("content", ""),
                existing_readme=readme_file,
                ai_manager=ai_manager,
                model_id=model_id
            )

            result["readme"].update(readme_result)
            if readme_result.get("content"):
                project.readme_content = readme_result["content"]

        # =====================================
        # مرحله 5: ایجاد/به‌روزرسانی فیلدهای پویا
        # =====================================
        logger.info(f"[{project_id}] مرحله 5: مدیریت فیلدهای پویا")

        fields_result = await _manage_dynamic_fields(
            project=project,
            files_data=files_data,
            insights=insights,
            analysis=result["analysis"],
            ai_manager=ai_manager,
            model_id=model_id
        )

        result["fields"] = fields_result

        # ذخیره تغییرات
        db_session.commit()

        result["success"] = True
        logger.info(f"[{project_id}] راه‌اندازی خودکار پیشرفته کامل شد")

    except Exception as e:
        logger.error(f"Error in advanced auto-setup: {e}", exc_info=True)
        result["error"] = str(e)
        db_session.rollback()

    return result


def _build_analysis_prompt(
    project_name: str,
    project_description: str,
    insights: Dict,
    files: List[Dict],
    existing_roadmap: str,
    existing_readme: str
) -> str:
    """ساخت پرامپت تحلیل جامع"""

    files_summary = []
    for f in files[:20]:
        path = f.get("path", "")
        content = f.get("content", "")[:1000]
        files_summary.append(f"### {path}\n```\n{content}\n```\n")

    prompt = f"""# تحلیل جامع پروژه

## اطلاعات پروژه:
- نام: {project_name}
- توضیحات: {project_description}
- زبان اصلی: {insights.get('language', '?')}
- فریم‌ورک‌ها: {', '.join(insights.get('frameworks', []))}
- معماری: {insights.get('architecture', '?')}

## فایل‌های پروژه:
{chr(10).join(files_summary)}

{f'''## نقشه‌راه موجود:
{existing_roadmap[:2000]}
''' if existing_roadmap else '## نقشه‌راه: ندارد'}

{f'''## README موجود:
{existing_readme[:1500]}
''' if existing_readme else '## README: ندارد'}

## وظیفه تو:
1. **وضعیت فعلی برنامه را توصیف کن** - چه کارهایی انجام می‌دهد؟ چه قابلیت‌هایی دارد؟
2. **ایرادات و مشکلات را شناسایی کن** - باگ‌ها، کمبودها، مشکلات معماری
3. **حالت ایده‌آل را شرح بده** - برنامه باید چطور باشد؟
4. **تطابق با نقشه‌راه را بررسی کن** (اگر وجود دارد)
5. **ساختار را تحلیل کن** - فایل‌های اضافی/کم، سیم‌کشی نادرست

## فرمت خروجی (JSON):
```json
{{
    "current_state": "توضیح کامل وضعیت فعلی برنامه (2-3 پاراگراف)",
    "issues_found": [
        {{
            "type": "bug|missing|architecture|security|performance",
            "severity": "critical|high|medium|low",
            "title": "عنوان مشکل",
            "description": "توضیح کامل",
            "file": "مسیر فایل (اگر مرتبط)",
            "suggestion": "پیشنهاد رفع"
        }}
    ],
    "ideal_state": "توضیح کامل حالت ایده‌آل برنامه (2-3 پاراگراف)",
    "roadmap_compliance": {{
        "compliant": true/false,
        "score": 0-100,
        "completed_items": ["موارد تکمیل شده"],
        "pending_items": ["موارد باقیمانده"],
        "missing_items": ["مواردی که در roadmap نیست ولی باید باشد"]
    }},
    "structure_analysis": {{
        "score": 0-100,
        "strengths": ["نقاط قوت ساختار"],
        "weaknesses": ["نقاط ضعف ساختار"],
        "missing_files": ["فایل‌های پیشنهادی که باید ایجاد شوند"],
        "unnecessary_files": ["فایل‌های اضافی"]
    }}
}}
```

مهم: فقط JSON برگردان!
"""
    return prompt


async def _manage_roadmap(
    project,
    files_data: List[Dict],
    insights: Dict,
    analysis: Dict,
    existing_roadmap: Optional[Dict],
    ai_manager,
    model_id: str
) -> Dict:
    """مدیریت Roadmap - ایجاد یا ارتقا"""
    result = {"created": False, "updated": False, "content": ""}

    roadmap_content = existing_roadmap.get("content") if existing_roadmap else (project.roadmap_content or "")

    prompt = f"""# مدیریت نقشه‌راه پروژه

## پروژه: {project.name}

## وضعیت فعلی:
{analysis.get('current_state', '')}

## ایرادات شناسایی شده:
{json.dumps(analysis.get('issues_found', []), ensure_ascii=False, indent=2)}

## حالت ایده‌آل:
{analysis.get('ideal_state', '')}

{f'''## نقشه‌راه موجود:
{roadmap_content[:3000]}
''' if roadmap_content else '## نقشه‌راه موجود: ندارد'}

## وظیفه:
{'ارتقا و تکمیل نقشه‌راه موجود' if roadmap_content else 'ایجاد نقشه‌راه جدید'}

یک نقشه‌راه کامل و حرفه‌ای به زبان فارسی بنویس که شامل:
1. اهداف کوتاه‌مدت و بلندمدت
2. فازهای توسعه با جزئیات
3. باگ‌ها و مشکلاتی که باید رفع شوند
4. قابلیت‌های جدید پیشنهادی
5. زمان‌بندی تقریبی

فقط محتوای Markdown نقشه‌راه را برگردان (بدون توضیح اضافی).
"""

    try:
        from .ai_manager import Message
        messages = [
            Message(role="system", content="تو یک مدیر پروژه متخصص هستی. نقشه‌راه حرفه‌ای بنویس."),
            Message(role="user", content=prompt)
        ]

        response = await ai_manager.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=3000,
            temperature=0.5
        )

        content = response.content.strip()

        # حذف markdown code block اگر وجود دارد
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("markdown"):
                content = content[8:]
            content = content.strip()

        result["content"] = content
        result["created"] = not bool(roadmap_content)
        result["updated"] = bool(roadmap_content)

    except Exception as e:
        logger.error(f"Error managing roadmap: {e}")

    return result


async def _manage_readme(
    project,
    files_data: List[Dict],
    insights: Dict,
    roadmap_content: str,
    existing_readme: Optional[Dict],
    ai_manager,
    model_id: str
) -> Dict:
    """مدیریت README - ایجاد یا ارتقا"""
    result = {"created": False, "updated": False, "content": ""}

    readme_content = existing_readme.get("content") if existing_readme else (project.readme_content or "")

    prompt = f"""# مدیریت README پروژه

## پروژه: {project.name}
## توضیحات: {project.description or ''}

## اطلاعات فنی:
- زبان: {insights.get('language', '?')}
- فریم‌ورک‌ها: {', '.join(insights.get('frameworks', []))}
- معماری: {insights.get('architecture', '?')}
- وابستگی‌ها: {', '.join(insights.get('dependencies', [])[:10])}

{f'''## README موجود:
{readme_content[:2000]}
''' if readme_content else '## README موجود: ندارد'}

{f'''## نقشه‌راه:
{roadmap_content[:1500]}
''' if roadmap_content else ''}

## وظیفه:
{'ارتقا و تکمیل README موجود' if readme_content else 'ایجاد README جدید'}

یک README کامل و حرفه‌ای به زبان فارسی بنویس که شامل:
1. معرفی پروژه
2. ویژگی‌ها و قابلیت‌ها
3. نیازمندی‌ها و نحوه نصب
4. نحوه استفاده
5. ساختار پروژه
6. مشارکت در توسعه

فقط محتوای Markdown README را برگردان.
"""

    try:
        from .ai_manager import Message
        messages = [
            Message(role="system", content="تو یک توسعه‌دهنده متخصص هستی. README حرفه‌ای بنویس."),
            Message(role="user", content=prompt)
        ]

        response = await ai_manager.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=2500,
            temperature=0.5
        )

        content = response.content.strip()

        # حذف markdown code block
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("markdown"):
                content = content[8:]
            content = content.strip()

        result["content"] = content
        result["created"] = not bool(readme_content)
        result["updated"] = bool(readme_content)

    except Exception as e:
        logger.error(f"Error managing readme: {e}")

    return result


async def _manage_dynamic_fields(
    project,
    files_data: List[Dict],
    insights: Dict,
    analysis: Dict,
    ai_manager,
    model_id: str
) -> Dict:
    """
    مدیریت هوشمند فیلدهای پویا بر اساس تحلیل

    🆕 قابلیت‌های جدید:
    - حفظ فیلدهای اجرا نشده که هنوز مشکلشان وجود دارد
    - ادغام هوشمند فیلدهای مشابه
    - بایگانی فقط فیلدهایی که مشکلشان رفع شده
    - مارکرگذاری فیلدهای معتبر
    - 🔴 حفظ فیلدهای ایجاد شده توسط گزارش مهندسی (created_from_report)
    """
    result = {
        "created": [],
        "updated": [],
        "merged": [],
        "archived": [],
        "preserved": [],  # 🆕 فیلدهای حفظ شده
        "protected": [],  # 🆕 فیلدهای محافظت شده (از گزارش مهندسی)
    }

    # دریافت فیلدهای موجود
    existing_fields = []
    try:
        if project.dynamic_fields:
            existing_fields = json.loads(project.dynamic_fields)
    except:
        pass

    # استخراج فایل‌های پروژه برای بررسی وجود مشکلات
    file_paths = [f.get("path", f.get("file_path", "")).lower() for f in files_data]
    file_contents = {f.get("path", f.get("file_path", "")).lower(): f.get("content", "") for f in files_data}

    # ====================================
    # 🔴 تابع تشخیص فیلدهای محافظت شده (ایجاد شده توسط گزارش مهندسی)
    # ====================================
    def is_protected_field(field: Dict) -> bool:
        """بررسی آیا فیلد توسط گزارش مهندسی ایجاد شده و نباید حذف شود"""
        # فیلدهای ایجاد شده توسط گزارش مهندسی
        if field.get("created_from_report"):
            return True
        # فیلدهای با مارکر اعتبارسنجی
        if field.get("validation_marker") in ["validated", "pending"]:
            return True
        # فیلدهای با validator_model (اعتبارسنجی شده توسط مدل)
        if field.get("validator_model"):
            return True
        # فیلدهایی که original_issue دارند (از health analysis آمده)
        if field.get("original_issue"):
            return True
        # فیلدهایی که نامشان با ✅ شروع می‌شود
        if field.get("name", "").startswith("✅"):
            return True
        return False

    # ====================================
    # 🆕 مرحله 1: بررسی فیلدهای موجود - آیا مشکلشان هنوز وجود دارد؟
    # ====================================
    preserved_fields = []
    fields_to_archive = []

    for field in existing_fields:
        if field.get("archived"):
            # فیلدهای بایگانی شده را نگه دار
            preserved_fields.append(field)
            continue

        # 🔴 فیلدهای محافظت شده (از گزارش مهندسی) - هرگز بایگانی نشوند مگر اجرا شده باشند
        if is_protected_field(field):
            if not field.get("executed", False):
                # فیلد محافظت شده و اجرا نشده - حتماً حفظ شود
                preserved_fields.append(field)
                result["protected"].append(field.get("name", "unknown"))
                logger.info(f"🛡️ Protected report-generated field (not executed): {field.get('name')}")
                continue
            else:
                # اجرا شده - بررسی archive_after_run
                if field.get("archive_after_run", False):
                    field["archived"] = True
                    field["archived_at"] = datetime.utcnow().isoformat()
                    field["archived_reason"] = "executed_report_field"
                    result["archived"].append(field.get("name", "unknown"))
                    logger.info(f"Archived executed report field: {field.get('name')}")
                else:
                    preserved_fields.append(field)
                continue

        # بررسی فیلدهای عادی اجرا نشده
        if not field.get("executed", False) and field.get("field_type") == "temporary":
            # بررسی آیا مشکل هنوز وجود دارد
            original_issue = field.get("original_issue", {})
            target_file = field.get("target_path") or original_issue.get("file", "")

            # اگر فایل مرتبط حذف شده، فیلد را بایگانی کن
            if target_file and target_file.lower() not in file_paths:
                field["archived"] = True
                field["archived_at"] = datetime.utcnow().isoformat()
                field["archived_reason"] = "target_file_removed"
                fields_to_archive.append(field["name"])
                result["archived"].append(field["name"])
                logger.info(f"Auto-archived field (file removed): {field['name']}")
            else:
                # فیلد را حفظ کن - مشکل هنوز ممکن است وجود داشته باشد
                preserved_fields.append(field)
                result["preserved"].append(field["name"])
                logger.info(f"Preserved unexecuted field: {field['name']}")
        elif field.get("executed", False):
            # فیلدهای اجرا شده را بررسی کن - آیا باید بایگانی شوند؟
            if field.get("archive_after_run", False):
                field["archived"] = True
                field["archived_at"] = datetime.utcnow().isoformat()
                field["archived_reason"] = "executed_and_archive_after_run"
                fields_to_archive.append(field["name"])
                result["archived"].append(field["name"])
            else:
                preserved_fields.append(field)
        else:
            # فیلدهای permanent را حفظ کن
            preserved_fields.append(field)

    # ====================================
    # 🆕 مرحله 2: ایجاد فیلدهای جدید فقط برای مشکلات جدید
    # ====================================
    new_fields = []
    issues = analysis.get("issues_found", [])

    # استخراج نام فیلدهای موجود برای جلوگیری از تکرار
    existing_field_issues = set()
    for f in preserved_fields:
        original = f.get("original_issue", {})
        if original:
            key = f"{original.get('file', '')}:{original.get('type', '')}:{original.get('line', '')}"
            existing_field_issues.add(key)
        # همچنین نام فیلد را چک کن
        existing_field_issues.add(f.get("name", "").lower())

    for i, issue in enumerate(issues[:5]):  # حداکثر 5 فیلد از مشکلات
        # بررسی تکراری بودن
        issue_key = f"{issue.get('file', '')}:{issue.get('type', '')}:{issue.get('line', '')}"
        issue_name = f"رفع: {issue.get('title', f'مشکل {i+1}')}".lower()

        if issue_key in existing_field_issues or issue_name in existing_field_issues:
            logger.info(f"Skipping duplicate issue: {issue_key}")
            continue

        severity = issue.get("severity", "medium")
        priority = {"critical": 1, "high": 2, "medium": 5, "low": 7}.get(severity, 5)

        field = {
            "id": f"field_{uuid.uuid4().hex[:8]}",
            "name": f"رفع: {issue.get('title', f'مشکل {i+1}')}",
            "value": f"""## مشکل شناسایی شده:
{issue.get('description', '')}

## فایل مرتبط:
{issue.get('file', 'نامشخص')}

## پیشنهاد رفع:
{issue.get('suggestion', '')}

---
لطفاً این مشکل را بررسی و رفع کنید.
""",
            "target_models": ["claude"],
            "trigger": {"enabled": False},
            "action_type": "display",
            "target_path": issue.get("file"),
            "field_type": "temporary",
            "priority": priority,
            "attachments": [],
            "created_at": datetime.utcnow().isoformat(),
            "auto_generated": True,
            "source": "auto-setup-analysis",
            "original_issue": issue,  # 🆕 ذخیره issue اصلی برای بررسی‌های بعدی
            "executed": False,
        }
        new_fields.append(field)
        result["created"].append(field["name"])
        existing_field_issues.add(issue_key)

    # ====================================
    # مرحله 3: ایجاد/به‌روزرسانی فیلد حالت ایده‌آل
    # ====================================
    if analysis.get("ideal_state"):
        # بررسی وجود فیلد حالت ایده‌آل
        existing_ideal = None
        for f in preserved_fields:
            if "حالت ایده‌آل" in f.get("name", ""):
                existing_ideal = f
                break

        if existing_ideal:
            # به‌روزرسانی فیلد موجود
            existing_ideal["value"] = f"""## حالت ایده‌آل:
{analysis.get('ideal_state', '')}

---
از این به عنوان راهنما برای توسعه استفاده کنید.
"""
            existing_ideal["updated_at"] = datetime.utcnow().isoformat()
            result["updated"].append("حالت ایده‌آل پروژه")
        else:
            # ایجاد فیلد جدید
            ideal_field = {
                "id": f"field_{uuid.uuid4().hex[:8]}",
                "name": "حالت ایده‌آل پروژه",
                "value": f"""## حالت ایده‌آل:
{analysis.get('ideal_state', '')}

---
از این به عنوان راهنما برای توسعه استفاده کنید.
""",
                "target_models": ["all"],
                "trigger": {"enabled": False},
                "action_type": "display",
                "field_type": "permanent",
                "priority": 10,
                "attachments": [],
                "created_at": datetime.utcnow().isoformat(),
                "auto_generated": True,
                "source": "auto-setup-analysis"
            }
            new_fields.append(ideal_field)
            result["created"].append("حالت ایده‌آل پروژه")

    # ====================================
    # مرحله 4: ترکیب و مرتب‌سازی
    # ====================================
    # فیلدهای فعال (غیربایگانی) و بایگانی شده را جدا کن
    active_fields = [f for f in preserved_fields if not f.get("archived")]
    archived_fields = [f for f in preserved_fields if f.get("archived")]

    # اضافه کردن فیلدهای جدید به فعال
    active_fields.extend(new_fields)

    # مرتب‌سازی براساس اولویت
    active_fields.sort(key=lambda x: int(x.get("priority", 5)) if str(x.get("priority", 5)).isdigit() else 5)

    # ترکیب نهایی
    all_fields = active_fields + archived_fields

    # ذخیره
    project.dynamic_fields = json.dumps(all_fields, ensure_ascii=False)

    logger.info(f"Field management: created={len(result['created'])}, preserved={len(result['preserved'])}, archived={len(result['archived'])}")

    return result


def _parse_json_response(content: str) -> Optional[Dict]:
    """پارس پاسخ JSON از AI"""
    if not content:
        return None

    try:
        # پیدا کردن JSON در پاسخ
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            for part in parts:
                if "{" in part and "}" in part:
                    content = part
                    break

        # پاکسازی
        content = content.strip()
        if not content.startswith("{"):
            start = content.find("{")
            if start != -1:
                content = content[start:]
        if not content.endswith("}"):
            end = content.rfind("}")
            if end != -1:
                content = content[:end + 1]

        return json.loads(content)

    except json.JSONDecodeError:
        return None
