# -*- coding: utf-8 -*-
"""
مدل دیتابیس برای ذخیره لاگ‌های Render
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Index
from sqlalchemy.sql import func
from ..core.database import Base


class RenderService(Base):
    """سرویس‌های Render"""
    __tablename__ = "render_services"

    id = Column(String(50), primary_key=True)  # srv-xxxxx
    name = Column(String(200), nullable=False)
    type = Column(String(50))  # web_service, background_worker, static_site, etc.
    region = Column(String(50))  # oregon, frankfurt, etc.
    status = Column(String(50))  # deployed, suspended, etc.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # تنظیمات
    auto_fetch_logs = Column(Boolean, default=True)  # آیا لاگ‌ها خودکار گرفته بشن
    log_retention_hours = Column(Integer, default=48)  # چند ساعت لاگ نگه داری بشه

    # آخرین دیپلوی و انتقال
    last_deploy_id = Column(String(50))  # آخرین deploy ID که fetch شده
    last_deploy_at = Column(DateTime)  # زمان آخرین deploy
    last_transferred_deploy_id = Column(String(50))  # آخرین deploy که خطاهاش منتقل شده

    # 🆕 اتصال به پروژه (دستی تنظیم می‌شود)
    project_id = Column(String(36), nullable=True, index=True)  # ID پروژه مرتبط


class RenderLog(Base):
    """لاگ‌های Render"""
    __tablename__ = "render_logs"

    id = Column(String(100), primary_key=True)  # unique log id
    service_id = Column(String(50), nullable=False, index=True)  # srv-xxxxx
    service_name = Column(String(200))  # نام سرویس برای نمایش سریع

    # محتوای لاگ
    timestamp = Column(DateTime, nullable=False, index=True)
    level = Column(String(20), index=True)  # info, warn, error, debug
    message = Column(Text)

    # متادیتا
    deploy_id = Column(String(50), index=True)  # شناسه دیپلوی مرتبط
    instance_id = Column(String(50))  # شناسه instance

    # زمان دریافت و ذخیره
    fetched_at = Column(DateTime, server_default=func.now())

    # انتقال به ایرادات
    transferred_to_issues = Column(Boolean, default=False, index=True)  # آیا به تب ایرادات منتقل شده
    transferred_at = Column(DateTime)  # زمان انتقال
    transferred_to_project = Column(String(100))  # ID پروژه مقصد

    # ایندکس‌های ترکیبی برای جستجوی سریع
    __table_args__ = (
        Index('ix_render_logs_service_timestamp', 'service_id', 'timestamp'),
        Index('ix_render_logs_level_timestamp', 'level', 'timestamp'),
    )


class RenderLogSettings(Base):
    """تنظیمات لاگ‌های Render"""
    __tablename__ = "render_log_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # تنظیمات polling
    polling_interval_seconds = Column(Integer, default=10)  # هر چند ثانیه یکبار
    polling_enabled = Column(Boolean, default=True)  # آیا polling فعال باشه

    # تنظیمات ذخیره‌سازی
    retention_hours = Column(Integer, default=48)  # چند ساعت لاگ زنده نگه داری بشه
    archive_enabled = Column(Boolean, default=True)  # آیا لاگ‌های قدیمی بایگانی بشن
    archive_retention_days = Column(Integer, default=30)  # چند روز آرشیو نگه داری بشه

    # فیلترهای پیش‌فرض
    default_log_levels = Column(String(200), default="info,warn,error")  # سطوح نمایش پیش‌فرض
    auto_scroll = Column(Boolean, default=True)  # اسکرول خودکار به آخرین لاگ

    # تنظیمات انتقال خودکار خطاها به ایرادات
    auto_transfer_enabled = Column(Boolean, default=False)  # آیا انتقال خودکار فعال باشه
    auto_transfer_interval_minutes = Column(Integer, default=30)  # هر چند دقیقه یکبار
    auto_transfer_hours_back = Column(Integer, default=24)  # چند ساعت به عقب برگرده (فقط در حالت time-based)
    # حالت‌های انتقال:
    # - since_deploy: خطاهای بعد از آخرین دیپلوی
    # - time_based: خطاهای X ساعت اخیر
    # - realtime: هر خطا فوراً منتقل شود
    auto_transfer_mode = Column(String(20), default="since_deploy")
    last_auto_transfer = Column(DateTime)  # آخرین زمان انتقال خودکار

    # =====================================================
    # 🆕 تنظیمات تریگرهای خودکار اضافی
    # =====================================================

    # تریگر تحلیل سلامت خودکار
    auto_health_analysis_enabled = Column(Boolean, default=False)
    auto_health_analysis_interval_minutes = Column(Integer, default=60)  # هر چند دقیقه
    last_auto_health_analysis = Column(DateTime)  # آخرین اجرا

    # تریگر فیلدهای پویا (sync شدن از طریق AI)
    auto_dynamic_fields_trigger_enabled = Column(Boolean, default=False)
    auto_dynamic_fields_trigger_interval_minutes = Column(Integer, default=120)  # هر 2 ساعت
    last_auto_dynamic_fields_trigger = Column(DateTime)

    # تریگر انتقال یافته‌های امنیتی به ایرادات
    auto_security_transfer_enabled = Column(Boolean, default=False)
    auto_security_transfer_interval_minutes = Column(Integer, default=60)
    last_auto_security_transfer = Column(DateTime)

    # تریگر انتقال پوشش تست به ایرادات
    auto_test_coverage_transfer_enabled = Column(Boolean, default=False)
    auto_test_coverage_transfer_interval_minutes = Column(Integer, default=60)
    last_auto_test_coverage_transfer = Column(DateTime)

    # تریگر گزارش مهندسی خودکار
    auto_engineering_report_enabled = Column(Boolean, default=False)
    auto_engineering_report_interval_minutes = Column(Integer, default=180)  # هر 3 ساعت
    last_auto_engineering_report = Column(DateTime)

    # آخرین بروزرسانی
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RenderLogArchive(Base):
    """آرشیو لاگ‌های قدیمی Render (فشرده شده)"""
    __tablename__ = "render_log_archives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String(50), nullable=False, index=True)

    # بازه زمانی
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # محتوای فشرده
    logs_count = Column(Integer, default=0)
    compressed_data = Column(Text)  # JSON فشرده شده با gzip و base64

    # متادیتا
    archived_at = Column(DateTime, server_default=func.now())
    size_bytes = Column(Integer)  # سایز داده فشرده نشده
