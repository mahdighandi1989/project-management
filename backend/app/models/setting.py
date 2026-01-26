"""
Setting Model - مدل تنظیمات
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean
from datetime import datetime

from ..core.database import Base


class Setting(Base):
    """جدول تنظیمات"""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)  # مقدار به صورت JSON یا string
    value_type = Column(String(20), default="string")  # string, json, int, bool, encrypted
    category = Column(String(50), default="general", index=True)  # general, api_keys, ai, storage, ...
    description = Column(Text)
    is_secret = Column(Boolean, default=False)  # آیا مقدار حساس است؟

    # زمان‌ها
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, hide_secrets: bool = True):
        """تبدیل به dictionary"""
        value = self.value
        if hide_secrets and self.is_secret and value:
            # فقط 4 کاراکتر آخر رو نشون بده
            value = "***" + value[-4:] if len(value) > 4 else "****"

        return {
            "key": self.key,
            "value": value,
            "value_type": self.value_type,
            "category": self.category,
            "description": self.description,
            "is_secret": self.is_secret,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_value(db, key: str, default=None):
        """دریافت مقدار یک تنظیم"""
        import json
        setting = db.query(Setting).filter(Setting.key == key).first()
        if not setting:
            return default

        value = setting.value
        if setting.value_type == "json":
            try:
                return json.loads(value)
            except:
                return default
        elif setting.value_type == "int":
            try:
                return int(value)
            except:
                return default
        elif setting.value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        return value

    @staticmethod
    def set_value(db, key: str, value, value_type: str = "string", category: str = "general",
                  description: str = None, is_secret: bool = False):
        """تنظیم مقدار"""
        import json

        # تبدیل مقدار به string
        if value_type == "json":
            str_value = json.dumps(value, ensure_ascii=False)
        elif value_type in ("int", "bool"):
            str_value = str(value)
        else:
            str_value = value

        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = str_value
            setting.value_type = value_type
            setting.category = category
            if description:
                setting.description = description
            setting.is_secret = is_secret
        else:
            setting = Setting(
                key=key,
                value=str_value,
                value_type=value_type,
                category=category,
                description=description,
                is_secret=is_secret
            )
            db.add(setting)

        db.commit()
        return setting
