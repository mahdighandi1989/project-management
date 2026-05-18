"""
Database Configuration - اتصال به SQLite
"""

import os
import asyncio
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# مسیر دیتابیس - استفاده از persistent storage در Render
# در production از /app/storage استفاده می‌کنیم که persistent disk است
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    # Render persistent disk path
    DATABASE_DIR = os.environ.get("DATABASE_DIR", "/app/storage")
else:
    # مسیر محلی برای development
    DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

DATABASE_PATH = os.path.join(DATABASE_DIR, "database.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# ایجاد پوشه data اگر وجود نداشت
os.makedirs(DATABASE_DIR, exist_ok=True)

logger.info(f"📁 Database directory: {DATABASE_DIR}")
logger.info(f"📁 Database path: {DATABASE_PATH}")

# ایجاد engine با تنظیمات بهینه برای SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # برای FastAPI async
        "timeout": 30,  # timeout برای lock
    },
    poolclass=StaticPool,  # برای SQLite بهتره
    echo=False,  # True برای دیباگ
)

# فعال کردن foreign keys در SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging برای performance بهتر
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class برای models
Base = declarative_base()


def get_db():
    """
    Dependency برای FastAPI
    استفاده: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager برای استفاده خارج از FastAPI
    استفاده: with get_db_session() as db:
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def migrate_db():
    """
    اعمال migration برای ستون‌های جدید
    SQLite از ALTER TABLE ADD COLUMN پشتیبانی می‌کند
    """
    import sqlite3

    if not os.path.exists(DATABASE_PATH):
        return  # دیتابیس وجود ندارد، نیاز به migration نیست

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # دریافت ستون‌های موجود در هر جدول
    def get_columns(table_name):
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

    try:
        # Migration برای جدول projects
        if "projects" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("projects")

            # اضافه کردن ستون extra_data اگر وجود نداشت
            if "extra_data" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN extra_data TEXT")
                logger.info("Added 'extra_data' column to projects table")

            # اضافه کردن ستون memory_instructions برای باکس حافظه
            if "memory_instructions" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN memory_instructions TEXT")
                logger.info("Added 'memory_instructions' column to projects table")

            # اضافه کردن ستون dynamic_fields برای فیلدهای پویا
            if "dynamic_fields" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN dynamic_fields TEXT")
                logger.info("Added 'dynamic_fields' column to projects table")

            # =====================================================
            # 🆕 ستون‌های جدید برای تحلیل سلامت پروژه
            # =====================================================

            # تنظیمات تحلیل
            if "analysis_settings" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN analysis_settings TEXT")
                logger.info("Added 'analysis_settings' column to projects table")

            # نمرات سلامت
            if "health_scores" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN health_scores TEXT")
                logger.info("Added 'health_scores' column to projects table")

            # نقشه سلامت فایل‌ها
            if "file_health_map" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN file_health_map TEXT")
                logger.info("Added 'file_health_map' column to projects table")

            # شناسه آخرین تحلیل
            if "last_analysis_id" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN last_analysis_id VARCHAR(50)")
                logger.info("Added 'last_analysis_id' column to projects table")

            # زمان آخرین تحلیل
            if "last_analysis_at" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN last_analysis_at DATETIME")
                logger.info("Added 'last_analysis_at' column to projects table")

            # مدل‌های آخرین تحلیل
            if "last_analysis_models" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN last_analysis_models TEXT")
                logger.info("Added 'last_analysis_models' column to projects table")

            # وضعیت تحلیل در حال اجرا (برای pause/resume)
            if "analysis_progress" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN analysis_progress TEXT")
                logger.info("Added 'analysis_progress' column to projects table")

            # محتوای Roadmap
            if "roadmap_content" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN roadmap_content TEXT")
                logger.info("Added 'roadmap_content' column to projects table")

            # محتوای README
            if "readme_content" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN readme_content TEXT")
                logger.info("Added 'readme_content' column to projects table")

            # حالت ایده‌آل
            if "ideal_state" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN ideal_state TEXT")
                logger.info("Added 'ideal_state' column to projects table")

            # مشکلات شناسایی شده
            if "issues_found" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN issues_found TEXT")
                logger.info("Added 'issues_found' column to projects table")

            # =====================================================
            # 🆕 ستون‌های جدید برای زنجیره اعتبارسنجی
            # =====================================================

            # آرشیو مسائل رد شده
            if "rejected_issues_archive" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN rejected_issues_archive TEXT")
                logger.info("Added 'rejected_issues_archive' column to projects table")

            # آخرین نتایج اعتبارسنجی
            if "last_validation_results" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN last_validation_results TEXT")
                logger.info("Added 'last_validation_results' column to projects table")

            # =====================================================
            # 🆕 آرشیو عمومی برای همه موارد پاک شده
            # =====================================================
            if "general_archive" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN general_archive TEXT")
                logger.info("Added 'general_archive' column to projects table")

            # =====================================================
            # 🆕 ستون‌های تحلیل امنیتی و کیفیت کد
            # =====================================================
            if "security_scan_result" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN security_scan_result TEXT")
                logger.info("Added 'security_scan_result' column to projects table")

            if "security_scan_at" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN security_scan_at DATETIME")
                logger.info("Added 'security_scan_at' column to projects table")

            if "license_analysis_result" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN license_analysis_result TEXT")
                logger.info("Added 'license_analysis_result' column to projects table")

            if "test_coverage_result" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN test_coverage_result TEXT")
                logger.info("Added 'test_coverage_result' column to projects table")

        # Migration برای جدول project_files
        if "project_files" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("project_files")

            # اضافه کردن ستون‌های جدید
            if "file_path" not in existing_cols:
                cursor.execute("ALTER TABLE project_files ADD COLUMN file_path VARCHAR(500)")
                logger.info("Added 'file_path' column to project_files table")

            if "content" not in existing_cols:
                cursor.execute("ALTER TABLE project_files ADD COLUMN content TEXT")
                logger.info("Added 'content' column to project_files table")

            if "github_url" not in existing_cols:
                cursor.execute("ALTER TABLE project_files ADD COLUMN github_url VARCHAR(500)")
                logger.info("Added 'github_url' column to project_files table")

            if "checksum" not in existing_cols:
                cursor.execute("ALTER TABLE project_files ADD COLUMN checksum VARCHAR(64)")
                logger.info("Added 'checksum' column to project_files table")

            if "storage_type" not in existing_cols:
                cursor.execute("ALTER TABLE project_files ADD COLUMN storage_type VARCHAR(20) DEFAULT 'local'")
                logger.info("Added 'storage_type' column to project_files table")

            if "storage_path" not in existing_cols:
                cursor.execute("ALTER TABLE project_files ADD COLUMN storage_path VARCHAR(500)")
                logger.info("Added 'storage_path' column to project_files table")

        # Migration برای جدول render_logs
        if "render_logs" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("render_logs")

            # اضافه کردن ستون‌های انتقال به ایرادات
            if "transferred_to_issues" not in existing_cols:
                cursor.execute("ALTER TABLE render_logs ADD COLUMN transferred_to_issues BOOLEAN DEFAULT 0")
                logger.info("Added 'transferred_to_issues' column to render_logs table")

            if "transferred_at" not in existing_cols:
                cursor.execute("ALTER TABLE render_logs ADD COLUMN transferred_at DATETIME")
                logger.info("Added 'transferred_at' column to render_logs table")

            if "transferred_to_project" not in existing_cols:
                cursor.execute("ALTER TABLE render_logs ADD COLUMN transferred_to_project VARCHAR(100)")
                logger.info("Added 'transferred_to_project' column to render_logs table")

        # Migration برای جدول render_log_settings
        if "render_log_settings" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("render_log_settings")

            # اضافه کردن ستون‌های انتقال خودکار
            if "auto_transfer_enabled" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_transfer_enabled BOOLEAN DEFAULT 0")
                logger.info("Added 'auto_transfer_enabled' column to render_log_settings table")

            if "auto_transfer_interval_minutes" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_transfer_interval_minutes INTEGER DEFAULT 30")
                logger.info("Added 'auto_transfer_interval_minutes' column to render_log_settings table")

            if "auto_transfer_hours_back" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_transfer_hours_back INTEGER DEFAULT 24")
                logger.info("Added 'auto_transfer_hours_back' column to render_log_settings table")

            if "last_auto_transfer" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN last_auto_transfer DATETIME")
                logger.info("Added 'last_auto_transfer' column to render_log_settings table")

            if "auto_transfer_mode" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_transfer_mode VARCHAR(20) DEFAULT 'since_deploy'")
                logger.info("Added 'auto_transfer_mode' column to render_log_settings table")

            # =====================================================
            # 🆕 ستون‌های تریگرهای خودکار اضافی
            # =====================================================

            # تریگر تحلیل سلامت خودکار
            if "auto_health_analysis_enabled" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_health_analysis_enabled BOOLEAN DEFAULT 0")
                logger.info("Added 'auto_health_analysis_enabled' column to render_log_settings table")

            if "auto_health_analysis_interval_minutes" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_health_analysis_interval_minutes INTEGER DEFAULT 60")
                logger.info("Added 'auto_health_analysis_interval_minutes' column to render_log_settings table")

            if "last_auto_health_analysis" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN last_auto_health_analysis DATETIME")
                logger.info("Added 'last_auto_health_analysis' column to render_log_settings table")

            # تریگر فیلدهای پویا
            if "auto_dynamic_fields_trigger_enabled" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_dynamic_fields_trigger_enabled BOOLEAN DEFAULT 0")
                logger.info("Added 'auto_dynamic_fields_trigger_enabled' column to render_log_settings table")

            if "auto_dynamic_fields_trigger_interval_minutes" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_dynamic_fields_trigger_interval_minutes INTEGER DEFAULT 120")
                logger.info("Added 'auto_dynamic_fields_trigger_interval_minutes' column to render_log_settings table")

            if "last_auto_dynamic_fields_trigger" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN last_auto_dynamic_fields_trigger DATETIME")
                logger.info("Added 'last_auto_dynamic_fields_trigger' column to render_log_settings table")

            # تریگر انتقال یافته‌های امنیتی
            if "auto_security_transfer_enabled" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_security_transfer_enabled BOOLEAN DEFAULT 0")
                logger.info("Added 'auto_security_transfer_enabled' column to render_log_settings table")

            if "auto_security_transfer_interval_minutes" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_security_transfer_interval_minutes INTEGER DEFAULT 60")
                logger.info("Added 'auto_security_transfer_interval_minutes' column to render_log_settings table")

            if "last_auto_security_transfer" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN last_auto_security_transfer DATETIME")
                logger.info("Added 'last_auto_security_transfer' column to render_log_settings table")

            # تریگر انتقال پوشش تست
            if "auto_test_coverage_transfer_enabled" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_test_coverage_transfer_enabled BOOLEAN DEFAULT 0")
                logger.info("Added 'auto_test_coverage_transfer_enabled' column to render_log_settings table")

            if "auto_test_coverage_transfer_interval_minutes" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_test_coverage_transfer_interval_minutes INTEGER DEFAULT 60")
                logger.info("Added 'auto_test_coverage_transfer_interval_minutes' column to render_log_settings table")

            if "last_auto_test_coverage_transfer" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN last_auto_test_coverage_transfer DATETIME")
                logger.info("Added 'last_auto_test_coverage_transfer' column to render_log_settings table")

            # تریگر گزارش مهندسی خودکار
            if "auto_engineering_report_enabled" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_engineering_report_enabled BOOLEAN DEFAULT 0")
                logger.info("Added 'auto_engineering_report_enabled' column to render_log_settings table")

            if "auto_engineering_report_interval_minutes" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN auto_engineering_report_interval_minutes INTEGER DEFAULT 180")
                logger.info("Added 'auto_engineering_report_interval_minutes' column to render_log_settings table")

            if "last_auto_engineering_report" not in existing_cols:
                cursor.execute("ALTER TABLE render_log_settings ADD COLUMN last_auto_engineering_report DATETIME")
                logger.info("Added 'last_auto_engineering_report' column to render_log_settings table")

        # Migration برای render_services - ستون‌های دیپلوی
        if "render_services" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("render_services")

            if "last_deploy_id" not in existing_cols:
                cursor.execute("ALTER TABLE render_services ADD COLUMN last_deploy_id VARCHAR(50)")
                logger.info("Added 'last_deploy_id' column to render_services table")

            if "last_deploy_at" not in existing_cols:
                cursor.execute("ALTER TABLE render_services ADD COLUMN last_deploy_at DATETIME")
                logger.info("Added 'last_deploy_at' column to render_services table")

            if "last_transferred_deploy_id" not in existing_cols:
                cursor.execute("ALTER TABLE render_services ADD COLUMN last_transferred_deploy_id VARCHAR(50)")
                logger.info("Added 'last_transferred_deploy_id' column to render_services table")

            # 🆕 ستون اتصال دستی به پروژه
            if "project_id" not in existing_cols:
                cursor.execute("ALTER TABLE render_services ADD COLUMN project_id VARCHAR(36)")
                logger.info("Added 'project_id' column to render_services table")
                # ایجاد ایندکس برای جستجوی سریع
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_render_services_project_id ON render_services(project_id)")
                logger.info("Created index on render_services.project_id")

            # 🆕 ستون URL واقعی سرویس (از Render API)
            if "service_url" not in existing_cols:
                cursor.execute("ALTER TABLE render_services ADD COLUMN service_url VARCHAR(500)")
                logger.info("Added 'service_url' column to render_services table")

        # 🔴 Migration برای prompt_executions - ستون‌های پیشرفت real-time
        if "prompt_executions" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("prompt_executions")

            if "current_step" not in existing_cols:
                cursor.execute("ALTER TABLE prompt_executions ADD COLUMN current_step VARCHAR(200)")
                logger.info("Added 'current_step' column to prompt_executions table")

            if "current_progress" not in existing_cols:
                cursor.execute("ALTER TABLE prompt_executions ADD COLUMN current_progress INTEGER DEFAULT 0")
                logger.info("Added 'current_progress' column to prompt_executions table")

            if "total_steps" not in existing_cols:
                cursor.execute("ALTER TABLE prompt_executions ADD COLUMN total_steps INTEGER DEFAULT 0")
                logger.info("Added 'total_steps' column to prompt_executions table")

            if "current_step_index" not in existing_cols:
                cursor.execute("ALTER TABLE prompt_executions ADD COLUMN current_step_index INTEGER DEFAULT 0")
                logger.info("Added 'current_step_index' column to prompt_executions table")

        # 🆕 Migration برای جدول project_issues - ستون Quick Approval
        if "project_issues" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("project_issues")

            # ستون ارتباط با فیلد تبدیل شده
            if "converted_field_id" not in existing_cols:
                cursor.execute("ALTER TABLE project_issues ADD COLUMN converted_field_id VARCHAR(50)")
                logger.info("Added 'converted_field_id' column to project_issues table")

        # 🆕 Migration برای جدول model_settings - ستون فعال‌سازی موقت
        if "model_settings" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("model_settings")

            # ستون فعال‌سازی موقت مدل
            if "temporary_enabled" not in existing_cols:
                cursor.execute("ALTER TABLE model_settings ADD COLUMN temporary_enabled INTEGER DEFAULT 0")
                logger.info("Added 'temporary_enabled' column to model_settings table")

        # 🆕 Migration برای جدول inspector_messages - ستون verified_by_model
        if "inspector_messages" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("inspector_messages")

            if "verified_by_model" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_messages ADD COLUMN verified_by_model VARCHAR(100)")
                logger.info("Added 'verified_by_model' column to inspector_messages table")

            if "logs_checked" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_messages ADD COLUMN logs_checked INTEGER")
                logger.info("Added 'logs_checked' column to inspector_messages table")

            if "error_logs_count" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_messages ADD COLUMN error_logs_count INTEGER")
                logger.info("Added 'error_logs_count' column to inspector_messages table")

            if "checked_logs_data" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_messages ADD COLUMN checked_logs_data TEXT")
                logger.info("Added 'checked_logs_data' column to inspector_messages table")

            if "extra_data" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_messages ADD COLUMN extra_data TEXT")
                logger.info("Added 'extra_data' column to inspector_messages table")

        # 🆕 (C7v2) Migration برای جدول inspector_prompt_fields — افزودن
        # ستون‌های archive، auto-sync، evidence_count، last_seen_at و
        # previous_content برای پشتیبانی از چرخهٔ تقویت/آرشیو
        if "inspector_prompt_fields" in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            existing_cols = get_columns("inspector_prompt_fields")

            if "archived" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_prompt_fields ADD COLUMN archived BOOLEAN DEFAULT 0")
                logger.info("Added 'archived' column to inspector_prompt_fields table")

            if "source" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_prompt_fields ADD COLUMN source VARCHAR(50)")
                logger.info("Added 'source' column to inspector_prompt_fields table")

            if "auto_synced" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_prompt_fields ADD COLUMN auto_synced BOOLEAN DEFAULT 0")
                logger.info("Added 'auto_synced' column to inspector_prompt_fields table")

            if "evidence_count" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_prompt_fields ADD COLUMN evidence_count INTEGER DEFAULT 0")
                logger.info("Added 'evidence_count' column to inspector_prompt_fields table")

            if "last_seen_at" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_prompt_fields ADD COLUMN last_seen_at DATETIME")
                logger.info("Added 'last_seen_at' column to inspector_prompt_fields table")

            if "previous_content" not in existing_cols:
                cursor.execute("ALTER TABLE inspector_prompt_fields ADD COLUMN previous_content TEXT")
                logger.info("Added 'previous_content' column to inspector_prompt_fields table")

        conn.commit()
        logger.info("Database migration completed")

    except Exception as e:
        logger.error(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()


def init_db():
    """
    ایجاد جداول در دیتابیس
    این تابع در startup اپلیکیشن فراخوانی می‌شود
    """
    # Import models تا register شوند
    from ..models import project, debate, setting, ai_log, ai_profile, system_prompt, inspector_session, inspector_prompt_field

    # اول migration رو اجرا کن (برای جداول موجود)
    migrate_db()

    # ایجاد جداول جدید (اگر وجود نداشتند)
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at {DATABASE_PATH}")

    # 🆕 اضافه کردن پرامپت‌های پیش‌فرض سیستم
    _seed_default_prompts()


def get_db_info():
    """اطلاعات دیتابیس"""
    import sqlite3

    if not os.path.exists(DATABASE_PATH):
        return {"exists": False, "path": DATABASE_PATH}

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # لیست جداول
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    # تعداد رکوردها در هر جدول
    table_counts = {}
    for table in tables:
        if not table.startswith('sqlite_'):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cursor.fetchone()[0]

    # سایز فایل
    file_size = os.path.getsize(DATABASE_PATH)

    conn.close()

    return {
        "exists": True,
        "path": DATABASE_PATH,
        "size_bytes": file_size,
        "size_mb": round(file_size / 1024 / 1024, 2),
        "tables": tables,
        "record_counts": table_counts
    }


def _seed_default_prompts():
    """
    اضافه کردن پرامپت‌های پیش‌فرض سیستم
    این تابع فقط یکبار در اولین اجرا، پرامپت‌های پایه را اضافه می‌کند
    """
    import json
    from ..models.system_prompt import SystemPrompt

    db = SessionLocal()
    try:
        # 🔴 بررسی و بازیابی پرامپت‌های گمشده (نه فقط اولین بار)
        logger.info("🔍 Checking for missing system prompts...")

        # لیست همه پرامپت‌های پیش‌فرض که باید وجود داشته باشند
        required_prompt_ids = [
            "health_micro_analysis", "health_macro_analysis", "health_structural_analysis",
            "eng_system_prompt", "eng_validation_prompt", "eng_field_management",
            "auto_setup_main", "auto_setup_roadmap", "auto_setup_readme"
        ]

        # چک کن کدام پرامپت‌ها وجود ندارند
        existing_ids = [p.id for p in db.query(SystemPrompt.id).filter(
            SystemPrompt.id.in_(required_prompt_ids)
        ).all()]

        missing_ids = [pid for pid in required_prompt_ids if pid not in existing_ids]

        if not missing_ids:
            logger.info(f"✅ All {len(required_prompt_ids)} default prompts exist")
            return

        logger.info(f"🌱 Restoring {len(missing_ids)} missing prompts: {missing_ids}")

        # =====================================================
        # 🩺 پرامپت‌های تحلیل سلامت (Health Analysis)
        # =====================================================
        health_prompts = [
            {
                "id": "health_micro_analysis",
                "name": "تحلیل جزئی فایل (Micro Analysis)",
                "description": "بررسی دقیق هر فایل به صورت جداگانه - کیفیت کد، امنیت، کارایی",
                "category": "health_analysis",
                "prompt_type": "instruction",
                "execution_order": 1,
                "is_required": True,
                "content": """# تحلیل جزئی فایل (Micro Analysis)

