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

# مسیر دیتابیس
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "database.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# ایجاد پوشه data اگر وجود نداشت
os.makedirs(DATABASE_DIR, exist_ok=True)

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

            # اضافه کردن ستون metadata اگر وجود نداشت
            if "metadata" not in existing_cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN metadata TEXT")
                logger.info("Added 'metadata' column to projects table")

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
    from ..models import project, debate, setting, ai_log

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
