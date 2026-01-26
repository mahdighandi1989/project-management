# -*- coding: utf-8 -*-
"""
سرویس راه‌اندازی خودکار پروژه
تحلیل پروژه و تولید دستورات حافظه و فیلدهای پویا به صورت خودکار
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# =====================================
# قالب‌های پیش‌فرض بر اساس نوع پروژه
# =====================================

PROJECT_TYPE_TEMPLATES = {
    "web_app": {
        "memory_instructions": """## دستورات کلی برای پروژه وب
- کدها باید تمیز، خوانا و با کامنت مناسب باشند
- از best practices برای امنیت استفاده کن (XSS, CSRF, SQL Injection)
- کدها باید responsive و سازگار با موبایل باشند
- از TypeScript/Type hints برای تایپ‌سیفتی استفاده کن
- Error handling مناسب داشته باش""",
        "dynamic_fields": [
            {
                "name": "بررسی امنیتی",
                "value": "کد را از نظر آسیب‌پذیری‌های امنیتی بررسی کن و گزارش بده",
                "target_models": ["claude", "openai"],
                "trigger": {"enabled": True, "interval_minutes": 1440, "interval_type": "days"}
            },
            {
                "name": "بهبود عملکرد",
                "value": "پیشنهادات بهبود performance و optimization ارائه بده",
                "target_models": ["deepseek", "openai"],
                "trigger": {"enabled": True, "interval_minutes": 10080, "interval_type": "days"}
            }
        ],
        "recommended_models": ["claude", "openai"]
    },
    "api": {
        "memory_instructions": """## دستورات کلی برای پروژه API
- از RESTful conventions پیروی کن
- مستندسازی endpoint ها با OpenAPI/Swagger
- Rate limiting و authentication مناسب
- Validation ورودی‌ها
- Error handling یکپارچه با کدهای HTTP مناسب
- Logging برای debugging""",
        "dynamic_fields": [
            {
                "name": "مستندسازی API",
                "value": "endpoint های جدید یا تغییر یافته را مستندسازی کن",
                "target_models": ["openai", "claude"],
                "trigger": {"enabled": False}
            },
            {
                "name": "تست endpoint",
                "value": "برای endpoint های جدید، test case پیشنهاد بده",
                "target_models": ["claude"],
                "trigger": {"enabled": True, "interval_minutes": 720, "interval_type": "minutes"}
            }
        ],
        "recommended_models": ["openai", "claude"]
    },
    "trading": {
        "memory_instructions": """## دستورات کلی برای پروژه ترید
- محاسبات مالی باید دقیق و بدون خطای گرد کردن باشند
- مدیریت ریسک و stop-loss در همه استراتژی‌ها
- لاگ کردن تمام تراکنش‌ها
- تست با داده‌های historical قبل از اجرای واقعی
- هشدار برای شرایط غیرعادی بازار""",
        "dynamic_fields": [
            {
                "name": "تحلیل استراتژی",
                "value": "استراتژی‌های ترید را تحلیل و پیشنهاد بهبود بده",
                "target_models": ["deepseek", "claude"],
                "trigger": {"enabled": True, "interval_minutes": 360, "interval_type": "minutes"}
            },
            {
                "name": "بررسی ریسک",
                "value": "ریسک‌های احتمالی کد را شناسایی کن",
                "target_models": ["claude", "openai"],
                "trigger": {"enabled": True, "interval_minutes": 720, "interval_type": "minutes"}
            }
        ],
        "recommended_models": ["deepseek", "claude"]
    },
    "github_import": {
        "memory_instructions": """## دستورات کلی برای پروژه وارد شده از GitHub
- ساختار و معماری فعلی پروژه را حفظ کن
- قبل از تغییرات، کد موجود را بررسی کن
- با استایل کدنویسی موجود همخوان باش
- تست‌های موجود را خراب نکن
- مستندات README را بروز نگه‌دار""",
        "dynamic_fields": [
            {
                "name": "خلاصه پروژه",
                "value": "یک خلاصه از ساختار و عملکرد پروژه ارائه بده",
                "target_models": ["claude", "openai"],
                "trigger": {"enabled": False}
            },
            {
                "name": "بررسی کیفیت کد",
                "value": "کیفیت کد را بررسی و پیشنهادات بهبود بده",
                "target_models": ["deepseek", "claude"],
                "trigger": {"enabled": True, "interval_minutes": 1440, "interval_type": "days"}
            }
        ],
        "recommended_models": ["claude", "deepseek"]
    },
    "default": {
        "memory_instructions": """## دستورات کلی