## فایل: {file_path}
## نوع فایل: {file_type}

## دستورات:
{instruction}

## محتوای فایل:
```
{content}
```

## وظیفه تو:
1. **بررسی کامل کد**: هر خط را بررسی کن (نه خلاصه!)
2. **شناسایی مشکلات**: باگ‌ها، آسیب‌پذیری‌ها، کد بد
3. **بررسی کیفیت**: نام‌گذاری، ساختار، خوانایی
4. **تطبیق با نقشه‌راه**: آیا این فایل با نقشه‌راه همخوانی دارد؟
5. **نمره‌دهی دقیق**: برای هر فاکتور نمره 0-100 بده

## فرمت خروجی (JSON):
```json
{
    "scores": {
        "code_quality": 0-100,
        "documentation": 0-100,
        "roadmap_compliance": 0-100,
        "security": 0-100,
        "efficiency": 0-100,
        "standards_compliance": 0-100
    },
    "issues": [
        {
            "line": شماره خط,
            "severity": "critical|high|medium|low",
            "type": "bug|security|quality|performance",
            "message": "توضیح مشکل",
            "suggestion": "پیشنهاد رفع"
        }
    ],
    "summary": "خلاصه یک خطی وضعیت فایل",
    "strengths": ["نقاط قوت"],
    "weaknesses": ["نقاط ضعف"]
}
```

