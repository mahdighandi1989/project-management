"""
Database Configuration - اتصال به SQLite
"""

import os
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

        # Migration برای render_services - ستون‌های دیپلوی
        if "render_services" in tables:
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
    from ..models import project, debate, setting, ai_log, ai_profile

    # اول migration رو اجرا کن (برای جداول موجود)
    migrate_db()

    # ایجاد جداول جدید (اگر وجود نداشتند)
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at {DATABASE_PATH}")


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