- کدها باید تمیز و خوانا باشند
- از best practices استفاده کن
- Error handling مناسب داشته باش
- کامنت‌های توضیحی برای بخش‌های پیچیده""",
        "dynamic_fields": [
            {
                "name": "بررسی کد",
                "value": "کد را بررسی و پیشنهادات بهبود بده",
                "target_models": ["all"],
                "trigger": {"enabled": False}
            }
        ],
        "recommended_models": ["openai", "claude"]
    }
}


# =====================================
# تشخیص نوع پروژه از فایل‌ها
# =====================================

TECHNOLOGY_PATTERNS = {
    # Frontend
    "react": ["package.json:react", "*.jsx", "*.tsx", "next.config.*"],
    "vue": ["package.json:vue", "*.vue", "nuxt.config.*"],
    "angular": ["package.json:@angular", "*.component.ts", "angular.json"],

    # Backend
    "fastapi": ["requirements.txt:fastapi", "main.py:FastAPI", "*.py:@router"],
    "django": ["manage.py", "settings.py:INSTALLED_APPS", "urls.py:urlpatterns"],
    "flask": ["requirements.txt:flask", "app.py:Flask"],
    "express": ["package.json:express", "*.js:require.*express"],
    "nestjs": ["package.json:@nestjs", "*.controller.ts", "*.module.ts"],

    # Trading
    "trading": ["*.py:ccxt", "*.py:pandas", "*.py:ta-lib", "strategy", "backtest"],

    # Mobile
    "react_native": ["package.json:react-native", "App.tsx", "metro.config.js"],
    "flutter": ["pubspec.yaml", "lib/main.dart", "*.dart"],

    # Data Science
    "data_science": ["*.ipynb", "requirements.txt:pandas", "requirements.txt:numpy", "*.py:sklearn"],
}


def detect_project_type_from_files(files: List[Dict]) -> str:
    """تشخیص نوع پروژه از فایل‌ها"""
    file_contents = {}
    file_names = []

    for f in files:
        path = f.get("path", f.get("file_path", ""))
        content = f.get("content", "")
        file_names.append(path.lower())
        file_contents[path.lower()] = content.lower() if content else ""

    scores = {}

    # بررسی الگوها
    for tech, patterns in TECHNOLOGY_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if ":" in pattern:
                # الگوی فایل:محتوا
                file_pattern, content_pattern = pattern.split(":", 1)
                for fname, fcontent in file_contents.items():
                    if file_pattern.replace("*", "") in fname:
                        if content_pattern.lower() in fcontent:
                            score += 2
            else:
                # الگوی نام فایل
                for fname in file_names:
                    if pattern.replace("*", "") in fname:
                        score += 1

        if score > 0:
            scores[tech] = score

    if not scores:
        return "default"

    # تشخیص نوع اصلی
    top_tech = max(scores, key=scores.get)

    if top_tech in ["trading"]:
        return "trading"
    elif top_tech in ["fastapi", "django", "flask", "express", "nestjs"]:
        return "api"
    elif top_tech in ["react", "vue", "angular"]:
        return "web_app"
    elif top_tech in ["react_native", "flutter"]:
        return "mobile"
    elif top_tech in ["data_science"]:
        return "data_science"

    return "default"


# =====================================
# تولید دستورات هوشمند با AI
# =====================================

async def generate_smart_instructions_with_ai(
    project_name: str,
    project_description: str,
    files_summary: List[Dict],
    project_type: str,
    model_id: str = "openai"
) -> Dict[str, Any]:
    """
    تولید دستورات هوشمند با استفاده از AI
    """
    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message

        ai_manager = get_ai_manager()

        # ساخت خلاصه فایل‌ها
        files_text = "\n".join([
            f"- {f.get('path', f.get('file_path', 'unknown'))}: {f.get('language', f.get('file_type', 'unknown'))}"
            for f in files_summary[:30]  # حداکثر 30 فایل
        ])

        prompt = f"""با توجه به پروژه زیر، دستورات مناسب برای کار با AI تولید کن:

نام پروژه: {project_name}
توضیحات: {project_description}
نوع شناسایی شده: {project_type}

فایل‌های پروژه:
{files_text}

لطفاً یک JSON با فرمت زیر برگردان:
{{
    "memory_instructions": "دستورات کلی برای AI (حداکثر 500 کاراکتر فارسی)",
    "dynamic_fields": [
        {{
            "name": "نام فیلد (فارسی)",
            "value": "دستور برای AI (فارسی)",
            "recommended_models": ["openai", "claude"],
            "needs_trigger": true/false,
            "trigger_interval_hours": 24
        }}
    ],
    "project_insights": "خلاصه‌ای از ماهیت پروژه"
}}