مهم: فقط JSON برگردان، بدون توضیح اضافی!""",
                "variables": json.dumps({
                    "file_path": "مسیر فایل",
                    "file_type": "نوع فایل (python, javascript, etc.)",
                    "instruction": "دستورات تحلیل",
                    "content": "محتوای فایل"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "json",
                    "min_tokens": 500,
                    "max_tokens": 4000,
                    "tags": ["analysis", "file", "quality"]
                }, ensure_ascii=False)
            },
            {
                "id": "health_macro_analysis",
                "name": "تحلیل کلی پروژه (Macro Analysis)",
                "description": "بررسی همکاری و جایگاه فایل‌ها در کل پروژه",
                "category": "health_analysis",
                "prompt_type": "instruction",
                "execution_order": 2,
                "is_required": True,
                "content": """# تحلیل کلی پروژه (Macro Analysis)

## دستورات:
{instruction}

## نمای کلی پروژه:
{project_overview}

## نقشه‌راه پروژه:
{roadmap_content}

## README پروژه:
{readme_content}

## وظیفه تو:
1. **همکاری فایل‌ها**: آیا فایل‌ها با هم به درستی کار می‌کنند؟
2. **جایگاه فایل‌ها**: آیا هر فایل در جای درست قرار دارد؟
3. **تطبیق با نقشه‌راه**: پروژه چقدر با نقشه‌راه مطابقت دارد؟
4. **تطبیق با README**: آیا README دقیق است؟
5. **نیازها و کمبودها**: چه چیزهایی کم است؟

