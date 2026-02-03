# -*- coding: utf-8 -*-
"""
سرویس کمکی پرامپت - Prompt Helper Service

این سرویس امکان استفاده از پرامپت‌های دیتابیس را فراهم می‌کند و:
1. پرامپت‌ها را از دیتابیس می‌خواند
2. متغیرها را جایگزین می‌کند
3. اجرای پرامپت‌ها را ثبت می‌کند
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PromptHelper:
    """
    کلاس کمکی برای کار با پرامپت‌های سیستم
    """

    # کش موقت پرامپت‌ها (برای جلوگیری از کوئری‌های تکراری)
    _cache: Dict[str, Dict] = {}
    _cache_time: Dict[str, datetime] = {}
    _cache_ttl = 300  # 5 دقیقه

    @classmethod
    def get_prompt(
        cls,
        db: Session,
        category: str,
        prompt_id: str,
        variables: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        دریافت پرامپت از دیتابیس و جایگزینی متغیرها

        Args:
            db: Session دیتابیس
            category: دسته پرامپت (health_analysis, engineering_report, auto_setup)
            prompt_id: شناسه پرامپت (health_micro_analysis, etc.)
            variables: دیکشنری متغیرها برای جایگزینی
            use_cache: استفاده از کش

        Returns:
            محتوای پرامپت با متغیرهای جایگزین شده یا None
        """
        from ..models.system_prompt import SystemPrompt

        cache_key = f"{category}:{prompt_id}"

        # چک کش
        if use_cache and cache_key in cls._cache:
            cache_time = cls._cache_time.get(cache_key)
            if cache_time and (datetime.now() - cache_time).seconds < cls._cache_ttl:
                prompt_data = cls._cache[cache_key]
                return cls._apply_variables(prompt_data["content"], variables)

        # کوئری از دیتابیس
        try:
            prompt = db.query(SystemPrompt).filter(
                SystemPrompt.id == prompt_id,
                SystemPrompt.category == category,
                SystemPrompt.is_active == True
            ).first()

            if not prompt:
                # تلاش با نام
                prompt = db.query(SystemPrompt).filter(
                    SystemPrompt.category == category,
                    SystemPrompt.name.ilike(f"%{prompt_id}%"),
                    SystemPrompt.is_active == True
                ).first()

            if not prompt:
                logger.warning(f"Prompt not found: {category}/{prompt_id}")
                return None

            # ذخیره در کش
            cls._cache[cache_key] = {
                "id": prompt.id,
                "content": prompt.content,
                "variables": prompt.variables
            }
            cls._cache_time[cache_key] = datetime.now()

            return cls._apply_variables(prompt.content, variables)

        except Exception as e:
            logger.error(f"Error fetching prompt {category}/{prompt_id}: {e}")
            return None

    @classmethod
    def get_prompt_by_name(
        cls,
        db: Session,
        category: str,
        name: str,
        variables: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        دریافت پرامپت با نام

        Args:
            db: Session دیتابیس
            category: دسته پرامپت
            name: نام پرامپت
            variables: متغیرها

        Returns:
            محتوای پرامپت یا None
        """
        from ..models.system_prompt import SystemPrompt

        try:
            prompt = db.query(SystemPrompt).filter(
                SystemPrompt.category == category,
                SystemPrompt.name == name,
                SystemPrompt.is_active == True
            ).first()

            if not prompt:
                return None

            return cls._apply_variables(prompt.content, variables)

        except Exception as e:
            logger.error(f"Error fetching prompt by name {category}/{name}: {e}")
            return None

    @classmethod
    def get_all_prompts(
        cls,
        db: Session,
        category: str,
        only_active: bool = True
    ) -> List[Dict]:
        """
        دریافت تمام پرامپت‌های یک دسته

        Args:
            db: Session دیتابیس
            category: دسته پرامپت
            only_active: فقط فعال‌ها

        Returns:
            لیست پرامپت‌ها
        """
        from ..models.system_prompt import SystemPrompt

        try:
            query = db.query(SystemPrompt).filter(
                SystemPrompt.category == category
            )
            if only_active:
                query = query.filter(SystemPrompt.is_active == True)

            prompts = query.order_by(SystemPrompt.execution_order).all()
            return [p.to_dict() for p in prompts]

        except Exception as e:
            logger.error(f"Error fetching prompts for {category}: {e}")
            return []

    @classmethod
    def _apply_variables(cls, content: str, variables: Dict[str, Any] = None) -> str:
        """
        جایگزینی متغیرها در محتوای پرامپت

        Args:
            content: محتوای پرامپت
            variables: دیکشنری متغیرها

        Returns:
            محتوا با متغیرهای جایگزین شده
        """
        if not variables or not content:
            return content

        result = content
        for key, value in variables.items():
            # جایگزینی {key} با value
            placeholder = f"{{{key}}}"
            if placeholder in result:
                str_value = str(value) if value is not None else ""
                result = result.replace(placeholder, str_value)

        return result

    @classmethod
    def start_execution(
        cls,
        db: Session,
        prompt_id: str,
        project_id: str = None
    ) -> Optional[str]:
        """
        شروع ثبت اجرای پرامپت

        Args:
            db: Session دیتابیس
            prompt_id: شناسه پرامپت
            project_id: شناسه پروژه

        Returns:
            شناسه اجرا یا None
        """
        from ..models.system_prompt import PromptExecution
        import uuid

        try:
            execution_id = str(uuid.uuid4())
            execution = PromptExecution(
                id=execution_id,
                prompt_id=prompt_id,
                project_id=project_id,
                status="running",
                started_at=datetime.utcnow()
            )
            db.add(execution)
            db.commit()

            logger.info(f"🚀 Started prompt execution: {prompt_id} -> {execution_id}")
            return execution_id

        except Exception as e:
            logger.error(f"Error starting execution for {prompt_id}: {e}")
            db.rollback()
            return None

    @classmethod
    def complete_execution(
        cls,
        db: Session,
        execution_id: str,
        success: bool = True,
        result_summary: str = None,
        error_message: str = None,
        model_used: str = None,
        tokens_used: int = None
    ):
        """
        تکمیل ثبت اجرای پرامپت

        Args:
            db: Session دیتابیس
            execution_id: شناسه اجرا
            success: موفقیت
            result_summary: خلاصه نتیجه
            error_message: پیام خطا
            model_used: مدل استفاده شده
            tokens_used: توکن‌های مصرفی
        """
        from ..models.system_prompt import PromptExecution, SystemPrompt

        try:
            execution = db.query(PromptExecution).filter(
                PromptExecution.id == execution_id
            ).first()

            if not execution:
                logger.warning(f"Execution not found: {execution_id}")
                return

            execution.status = "completed" if success else "failed"
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                execution.duration_seconds = int(
                    (execution.completed_at - execution.started_at).total_seconds()
                )
            execution.result_summary = result_summary
            execution.error_message = error_message
            execution.model_used = model_used
            execution.tokens_used = tokens_used

            # به‌روزرسانی آمار پرامپت
            prompt = db.query(SystemPrompt).filter(
                SystemPrompt.id == execution.prompt_id
            ).first()
            if prompt:
                prompt.usage_count = (prompt.usage_count or 0) + 1
                if success:
                    prompt.success_count = (prompt.success_count or 0) + 1
                prompt.last_used_at = datetime.utcnow()
                if error_message:
                    prompt.last_error = error_message

            db.commit()
            logger.info(f"✅ Completed prompt execution: {execution_id} (success={success})")

        except Exception as e:
            logger.error(f"Error completing execution {execution_id}: {e}")
            db.rollback()

    @classmethod
    def get_active_executions(cls, db: Session, project_id: str = None) -> List[Dict]:
        """
        دریافت اجراهای فعال

        Args:
            db: Session دیتابیس
            project_id: شناسه پروژه (اختیاری)

        Returns:
            لیست اجراهای فعال
        """
        from ..models.system_prompt import PromptExecution

        try:
            query = db.query(PromptExecution).filter(
                PromptExecution.status == "running"
            )
            if project_id:
                query = query.filter(PromptExecution.project_id == project_id)

            executions = query.order_by(PromptExecution.started_at.desc()).all()
            return [e.to_dict() for e in executions]

        except Exception as e:
            logger.error(f"Error fetching active executions: {e}")
            return []

    @classmethod
    def clear_cache(cls, category: str = None, prompt_id: str = None):
        """
        پاک کردن کش

        Args:
            category: دسته (اختیاری)
            prompt_id: شناسه پرامپت (اختیاری)
        """
        if category and prompt_id:
            cache_key = f"{category}:{prompt_id}"
            cls._cache.pop(cache_key, None)
            cls._cache_time.pop(cache_key, None)
        elif category:
            keys_to_remove = [k for k in cls._cache.keys() if k.startswith(f"{category}:")]
            for key in keys_to_remove:
                cls._cache.pop(key, None)
                cls._cache_time.pop(key, None)
        else:
            cls._cache.clear()
            cls._cache_time.clear()

    @classmethod
    def get_ordered_prompts_for_execution(
        cls,
        db: Session,
        category: str,
        only_required: bool = False
    ) -> List[Dict]:
        """
        🔴 دریافت پرامپت‌های یک دسته به ترتیب execution_order برای اجرای متوالی

        Args:
            db: Session دیتابیس
            category: دسته پرامپت
            only_required: فقط پرامپت‌های اجباری

        Returns:
            لیست پرامپت‌ها مرتب شده بر اساس execution_order
        """
        from ..models.system_prompt import SystemPrompt

        try:
            query = db.query(SystemPrompt).filter(
                SystemPrompt.category == category,
                SystemPrompt.is_active == True
            )

            if only_required:
                query = query.filter(SystemPrompt.is_required == True)

            # مرتب‌سازی بر اساس execution_order
            prompts = query.order_by(SystemPrompt.execution_order.asc()).all()

            return [p.to_dict() for p in prompts]

        except Exception as e:
            logger.error(f"Error fetching ordered prompts for {category}: {e}")
            return []

    @classmethod
    def execute_prompts_in_order(
        cls,
        db: Session,
        category: str,
        project_id: str,
        executor_func,
        variables: Dict[str, Any] = None,
        only_required: bool = False
    ) -> List[Dict]:
        """
        🔴 اجرای پرامپت‌ها به ترتیب execution_order

        Args:
            db: Session دیتابیس
            category: دسته پرامپت
            project_id: شناسه پروژه
            executor_func: تابع اجرا کننده (async یا sync)
            variables: متغیرها برای جایگزینی
            only_required: فقط اجباری‌ها

        Returns:
            لیست نتایج اجرا
        """
        import json

        prompts = cls.get_ordered_prompts_for_execution(db, category, only_required)
        results = []

        for prompt in prompts:
            prompt_id = prompt.get("id")

            # بررسی وابستگی‌ها
            depends_on = prompt.get("depends_on", [])
            if isinstance(depends_on, str):
                try:
                    depends_on = json.loads(depends_on)
                except:
                    depends_on = []

            # چک کن آیا وابستگی‌ها موفق بودند
            if depends_on:
                dependencies_met = True
                for dep_id in depends_on:
                    dep_result = next(
                        (r for r in results if r.get("prompt_id") == dep_id),
                        None
                    )
                    if not dep_result or not dep_result.get("success"):
                        dependencies_met = False
                        logger.warning(f"Dependency {dep_id} not met for prompt {prompt_id}")
                        break

                if not dependencies_met:
                    results.append({
                        "prompt_id": prompt_id,
                        "prompt_name": prompt.get("name"),
                        "success": False,
                        "skipped": True,
                        "reason": "وابستگی‌ها برآورده نشدند"
                    })
                    continue

            # شروع اجرا
            execution_id = cls.start_execution(db, prompt_id, project_id)

            try:
                # جایگزینی متغیرها در محتوا
                content = prompt.get("content", "")
                if variables:
                    content = cls._apply_variables(content, variables)

                # فراخوانی تابع اجرا
                result = executor_func(prompt_id, content, prompt)

                # تکمیل اجرا
                cls.complete_execution(
                    db=db,
                    execution_id=execution_id,
                    success=True,
                    result_summary=f"اجرا شد: {prompt.get('name')}"
                )

                results.append({
                    "prompt_id": prompt_id,
                    "prompt_name": prompt.get("name"),
                    "execution_order": prompt.get("execution_order"),
                    "success": True,
                    "result": result
                })

            except Exception as e:
                cls.complete_execution(
                    db=db,
                    execution_id=execution_id,
                    success=False,
                    error_message=str(e)
                )

                results.append({
                    "prompt_id": prompt_id,
                    "prompt_name": prompt.get("name"),
                    "success": False,
                    "error": str(e)
                })

        return results


# Singleton instance
_prompt_helper = None


def get_prompt_helper() -> PromptHelper:
    """دریافت instance پرامپت هلپر"""
    global _prompt_helper
    if _prompt_helper is None:
        _prompt_helper = PromptHelper()
    return _prompt_helper