حداکثر 3 فیلد پویا تعریف کن. دستورات باید مفید و عملی باشند."""

        messages = [
            Message(role="system", content="تو یک متخصص تحلیل پروژه و DevOps هستی. پاسخ را فقط به صورت JSON بده."),
            Message(role="user", content=prompt)
        ]

        response = await ai_manager.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=1500,
            temperature=0.7
        )

        # پارس JSON از پاسخ
        content = response.content

        # استخراج JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        return {
            "success": True,
            "data": result,
            "tokens_used": response.tokens_used
        }

    except Exception as e:
        logger.error(f"Error generating AI instructions: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# =====================================
# راه‌اندازی خودکار پروژه
# =====================================

async def auto_setup_project_memory(
    project_id: str,
    project_name: str,
    project_description: str,
    project_type: str,
    files: List[Dict],
    use_ai: bool = True,
    db_session = None
) -> Dict[str, Any]:
    """
    راه‌اندازی خودکار حافظه و فیلدهای پویا برای پروژه
    """
    try:
        # تشخیص نوع پروژه از فایل‌ها اگه مشخص نیست
        detected_type = project_type
        if not detected_type or detected_type in ["custom", "unknown", ""]:
            detected_type = detect_project_type_from_files(files)

        logger.info(f"Auto-setup for project {project_id}, detected type: {detected_type}")

        # دریافت قالب پیش‌فرض
        template = PROJECT_TYPE_TEMPLATES.get(detected_type, PROJECT_TYPE_TEMPLATES["default"])

        memory_instructions = template["memory_instructions"]
        dynamic_fields = []

        # تولید فیلدهای پویا از قالب
        for field_template in template["dynamic_fields"]:
            field = {
                "id": f"field_{uuid.uuid4().hex[:8]}",
                "name": field_template["name"],
                "value": field_template["value"],
                "target_models": field_template.get("target_models", ["all"]),
                "trigger": field_template.get("trigger", {"enabled": False}),
                "created_at": datetime.utcnow().isoformat(),
                "auto_generated": True
            }
            dynamic_fields.append(field)

        ai_insights = None

        # اگه AI فعاله، دستورات هوشمندتر تولید کن
        if use_ai and files:
            try:
                # انتخاب مدل مناسب
                model_id = template["recommended_models"][0] if template["recommended_models"] else "openai"

                ai_result = await generate_smart_instructions_with_ai(
                    project_name=project_name,
                    project_description=project_description,
                    files_summary=files[:20],
                    project_type=detected_type,
                    model_id=model_id
                )

                if ai_result.get("success"):
                    data = ai_result["data"]

                    # ترکیب با دستورات قالب
                    if data.get("memory_instructions"):
                        memory_instructions = data["memory_instructions"]

                    # افزودن فیلدهای AI
                    if data.get("dynamic_fields"):
                        for ai_field in data["dynamic_fields"]:
                            field = {
                                "id": f"field_{uuid.uuid4().hex[:8]}",
                                "name": ai_field.get("name", "فیلد جدید"),
                                "value": ai_field.get("value", ""),
                                "target_models": ai_field.get("recommended_models", ["all"]),
                                "trigger": {
                                    "enabled": ai_field.get("needs_trigger", False),
                                    "interval_minutes": ai_field.get("trigger_interval_hours", 24) * 60,
                                    "interval_type": "minutes"
                                },
                                "created_at": datetime.utcnow().isoformat(),
                                "auto_generated": True,
                                "ai_generated": True
                            }
                            dynamic_fields.append(field)

                    ai_insights = data.get("project_insights")

            except Exception as e:
                logger.warning(f"AI generation failed, using template: {e}")

        # ذخیره در دیتابیس
        result = {
            "memory_instructions": {
                "content": memory_instructions,
                "target_models": ["all"],
                "auto_generated": True
            },
            "dynamic_fields": dynamic_fields,
            "detected_type": detected_type,
            "ai_insights": ai_insights,
            "recommended_models": template["recommended_models"]
        }

        if db_session:
            try:
                from ..models.project import Project

                project = db_session.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.memory_instructions = json.dumps(result["memory_instructions"], ensure_ascii=False)
                    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
                    db_session.commit()
                    logger.info(f"Auto-setup saved for project {project_id}")
            except Exception as e:
                logger.error(f"Error saving auto-setup: {e}")
                db_session.rollback()

        return {
            "success": True,
            "project_id": project_id,
            "detected_type": detected_type,
            "memory_instructions": result["memory_instructions"],
            "dynamic_fields": dynamic_fields,
            "ai_insights": ai_insights,
            "recommended_models": template["recommended_models"]
        }

    except Exception as e:
        logger.error(f"Error in auto_setup_project_memory: {e}")
        return {
            "success": False,
            "error": str(e)
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

        # بررسی اگه قبلا تنظیم شده
        existing_memory = {}
        existing_fields = []

        try:
            if project.memory_instructions:
                existing_memory = json.loads(project.memory_instructions)
            if project.dynamic_fields:
                existing_fields = json.loads(project.dynamic_fields)
        except:
            pass

        # اگه قبلا تنظیم شده، اسکیپ کن (مگه اینکه خالی باشه)
        if existing_memory.get("content") and not existing_memory.get("auto_generated"):
            return {
                "success": True,
                "message": "پروژه قبلاً تنظیم شده",
                "skipped": True
            }

        # دریافت فایل‌ها
        files = db_session.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        files_data = [
            {"path": f.file_path, "content": f.content[:1000] if f.content else "", "file_type": f.file_type}
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