## فرمت خروجی (JSON):
```json
{
    "cooperation_scores": {
        "فایل1": {"score": 0-100, "issues": [], "cooperates_well_with": [], "conflicts_with": []}
    },
    "roadmap_compliance": {
        "overall_score": 0-100,
        "completed_items": [],
        "missing_items": []
    },
    "project_needs": {
        "missing_files": ["فایل‌هایی که باید ایجاد شوند"],
        "files_to_remove": ["فایل‌های اضافی"]
    },
    "overall_health": 0-100,
    "summary": "خلاصه وضعیت کلی"
}
```

مهم: فقط JSON برگردان!""",
                "variables": json.dumps({
                    "instruction": "دستورات تحلیل",
                    "project_overview": "نمای کلی پروژه",
                    "roadmap_content": "محتوای نقشه‌راه",
                    "readme_content": "محتوای README"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "json",
                    "min_tokens": 1000,
                    "max_tokens": 6000,
                    "tags": ["analysis", "project", "macro"]
                }, ensure_ascii=False)
            },
            {
                "id": "health_structural_analysis",
                "name": "تحلیل ساختاری (Structural Analysis)",
                "description": "بررسی سیم‌کشی، وابستگی‌ها و معماری پروژه",
                "category": "health_analysis",
                "prompt_type": "instruction",
                "execution_order": 3,
                "is_required": True,
                "content": """# تحلیل ساختاری پروژه (Structural Analysis)

