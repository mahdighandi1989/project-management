# -*- coding: utf-8 -*-
"""
سرویس راه‌اندازی خودکار هوشمند پروژه
تحلیل عمیق پروژه و تولید دستورات و فیلدهای اختصاصی با AI
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


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
    model_id: str = "claude"
) -> Dict[str, Any]:
    """
    تولید دستورات و فیلدهای کاملاً اختصاصی با AI
    """
    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message

        ai_manager = get_ai_manager()

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

## نمونه فایل‌های پروژه
{files_text}

## وظیفه تو
بر اساس تحلیل دقیق این پروژه، یک JSON با این ساختار برگردان:

{{
    "memory_instructions": "دستورات ثابت و اختصاصی برای این پروژه (۳۰۰-۵۰۰ کاراکتر فارسی). شامل: نحوه کدنویسی، استانداردها، نکات مهم این پروژه خاص، چیزهایی که باید رعایت شود",

    "dynamic_fields": [
        {{
            "name": "نام فیلد (فارسی، مرتبط با این پروژه)",
            "value": "دستور دقیق برای AI (فارسی)",
            "why": "چرا این فیلد برای این پروژه مهمه",
            "recommended_model": "openai یا claude یا deepseek (بر اساس نوع کار)",
            "needs_trigger": true/false,
            "trigger_hours": 24
        }}
    ],

    "project_summary": "خلاصه ۲-۳ خطی از ماهیت و هدف پروژه",

    "key_recommendations": ["توصیه ۱", "توصیه ۲", "توصیه ۳"]
}}

نکات مهم:
- دستورات باید کاملاً اختصاصی این پروژه باشند، نه کلی
- حداکثر ۴ فیلد پویا تعریف کن
- فیلدها باید واقعاً مفید و عملی باشند
- از تحلیل کدها و ساختار پروژه استفاده کن
- اگه پروژه ترید/مالی است، روی ریسک و دقت تمرکز کن
- اگه وب اپ است، روی UX و امنیت تمرکز کن
- اگه API است، روی مستندسازی و تست تمرکز کن"""

        messages = [
            Message(role="system", content="تو یک معمار نرم‌افزار متخصص هستی که پروژه‌ها را تحلیل می‌کنی. پاسخ را فقط به صورت JSON معتبر بده."),
            Message(role="user", content=prompt)
        ]

        # اول claude امتحان کن، بعد openai
        for try_model in [model_id, "claude", "openai", "deepseek"]:
            try:
                response = await ai_manager.generate(
                    model_id=try_model,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                break
            except Exception:
                continue
        else:
            return {"success": False, "error": "هیچ مدل AI در دسترس نیست"}

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

        result = json.loads(content)
        return {
            "success": True,
            "data": result,
            "tokens_used": response.tokens_used,
            "model_used": response.model_id
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {"success": False, "error": f"خطا در پارس پاسخ AI: {e}"}
    except Exception as e:
        logger.error(f"Error generating AI instructions: {e}")
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
    db_session=None
) -> Dict[str, Any]:
    """
    راه‌اندازی خودکار هوشمند حافظه و فیلدهای پویا
    """
    try:
        logger.info(f"Starting intelligent auto-setup for project {project_id}")

        # مرحله ۱: تحلیل عمیق پروژه
        insights = extract_project_insights(files)
        logger.info(f"Project insights: {insights.get('domain')}, {insights.get('architecture')}")

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
            important_files = important_files[:10]

        # مرحله ۲: تولید دستورات با AI
        ai_result = None
        if use_ai and important_files:
            best_model = select_best_model("analysis", insights.get("domain", ""))
            ai_result = await generate_intelligent_setup(
                project_name=project_name,
                project_description=project_description,
                insights=insights,
                sample_files=important_files,
                model_id=best_model
            )

        # مرحله ۳: ساخت نتیجه نهایی
        if ai_result and ai_result.get("success"):
            data = ai_result["data"]

            memory_instructions = {
                "content": data.get("memory_instructions", ""),
                "target_models": ["all"],
                "auto_generated": True,
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": ai_result.get("model_used")
            }

            dynamic_fields = []
            for ai_field in data.get("dynamic_fields", []):
                recommended_model = ai_field.get("recommended_model", "claude")
                field = {
                    "id": f"field_{uuid.uuid4().hex[:8]}",
                    "name": ai_field.get("name", "فیلد"),
                    "value": ai_field.get("value", ""),
                    "target_models": [recommended_model] if recommended_model != "all" else ["all"],
                    "trigger": {
                        "enabled": ai_field.get("needs_trigger", False),
                        "interval_minutes": ai_field.get("trigger_hours", 24) * 60,
                        "interval_type": "minutes"
                    },
                    "created_at": datetime.utcnow().isoformat(),
                    "auto_generated": True,
                    "ai_generated": True,
                    "reason": ai_field.get("why", "")
                }
                dynamic_fields.append(field)

            result = {
                "success": True,
                "project_id": project_id,
                "detected_type": insights.get("domain", project_type),
                "language": insights.get("language"),
                "architecture": insights.get("architecture"),
                "frameworks": insights.get("frameworks", []),
                "memory_instructions": memory_instructions,
                "dynamic_fields": dynamic_fields,
                "ai_insights": data.get("project_summary"),
                "recommendations": data.get("key_recommendations", []),
                "tokens_used": ai_result.get("tokens_used", 0),
                "model_used": ai_result.get("model_used")
            }

        else:
            # Fallback به حالت ساده
            result = _create_fallback_setup(project_id, project_name, insights)

        # مرحله ۴: ذخیره در دیتابیس
        if db_session and result.get("success"):
            try:
                from ..models.project import Project

                project = db_session.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.memory_instructions = json.dumps(result["memory_instructions"], ensure_ascii=False)
                    project.dynamic_fields = json.dumps(result["dynamic_fields"], ensure_ascii=False)
                    db_session.commit()
                    logger.info(f"Intelligent auto-setup saved for project {project_id}")
            except Exception as e:
                logger.error(f"Error saving auto-setup: {e}")
                db_session.rollback()

        return result

    except Exception as e:
        logger.error(f"Error in auto_setup_project_memory: {e}")
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
- تست‌پذیری کد مهم است"""

    return {
        "success": True,
        "project_id": project_id,
        "detected_type": domain,
        "language": lang,
        "memory_instructions": {
            "content": memory,
            "target_models": ["all"],
            "auto_generated": True,
            "fallback": True
        },
        "dynamic_fields": [{
            "id": f"field_{uuid.uuid4().hex[:8]}",
            "name": "بررسی کد",
            "value": f"کد {lang} را بررسی و پیشنهاد بهبود بده",
            "target_models": ["all"],
            "trigger": {"enabled": False},
            "auto_generated": True
        }],
        "ai_insights": None,
        "recommendations": []
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