## دستورات:
{instruction}

## لیست فایل‌ها:
{file_list}

## گراف وابستگی‌ها:
{dependency_graph}

## خلاصه تحلیل جزئی (Micro):
{micro_summary}

## خلاصه تحلیل کلی (Macro):
{macro_summary}

## وظیفه تو:
1. **سیم‌کشی**: آیا import ها و وابستگی‌ها درست هستند؟
2. **معماری**: آیا ساختار پروژه منطقی است؟
3. **circular dependencies**: آیا وابستگی دایره‌ای وجود دارد؟
4. **کمبودها**: چه فایل‌هایی باید ایجاد شوند؟
5. **اضافات**: چه فایل‌هایی اضافی هستند؟
6. **حالت ایده‌آل**: ساختار ایده‌آل چیست؟

## فرمت خروجی (JSON):
```json
{
    "architecture": {
        "type": "monolith|microservice|modular|...",
        "score": 0-100,
        "issues": []
    },
    "circular_dependencies": [
        {"files": ["فایل1", "فایل2"], "severity": "high|medium|low"}
    ],
    "missing_files": [
        {"path": "مسیر پیشنهادی", "purpose": "هدف", "priority": "high|medium|low"}
    ],
    "ideal_structure": {
        "description": "توضیح ساختار ایده‌آل",
        "components": [],
        "roadmap_to_ideal": []
    },
    "overall_score": 0-100,
    "summary": "خلاصه وضعیت ساختار"
}
```

مهم: فقط JSON برگردان!""",
                "variables": json.dumps({
                    "instruction": "دستورات تحلیل",
                    "file_list": "لیست فایل‌ها",
                    "dependency_graph": "گراف وابستگی‌ها",
                    "micro_summary": "خلاصه تحلیل جزئی",
                    "macro_summary": "خلاصه تحلیل کلی"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "json",
                    "min_tokens": 1000,
                    "max_tokens": 6000,
                    "tags": ["analysis", "structure", "architecture"]
                }, ensure_ascii=False)
            }
        ]

        # =====================================================
        # 📊 پرامپت‌های گزارش مهندسی (Engineering Report)
        # =====================================================
        engineering_prompts = [
            {
                "id": "eng_system_prompt",
                "name": "دستورات سیستمی گزارش مهندسی",
                "description": "دستورات اصلی برای تولید گزارش مهندسی جامع",
                "category": "engineering_report",
                "prompt_type": "system",
                "execution_order": 1,
                "is_required": True,
                "content": """تو یک مهندس ارشد نرم‌افزار هستی که باید یک گزارش مهندسی جامع و حرفه‌ای تولید کنی.

🔴 وظایف اصلی:
1. اعتبارسنجی health analysis - هر ایراد را بررسی و تایید/رد کن
2. بررسی فیلدهای PENDING - تایید، رد یا ادغام کن
3. بررسی نقشه راه - آیتم‌های انجام شده و نشده
4. تولید فیلدهای عملیاتی برای مشکلات

📝 ساختار خروجی JSON:
- executive_summary: خلاصه مدیریتی
- project_health: نمره و وضعیت سلامت
- technical_analysis: نقاط قوت و ضعف
- bugs_and_issues: باگ‌ها و مشکلات
- security_review: بررسی امنیتی
- recommendations: توصیه‌ها
- field_management: مدیریت فیلدها
- roadmap: نقشه راه فوری/کوتاه‌مدت/بلندمدت
- health_analysis_validation: اعتبارسنجی ایرادات

⚠️ نکات مهم:
- فیلدهای display ایجاد نکن - فقط github_commit/github_multi_commit
- target_path حتماً باید مسیر فایل هدف باشد
- توضیحات باید کامل باشد تا AI بتواند کد تولید کند
- priority از 1 (بالاترین) تا 10 (پایین‌ترین)""",
                "variables": json.dumps({}, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "json",
                    "min_tokens": 2000,
                    "max_tokens": 8000,
                    "tags": ["engineering", "report", "system"]
                }, ensure_ascii=False)
            },
            {
                "id": "eng_validation_prompt",
                "name": "اعتبارسنجی ایرادات سلامت",
                "description": "بررسی و تایید/رد ایرادات شناسایی شده در health analysis",
                "category": "engineering_report",
                "prompt_type": "instruction",
                "execution_order": 2,
                "is_required": True,
                "content": """🔴 اعتبارسنجی health analysis (بسیار مهم):

## ایرادات شناسایی شده:
{health_issues}

## کد مربوطه:
{related_code}

## وظیفه:
- تمام ایرادات ارسال شده را یک به یک بررسی کن
- با نگاه به کد واقعی، مشخص کن آیا هر ایراد معتبر است یا نه
- ایرادات معتبر را در validated_issues با create_field=true قرار بده
- ایرادات نامعتبر را در rejected_issues با دلیل دقیق رد شدن قرار بده
- validation_score از 0-100: بالای 70 = معتبر، زیر 30 = رد شده

## فرمت خروجی:
```json
{
    "health_analysis_validation": {
        "total_reviewed": 15,
        "validated_issues": [
            {
                "original_issue": {"file": "path", "type": "security", "message": "..."},
                "validation_score": 95,
                "validation_note": "این ایراد تایید می‌شود چون...",
                "priority": "high",
                "create_field": true
            }
        ],
        "rejected_issues": [
            {
                "original_issue": {"file": "path", "type": "unused", "message": "..."},
                "rejection_reason": "دلیل رد شدن",
                "validation_score": 20
            }
        ],
        "validation_summary": "خلاصه اعتبارسنجی"
    }
}
```""",
                "variables": json.dumps({
                    "health_issues": "لیست ایرادات از health analysis",
                    "related_code": "کد مربوطه برای بررسی"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "json",
                    "tags": ["validation", "health", "issues"]
                }, ensure_ascii=False)
            },
            {
                "id": "eng_field_management",
                "name": "مدیریت فیلدهای پویا",
                "description": "بررسی و مدیریت فیلدهای PENDING - تایید، رد، ادغام",
                "category": "engineering_report",
                "prompt_type": "instruction",
                "execution_order": 3,
                "is_required": True,
                "content": """🔴 مدیریت فیلدهای PENDING (بسیار مهم):

## فیلدهای PENDING:
{pending_fields}

## فیلدهای موجود (تایید شده):
{approved_fields}

## فیلدهای بایگانی شده:
{archived_fields}

## وظیفه:
1. هر فیلد pending را بررسی کن
2. اگر لازم است: id را در fields_to_approve قرار بده
3. اگر غیرضروری/تکراری: id را در fields_to_reject قرار بده
4. اگر قابل ادغام با فیلد دیگر: در fields_to_merge قرار بده
5. اگر نیاز به به‌روزرسانی: در fields_to_update قرار بده

## فرمت خروجی:
```json
{
    "field_management": {
        "fields_to_archive": ["id_فیلدهایی که انجام شده"],
        "fields_to_approve": ["id_فیلدهای pending که تایید می‌شوند"],
        "fields_to_reject": ["id_فیلدهای pending که رد می‌شوند"],
        "fields_to_merge": [
            {"source_ids": ["id1", "id2"], "merged_name": "نام جدید", "merged_value": "دستور ادغام‌شده"}
        ],
        "fields_to_update": [
            {"id": "id_فیلد", "new_value": "دستور جدید", "new_priority": 3}
        ]
    }
}
```""",
                "variables": json.dumps({
                    "pending_fields": "فیلدهای در انتظار تایید",
                    "approved_fields": "فیلدهای تایید شده",
                    "archived_fields": "فیلدهای بایگانی شده"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "json",
                    "tags": ["fields", "management", "approval"]
                }, ensure_ascii=False)
            }
        ]

        # =====================================================
        # 🚀 پرامپت‌های راه‌اندازی خودکار (Auto Setup)
        # =====================================================
        auto_setup_prompts = [
            {
                "id": "auto_setup_main",
                "name": "راه‌اندازی خودکار پروژه",
                "description": "تحلیل پروژه و تولید فیلدهای پویا و دستورات AI",
                "category": "auto_setup",
                "prompt_type": "instruction",
                "execution_order": 1,
                "is_required": True,
                "content": """تو یک معمار نرم‌افزار و DevOps متخصص هستی. این پروژه را تحلیل کن و دستورات دقیق و اختصاصی برای کار با AI تولید کن.

## اطلاعات پروژه
- **نام**: {project_name}
- **توضیحات**: {project_description}
- **زبان اصلی**: {language}
- **فریم‌ورک‌ها**: {frameworks}
- **معماری**: {architecture}

## فایل‌های موجود در پروژه
{file_list}

## وظیفه تو
بر اساس تحلیل دقیق این پروژه، یک JSON با این ساختار برگردان:

```json
{
    "memory_instructions": "دستورالعمل‌های حافظه (توضیح کامل در پایین)",
    "fields_to_archive": ["id_فیلد_1"],
    "fields_to_merge": [
        {"source_ids": ["id1", "id2"], "merged_name": "نام", "merged_value": "دستور"}
    ],
    "dynamic_fields": [
        {
            "name": "نام فیلد (فارسی)",
            "value": "دستور دقیق برای AI",
            "why": "چرا این فیلد مهمه",
            "recommended_model": "claude|openai|deepseek",
            "action_type": "display|github_commit|github_multi_commit",
            "target_path": "مسیر فایل",
            "archive_after_run": true/false,
            "priority": 1-10,
            "field_type": "permanent|temporary"
        }
    ],
    "missing_files": [
        {"path": "مسیر", "description": "توضیح", "priority": "high|medium|low"}
    ],
    "project_summary": "خلاصه 3-5 خطی",
    "key_recommendations": ["توصیه 1", "توصیه 2"]
}
```

## ⚠️ مهم‌ترین نکته: memory_instructions چیست؟

**باکس حافظه توضیح پروژه نیست!** این یک چارچوب و دستورالعمل برای مدل‌های AI است که باید قبل از هر کاری آن را مطالعه کنند.

memory_instructions باید شامل موارد زیر باشد (حداقل 1000 کاراکتر):

### 1. قوانین کلی پروژه
- استانداردهای کدنویسی (مثلاً: "همیشه از TypeScript استفاده کن، از any پرهیز کن")
- قواعد نام‌گذاری (مثلاً: "کامپوننت‌ها PascalCase، متغیرها camelCase")
- ساختار پوشه‌بندی که باید رعایت شود

### 2. محدودیت‌ها و هشدارها
- فایل‌هایی که نباید تغییر کنند (مثلاً: "فایل config.prod.js را ویرایش نکن")
- وابستگی‌هایی که نباید نصب شوند
- الگوهایی که نباید استفاده شوند

### 3. ترجیحات فنی
- کتابخانه‌های ترجیحی (مثلاً: "برای state از Zustand استفاده کن نه Redux")
- روش‌های ترجیحی (مثلاً: "برای API از React Query استفاده کن")
- سبک کدنویسی ترجیحی

### 4. نکات خاص این پروژه
- باگ‌های شناخته‌شده که باید مراقبشان بود
- قسمت‌های حساس کد
- نکاتی که توسعه‌دهنده قبلی گذاشته

### 5. دستورات دائمی
- کارهایی که همیشه باید انجام شود (مثلاً: "بعد از هر تغییر، تست بنویس")
- بررسی‌هایی که همیشه لازم است

**مثال صحیح:**
```
## قوانین کدنویسی
- از TypeScript strict mode استفاده کن
- هر کامپوننت باید در پوشه جداگانه با index.ts باشد
- از inline styles استفاده نکن، فقط Tailwind

## محدودیت‌ها
- فایل‌های /core را تغییر نده مگر اینکه صریحاً گفته شود
- از moment.js استفاده نکن، از date-fns استفاده کن

## نکات مهم
- API قدیمی /api/v1 در حال deprecation است، از /api/v2 استفاده کن
- کامپوننت Button در /shared/ui باگ شناخته‌شده دارد، از /components/Button استفاده کن
```

**مثال اشتباه (این کار را نکن!):**
```
این پروژه یک سیستم مدیریت است که با React نوشته شده و...
```

## نکات دیگر:
- حداقل 2 و حداکثر 6 فیلد پویای جدید تعریف کن
- فیلدهای تکراری ایجاد نکن
- priority از 1 (بالاترین) تا 10 (پایین‌ترین)
- field_type: permanent برای دائمی، temporary برای یکبار مصرف""",
                "variables": json.dumps({
                    "project_name": "نام پروژه",
                    "project_description": "توضیحات پروژه",
                    "language": "زبان برنامه‌نویسی",
                    "frameworks": "فریم‌ورک‌ها",
                    "architecture": "معماری",
                    "file_list": "لیست فایل‌ها"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "json",
                    "min_tokens": 1500,
                    "max_tokens": 6000,
                    "tags": ["setup", "fields", "memory"]
                }, ensure_ascii=False)
            },
            {
                "id": "auto_setup_roadmap",
                "name": "ایجاد/ارتقای نقشه‌راه",
                "description": "مدیریت و به‌روزرسانی نقشه‌راه پروژه",
                "category": "auto_setup",
                "prompt_type": "instruction",
                "execution_order": 2,
                "is_required": False,
                "content": """# مدیریت نقشه‌راه پروژه

## پروژه: {project_name}

## وضعیت فعلی:
{current_state}

## ایرادات شناسایی شده:
{issues_found}

## حالت ایده‌آل:
{ideal_state}

## نقشه‌راه موجود:
{existing_roadmap}

## وظیفه:
{task_type}

یک نقشه‌راه کامل و حرفه‌ای به زبان فارسی بنویس که شامل:
1. اهداف کوتاه‌مدت و بلندمدت
2. فازهای توسعه با جزئیات
3. باگ‌ها و مشکلاتی که باید رفع شوند
4. قابلیت‌های جدید پیشنهادی
5. زمان‌بندی تقریبی

فقط محتوای Markdown نقشه‌راه را برگردان.""",
                "variables": json.dumps({
                    "project_name": "نام پروژه",
                    "current_state": "وضعیت فعلی",
                    "issues_found": "ایرادات شناسایی شده",
                    "ideal_state": "حالت ایده‌آل",
                    "existing_roadmap": "نقشه‌راه موجود",
                    "task_type": "ایجاد جدید یا ارتقا"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "markdown",
                    "tags": ["roadmap", "planning"]
                }, ensure_ascii=False)
            },
            {
                "id": "auto_setup_readme",
                "name": "ایجاد/ارتقای README",
                "description": "مدیریت و به‌روزرسانی فایل README پروژه",
                "category": "auto_setup",
                "prompt_type": "instruction",
                "execution_order": 3,
                "is_required": False,
                "content": """# مدیریت README پروژه

## پروژه: {project_name}
## توضیحات: {project_description}

## اطلاعات فنی:
- زبان: {language}
- فریم‌ورک‌ها: {frameworks}
- معماری: {architecture}
- وابستگی‌ها: {dependencies}

## README موجود:
{existing_readme}

## نقشه‌راه:
{roadmap_content}

## وظیفه:
{task_type}

یک README کامل و حرفه‌ای به زبان فارسی بنویس که شامل:
1. معرفی پروژه
2. ویژگی‌ها و قابلیت‌ها
3. نیازمندی‌ها و نحوه نصب
4. نحوه استفاده
5. ساختار پروژه
6. مشارکت در توسعه

فقط محتوای Markdown README را برگردان.""",
                "variables": json.dumps({
                    "project_name": "نام پروژه",
                    "project_description": "توضیحات",
                    "language": "زبان",
                    "frameworks": "فریم‌ورک‌ها",
                    "architecture": "معماری",
                    "dependencies": "وابستگی‌ها",
                    "existing_readme": "README موجود",
                    "roadmap_content": "محتوای نقشه‌راه",
                    "task_type": "ایجاد جدید یا ارتقا"
                }, ensure_ascii=False),
                "metadata_json": json.dumps({
                    "output_format": "markdown",
                    "tags": ["readme", "documentation"]
                }, ensure_ascii=False)
            }
        ]

        # ذخیره همه پرامپت‌ها
        all_prompts = health_prompts + engineering_prompts + auto_setup_prompts

        # 🔴 فقط پرامپت‌های گمشده را اضافه کن
        added_count = 0
        for prompt_data in all_prompts:
            if prompt_data["id"] not in missing_ids:
                continue  # این پرامپت قبلاً وجود دارد

            prompt = SystemPrompt(
                id=prompt_data["id"],
                name=prompt_data["name"],
                description=prompt_data.get("description", ""),
                category=prompt_data["category"],
                prompt_type=prompt_data.get("prompt_type", "instruction"),
                execution_order=prompt_data.get("execution_order", 1),
                is_required=prompt_data.get("is_required", True),
                content=prompt_data["content"],
                variables=prompt_data.get("variables"),
                metadata_json=prompt_data.get("metadata_json"),
                is_active=True,
                is_default=True,
                is_locked=True  # پرامپت‌های پیش‌فرض قفل هستند (قابل حذف نیستند)
            )
            db.add(prompt)
            added_count += 1
            logger.info(f"  + Restored prompt: {prompt_data['id']}")

        db.commit()
        logger.info(f"✅ Restored {added_count} missing system prompts")

    except Exception as e:
        logger.error(f"❌ Error seeding default prompts: {e}")
        db.rollback()
    finally:
        db.close()


# =====================================
# 🔴 Project Lock Manager - جلوگیری از Race Condition
# =====================================

class ProjectLockManager:
    """
    مدیریت قفل برای عملیات همزمان روی پروژه‌ها

    هر پروژه یک قفل مجزا دارد تا عملیات روی پروژه‌های مختلف
    بدون تداخل انجام شود، اما عملیات روی یک پروژه serialize شود.

    Usage:
        async with project_lock_manager.acquire_lock(project_id, "issues_found"):
            # عملیات روی issues_found
            db.refresh(project)
            # ... modifications ...
            db.commit()
    """

    def __init__(self):
        self._locks: dict = {}  # project_id:field -> asyncio.Lock
        self._master_lock = asyncio.Lock()  # برای ایجاد قفل‌های جدید

    async def acquire_lock(self, project_id: str, field: str = "default"):
        """
        دریافت قفل برای یک فیلد خاص از پروژه

        Args:
            project_id: شناسه پروژه
            field: نام فیلد (issues_found, dynamic_fields, memory_instructions, ...)
        """
        lock_key = f"{project_id}:{field}"

        async with self._master_lock:
            if lock_key not in self._locks:
                self._locks[lock_key] = asyncio.Lock()

        return self._locks[lock_key]

    async def get_lock(self, project_id: str, field: str = "default"):
        """Alias برای acquire_lock - برای سازگاری"""
        return await self.acquire_lock(project_id, field)

    def cleanup_old_locks(self, max_locks: int = 1000):
        """پاکسازی قفل‌های قدیمی برای جلوگیری از memory leak"""
        if len(self._locks) > max_locks:
            # حذف نیمی از قفل‌هایی که در حال استفاده نیستند
            to_remove = []
            for key, lock in self._locks.items():
                if not lock.locked():
                    to_remove.append(key)
                if len(to_remove) >= max_locks // 2:
                    break
            for key in to_remove:
                del self._locks[key]
            logger.info(f"🔒 Cleaned up {len(to_remove)} unused locks")


# Singleton instance
project_lock_manager = ProjectLockManager()


def get_project_lock_manager() -> ProjectLockManager:
    """دریافت instance از مدیر قفل"""
    return project_lock_manager


# =====================================
# 🔴 Helper functions برای db operations
# =====================================

def safe_refresh(db, obj, logger_name: str = "DB"):
    """
    بازخوانی امن یک object از دیتابیس

    Args:
        db: Database session
        obj: SQLAlchemy object
        logger_name: نام لاگر برای پیام‌ها
    """
    try:
        db.refresh(obj)
        return True
    except Exception as e:
        logger.warning(f"[{logger_name}] Could not refresh object: {e}")
        return False


def safe_commit(db, logger_name: str = "DB") -> bool:
    """
    کامیت امن با rollback در صورت خطا

    Args:
        db: Database session
        logger_name: نام لاگر

    Returns:
        True اگر موفق، False اگر خطا
    """
    try:
        db.commit()
        return True
    except Exception as e:
        logger.error(f"[{logger_name}] Commit failed, rolling back: {e}")
        try:
            db.rollback()
        except:
            pass
        return False
