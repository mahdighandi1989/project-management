# -*- coding: utf-8 -*-
"""
🚀 API Routes برای لاگ‌های Render

امکانات:
- دریافت لیست سرویس‌ها
- دریافت لاگ‌های زنده
- فیلتر و جستجو
- تنظیمات polling
- آرشیو و بازیابی
- WebSocket برای streaming واقعی
"""

import json
import logging
import os
import re
import uuid
import traceback
import hashlib
import time as _time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from ...core.database import get_db
from ...core.logging_utils import StructuredLogger
from ...services.render_service import get_render_service, reset_render_service
from ...models.render_log import RenderLog, RenderService, RenderLogSettings, RenderLogArchive

slog = StructuredLogger(__name__, "RENDER-API")

# 🐛 (C7v2 Section 8 — logger NameError fix) — قبلاً logger در سطح module
# تعریف نشده بود و helper های جدید (_build_task_context_block, ...) که از
# logger.warning/info/debug استفاده می‌کنند، در multi-step execution NameError
# می‌دادند. این تعریف برای دسترسی کل توابع ماژول الزامی است.
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/render", tags=["Render Logs"])

# ── Background Batch Tasks — پردازش مستقل از SSE ──────────────────
# وقتی کاربر از صفحه خارج بشه یا اتصال قطع بشه، پردازش متوقف نمیشه.
# SSE فقط "ناظر" هست — task اصلی تو بک‌گراند اجرا میشه.
import asyncio as _asyncio

_BATCH_TASKS: Dict[str, Dict[str, Any]] = {}
_BATCH_TASKS_TTL = 1800  # ۳۰ دقیقه


def _batch_task_key(project_id: str, message: str, file_paths: list) -> str:
    """ساخت کلید یکتا برای background task"""
    raw = f"{project_id}:{message}:{','.join(sorted(file_paths[:50]))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _get_batch_task(key: str) -> Optional[Dict[str, Any]]:
    """گرفتن task موجود (اگه فعال یا تازه تموم شده باشه)"""
    entry = _BATCH_TASKS.get(key)
    if entry and _time.time() - entry.get("created_at", 0) < _BATCH_TASKS_TTL:
        return entry
    if key in _BATCH_TASKS:
        # پاکسازی task منقضی‌شده
        task = entry.get("task")
        if task and not task.done():
            task.cancel()
        del _BATCH_TASKS[key]
    return None


# ── منبع حقیقت واحد برای دستورات عمومی سیستم ──────────────────────
# هر تغییر در این تابع، هم در فرانت (پنل دستورات) و هم در پرامپت مدل‌ها
# خودکار منعکس میشه — نیازی به آپدیت جداگانه نیست.
def _build_general_instructions_list(
    project_name: str = "نامشخص",
    technologies: str = "نامشخص",
    github_path: str = "نامشخص"
) -> list:
    """
    لیست کامل دستورات عمومی سیستم.
    ⚠️ این تابع تنها منبع حقیقت (single source of truth) است:
    - اندپوینت /general-instructions ازش استفاده میکنه (نمایش در فرانت)
    - general_instructions_text ازش ساخته میشه (تزریق در پرامپت مدل‌ها)
    هر تغییری اینجا بدی، خودکار همه جا منعکس میشه.
    """
    return [
        {
            "id": "sys_language",
            "title": "زبان پاسخ‌دهی",
            "content": "به فارسی پاسخ بده. کدها و اصطلاحات فنی می‌توانند انگلیسی باشند.",
            "icon": "🗣️",
            "prompt_detail": "به فارسی پاسخ بده. کدها و اصطلاحات فنی می‌توانند انگلیسی باشند.",
        },
        {
            "id": "sys_project",
            "title": "شناخت پروژه",
            "content": f"نام پروژه: {project_name}\nتکنولوژی‌ها: {technologies}\nGitHub: {github_path}",
            "icon": "📂",
            "prompt_detail": f"نام پروژه: {project_name}\nتکنولوژی‌ها: {technologies}\nGitHub: {github_path}",
        },
        {
            "id": "sys_analysis",
            "title": "روش تحلیل",
            "content": "مستقیماً تحلیل کن و راه‌حل عملی ارائه بده. هرگز از کاربر نخواه کار دستی انجام دهد. اگر مشکلی گزارش شده، مستقیماً در کد بررسی کن.",
            "icon": "🔍",
            "prompt_detail": """- مستقیماً تحلیل کن و راه‌حل عملی ارائه بده
- هرگز از کاربر نخواه کار دستی انجام دهد (مثل grep، بررسی فایل، اجرای دستور)
- اگر مشکلی گزارش شده، مستقیماً در کد بررسی کن و راه‌حل ارائه بده""",
        },
        {
            "id": "sys_intent",
            "title": "درک منظور کاربر",
            "content": "کاربران ممکن است غیرمستقیم، کوتاه یا عامیانه بنویسند. همیشه منظور واقعی را از context مکالمه بفهم.",
            "icon": "🧠",
            "prompt_detail": """- کاربران ممکن است غیرمستقیم، کوتاه یا عامیانه بنویسند
- همیشه منظور واقعی کاربر را از context مکالمه بفهم
- اگر پیام مبهم است (مثل "آره"، "همونه")، تاریخچه مکالمه را بخوان""",
        },
        {
            "id": "sys_compat",
            "title": "سازگاری با پروژه",
            "content": "از سبک کدنویسی موجود پیروی کن. تغییرات باید با ساختار فعلی سازگار باشد. وابستگی‌ها را بررسی کن.",
            "icon": "⚙️",
            "prompt_detail": """- از سبک کدنویسی موجود در پروژه پیروی کن
- تغییرات باید با ساختار فعلی پروژه سازگار باشد
- تمام وابستگی‌ها (imports, types, configs) را بررسی کن""",
        },
        {
            "id": "sys_retry_depth",
            "title": "تحلیل عمیق‌تر در هر تلاش مجدد",
            "content": "اگر مشکلی بعد از فیکس قبلی باقی ماند: ۱) دامنه بررسی را وسیع‌تر کن (فایل‌های جدید) ۲) زنجیره وابستگی را دنبال کن (route→service→model→config) ۳) ریشه‌یابی کن چرا فیکس قبلی کار نکرد ۴) فایل‌های نادیده‌گرفته‌شده مثل config, types, .env, middleware را بررسی کن ۵) هرگز همان راه‌حل را تکرار نکن — رویکرد متفاوت امتحان کن",
            "icon": "🔴",
            "prompt_detail": """اگر کاربر بعد از پاسخ قبلی تو دوباره مشکل مشابه را مطرح کرد (مثل «هنوز خطا میده»، «نشد»، «بازم همونه»، «درست نشد»):
1. **فیکس قبلی ناکافی بوده** — فقط تکرار یا اصلاح جزئی همان فایل‌ها کافی نیست
2. **دامنه بررسی را وسیع‌تر کن**: فایل‌های جدید و مرتبط که قبلاً بررسی نشده‌اند
3. **زنجیره وابستگی را دنبال کن**:
   - اگر فرانت خطا دارد → فقط کامپوننت نه، API endpoint → service → model → DB همه رو ببین
   - اگر بکند خطا دارد → فقط route نه، middleware → config → .env → imports همه رو ببین
4. **ریشه‌یابی کن**: قبل از نوشتن کد، تحلیل کن چرا فیکس قبلی کار نکرد
5. **فایل‌هایی که معمولاً نادیده گرفته میشن**: tsconfig.json, vite.config, next.config, .env, package.json, types/interfaces, middleware, interceptors, guards
6. **هرگز** همان راه‌حل را با تغییر جزئی تکرار نکن — اگر یک رویکرد جواب نداد، رویکرد متفاوت امتحان کن""",
        },
        {
            "id": "sys_no_guess",
            "title": "ممنوعیت مطلق حدس‌زنی و ممنوعیت درخواست ارسال مجدد",
            "content": "سیستم هوشمند مرتبط‌ترین فایل‌ها را از کل مخزن خوانده و در اختیارت گذاشته. همیشه با همین فایل‌ها کار کن و action_plan بنویس. هرگز نگو «فایل در اختیارم نیست» یا «دوباره ارسال کنید». اگر فایلی نیست، یعنی وجود نداره — آن را create کن.",
            "icon": "🔑",
            "prompt_detail": """🔑 **قانون مطلق — بدون استثنا:**
سیستم هوشمند، مرتبط‌ترین فایل‌های پروژه را از کل مخزن انتخاب و خوانده و در اختیار تو گذاشته.
**تو باید همیشه با همین فایل‌ها کار کنی و action_plan تولید کنی.**

⛔ **عبارات ممنوعه (هرگز از هیچ‌کدام استفاده نکن):**
- «دسترسی ندارم» / «در اختیار من نیست» / «در اختیارم قرار نگرفته»
- «این فایل خوانده نشده» / «محتوای فایل X را ندارم»
- «دوباره ارسال کنید» / «دوباره بپرسید» / «دوباره تلاش کنید»
- «سیستم هوشمند این فایل را نداده» / «فایل‌های فرانت‌اند در اختیارم نیست»
- «نیاز به بررسی محتوای فایل‌ها دارم» / «قادر به نوشتن action_plan نیستم»
- «لطفاً فایل X را هم بخوانید» / «لطفاً دوباره درخواست دهید»
- «فرض می‌کنیم» / «احتمالاً محتوایش اینه» / «ساختارش باید اینطوری باشه»

✅ **به جای آن، این کار را بکن:**
- فایل‌هایی که محتوایشان را می‌بینی → مستقیماً در action_plan با operation: "update" بگذار
- فایل‌هایی که وجود ندارند یا محتوایشان نیست → با operation: "create" بساز (بر اساس الگوهای پروژه و دانشت)
- **همیشه** action_plan تولید کن — حتی اگر فکر می‌کنی اطلاعات کافی نیست، بهترین راه‌حل ممکن با فایل‌های موجود را بنویس
- اگر واقعاً فایل مهمی کم است، آن را به عنوان «نکته» در متن تحلیل ذکر کن (مثلاً «💡 برای دقت بیشتر، فایل X هم مفید بود») ولی **باز هم action_plan کامل بنویس**""",
        },
        {
            "id": "sys_holistic_fix",
            "title": "حل کامل و یکجا — نه تکه‌تکه",
            "content": "قبل از نوشتن هر تغییر، کل زنجیره وابستگی را ردیابی کن. تمام فایل‌های config مرتبط (package.json, tsconfig, postcss.config, vite.config) را بررسی کن. نسخه پکیج‌ها فقط از فایل‌های موجود پروژه یا دانش قطعی. هرگز یک مشکل را نیمه‌کاره حل نکن.",
            "icon": "🎯",
            "prompt_detail": """## ⛔ ممنوعیت حل تکه‌تکه — هر تغییر باید کامل و نهایی باشد
قبل از نوشتن action_plan، این مراحل را **حتماً** طی کن:

### ۱) ردیابی زنجیره وابستگی (Dependency Chain Tracing):
- اگر `postcss.config.js` تغییر میکنه → حتماً `package.json` (فیلد "type") و `tailwind.config` و `vite.config` هم بررسی شود
- اگر `package.json` تغییر میکنه → حتماً سازگاری نسخه‌ها بین تمام وابستگی‌ها بررسی شود
- اگر `requirements.txt` تغییر میکنه → حتماً سازگاری با Python version و Dockerfile بررسی شود
- اگر `Dockerfile` تغییر میکنه → حتماً build context و مسیر فایل‌ها و deploy scripts بررسی شود

### ۲) بررسی متقابل فایل‌های Config (Cross-Reference):
- قبل از نوشتن هر فایل config:
  ⚠️ اگر `package.json` دارای `"type": "module"` باشه → فایل‌های `.js` باید ESM syntax (export default) باشند، نه CJS (module.exports)
  ⚠️ اگر `package.json` دارای `"type": "module"` نباشه → CJS مجاز ولی ESM هم کار میکنه
  ⚠️ اگر فایل `.mjs` هست → حتماً ESM
  ⚠️ اگر فایل `.cjs` هست → حتماً CJS
- قبل از تغییر هر وابستگی → فایل lock (package-lock.json, yarn.lock) و سایر وابستگی‌ها را بررسی کن

### ۳) نسخه پکیج‌ها — فقط نسخه‌های تأیید شده:
- ⛔ هرگز نسخه‌ای پین نکن که مطمئن نیستی وجود دارد
- ✅ نسخه‌ای که در package.json یا lock file فعلی پروژه هست → مجاز
- ✅ نسخه‌ای که دقیقاً از دانش قبلی‌ات (training data) مطمئنی وجود دارد → مجاز
- ⛔ نسخه‌ای که حدس میزنی شاید وجود داشته باشه → ممنوع — به جایش بنویس "نسخه سازگار X.Y.Z" یا range مثل "^X.Y.Z" بذار
- ✅ اگر مطمئن نیستی، از caret range (^) استفاده کن که خودش نسخه سازگار را resolve میکنه

### ۴) شبیه‌سازی ذهنی کل مسیر:
قبل از نوشتن action_plan، ذهنی این سؤالات را بررسی کن:
1. آیا بعد از اعمال تمام فایل‌های action_plan، اپلیکیشن بدون خطا build و deploy میشه؟
2. آیا هیچ فایل config دیگری هست که باید آپدیت بشه ولی فراموش شده؟
3. آیا نسخه‌های وابستگی‌ها با هم سازگارند؟ (مثلاً Tailwind v3 vs v4 plugins متفاوتی دارند)
4. آیا module system سازگاره؟ (ESM vs CJS)
5. آیا تغییر من مشکل جدیدی ایجاد نمیکنه؟""",
        },
        {
            "id": "sys_deploy_safe",
            "title": "محافظت از بیلد و دیپلوی",
            "content": "کد تولیدی باید بدون خطای سینتکس، تایپ و import باشد. قبل از نوشتن action_plan، ذهنی بیلد و کامپایل را شبیه‌سازی کن. تمام import/export ها، پرانتزها، آکولادها، و تایپ‌ها را چک کن. هرگز فایل ناقص یا نیمه‌کاره تحویل نده.",
            "icon": "🏗️",
            "prompt_detail": """- 🔴 کد تولیدی باید مستقیماً بیلد و دیپلوی شود بدون هیچ خطایی — هر خطای سینتکس = شکست دیپلوی
- قبل از نوشتن content هر فایل در action_plan، ذهنی مراحل بیلد را شبیه‌سازی کن:
  ۱) آیا تمام import ها درست هستند؟ (مسیر، نام، default vs named)
  ۲) آیا تمام پرانتزها () و آکولادها {} و براکت‌ها [] بسته شده‌اند؟
  ۳) آیا هیچ متغیر، تابع یا تایپ undefined استفاده نشده؟
  ۴) آیا export ها با import های فایل‌های دیگر سازگارند؟
  ۵) آیا TypeScript types و interfaces صحیح هستند؟
  ۶) آیا JSON ها valid هستند (کاما اضافی، کاما کم)؟
  ۷) آیا JSX tags همه بسته شده‌اند؟
  ۸) آیا async/await درست استفاده شده؟
- محتوای هر فایل در action_plan باید **کامل و قابل جایگزینی** باشد — نه تکه‌ای از فایل
- 🔴 **تمام** فایل‌ها و content/sections باید **داخل** یک بلوک JSON باشد. کد رو جدا از action_plan ننویس!
- هرگز «// ... بقیه کد» یا «// rest of file» ننویس — محتوای کامل بده
- 🔴 **فایل‌های بزرگ (>200 خط)**: اگر فایلی بیش از ۲۰۰ خط دارد → **الزامی** است از `modify_sections` استفاده کنی (بازنویسی کامل فایل ممنوع و خودکار حذف میشه!):
  - ✅ **روش اجباری: از `modify_sections` استفاده کن** (بازنویسی کل فایل ممنوع):
    ```json
    {"path": "path/to/file.tsx", "operation": "modify_sections", "sections": [
      {"find": "متن دقیق بخشی از فایل اصلی", "replace": "متن جایگزین"},
      {"find": "بخش دوم فایل اصلی", "replace": "جایگزین دوم"}
    ], "description": "توضیح تغییرات"}
    ```
  - `find` = متن **COPY-PASTE دقیق** از فایل اصلی (حداقل ۲-۳ خط کامل و یکتا)
  - `replace` = متن جایگزین (میتونه کمتر/بیشتر/خالی باشه)
  - سیستم خودش فایل اصلی رو از ریپو میخونه و sections رو اعمال میکنه
  - 🔴 مزیت: هیچ بخشی از فایل اصلی حذف نمیشه — فقط بخش‌های مشخص‌شده تغییر میکنن
  - اگر بخواهی بخشی رو **حذف** کنی: `"replace": ""` (خالی)
  - اگر بخواهی بخشی رو **اضافه** کنی: `find` = خط قبل از محل اضافه، `replace` = همان خط + کد جدید
  - 🔴🔴🔴 `find` باید **دقیقاً** مطابق متن فایل اصلی باشد — شامل فاصله‌ها، tab ها، indentation و حتی کامنت‌ها
  - ⛔ **هرگز find رو حدس نزن** — حتماً از متن فایل که بالاتر آمده COPY کن — حتی ۱ کاراکتر فرق = شکست
  - ✅ find رو بزرگ‌تر بگیر (۵-۱۰ خط) تا شانس تطبیق بالا بره — خط کوتاه ممکنه تکراری باشه
  - اگر operation = "modify" استفاده کنی → content خروجی باید تعداد خطوطش **مشابه** فایل اصلی باشد (±۱۰٪)
  - ❌ اگر فایل ۱۰۰۰ خط داره و خروجی تو ۱۰۰ خطه → حتماً بخش بزرگی حذف شده — ممنوع!
  - سیستم خودکار فایل‌هایی که کمتر از ۵۰٪ فایل اصلی باشند رو **حذف** میکنه
- تمام وابستگی‌های بین فایلی را بررسی کن: اگر یک interface تغییر کرد، همه فایل‌های مصرف‌کننده باید آپدیت شوند

🔴 قوانین خاص فایل‌های زیرساختی (Dockerfile, deploy scripts, package.json, requirements.txt):
- ⛔ هرگز فایل‌های deploy script (deploy.sh, cloudbuild.yaml و...) را کامل بازنویسی نکن — فقط خط‌های مشکل‌دار را تغییر بده
- ⛔ قبل از تغییر Dockerfile، حتماً بفهم build context کجاست (از اسکریپت‌های deploy بررسی کن)
- ⛔ اگر Dockerfile در پوشه backend/ هست و build context هم backend/ هست، مسیرها نسبت به backend باشند (مثلاً `COPY requirements.txt .` نه `COPY backend/requirements.txt .`)
- ⛔ تمام وابستگی‌ها در package.json و requirements.txt باید با نسخه سازگار پین شوند
- ⛔ هرگز نسخه‌ای پین نکن که مطمئن نیستی وجود دارد — فقط از نسخه‌های موجود در فایل‌های پروژه یا دانش قطعی استفاده کن
- ⛔ اگر نسخه پکیجی تغییر می‌کنه، بررسی کن با سایر وابستگی‌ها سازگار هست — Tailwind v3 plugins با Tailwind v4 متفاوتند
- ⛔ قبل از نوشتن هر فایل config جاوااسکریپتی، حتماً `package.json` فیلد `"type"` را بررسی کن — اگر `"type": "module"` هست باید ESM syntax بنویسی
- ⛔ هرگز فایل TypeScript/JavaScript معتبر رو با محتوای JSON جایگزین نکن — اگر فایل .ts هست، content باید کد TypeScript باشه نه JSON
- ⛔ هرگز یک مشکل رو نیمه‌کاره حل نکن — اگر postcss.config.js تغییر میکنه، package.json و vite.config.ts هم بررسی بشن""",
        },
        {
            "id": "sys_preserve_existing",
            "title": "ممنوعیت بازنویسی مخرب — حفظ تمام قابلیت‌های موجود",
            "content": "هرگز فایل موجود را از صفر بازننویس. فقط بخش‌هایی که مستقیماً مربوط به درخواست کاربر هستند تغییر بده. تمام قابلیت‌ها، UI، استایل‌ها و منطق موجود باید حفظ شوند. قبل از ایجاد فایل جدید، بررسی کن آیا کامپوننت مشابه وجود داره.",
            "icon": "🛡️",
            "prompt_detail": """## 🛡️ قانون حیاتی: ممنوعیت بازنویسی مخرب (Destructive Rewrite)

### ⛔ ممنوعیت‌های مطلق:
1. **هرگز یک فایل موجود را از صفر بازننویس** — حتی اگر فکر کنی ساختار بهتری داری
   - اگر فایل MonitoringPage.tsx دارای حساب معاملاتی، فیلتر، جدول و ۳۰۰ خط کد است → تغییرات تو باید فقط بخش مربوط به درخواست کاربر را عوض کند — **نه کل فایل**
   - اگر فایل ۵۰۰ خط دارد و تو فقط ۲۰ خط تغییر میدهی → content باید همان ۵۰۰ خط باشد با ۲۰ خط تغییر‌یافته
   - 🔴 **قانون عددی**: تعداد خطوط content خروجی تو باید حداقل ۸۰٪ تعداد خطوط فایل اصلی باشد. اگر فایل اصلی ۱۰۰۰ خط دارد، content تو نباید کمتر از ۸۰۰ خط باشد. **سیستم خودکار فایل‌هایی با کمتر از ۵۰٪ خطوط اصلی رو حذف میکنه!**

2. **هرگز قابلیت‌های موجود را حذف نکن** مگر کاربر صراحتاً خواسته باشد:
   - ❌ اگر صفحه‌ای دارای بخش‌های A, B, C, D است و کاربر خواسته C رو عوض کنی → A, B, D باید دست‌نخورده بمانند
   - ❌ اگر کامپوننتی state, event handler, useEffect, API call دارد → هیچ‌کدام حذف نشوند مگر بخشی از درخواست باشد
   - ❌ استایل‌ها، کلاس‌های CSS، آیکون‌ها، المان‌های UI که به درخواست مربوط نیستند → حذف ممنوع

3. **قبل از ایجاد فایل جدید (operation: "create")، حتماً بررسی کن:**
   - آیا کامپوننت یا فایل مشابهی در پروژه وجود دارد؟ (ساختار پروژه رو بخون)
   - آیا عملکرد مورد نظر قبلاً پیاده‌سازی شده؟
   - ❌ ایجاد `TradingViewWidget.tsx` وقتی از قبل وجود داره → ممنوع
   - ❌ ایجاد فایل CSS جدید وقتی پروژه از Tailwind استفاده میکنه → ممنوع (مگر دلیل فنی خاص)

4. **هرگز عملکرد واقعی را با placeholder جایگزین نکن:**
   - ❌ iframe کاری که دکمه‌ها و URL واقعی داره → جایگزین با div خالی و متن «اینجا ویجت قرار خواهد گرفت» = ممنوع
   - ✅ اگر iframe واقعی از قبل هست → آن را حفظ کن و فقط مشکلش رو رفع کن

### ✅ روش صحیح تغییر فایل موجود:
1. کل محتوای فعلی فایل را بخوان و درک کن
2. **فقط** بخش‌های مربوط به درخواست را تغییر بده
3. باقی فایل (imports, state, handlers, UI sections, styles) را دقیقاً مثل اصل حفظ کن
4. content نهایی = فایل اصلی + تغییرات تو (نه فایل جدید از صفر)

### 🔧 modify_sections — **الزامی** برای فایل‌های بزرگ:
- برای فایل‌های **بیش از ۲۰۰ خط** → **حتماً** از `operation: "modify_sections"` استفاده کن (سیستم بازنویسی‌های مخرب رو خودکار حذف میکنه!)
- بجای نوشتن کل محتوای فایل، فقط بخش‌های تغییریافته رو مشخص کن:
  ```json
  {"path": "file.tsx", "operation": "modify_sections", "sections": [
    {"find": "متن دقیق از فایل اصلی", "replace": "متن جایگزین"}
  ]}
  ```
- سیستم خودش فایل اصلی رو میخونه و فقط بخش‌های مشخص‌شده رو عوض میکنه
- ✅ برای اضافه کردن import: `find` = آخرین import موجود، `replace` = همان import + import جدید
- ✅ برای حذف: `"replace": ""`
- ⚠️ اگر **کل فایل** باید تغییر کنه (>50% محتوا) → از `modify` معمولی استفاده کن
- ⚠️ `find` باید **دقیقاً** مطابق متن اصلی باشد (whitespace و indentation شامل)

### 🔄 قانون ویژه multi-step (اجرای مرحله‌ای):
- اگر در پرامپت «فایل‌های تغییر یافته تا الان» آمده → **محتوای آن‌ها خروجی مراحل قبلی است**
- اگر فایلی در مرحله قبل تغییر یافته و در مرحله فعلی هم باید تغییر کنه → **تمام محتوای مرحله قبل حفظ شود** + تغییرات جدید اضافه شود
- ❌ هرگز فایل مرحله قبل را دور بینداز و از صفر بنویس
- ❌ URL‌ها، API baseها، نام event‌ها، نام متغیرها: **دقیقاً مثل مراحل قبلی** — تغییر ندهید
- ✅ content مرحله فعلی = content مرحله قبل + تغییرات جدید

### 🚨 قانون حیاتی: stack-traced files — هرگز skip نکن
اگر در پیام کاربر یا backend_logs یک stack trace هست (مثل
`File "/opt/render/project/src/app/main.py", line 32`):
- **آن فایل تقریباً قطعاً مشکل دارد** — به‌جز موارد بسیار نادر
- **هرگز** بدون **نقل‌قول محتوای فعلی** آن فایل نگو «صحیح است» یا «نیازی به تغییر ندارد»
- اگر محتوای فعلی فایل کد مشکل‌دار (مثل خط ۳۲ که error می‌دهد) را همچنان دارد → **حتماً** در action_plan آن را تغییر بده
- اگر AI قبلی (مرحله قبل) گفت «این فایل درست است» ولی کد مشکل‌دار همچنان موجود است → اعتماد نکن و فایل را در این مرحله fix کن
- مثال غلط: «`app/main.py` صحیح است، نیازی به تغییر ندارد» (در حالی که خط ۳۲ همچنان `async with engine.begin()` دارد)
- مثال درست: «خط ۳۲ `app/main.py` همچنان `engine.begin()` می‌زند، باید به `init_db()` تبدیل شود — این change را در action_plan قرار می‌دهم.»

### 🚨 قانون حیاتی: log حقیقت است، توصیف کاربر نه
- اگر backend_logs یا log در پیام، یک error trace واقعی دارد، **اول
  log را به دقت بخوان** قبل از پذیرش description کاربر
- کاربر ممکن است error قبلی session را تکرار کند، یا نام package اشتباه
  بنویسد. **log منبع حقیقت است**
- مثال غلط: کاربر می‌گوید «pydantic-core fail شد» ولی log می‌گوید
  `Failed to build tiktoken` → AI روی pydantic-core کار می‌کند
- مثال درست: «در پیام کاربر pydantic-core ذکر شده ولی log جدید tiktoken
  را نشان می‌دهد — مشکل واقعی tiktoken است.»

### 🚨 قانون حیاتی: Render env var ها (DATABASE_URL، API_KEY و …)
اگر مشکل از **متغیر محیطی** در Render است (نه از کد):
- مثال: `ConnectionRefusedError` به دلیل `DATABASE_URL` تنظیم‌نشده
- مثال: `KeyError: 'API_KEY'` به دلیل API_KEY missing
- در این موارد، **علاوه بر تغییرات کد** (اگر لازم است fallback اضافه شود)،
  می‌توانی در action_plan فیلد `render_actions` اضافه کنی:

```json
{
  "files": [...],
  "render_actions": [
    {
      "type": "set_env_var",
      "service_name": "نام_دقیق_سرویس_در_Render",
      "key": "DATABASE_URL",
      "value": "postgresql+asyncpg://..."
    },
    {"type": "restart_service", "service_name": "..."},
    {"type": "trigger_deploy", "service_name": "...", "clear_cache": false}
  ]
}
```

- `set_env_var`: تنظیم یا به‌روزرسانی یک env var
- `set_env_vars_bulk`: چندتایی با `{"vars": {"K1": "v1", "K2": "v2"}}`
- `restart_service`: restart سرویس بدون deploy جدید
- `trigger_deploy`: deploy جدید
- `service_name`: نام دقیق سرویس در Render (مثلاً `lifemanager`)
- این operations **بعد از file commits** اجرا می‌شوند
- اگر مقدار `value` را نمی‌دانی، از کاربر بپرس یا یک placeholder بگذار
- ⛔ هرگز در `value` راز/credentials واقعی نگذار اگر در پیام کاربر نیست

### 🚨 قانون حیاتی: قبل از create، چک کن فایل از قبل موجود است
هرگز قبل از چک کردن، `operation: "create"` نگذار:
- **اگر فایل در repo از قبل موجود است**: عملیات باید `modify` باشد.
  حتی اگر کاربر گفت «بساز» — منظورش معمولاً «به‌روزرسانی کن» است
- **مثال غلط 1**: کاربر می‌گوید «runtime.txt بساز با python-3.12.7»،
  AI با `operation=create` فایل را overwrite می‌کند، **محتوای فعلی
  (python-3.11.10) گم می‌شود**. اگر در دفعهٔ قبلی کاربر این فایل را
  ساخته بود، این نسخه‌برگشت محسوب می‌شود.
- **مثال درست**: قبل از تولید content، چک کن آیا فایل در repo هست:
  - بله → operation=modify، content جدید را با حفظ ساختار قبلی بساز
  - خیر → operation=create
- **همینطور برای requirements.txt، Dockerfile و …**: همیشه نسخه‌ای که
  در repo هست را در نظر بگیر. اگر در فایل‌های `previously_read_files`
  هست، محتوای آن را در content جدید شامل کن (حفظ + تغییر هدف، نه
  بازنویسی از صفر)
- اگر مطمئن نیستی فایل موجود است یا نه، **در analysis ذکر کن**:
  «در action_plan فرض می‌کنم runtime.txt موجود نیست — اگر موجود است،
  لطفاً به جای create از modify استفاده شود.»

### 🚨🚨 قانون حیاتی: هرگز محتوای فایلی که نخوانده‌ای را حدس نزن
- **هرگز** نگو «فایل X خالی است» مگر اینکه محتوای واقعی آن را **دیده** باشی
  و واقعاً خالی باشد. اگر فایل را ندیده‌ای، یعنی نمی‌دانی خالی است یا نه.
- **مثال غلط (که اتفاق افتاده)**: مدل گفت «requirements.txt خالی است،
  package.json خالی است، index.html خالی است» و آن‌ها را با محتوای **حدسی**
  پر کرد — در حالی که این فایل‌ها محتوای واقعی داشتند و overwrite شدند.
- **قانون**: اگر باید فایلی را `modify` کنی که محتوایش را در این تحلیل
  نخوانده‌ای:
  - **گزینهٔ درست**: در analysis بنویس «برای اصلاح X نیاز دارم محتوای فعلی
    آن را ببینم» — و آن فایل را در action_plan **نگذار** (سیستم آن را به‌خاطر
    overwrite کور reject می‌کند).
  - یا اگر فقط یک تغییر کوچک لازم است، از `modify_sections` با find/replace
    دقیق استفاده کن (نه content کامل).
- ⛔ سیستم به‌صورت خودکار هر فایلی را که `operation=modify` با content کامل
  دارد ولی خوانده نشده و در repo موجود است، **reject می‌کند** — پس content
  حدسی بی‌فایده است. اول فایل را بخوان.

### 🚨 قانون حیاتی: Python wheel/cp31X compile errors در Render
اگر log شامل `Read-only file system` در `/usr/local/cargo/` یا
`Failed to build wheel for ...` در deploy Python:
- چک کن نسخهٔ Python در log (مثل `python3.14`, `cp314`)
- **Python 3.13+** و به‌خصوص 3.14 (preview) — اکثر packages هنوز wheel
  ندارند → از source compile می‌شوند → نیاز به Rust/Cargo دارند →
  Render فایل‌سیستم read-only است → fail
- **راه‌حل واحد و درست**: یک فایل `runtime.txt` با محتوای:
  `python-3.11.10` یا `python-3.12.7` در ریشهٔ پروژه
- این تنها fix در action_plan کافی است — بقیه (pydantic-core unpin،
  maturin، Dockerfile Rust install) **بی‌اثر یا مضر** هستند چون
  Render Native Python runtime از Dockerfile استفاده نمی‌کند
- **هرگز** پیشنهاد نده «maturin به requirements اضافه کن» چون maturin
  هم Rust compile نیاز دارد و در همان محیط fail می‌کند""",
        },
        {
            "id": "sys_clarify_first",
            "title": "قانون ابهام — اول سوال، بعد عمل",
            "content": "اگر درخواست کاربر مبهم است یا چند راه‌حل معقول وجود دارد، به‌جای حدس زدن یا اجرای random، یک سوال شفاف از کاربر بپرس. برای این کار به جای `files` در JSON خروجی، از فرمت `ask_user` استفاده کن.",
            "icon": "❓",
            "prompt_detail": """## ❓ قانون حیاتی: ابهام را با سوال حل کن، نه با حدس

### کِی باید سوال بپرسی؟
به جای تولید `action_plan` با `files`، یک JSON با فیلد `ask_user` برگردان وقتی:

1. **چند راه‌حل معقول وجود دارد و trade-off دارند** — مثلاً «دیپلوی شکست خورد چون DATABASE_URL نیست»:
   - راه ۱: کد را graceful degradation کنیم (DB optional)
   - راه ۲: DATABASE_URL واقعی در Render تنظیم کنیم
   - راه ۳: کلاً وابستگی به DB را حذف کنیم
   → باید بپرسی کدام را می‌خواهد، نه اینکه یکی را انتخاب کنی

2. **اطلاعات حیاتی کم است** — مثلاً «خطای auth fix کن» ولی نمی‌دانی کدام endpoint:
   - بپرس کدام بخش (login/signup/refresh) را می‌گوید

3. **scope مبهم است** — مثلاً «اضافه کن notification»:
   - بپرس notification چه نوعی (toast/email/push) و کجا (header/dashboard/همه‌جا)

4. **مقدار credentials/URL/secret نیاز دارد** — مثلاً DATABASE_URL value:
   - بپرس از کاربر مقدار را وارد کند یا تأیید کند placeholder قابل قبول است

5. **اعتمادت < 70% است** برای تشخیص فایل/خط مشکل‌دار

### چه وقتی **نباید** سوال بپرسی؟
- ❌ اگر در پیام کاربر یا history جواب صریح هست (فقط حواست را جمع کن)
- ❌ برای جزئیات formatting/styling/whitespace (تصمیم خودت بگیر)
- ❌ اگر فقط یک راه‌حل منطقی هست
- ❌ اگر کاربر صریحاً گفت «هر چی صلاح می‌دانی»

### فرمت دقیق `ask_user`:
به جای `{"files": [...]}` این را برگردان:

```json
{
  "ask_user": {
    "question": "متن سوال — کوتاه، مشخص، با context کافی",
    "type": "single" | "multi" | "text",
    "context": "چرا این سوال — توضیح ۱-۲ خطی از وضعیتی که کاربر باید تصمیم بگیرد",
    "options": [
      {"id": "opt_bypass", "label": "گزینهٔ ۱ — کوتاه", "description": "توضیح آن گزینه و trade-off"},
      {"id": "opt_setup", "label": "گزینهٔ ۲ — کوتاه", "description": "..."}
    ],
    "default": "opt_bypass"
  },
  "commit_message": ""
}
```

- `type: "single"` → یک گزینه — `options` لازم است
- `type: "multi"` → چند گزینه با تیک — `options` لازم است
- `type: "text"` → پاسخ متنی آزاد — `options` نگذار
- `id` هر option باید snake_case، unique و معنی‌دار باشد
- `default` (اختیاری) → گزینهٔ پیشنهادی

### مثال‌های دقیق:

**مثال ۱ (single — trade-off دیپلوی):**
```json
{
  "ask_user": {
    "question": "دیپلوی به خاطر DATABASE_URL تنظیم‌نشده شکست می‌خورد. چه کار کنم؟",
    "type": "single",
    "context": "لاگ نشان می‌دهد ConnectionRefusedError برای localhost:5432. سه راه معقول وجود دارد و هرکدام trade-off دارد.",
    "options": [
      {"id": "bypass_db", "label": "DB را optional کن", "description": "کد را طوری تغییر می‌دهم که اگر DATABASE_URL نباشد، اپ بدون DB بالا بیاید. سریع‌ترین راه و بدون نیاز به credentials."},
      {"id": "setup_db", "label": "DATABASE_URL را در Render ست کن", "description": "نیاز دارم مقدار واقعی DATABASE_URL را بدهی. اپ با DB کار خواهد کرد."},
      {"id": "remove_db", "label": "DB را کاملاً حذف کن", "description": "اگر اصلاً DB لازم نداری، تمام کد مرتبط با DB را حذف می‌کنم."}
    ],
    "default": "bypass_db"
  }
}
```

**مثال ۲ (text — مقدار credential):**
```json
{
  "ask_user": {
    "question": "مقدار DATABASE_URL را وارد کن (یا 'placeholder' اگر بعداً ست می‌کنی):",
    "type": "text",
    "context": "می‌خواهم env var واقعی در Render تنظیم کنم اما secret نباید حدس بزنم."
  }
}
```

**مثال ۳ (multi — چند ویژگی):**
```json
{
  "ask_user": {
    "question": "کدام بخش‌های notification را اضافه کنم؟",
    "type": "multi",
    "context": "گفتی «notification اضافه کن» — می‌توانم چند نوع پیاده کنم.",
    "options": [
      {"id": "toast", "label": "Toast پاپ‌آپ", "description": "پیام موقت در گوشهٔ صفحه"},
      {"id": "header_bell", "label": "زنگ در header", "description": "آیکن زنگ + لیست notification"},
      {"id": "email", "label": "Email", "description": "ایمیل برای رویدادهای مهم"}
    ]
  }
}
```

### قانون مسیریابی (route_to):
اگر تشخیص دادی که برای جواب درست نیاز به **اسکن عمیق چند فایل** داری (مثلاً تغییر روی >۵ فایل یا چند ماژول)، به‌جای `files`، این را برگردان:

```json
{
  "route_to": "deep_scan",
  "reason": "این تغییر روی frontend+backend+tests اثر دارد و نیاز به اسکن سراسری دارم.",
  "scan_config": {
    "sections": ["frontend", "backend"],
    "focus_notes": "تمرکز روی auth flow",
    "custom_paths": []
  }
}
```

⛔ از `route_to` فقط وقتی استفاده کن که scope **واقعاً** بزرگ است. برای تغییرات ۱-۳ فایلی، خودت کار را تمام کن.

### قانون حیاتی: Infrastructure errors → همیشه ask_user
اگر در `backend_logs` یا پیام کاربر یکی از موارد زیر دیدی:
- `ConnectionRefusedError`، `Connection refused`، `[Errno 111]`
- `could not connect to server`، `connect call failed`
- `asyncpg.exceptions.ConnectionFailureError`، `psycopg2.OperationalError`
- `redis.exceptions.ConnectionError`، `DNSLookupError`، `ConnectTimeoutError`

این یک infrastructure issue است و **نباید** فایل‌های زیادی تغییر دهی. **حتماً** ask_user بدهی با ۳ گزینه (بدون استثنا):

```json
{
  "ask_user": {
    "question": "خطای connection به <SERVICE> شناسایی شد. چطور fix کنم؟",
    "type": "single",
    "context": "از log: <نقل قول دقیق خط error>. سه راه‌حل دارد و trade-off دارند.",
    "options": [
      {"id": "graceful", "label": "Graceful degradation در کد", "description": "اپ را طوری تغییر دهم که اگر <SERVICE> در دسترس نباشد، بدون error بالا بیاید. سریع‌ترین راه، بدون نیاز به credentials."},
      {"id": "setup_env", "label": "ست کردن env var واقعی در Render", "description": "نیاز دارم مقدار <ENV_VAR> را بدهی. <SERVICE> با اپ کار می‌کند."},
      {"id": "remove_dep", "label": "حذف کامل وابستگی به <SERVICE>", "description": "اگر اصلاً <SERVICE> لازم نداری، تمام کد مرتبط را پاک می‌کنم."}
    ],
    "default": "graceful"
  }
}
```

- ⛔ **هرگز** بدون ask_user مستقیماً action_plan با فایل بده برای infra errors
- ⛔ **هرگز** scope را گسترش نده — فقط فایل مستقیماً مرتبط با connection (مثل `main.py` startup، `database.py`) را در نظر بگیر

### قانون پاسخ کاربر:
اگر در پیام کاربر تگ `[user_clarification ref=... qtype=...]` دیدی:
- این پاسخ کاربر به سوال قبلی **خودت** است
- **هرگز** دوباره همان سوال را نپرس
- مستقیماً بر اساس تصمیم کاربر `action_plan` با `files` (و در صورت نیاز `render_actions`) تولید کن
- اگر کاربر `id=opt_xxx` انتخاب کرده، در history قبلی گزینهٔ متناظر را پیدا کن و طبق توضیح آن عمل کن
- اگر کاربر متن آزاد داد، مقدار را مستقیم در تنظیمات (مثلاً `render_actions[].value`) قرار بده""",
        },
        {
            "id": "sys_exact_intent",
            "title": "فهم دقیق کلمه‌به‌کلمه درخواست کاربر",
            "content": "کلمات کاربر را دقیق و تحت‌اللفظی بخوان. «فقط» یعنی فقط. «نباید» یعنی ممنوع. هرگز معنی درخواست را برعکس تفسیر نکن. اگر مبهم است، محتاطانه‌ترین تفسیر را انتخاب کن.",
            "icon": "🎯",
            "prompt_detail": """## 🎯 قانون حیاتی: فهم دقیق و تحت‌اللفظی درخواست کاربر

### قوانین تفسیر:
1. **کلمات کلیدی را تحت‌اللفظی بخوان:**
   - «فقط» (فقط) = ONLY — هیچ جای دیگری نه
   - «نباید» (نباید) = MUST NOT — ممنوع
   - «همه جا» (همه جا) = EVERYWHERE — بدون استثنا
   - «حذف کن» (حذف) = DELETE — کاملاً پاک شود
   - «اضافه کن» (اضافه) = ADD — بدون حذف چیزهای موجود

2. **مثال‌های حیاتی:**
   - کاربر: «ویجت چت **فقط** در صفحه مانیتورینگ باشه و **نباید** جای دیگه نشون داده بشه»
     ✅ صحیح: ChatWidget فقط در /monitoring رندر شود → شرطی کردن
     ❌ غلط: ChatWidget در تمام صفحات نشان داده شود (برعکس درخواست!)
   - کاربر: «ارتفاع چت رو **کمتر** کن»
     ✅ صحیح: فقط max-height یا height را تغییر بده
     ❌ غلط: کل کامپوننت چت را از صفر بازنویسی کن
   - کاربر: «تب‌ها **کار نمی‌کنن**»
     ✅ صحیح: باگ تب‌ها را پیدا و رفع کن (CSS/JS issue)
     ❌ غلط: کل صفحه را از صفر بنویس

3. **در بازتحلیل (reanalyze):**
   - وقتی گزارش مدل قبلی را بررسی می‌کنی → درخواست اصلی کاربر را دوباره بخوان
   - اگر مدل قبلی بخشی را **درست** انجام داده → آن را تأیید کن و تغییر نده
   - اگر مدل قبلی بخشی را **غلط** انجام داده → فقط همان بخش را اصلاح کن
   - ❌ هرگز یک تصمیم صحیح مدل قبلی را فقط به خاطر «متفاوت بودن» رد نکن
   - ❌ هرگز معنی درخواست کاربر را برعکس مدل قبلی تفسیر نکن — خود درخواست اصلی معیار است

4. **در مرحله‌های چندگانه (multi-step):**
   - هر مرحله باید با مراحل قبلی **سازگار** باشد
   - اگر مرحله ۱ یک تصمیم درست گرفته → مرحله ۲ و ۳ آن را حفظ کنند
   - ❌ مرحله ۳ نباید تغییرات مرحله ۱ را نقض کند""",
        },
    ]


def _build_general_instructions_text(instructions_list: list) -> str:
    """
    ساخت متن دستورات عمومی از لیست واحد — برای تزریق در پرامپت مدل‌ها.
    از prompt_detail (جزئیات کامل) استفاده می‌کنه.
    """
    lines = ["\n## 📌 دستورات عمومی سیستم (همیشه فعال):\n"]
    for idx, inst in enumerate(instructions_list, 1):
        icon = inst.get("icon", "")
        title = inst["title"]
        detail = inst.get("prompt_detail", inst["content"])
        lines.append(f"### {idx}. {icon} {title}")
        lines.append(detail)
        lines.append("")
    return "\n".join(lines)


def _cleanup_old_batch_tasks():
    """پاکسازی task‌های قدیمی (فراخوانی هر چند وقت یکبار)"""
    now = _time.time()
    expired = [k for k, v in _BATCH_TASKS.items()
               if now - v.get("created_at", 0) > _BATCH_TASKS_TTL]
    for k in expired:
        entry = _BATCH_TASKS.pop(k, {})
        task = entry.get("task")
        if task and not task.done():
            task.cancel()


async def _run_batch_processing_bg(
    task_key: str,
    github_svc,
    ai_manager,
    owner: str,
    repo: str,
    token: str,
    selected: list,
    batches: list,
    per_file_limit: int,
    primary_model: str,
    model_max_output: int,
    request_message: str,
    history_text: str,
    tree_summary: str,
    flow_type: str = "action",  # "action" | "question" | "error_log"
):
    """
    پردازش دسته‌ای در بک‌گراند — مستقل از SSE connection.
    نتایج تو _BATCH_TASKS ذخیره میشه و SSE از اونجا میخونه.
    """
    info = _BATCH_TASKS.get(task_key)
    if not info:
        return

    try:
        batch_count = len(batches)
        findings = []
        total_read = 0
        read_failures = 0

        for batch_idx, batch_files in enumerate(batches):
            batch_code = ""
            batch_ok = 0

            info["events"].append(("progress", {
                "step": "batch_reading",
                "message": f"📖 خواندن دسته {batch_idx+1} از {batch_count} ({len(batch_files)} فایل)..."
            }))
            info["new_event"].set()

            for fi, fp in enumerate(batch_files):
                try:
                    result = await github_svc.get_file_content(owner, repo, fp, token=token)
                    if result.get("success"):
                        content = result.get("content", "")
                        info["file_contents"][fp] = content  # ذخیره اصلی برای تشخیص بازنویسی مخرب
                        if len(content) > per_file_limit:
                            content = content[:per_file_limit] + "\n... [truncated]"
                        batch_code += f"\n\n=== {fp} ===\n{content}"
                        batch_ok += 1
                    else:
                        read_failures += 1
                except Exception:
                    read_failures += 1
                if fi > 0 and fi % 5 == 0:
                    info["events"].append(("heartbeat", {
                        "message": f"📖 دسته {batch_idx+1}: {fi}/{len(batch_files)}..."
                    }))
                    info["new_event"].set()
                await _asyncio.sleep(0.1)

            total_read += batch_ok

            if not batch_code.strip():
                findings.append(f"### دسته {batch_idx+1}: هیچ فایلی خوانده نشد")
                continue

            info["events"].append(("progress", {
                "step": "batch_analyzing",
                "message": f"🧠 تحلیل دسته {batch_idx+1} از {batch_count} ({batch_ok} فایل)..."
            }))
            info["new_event"].set()

            # ساخت پرامپت بر اساس نوع flow
            if flow_type == "question":
                batch_prompt = f"سؤال کاربر: {request_message}\n\nفایل‌های دسته {batch_idx+1}:{batch_code}\n\nساختار پروژه:\n{tree_summary[:2000]}\n\nیافته‌های مرتبط با سؤال را استخراج کن. خلاصه و دقیق."
                sys_msg = f"تحلیل‌گر دسته‌ای. دسته {batch_idx+1}/{batch_count}. سؤال: {request_message[:200]}. یافته‌های کلیدی مرتبط."
            elif flow_type == "error_log":
                batch_prompt = f"خطا/لاگ: {request_message[:2000]}\n\nفایل‌های دسته {batch_idx+1}:{batch_code}\n\nساختار پروژه:\n{tree_summary[:2000]}\n\nیافته‌های مرتبط با خطا را استخراج کن. خلاصه و دقیق."
                sys_msg = f"تحلیل‌گر دسته‌ای خطا. دسته {batch_idx+1}/{batch_count}. خطا: {request_message[:200]}. یافته‌های مرتبط با خطا."
            else:  # action
                batch_prompt = f"""## درخواست کاربر:
{request_message}

## تاریخچه مکالمه (خلاصه):
{history_text[-2000:]}

## فایل‌های دسته {batch_idx+1} از {batch_count} — محتوای کامل:
{batch_code}

## ساختار کلی پروژه:
{tree_summary[:3000]}

## وظیفه تو — تحلیل دسته‌ای:
بر اساس درخواست کاربر، فایل‌های این دسته را دقیق تحلیل کن:
- برای هر فایل: imports، exports، عملکرد اصلی، وابستگی‌ها
- یافته‌های مرتبط با درخواست کاربر (فایل بلااستفاده، باگ، مشکل ساختاری، کد تکراری، ...)
- ارجاعات بین فایلی: این فایل از کجاها import میکنه و احتمالاً کجاها ازش استفاده میشه
- اگر مشکل یا نکته مهمی در خطوط پایین فایل هست، حتماً ذکر کن
⚠️ فقط یافته‌ها و تحلیل دقیق بنویس — جمع‌بندی نهایی در مرحله بعد انجام میشه."""
                sys_msg = f"تحلیل‌گر دسته‌ای پروژه. دسته {batch_idx+1}/{batch_count}. درخواست: {request_message[:200]}. فقط یافته‌های کلیدی. دقیق و کامل."

            try:
                from ...services.ai_base import Message
                batch_task = _asyncio.create_task(ai_manager.generate(
                    model_id=primary_model,
                    messages=[
                        Message(role="system", content=sys_msg),
                        Message(role="user", content=batch_prompt)
                    ],
                    max_tokens=model_max_output,
                    temperature=0.2
                ))
                bwait = 0
                while not batch_task.done():
                    done_set, _ = await _asyncio.wait({batch_task}, timeout=5.0)
                    if done_set:
                        break
                    bwait += 5
                    info["events"].append(("heartbeat", {
                        "message": f"⏳ تحلیل دسته {batch_idx+1}/{batch_count}... ({bwait}s)"
                    }))
                    info["new_event"].set()
                    if bwait >= 120:
                        batch_task.cancel()
                        raise TimeoutError(f"Batch {batch_idx+1} timed out")

                batch_response = batch_task.result()
                if batch_response.content and batch_response.content.strip():
                    file_names = ", ".join(bf.split("/")[-1] for bf in batch_files[:5])
                    if len(batch_files) > 5:
                        file_names += f" و {len(batch_files)-5} فایل دیگر"
                    findings.append(f"### 📦 دسته {batch_idx+1} ({file_names}):\n{batch_response.content}")
            except Exception as e:
                slog.warning(f"[batch-bg] Batch {batch_idx+1} failed: {e}")
                findings.append(f"### دسته {batch_idx+1}: ❌ خطا: {str(e)[:100]}")

            info["events"].append(("progress", {
                "step": "batch_done",
                "message": f"✅ دسته {batch_idx+1}/{batch_count} تحلیل شد ({total_read} فایل تا الان)"
            }))
            info["findings"] = list(findings)
            info["total_read"] = total_read
            info["new_event"].set()

        # تکمیل
        info["code_context"] = "\n\n".join(findings)
        info["findings"] = findings
        info["total_read"] = total_read
        info["batch_count"] = batch_count
        info["status"] = "completed"
        info["events"].append(("progress", {
            "step": "batch_complete",
            "message": f"✅ پردازش دسته‌ای کامل: {batch_count} دسته، {total_read} فایل خوانده و تحلیل شد"
        }))
        info["new_event"].set()

    except _asyncio.CancelledError:
        info["status"] = "cancelled"
        info["new_event"].set()
    except Exception as e:
        slog.error(f"[batch-bg] Background task failed: {e}")
        info["status"] = "error"
        info["error"] = str(e)
        info["events"].append(("error", {"message": f"❌ خطا در پردازش: {str(e)[:150]}"}))
        info["new_event"].set()


async def _follow_bg_batch(info: dict, sse):
    """
    دنبال کردن یک background batch task — SSE event ها رو relay میکنه.
    این async generator توسط SSE stream فراخوانی میشه.
    اگر SSE قطع بشه، task اصلی بک‌گراند ادامه پیدا میکنه.
    """
    event_idx = 0
    while info["status"] == "running":
        while event_idx < len(info["events"]):
            evt_type, evt_data = info["events"][event_idx]
            yield sse(evt_type, evt_data)
            event_idx += 1
        try:
            info["new_event"].clear()
            await _asyncio.wait_for(info["new_event"].wait(), timeout=5.0)
        except _asyncio.TimeoutError:
            yield sse("heartbeat", {"message": "⏳ در حال پردازش..."})
    # drain remaining events
    while event_idx < len(info["events"]):
        evt_type, evt_data = info["events"][event_idx]
        yield sse(evt_type, evt_data)
        event_idx += 1
    # handle error
    if info["status"] == "error":
        yield sse("error", {"message": f"❌ {info.get('error', 'خطای ناشناخته')}"})


def _start_bg_batch(
    project_id: str, message: str, selected: list, batches: list,
    per_file_limit: int, github_svc, ai_manager, owner: str, repo: str,
    token: str, primary_model: str, model_max_output: int,
    history_text: str, tree_summary: str, flow_type: str = "action"
):
    """
    شروع یک background batch task جدید یا برگرداندن task موجود.
    Returns: (task_key, info, is_reconnect)
    """
    _cleanup_old_batch_tasks()
    task_key = _batch_task_key(project_id, message, selected)
    existing = _get_batch_task(task_key)

    if existing:
        return task_key, existing, True

    info = {
        "task": None,
        "events": [],
        "new_event": _asyncio.Event(),
        "status": "running",
        "code_context": "",
        "findings": [],
        "total_read": 0,
        "batch_count": len(batches),
        "created_at": _time.time(),
        "project_id": project_id,
        "flow_type": flow_type,
        "file_contents": {},  # ذخیره محتوای اصلی فایل‌ها برای تشخیص بازنویسی مخرب
    }
    _BATCH_TASKS[task_key] = info
    info["task"] = _asyncio.create_task(_run_batch_processing_bg(
        task_key, github_svc, ai_manager, owner, repo, token,
        selected, batches, per_file_limit, primary_model,
        model_max_output, message, history_text, tree_summary,
        flow_type=flow_type
    ))
    return task_key, info, False


# ── Constants ────────────────────────────────────────────────────────
# فیلتر مسیرهای غیرکد (استفاده مشترک در همه endpoint های Inspector)
IGNORED_PATH_PREFIXES = (
    "node_modules/", ".git/", "dist/", "build/", ".next/",
    "__pycache__/", ".venv/", "venv/", ".cache/", ".idea/", ".vscode/",
)
CODE_EXTENSIONS = (
    ".js", ".ts", ".tsx", ".jsx", ".py", ".java", ".go", ".rs",
    ".vue", ".svelte", ".html", ".css", ".scss", ".json", ".yaml", ".yml",
    ".toml", ".env", ".md", ".sql", ".sh", ".rb", ".php", ".cs",
)


IGNORED_FILENAMES = (
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "InspectorBridge", "inspector-bridge", "inspectorBridge",
)
IGNORED_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mp3", ".zip", ".tar", ".gz",
)


def _is_code_file(path: str, max_size: int = 200000, file_size: int = 0) -> bool:
    """بررسی اینکه فایل یک فایل کد قابل بررسی هست"""
    if file_size > max_size:
        return False
    if any(path.startswith(p) or f"/{p}" in path for p in IGNORED_PATH_PREFIXES):
        return False
    if any(ig in path for ig in IGNORED_FILENAMES):
        return False
    if any(path.endswith(ext) for ext in IGNORED_EXTENSIONS):
        return False
    return True


# =====================================
# Request/Response Models
# =====================================

class LogFilterRequest(BaseModel):
    """فیلتر لاگ‌ها"""
    service_ids: Optional[List[str]] = None
    levels: Optional[List[str]] = None  # info, warn, error, debug
    search: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class LogSettingsRequest(BaseModel):
    """تنظیمات لاگ"""
    polling_interval_seconds: int = 10
    polling_enabled: bool = True
    retention_hours: int = 48
    archive_enabled: bool = True
    archive_retention_days: int = 30
    default_log_levels: str = "info,warn,error"
    auto_scroll: bool = True
    # تنظیمات انتقال خودکار
    auto_transfer_enabled: bool = False
    auto_transfer_interval_minutes: int = 30
    auto_transfer_hours_back: int = 24  # فقط در حالت time_based استفاده می‌شود
    # حالت‌های انتقال:
    # - since_deploy: خطاهای بعد از آخرین دیپلوی (با اینتروال)
    # - time_based: خطاهای X ساعت اخیر (با اینتروال)
    # - realtime: هر خطا فوراً منتقل شود (بدون اینتروال)
    auto_transfer_mode: str = "since_deploy"


# =====================================
# Services Endpoints
# =====================================

@router.get("/services")
async def get_services(
    refresh: bool = False,
    db: Session = Depends(get_db)
):
    """
    دریافت لیست سرویس‌های Render

    - refresh=True: دریافت مستقیم از API
    - refresh=False: استفاده از cache دیتابیس
    """
    slog.api_request("GET", "/render/services", refresh=refresh)

    if refresh:
        # دریافت از API
        render = get_render_service()
        result = await render.get_services()

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "خطا در دریافت سرویس‌ها")
            )

        return result

    # دریافت از دیتابیس
    try:
        services = db.query(RenderService).order_by(RenderService.name).all()

        return {
            "success": True,
            "services": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.type,
                    "region": s.region,
                    "status": s.status,
                    "auto_fetch_logs": getattr(s, 'auto_fetch_logs', True),
                    "log_retention_hours": getattr(s, 'log_retention_hours', 48),
                    "last_deploy_id": getattr(s, 'last_deploy_id', None),
                    "last_transferred_deploy_id": getattr(s, 'last_transferred_deploy_id', None)
                }
                for s in services
            ],
            "source": "database",
            "last_updated": services[0].updated_at.isoformat() if services and hasattr(services[0], 'updated_at') and services[0].updated_at else None
        }
    except Exception as e:
        slog.error("Error fetching services from database (ORM)", exception=e)
        # Fallback: استفاده از raw SQL برای ستون‌های پایه
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT id, name, type, region, status FROM render_services ORDER BY name"))
            rows = result.fetchall()
            return {
                "success": True,
                "services": [
                    {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "region": row[3],
                        "status": row[4],
                        "auto_fetch_logs": True,
                        "log_retention_hours": 48,
                        "last_deploy_id": None,
                        "last_transferred_deploy_id": None
                    }
                    for row in rows
                ],
                "source": "database_raw",
                "last_updated": None
            }
        except Exception as e2:
            slog.error("Error fetching services from database (raw SQL)", exception=e2)
            return {
                "success": False,
                "services": [],
                "error": str(e)
            }


@router.post("/services/refresh")
async def refresh_services():
    """
    بروزرسانی لیست سرویس‌ها از Render API
    """
    slog.api_request("POST", "/render/services/refresh")

    render = get_render_service()
    result = await render.get_services()

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "خطا در بروزرسانی سرویس‌ها")
        )

    return result


@router.patch("/services/{service_id}")
async def update_service_settings(
    service_id: str,
    auto_fetch_logs: Optional[bool] = None,
    log_retention_hours: Optional[int] = None,
    project_id: Optional[str] = None,  # 🆕 نگاشت به پروژه
    db: Session = Depends(get_db)
):
    """
    بروزرسانی تنظیمات یک سرویس

    Args:
        project_id: ID پروژه برای نگاشت (یا null برای حذف نگاشت)
    """
    slog.api_request("PATCH", f"/render/services/{service_id}")

    service = db.query(RenderService).filter(RenderService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="سرویس یافت نشد")

    if auto_fetch_logs is not None:
        service.auto_fetch_logs = auto_fetch_logs
    if log_retention_hours is not None:
        service.log_retention_hours = log_retention_hours

    # 🆕 بروزرسانی نگاشت به پروژه
    if project_id is not None:
        if project_id == "" or project_id == "null":
            service.project_id = None
            slog.info(f"Removed project mapping for service {service_id}")
        else:
            # بررسی وجود پروژه
            from ...models.project import Project
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                service.project_id = project_id
                slog.info(f"Mapped service {service_id} to project {project.name}")
            else:
                raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    db.commit()

    return {
        "success": True,
        "service_id": service_id,
        "project_id": service.project_id,
        "message": "تنظیمات بروزرسانی شد"
    }


@router.get("/services/mappings")
async def get_service_project_mappings(
    db: Session = Depends(get_db)
):
    """
    دریافت وضعیت نگاشت سرویس‌ها به پروژه‌ها

    شامل:
    - سرویس‌های نگاشت شده (دستی و خودکار)
    - سرویس‌های بدون نگاشت
    - لیست پروژه‌ها برای انتخاب
    """
    from ...models.project import Project

    services = db.query(RenderService).all()
    projects = db.query(Project).all()

    mappings = []
    unmapped = []

    projects_dict = {p.id: p for p in projects}

    for service in services:
        service_info = {
            "service_id": service.id,
            "service_name": service.name,
            "service_type": service.type,
            "project_id": service.project_id,
            "project_name": None,
            "mapping_type": None
        }

        if service.project_id and service.project_id in projects_dict:
            project = projects_dict[service.project_id]
            service_info["project_name"] = project.name
            service_info["mapping_type"] = "manual"
            mappings.append(service_info)
        else:
            # تلاش برای یافتن خودکار
            search_term = service.name.split('-')[0]
            auto_project = db.query(Project).filter(
                Project.name.ilike(f"%{search_term}%")
            ).first()

            if auto_project:
                service_info["project_id"] = auto_project.id
                service_info["project_name"] = auto_project.name
                service_info["mapping_type"] = "auto"
                mappings.append(service_info)
            else:
                unmapped.append(service_info)

    return {
        "success": True,
        "mapped": mappings,
        "unmapped": unmapped,
        "total_services": len(services),
        "total_mapped": len(mappings),
        "total_unmapped": len(unmapped),
        "projects": [{"id": p.id, "name": p.name} for p in projects]
    }


@router.get("/services/by-project/{project_id}")
async def get_services_by_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    دریافت سرویس‌های مرتبط با یک پروژه خاص

    این endpoint برای تب بازرس ویژه استفاده می‌شود تا سرویس‌های
    یک پروژه را برای نمایش لاگ‌ها و پیش‌نمایش لود کند.

    Returns:
        - services: لیست سرویس‌ها با URL و نوع
        - frontend_url: URL فرانت‌اند برای نمایش در iframe
        - backend_services: لیست سرویس‌های بک‌اند برای نمایش لاگ
    """
    slog.api_request("GET", f"/render/services/by-project/{project_id}")

    # 1. سرویس‌های نگاشت شده به این پروژه
    services = db.query(RenderService).filter(
        RenderService.project_id == project_id
    ).all()

    # 2. اگر نگاشت دستی نداشت، جستجوی خودکار
    if not services:
        from ...models.project import Project
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            # جستجو بر اساس نام پروژه
            search_term = project.name.lower().replace(" ", "-").replace("_", "-")
            all_services = db.query(RenderService).all()
            services = [
                s for s in all_services
                if search_term in s.name.lower() or s.name.lower() in search_term
            ]

    if not services:
        return {
            "success": True,
            "services": [],
            "frontend_url": None,
            "backend_services": [],
            "message": "هیچ سرویسی برای این پروژه یافت نشد. از صفحه تنظیمات Render Logs سرویس‌ها را به این پروژه نگاشت کنید."
        }

    # 3. دسته‌بندی سرویس‌ها
    frontend_url = None
    backend_services = []
    all_web_services = []  # همه سرویس‌های وب برای fallback

    def get_service_url(s):
        """استخراج URL سرویس - اول از دیتابیس، بعد fallback به ساخت از نام"""
        # 🆕 اول از URL ذخیره شده استفاده کن
        if hasattr(s, 'service_url') and s.service_url:
            return s.service_url
        # Fallback: ساخت از نام (برای رکوردهای قدیمی)
        if s.type in ["web_service", "static_site"]:
            slug = s.name.lower().replace(" ", "-").replace("_", "-")
            return f"https://{slug}.onrender.com"
        return None

    for s in services:
        service_url = get_service_url(s)
        service_info = {
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "status": s.status,
            "url": service_url,
            "dashboard_url": f"https://dashboard.render.com/web/{s.id}"
        }

        # ذخیره همه web_service ها
        if s.type in ["web_service", "static_site"]:
            all_web_services.append(service_info)

        # تشخیص فرانت‌اند vs بک‌اند
        name_lower = s.name.lower()
        is_frontend_like = any(x in name_lower for x in ["frontend", "front", "client", "ui", "static"])
        is_backend_like = any(x in name_lower for x in ["backend", "back", "api", "server"])

        if is_frontend_like and not is_backend_like:
            # فقط فرانت‌اند
            if not frontend_url and service_url:
                frontend_url = service_url
            service_info["role"] = "frontend"
        elif is_backend_like and not is_frontend_like:
            # فقط بک‌اند
            service_info["role"] = "backend"
            backend_services.append(service_info)
        else:
            # یکپارچه (هم فرانت هم بک) یا نامشخص
            # برای لاگ‌ها به عنوان بک‌اند استفاده کن
            service_info["role"] = "unified"
            backend_services.append(service_info)
            # برای پیش‌نمایش هم استفاده کن (اگر فرانت جدا نداریم)
            if not frontend_url and service_url:
                frontend_url = service_url

    # اگر فرانت‌اند پیدا نشد، اولین web_service را انتخاب کن
    if not frontend_url and all_web_services:
        frontend_url = all_web_services[0]["url"]
        # اگر این سرویس در backend_services نیست، اضافه کن
        first_web_id = all_web_services[0]["id"]
        if not any(bs["id"] == first_web_id for bs in backend_services):
            backend_services.append(all_web_services[0])

    return {
        "success": True,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "status": s.status,
                "url": get_service_url(s),
                "role": next((bs["role"] for bs in backend_services if bs["id"] == s.id), "frontend")
            }
            for s in services
        ],
        "frontend_url": frontend_url,
        "backend_services": backend_services,
        "total": len(services)
    }


# =====================================
# Logs Endpoints
# =====================================

@router.get("/logs")
async def get_logs(
    service_id: Optional[str] = None,
    service_ids: Optional[List[str]] = Query(None),
    level: Optional[str] = None,
    search: Optional[str] = None,
    minutes: int = 30,
    hours: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    دریافت لاگ‌ها از دیتابیس

    Args:
        service_id: فیلتر بر اساس سرویس (تک سرویس)
        service_ids: فیلتر بر اساس چند سرویس
        level: فیلتر سطح (info,warn,error,debug)
        search: جستجو در متن
        minutes: لاگ‌های X دقیقه اخیر
        hours: لاگ‌های X ساعت اخیر (اولویت بالاتر)
        limit: تعداد
        offset: صفحه‌بندی
    """
    slog.api_request("GET", "/render/logs",
        service_id=service_id,
        service_ids=service_ids,
        log_level=level,
        minutes=minutes
    )

    # ساخت کوئری
    query = db.query(RenderLog)

    # فیلتر زمانی
    if hours:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
    else:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    query = query.filter(RenderLog.timestamp >= cutoff)

    # فیلتر سرویس - پشتیبانی از چند سرویس
    if service_ids and len(service_ids) > 0:
        query = query.filter(RenderLog.service_id.in_(service_ids))
    elif service_id:
        query = query.filter(RenderLog.service_id == service_id)

    # فیلتر سطح
    if level:
        levels = level.split(",")
        query = query.filter(RenderLog.level.in_(levels))

    # جستجو
    if search:
        query = query.filter(RenderLog.message.ilike(f"%{search}%"))

    # تعداد کل
    total = query.count()

    # مرتب‌سازی و صفحه‌بندی
    logs = query.order_by(desc(RenderLog.timestamp))\
        .offset(offset)\
        .limit(limit)\
        .all()

    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "service_id": log.service_id,
                "service_name": log.service_name,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "deploy_id": log.deploy_id,
                "instance_id": log.instance_id
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total
    }


@router.post("/logs/fetch")
async def fetch_new_logs(
    service_id: Optional[str] = None,
    limit: int = 100,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    دریافت لاگ‌های جدید از Render API و ذخیره در دیتابیس

    - اگر service_id داده نشه، همه سرویس‌ها بررسی می‌شن
    """
    slog.api_request("POST", "/render/logs/fetch",
        service_id=service_id,
        limit=limit
    )

    try:
        render = get_render_service()
        total_fetched = 0
        total_saved = 0
        errors = []

        # تعیین سرویس‌ها
        services = []
        try:
            if service_id:
                services = db.query(RenderService).filter(
                    RenderService.id == service_id
                ).all()
            else:
                # استفاده از filter ساده‌تر در صورت مشکل با auto_fetch_logs
                services = db.query(RenderService).all()
                # فیلتر در پایتون به جای SQL
                services = [s for s in services if getattr(s, 'auto_fetch_logs', True)]
        except Exception as e:
            slog.error("Error querying services (ORM)", exception=e)
            # Fallback: raw SQL
            try:
                from sqlalchemy import text
                if service_id:
                    result = db.execute(text("SELECT id, name FROM render_services WHERE id = :sid"), {"sid": service_id})
                else:
                    result = db.execute(text("SELECT id, name FROM render_services"))
                rows = result.fetchall()
                # ساخت شیء ساده به جای ORM model
                class SimpleService:
                    def __init__(self, id, name):
                        self.id = id
                        self.name = name
                        self.auto_fetch_logs = True
                services = [SimpleService(row[0], row[1]) for row in rows]
            except Exception as e2:
                slog.error("Error querying services (raw SQL)", exception=e2)
                services = []

        if not services:
            # اگر سرویسی نبود، اول لیست رو بگیر
            result = await render.get_services()
            if result["success"]:
                services = db.query(RenderService).all()
            else:
                return {
                    "success": False,
                    "error": result.get("error", "هیچ سرویسی یافت نشد. ابتدا لیست سرویس‌ها را بروزرسانی کنید.")
                }

        # دریافت لاگ برای هر سرویس
        for service in services:
            try:
                result = await render.get_logs(
                    service_id=service.id,
                    limit=limit,
                    direction="backward"
                )

                if result["success"]:
                    total_fetched += len(result["logs"])

                    # ذخیره در دیتابیس
                    saved = await render.save_logs_to_db(
                        result["logs"],
                        service_name=service.name
                    )
                    total_saved += saved

                else:
                    errors.append({
                        "service_id": service.id,
                        "service_name": service.name,
                        "error": result.get("error")
                    })

            except Exception as e:
                errors.append({
                    "service_id": service.id,
                    "service_name": service.name,
                    "error": str(e)
                })

        slog.success("Logs fetched",
            total_fetched=total_fetched,
            total_saved=total_saved,
            errors_count=len(errors)
        )

        return {
            "success": True,
            "total_fetched": total_fetched,
            "total_saved": total_saved,
            "services_processed": len(services),
            "errors": errors if errors else None
        }

    except Exception as e:
        slog.error("Fetch logs failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/logs/live")
async def get_live_logs(
    service_id: Optional[str] = None,
    since_id: Optional[str] = None,
    since_timestamp: Optional[str] = None,
    levels: str = "info,warn,error",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    دریافت لاگ‌های جدید (برای polling)

    Args:
        since_id: لاگ‌های بعد از این ID
        since_timestamp: لاگ‌های بعد از این زمان
        levels: سطوح لاگ
        limit: حداکثر تعداد
    """
    query = db.query(RenderLog)

    # فیلتر سرویس
    if service_id:
        query = query.filter(RenderLog.service_id == service_id)

    # فیلتر زمانی
    if since_timestamp:
        try:
            ts = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
            query = query.filter(RenderLog.timestamp > ts)
        except:
            pass

    # فیلتر سطح
    if levels:
        level_list = levels.split(",")
        query = query.filter(RenderLog.level.in_(level_list))

    # مرتب‌سازی و محدود کردن
    logs = query.order_by(desc(RenderLog.timestamp)).limit(limit).all()

    # معکوس کردن برای ترتیب زمانی
    logs = list(reversed(logs))

    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "service_id": log.service_id,
                "service_name": log.service_name,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "deploy_id": log.deploy_id
            }
            for log in logs
        ],
        "latest_timestamp": logs[-1].timestamp.isoformat() if logs else None,
        "count": len(logs)
    }


@router.post("/logs/search")
async def search_logs(
    request: LogFilterRequest,
    db: Session = Depends(get_db)
):
    """
    جستجوی پیشرفته در لاگ‌ها
    """
    slog.api_request("POST", "/render/logs/search",
        search=request.search,
        levels=request.levels
    )

    query = db.query(RenderLog)

    # فیلتر سرویس‌ها
    if request.service_ids:
        query = query.filter(RenderLog.service_id.in_(request.service_ids))

    # فیلتر سطح
    if request.levels:
        query = query.filter(RenderLog.level.in_(request.levels))

    # فیلتر زمانی
    if request.start_time:
        query = query.filter(RenderLog.timestamp >= request.start_time)
    if request.end_time:
        query = query.filter(RenderLog.timestamp <= request.end_time)

    # جستجوی متنی
    if request.search:
        query = query.filter(RenderLog.message.ilike(f"%{request.search}%"))

    # شمارش
    total = query.count()

    # نتایج
    logs = query.order_by(desc(RenderLog.timestamp))\
        .offset(request.offset)\
        .limit(request.limit)\
        .all()

    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "service_id": log.service_id,
                "service_name": log.service_name,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "deploy_id": log.deploy_id
            }
            for log in logs
        ],
        "total": total,
        "has_more": request.offset + request.limit < total
    }


# =====================================
# Settings Endpoints
# =====================================

@router.get("/settings")
async def get_log_settings(db: Session = Depends(get_db)):
    """دریافت تنظیمات لاگ"""
    try:
        settings = db.query(RenderLogSettings).first()

        if not settings:
            # ایجاد تنظیمات پیش‌فرض
            settings = RenderLogSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return {
            "success": True,
            "settings": {
                "polling_interval_seconds": settings.polling_interval_seconds,
                "polling_enabled": settings.polling_enabled,
                "retention_hours": settings.retention_hours,
                "archive_enabled": settings.archive_enabled,
                "archive_retention_days": settings.archive_retention_days,
                "default_log_levels": settings.default_log_levels,
                "auto_scroll": settings.auto_scroll,
                # تنظیمات انتقال خودکار
                "auto_transfer_enabled": getattr(settings, 'auto_transfer_enabled', False),
                "auto_transfer_interval_minutes": getattr(settings, 'auto_transfer_interval_minutes', 30),
                "auto_transfer_hours_back": getattr(settings, 'auto_transfer_hours_back', 24),
                "auto_transfer_mode": getattr(settings, 'auto_transfer_mode', 'since_deploy') or 'since_deploy',
                "last_auto_transfer": settings.last_auto_transfer.isoformat() if getattr(settings, 'last_auto_transfer', None) else None
            }
        }
    except Exception as e:
        slog.error("Error fetching settings (ORM)", exception=e)
        # Fallback: مقادیر پیش‌فرض
        return {
            "success": True,
            "settings": {
                "polling_interval_seconds": 10,
                "polling_enabled": True,
                "retention_hours": 48,
                "archive_enabled": True,
                "archive_retention_days": 30,
                "default_log_levels": "info,warn,error",
                "auto_scroll": True,
                "auto_transfer_enabled": False,
                "auto_transfer_interval_minutes": 30,
                "auto_transfer_hours_back": 24,
                "auto_transfer_mode": "since_deploy",
                "last_auto_transfer": None
            },
            "source": "defaults"
        }


@router.put("/settings")
async def update_log_settings(
    request: LogSettingsRequest,
    db: Session = Depends(get_db)
):
    """بروزرسانی تنظیمات لاگ"""
    slog.api_request("PUT", "/render/settings")

    settings = db.query(RenderLogSettings).first()
    if not settings:
        settings = RenderLogSettings()
        db.add(settings)

    settings.polling_interval_seconds = request.polling_interval_seconds
    settings.polling_enabled = request.polling_enabled
    settings.retention_hours = request.retention_hours
    settings.archive_enabled = request.archive_enabled
    settings.archive_retention_days = request.archive_retention_days
    settings.default_log_levels = request.default_log_levels
    settings.auto_scroll = request.auto_scroll
    # تنظیمات انتقال خودکار
    settings.auto_transfer_enabled = request.auto_transfer_enabled
    settings.auto_transfer_interval_minutes = request.auto_transfer_interval_minutes
    settings.auto_transfer_hours_back = request.auto_transfer_hours_back
    settings.auto_transfer_mode = request.auto_transfer_mode

    db.commit()

    # 🆕 به‌روزرسانی scheduler برای auto-transfer
    try:
        from ...services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()
        await scheduler.update_auto_transfer_settings(
            enabled=request.auto_transfer_enabled,
            interval_minutes=request.auto_transfer_interval_minutes,
            hours_back=request.auto_transfer_hours_back,
            mode=request.auto_transfer_mode
        )
    except Exception as e:
        slog.warning("Failed to update scheduler", exception=e)

    slog.success("Log settings updated",
        polling_interval=request.polling_interval_seconds,
        retention_hours=request.retention_hours,
        auto_transfer_enabled=request.auto_transfer_enabled,
        auto_transfer_mode=request.auto_transfer_mode
    )

    return {
        "success": True,
        "message": "تنظیمات ذخیره شد"
    }


# =====================================
# Download Endpoint
# =====================================

from fastapi.responses import Response
import csv
import io

@router.get("/logs/download")
async def download_logs(
    service_ids: Optional[List[str]] = Query(None),
    hours: Optional[int] = None,
    limit: Optional[int] = None,
    level: Optional[str] = None,
    after_deploy: bool = False,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """
    دانلود لاگ‌ها با فیلترهای مختلف

    Args:
        service_ids: لیست سرویس‌ها
        hours: بازه زمانی (ساعت)
        limit: تعداد لاگ
        level: سطح لاگ (error, warn, info)
        after_deploy: فقط لاگ‌های بعد از آخرین دیپلوی
        format: فرمت خروجی (json, txt, csv)
    """
    slog.api_request("GET", "/render/logs/download",
        service_ids=service_ids,
        hours=hours,
        limit=limit,
        log_level=level,
        output_format=format
    )

    query = db.query(RenderLog)

    # فیلتر سرویس
    if service_ids and len(service_ids) > 0:
        query = query.filter(RenderLog.service_id.in_(service_ids))

    # فیلتر زمانی
    if hours:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(RenderLog.timestamp >= cutoff)

    # فیلتر سطح
    if level:
        if level == "error":
            query = query.filter(RenderLog.level == "error")
        elif level == "warn":
            query = query.filter(RenderLog.level.in_(["error", "warn"]))

    # فیلتر بعد از آخرین دیپلوی
    if after_deploy:
        # پیدا کردن آخرین دیپلوی موفق
        last_deploy = db.query(RenderLog).filter(
            RenderLog.message.ilike("%deploy%success%")
        ).order_by(desc(RenderLog.timestamp)).first()
        if last_deploy:
            query = query.filter(RenderLog.timestamp >= last_deploy.timestamp)

    # مرتب‌سازی
    query = query.order_by(RenderLog.timestamp)

    # محدود کردن تعداد
    if limit:
        query = query.limit(limit)
    else:
        query = query.limit(10000)  # حداکثر 10000 لاگ

    logs = query.all()

    # تبدیل به فرمت مناسب
    if format == "json":
        import json
        content = json.dumps([
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level or "unknown",
                "service": log.service_name or log.service_id or "unknown",
                "message": log.message or "",
                "deploy_id": log.deploy_id
            }
            for log in logs
        ], ensure_ascii=False, indent=2)
        media_type = "application/json"

    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "level", "service", "message", "deploy_id"])
        for log in logs:
            writer.writerow([
                log.timestamp.isoformat() if log.timestamp else "",
                log.level or "unknown",
                log.service_name or log.service_id or "unknown",
                log.message or "",
                log.deploy_id or ""
            ])
        content = output.getvalue()
        media_type = "text/csv"

    else:  # txt
        lines = []
        for log in logs:
            ts = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A"
            level = (log.level or "unknown").upper()
            service = log.service_name or log.service_id or "unknown"
            message = log.message or ""
            lines.append(f"[{ts}] [{level}] [{service}] {message}")
        content = "\n".join(lines)
        media_type = "text/plain"

    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="render-logs.{format}"'
        }
    )


# =====================================
# Cleanup & Archive Endpoints
# =====================================

@router.post("/cleanup")
async def cleanup_old_logs(
    retention_hours: int = 48,
    db: Session = Depends(get_db)
):
    """
    پاکسازی لاگ‌های قدیمی و آرشیو
    """
    slog.api_request("POST", "/render/cleanup",
        retention_hours=retention_hours
    )

    render = get_render_service()
    result = await render.cleanup_old_logs(retention_hours)

    return {
        "success": True,
        "archived": result.get("archived", 0),
        "deleted": result.get("deleted", 0),
        "message": f"{result.get('deleted', 0)} لاگ حذف و {result.get('archived', 0)} آرشیو شد"
    }


@router.get("/archives")
async def get_archives(
    service_id: Optional[str] = None,
    service_ids: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """دریافت لیست آرشیوها"""
    query = db.query(RenderLogArchive)

    # پشتیبانی از چند سرویس
    if service_ids and len(service_ids) > 0:
        query = query.filter(RenderLogArchive.service_id.in_(service_ids))
    elif service_id:
        query = query.filter(RenderLogArchive.service_id == service_id)

    archives = query.order_by(desc(RenderLogArchive.archived_at)).limit(100).all()

    return {
        "success": True,
        "archives": [
            {
                "id": a.id,
                "service_id": a.service_id,
                "start_time": a.start_time.isoformat(),
                "end_time": a.end_time.isoformat(),
                "logs_count": a.logs_count,
                "size_bytes": a.size_bytes,
                "archived_at": a.archived_at.isoformat()
            }
            for a in archives
        ]
    }


@router.get("/archives/{archive_id}")
async def get_archive_content(
    archive_id: int,
    db: Session = Depends(get_db)
):
    """دریافت محتوای یک آرشیو"""
    archive = db.query(RenderLogArchive).filter(
        RenderLogArchive.id == archive_id
    ).first()

    if not archive:
        raise HTTPException(status_code=404, detail="آرشیو یافت نشد")

    render = get_render_service()
    logs = await render.get_archived_logs(
        service_id=archive.service_id,
        start_time=archive.start_time,
        end_time=archive.end_time
    )

    return {
        "success": True,
        "archive_id": archive_id,
        "service_id": archive.service_id,
        "start_time": archive.start_time.isoformat(),
        "end_time": archive.end_time.isoformat(),
        "logs": logs
    }


# =====================================
# Log to Issues Transfer
# =====================================

from ...services.log_to_issues_service import get_log_to_issues_service

@router.post("/transfer-errors")
async def transfer_errors_to_issues(
    service_ids: Optional[List[str]] = Query(None),
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    انتقال لاگ‌های خطا به تب ایرادات پروژه‌ها

    - فقط پروژه‌های ایمپورت شده
    - تحلیل AI برای توضیح خطا
    - جستجوی ایرادات مشابه و ادغام
    """
    slog.api_request("POST", "/render/transfer-errors",
        service_ids=service_ids,
        hours=hours
    )

    service = get_log_to_issues_service()
    result = await service.transfer_error_logs(
        service_ids=service_ids,
        hours=hours,
        auto_mode=False,
        db=db
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "خطا در انتقال لاگ‌ها")
        )

    return result


@router.get("/transfer-status")
async def get_transfer_status(
    since_deploy: bool = True,  # 🆕 فقط خطاهای پس از دیپلوی
    db: Session = Depends(get_db)
):
    """
    وضعیت انتقال لاگ‌های خطا

    - تعداد لاگ‌های منتقل شده
    - تعداد لاگ‌های در انتظار (فقط پس از آخرین دیپلوی)
    """
    from sqlalchemy import and_, or_

    # 🆕 دریافت زمان آخرین دیپلوی هر سرویس
    services = db.query(RenderService).all()
    # 🔴 FIX: استفاده از s.id به جای s.service_id
    service_deploy_times = {s.id: s.last_deploy_at for s in services if s.last_deploy_at}

    # Base filter for error logs
    error_filter = RenderLog.level.in_(["error", "fatal", "critical"])

    if since_deploy and service_deploy_times:
        # 🆕 فیلتر بر اساس آخرین دیپلوی هر سرویس
        conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp >= deploy_time
                )
            )
        # سرویس‌های بدون deploy_at - fallback به 24 ساعت
        # 🔴 FIX: استفاده از s.id به جای s.service_id
        services_without_deploy = [s.id for s in services if not s.last_deploy_at]
        if services_without_deploy:
            fallback_cutoff = datetime.utcnow() - timedelta(hours=24)
            conditions.append(
                and_(
                    RenderLog.service_id.in_(services_without_deploy),
                    RenderLog.timestamp >= fallback_cutoff
                )
            )

        if conditions:
            time_filter = or_(*conditions)
        else:
            time_filter = None
    else:
        time_filter = None

    # لاگ‌های خطای منتقل نشده (پس از دیپلوی)
    pending_query = db.query(RenderLog).filter(
        error_filter,
        RenderLog.transferred_to_issues == False
    )
    if time_filter is not None:
        pending_query = pending_query.filter(time_filter)
    pending_count = pending_query.count()

    # لاگ‌های منتقل شده
    transferred_count = db.query(RenderLog).filter(
        RenderLog.transferred_to_issues == True
    ).count()

    # 🆕 خطاهای تاریخی (قبل از دیپلوی) که منتقل نشده‌اند
    historical_pending = 0
    if since_deploy and service_deploy_times:
        historical_conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            historical_conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp < deploy_time
                )
            )
        if historical_conditions:
            historical_pending = db.query(RenderLog).filter(
                error_filter,
                RenderLog.transferred_to_issues == False,
                or_(*historical_conditions)
            ).count()

    return {
        "success": True,
        "pending_errors": pending_count,
        "transferred_errors": transferred_count,
        "can_transfer": pending_count > 0,
        # 🆕 اطلاعات تکمیلی
        "since_deploy": since_deploy,
        "historical_pending": historical_pending if since_deploy else None,
        "total_pending": pending_count + historical_pending if since_deploy else pending_count
    }


from fastapi.responses import StreamingResponse
import asyncio

@router.post("/transfer-errors-stream")
async def transfer_errors_stream(
    service_ids: Optional[List[str]] = Query(None),
    hours: int = 24,
    mode: str = "since_deploy",
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    انتقال لاگ‌های خطا با گزارش پیشرفت لحظه‌ای (SSE)

    Stream events:
    - {"type": "start", "total_logs": N}
    - {"type": "progress", "current": N, "total": N, "status": "..."}
    - {"type": "log_processed", "log_id": X, "action": "transferred|merged|skipped"}
    - {"type": "complete", "transferred": N, "merged": N, "skipped": N}
    - {"type": "error", "message": "..."}

    Args:
        force: اگر True باشد، لاگ‌هایی که قبلاً منتقل شده‌اند هم مجدداً پردازش می‌شوند
    """

    async def event_generator():
        try:
            service = get_log_to_issues_service()

            # 1. شمارش لاگ‌ها
            error_logs = await service._get_error_logs(db, service_ids, hours, mode, force=force)
            total_logs = len(error_logs)

            yield f"data: {json.dumps({'type': 'start', 'total_logs': total_logs, 'message': f'شروع پردازش {total_logs} لاگ خطا...', 'force': force})}\n\n"

            if total_logs == 0:
                # DEBUG: نمایش اطلاعات بیشتر در صورت نبود لاگ
                debug_info = await service._get_debug_info(db, service_ids, hours)
                yield f"data: {json.dumps({'type': 'complete', 'transferred': 0, 'merged': 0, 'skipped': 0, 'message': 'لاگ خطایی یافت نشد', 'debug': debug_info})}\n\n"
                return

            # 2. ساخت نگاشت سرویس-پروژه
            yield f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': total_logs, 'status': 'در حال نگاشت سرویس‌ها به پروژه‌ها...'})}\n\n"
            service_project_map = await service._build_service_project_map(db)

            # DEBUG: نمایش تعداد نگاشت‌ها
            yield f"data: {json.dumps({'type': 'debug', 'message': f'نگاشت سرویس-پروژه: {len(service_project_map)} مورد', 'mappings': list(service_project_map.keys())})}\n\n"

            transferred = 0
            merged = 0
            skipped = 0

            # 3. پردازش هر لاگ با گزارش پیشرفت
            for i, log in enumerate(error_logs):
                try:
                    yield f"data: {json.dumps({'type': 'progress', 'current': i + 1, 'total': total_logs, 'status': f'پردازش لاگ {i + 1} از {total_logs}...', 'service': log.service_name or 'unknown'})}\n\n"

                    result = await service._process_error_log(log, service_project_map, db)

                    action = result.get("status", "skipped")
                    if action == "transferred":
                        transferred += 1
                    elif action == "merged":
                        merged += 1
                    else:
                        skipped += 1

                    yield f"data: {json.dumps({'type': 'log_processed', 'log_id': log.id, 'action': action, 'current': i + 1, 'total': total_logs})}\n\n"

                    # کمی صبر برای جلوگیری از overload
                    await asyncio.sleep(0.1)

                except Exception as e:
                    slog.error(f"Error processing log {log.id}", exception=e)
                    skipped += 1
                    yield f"data: {json.dumps({'type': 'log_error', 'log_id': log.id, 'error': str(e)})}\n\n"

            # 4. آرشیو کردن
            if transferred > 0 or merged > 0:
                yield f"data: {json.dumps({'type': 'progress', 'current': total_logs, 'total': total_logs, 'status': 'در حال آرشیو کردن...'})}\n\n"
                await service._archive_transferred_logs(db, error_logs, service_project_map)

            db.commit()

            yield f"data: {json.dumps({'type': 'complete', 'transferred': transferred, 'merged': merged, 'skipped': skipped, 'message': f'✅ {transferred} یافته جدید منتقل شد، {merged} ایراد ادغام شد'})}\n\n"

        except Exception as e:
            slog.error("Transfer stream error", exception=e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/archive-stale-issues")
async def archive_stale_issues_after_deploy(
    service_id: str,
    deploy_id: str,
    db: Session = Depends(get_db)
):
    """
    بایگانی خودکار ایرادات قدیمی بعد از دیپلوی جدید

    وقتی یک دیپلوی جدید شناسایی می‌شود:
    - ایرادات مربوط به دیپلوی‌های قبلی بایگانی می‌شوند
    - فقط ایرادات دیپلوی جاری باقی می‌مانند

    این endpoint را می‌توان بعد از هر دیپلوی جدید صدا زد
    """
    slog.api_request("POST", "/render/archive-stale-issues",
        service_id=service_id,
        deploy_id=deploy_id
    )

    service = get_log_to_issues_service()
    result = await service.archive_stale_issues_after_deploy(
        service_id=service_id,
        new_deploy_id=deploy_id,
        db=db
    )

    return {
        "success": True,
        **result
    }


# =====================================
# Stats Endpoints
# =====================================

@router.get("/stats")
async def get_log_stats(
    hours: int = 24,
    since_deploy: bool = True,  # 🆕 پیش‌فرض: فقط لاگ‌های بعد از آخرین دیپلوی
    db: Session = Depends(get_db)
):
    """
    آمار لاگ‌ها

    Args:
        hours: بازه زمانی (ساعت) - فقط در حالت since_deploy=False استفاده می‌شود
        since_deploy: اگر True باشد، فقط لاگ‌های بعد از آخرین دیپلوی هر سرویس شمرده می‌شوند
    """
    from sqlalchemy import func, or_, and_

    # 🆕 دریافت آخرین deploy_at هر سرویس
    services = db.query(RenderService).all()
    # 🔴 FIX: استفاده از s.id به جای s.service_id
    service_deploy_times = {s.id: s.last_deploy_at for s in services if s.last_deploy_at}

    # Base query
    if since_deploy and service_deploy_times:
        # 🆕 فیلتر بر اساس آخرین دیپلوی هر سرویس
        # لاگ‌هایی که timestamp آنها بعد از last_deploy_at سرویس مربوطه است
        conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp >= deploy_time
                )
            )
        # اگر سرویسی last_deploy_at نداشته باشد، لاگ‌های 24 ساعت اخیر آن را بگیر
        # 🔴 FIX: استفاده از s.id به جای s.service_id
        services_without_deploy = [s.id for s in services if not s.last_deploy_at]
        if services_without_deploy:
            fallback_cutoff = datetime.utcnow() - timedelta(hours=24)
            conditions.append(
                and_(
                    RenderLog.service_id.in_(services_without_deploy),
                    RenderLog.timestamp >= fallback_cutoff
                )
            )

        if conditions:
            base_filter = or_(*conditions)
        else:
            base_filter = RenderLog.timestamp >= (datetime.utcnow() - timedelta(hours=24))
    else:
        # حالت قدیمی: بر اساس hours
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        base_filter = RenderLog.timestamp >= cutoff

    # تعداد کل
    total = db.query(RenderLog).filter(base_filter).count()

    # تعداد بر اساس سطح
    level_counts = db.query(
        RenderLog.level,
        func.count(RenderLog.id)
    ).filter(base_filter).group_by(RenderLog.level).all()

    # تعداد بر اساس سرویس
    service_counts = db.query(
        RenderLog.service_id,
        RenderLog.service_name,
        func.count(RenderLog.id)
    ).filter(base_filter).group_by(RenderLog.service_id, RenderLog.service_name).all()

    # 🆕 آمار تاریخی (قبل از دیپلوی) - فقط برای نمایش
    historical_error_count = 0
    if since_deploy and service_deploy_times:
        historical_conditions = []
        for service_id, deploy_time in service_deploy_times.items():
            historical_conditions.append(
                and_(
                    RenderLog.service_id == service_id,
                    RenderLog.timestamp < deploy_time,
                    RenderLog.level == "error"
                )
            )
        if historical_conditions:
            historical_error_count = db.query(RenderLog).filter(
                or_(*historical_conditions)
            ).count()

    return {
        "success": True,
        "period_hours": hours if not since_deploy else None,
        "since_deploy": since_deploy,
        "total_logs": total,
        "by_level": {level: count for level, count in level_counts},
        "by_service": [
            {"service_id": sid, "service_name": sname, "count": count}
            for sid, sname, count in service_counts
        ],
        "error_count": next((c for l, c in level_counts if l == "error"), 0),
        "warning_count": next((c for l, c in level_counts if l == "warn"), 0),
        # 🆕 آمار تاریخی
        "historical_error_count": historical_error_count if since_deploy else None,
        "deploy_info": {
            sid: dt.isoformat() if dt else None
            for sid, dt in service_deploy_times.items()
        } if since_deploy else None
    }


# =====================================
# Scheduler Status Endpoints
# =====================================

@router.get("/scheduler/status")
async def get_scheduler_status():
    """وضعیت scheduler و job های فعال"""
    try:
        from ...services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()
        return {
            "success": True,
            **scheduler.get_jobs_info()
        }
    except Exception as e:
        slog.error("Failed to get scheduler status", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/scheduler/trigger-auto-transfer")
async def trigger_auto_transfer_now():
    """اجرای فوری auto-transfer"""
    try:
        from ...services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()

        # اجرای مستقیم به جای trigger job
        result = await scheduler._run_auto_transfer()

        return {
            "success": True,
            "message": "Auto-transfer executed",
            "result": result
        }
    except Exception as e:
        slog.error("Failed to trigger auto-transfer", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/auto-transfer/debug")
async def debug_auto_transfer(db: Session = Depends(get_db)):
    """
    🔍 تشخیص مشکلات انتقال خودکار

    بررسی می‌کند:
    1. تنظیمات auto-transfer فعال است؟
    2. scheduler اجرا می‌شود؟
    3. سرویس‌ها به پروژه نگاشت شده‌اند؟
    4. لاگ خطایی برای انتقال وجود دارد؟
    """
    from ...services.log_to_issues_service import get_log_to_issues_service
    from ...services.background_scheduler import get_background_scheduler
    from datetime import datetime, timedelta

    diagnosis = {
        "timestamp": datetime.utcnow().isoformat(),
        "settings": {},
        "scheduler": {},
        "service_mapping": {},
        "error_logs": {},
        "issues": [],
        "recommendations": []
    }

    try:
        # 1. بررسی تنظیمات
        settings = db.query(RenderLogSettings).first()
        if settings:
            diagnosis["settings"] = {
                "auto_transfer_enabled": settings.auto_transfer_enabled,
                "auto_transfer_mode": getattr(settings, 'auto_transfer_mode', 'since_deploy') or 'since_deploy',
                "auto_transfer_interval_minutes": settings.auto_transfer_interval_minutes,
                "auto_transfer_hours_back": settings.auto_transfer_hours_back,
                "last_auto_transfer": settings.last_auto_transfer.isoformat() if settings.last_auto_transfer else None
            }
            if not settings.auto_transfer_enabled:
                diagnosis["issues"].append("❌ انتقال خودکار غیرفعال است!")
                diagnosis["recommendations"].append("✅ از تب تنظیمات Render Logs، گزینه 'انتقال خودکار خطاها' را فعال کنید")
        else:
            diagnosis["settings"] = {"error": "تنظیمات یافت نشد"}
            diagnosis["issues"].append("❌ تنظیمات Render Logs ایجاد نشده")

        # 2. بررسی scheduler
        try:
            scheduler = get_background_scheduler()
            jobs_info = scheduler.get_jobs_info()
            diagnosis["scheduler"] = jobs_info

            if not jobs_info.get("running"):
                diagnosis["issues"].append("❌ Scheduler اجرا نمی‌شود!")
                diagnosis["recommendations"].append("✅ سرور را ری‌استارت کنید")
            elif not any(j["id"] == "auto_transfer_errors" for j in jobs_info.get("jobs", [])):
                diagnosis["issues"].append("⚠️ Job انتقال خودکار ثبت نشده (احتمالاً چون auto_transfer_enabled=False)")
                diagnosis["recommendations"].append("✅ انتقال خودکار را فعال کرده و ذخیره کنید")
        except Exception as se:
            diagnosis["scheduler"] = {"error": str(se)}

        # 3. بررسی نگاشت سرویس-پروژه
        try:
            service = get_log_to_issues_service()
            service_map = await service._build_service_project_map(db)

            # دریافت همه سرویس‌ها
            services = db.query(RenderService).all()

            mapped_count = 0
            unmapped_services = []

            for s in services:
                if s.id in service_map:
                    mapped_count += 1
                else:
                    unmapped_services.append({
                        "id": s.id,
                        "name": s.name,
                        "manual_project_id": s.project_id
                    })

            diagnosis["service_mapping"] = {
                "total_services": len(services),
                "mapped_services": mapped_count,
                "unmapped_services": unmapped_services,
                "mapping_details": {k: v["project_name"] for k, v in service_map.items()}
            }

            if unmapped_services:
                diagnosis["issues"].append(f"⚠️ {len(unmapped_services)} سرویس بدون نگاشت به پروژه")
                diagnosis["recommendations"].append("✅ برای هر سرویس، project_id را در تنظیمات سرویس تعیین کنید")

        except Exception as me:
            diagnosis["service_mapping"] = {"error": str(me)}

        # 4. بررسی لاگ‌های خطا
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)

            total_errors = db.query(RenderLog).filter(
                RenderLog.timestamp >= cutoff,
                RenderLog.level.in_(["error", "fatal", "critical"])
            ).count()

            transferred_errors = db.query(RenderLog).filter(
                RenderLog.timestamp >= cutoff,
                RenderLog.level.in_(["error", "fatal", "critical"]),
                RenderLog.transferred_to_issues == True
            ).count()

            not_transferred = total_errors - transferred_errors

            diagnosis["error_logs"] = {
                "period": "24 hours",
                "total_error_logs": total_errors,
                "already_transferred": transferred_errors,
                "not_transferred": not_transferred
            }

            if total_errors == 0:
                diagnosis["issues"].append("ℹ️ هیچ لاگ خطایی در ۲۴ ساعت گذشته وجود ندارد")
            elif not_transferred > 0 and settings and settings.auto_transfer_enabled:
                diagnosis["issues"].append(f"⚠️ {not_transferred} خطا منتظر انتقال هستند")
                diagnosis["recommendations"].append("✅ روی 'اجرای فوری انتقال' کلیک کنید یا منتظر اجرای خودکار بمانید")

        except Exception as le:
            diagnosis["error_logs"] = {"error": str(le)}

        # نتیجه‌گیری
        if not diagnosis["issues"]:
            diagnosis["status"] = "✅ همه چیز سالم به نظر می‌رسد"
        else:
            diagnosis["status"] = f"⚠️ {len(diagnosis['issues'])} مشکل شناسایی شد"

        return {
            "success": True,
            "diagnosis": diagnosis
        }

    except Exception as e:
        slog.error("Auto-transfer debug failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/auto-transfer/force-transfer")
async def force_transfer_all_errors(
    hours_back: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=100),  # 🆕 محدود کردن تعداد برای تست
    db: Session = Depends(get_db)
):
    """
    🔴 انتقال اجباری خطاها با logging کامل

    - limit: حداکثر تعداد لاگ برای پردازش (برای تست)
    """
    from ...services.log_to_issues_service import get_log_to_issues_service
    from ...models.project import Project, ProjectIssue

    debug_log = []

    try:
        service = get_log_to_issues_service()
        service.initialize()

        # ریست کردن فلگ transferred برای تست
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        reset_count = db.query(RenderLog).filter(
            RenderLog.timestamp >= cutoff,
            RenderLog.level.in_(["error", "fatal", "critical"]),
            RenderLog.transferred_to_issues == True
        ).update({RenderLog.transferred_to_issues: False})
        db.commit()
        debug_log.append(f"✅ Reset {reset_count} transferred flags")

        # شمارش ایرادات قبل
        issues_before = db.query(ProjectIssue).count()
        debug_log.append(f"📊 Issues before: {issues_before}")

        # دریافت لاگ‌های خطا (محدود)
        error_logs = db.query(RenderLog).filter(
            RenderLog.timestamp >= cutoff,
            RenderLog.level.in_(["error", "fatal", "critical"]),
            RenderLog.transferred_to_issues == False
        ).order_by(RenderLog.timestamp.desc()).limit(limit).all()

        debug_log.append(f"📋 Found {len(error_logs)} error logs to process")

        # ساخت service-project map
        service_project_map = await service._build_service_project_map(db)
        debug_log.append(f"🗺️ Service mapping: {len(service_project_map)} services mapped")

        # پردازش دستی هر لاگ با logging کامل
        transferred = 0
        merged = 0
        skipped = 0
        errors_list = []

        for i, log in enumerate(error_logs):
            try:
                debug_log.append(f"\n--- Log {i+1}/{len(error_logs)} ---")
                debug_log.append(f"   Service: {log.service_name} ({log.service_id})")
                debug_log.append(f"   Message: {(log.message or '')[:100]}...")

                # بررسی mapping
                if log.service_id not in service_project_map:
                    debug_log.append(f"   ❌ SKIPPED: service not mapped")
                    skipped += 1
                    continue

                mapping = service_project_map[log.service_id]
                project_id = mapping["project_id"]
                debug_log.append(f"   ✅ Mapped to project: {mapping['project_name']}")

                # دریافت پروژه
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    debug_log.append(f"   ❌ SKIPPED: project not found")
                    skipped += 1
                    continue

                # تحلیل AI
                debug_log.append(f"   🧠 Running AI analysis...")
                ai_analysis = await service._analyze_error_with_ai(log, project)
                debug_log.append(f"   📝 AI result: {ai_analysis.get('error_type', 'unknown')}")

                # جستجوی ایراد مشابه
                existing = service._find_similar_issue_in_db(
                    db, project_id, log.message, ai_analysis.get("error_type", "")
                )

                if existing:
                    existing.occurrences = (existing.occurrences or 0) + 1
                    existing.updated_at = datetime.utcnow()
                    merged += 1
                    debug_log.append(f"   🔄 MERGED with existing issue {existing.id}")
                else:
                    # ایجاد ایراد جدید
                    priority_map = {"high": 2, "medium": 3, "low": 4, "critical": 1}
                    new_issue = ProjectIssue(
                        project_id=project_id,
                        title=ai_analysis.get("error_type", "خطای Render")[:200] or (log.message or "")[:200],
                        description=ai_analysis.get("explanation", log.message),
                        solution=ai_analysis.get("suggested_fix", "بررسی لاگ کامل"),
                        priority=priority_map.get(ai_analysis.get("priority", "medium"), 3),
                        status="open",
                        source="render_logs",
                        source_data=json.dumps({
                            "log_id": log.id,
                            "service_name": log.service_name,
                            "ai_analysis": ai_analysis
                        }, ensure_ascii=False),
                        occurrences=1,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_issue)
                    transferred += 1
                    debug_log.append(f"   ✅ CREATED new issue")

                # علامت‌گذاری لاگ
                log.transferred_to_issues = True
                log.transferred_at = datetime.utcnow()

            except Exception as e:
                debug_log.append(f"   ❌ ERROR: {str(e)}")
                errors_list.append({"log_id": log.id, "error": str(e)})

        # Commit
        try:
            db.commit()
            debug_log.append(f"\n✅ Committed successfully")
        except Exception as ce:
            debug_log.append(f"\n❌ Commit failed: {str(ce)}")
            db.rollback()

        # شمارش بعد
        issues_after = db.query(ProjectIssue).count()
        debug_log.append(f"📊 Issues after: {issues_after}")
        debug_log.append(f"📊 New issues: {issues_after - issues_before}")

        return {
            "success": True,
            "summary": {
                "reset_count": reset_count,
                "logs_processed": len(error_logs),
                "transferred": transferred,
                "merged": merged,
                "skipped": skipped,
                "issues_before": issues_before,
                "issues_after": issues_after,
                "new_issues": issues_after - issues_before
            },
            "errors": errors_list,
            "debug_log": debug_log
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "debug_log": debug_log
        }


# =====================================
# WebSocket Endpoints
# =====================================

@router.websocket("/ws/stream")
async def websocket_log_stream(websocket: WebSocket):
    """
    WebSocket endpoint برای streaming لاگ‌های زنده

    Protocol:
    1. Client متصل می‌شود
    2. Client می‌تواند فیلترها را ارسال کند: {"type": "set_filters", "filters": {...}}
    3. Server لاگ‌های جدید را broadcast می‌کند: {"type": "new_logs", "logs": [...]}
    4. Client می‌تواند ping ارسال کند: {"type": "ping"}
    5. Server پاسخ می‌دهد: {"type": "pong"}
    """
    from ...services.log_stream_service import get_log_stream_service

    await websocket.accept()
    client_id = str(uuid.uuid4())

    slog.info("WebSocket client connected", client_id=client_id)

    try:
        # ثبت کلاینت
        stream_service = get_log_stream_service()
        await stream_service.register_client(client_id, websocket)

        # ارسال پیام خوش‌آمدگویی
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to log stream"
        })

        # حلقه دریافت پیام
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "set_filters":
                    # به‌روزرسانی فیلترها
                    filters = data.get("filters", {})
                    await stream_service.update_client_filters(client_id, filters)
                    await websocket.send_json({
                        "type": "filters_updated",
                        "filters": filters
                    })

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "start_polling":
                    await stream_service.start_polling()
                    await websocket.send_json({
                        "type": "polling_started"
                    })

                elif msg_type == "stop_polling":
                    await stream_service.stop_polling()
                    await websocket.send_json({
                        "type": "polling_stopped"
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                slog.warning("WebSocket message error", client_id=client_id, exception=e)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        slog.error("WebSocket error", client_id=client_id, exception=e)
    finally:
        # حذف کلاینت
        await stream_service.unregister_client(client_id)
        slog.info("WebSocket client disconnected", client_id=client_id)


@router.get("/stream/status")
async def get_stream_status():
    """وضعیت سرویس streaming"""
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    return {
        "success": True,
        **service.get_status()
    }


@router.post("/stream/start")
async def start_server_polling():
    """شروع server-side polling"""
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    await service.start_polling()

    return {
        "success": True,
        "message": "Server-side polling started"
    }


@router.post("/stream/stop")
async def stop_server_polling():
    """توقف server-side polling"""
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    await service.stop_polling()

    return {
        "success": True,
        "message": "Server-side polling stopped"
    }


@router.get("/stream/latest")
async def get_latest_logs_for_stream(
    service_ids: Optional[List[str]] = Query(None),
    levels: Optional[List[str]] = Query(None),
    limit: int = 100,
    since_id: Optional[str] = None
):
    """
    دریافت آخرین لاگ‌ها (برای HTTP polling fallback)

    این endpoint برای کلاینت‌هایی است که نمی‌توانند
    از WebSocket استفاده کنند
    """
    from ...services.log_stream_service import get_log_stream_service

    service = get_log_stream_service()
    return await service.fetch_latest_logs(
        service_ids=service_ids,
        levels=levels,
        limit=limit,
        since_id=since_id
    )


# =====================================
# 🆕 Inspector Chat - چت با مدل‌های AI
# =====================================

class InspectorChatMessage(BaseModel):
    """یک پیام در چت بازرس"""
    role: str  # user, assistant
    content: str


class InspectorSessionContext(BaseModel):
    """اطلاعات جلسه برای چت هوشمند"""
    has_investigation: bool = False
    has_errors: bool = False
    models_from_investigation: bool = False


class InspectorChatRequest(BaseModel):
    """درخواست چت با بازرس"""
    model_id: str
    message: str
    project_id: str
    # Context
    backend_logs: Optional[List[dict]] = None
    frontend_url: Optional[str] = None
    project_files: Optional[List[dict]] = None  # [{path, content}]
    project_structure: Optional[dict] = None
    chat_history: Optional[List[InspectorChatMessage]] = None
    session_context: Optional[InspectorSessionContext] = None
    # تنظیمات
    max_tokens: int = 16384
    temperature: float = 0.7
    stream: bool = False
    # 🆕 (inspector-scan) — context اضافی برای intent resolver. اگر این
    # فیلدها در request باشند، scan موردی هوشمندانه‌تر trigger می‌شود.
    # همگی optional — backward compatible.
    console_logs: Optional[List[dict]] = None
    page_url: Optional[str] = None
    api_paths: Optional[List[str]] = None
    linked_task: Optional[dict] = None  # {target_files, title, ...}
    screenshots: Optional[List[dict]] = None
    mode: Optional[str] = None  # "chat" | "visual_debug"
    session_id: Optional[int] = None  # اگر فرانت‌اند session فعال را می‌داند
    enable_selective_scan: bool = True  # برای flag-off اگر نیاز شد


class InspectorMultiChatRequest(BaseModel):
    """درخواست چت با چند مدل"""
    model_ids: List[str]
    message: str
    project_id: str
    # Context
    backend_logs: Optional[List[dict]] = None
    frontend_url: Optional[str] = None
    project_files: Optional[List[dict]] = None
    project_structure: Optional[dict] = None
    chat_history: Optional[List[InspectorChatMessage]] = None
    session_context: Optional[InspectorSessionContext] = None
    # تنظیمات
    max_tokens: int = 16384
    temperature: float = 0.7


def build_inspector_system_prompt(
    project_id: str,
    backend_logs: Optional[List[dict]] = None,
    frontend_url: Optional[str] = None,
    project_files: Optional[List[dict]] = None,
    project_structure: Optional[dict] = None,
    db: Session = None,
    session_context: Optional[dict] = None
) -> str:
    """ساخت system prompt با تمام context های پروژه"""

    prompt_parts = [
        "# 🔍 بازرس ویژه پروژه",
        "",
        "تو یک بازرس هوشمند و متخصص هستی که به تمام داده‌های پروژه دسترسی داری.",
        "وظیفه تو تحلیل، عیب‌یابی، بررسی امنیت و کمک به توسعه‌دهنده است.",
        "",
        "## دسترسی‌های تو:",
        "- لاگ‌های بک‌اند (زنده)",
        "- URL فرانت‌اند (پیش‌نمایش)",
        "- فایل‌های پروژه",
        "- ساختار پروژه",
        "",
    ]

    # اطلاعات پروژه از دیتابیس
    if db:
        try:
            from ...models.project import Project
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                prompt_parts.extend([
                    f"## پروژه: {project.name}",
                    f"- توضیحات: {project.description or 'ندارد'}",
                    f"- نوع: {getattr(project, 'type', 'نامشخص')}",
                    f"- تاریخ ایجاد: {project.created_at}",
                    "",
                ])
        except Exception as e:
            slog.warning("Could not fetch project info", error=str(e))

    # لاگ‌های بک‌اند
    if backend_logs:
        prompt_parts.extend([
            "## 📋 لاگ‌های بک‌اند (آخرین لاگ‌ها):",
            "```",
        ])
        for log in backend_logs[-30:]:  # آخرین 30 لاگ
            level = log.get('level', 'info').upper()
            timestamp = log.get('timestamp', '')[:19]
            message = log.get('message', '')[:200]
            prompt_parts.append(f"[{timestamp}] [{level}] {message}")
        prompt_parts.extend(["```", ""])

        # خلاصه خطاها
        errors = [l for l in backend_logs if l.get('level') == 'error']
        if errors:
            prompt_parts.extend([
                f"### ⚠️ {len(errors)} خطا شناسایی شده:",
            ])
            for err in errors[-5:]:
                prompt_parts.append(f"- {err.get('message', '')[:100]}")
            prompt_parts.append("")

    # URL فرانت‌اند
    if frontend_url:
        prompt_parts.extend([
            f"## 🌐 URL فرانت‌اند:",
            f"- {frontend_url}",
            "",
        ])

    # ساختار پروژه
    if project_structure:
        prompt_parts.extend([
            "## 📁 ساختار پروژه:",
            "```",
            json.dumps(project_structure, ensure_ascii=False, indent=2)[:2000],
            "```",
            "",
        ])

    # فایل‌های پروژه
    if project_files:
        prompt_parts.extend([
            "## 📄 فایل‌های پروژه:",
        ])
        for f in project_files[:10]:  # حداکثر 10 فایل
            path = f.get('path', '')
            content = f.get('content', '')[:3000]  # حداکثر 3000 کاراکتر
            prompt_parts.extend([
                f"### {path}",
                "```",
                content,
                "```",
                "",
            ])

    prompt_parts.extend([
        "---",
        "## دستورالعمل:",
        "1. پاسخ‌ها را به فارسی بده",
        "2. اگر خطایی در لاگ‌ها دیدی، آن را تحلیل کن",
        "3. پیشنهادات عملی و کاربردی بده",
        "4. اگر کد نیاز بود، کد کامل و قابل اجرا بنویس",
        "5. امنیت را همیشه در نظر بگیر",
        "",
        "## 🔴 اصل حیاتی — تحلیل عمیق‌تر در هر تلاش مجدد:",
        "اگر کاربر مشکلی را دوباره مطرح کرد یا گفت «هنوز کار نمیکنه» / «بازم خطا داد» / «نشد»:",
        "- **هرگز** فقط همان فایل‌های قبلی را بررسی نکن — دامنه بررسی را وسیع‌تر کن",
        "- ابتدا از خودت بپرس: «چرا فیکس قبلی کار نکرد؟» — شاید مشکل در فایل/لایه دیگری است",
        "- فایل‌های مرتبط جدید بررسی کن: config ها، middleware ها، types، helpers، services",
        "- زنجیره فراخوانی را دنبال کن: مثلاً اگر API خطا میده، فقط route رو نگاه نکن — service → model → migration → config همه رو ببین",
        "- اگر یک فایل قبلاً بررسی و اصلاح شده ولی مشکل باقیه، حتماً فایل‌های وابسته به آن فایل را بررسی کن",
        "- **هر بار** باید دامنه تحلیل بزرگ‌تر از دفعه قبل باشد — هرگز دامنه را محدودتر نکن",
    ])

    # 🆕 دستورالعمل‌های هوشمند بر اساس context جلسه
    if session_context:
        has_investigation = session_context.get('has_investigation', False)
        has_errors = session_context.get('has_errors', False)
        from_investigation = session_context.get('models_from_investigation', False)

        if has_investigation or has_errors:
            prompt_parts.extend([
                "",
                "## ⚡ زمینه جلسه فعال:",
            ])

            if has_investigation:
                prompt_parts.extend([
                    "- در این جلسه قبلاً یک بررسی ریشه‌ای خطا (investigation) انجام شده.",
                    "- گزارش بررسی در تاریخچه چت موجود است. از آن استفاده کن.",
                    "- اگر کاربر سؤالی درباره خطا بپرسد، بر اساس گزارش بررسی قبلی پاسخ بده.",
                ])

            if has_errors:
                prompt_parts.extend([
                    "- خطاهای فرانت‌اند (JavaScript errors) در تاریخچه ثبت شده‌اند.",
                    "- این خطاها از مرورگر کاربر گرفته شده‌اند (window.onerror, console.error).",
                ])

            if from_investigation:
                prompt_parts.extend([
                    "- مدل فعلی از مودال بررسی/اصلاح انتخاب شده.",
                    "- کاربر احتمالاً ادامه بررسی خطا را می‌خواهد.",
                ])

            prompt_parts.extend([
                "",
                "### نحوه پاسخ‌دهی هوشمند:",
                "- اگر سؤال است: مستقیم و دقیق پاسخ بده با ارجاع به گزارش/خطاهای قبلی",
                "- اگر درخواست اقدام است: مراحل دقیق را بنویس و کد اصلاحی کامل ارائه بده",
                "- همیشه به تاریخچه چت نگاه کن و context قبلی را از دست نده",
            ])

    return "\n".join(prompt_parts)


@router.post("/inspector/chat")
async def inspector_chat(
    request: InspectorChatRequest,
    db: Session = Depends(get_db)
):
    """
    چت با مدل AI در تب بازرس ویژه

    این endpoint تمام context های پروژه را به مدل می‌دهد:
    - لاگ‌های بک‌اند
    - URL فرانت‌اند
    - فایل‌های پروژه
    - ساختار پروژه
    """
    slog.api_request("POST", "/render/inspector/chat",
        model=request.model_id,
        project_id=request.project_id
    )

    try:
        from ...services.ai_manager import get_ai_manager
        from ...services.ai_base import Message

        # 🆕 (inspector-scan) — قبل از فراخوانی chat، intent را resolve کن.
        # اگر کاربر در حال درخواست بررسی/اصلاح است، به‌جای پاسخ یک‌شات سطحی،
        # یک scan موردی deep در background trigger می‌کنیم و پاسخ مناسب
        # برمی‌گردانیم. هیچ‌چیز در مرکز نظارت ذخیره نمی‌شود — تنها در همان
        # session chat لاگ می‌شود.
        if request.enable_selective_scan:
            try:
                from ...services.inspector_intent_resolver import (
                    resolve_intent_from_chat_context,
                )
                from ...services.inspector_scan_bridge import (
                    trigger_inspector_selective_scan,
                    get_or_create_active_session_for_project,
                    is_scan_active_for_session,
                )

                # 🆕 (v3 chat-history) — forward chat_history برای
                # continuation detection
                _hist_v3: List[Dict[str, Any]] = []
                if request.chat_history:
                    try:
                        _hist_v3 = [
                            {"role": m.role, "content": m.content}
                            for m in request.chat_history
                            if hasattr(m, "role") and hasattr(m, "content")
                        ]
                    except Exception:
                        _hist_v3 = []

                intent = resolve_intent_from_chat_context(
                    user_message=request.message,
                    backend_logs=request.backend_logs,
                    console_logs=request.console_logs,
                    frontend_url=request.frontend_url,
                    page_url=request.page_url,
                    api_paths=request.api_paths,
                    linked_task=request.linked_task,
                    screenshots=request.screenshots,
                    mode=request.mode or "chat",
                    chat_history=_hist_v3 or None,
                )

                if intent.should_scan:
                    session_id = request.session_id or get_or_create_active_session_for_project(
                        request.project_id
                    )
                    if not session_id:
                        slog.warning(
                            "selective_scan skipped — could not resolve session",
                            project_id=request.project_id,
                        )
                    elif is_scan_active_for_session(session_id):
                        return {
                            "success": True,
                            "model_id": request.model_id,
                            "kind": "scan_already_running",
                            "content": (
                                "⚠️ یک اسکن موردی دیگر در این session در حال اجراست. "
                                "لطفاً منتظر بمانید تا کامل شود، یا فقط یک سؤال info-only بپرسید."
                            ),
                            "session_id": session_id,
                        }
                    else:
                        scan_result = await trigger_inspector_selective_scan(
                            session_id=session_id,
                            project_id=request.project_id,
                            user_message=request.message,
                            intent=intent,
                            model_id=request.model_id,
                        )
                        # 🆕 (clarify-first) — deep scan قبل از start سوال logged
                        if scan_result.get("status") == "needs_clarification":
                            return {
                                "success": True,
                                "model_id": request.model_id,
                                "kind": "scan_clarification_needed",
                                "session_id": session_id,
                                "content": (
                                    "🤔 قبل از شروع اسکن عمیق، یک سوال کوتاه دارم — "
                                    "لطفاً به سوال در چت پاسخ بده."
                                ),
                            }
                        if scan_result.get("success"):
                            return {
                                "success": True,
                                "model_id": request.model_id,
                                "kind": "scan_initiated",
                                "scan_id": scan_result["scan_id"],
                                "session_id": session_id,
                                "content": (
                                    "🔍 **در حال اسکن موردی عمیق...**\n\n"
                                    f"بر اساس پیامتان و context موجود (logs/URL/screenshots) "
                                    f"تشخیص داده شد که نیاز به بررسی عمیق دارد. "
                                    f"دلیل: `{intent.reason}` — اطمینان: {int(intent.confidence * 100)}%.\n\n"
                                    f"تعداد {len(intent.custom_paths)} مسیر را scope کردم. "
                                    "پیشنهاد‌ها چند دقیقه دیگر در همین چت ظاهر می‌شوند."
                                ),
                                "intent": {
                                    "reason": intent.reason,
                                    "matched_keywords": intent.matched_keywords,
                                    "custom_paths": intent.custom_paths[:10],
                                    "selected_sections": intent.selected_sections,
                                    "visual_debug": intent.visual_debug,
                                    "confidence": intent.confidence,
                                },
                            }
                        else:
                            slog.warning(
                                "selective_scan trigger failed; fallback to chat",
                                error=scan_result.get("error"),
                            )
            except Exception as _intent_e:
                slog.warning("selective_scan path raised; fallback to chat",
                             error=str(_intent_e))

        ai_manager = get_ai_manager()

        # ساخت system prompt با context
        session_ctx = request.session_context.dict() if request.session_context else None
        system_prompt = build_inspector_system_prompt(
            project_id=request.project_id,
            backend_logs=request.backend_logs,
            frontend_url=request.frontend_url,
            project_files=request.project_files,
            project_structure=request.project_structure,
            db=db,
            session_context=session_ctx
        )

        # ساخت messages
        messages = [Message(role="system", content=system_prompt)]

        # افزودن تاریخچه چت - بیشتر اگر context جلسه داریم
        history_limit = 50 if session_ctx else 20
        if request.chat_history:
            for msg in request.chat_history[-history_limit:]:
                # نقش system را به user تبدیل کن (بعضی مدل‌ها system اضافی نمی‌پذیرند)
                role = msg.role if msg.role in ('user', 'assistant') else 'user'
                messages.append(Message(role=role, content=msg.content))

        # افزودن پیام جدید کاربر
        messages.append(Message(role="user", content=request.message))

        slog.ai_call(request.model_id, "inspector chat",
            messages_count=len(messages),
            has_logs=bool(request.backend_logs),
            has_files=bool(request.project_files),
            has_session_context=bool(session_ctx)
        )

        # ارسال به AI
        response = await ai_manager.generate(
            model_id=request.model_id,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        slog.success("Inspector chat response generated",
            model=response.model_id,
            tokens_used=response.tokens_used
        )

        return {
            "success": True,
            "model_id": response.model_id,
            "content": response.content,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
            "finish_reason": response.finish_reason
        }

    except Exception as e:
        slog.error("Inspector chat failed", exception=e, model=request.model_id)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/inspector/chat/multi")
async def inspector_chat_multi(
    request: InspectorMultiChatRequest,
    db: Session = Depends(get_db)
):
    """
    چت با چند مدل AI به صورت موازی

    پاسخ همه مدل‌های انتخاب شده را برمی‌گرداند
    """
    slog.api_request("POST", "/render/inspector/chat/multi",
        models=request.model_ids,
        project_id=request.project_id
    )

    try:
        from ...services.ai_manager import get_ai_manager
        from ...services.ai_base import Message

        ai_manager = get_ai_manager()

        # ساخت system prompt با context
        session_ctx = request.session_context.dict() if request.session_context else None
        system_prompt = build_inspector_system_prompt(
            project_id=request.project_id,
            backend_logs=request.backend_logs,
            frontend_url=request.frontend_url,
            project_files=request.project_files,
            project_structure=request.project_structure,
            db=db,
            session_context=session_ctx
        )

        # ساخت messages
        messages = [Message(role="system", content=system_prompt)]

        # افزودن تاریخچه چت - بیشتر اگر context جلسه داریم
        history_limit = 50 if session_ctx else 20
        if request.chat_history:
            for msg in request.chat_history[-history_limit:]:
                role = msg.role if msg.role in ('user', 'assistant') else 'user'
                messages.append(Message(role=role, content=msg.content))

        # افزودن پیام جدید کاربر
        messages.append(Message(role="user", content=request.message))

        slog.ai_call(",".join(request.model_ids), "inspector multi-chat",
            models_count=len(request.model_ids),
            has_session_context=bool(session_ctx)
        )

        # ارسال به همه مدل‌ها به صورت موازی
        responses = await ai_manager.generate_parallel(
            model_ids=request.model_ids,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        successful = [r for r in responses if not r.error]
        slog.success("Inspector multi-chat completed",
            total=len(responses),
            successful=len(successful)
        )

        return {
            "success": True,
            "responses": [
                {
                    "model_id": r.model_id,
                    "content": r.content,
                    "tokens_used": r.tokens_used,
                    "latency_ms": r.latency_ms,
                    "error": r.error
                }
                for r in responses
            ],
            "total_models": len(request.model_ids),
            "successful_count": len(successful)
        }

    except Exception as e:
        slog.error("Inspector multi-chat failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/inspector/models")
async def get_available_models_for_inspector(db: Session = Depends(get_db)):
    """
    دریافت لیست مدل‌های موجود برای استفاده در بازرس

    همه مدل‌ها (فعال و غیرفعال) برگردانده می‌شوند
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY
        from ...services.ai_manager import get_ai_manager
        from ...models.ai_profile import ModelSettings

        # دریافت provider های فعال
        available_providers = []
        try:
            ai_manager = get_ai_manager()
            available_providers = ai_manager.get_available_providers()
        except Exception as e:
            slog.warning("Could not get AI manager", error=str(e))

        # دریافت تنظیمات از دیتابیس
        db_settings = db.query(ModelSettings).all() if db else []
        settings_map = {s.model_id: s for s in db_settings}

        # گروه‌بندی بر اساس provider
        models_by_provider = {}
        models_list = []

        for model_id, model in MODEL_REGISTRY.items():
            provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)

            # بررسی فعال بودن
            setting = settings_map.get(model_id)
            is_enabled = setting.enabled if setting else True
            provider_available = provider in [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]

            model_info = {
                "id": model_id,
                "name": model.name,
                "provider": provider,
                "context_window": getattr(model, 'context_window', 4096),
                "enabled": is_enabled and provider_available,
                "provider_available": provider_available
            }

            models_list.append(model_info)

            if provider not in models_by_provider:
                models_by_provider[provider] = []
            models_by_provider[provider].append(model_info)

        # بررسی اتصال GitHub - همان روش deploy-keys/status
        from ...models.setting import Setting

        # روش 1: از environment
        github_key = os.environ.get("GITHUB_TOKEN", "")

        # روش 2: اگر نبود، از دیتابیس بخون و در environment ست کن
        if not github_key:
            try:
                github_key = Setting.get_value(db, "api_key_github") or ""
                if github_key:
                    os.environ["GITHUB_TOKEN"] = github_key
                    slog.info("Loaded GitHub token from database and set in environment")
            except Exception as e:
                slog.warning("Failed to get GitHub token from DB", error=str(e))

        github_connected = bool(github_key) and len(github_key) > 10

        slog.info("GitHub connection check",
            has_env_token=bool(os.environ.get("GITHUB_TOKEN")),
            token_length=len(github_key) if github_key else 0,
            connected=github_connected
        )

        return {
            "success": True,
            "models": models_list,
            "models_by_provider": models_by_provider,
            "total": len(models_list),
            "available_providers": [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers],
            "github_connected": github_connected
        }

    except Exception as e:
        slog.error("Failed to get models for inspector", exception=e)
        return {
            "success": False,
            "models": [],
            "models_by_provider": {},
            "error": str(e),
            "github_connected": False
        }


@router.get("/inspector/smart-select-model/{project_id}")
async def smart_select_model_endpoint(project_id: str, db: Session = Depends(get_db)):
    """انتخاب هوشمند مدل بر اساس آرشیو چت‌ها و مدل‌های فعال"""
    try:
        selected = await _smart_select_model(db, project_id)
        return {"success": True, "model_id": selected}
    except Exception as e:
        return {"success": False, "model_id": "gemini-2.0-flash", "error": str(e)}


# =====================================
# 🆕 انتخاب هوشمند و همکاری مدل‌ها
# =====================================

class SmartTaskRequest(BaseModel):
    """درخواست اجرای کار هوشمند"""
    task: str  # توضیح کار
    project_id: str
    auto_select: bool = True  # انتخاب خودکار مدل
    collaborative: bool = True  # همکاری مدل‌ها
    visual_mode: bool = False  # تعامل بصری با صفحه
    # Context
    backend_logs: Optional[List[dict]] = None
    frontend_url: Optional[str] = None
    project_files: Optional[List[dict]] = None
    github_repo: Optional[str] = None  # مثل owner/repo


class TaskAction(BaseModel):
    """یک اقدام در جریان کار"""
    id: str
    model_id: str
    action_type: str  # click, type, navigate, edit, read, analyze, log
    description: str
    target: Optional[str] = None  # مسیر فایل یا سلکتور CSS
    data: Optional[dict] = None
    status: str = "pending"  # pending, running, done, failed
    result: Optional[str] = None


# ذخیره وضعیت کارهای در حال اجرا (در محیط واقعی از Redis استفاده می‌شود)
active_tasks = {}
task_action_queues = {}


def analyze_task_for_model_selection(task: str) -> dict:
    """تحلیل کار برای انتخاب مدل‌های مناسب"""
    task_lower = task.lower()

    capabilities_needed = []
    suggested_models = []

    # تشخیص نیازهای کار
    if any(x in task_lower for x in ["کد", "code", "برنامه", "program", "فایل", "file", "ویرایش", "edit"]):
        capabilities_needed.append("coding")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o", "gpt-4-turbo"])

    if any(x in task_lower for x in ["تحلیل", "analyze", "بررسی", "review", "خطا", "error", "باگ", "bug"]):
        capabilities_needed.append("analysis")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro"])

    if any(x in task_lower for x in ["امنیت", "security", "آسیب", "vulnerability"]):
        capabilities_needed.append("security")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])

    if any(x in task_lower for x in ["تست", "test", "آزمایش"]):
        capabilities_needed.append("testing")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])

    if any(x in task_lower for x in ["صفحه", "page", "کلیک", "click", "بصری", "visual", "ui", "رابط"]):
        capabilities_needed.append("visual")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])  # مدل‌های با قابلیت vision

    if any(x in task_lower for x in ["گیت", "git", "github", "کامیت", "commit", "پوش", "push"]):
        capabilities_needed.append("git")
        suggested_models.extend(["claude-3-5-sonnet", "gpt-4o"])

    # حذف تکراری‌ها و حفظ ترتیب
    seen = set()
    unique_models = []
    for m in suggested_models:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    return {
        "capabilities_needed": capabilities_needed,
        "suggested_models": unique_models[:5],  # حداکثر 5 مدل
        "requires_visual": "visual" in capabilities_needed,
        "requires_git": "git" in capabilities_needed,
        "task_complexity": "complex" if len(capabilities_needed) > 2 else "simple"
    }


@router.post("/inspector/smart-task")
async def execute_smart_task(
    request: SmartTaskRequest,
    db: Session = Depends(get_db)
):
    """
    اجرای کار هوشمند با انتخاب خودکار مدل‌ها و همکاری

    این endpoint:
    1. کار را تحلیل می‌کند
    2. مدل‌های مناسب را انتخاب می‌کند
    3. مدل‌های غیرفعال را موقتاً فعال می‌کند
    4. کار را بین مدل‌ها توزیع می‌کند
    5. نتایج را جمع‌آوری می‌کند
    """
    import uuid

    slog.api_request("POST", "/render/inspector/smart-task",
        task=request.task[:100],
        project_id=request.project_id,
        auto_select=request.auto_select
    )

    task_id = str(uuid.uuid4())[:8]

    try:
        from ...core.models_registry import MODEL_REGISTRY
        from ...services.ai_manager import get_ai_manager
        from ...models.ai_profile import ModelSettings

        # 1. تحلیل کار
        analysis = analyze_task_for_model_selection(request.task)

        # 2. دریافت مدل‌های موجود
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
        available_provider_names = [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]

        # تنظیمات مدل‌ها
        db_settings = db.query(ModelSettings).all()
        settings_map = {s.model_id: s for s in db_settings}

        # 3. انتخاب مدل‌ها
        selected_models = []
        temporarily_enabled = []

        if request.auto_select:
            for model_id in analysis["suggested_models"]:
                if model_id in MODEL_REGISTRY:
                    model = MODEL_REGISTRY[model_id]
                    provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)

                    if provider in available_provider_names:
                        setting = settings_map.get(model_id)
                        is_enabled = setting.enabled if setting else True

                        if is_enabled:
                            selected_models.append(model_id)
                        elif request.auto_select:
                            # 🆕 فعال کردن موقت در دیتابیس
                            selected_models.append(model_id)
                            temporarily_enabled.append(model_id)

                            # فعال‌سازی موقت در دیتابیس
                            if setting:
                                setting.enabled = True
                                setting.temporary_enabled = True  # فلگ موقت
                                db.commit()
                                slog.info(f"Temporarily enabled model: {model_id}")
                            else:
                                # ایجاد تنظیمات جدید
                                new_setting = ModelSettings(
                                    model_id=model_id,
                                    enabled=True,
                                    temporary_enabled=True
                                )
                                db.add(new_setting)
                                db.commit()
                                slog.info(f"Created temporary model settings: {model_id}")

        if not selected_models:
            # Fallback به اولین مدل موجود
            for model_id, model in MODEL_REGISTRY.items():
                provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)
                if provider in available_provider_names:
                    selected_models.append(model_id)
                    break

        # 4. ایجاد Task
        task_info = {
            "id": task_id,
            "description": request.task,
            "models": selected_models,
            "status": "running",
            "actions": [],
            "analysis": analysis,
            "temporarily_enabled": temporarily_enabled,
            "created_at": datetime.utcnow().isoformat()
        }
        active_tasks[task_id] = task_info

        # 5. اجرای کار (ساده شده - در نسخه کامل از async workers استفاده می‌شود)
        from ...services.ai_base import Message

        # ساخت system prompt برای همکاری
        collab_prompt = f"""# کار تیمی مدل‌ها

شما بخشی از یک تیم هستید که روی این کار کار می‌کنید:
{request.task}

## مدل‌های تیم:
{', '.join(selected_models)}

## قوانین همکاری:
1. هر اقدام خود را با فرمت زیر گزارش دهید:
   [ACTION] نوع: توضیح
   مثال: [ACTION] ANALYZE: در حال بررسی لاگ‌های خطا

2. قبل از ویرایش فایل، بررسی کنید که مدل دیگری روی آن کار نمی‌کند

3. نتایج را به صورت خلاصه و قابل فهم گزارش دهید

## Context پروژه:
- Frontend URL: {request.frontend_url or 'نامشخص'}
- GitHub Repo: {request.github_repo or 'نامشخص'}
"""

        if request.backend_logs:
            collab_prompt += f"\n## آخرین لاگ‌های بک‌اند:\n"
            for log in request.backend_logs[-20:]:
                collab_prompt += f"[{log.get('level', 'info').upper()}] {log.get('message', '')[:100]}\n"

        # اجرای درخواست به مدل‌های انتخاب شده
        results = []
        for model_id in selected_models:
            try:
                messages = [
                    Message(role="system", content=collab_prompt),
                    Message(role="user", content=request.task)
                ]

                response = await ai_manager.generate(
                    model_id=model_id,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.7,
                )

                # ثبت action
                action = {
                    "id": f"action_{len(task_info['actions'])}",
                    "model_id": model_id,
                    "action_type": "analyze",
                    "description": f"تحلیل و اجرای کار توسط {model_id}",
                    "status": "done",
                    "result": response.content,
                    "tokens_used": response.tokens_used
                }
                task_info["actions"].append(action)

                results.append({
                    "model_id": model_id,
                    "content": response.content,
                    "tokens_used": response.tokens_used,
                    "success": True
                })

            except Exception as e:
                slog.error(f"Model {model_id} failed", exception=e)
                results.append({
                    "model_id": model_id,
                    "content": str(e),
                    "success": False
                })

        # 6. به‌روزرسانی وضعیت
        task_info["status"] = "completed"
        task_info["results"] = results

        # 6.5. 🆕 غیرفعال کردن مدل‌های موقتاً فعال شده
        for model_id in temporarily_enabled:
            setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
            if setting and setting.temporary_enabled:
                setting.enabled = False
                setting.temporary_enabled = False
                db.commit()
                slog.info(f"Disabled temporary model: {model_id}")

        # 7. بررسی اتصال GitHub
        from ...models.setting import Setting
        github_key = os.environ.get("GITHUB_TOKEN", "")
        if not github_key:
            github_key = Setting.get_value(db, "api_key_github") or ""
            if github_key:
                os.environ["GITHUB_TOKEN"] = github_key
        github_connected = bool(github_key) and len(github_key) > 10

        # 8. ساخت پاسخ یکپارچه
        combined_content = ""
        total_tokens = 0
        for r in results:
            if r.get("success"):
                combined_content += f"\n\n**{r['model_id']}:**\n{r['content']}"
                total_tokens += r.get("tokens_used", 0)
            else:
                combined_content += f"\n\n**{r['model_id']}:** ❌ خطا: {r['content']}"

        return {
            "success": True,
            "task_id": task_id,
            "task": task_info,
            "analysis": analysis,
            "selected_models": selected_models,
            "temporarily_enabled": temporarily_enabled,
            "results": results,
            "content": combined_content.strip() or "کار انجام شد.",
            "tokens_used": total_tokens,
            "github_connected": github_connected,
            "actions": task_info["actions"]
        }

    except Exception as e:
        slog.error("Smart task failed", exception=e)
        if task_id in active_tasks:
            active_tasks[task_id]["status"] = "failed"
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/inspector/task/{task_id}")
async def get_task_status(task_id: str):
    """دریافت وضعیت یک کار"""
    if task_id not in active_tasks:
        return {
            "success": False,
            "error": "Task not found"
        }

    return {
        "success": True,
        "task": active_tasks[task_id]
    }


@router.post("/inspector/task/{task_id}/action")
async def add_task_action(task_id: str, action: TaskAction):
    """افزودن یک اقدام به کار (برای لاگ real-time)"""
    if task_id not in active_tasks:
        return {
            "success": False,
            "error": "Task not found"
        }

    active_tasks[task_id]["actions"].append({
        "id": action.id,
        "model_id": action.model_id,
        "action_type": action.action_type,
        "description": action.description,
        "target": action.target,
        "status": action.status,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {
        "success": True,
        "action_count": len(active_tasks[task_id]["actions"])
    }


@router.get("/inspector/github/files/{owner}/{repo}")
async def get_github_files(
    owner: str,
    repo: str,
    path: str = "",
    db: Session = Depends(get_db)
):
    """دریافت فایل‌های GitHub برای ویرایش"""
    try:
        from ...models.setting import Setting
        import aiohttp

        # دریافت توکن GitHub
        token_setting = db.query(Setting).filter(Setting.key == "api_key_github").first()
        if not token_setting:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است"
            }

        headers = {
            "Authorization": f"token {token_setting.value}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "files": data if isinstance(data, list) else [data],
                        "path": path
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status}"
                    }

    except Exception as e:
        slog.error("GitHub files fetch failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.put("/inspector/github/files/{owner}/{repo}")
async def update_github_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    sha: str,
    db: Session = Depends(get_db)
):
    """ویرایش فایل در GitHub"""
    try:
        from ...models.setting import Setting
        import aiohttp
        import base64

        # دریافت توکن GitHub
        token_setting = db.query(Setting).filter(Setting.key == "api_key_github").first()
        if not token_setting:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است"
            }

        headers = {
            "Authorization": f"token {token_setting.value}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

        # محتوا باید base64 باشد
        content_b64 = base64.b64encode(content.encode()).decode()

        payload = {
            "message": message,
            "content": content_b64,
            "sha": sha
        }

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    return {
                        "success": True,
                        "commit": data.get("commit", {})
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status}"
                    }

    except Exception as e:
        slog.error("GitHub file update failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


# =====================================
# 🆕 Browser Automation Endpoints
# =====================================

class BrowserActionRequest(BaseModel):
    """درخواست اکشن مرورگر"""
    session_id: str
    action: str  # analyze, click, type, scroll, find_login, login, screenshot
    params: Optional[dict] = {}


class BrowserSessionRequest(BaseModel):
    """درخواست ایجاد سشن مرورگر"""
    url: str
    session_id: Optional[str] = None


@router.post("/inspector/browser/session")
async def create_browser_session(request: BrowserSessionRequest):
    """
    ایجاد یک سشن مرورگر جدید برای کنترل با AI

    این endpoint یک مرورگر headless باز می‌کند و آماده دریافت دستورات می‌شود
    """
    import uuid
    from ...services.browser_automation import create_session

    session_id = request.session_id or str(uuid.uuid4())[:8]

    slog.api_request("POST", "/inspector/browser/session",
        url=request.url,
        session_id=session_id
    )

    try:
        session = await create_session(session_id, request.url)
        screenshot = await session.take_screenshot()
        page_info = await session.get_page_info()

        return {
            "success": True,
            "session_id": session_id,
            "page_info": page_info,
            "screenshot": screenshot,
            "message": f"مرورگر باز شد: {page_info.get('title', 'Unknown')}"
        }
    except Exception as e:
        slog.error("Browser session creation failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/inspector/browser/action")
async def execute_browser_action(request: BrowserActionRequest):
    """
    اجرای یک اکشن در مرورگر

    action types:
    - analyze: تحلیل صفحه
    - find_login: پیدا کردن فرم لاگین
    - login: انجام لاگین کامل (params: username, password)
    - click: کلیک (params: selector یا x,y)
    - type: تایپ (params: selector, text)
    - scroll: اسکرول (params: delta_y)
    - screenshot: گرفتن screenshot
    """
    from ...services.browser_automation import get_session, execute_ai_action

    slog.api_request("POST", "/inspector/browser/action",
        session_id=request.session_id,
        action=request.action
    )

    try:
        session = await get_session(request.session_id)
        if not session:
            return {
                "success": False,
                "error": "Session not found. Create a session first."
            }

        result = await execute_ai_action(session, request.action, request.params or {})

        return {
            "success": result.get("success", False),
            "action": request.action,
            "cursor_position": result.get("cursor_position"),
            "message": result.get("message", ""),
            "data": {k: v for k, v in result.items() if k not in ["success", "cursor_position", "message"]}
        }

    except Exception as e:
        slog.error("Browser action failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/inspector/browser/session/{session_id}")
async def close_browser_session(session_id: str):
    """بستن سشن مرورگر"""
    from ...services.browser_automation import close_session

    try:
        await close_session(session_id)
        return {"success": True, "message": "Session closed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class AIInteractRequest(BaseModel):
    """درخواست تعامل AI با صفحه"""
    task: str
    url: str
    model_id: Optional[str] = None  # اگر None باشد، خودکار انتخاب می‌شود
    max_steps: Optional[int] = 10
    debug: Optional[bool] = False  # 🆕 برای دیدن پاسخ خام AI


def get_best_vision_model(ai_manager, db, allow_temporary_enable: bool = True) -> tuple:
    """
    انتخاب بهترین مدل vision موجود

    اولویت:
    1. Claude (بهترین برای تحلیل و تصمیم‌گیری)
    2. GPT-4o (قدرتمند در vision)
    3. Gemini (سریع و مقرون به صرفه)

    Returns:
        tuple: (model_id, temporarily_enabled: bool)
    """
    from ...core.models_registry import get_vision_models, MODEL_REGISTRY
    from ...models.ai_profile import ModelSettings

    # مدل‌های vision به ترتیب اولویت
    priority_order = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "gpt-4o",
        "gpt-4-turbo",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gpt-4o-mini",
    ]

    # دریافت provider های فعال
    available_providers = []
    try:
        available_providers = ai_manager.get_available_providers()
        available_provider_names = [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]
    except:
        available_provider_names = []

    # دریافت تنظیمات مدل‌ها
    try:
        db_settings = db.query(ModelSettings).all() if db else []
        settings_map = {s.model_id: s for s in db_settings}
    except:
        settings_map = {}

    # 🆕 لیست مدل‌های غیرفعال که می‌توانند موقتاً فعال شوند
    disabled_vision_models = []

    # پیدا کردن اولین مدل فعال موجود
    for model_id in priority_order:
        if model_id in MODEL_REGISTRY:
            model = MODEL_REGISTRY[model_id]
            provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)

            # بررسی فعال بودن provider
            if provider not in available_provider_names:
                continue

            # بررسی قابلیت vision
            if not model.supports_images:
                continue

            # بررسی تنظیمات کاربر
            setting = settings_map.get(model_id)
            if setting and not setting.enabled:
                # 🆕 ذخیره برای فعال‌سازی موقت
                disabled_vision_models.append((model_id, setting))
                continue

            slog.info(f"Selected vision model (enabled): {model_id}")
            return model_id, False  # False = not temporarily enabled

    # 🆕 اگر مدل فعال پیدا نشد و اجازه فعال‌سازی موقت داریم
    if allow_temporary_enable and disabled_vision_models:
        model_id, setting = disabled_vision_models[0]  # بهترین مدل غیرفعال

        # فعال‌سازی موقت در دیتابیس
        slog.info(f"Temporarily enabling vision model: {model_id}")
        setting.enabled = True
        setting.temporary_enabled = True
        db.commit()

        return model_id, True  # True = temporarily enabled

    # Fallback به اولین مدل vision موجود
    vision_models = get_vision_models()
    for model in vision_models:
        provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)
        if provider in available_provider_names:
            return model.id, False

    return None, False


@router.post("/inspector/ai-interact")
async def ai_interact_with_page(
    request: AIInteractRequest,
    db: Session = Depends(get_db)
):
    """
    🤖 تعامل هوشمند AI با صفحه وب

    این endpoint یک AI Agent کامل است که می‌تواند هر دستوری را اجرا کند:
    - صفحه را می‌بیند (screenshot)
    - تصمیم می‌گیرد چه کاری انجام دهد
    - اقدام می‌کند (کلیک، تایپ، اسکرول)
    - نتیجه را می‌بیند و تکرار می‌کند تا task کامل شود

    مدل انتخابی:
    - اگر model_id داده نشود، بهترین مدل vision موجود انتخاب می‌شود
    - اولویت: Claude > GPT-4o > Gemini

    مثال‌ها:
    - "لاگین کن" → فرم لاگین را پیدا می‌کند و لاگین می‌کند
    - "برو به منوی Settings" → منو را پیدا می‌کند و کلیک می‌کند
    - "اسکرول کن تا قسمت Contact" → اسکرول می‌کند تا آن قسمت را پیدا کند
    - "دکمه Submit را بزن" → دکمه را پیدا می‌کند و کلیک می‌کند
    """
    import uuid
    from ...services.browser_automation import create_session, execute_ai_agent_task, close_session
    from ...services.ai_manager import get_ai_manager
    from ...models.ai_profile import ModelSettings

    session_id = str(uuid.uuid4())[:8]
    temporarily_enabled = False  # 🆕 آیا مدل موقتاً فعال شده

    # 1. دریافت AI manager
    ai_manager = get_ai_manager()

    # 2. انتخاب مدل vision (داینامیک یا مشخص شده)
    selected_model = request.model_id
    if not selected_model:
        selected_model, temporarily_enabled = get_best_vision_model(ai_manager, db)

    if not selected_model:
        return {
            "success": False,
            "error": "هیچ مدل vision فعالی یافت نشد. لطفاً API key یکی از مدل‌های vision (OpenAI, Claude, Gemini) را تنظیم کنید."
        }

    slog.api_request("POST", "/inspector/ai-interact",
        task=request.task[:100],
        url=request.url,
        model_id=selected_model,
        temporarily_enabled=temporarily_enabled
    )

    try:
        # 3. باز کردن مرورگر
        session = await create_session(session_id, request.url)
        page_info = await session.get_page_info()

        slog.info(f"Browser opened", session_id=session_id, title=page_info.get('title'), model=selected_model,
            temp_enabled=temporarily_enabled)

        # 4. اجرای task با AI Agent
        result = await execute_ai_agent_task(
            session=session,
            task=request.task,
            ai_manager=ai_manager,
            model_id=selected_model,
            max_steps=request.max_steps
        )

        # 5. فرمت کردن اکشن‌ها برای نمایش
        formatted_actions = []
        for action in result.get("actions", []):
            formatted_actions.append({
                "step": action.get("step"),
                "action": action.get("action"),
                "message": action.get("description") or action.get("thinking", "")[:100],
                "element": action.get("element", ""),
                "status": action.get("status", "done")
            })

        # 🆕 دریافت اطلاعات صفحه بعد از اجرای task (URL نهایی)
        final_page_info = await session.get_page_info()
        slog.info(f"Final page after task",
            final_url=final_page_info.get('url'),
            final_title=final_page_info.get('title')
        )

        response_data = {
            "success": result.get("success", False),
            "session_id": session_id,
            "task": request.task,
            "selected_model": selected_model,
            "actions": formatted_actions,
            "cursor_positions": result.get("cursor_positions", []),
            "final_screenshot": result.get("final_screenshot"),
            "total_steps": result.get("total_steps", 0),
            "message": f"کار انجام شد: {result.get('total_steps', 0)} مرحله (مدل: {selected_model})",
            "page_info": page_info,
            # 🆕 URL نهایی برای به‌روزرسانی iframe فرانت‌اند
            "final_url": final_page_info.get('url'),
            "final_page_info": final_page_info
        }

        # 🆕 اضافه کردن debug info
        if request.debug:
            response_data["debug"] = {
                "raw_actions": result.get("actions", []),
                "ai_responses": result.get("ai_responses", [])
            }

        # 🆕 غیرفعال کردن مدل موقتاً فعال شده
        if temporarily_enabled and selected_model:
            try:
                setting = db.query(ModelSettings).filter(ModelSettings.model_id == selected_model).first()
                if setting and setting.temporary_enabled:
                    setting.enabled = False
                    setting.temporary_enabled = False
                    db.commit()
                    slog.info(f"Disabled temporarily enabled model: {selected_model}")
            except Exception as cleanup_error:
                slog.warning(f"Failed to disable temporary model", error=str(cleanup_error))

        # 🆕 اضافه کردن اطلاعات فعال‌سازی موقت به response
        response_data["temporarily_enabled"] = temporarily_enabled

        # 🆕 بستن session مرورگر بعد از اتمام کار (جلوگیری از نشت حافظه)
        try:
            await close_session(session_id)
            slog.info(f"Browser session closed successfully: {session_id}")
        except Exception as close_error:
            slog.warning(f"Failed to close browser session", session_id=session_id, error=str(close_error))

        return response_data

    except Exception as e:
        slog.error("AI interaction failed", exception=e)

        # 🆕 غیرفعال کردن مدل موقت حتی در صورت خطا
        if temporarily_enabled and selected_model:
            try:
                setting = db.query(ModelSettings).filter(ModelSettings.model_id == selected_model).first()
                if setting and setting.temporary_enabled:
                    setting.enabled = False
                    setting.temporary_enabled = False
                    db.commit()
                    slog.info(f"Disabled temporarily enabled model after error: {selected_model}")
            except:
                pass

        try:
            await close_session(session_id)
        except:
            pass
        return {
            "success": False,
            "error": str(e),
            "actions": []
        }


# =====================================
# 🆕 اسکن بصری و کلیک مستقیم
# =====================================

class VisualScanRequest(BaseModel):
    """درخواست اسکن بصری صفحه"""
    url: str
    search_text: str  # متنی که باید پیدا شود
    click_on_find: bool = True  # آیا بعد از پیدا کردن کلیک کند


@router.post("/inspector/get-elements")
async def get_page_elements(url: str):
    """
    🔍 دریافت همه المان‌های صفحه برای اسکن واقعی در فرانت‌اند

    این endpoint صفحه را باز می‌کند و لیست همه المان‌های قابل کلیک را
    با موقعیت دقیقشان برمی‌گرداند. فرانت‌اند می‌تواند این المان‌ها را
    یکی یکی اسکن کند.
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]

    slog.api_request("POST", "/inspector/get-elements", url=url)

    try:
        session = await create_session(session_id, url)

        # استخراج همه المان‌های قابل کلیک
        elements = await session.extract_interactive_elements()

        # مرتب‌سازی بر اساس موقعیت: از بالا به پایین، چپ به راست
        elements_sorted = sorted(elements, key=lambda e: (e["center_y"], e["center_x"]))

        await close_session(session_id)

        return {
            "success": True,
            "elements": elements_sorted,
            "total": len(elements_sorted)
        }

    except Exception as e:
        slog.error("Get elements failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {"success": False, "error": str(e), "elements": []}


@router.post("/inspector/find-and-click")
async def find_element_and_click(url: str, search_text: str):
    """
    🔍 جستجوی Ctrl+F style - پیدا کردن متن در صفحه و کلیک

    مثل Ctrl+F مرورگر:
    1. متن رو در صفحه جستجو میکنه
    2. اگه پیدا شد، المان رو highlight میکنه (چشمک)
    3. scroll میکنه تا دیده بشه
    4. کلیک میکنه

    برمیگردونه:
    - found_elements: لیست همه المان‌های پیدا شده با موقعیت
    - clicked_index: کدوم کلیک شد
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]
    slog.api_request("POST", "/inspector/find-and-click", url=url, search_text=search_text)

    try:
        session = await create_session(session_id, url)

        if not session.page:
            await close_session(session_id)
            return {"success": False, "error": "Page not loaded"}

        page = session.page
        search_clean = search_text.strip()

        slog.info(f"🔍 Ctrl+F search for: '{search_clean}'")

        # 1. جستجوی متن با getByText (مثل Ctrl+F)
        locator = page.get_by_text(search_clean, exact=False)
        count = await locator.count()

        slog.info(f"Found {count} matches for '{search_clean}'")

        if count == 0:
            await close_session(session_id)
            return {
                "success": False,
                "error": f"'{search_text}' در این صفحه پیدا نشد",
                "found_count": 0
            }

        # 2. جمع‌آوری اطلاعات همه المان‌های پیدا شده
        found_elements = []
        for i in range(min(count, 20)):  # حداکثر 20 تا
            try:
                el = locator.nth(i)
                is_visible = await el.is_visible()
                if not is_visible:
                    continue

                box = await el.bounding_box()
                if not box or box["width"] < 3 or box["height"] < 3:
                    continue

                text = await el.text_content()
                text = (text or "").strip()[:100]

                found_elements.append({
                    "index": i,
                    "text": text,
                    "box": box,
                    "center_x": box["x"] + box["width"] / 2,
                    "center_y": box["y"] + box["height"] / 2,
                    "percent_x": round((box["x"] + box["width"]/2) / session.viewport["width"] * 100, 1),
                    "percent_y": round((box["y"] + box["height"]/2) / session.viewport["height"] * 100, 1)
                })
            except:
                continue

        if not found_elements:
            await close_session(session_id)
            return {
                "success": False,
                "error": f"'{search_text}' پیدا شد ولی visible نیست",
                "found_count": count
            }

        slog.info(f"Found {len(found_elements)} visible elements")

        # 3. پیدا کردن بهترین المان برای کلیک
        # اولویت: المان کوتاه‌تر (دقیق‌تر) و در موقعیت طبیعی
        found_elements.sort(key=lambda e: (len(e["text"]), e["center_y"]))
        best_element = found_elements[0]
        best_index = best_element["index"]

        slog.info(f"Best match: '{best_element['text'][:30]}' at ({best_element['percent_x']}%, {best_element['percent_y']}%)")

        # 4. Scroll تا المان دیده بشه
        el = locator.nth(best_index)
        await el.scroll_into_view_if_needed()
        await session.wait(300)

        # 5. Highlight animation (چشمک زدن)
        try:
            await el.evaluate("""el => {
                const originalOutline = el.style.outline;
                const originalBg = el.style.backgroundColor;
                const originalTransition = el.style.transition;

                el.style.transition = 'all 0.2s ease';
                let count = 0;
                const blink = setInterval(() => {
                    if (count % 2 === 0) {
                        el.style.outline = '3px solid #00ff00';
                        el.style.backgroundColor = 'rgba(0, 255, 0, 0.3)';
                    } else {
                        el.style.outline = originalOutline;
                        el.style.backgroundColor = originalBg;
                    }
                    count++;
                    if (count >= 6) {
                        clearInterval(blink);
                        el.style.outline = originalOutline;
                        el.style.backgroundColor = originalBg;
                        el.style.transition = originalTransition;
                    }
                }, 150);
            }""")
            await session.wait(1000)  # صبر برای انیمیشن
        except Exception as e:
            slog.warning(f"Highlight failed: {e}")

        # 6. آپدیت موقعیت بعد از scroll
        box = await el.bounding_box()
        if box:
            best_element["box"] = box
            best_element["center_x"] = box["x"] + box["width"] / 2
            best_element["center_y"] = box["y"] + box["height"] / 2
            best_element["percent_x"] = round((box["x"] + box["width"]/2) / session.viewport["width"] * 100, 1)
            best_element["percent_y"] = round((box["y"] + box["height"]/2) / session.viewport["height"] * 100, 1)

        # 7. کلیک!
        await el.click(timeout=5000)
        slog.info(f"✅ Clicked on '{best_element['text'][:30]}'")

        # 8. صبر برای navigation
        await session.wait(1500)
        new_url = page.url

        await close_session(session_id)

        return {
            "success": True,
            "found": best_element["text"],
            "found_count": len(found_elements),
            "found_elements": found_elements[:5],  # 5 تای اول برای نمایش
            "clicked_index": best_index,
            "position": best_element,
            "url_changed": new_url != url,
            "new_url": new_url
        }

    except Exception as e:
        slog.error("Find and click failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {"success": False, "error": str(e)}


@router.post("/inspector/click-at")
async def click_at_position(url: str, x: float, y: float):
    """
    🖱️ کلیک در موقعیت مشخص (پیکسل)
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]

    try:
        session = await create_session(session_id, url)
        result = await session.click(x, y)
        await session.wait(1000)
        new_url = session.page.url if session.page else url
        await close_session(session_id)

        return {
            "success": True,
            "clicked_at": {"x": x, "y": y},
            "url_changed": new_url != url,
            "new_url": new_url
        }

    except Exception as e:
        slog.error("Click failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {"success": False, "error": str(e)}


@router.post("/inspector/visual-scan")
async def visual_scan_and_click(request: VisualScanRequest):
    """
    🔍 اسکن بصری صفحه با نوارهای متحرک

    این endpoint:
    1. صفحه را باز می‌کند
    2. متن مورد نظر را جستجو می‌کند
    3. مختصات اسکن را برای انیمیشن نوار برمی‌گرداند
    4. اگر click_on_find=true باشد، کلیک می‌کند

    Response شامل:
    - scan_animation: مراحل انیمیشن نوار اسکن
    - target_position: موقعیت هدف (درصد)
    - clicked: آیا کلیک شد
    """
    import uuid
    from ...services.browser_automation import create_session, close_session

    session_id = str(uuid.uuid4())[:8]

    slog.api_request("POST", "/inspector/visual-scan",
        url=request.url,
        search_text=request.search_text
    )

    try:
        # 1. باز کردن مرورگر
        session = await create_session(session_id, request.url)

        # 2. جستجوی متن
        if request.click_on_find:
            result = await session.scan_and_click_text(request.search_text)
        else:
            result = await session.find_text_on_page(request.search_text)

        # 3. ساخت انیمیشن اسکن
        # نوار عمودی از چپ به راست، نوار افقی از بالا به پایین
        scan_animation = {
            "vertical_bar": [],   # نوار عمودی - حرکت افقی
            "horizontal_bar": [], # نوار افقی - حرکت عمودی
            "intersection": None  # نقطه تقاطع (هدف)
        }

        if result.get("found") or result.get("success"):
            target = result.get("element") or result.get("clicked_element")
            if target:
                target_x = target["percent_x"]
                target_y = target["percent_y"]

                # انیمیشن نوار عمودی (از چپ به راست تا x هدف)
                for x in range(0, int(target_x) + 1, 5):
                    scan_animation["vertical_bar"].append({"x": x, "duration": 30})

                # انیمیشن نوار افقی (از بالا به پایین تا y هدف)
                for y in range(0, int(target_y) + 1, 5):
                    scan_animation["horizontal_bar"].append({"y": y, "duration": 30})

                # نقطه تقاطع
                scan_animation["intersection"] = {
                    "x": target_x,
                    "y": target_y,
                    "text": target.get("text", "")[:50]
                }

        # 4. گرفتن screenshot
        screenshot = await session.take_screenshot()

        # 5. بستن session
        await close_session(session_id)

        return {
            "success": result.get("found", False) or result.get("success", False),
            "scan_animation": scan_animation,
            "target_position": result.get("cursor_position") or (
                {"x": result["element"]["percent_x"], "y": result["element"]["percent_y"]}
                if result.get("element") else None
            ),
            "clicked": request.click_on_find and result.get("success", False),
            "url_changed": result.get("url_changed", False),
            "final_url": result.get("url", request.url),
            "total_matches": result.get("total_matches", 0),
            "screenshot": screenshot,
            "message": f"پیدا شد: {result.get('element', {}).get('text', '')[:50]}" if result.get("found") else "پیدا نشد"
        }

    except Exception as e:
        slog.error("Visual scan failed", exception=e)
        try:
            await close_session(session_id)
        except:
            pass
        return {
            "success": False,
            "error": str(e),
            "scan_animation": {"vertical_bar": [], "horizontal_bar": [], "intersection": None}
        }


# =====================================
# 🆕 بازرسی همزمان فرانت‌اند و بک‌اند
# =====================================

class SyncInspectionRequest(BaseModel):
    """درخواست بازرسی همزمان فرانت‌اند و بک‌اند"""
    task: str  # دستور کار
    project_id: str
    frontend_url: Optional[str] = None
    backend_logs: Optional[List[dict]] = None
    # مدل‌های انتخابی
    frontend_model_ids: Optional[List[str]] = None  # مدل‌های فرانت
    backend_model_ids: Optional[List[str]] = None   # مدل‌های بک‌اند
    auto_select: bool = True  # انتخاب خودکار مدل‌ها
    max_steps: int = 10


@router.post("/inspector/sync-inspection")
async def synchronized_inspection(
    request: SyncInspectionRequest,
    db: Session = Depends(get_db)
):
    """
    🔄 بازرسی همزمان فرانت‌اند و بک‌اند

    این endpoint:
    1. مدل‌های فرانت را روی صفحه پیش‌نمایش کار می‌گذارد
    2. همزمان مدل‌های بک‌اند را روی لاگ‌ها می‌گذارد
    3. نتایج هر دو را در لحظه گزارش می‌کند
    4. اگر فرانت اقدامی انجام دهد، بک‌اند لاگ مربوطه را رصد می‌کند
    """
    import asyncio
    from ...services.ai_manager import get_ai_manager
    from ...models.ai_profile import ModelSettings
    from ...services.ai_base import Message

    slog.api_request("POST", "/inspector/sync-inspection",
        task=request.task[:100],
        project_id=request.project_id
    )

    try:
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
        available_provider_names = [str(p.value) if hasattr(p, 'value') else str(p) for p in available_providers]

        # دریافت تنظیمات مدل‌ها
        db_settings = db.query(ModelSettings).all()
        settings_map = {s.model_id: s for s in db_settings}

        # انتخاب مدل‌ها
        frontend_models = request.frontend_model_ids or []
        backend_models = request.backend_model_ids or []

        if request.auto_select:
            # انتخاب خودکار بهترین مدل‌های vision برای فرانت
            if not frontend_models:
                # 🆕 get_best_vision_model returns tuple (model_id, temporarily_enabled)
                vision_result = get_best_vision_model(ai_manager, db)
                if vision_result and vision_result[0]:
                    frontend_models = [vision_result[0]]

            # انتخاب خودکار مدل‌های تحلیل برای بک‌اند
            if not backend_models:
                from ...core.models_registry import MODEL_REGISTRY
                analysis_models = ["claude-sonnet-4-20250514", "gpt-4o", "gemini-2.5-pro"]
                for model_id in analysis_models:
                    if model_id in MODEL_REGISTRY:
                        model = MODEL_REGISTRY[model_id]
                        provider = str(model.provider.value) if hasattr(model.provider, 'value') else str(model.provider)
                        if provider in available_provider_names:
                            setting = settings_map.get(model_id)
                            if not setting or setting.enabled:
                                backend_models = [model_id]
                                break

        # نتایج
        results = {
            "frontend": {"model": frontend_models, "actions": [], "status": "pending"},
            "backend": {"model": backend_models, "actions": [], "status": "pending"},
            "sync_events": []  # رویدادهای همگام‌سازی
        }

        # ==================
        # تابع تحلیل بک‌اند
        # ==================
        async def analyze_backend_logs():
            if not backend_models or not request.backend_logs:
                results["backend"]["status"] = "skipped"
                return

            results["backend"]["status"] = "running"

            backend_prompt = f"""شما یک تحلیل‌گر لاگ بک‌اند هستید.

## وظیفه:
{request.task}

## لاگ‌های بک‌اند:
```
"""
            for log in request.backend_logs[-50:]:
                level = log.get('level', 'info').upper()
                timestamp = log.get('timestamp', '')[:19]
                message = log.get('message', '')[:200]
                backend_prompt += f"[{timestamp}] {level}: {message}\n"

            backend_prompt += """```

## وظیفه شما:
1. لاگ‌ها را تحلیل کنید
2. خطاها و هشدارها را شناسایی کنید
3. اگر مشکلی وجود دارد، راه‌حل پیشنهاد دهید
4. گزارش مختصر بدهید

فرمت پاسخ:
- خلاصه: ...
- خطاها: ...
- پیشنهادات: ...
"""

            for model_id in backend_models:
                try:
                    messages = [
                        Message(role="system", content="شما یک تحلیل‌گر متخصص لاگ‌های سرور هستید."),
                        Message(role="user", content=backend_prompt)
                    ]

                    response = await ai_manager.generate(
                        model_id=model_id,
                        messages=messages,
                        max_tokens=2048,
                        temperature=0.3
                    )

                    results["backend"]["actions"].append({
                        "model_id": model_id,
                        "type": "analysis",
                        "content": response.content,
                        "tokens_used": response.tokens_used,
                        "success": True
                    })

                    # رویداد همگام‌سازی
                    results["sync_events"].append({
                        "time": datetime.utcnow().isoformat(),
                        "source": "backend",
                        "model": model_id,
                        "event": "تحلیل لاگ‌ها کامل شد"
                    })

                except Exception as e:
                    results["backend"]["actions"].append({
                        "model_id": model_id,
                        "type": "error",
                        "content": str(e),
                        "success": False
                    })

            results["backend"]["status"] = "completed"

        # ==================
        # تابع تعامل فرانت‌اند
        # ==================
        async def interact_with_frontend():
            if not frontend_models or not request.frontend_url:
                results["frontend"]["status"] = "skipped"
                return

            results["frontend"]["status"] = "running"

            try:
                from ...services.browser_automation import create_session, execute_ai_agent_task, close_session, PLAYWRIGHT_AVAILABLE

                if not PLAYWRIGHT_AVAILABLE:
                    results["frontend"]["status"] = "error"
                    results["frontend"]["actions"].append({
                        "type": "error",
                        "content": "Playwright not installed. Please install: pip install playwright && playwright install chromium"
                    })
                    return

                import uuid
                session_id = str(uuid.uuid4())[:8]

                session = await create_session(session_id, request.frontend_url)

                for model_id in frontend_models:
                    result = await execute_ai_agent_task(
                        session=session,
                        task=request.task,
                        ai_manager=ai_manager,
                        model_id=model_id,
                        max_steps=request.max_steps
                    )

                    results["frontend"]["actions"].append({
                        "model_id": model_id,
                        "type": "interaction",
                        "steps": result.get("actions", []),
                        "cursor_positions": result.get("cursor_positions", []),
                        "success": result.get("success", False)
                    })

                    # رویدادهای همگام‌سازی برای هر اقدام
                    for action in result.get("actions", []):
                        results["sync_events"].append({
                            "time": datetime.utcnow().isoformat(),
                            "source": "frontend",
                            "model": model_id,
                            "event": f"{action.get('action')}: {action.get('description', '')[:50]}"
                        })

                await close_session(session_id)
                results["frontend"]["status"] = "completed"

            except Exception as e:
                results["frontend"]["status"] = "error"
                results["frontend"]["actions"].append({
                    "type": "error",
                    "content": str(e)
                })

        # ==================
        # اجرای همزمان
        # ==================
        await asyncio.gather(
            analyze_backend_logs(),
            interact_with_frontend()
        )

        # بررسی اتصال GitHub
        from ...models.setting import Setting
        github_key = os.environ.get("GITHUB_TOKEN", "")
        if not github_key:
            github_key = Setting.get_value(db, "api_key_github") or ""
            if github_key:
                os.environ["GITHUB_TOKEN"] = github_key
        github_connected = bool(github_key) and len(github_key) > 10

        return {
            "success": True,
            "task": request.task,
            "results": results,
            "frontend_models": frontend_models,
            "backend_models": backend_models,
            "github_connected": github_connected,
            "message": f"بازرسی همزمان کامل شد - فرانت: {len(results['frontend']['actions'])} اقدام، بک‌اند: {len(results['backend']['actions'])} تحلیل"
        }

    except Exception as e:
        slog.error("Sync inspection failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# 🆕🆕🆕 Live Action Tracking - رصد لحظه‌ای فعالیت کاربر
# ============================================

class AnalyzeActionRequest(BaseModel):
    """درخواست تحلیل اقدام کاربر"""
    url: str
    action_type: str  # click, scroll, input
    position: dict  # {x: number, y: number}
    project_id: str
    selected_models: Optional[List[str]] = None


class AnalyzeErrorRequest(BaseModel):
    """درخواست تحلیل خطا از GitHub"""
    project_id: str
    error_message: str
    log_details: Optional[str] = None
    source_hint: Optional[str] = None
    selected_models: Optional[List[str]] = None


@router.post("/inspector/analyze-action")
async def analyze_user_action(
    request: AnalyzeActionRequest,
    db: Session = Depends(get_db)
):
    """
    🎯 تحلیل سریع اقدام کاربر - بدون Playwright

    این endpoint سریع پاسخ می‌دهد و فقط لاگ‌های بک‌اند را برای خطا چک می‌کند.
    """
    slog.api_request("POST", "/inspector/analyze-action",
        action_type=request.action_type,
        position=request.position
    )

    try:
        # تولید توضیح ساده بر اساس نوع عمل
        action_type_fa = {
            "click": "کلیک",
            "scroll": "اسکرول",
            "input": "تایپ",
            "navigate": "ناوبری"
        }

        action_description = f"{action_type_fa.get(request.action_type, 'عملیات')} در موقعیت ({request.position.get('x', 0):.0f}%, {request.position.get('y', 0):.0f}%)"

        # بررسی لاگ‌های بک‌اند برای خطا
        backend_status = None
        has_error = False
        error_info = None

        from ...models.project import Project
        project = db.query(Project).filter(Project.id == request.project_id).first()

        if project:
            # بررسی render_service_ids
            service_ids = []
            if hasattr(project, 'render_service_ids') and project.render_service_ids:
                if isinstance(project.render_service_ids, str):
                    service_ids = [s.strip() for s in project.render_service_ids.split(',') if s.strip()]
                else:
                    service_ids = project.render_service_ids

            if service_ids:
                # دریافت لاگ‌های اخیر (10 ثانیه آخر)
                recent_logs = db.query(RenderLog).filter(
                    RenderLog.service_id.in_(service_ids),
                    RenderLog.created_at >= datetime.utcnow() - timedelta(seconds=10)
                ).order_by(desc(RenderLog.created_at)).limit(5).all()

                error_log = next((log for log in recent_logs if log.level == 'error'), None)

                if error_log:
                    has_error = True
                    backend_status = {
                        "has_error": True,
                        "message": f"⚠️ خطا در بک‌اند: {error_log.message[:100] if error_log.message else 'نامشخص'}"
                    }
                    error_info = {
                        "message": error_log.message or "خطای ناشناخته",
                        "log_details": f"[{error_log.level}] {error_log.message}"
                    }
                else:
                    backend_status = {
                        "has_error": False,
                        "message": "✅ بک‌اند: عملیات موفق"
                    }

        return {
            "success": True,
            "action_type": request.action_type,
            "position": request.position,
            "action_description": action_description,
            "visual_model": None,
            "page_title": None,
            "new_url": None,
            "page_name": None,
            "backend_status": backend_status,
            "backend_model": None,
            "has_error": has_error,
            "error_info": error_info
        }

    except Exception as e:
        slog.error("Analyze action failed", exception=e)
        return {
            "success": False,
            "error": str(e),
            "action_description": f"{request.action_type} انجام شد"
        }


@router.post("/inspector/analyze-error")
async def analyze_error_from_source(
    request: AnalyzeErrorRequest,
    db: Session = Depends(get_db)
):
    """
    🔍 تحلیل عمیق خطا با بررسی کد منبع از GitHub

    این endpoint:
    1. پیام خطا را تحلیل می‌کند
    2. به GitHub پروژه مراجعه می‌کند
    3. فایل‌های مرتبط را پیدا می‌کند
    4. علت خطا را شناسایی می‌کند
    5. راه‌حل پیشنهاد می‌دهد
    """
    from ...services.ai_manager import get_ai_manager
    from ...models.project import Project
    from ...models.setting import Setting
    import httpx

    slog.api_request("POST", "/inspector/analyze-error",
        project_id=request.project_id,
        error_message=request.error_message[:100]
    )

    try:
        # دریافت پروژه
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # توکن GitHub
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است",
                "analysis": "برای بررسی کد منبع، ابتدا توکن GitHub را در تنظیمات وارد کنید."
            }

        # استخراج owner/repo از github_path پروژه
        github_path = getattr(project, 'github_path', None)
        if not github_path:
            return {
                "success": False,
                "error": "این پروژه به GitHub متصل نیست",
                "analysis": request.error_message
            }

        # پارس کردن github_path
        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            return {"success": False, "error": f"فرمت GitHub path نامعتبر: {github_path}"}

        owner, repo = parts[0], parts[1]

        # انتخاب مدل تحلیل
        ai_manager = get_ai_manager()
        analysis_model = None

        if request.selected_models:
            analysis_model = request.selected_models[0]
        else:
            # انتخاب بهترین مدل تحلیل
            for model_id in ["claude-sonnet-4-20250514", "gpt-4o", "gemini-2.5-pro"]:
                try:
                    # تست سریع
                    analysis_model = model_id
                    break
                except:
                    continue

        if not analysis_model:
            analysis_model = "gpt-4o-mini"

        # دریافت لیست فایل‌ها از GitHub
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        source_files = []
        file_contents = {}

        async with httpx.AsyncClient() as client:
            # دریافت tree برای پیدا کردن فایل‌های مرتبط
            tree_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1",
                headers=headers,
                timeout=15.0
            )

            if tree_res.status_code == 200:
                tree_data = tree_res.json()
                all_files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

                # فیلتر فایل‌های کد
                code_files = [f for f in all_files if f.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.vue', '.go', '.rs'))]

                # پیدا کردن فایل‌های مرتبط با خطا
                error_keywords = request.error_message.lower().split()
                relevant_files = []

                for file_path in code_files[:100]:  # محدودیت
                    file_lower = file_path.lower()
                    # امتیاز بر اساس تطابق کلمات
                    score = sum(1 for kw in error_keywords if kw in file_lower and len(kw) > 3)
                    if score > 0:
                        relevant_files.append((file_path, score))

                # اگر فایل مرتبط نبود، فایل‌های اصلی را بگیر
                if not relevant_files:
                    main_files = [f for f in code_files if any(x in f.lower() for x in ['main', 'app', 'index', 'server', 'api', 'route'])]
                    relevant_files = [(f, 1) for f in main_files[:5]]

                # مرتب‌سازی بر اساس امتیاز
                relevant_files.sort(key=lambda x: -x[1])
                relevant_files = relevant_files[:5]  # حداکثر 5 فایل

                # دریافت محتوای فایل‌ها
                for file_path, _ in relevant_files:
                    try:
                        content_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}",
                            headers=headers,
                            timeout=10.0
                        )
                        if content_res.status_code == 200:
                            import base64
                            content_data = content_res.json()
                            if content_data.get("encoding") == "base64":
                                content = base64.b64decode(content_data["content"]).decode('utf-8', errors='ignore')
                                file_contents[file_path] = content[:5000]  # محدودیت سایز
                                source_files.append({"path": file_path, "issue": "در حال بررسی..."})
                    except Exception as e:
                        slog.warning(f"Failed to fetch {file_path}: {e}")

        # تحلیل با AI
        from ...services.ai_base import Message

        analysis_prompt = f"""شما یک مهندس نرم‌افزار متخصص هستید که باید خطا را تحلیل کنید.

## خطای گزارش شده:
{request.error_message}

## جزئیات لاگ:
{request.log_details or 'ندارد'}

## فایل‌های کد پروژه:
"""
        for file_path, content in file_contents.items():
            analysis_prompt += f"\n### {file_path}\n```\n{content[:3000]}\n```\n"

        analysis_prompt += """

## وظیفه شما:
1. علت اصلی خطا را شناسایی کنید
2. فایل یا فایل‌های مسبب را مشخص کنید
3. راه‌حل دقیق برای رفع خطا پیشنهاد دهید

## فرمت پاسخ (JSON):
{
  "analysis": "توضیح علت خطا به فارسی",
  "source_files": [
    {"path": "مسیر فایل", "issue": "مشکل این فایل چیست"}
  ],
  "suggested_fix": "راه‌حل پیشنهادی به فارسی"
}

فقط JSON خالص برگردانید، بدون توضیح اضافی."""

        try:
            messages = [
                Message(role="system", content="شما یک مهندس نرم‌افزار متخصص در debugging هستید. پاسخ را به صورت JSON خالص برگردانید."),
                Message(role="user", content=analysis_prompt)
            ]

            response = await ai_manager.generate(
                model_id=analysis_model,
                messages=messages,
                max_tokens=2000,
                temperature=0.2
            )

            # پارس کردن پاسخ JSON
            response_text = response.content.strip()
            # حذف markdown اگر وجود دارد
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            result = json.loads(response_text)

            return {
                "success": True,
                "analysis": result.get("analysis", "تحلیل انجام شد"),
                "source_files": result.get("source_files", source_files),
                "suggested_fix": result.get("suggested_fix", "بررسی فایل‌های مرتبط"),
                "model_used": analysis_model,
                "detailed_report": f"تحلیل توسط {analysis_model}:\n\n{result.get('analysis', '')}"
            }

        except json.JSONDecodeError:
            # اگر JSON نبود، متن خام را برگردان
            return {
                "success": True,
                "analysis": response.content if 'response' in dir() else "خطا در تحلیل",
                "source_files": source_files,
                "suggested_fix": "بررسی فایل‌های مرتبط",
                "model_used": analysis_model,
                "detailed_report": response.content if 'response' in dir() else ""
            }

    except Exception as e:
        slog.error("Analyze error from source failed", exception=e)
        return {
            "success": False,
            "error": str(e),
            "analysis": f"خطا در تحلیل: {str(e)}"
        }


# =====================================
# 🌉 Bridge Script Injection
# تزریق اسکریپت ارتباطی به پروژه‌ها
# =====================================

class InjectBridgeRequest(BaseModel):
    """درخواست تزریق Bridge Script"""
    project_id: str
    remove: bool = False  # True = حذف اسکریپت
    force_update: bool = False  # True = حذف نسخه قدیمی و تزریق نسخه جدید
    custom_path: Optional[str] = None  # مسیر سفارشی به فایل HTML (مثال: "frontend/public/index.html")


# محتوای Bridge Script که به پروژه‌ها تزریق می‌شود (نسخه HTML)
INSPECTOR_BRIDGE_SCRIPT = '''
<!-- Inspector Bridge Script - Auto-injected -->
<!-- Version: 2.4 -->
<script>
(function() {
  console.log('🌉 Inspector Bridge: Script starting...');

  // جلوگیری از اجرای چندباره
  if (window.__inspectorBridgeLoaded) {
    console.log('🌉 Inspector Bridge: Already loaded, skipping');
    return;
  }
  window.__inspectorBridgeLoaded = true;

  // بررسی اینکه آیا در iframe هستیم
  const isInIframe = window !== window.parent;
  console.log('🌉 Inspector Bridge: In iframe?', isInIframe);
  console.log('🌉 Inspector Bridge: Page URL:', window.location.href);

  // تنظیمات WebSocket
  const WS_URL = '__BRIDGE_WS_URL__';
  const PROJECT_ID = '__BRIDGE_PROJECT_ID__';
  const DEBOUNCE_MS = 100;
  let lastEventTime = 0;
  let messagesSent = 0;
  let ws = null;
  let wsReady = false;
  let reconnectTimer = null;
  let messageQueue = [];

  // 🌐 اتصال WebSocket به Backend Hub
  function connectWebSocket() {
    if (!WS_URL || WS_URL === '__BRIDGE_WS_URL__') {
      console.log('🌉 Inspector Bridge: No WS URL configured, using postMessage only');
      return;
    }
    try {
      ws = new WebSocket(WS_URL);
      ws.onopen = function() {
        console.log('🌉 Inspector Bridge: WebSocket connected');
        ws.send(JSON.stringify({ type: 'register', role: 'bridge' }));
      };
      ws.onmessage = function(event) {
        try {
          var msg = JSON.parse(event.data);
          if (msg.type === 'registered') {
            wsReady = true;
            console.log('🌉 Inspector Bridge: Registered as bridge via WebSocket');
            // ارسال پیام‌های در صف
            while (messageQueue.length > 0) {
              var queued = messageQueue.shift();
              ws.send(JSON.stringify(queued));
            }
            // ارسال پیام آماده بودن
            ws.send(JSON.stringify({
              type: 'inspector-bridge-ready',
              pageUrl: window.location.href,
              isInIframe: isInIframe,
              timestamp: Date.now()
            }));
          } else if (msg.type === 'pong') {
            // heartbeat response
          } else if (msg.type === 'command') {
            // دریافت دستور از Inspector
            console.log('🌉 Inspector Bridge: Received command:', msg);
            handleInspectorCommand(msg);
          }
        } catch (e) {
          console.warn('🌉 Inspector Bridge: WS message parse error', e);
        }
      };
      ws.onclose = function() {
        wsReady = false;
        console.log('🌉 Inspector Bridge: WebSocket disconnected, reconnecting in 3s...');
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      };
      ws.onerror = function(e) {
        console.warn('🌉 Inspector Bridge: WebSocket error', e);
      };
    } catch (e) {
      console.warn('🌉 Inspector Bridge: Failed to create WebSocket', e);
    }
  }

  // پردازش دستورات از Inspector
  function handleInspectorCommand(msg) {
    if (msg.command === 'click') {
      // کلیک روی المان با selector
      var el = document.querySelector(msg.selector);
      if (el) { el.click(); sendToInspector('command-result', { success: true, command: 'click', selector: msg.selector }); }
      else { sendToInspector('command-result', { success: false, command: 'click', error: 'Element not found' }); }
    } else if (msg.command === 'navigate') {
      window.location.href = msg.url;
    } else if (msg.command === 'get-elements') {
      var elements = [];
      document.querySelectorAll('a, button, input, textarea, select, [role="button"], [onclick]').forEach(function(el, i) {
        elements.push({
          index: i,
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.value || '').trim().slice(0, 50),
          id: el.id || '',
          className: (el.className || '').toString().slice(0, 50),
          href: el.href || ''
        });
      });
      sendToInspector('elements-list', { elements: elements });
    }
  }

  // تابع ارسال پیام (WebSocket اولویت اول، postMessage فالبک)
  function sendToInspector(action, data) {
    try {
      var message = {
        type: 'inspector-bridge-event',
        action: action,
        target: data.target || '',
        elementInfo: data.elementInfo || '',
        position: data.position || { xPercent: 50, yPercent: 50 },
        pageUrl: window.location.href,
        timestamp: Date.now(),
        level: data.level || null,
        source: 'imported-project',
        networkMeta: data.networkMeta || null
      };

      // ارسال از طریق WebSocket
      if (ws && wsReady) {
        ws.send(JSON.stringify(message));
      } else if (ws && !wsReady) {
        messageQueue.push(message);
      }

      // همیشه postMessage هم بفرست (فالبک)
      if (isInIframe) {
        window.parent.postMessage(message, '*');
      }

      messagesSent++;
      console.log('🌉 Inspector Bridge: Sent message #' + messagesSent, action, data.elementInfo);
    } catch (e) {
      console.warn('Inspector bridge: failed to send message', e);
    }
  }

  // 🌐 Network Monitoring (fetch + XHR) — v2.4
  // hook کردن window.fetch و XMLHttpRequest برای ثبت درخواست‌های شبکه پروژهٔ deploy شده.
  // event ها: network-request (شروع)، network-response (موفق)، network-error (ناموفق).
  // قبل از send، header های Authorization/Cookie و query paramهای حساس masked می‌شوند.
  (function setupNetworkMonitoring() {
    try {
      var __netReqSeq = 0;
      var __maskValue = function(v) {
        if (!v) return v;
        var s = String(v);
        return s.length > 8 ? s.slice(0, 4) + '****' + s.slice(-2) : '****';
      };
      var __maskUrl = function(url) {
        try {
          var u = new URL(url, window.location.origin);
          u.searchParams.forEach(function(val, key) {
            var lk = key.toLowerCase();
            if (lk.indexOf('token') >= 0 || lk.indexOf('key') >= 0 || lk.indexOf('secret') >= 0 || lk.indexOf('password') >= 0) {
              u.searchParams.set(key, __maskValue(val));
            }
          });
          return u.toString();
        } catch (e) { return String(url); }
      };
      var __summarizeUrl = function(url) {
        try {
          var u = new URL(url, window.location.origin);
          var path = u.pathname;
          if (path.length > 80) path = path.slice(0, 77) + '...';
          return u.host + path;
        } catch (e) { return String(url).slice(0, 100); }
      };
      // ---- fetch ----
      if (typeof window.fetch === 'function' && !window.__inspectorFetchHooked) {
        window.__inspectorFetchHooked = true;
        var origFetch = window.fetch.bind(window);
        window.fetch = function(input, init) {
          var reqId = 'fetch_' + (++__netReqSeq) + '_' + Date.now();
          var url = typeof input === 'string' ? input : (input && input.url) || '';
          var method = (init && init.method) || (input && input.method) || 'GET';
          var maskedUrl = __maskUrl(url);
          var startedAt = Date.now();
          try {
            sendToInspector('network-request', {
              elementInfo: method.toUpperCase() + ' ' + __summarizeUrl(maskedUrl),
              level: null,
              networkMeta: { reqId: reqId, method: method.toUpperCase(), url: maskedUrl, startedAt: startedAt }
            });
          } catch (e) {}
          return origFetch(input, init).then(function(res) {
            try {
              var dur = Date.now() - startedAt;
              var ok = res && res.ok;
              var status = res ? res.status : 0;
              var label = method.toUpperCase() + ' ' + __summarizeUrl(maskedUrl) + ' → ' + status + ' (' + dur + 'ms)';
              sendToInspector(ok ? 'network-response' : 'network-error', {
                elementInfo: label,
                level: ok ? null : 'error',
                networkMeta: { reqId: reqId, method: method.toUpperCase(), url: maskedUrl, status: status, durationMs: dur, ok: !!ok }
              });
            } catch (e) {}
            return res;
          }).catch(function(err) {
            try {
              var dur = Date.now() - startedAt;
              sendToInspector('network-error', {
                elementInfo: method.toUpperCase() + ' ' + __summarizeUrl(maskedUrl) + ' ✗ ' + (err && err.message || 'fetch failed'),
                level: 'error',
                networkMeta: { reqId: reqId, method: method.toUpperCase(), url: maskedUrl, status: 0, durationMs: dur, ok: false, errorMessage: err && err.message }
              });
            } catch (e) {}
            throw err;
          });
        };
      }
      // ---- XMLHttpRequest ----
      if (window.XMLHttpRequest && !window.__inspectorXhrHooked) {
        window.__inspectorXhrHooked = true;
        var origOpen = XMLHttpRequest.prototype.open;
        var origSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function(method, url) {
          try {
            this.__inspectorReqId = 'xhr_' + (++__netReqSeq) + '_' + Date.now();
            this.__inspectorMethod = (method || 'GET').toUpperCase();
            this.__inspectorUrl = __maskUrl(url);
          } catch (e) {}
          return origOpen.apply(this, arguments);
        };
        XMLHttpRequest.prototype.send = function() {
          var xhr = this;
          try {
            xhr.__inspectorStartedAt = Date.now();
            sendToInspector('network-request', {
              elementInfo: xhr.__inspectorMethod + ' ' + __summarizeUrl(xhr.__inspectorUrl),
              level: null,
              networkMeta: { reqId: xhr.__inspectorReqId, method: xhr.__inspectorMethod, url: xhr.__inspectorUrl, startedAt: xhr.__inspectorStartedAt }
            });
            xhr.addEventListener('loadend', function() {
              try {
                var dur = Date.now() - xhr.__inspectorStartedAt;
                var status = xhr.status || 0;
                var ok = status >= 200 && status < 400;
                var label = xhr.__inspectorMethod + ' ' + __summarizeUrl(xhr.__inspectorUrl) + ' → ' + status + ' (' + dur + 'ms)';
                sendToInspector(ok ? 'network-response' : 'network-error', {
                  elementInfo: label,
                  level: ok ? null : 'error',
                  networkMeta: { reqId: xhr.__inspectorReqId, method: xhr.__inspectorMethod, url: xhr.__inspectorUrl, status: status, durationMs: dur, ok: ok }
                });
              } catch (e) {}
            });
          } catch (e) {}
          return origSend.apply(this, arguments);
        };
      }
    } catch (e) { /* network monitoring boot failed - non-critical */ }
  })();

  // شروع اتصال WebSocket
  connectWebSocket();

  // Heartbeat هر 25 ثانیه
  setInterval(function() {
    if (ws && wsReady) {
      try { ws.send(JSON.stringify({ type: 'ping' })); } catch(e) {}
    }
  }, 25000);

  // گرفتن اطلاعات المنت
  function getElementInfo(el) {
    if (!el) return 'عنصر ناشناخته';

    // متن المنت
    let text = (el.innerText || el.value || '').trim().slice(0, 50);

    // نوع المنت
    let type = el.tagName?.toLowerCase() || 'unknown';

    // کلاس یا آیدی
    let identifier = el.id ? '#' + el.id :
                     el.className ? '.' + el.className.split(' ')[0] : '';

    // ترجمه تگ‌های معروف به فارسی
    const tagLabels = {
      'button': 'دکمه',
      'a': 'لینک',
      'input': 'فیلد ورودی',
      'textarea': 'فیلد متن',
      'select': 'منوی انتخاب',
      'img': 'تصویر',
      'video': 'ویدیو',
      'form': 'فرم',
      'table': 'جدول',
      'div': 'بخش',
      'span': 'متن',
      'p': 'پاراگراف',
      'h1': 'عنوان اصلی',
      'h2': 'عنوان',
      'h3': 'عنوان',
      'nav': 'منوی ناوبری',
      'header': 'سربرگ',
      'footer': 'پاورقی',
      'li': 'آیتم لیست'
    };

    let typeLabel = tagLabels[type] || type;

    if (text) {
      return typeLabel + ' "' + text + '"';
    }
    return typeLabel + (identifier ? ' ' + identifier : '');
  }

  // محاسبه درصد موقعیت
  function getPositionPercent(e) {
    return {
      xPercent: (e.clientX / window.innerWidth) * 100,
      yPercent: (e.clientY / window.innerHeight) * 100
    };
  }

  // Debounce
  function shouldSend() {
    const now = Date.now();
    if (now - lastEventTime < DEBOUNCE_MS) return false;
    lastEventTime = now;
    return true;
  }

  // Event Listeners - window capture phase (بالاترین اولویت ممکن)
  // mousedown + pointerdown به عنوان فالبک برای زمانی که overlay ها click رو مصرف می‌کنند

  // کلیک - بالاترین لایه capture
  window.addEventListener('click', function(e) {
    if (!shouldSend()) return;
    sendToInspector('click', {
      target: e.target?.tagName,
      elementInfo: getElementInfo(e.target),
      position: getPositionPercent(e)
    });
  }, true);

  // 🆕 فالبک: mousedown و pointerdown (برای overlay هایی که click رو stop می‌کنند)
  var lastPointerDownTime = 0;
  window.addEventListener('pointerdown', function(e) {
    lastPointerDownTime = Date.now();
    // اگر 200ms بعد click نیومد، pointerdown رو ارسال کن
    setTimeout(function() {
      if (Date.now() - lastEventTime > 180) {
        sendToInspector('click', {
          target: e.target?.tagName,
          elementInfo: getElementInfo(e.target) + ' (pointerdown)',
          position: getPositionPercent(e)
        });
      }
    }, 200);
  }, true);

  // اسکرول
  let scrollTimeout;
  window.addEventListener('scroll', function(e) {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(function() {
      sendToInspector('scroll', {
        elementInfo: 'صفحه',
        position: {
          xPercent: (window.scrollX / (document.body.scrollWidth - window.innerWidth)) * 100 || 0,
          yPercent: (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100 || 0
        }
      });
    }, 200);
  }, true);

  // تایپ در فیلدها
  window.addEventListener('input', function(e) {
    if (!shouldSend()) return;
    if (e.target?.tagName === 'INPUT' || e.target?.tagName === 'TEXTAREA') {
      sendToInspector('input', {
        target: e.target?.tagName,
        elementInfo: getElementInfo(e.target),
        position: { xPercent: 50, yPercent: 50 }
      });
    }
  }, true);

  // فوکوس
  window.addEventListener('focus', function(e) {
    if (!shouldSend()) return;
    if (e.target && e.target !== document && e.target !== document.body) {
      sendToInspector('focus', {
        target: e.target?.tagName,
        elementInfo: getElementInfo(e.target),
        position: { xPercent: 50, yPercent: 50 }
      });
    }
  }, true);

  // 🔴 گیرنده خطاهای جاوااسکریپت فرانت‌اند
  var errorCount = 0;
  var MAX_ERRORS = 50; // حداکثر خطا در هر صفحه
  var consoleLogCount = 0;
  var MAX_CONSOLE_LOGS = 200; // حداکثر لاگ کنسول

  window.onerror = function(message, source, lineno, colno, error) {
    if (errorCount >= MAX_ERRORS) return;
    errorCount++;
    var errorInfo = (message || 'Unknown error').toString().slice(0, 150);
    if (source) errorInfo += ' (at ' + source.split('/').pop() + ':' + lineno + ')';
    sendToInspector('error', {
      target: 'window',
      elementInfo: errorInfo,
      position: { xPercent: 50, yPercent: 10 },
      level: 'error'
    });
  };

  window.addEventListener('unhandledrejection', function(e) {
    if (errorCount >= MAX_ERRORS) return;
    errorCount++;
    var reason = (e.reason && (e.reason.message || e.reason.toString())) || 'Promise rejected';
    sendToInspector('error', {
      target: 'promise',
      elementInfo: reason.toString().slice(0, 150),
      position: { xPercent: 50, yPercent: 10 },
      level: 'error'
    });
  });

  // 🔵 رهگیری تمام متدهای کنسول - تفکیک لاگ‌های پروژه ایمپورت شده
  function interceptConsole(level, origFn) {
    return function() {
      origFn.apply(console, arguments);
      if (consoleLogCount >= MAX_CONSOLE_LOGS) return;
      consoleLogCount++;
      var msg = Array.prototype.slice.call(arguments).map(function(a) {
        return typeof a === 'object' ? JSON.stringify(a).slice(0, 200) : String(a).slice(0, 200);
      }).join(' ').slice(0, 500);
      // فیلتر: لاگ‌های خود bridge رو ارسال نکن
      if (msg.indexOf('Inspector Bridge') !== -1) return;
      if (msg.indexOf('🌉') !== -1) return;
      // ارسال به inspector با تفکیک سطح
      sendToInspector(level === 'error' ? 'console-error' : 'console-log', {
        target: 'console',
        elementInfo: msg,
        position: { xPercent: 50, yPercent: 10 },
        level: level
      });
    };
  }

  var origConsoleLog = console.log;
  var origConsoleWarn = console.warn;
  var origConsoleError = console.error;
  var origConsoleInfo = console.info;
  var origConsoleDebug = console.debug;

  console.log = interceptConsole('log', origConsoleLog);
  console.warn = interceptConsole('warn', origConsoleWarn);
  console.error = interceptConsole('error', origConsoleError);
  console.info = interceptConsole('info', origConsoleInfo);
  console.debug = interceptConsole('debug', origConsoleDebug);

  // 🔍 MutationObserver - تشخیص لایه‌های خطا (Error Overlays)
  var __attachedOverlays = new WeakSet();
  function attachOverlayListeners(node) {
    if (__attachedOverlays.has(node)) return;
    __attachedOverlays.add(node);
    var overlayText = (node.textContent || '').slice(0, 500);
    sendToInspector('error-overlay', {
      target: node.tagName,
      elementInfo: 'لایه خطا شناسایی شد: ' + overlayText.slice(0, 200),
      position: { xPercent: 50, yPercent: 50 },
      level: 'error'
    });
    // اتصال listener ها به لایه خطا (click + pointerdown)
    node.addEventListener('click', function(e) {
      sendToInspector('click', {
        target: e.target?.tagName,
        elementInfo: getElementInfo(e.target) + ' (error overlay)',
        position: getPositionPercent(e)
      });
    }, true);
    node.addEventListener('pointerdown', function(e) {
      sendToInspector('click', {
        target: e.target?.tagName,
        elementInfo: getElementInfo(e.target) + ' (overlay pointerdown)',
        position: getPositionPercent(e)
      });
    }, true);
    // اگر Shadow DOM داره، listener داخلش هم بذار
    if (node.shadowRoot) {
      node.shadowRoot.addEventListener('click', function(e) {
        sendToInspector('click', {
          target: e.target?.tagName,
          elementInfo: getElementInfo(e.target) + ' (shadow DOM)',
          position: { xPercent: 50, yPercent: 50 }
        });
      }, true);
    }
  }

  function isOverlayElement(node) {
    try {
      var style = window.getComputedStyle(node);
      var zIndex = parseInt(style.zIndex) || 0;
      var isFixed = style.position === 'fixed' || style.position === 'absolute';
      var isFullScreen = node.offsetWidth > window.innerWidth * 0.8 && node.offsetHeight > window.innerHeight * 0.5;
      return isFixed && (zIndex > 1000 || isFullScreen);
    } catch(e) { return false; }
  }

  try {
    var overlayObserver = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        for (var i = 0; i < mutation.addedNodes.length; i++) {
          var node = mutation.addedNodes[i];
          if (node.nodeType !== 1) continue;
          if (isOverlayElement(node)) attachOverlayListeners(node);
        }
      });
    });
    if (document.body) {
      overlayObserver.observe(document.body, { childList: true, subtree: true });
    } else {
      document.addEventListener('DOMContentLoaded', function() {
        overlayObserver.observe(document.body, { childList: true, subtree: true });
      });
    }
  } catch(obsErr) {}

  // 🔁 اسکن دوره‌ای DOM برای overlay هایی که MutationObserver ممکنه از دست بده
  setInterval(function() {
    try {
      var allFixed = document.querySelectorAll('[style*="position: fixed"], [style*="position:fixed"]');
      for (var i = 0; i < allFixed.length; i++) {
        if (isOverlayElement(allFixed[i])) attachOverlayListeners(allFixed[i]);
      }
      // بررسی nextjs-portal و shadow roots
      var portals = document.querySelectorAll('nextjs-portal, [id*="overlay"], [id*="error"], [class*="overlay"], [class*="error-boundary"]');
      for (var j = 0; j < portals.length; j++) {
        if (portals[j].shadowRoot && !__attachedOverlays.has(portals[j])) {
          attachOverlayListeners(portals[j]);
        }
      }
    } catch(e) {}
  }, 2000);

  // اعلام آماده بودن
  try {
    window.parent.postMessage({
      type: 'inspector-bridge-ready',
      pageUrl: window.location.href,
      isInIframe: isInIframe,
      timestamp: Date.now()
    }, '*');
    console.log('🌉 Inspector Bridge: Ready message sent to parent');
  } catch (readyErr) {
    console.warn('🌉 Inspector Bridge: Failed to send ready message', readyErr);
  }

  console.log('🌉 Inspector Bridge: Script loaded and active!');
  console.log('🌉 Inspector Bridge: Click, scroll, or type to test');
})();
</script>
'''

# 🆕 محتوای Bridge Script برای پروژه‌های React/Next.js (نسخه JS/TS)
INSPECTOR_BRIDGE_SCRIPT_JS = '''
// 🌉 Inspector Bridge Script - Auto-injected
// Version: 2.4
// ارتباط با Inspector از طریق WebSocket (حل مشکل cross-origin)
/* eslint-disable */
// @ts-nocheck
if (typeof window !== 'undefined' && !window.__inspectorBridgeLoaded) {
  // @ts-ignore
  window.__inspectorBridgeLoaded = true;

  const isInIframe = window !== window.parent;
  const WS_URL = '__BRIDGE_WS_URL__';
  let ws = null;
  let wsReady = false;
  let messageQueue = [];

  console.log('🌉 Inspector Bridge: Active (WebSocket mode)');

  // Debounce
  const DEBOUNCE_MS = 100;
  let lastEventTime = 0;
  let messagesSent = 0;
  const shouldSend = () => {
    const now = Date.now();
    if (now - lastEventTime < DEBOUNCE_MS) return false;
    lastEventTime = now;
    return true;
  };

  // اتصال WebSocket
  const connectWS = () => {
    if (!WS_URL || WS_URL === '__BRIDGE_WS_URL__') return;
    try {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => { ws.send(JSON.stringify({ type: 'register', role: 'bridge' })); };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'registered') {
            wsReady = true;
            console.log('🌉 Inspector Bridge: WebSocket connected');
            messageQueue.forEach(m => ws.send(JSON.stringify(m)));
            messageQueue = [];
            ws.send(JSON.stringify({ type: 'inspector-bridge-ready', pageUrl: window.location.href, isInIframe, timestamp: Date.now() }));
          } else if (msg.type === 'command') {
            handleCommand(msg);
          }
        } catch (e) {}
      };
      ws.onclose = () => { wsReady = false; setTimeout(connectWS, 3000); };
      ws.onerror = () => {};
    } catch (e) {}
  };

  const handleCommand = (msg) => {
    if (msg.command === 'click') {
      const el = document.querySelector(msg.selector);
      if (el) el.click();
    } else if (msg.command === 'navigate') {
      window.location.href = msg.url;
    } else if (msg.command === 'get-elements') {
      const elements = [];
      document.querySelectorAll('a, button, input, textarea, select, [role="button"]').forEach((el, i) => {
        elements.push({ index: i, tag: el.tagName.toLowerCase(), text: (el.innerText || el.value || '').trim().slice(0, 50), id: el.id, href: el.href || '' });
      });
      sendToInspector('elements-list', { elements });
    }
  };

  const sendToInspector = (action, data) => {
    const message = {
      type: 'inspector-bridge-event', action,
      elementInfo: data.elementInfo || '', position: data.position || { xPercent: 50, yPercent: 50 },
      pageUrl: window.location.href, timestamp: Date.now(),
      level: data.level || null, source: 'imported-project',
      networkMeta: data.networkMeta || null
    };
    if (ws && wsReady) ws.send(JSON.stringify(message));
    else if (ws) messageQueue.push(message);
    if (isInIframe) { try { window.parent.postMessage(message, '*'); } catch(e) {} }
  };

  const getElementInfo = (el) => {
    if (!el) return '';
    const text = (el.innerText || el.value || '').trim().slice(0, 50);
    const tag = el.tagName?.toLowerCase() || '';
    const id = el.id ? '#' + el.id : '';
    const cls = el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '';
    const tagLabels = {
      'button': 'دکمه', 'a': 'لینک', 'input': 'فیلد ورودی', 'textarea': 'فیلد متن',
      'select': 'منوی انتخاب', 'img': 'تصویر', 'form': 'فرم', 'div': 'بخش', 'span': 'متن',
      'p': 'پاراگراف', 'h1': 'عنوان اصلی', 'h2': 'عنوان', 'h3': 'عنوان', 'nav': 'منوی ناوبری',
      'header': 'سربرگ', 'footer': 'پاورقی', 'li': 'آیتم لیست', 'table': 'جدول', 'video': 'ویدیو'
    };
    const typeLabel = tagLabels[tag] || tag;
    if (text) return typeLabel + ' "' + text + '"';
    return typeLabel + (id || cls || '');
  };

  const getPositionPercent = (e) => ({
    xPercent: (e.clientX / window.innerWidth) * 100,
    yPercent: (e.clientY / window.innerHeight) * 100
  });

  // Event Listeners - window capture phase (بالاترین اولویت)
  window.addEventListener('click', (e) => {
    if (!shouldSend()) return;
    sendToInspector('click', { elementInfo: getElementInfo(e.target), position: getPositionPercent(e) });
  }, true);

  // 🆕 فالبک pointerdown برای overlay هایی که click رو مصرف می‌کنند
  window.addEventListener('pointerdown', (e) => {
    setTimeout(() => {
      if (Date.now() - lastEventTime > 180) {
        sendToInspector('click', { elementInfo: getElementInfo(e.target) + ' (pointerdown)', position: getPositionPercent(e) });
      }
    }, 200);
  }, true);

  window.addEventListener('input', (e) => {
    if (!shouldSend()) return;
    if (e.target?.tagName === 'INPUT' || e.target?.tagName === 'TEXTAREA') {
      sendToInspector('input', { elementInfo: getElementInfo(e.target) });
    }
  }, true);

  window.addEventListener('focus', (e) => {
    if (!shouldSend()) return;
    if (e.target && e.target !== document && e.target !== document.body) {
      sendToInspector('focus', { elementInfo: getElementInfo(e.target) });
    }
  }, true);

  let scrollTimeout;
  window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => { sendToInspector('scroll', { elementInfo: 'صفحه' }); }, 200);
  }, true);

  // 🔵 رهگیری تمام متدهای کنسول
  let consoleLogCount = 0;
  const MAX_CONSOLE_LOGS = 200;

  const interceptConsole = (level, origFn) => (...args) => {
    origFn.apply(console, args);
    if (consoleLogCount >= MAX_CONSOLE_LOGS) return;
    consoleLogCount++;
    const msg = args.map(a => typeof a === 'object' ? JSON.stringify(a).slice(0, 200) : String(a).slice(0, 200)).join(' ').slice(0, 500);
    if (msg.includes('Inspector Bridge') || msg.includes('🌉')) return;
    sendToInspector(level === 'error' ? 'console-error' : 'console-log', { elementInfo: msg, level });
  };

  const origLog = console.log, origWarn = console.warn, origError = console.error, origInfo = console.info, origDebug = console.debug;
  console.log = interceptConsole('log', origLog);
  console.warn = interceptConsole('warn', origWarn);
  console.error = interceptConsole('error', origError);
  console.info = interceptConsole('info', origInfo);
  console.debug = interceptConsole('debug', origDebug);

  // 🔴 خطاهای JS
  let errorCount = 0;
  const MAX_ERRORS = 50;

  window.onerror = (message, source, lineno) => {
    if (errorCount >= MAX_ERRORS) return;
    errorCount++;
    let errorInfo = String(message || 'Unknown error').slice(0, 150);
    if (source) errorInfo += ` (at ${source.split('/').pop()}:${lineno})`;
    sendToInspector('error', { elementInfo: errorInfo, level: 'error' });
  };

  window.addEventListener('unhandledrejection', (e) => {
    if (errorCount >= MAX_ERRORS) return;
    errorCount++;
    const reason = (e.reason?.message || e.reason?.toString()) || 'Promise rejected';
    sendToInspector('error', { elementInfo: String(reason).slice(0, 150), level: 'error' });
  });

  // 🔍 MutationObserver + اسکن دوره‌ای - تشخیص لایه‌های خطا
  const __attachedOverlays = new WeakSet();
  const isOverlay = (node) => {
    try {
      const s = window.getComputedStyle(node);
      const z = parseInt(s.zIndex) || 0;
      return (s.position === 'fixed' || s.position === 'absolute') && (z > 1000 || (node.offsetWidth > window.innerWidth*0.8 && node.offsetHeight > window.innerHeight*0.5));
    } catch(e) { return false; }
  };
  const attachOverlay = (node) => {
    if (__attachedOverlays.has(node)) return;
    __attachedOverlays.add(node);
    sendToInspector('error-overlay', { elementInfo: 'لایه خطا: ' + (node.textContent||'').slice(0,200), level: 'error' });
    node.addEventListener('click', (e) => {
      sendToInspector('click', { elementInfo: getElementInfo(e.target) + ' (overlay)', position: getPositionPercent(e) });
    }, true);
    node.addEventListener('pointerdown', (e) => {
      sendToInspector('click', { elementInfo: getElementInfo(e.target) + ' (overlay pointerdown)', position: getPositionPercent(e) });
    }, true);
    if (node.shadowRoot) {
      node.shadowRoot.addEventListener('click', (e) => {
        sendToInspector('click', { elementInfo: getElementInfo(e.target) + ' (shadow)', position: { xPercent: 50, yPercent: 50 } });
      }, true);
    }
  };

  try {
    const overlayObs = new MutationObserver((mutations) => {
      mutations.forEach(m => m.addedNodes.forEach(node => {
        if (node.nodeType !== 1) return;
        if (isOverlay(node)) attachOverlay(node);
      }));
    });
    if (document.body) overlayObs.observe(document.body, { childList: true, subtree: true });
    else document.addEventListener('DOMContentLoaded', () => overlayObs.observe(document.body, { childList: true, subtree: true }));
  } catch(e) {}

  // 🔁 اسکن دوره‌ای برای overlay های از دست رفته
  setInterval(() => {
    try {
      document.querySelectorAll('[style*="position: fixed"], [style*="position:fixed"], nextjs-portal, [id*="overlay"], [id*="error"], [class*="overlay"]').forEach(el => {
        if (isOverlay(el)) attachOverlay(el);
        if (el.shadowRoot && !__attachedOverlays.has(el)) attachOverlay(el);
      });
    } catch(e) {}
  }, 2000);

  // 🌐 Network Monitoring (fetch + XHR) — v2.4
  (function setupNetworkMonitoring() {
    try {
      let __netReqSeq = 0;
      const __maskValue = (v) => {
        if (!v) return v;
        const s = String(v);
        return s.length > 8 ? s.slice(0, 4) + '****' + s.slice(-2) : '****';
      };
      const __maskUrl = (url) => {
        try {
          const u = new URL(url, window.location.origin);
          u.searchParams.forEach((val, key) => {
            const lk = key.toLowerCase();
            if (lk.indexOf('token') >= 0 || lk.indexOf('key') >= 0 || lk.indexOf('secret') >= 0 || lk.indexOf('password') >= 0) {
              u.searchParams.set(key, __maskValue(val));
            }
          });
          return u.toString();
        } catch(e) { return String(url); }
      };
      const __summarizeUrl = (url) => {
        try {
          const u = new URL(url, window.location.origin);
          let path = u.pathname;
          if (path.length > 80) path = path.slice(0, 77) + '...';
          return u.host + path;
        } catch(e) { return String(url).slice(0, 100); }
      };
      if (typeof window.fetch === 'function' && !window.__inspectorFetchHooked) {
        window.__inspectorFetchHooked = true;
        const origFetch = window.fetch.bind(window);
        window.fetch = function(input, init) {
          const reqId = 'fetch_' + (++__netReqSeq) + '_' + Date.now();
          const url = typeof input === 'string' ? input : (input && input.url) || '';
          const method = (init && init.method) || (input && input.method) || 'GET';
          const maskedUrl = __maskUrl(url);
          const startedAt = Date.now();
          try {
            sendToInspector('network-request', {
              elementInfo: method.toUpperCase() + ' ' + __summarizeUrl(maskedUrl),
              level: null,
              networkMeta: { reqId, method: method.toUpperCase(), url: maskedUrl, startedAt }
            });
          } catch(e) {}
          return origFetch(input, init).then((res) => {
            try {
              const dur = Date.now() - startedAt;
              const ok = res && res.ok;
              const status = res ? res.status : 0;
              const label = method.toUpperCase() + ' ' + __summarizeUrl(maskedUrl) + ' → ' + status + ' (' + dur + 'ms)';
              sendToInspector(ok ? 'network-response' : 'network-error', {
                elementInfo: label,
                level: ok ? null : 'error',
                networkMeta: { reqId, method: method.toUpperCase(), url: maskedUrl, status, durationMs: dur, ok: !!ok }
              });
            } catch(e) {}
            return res;
          }).catch((err) => {
            try {
              const dur = Date.now() - startedAt;
              sendToInspector('network-error', {
                elementInfo: method.toUpperCase() + ' ' + __summarizeUrl(maskedUrl) + ' ✗ ' + (err && err.message || 'fetch failed'),
                level: 'error',
                networkMeta: { reqId, method: method.toUpperCase(), url: maskedUrl, status: 0, durationMs: dur, ok: false, errorMessage: err && err.message }
              });
            } catch(e) {}
            throw err;
          });
        };
      }
      if (window.XMLHttpRequest && !window.__inspectorXhrHooked) {
        window.__inspectorXhrHooked = true;
        const origOpen = XMLHttpRequest.prototype.open;
        const origSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function(method, url) {
          try {
            this.__inspectorReqId = 'xhr_' + (++__netReqSeq) + '_' + Date.now();
            this.__inspectorMethod = (method || 'GET').toUpperCase();
            this.__inspectorUrl = __maskUrl(url);
          } catch(e) {}
          return origOpen.apply(this, arguments);
        };
        XMLHttpRequest.prototype.send = function() {
          const xhr = this;
          try {
            xhr.__inspectorStartedAt = Date.now();
            sendToInspector('network-request', {
              elementInfo: xhr.__inspectorMethod + ' ' + __summarizeUrl(xhr.__inspectorUrl),
              level: null,
              networkMeta: { reqId: xhr.__inspectorReqId, method: xhr.__inspectorMethod, url: xhr.__inspectorUrl, startedAt: xhr.__inspectorStartedAt }
            });
            xhr.addEventListener('loadend', () => {
              try {
                const dur = Date.now() - xhr.__inspectorStartedAt;
                const status = xhr.status || 0;
                const ok = status >= 200 && status < 400;
                const label = xhr.__inspectorMethod + ' ' + __summarizeUrl(xhr.__inspectorUrl) + ' → ' + status + ' (' + dur + 'ms)';
                sendToInspector(ok ? 'network-response' : 'network-error', {
                  elementInfo: label,
                  level: ok ? null : 'error',
                  networkMeta: { reqId: xhr.__inspectorReqId, method: xhr.__inspectorMethod, url: xhr.__inspectorUrl, status, durationMs: dur, ok }
                });
              } catch(e) {}
            });
          } catch(e) {}
          return origSend.apply(this, arguments);
        };
      }
    } catch(e) { /* non-critical */ }
  })();

  connectWS();
  setInterval(() => { if (ws && wsReady) try { ws.send(JSON.stringify({ type: 'ping' })); } catch(e) {} }, 25000);

  // فالبک postMessage
  if (isInIframe) {
    try { window.parent.postMessage({ type: 'inspector-bridge-ready', pageUrl: window.location.href }, '*'); } catch(e) {}
  }
}
// 🌉 End of Inspector Bridge Script
'''

# 🆕 Next.js App Router - Client Component برای Bridge Script (WebSocket)
INSPECTOR_BRIDGE_VERSION = "2.4"  # نسخه فعلی bridge template - افزایش بده هر وقت template تغییر کرد

INSPECTOR_BRIDGE_CLIENT_COMPONENT = '''// @ts-nocheck
"use client";
// 🌉 Inspector Bridge Script - Client Component for Next.js App Router
// Version: 2.4
// ارتباط با Inspector از طریق WebSocket (حل مشکل cross-origin)
import { useEffect } from "react";

declare global {
  interface Window {
    __inspectorBridgeLoaded?: boolean;
  }
}

export default function InspectorBridge() {
  useEffect(() => {
    if (typeof window === "undefined" || window.__inspectorBridgeLoaded) return;
    window.__inspectorBridgeLoaded = true;

    const isInIframe = window !== window.parent;
    const WS_URL = "__BRIDGE_WS_URL__";
    let ws = null;
    let wsReady = false;
    let messageQueue = [];

    console.log("🌉 Inspector Bridge: Active (WebSocket mode)");

    // Debounce
    const DEBOUNCE_MS = 100;
    let lastEventTime = 0;
    let messagesSent = 0;
    const shouldSend = () => {
      const now = Date.now();
      if (now - lastEventTime < DEBOUNCE_MS) return false;
      lastEventTime = now;
      return true;
    };

    // 🌐 اتصال WebSocket
    const connectWS = () => {
      if (!WS_URL || WS_URL === "__BRIDGE_WS_URL__") return;
      try {
        ws = new WebSocket(WS_URL);
        ws.onopen = () => { ws.send(JSON.stringify({ type: "register", role: "bridge" })); };
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "registered") {
              wsReady = true;
              console.log("🌉 Inspector Bridge: WebSocket connected");
              messageQueue.forEach(m => ws.send(JSON.stringify(m)));
              messageQueue = [];
              ws.send(JSON.stringify({ type: "inspector-bridge-ready", pageUrl: window.location.href, isInIframe, timestamp: Date.now() }));
            } else if (msg.type === "command") {
              handleCommand(msg);
            }
          } catch (e) {}
        };
        ws.onclose = () => { wsReady = false; setTimeout(connectWS, 3000); };
        ws.onerror = () => {};
      } catch (e) {}
    };

    const handleCommand = (msg) => {
      if (msg.command === "click") {
        const el = document.querySelector(msg.selector);
        if (el) el.click();
      } else if (msg.command === "navigate") {
        window.location.href = msg.url;
      } else if (msg.command === "get-elements") {
        const elements = [];
        document.querySelectorAll("a, button, input, textarea, select, [role=button]").forEach((el, i) => {
          elements.push({ index: i, tag: el.tagName.toLowerCase(), text: (el.innerText || el.value || "").trim().slice(0, 50), id: el.id, href: el.href || "" });
        });
        sendToInspector("elements-list", { elements });
      }
    };

    const sendToInspector = (action, data) => {
      const message = {
        type: "inspector-bridge-event", action,
        elementInfo: data.elementInfo || "", position: data.position || { xPercent: 50, yPercent: 50 },
        pageUrl: window.location.href, timestamp: Date.now(),
        level: data.level || null, source: "imported-project",
        networkMeta: data.networkMeta || null
      };
      if (ws && wsReady) ws.send(JSON.stringify(message));
      else if (ws) messageQueue.push(message);
      if (isInIframe) { try { window.parent.postMessage(message, "*"); } catch(e) {} }
    };

    const getElementInfo = (el) => {
      if (!el) return "";
      const text = (el.innerText || el.value || "").trim().slice(0, 50);
      const tag = el.tagName?.toLowerCase() || "";
      const id = el.id ? "#" + el.id : "";
      const cls = el.className && typeof el.className === "string" ? "." + el.className.split(" ")[0] : "";
      const tagLabels = {
        "button": "دکمه", "a": "لینک", "input": "فیلد ورودی", "textarea": "فیلد متن",
        "select": "منوی انتخاب", "img": "تصویر", "form": "فرم", "div": "بخش", "span": "متن",
        "p": "پاراگراف", "h1": "عنوان اصلی", "h2": "عنوان", "h3": "عنوان", "nav": "منوی ناوبری",
        "header": "سربرگ", "footer": "پاورقی", "li": "آیتم لیست", "table": "جدول", "video": "ویدیو"
      };
      const typeLabel = tagLabels[tag] || tag;
      if (text) return `${typeLabel} "${text}"`;
      return typeLabel + (id || cls || "");
    };

    const getPositionPercent = (e) => ({
      xPercent: (e.clientX / window.innerWidth) * 100,
      yPercent: (e.clientY / window.innerHeight) * 100
    });

    // window capture phase (بالاترین اولویت)
    const handleClick = (e) => {
      if (!shouldSend()) return;
      sendToInspector("click", { elementInfo: getElementInfo(e.target), position: getPositionPercent(e) });
    };
    const handleInput = (e) => {
      if (!shouldSend()) return;
      if (e.target?.tagName === "INPUT" || e.target?.tagName === "TEXTAREA") {
        sendToInspector("input", { elementInfo: getElementInfo(e.target) });
      }
    };
    const handleFocus = (e) => {
      if (!shouldSend()) return;
      if (e.target && e.target !== document && e.target !== document.body) {
        sendToInspector("focus", { elementInfo: getElementInfo(e.target) });
      }
    };
    let scrollTimeout;
    const handleScroll = () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => { sendToInspector("scroll", { elementInfo: "صفحه" }); }, 200);
    };

    window.addEventListener("click", handleClick, true);
    window.addEventListener("input", handleInput, true);
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("focus", handleFocus, true);

    // 🆕 فالبک pointerdown
    const handlePointerDown = (e) => {
      setTimeout(() => {
        if (Date.now() - lastEventTime > 180) {
          sendToInspector("click", { elementInfo: getElementInfo(e.target) + " (pointerdown)", position: getPositionPercent(e) });
        }
      }, 200);
    };
    window.addEventListener("pointerdown", handlePointerDown, true);

    // 🔵 رهگیری تمام متدهای کنسول
    let consoleLogCount = 0;
    const MAX_CONSOLE_LOGS = 200;

    const interceptConsole = (level, origFn) => (...args) => {
      origFn.apply(console, args);
      if (consoleLogCount >= MAX_CONSOLE_LOGS) return;
      consoleLogCount++;
      const msg = args.map(a => typeof a === "object" ? JSON.stringify(a).slice(0, 200) : String(a).slice(0, 200)).join(" ").slice(0, 500);
      if (msg.includes("Inspector Bridge") || msg.includes("🌉")) return;
      sendToInspector(level === "error" ? "console-error" : "console-log", { elementInfo: msg, level });
    };

    const origLog = console.log, origWarn = console.warn, origError = console.error, origInfo = console.info, origDebug = console.debug;
    console.log = interceptConsole("log", origLog);
    console.warn = interceptConsole("warn", origWarn);
    console.error = interceptConsole("error", origError);
    console.info = interceptConsole("info", origInfo);
    console.debug = interceptConsole("debug", origDebug);

    // 🔴 خطاهای JS
    let errorCount = 0;
    const MAX_ERRORS = 50;

    const handleError = (event) => {
      if (errorCount >= MAX_ERRORS) return;
      errorCount++;
      let errorInfo = String(event.message || "Unknown error").slice(0, 150);
      if (event.filename) errorInfo += ` (at ${event.filename.split("/").pop()}:${event.lineno})`;
      sendToInspector("error", { elementInfo: errorInfo, level: "error" });
    };

    const handleRejection = (event) => {
      if (errorCount >= MAX_ERRORS) return;
      errorCount++;
      const reason = (event.reason?.message || event.reason?.toString()) || "Promise rejected";
      sendToInspector("error", { elementInfo: String(reason).slice(0, 150), level: "error" });
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);

    // 🔍 MutationObserver + اسکن دوره‌ای - تشخیص لایه‌های خطا
    const __attachedOverlays = new WeakSet();
    const isOverlay = (node) => {
      try {
        const s = window.getComputedStyle(node);
        const z = parseInt(s.zIndex) || 0;
        return (s.position === "fixed" || s.position === "absolute") && (z > 1000 || (node.offsetWidth > window.innerWidth*0.8 && node.offsetHeight > window.innerHeight*0.5));
      } catch(e) { return false; }
    };
    const attachOverlay = (node) => {
      if (__attachedOverlays.has(node)) return;
      __attachedOverlays.add(node);
      sendToInspector("error-overlay", { elementInfo: "لایه خطا: " + (node.textContent||"").slice(0,200), level: "error" });
      node.addEventListener("click", (e) => {
        sendToInspector("click", { elementInfo: getElementInfo(e.target) + " (overlay)", position: getPositionPercent(e) });
      }, true);
      node.addEventListener("pointerdown", (e) => {
        sendToInspector("click", { elementInfo: getElementInfo(e.target) + " (overlay pointerdown)", position: getPositionPercent(e) });
      }, true);
      if (node.shadowRoot) {
        node.shadowRoot.addEventListener("click", (e) => {
          sendToInspector("click", { elementInfo: getElementInfo(e.target) + " (shadow)", position: { xPercent: 50, yPercent: 50 } });
        }, true);
      }
    };

    let overlayObs;
    try {
      overlayObs = new MutationObserver((mutations) => {
        mutations.forEach(m => m.addedNodes.forEach(node => {
          if (node.nodeType !== 1) return;
          if (isOverlay(node)) attachOverlay(node);
        }));
      });
      if (document.body) overlayObs.observe(document.body, { childList: true, subtree: true });
      else document.addEventListener("DOMContentLoaded", () => overlayObs.observe(document.body, { childList: true, subtree: true }));
    } catch(e) {}

    // 🔁 اسکن دوره‌ای
    const overlayScan = setInterval(() => {
      try {
        document.querySelectorAll('[style*="position: fixed"], [style*="position:fixed"], nextjs-portal, [id*="overlay"], [id*="error"], [class*="overlay"]').forEach(el => {
          if (isOverlay(el)) attachOverlay(el);
          if (el.shadowRoot && !__attachedOverlays.has(el)) attachOverlay(el);
        });
      } catch(e) {}
    }, 2000);

    // 🌐 Network Monitoring (fetch + XHR) — v2.4
    (function setupNetworkMonitoring() {
      try {
        let __netReqSeq = 0;
        const __maskValue = (v) => {
          if (!v) return v;
          const s = String(v);
          return s.length > 8 ? s.slice(0, 4) + "****" + s.slice(-2) : "****";
        };
        const __maskUrl = (url) => {
          try {
            const u = new URL(url, window.location.origin);
            u.searchParams.forEach((val, key) => {
              const lk = key.toLowerCase();
              if (lk.indexOf("token") >= 0 || lk.indexOf("key") >= 0 || lk.indexOf("secret") >= 0 || lk.indexOf("password") >= 0) {
                u.searchParams.set(key, __maskValue(val));
              }
            });
            return u.toString();
          } catch(e) { return String(url); }
        };
        const __summarizeUrl = (url) => {
          try {
            const u = new URL(url, window.location.origin);
            let path = u.pathname;
            if (path.length > 80) path = path.slice(0, 77) + "...";
            return u.host + path;
          } catch(e) { return String(url).slice(0, 100); }
        };
        if (typeof window.fetch === "function" && !window.__inspectorFetchHooked) {
          window.__inspectorFetchHooked = true;
          const origFetch = window.fetch.bind(window);
          window.fetch = function(input, init) {
            const reqId = "fetch_" + (++__netReqSeq) + "_" + Date.now();
            const url = typeof input === "string" ? input : (input && input.url) || "";
            const method = (init && init.method) || (input && input.method) || "GET";
            const maskedUrl = __maskUrl(url);
            const startedAt = Date.now();
            try {
              sendToInspector("network-request", {
                elementInfo: method.toUpperCase() + " " + __summarizeUrl(maskedUrl),
                level: null,
                networkMeta: { reqId, method: method.toUpperCase(), url: maskedUrl, startedAt }
              });
            } catch(e) {}
            return origFetch(input, init).then((res) => {
              try {
                const dur = Date.now() - startedAt;
                const ok = res && res.ok;
                const status = res ? res.status : 0;
                const label = method.toUpperCase() + " " + __summarizeUrl(maskedUrl) + " → " + status + " (" + dur + "ms)";
                sendToInspector(ok ? "network-response" : "network-error", {
                  elementInfo: label,
                  level: ok ? null : "error",
                  networkMeta: { reqId, method: method.toUpperCase(), url: maskedUrl, status, durationMs: dur, ok: !!ok }
                });
              } catch(e) {}
              return res;
            }).catch((err) => {
              try {
                const dur = Date.now() - startedAt;
                sendToInspector("network-error", {
                  elementInfo: method.toUpperCase() + " " + __summarizeUrl(maskedUrl) + " ✗ " + (err && err.message || "fetch failed"),
                  level: "error",
                  networkMeta: { reqId, method: method.toUpperCase(), url: maskedUrl, status: 0, durationMs: dur, ok: false, errorMessage: err && err.message }
                });
              } catch(e) {}
              throw err;
            });
          };
        }
        if (window.XMLHttpRequest && !window.__inspectorXhrHooked) {
          window.__inspectorXhrHooked = true;
          const origOpen = XMLHttpRequest.prototype.open;
          const origSend = XMLHttpRequest.prototype.send;
          XMLHttpRequest.prototype.open = function(method, url) {
            try {
              this.__inspectorReqId = "xhr_" + (++__netReqSeq) + "_" + Date.now();
              this.__inspectorMethod = (method || "GET").toUpperCase();
              this.__inspectorUrl = __maskUrl(url);
            } catch(e) {}
            return origOpen.apply(this, arguments);
          };
          XMLHttpRequest.prototype.send = function() {
            const xhr = this;
            try {
              xhr.__inspectorStartedAt = Date.now();
              sendToInspector("network-request", {
                elementInfo: xhr.__inspectorMethod + " " + __summarizeUrl(xhr.__inspectorUrl),
                level: null,
                networkMeta: { reqId: xhr.__inspectorReqId, method: xhr.__inspectorMethod, url: xhr.__inspectorUrl, startedAt: xhr.__inspectorStartedAt }
              });
              xhr.addEventListener("loadend", () => {
                try {
                  const dur = Date.now() - xhr.__inspectorStartedAt;
                  const status = xhr.status || 0;
                  const ok = status >= 200 && status < 400;
                  const label = xhr.__inspectorMethod + " " + __summarizeUrl(xhr.__inspectorUrl) + " → " + status + " (" + dur + "ms)";
                  sendToInspector(ok ? "network-response" : "network-error", {
                    elementInfo: label,
                    level: ok ? null : "error",
                    networkMeta: { reqId: xhr.__inspectorReqId, method: xhr.__inspectorMethod, url: xhr.__inspectorUrl, status, durationMs: dur, ok }
                  });
                } catch(e) {}
              });
            } catch(e) {}
            return origSend.apply(this, arguments);
          };
        }
      } catch(e) { /* non-critical */ }
    })();

    connectWS();
    const heartbeat = setInterval(() => { if (ws && wsReady) try { ws.send(JSON.stringify({ type: "ping" })); } catch(e) {} }, 25000);

    // فالبک postMessage
    if (isInIframe) {
      try { window.parent.postMessage({ type: "inspector-bridge-ready", pageUrl: window.location.href }, "*"); } catch(e) {}
    }

    return () => {
      window.removeEventListener("click", handleClick, true);
      window.removeEventListener("pointerdown", handlePointerDown, true);
      window.removeEventListener("input", handleInput, true);
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("focus", handleFocus, true);
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
      console.log = origLog; console.warn = origWarn; console.error = origError; console.info = origInfo; console.debug = origDebug;
      if (overlayObs) overlayObs.disconnect();
      clearInterval(heartbeat);
      clearInterval(overlayScan);
      if (ws) { try { ws.close(); } catch(e) {} }
    };
  }, []);

  return null;
}
// 🌉 End of Inspector Bridge Script
'''


@router.post("/inspector/inject-bridge")
async def inject_bridge_script(
    request: InjectBridgeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🌉 تزریق Bridge Script به پروژه

    این endpoint:
    1. فایل index.html پروژه را از GitHub دریافت می‌کند
    2. اسکریپت Bridge را به آن اضافه می‌کند
    3. تغییرات را commit و push می‌کند
    4. یک deploy جدید trigger می‌شود
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import httpx
    import base64

    slog.api_request("POST", "/inspector/inject-bridge",
        project_id=request.project_id,
        remove=request.remove
    )

    try:
        # دریافت پروژه
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # توکن GitHub
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            return {
                "success": False,
                "error": "توکن GitHub تنظیم نشده است"
            }

        # استخراج owner/repo از github_path یا extra_data
        github_path = getattr(project, 'github_path', None)
        owner = None
        repo = None

        # اگر github_path خالی بود، چک کن شاید در extra_data باشد
        if not github_path:
            extra_data = getattr(project, 'extra_data', None)
            if extra_data:
                try:
                    extra = json.loads(extra_data) if isinstance(extra_data, str) else extra_data

                    # روش 1: github_path یا github_url مستقیم
                    github_path = extra.get('github_path') or extra.get('github_url') or extra.get('repository_url') or extra.get('source_url') or extra.get('clone_url')

                    # روش 2: owner و repo جداگانه
                    if not github_path and extra.get('owner') and extra.get('repo'):
                        owner = extra.get('owner')
                        repo = extra.get('repo')
                        github_path = f"{owner}/{repo}"

                        # 🆕 خودکار ست کردن github_path برای دفعات بعد
                        project.github_path = github_path
                        db.commit()
                        slog.info(f"Auto-set github_path from extra_data: {github_path}")
                except Exception as e:
                    slog.warning(f"Failed to parse extra_data: {e}")

        if not github_path:
            # برگرداندن اطلاعات تشخیصی
            return {
                "success": False,
                "error": "این پروژه به GitHub متصل نیست.",
                "debug_info": {
                    "project_id": project.id,
                    "project_name": project.name,
                    "github_path": getattr(project, 'github_path', 'N/A'),
                    "extra_data_preview": str(getattr(project, 'extra_data', ''))[:200] if getattr(project, 'extra_data', None) else None,
                    "hint": "برای اتصال، از قسمت تنظیمات پروژه آدرس GitHub را وارد کنید"
                }
            }

        # پارس کردن github_path که می‌تواند به فرمت‌های مختلف باشد:
        # - owner/repo
        # - https://github.com/owner/repo
        # - https://github.com/owner/repo.git
        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            return {"success": False, "error": f"فرمت GitHub path نامعتبر است: {github_path}"}

        owner, repo = parts[0], parts[1]

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient() as client:
            index_path = None
            index_content = None
            index_sha = None
            found_html_files = []
            is_framework_without_html = False
            is_nextjs = False
            is_nuxt = False
            is_gatsby = False
            all_files = []  # لیست همه فایل‌ها
            search_error = None  # خطای جستجو
            is_js_file = False  # آیا فایل پیدا شده JS/TS است؟

            # اگر مسیر سفارشی داده شده، اول آن را امتحان کن
            if request.custom_path:
                try:
                    res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{request.custom_path}",
                        headers=headers,
                        timeout=10.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("encoding") == "base64":
                            index_content = base64.b64decode(data["content"]).decode('utf-8')
                            index_sha = data["sha"]
                            index_path = request.custom_path
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"فایل در مسیر سفارشی یافت نشد: {request.custom_path}",
                        "detail": str(e)
                    }

            # 🆕 جستجوی فوق‌هوشمند: اول package.json رو بخون، بعد تصمیم بگیر
            # متغیرهای tracking برای debug
            detected_framework = None
            entry_candidates = []
            package_json_found = False
            package_json_status = None
            tree_status = None
            deps_found = {}
            default_branch = 'main'
            all_package_jsons = []  # همه package.json های پیدا شده
            html_files = []  # همه فایل‌های HTML پیدا شده
            pattern_match_files = []  # فایل‌های پیدا شده با pattern search
            frontend_files = []  # فایل‌های داخل پوشه frontend
            pattern_search_reason = None  # دلیل عدم استفاده از pattern match
            bridge_already_installed_in = None  # فایلی که قبلاً bridge دارد

            if not index_path:
                try:
                    slog.info(f"🔍 Smart search starting for {owner}/{repo}")

                    # 📦 مرحله ۱: خواندن package.json برای تشخیص فریم‌ورک
                    pkg_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/package.json",
                        headers=headers,
                        timeout=10.0
                    )
                    package_json_status = pkg_res.status_code
                    slog.info(f"📦 package.json status: {package_json_status}")

                    if pkg_res.status_code == 200:
                        package_json_found = True
                        pkg_data = pkg_res.json()
                        if pkg_data.get("encoding") == "base64":
                            pkg_content = json.loads(base64.b64decode(pkg_data["content"]).decode('utf-8'))
                            slog.info(f"📦 Found package.json: {pkg_content.get('name', 'unnamed')}")

                            # تشخیص فریم‌ورک از dependencies
                            deps = {**pkg_content.get('dependencies', {}), **pkg_content.get('devDependencies', {})}
                            # ذخیره لیست dependency ها برای debug
                            deps_found = list(deps.keys())[:20]  # فقط ۲۰ تای اول
                            slog.info(f"📦 Dependencies found: {deps_found}")

                            if 'next' in deps:
                                detected_framework = 'nextjs'
                                entry_candidates = [
                                    # App Router (layout.tsx is the root layout)
                                    'app/layout.tsx', 'app/layout.jsx', 'app/layout.js',
                                    'src/app/layout.tsx', 'src/app/layout.jsx', 'src/app/layout.js',
                                    # Pages Router (_app is the root wrapper)
                                    'pages/_app.tsx', 'pages/_app.jsx', 'pages/_app.js',
                                    'src/pages/_app.tsx', 'src/pages/_app.jsx', 'src/pages/_app.js',
                                    # _document for HTML-level injection
                                    'pages/_document.tsx', 'pages/_document.jsx', 'pages/_document.js',
                                    'src/pages/_document.tsx', 'src/pages/_document.js',
                                ]
                            elif 'nuxt' in deps:
                                detected_framework = 'nuxt'
                                entry_candidates = ['app.vue', 'layouts/default.vue', 'pages/index.vue']
                            elif 'gatsby' in deps:
                                detected_framework = 'gatsby'
                                entry_candidates = ['gatsby-browser.js', 'src/pages/index.js', 'src/pages/index.tsx']
                            elif 'vue' in deps:
                                detected_framework = 'vue'
                                entry_candidates = ['src/App.vue', 'src/main.js', 'src/main.ts', 'app/App.vue']
                            elif 'react' in deps or 'react-dom' in deps:
                                detected_framework = 'react'
                                # بررسی اینکه Vite هست یا CRA
                                if 'vite' in deps:
                                    entry_candidates = ['src/main.tsx', 'src/main.jsx', 'src/main.js', 'index.html']
                                else:
                                    entry_candidates = ['src/index.tsx', 'src/index.jsx', 'src/index.js', 'public/index.html']
                            elif 'svelte' in deps:
                                detected_framework = 'svelte'
                                entry_candidates = ['src/App.svelte', 'src/main.js', 'src/main.ts']
                            elif 'angular' in deps or '@angular/core' in deps:
                                detected_framework = 'angular'
                                entry_candidates = ['src/main.ts', 'src/index.html']

                            slog.info(f"🔧 Detected framework from package.json: {detected_framework}")
                            slog.info(f"📄 Entry candidates: {entry_candidates}")

                    # 🐍 مرحله ۱.۵: اگر package.json نبود، requirements.txt رو چک کن (پروژه‌های Python)
                    if not package_json_found:
                        slog.info("📦 No package.json, checking for Python project (requirements.txt)...")
                        req_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/contents/requirements.txt",
                            headers=headers,
                            timeout=10.0
                        )
                        if req_res.status_code == 200:
                            req_data = req_res.json()
                            if req_data.get("encoding") == "base64":
                                req_content = base64.b64decode(req_data["content"]).decode('utf-8').lower()
                                slog.info(f"🐍 Found requirements.txt")

                                # تشخیص فریم‌ورک Python
                                if 'flask' in req_content:
                                    detected_framework = 'flask'
                                    entry_candidates = [
                                        'templates/index.html', 'templates/base.html',
                                        'app/templates/index.html', 'app/templates/base.html',
                                        'src/templates/index.html'
                                    ]
                                    slog.info("🐍 Detected Flask project")
                                elif 'django' in req_content:
                                    detected_framework = 'django'
                                    entry_candidates = [
                                        'templates/base.html', 'templates/index.html',
                                        'app/templates/base.html', 'core/templates/base.html'
                                    ]
                                    slog.info("🐍 Detected Django project")
                                elif 'fastapi' in req_content or 'starlette' in req_content:
                                    detected_framework = 'fastapi'
                                    entry_candidates = [
                                        'templates/index.html', 'static/index.html',
                                        'frontend/index.html'
                                    ]
                                    slog.info("🐍 Detected FastAPI project")
                                else:
                                    detected_framework = 'python'
                                    entry_candidates = [
                                        'templates/index.html', 'templates/base.html',
                                        'static/index.html', 'public/index.html'
                                    ]
                                    slog.info("🐍 Detected generic Python project")

                    # 🌳 مرحله ۲: دریافت لیست فایل‌ها
                    # اول اطلاعات ریپو رو بگیر برای default branch
                    default_branch = 'main'
                    try:
                        repo_info = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}",
                            headers=headers,
                            timeout=10.0
                        )
                        if repo_info.status_code == 200:
                            default_branch = repo_info.json().get('default_branch', 'main')
                            slog.info(f"🌿 Default branch: {default_branch}")
                    except Exception as e:
                        slog.warning(f"Failed to get repo info: {e}")

                    tree_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
                        headers=headers,
                        timeout=15.0
                    )

                    # اگر branch پیش‌فرض کار نکرد، main و master رو امتحان کن
                    if tree_res.status_code == 404 and default_branch != 'main':
                        slog.info(f"Branch '{default_branch}' not found, trying 'main'")
                        tree_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1",
                            headers=headers,
                            timeout=15.0
                        )

                    if tree_res.status_code == 404:
                        slog.info("Branch 'main' not found, trying 'master'")
                        tree_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1",
                            headers=headers,
                            timeout=15.0
                        )

                    tree_status = tree_res.status_code
                    slog.info(f"🌳 GitHub tree response: {tree_status}")

                    if tree_res.status_code == 200:
                        tree_data = tree_res.json()
                        all_files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]
                        slog.info(f"📁 Total files in repo: {len(all_files)}")

                        # 📂 فایل‌های داخل پوشه‌های frontend-like
                        frontend_files = [f for f in all_files if any(f.startswith(p) for p in ['frontend/', 'client/', 'web/', 'ui/'])]
                        slog.info(f"📂 Frontend folder files: {frontend_files[:20]}")

                        # 🔍 مرحله ۲.۵: جستجوی هوشمند در همه پوشه‌ها
                        # پیدا کردن همه package.json ها (نه فقط root)
                        all_package_jsons = [f for f in all_files if f.endswith('package.json') and 'node_modules' not in f]
                        slog.info(f"📦 Found {len(all_package_jsons)} package.json files: {all_package_jsons}")

                        # 🔑 تغییر مهم: اگر فریم‌ورک تشخیص داده نشده، پوشه‌های nested رو چک کن
                        # (حتی اگر root package.json وجود داشته باشه)
                        if not detected_framework and all_package_jsons:
                            # اولویت با پوشه‌های frontend-like
                            frontend_folders = ['frontend/', 'client/', 'web/', 'app/', 'ui/', 'src/']
                            # فقط package.json های nested (نه root)
                            nested_pkgs = [p for p in all_package_jsons if '/' in p]
                            sorted_pkgs = sorted(nested_pkgs, key=lambda p: (
                                0 if any(p.startswith(f) for f in frontend_folders) else 1,
                                len(p)  # کوتاه‌تر = نزدیک‌تر به root
                            ))
                            slog.info(f"📦 Checking nested packages: {sorted_pkgs}")

                            for pkg_path in sorted_pkgs:
                                try:
                                    pkg_res2 = await client.get(
                                        f"https://api.github.com/repos/{owner}/{repo}/contents/{pkg_path}",
                                        headers=headers,
                                        timeout=10.0
                                    )
                                    if pkg_res2.status_code == 200:
                                        pkg_data2 = pkg_res2.json()
                                        if pkg_data2.get("encoding") == "base64":
                                            pkg_content2 = json.loads(base64.b64decode(pkg_data2["content"]).decode('utf-8'))
                                            deps2 = {**pkg_content2.get('dependencies', {}), **pkg_content2.get('devDependencies', {})}
                                            pkg_folder = '/'.join(pkg_path.split('/')[:-1])
                                            if pkg_folder:
                                                pkg_folder += '/'

                                            slog.info(f"📦 Checking nested package.json: {pkg_path} (folder: {pkg_folder})")
                                            slog.info(f"📦 Dependencies: {list(deps2.keys())[:10]}")

                                            # تشخیص فریم‌ورک
                                            if 'next' in deps2:
                                                detected_framework = 'nextjs'
                                                entry_candidates = [
                                                    f'{pkg_folder}app/layout.tsx', f'{pkg_folder}app/layout.jsx', f'{pkg_folder}app/layout.js',
                                                    f'{pkg_folder}src/app/layout.tsx', f'{pkg_folder}src/app/layout.jsx',
                                                    f'{pkg_folder}pages/_app.tsx', f'{pkg_folder}pages/_app.jsx', f'{pkg_folder}pages/_app.js',
                                                    f'{pkg_folder}src/pages/_app.tsx', f'{pkg_folder}src/pages/_app.js',
                                                ]
                                            elif 'react' in deps2 or 'react-dom' in deps2:
                                                detected_framework = 'react'
                                                if 'vite' in deps2:
                                                    entry_candidates = [
                                                        f'{pkg_folder}index.html',
                                                        f'{pkg_folder}src/main.tsx', f'{pkg_folder}src/main.jsx'
                                                    ]
                                                else:
                                                    entry_candidates = [
                                                        f'{pkg_folder}public/index.html',
                                                        f'{pkg_folder}src/index.tsx', f'{pkg_folder}src/index.jsx'
                                                    ]
                                            elif 'vue' in deps2:
                                                detected_framework = 'vue'
                                                entry_candidates = [
                                                    f'{pkg_folder}index.html',
                                                    f'{pkg_folder}public/index.html',
                                                    f'{pkg_folder}src/main.js'
                                                ]
                                            elif 'svelte' in deps2:
                                                detected_framework = 'svelte'
                                                entry_candidates = [f'{pkg_folder}src/App.svelte', f'{pkg_folder}index.html']
                                            elif 'angular' in deps2 or '@angular/core' in deps2:
                                                detected_framework = 'angular'
                                                entry_candidates = [f'{pkg_folder}src/index.html']

                                            if detected_framework:
                                                slog.info(f"✅ Found frontend in {pkg_folder}: {detected_framework}")
                                                package_json_found = True
                                                deps_found = list(deps2.keys())[:20]
                                                break
                                except Exception as e:
                                    slog.warning(f"Failed to check {pkg_path}: {e}")
                                    continue

                        # 🎯 مرحله ۳: پیدا کردن بهترین فایل برای تزریق

                        # اول فایل‌های HTML و template رو چک کن
                        # پشتیبانی از فرمت‌های مختلف: .html, .htm, .jinja, .jinja2, .j2
                        template_extensions = ('.html', '.htm', '.jinja', '.jinja2', '.j2')
                        html_files = [f for f in all_files
                                    if any(f.lower().endswith(ext) for ext in template_extensions)
                                    and 'node_modules' not in f]
                        slog.info(f"🔍 Found {len(html_files)} HTML/template files: {html_files[:10]}")

                        # امتیازدهی به HTML ها
                        def score_html_file(path: str) -> int:
                            score = 0
                            path_lower = path.lower()
                            if path_lower.endswith('index.html'):
                                score += 100
                            # 🔑 پوشه‌های frontend-like امتیاز بالا
                            if 'frontend/' in path_lower or 'client/' in path_lower or 'web/' in path_lower:
                                score += 90
                            if 'public/' in path_lower:
                                score += 80
                            # 🐍 Python templates folder
                            if 'templates/' in path_lower:
                                score += 70
                                if 'base.html' in path_lower or 'layout.html' in path_lower:
                                    score += 30  # base templates are good for injection
                            if 'src/' in path_lower and 'public/' not in path_lower:
                                score += 30
                            if 'static/' in path_lower:
                                score += 40
                            if 'dist/' in path_lower or 'build/' in path_lower:
                                score -= 50
                            return score

                        html_files_scored = [(f, score_html_file(f)) for f in html_files]
                        html_files_scored.sort(key=lambda x: -x[1])

                        # اگر HTML با امتیاز بالا پیدا شد، از اون استفاده کن
                        slog.info(f"🔍 Checking {len(html_files_scored)} HTML files for injection...")
                        for html_path, score in html_files_scored:
                            slog.info(f"  📄 {html_path} (score: {score})")
                            if score >= 50:  # فقط HTML های خوب
                                try:
                                    content_res = await client.get(
                                        f"https://api.github.com/repos/{owner}/{repo}/contents/{html_path}",
                                        headers=headers,
                                        timeout=10.0
                                    )
                                    slog.info(f"  📥 Fetch status: {content_res.status_code}")
                                    if content_res.status_code == 200:
                                        data = content_res.json()
                                        if data.get("encoding") == "base64":
                                            content = base64.b64decode(data["content"]).decode('utf-8')
                                            content_preview = content[:200].replace('\n', ' ')
                                            slog.info(f"  📝 Content preview: {content_preview}")

                                            # 🔑 بررسی ساده‌تر: فقط چک کن که HTML باشه
                                            # (حتی Vite minimal HTML هم قبول کن)
                                            is_html = ('<html' in content.lower() or
                                                      '<!doctype' in content.lower() or
                                                      '<head' in content.lower() or
                                                      '<body' in content.lower() or
                                                      html_path.endswith('.html'))  # اعتماد به پسوند فایل

                                            has_bridge = 'Inspector Bridge Script' in content

                                            slog.info(f"  ✓ Is HTML: {is_html}, Has Bridge: {has_bridge}")

                                            if is_html and not has_bridge:
                                                index_content = content
                                                index_sha = data["sha"]
                                                index_path = html_path
                                                is_js_file = False
                                                slog.info(f"✅ Selected HTML for injection: {html_path} (score: {score})")
                                                break
                                            elif has_bridge:
                                                slog.info(f"  ⏭️ Skipped (already has bridge): {html_path}")
                                except Exception as e:
                                    slog.warning(f"  ❌ Error checking {html_path}: {e}")
                                    continue

                        # 🔍 مرحله ۴: اگر HTML پیدا نشد، از entry candidates استفاده کن
                        if not index_path and entry_candidates:
                            slog.info(f"No good HTML found, trying framework entry points: {entry_candidates}")
                            for candidate in entry_candidates:
                                slog.info(f"  🔎 Checking: {candidate} - exists: {candidate in all_files}")
                                if candidate in all_files:
                                    try:
                                        content_res = await client.get(
                                            f"https://api.github.com/repos/{owner}/{repo}/contents/{candidate}",
                                            headers=headers,
                                            timeout=10.0
                                        )
                                        if content_res.status_code == 200:
                                            data = content_res.json()
                                            if data.get("encoding") == "base64":
                                                content = base64.b64decode(data["content"]).decode('utf-8')
                                                if 'Inspector Bridge Script' not in content:
                                                    index_content = content
                                                    index_sha = data["sha"]
                                                    index_path = candidate
                                                    is_js_file = not candidate.endswith('.html')
                                                    slog.info(f"✅ Found entry point: {candidate}")
                                                    break
                                    except Exception as e:
                                        slog.warning(f"Failed to fetch {candidate}: {e}")
                                        continue

                        # 🔍 مرحله ۴.۵: جستجوی هوشمند برای فایل‌های Next.js/React
                        # اگر entry candidates دقیق پیدا نشد، دنبال pattern بگرد
                        if not index_path and detected_framework:
                            slog.info(f"Entry candidates not found exactly, searching by pattern in {len(all_files)} files...")

                            # الگوهای فایل بر اساس فریم‌ورک
                            if detected_framework == 'nextjs':
                                patterns = ['layout.tsx', 'layout.jsx', 'layout.js', '_app.tsx', '_app.jsx', '_app.js', '_document.tsx', '_document.jsx', '_document.js', 'page.tsx', 'page.jsx', 'page.js']
                            elif detected_framework in ['react', 'vue', 'svelte']:
                                patterns = ['main.tsx', 'main.jsx', 'main.js', 'App.tsx', 'App.jsx', 'App.js', 'index.tsx', 'index.jsx']
                            else:
                                patterns = ['index.tsx', 'index.jsx', 'index.js', 'main.tsx', 'main.jsx', 'main.js']

                            # پیدا کردن فایل‌هایی که با pattern مطابقت دارند
                            matching_files = []
                            for f in all_files:
                                for pattern in patterns:
                                    if f.endswith(pattern) and 'node_modules' not in f:
                                        matching_files.append(f)
                                        break

                            slog.info(f"  📂 Found {len(matching_files)} matching files: {matching_files[:10]}")
                            pattern_match_files = matching_files.copy()  # ذخیره برای debug
                            pattern_search_reason = None  # دلیل عدم استفاده
                            bridge_already_installed_in = None  # فایلی که قبلاً bridge دارد

                            # اولویت با فایل‌های در پوشه frontend
                            matching_files.sort(key=lambda x: (
                                0 if 'frontend/' in x or 'client/' in x else 1,
                                0 if '/src/' in x or '/app/' in x or '/pages/' in x else 1,
                                len(x)
                            ))

                            for match_file in matching_files:
                                try:
                                    slog.info(f"  🔎 Trying: {match_file}")
                                    content_res = await client.get(
                                        f"https://api.github.com/repos/{owner}/{repo}/contents/{match_file}",
                                        headers=headers,
                                        timeout=10.0
                                    )
                                    slog.info(f"  📥 Status: {content_res.status_code}")
                                    if content_res.status_code == 200:
                                        data = content_res.json()
                                        if data.get("encoding") == "base64":
                                            content = base64.b64decode(data["content"]).decode('utf-8')
                                            # بررسی هر دو روش: inline script یا InspectorBridge import
                                            has_bridge = 'Inspector Bridge Script' in content or 'InspectorBridge' in content
                                            slog.info(f"  📝 Has bridge: {has_bridge}, Content length: {len(content)}")
                                            if not has_bridge:
                                                index_content = content
                                                index_sha = data["sha"]
                                                index_path = match_file
                                                is_js_file = True
                                                slog.info(f"✅ Found by pattern search: {match_file}")
                                                break
                                            else:
                                                pattern_search_reason = f"File {match_file} already has bridge script"
                                                bridge_already_installed_in = match_file  # ذخیره فایل
                                                slog.info(f"  ✅ Bridge already installed in: {match_file}")
                                                break  # نیازی به ادامه نیست
                                    else:
                                        pattern_search_reason = f"Failed to fetch {match_file}: HTTP {content_res.status_code}"
                                        slog.warning(f"  ❌ Fetch failed: HTTP {content_res.status_code}")
                                        continue  # 🔧 مهم: برو سراغ فایل بعدی
                                except Exception as e:
                                    pattern_search_reason = f"Error fetching {match_file}: {str(e)}"
                                    slog.warning(f"  ❌ Error: {e}")
                                    continue

                        # 🔎 مرحله ۵: اگر هنوز پیدا نشد، جستجوی عمومی
                        if not index_path:
                            slog.info("Trying generic search for any entry file...")
                            generic_patterns = [
                                # فایل‌های entry point رایج - JavaScript/TypeScript
                                'src/App.tsx', 'src/App.jsx', 'src/App.js',
                                'src/index.tsx', 'src/index.jsx', 'src/index.js',
                                'src/main.tsx', 'src/main.jsx', 'src/main.js', 'src/main.ts',
                                'app/App.tsx', 'app/App.js',
                                'App.tsx', 'App.js', 'App.jsx',
                                'index.tsx', 'index.js',
                                # HTML های عمومی
                                'index.html', 'public/index.html',
                                # 🐍 Python templates
                                'templates/index.html', 'templates/base.html', 'templates/layout.html',
                                'app/templates/index.html', 'app/templates/base.html',
                                'frontend/index.html', 'static/index.html',
                                'client/index.html', 'web/index.html'
                            ]

                            for pattern in generic_patterns:
                                if pattern in all_files:
                                    try:
                                        content_res = await client.get(
                                            f"https://api.github.com/repos/{owner}/{repo}/contents/{pattern}",
                                            headers=headers,
                                            timeout=10.0
                                        )
                                        if content_res.status_code == 200:
                                            data = content_res.json()
                                            if data.get("encoding") == "base64":
                                                content = base64.b64decode(data["content"]).decode('utf-8')
                                                if 'Inspector Bridge Script' not in content:
                                                    index_content = content
                                                    index_sha = data["sha"]
                                                    index_path = pattern
                                                    is_js_file = not pattern.endswith('.html')
                                                    slog.info(f"✅ Found via generic search: {pattern}")
                                                    break
                                    except:
                                        continue

                        # 📝 ذخیره اطلاعات برای نمایش به کاربر
                        found_html_files = [f for f, _ in html_files_scored[:10]]
                        if detected_framework:
                            is_framework_without_html = detected_framework in ['nextjs', 'nuxt', 'gatsby']
                            is_nextjs = detected_framework == 'nextjs'
                            is_nuxt = detected_framework == 'nuxt'
                            is_gatsby = detected_framework == 'gatsby'

                except Exception as e:
                    slog.warning(f"Smart HTML search failed: {e}")
                    found_html_files = []
                    is_framework_without_html = False
                    search_error = str(e)

            # ✅ اگر Bridge قبلاً نصب شده
            if not index_path and bridge_already_installed_in:
                # اگر درخواست حذف یا re-inject هست، فایل رو بخون تا بتونیم عمل کنیم
                if request.remove or getattr(request, 'force_update', False):
                    slog.info(f"Bridge found in {bridge_already_installed_in}, loading for {'remove' if request.remove else 'update'}")
                    try:
                        content_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/contents/{bridge_already_installed_in}",
                            headers=headers,
                            timeout=10.0
                        )
                        if content_res.status_code == 200:
                            data = content_res.json()
                            if data.get("encoding") == "base64":
                                index_content = base64.b64decode(data["content"]).decode('utf-8')
                                index_sha = data["sha"]
                                index_path = bridge_already_installed_in
                                is_js_file = not bridge_already_installed_in.endswith('.html')
                                slog.info(f"✅ Loaded bridge file for modification: {bridge_already_installed_in}")
                    except Exception as e:
                        slog.warning(f"Failed to load bridge file: {e}")

                # اگر هنوز index_path ست نشده (یعنی درخواست inject عادی بود)
                if not index_path:
                    framework_name = None
                    if detected_framework:
                        framework_map = {
                            'nextjs': 'Next.js', 'nuxt': 'Nuxt', 'gatsby': 'Gatsby',
                            'react': 'React', 'vue': 'Vue', 'svelte': 'Svelte', 'angular': 'Angular'
                        }
                        framework_name = framework_map.get(detected_framework, detected_framework)

                    slog.info(f"✅ Bridge already installed in {bridge_already_installed_in}")
                    return {
                        "success": True,
                        "message": "Bridge script is already installed",
                        "already_installed": True,
                        "file_path": bridge_already_installed_in,
                        "framework_detected": framework_name,
                        "debug": {
                            "github_path": f"{owner}/{repo}",
                            "bridge_file": bridge_already_installed_in
                        }
                    }

            if not index_path:
                # تشخیص بهتر نوع مشکل
                # 🔍 اطلاعات فریم‌ورک برای نمایش
                framework_name = None
                if detected_framework:
                    framework_map = {
                        'nextjs': 'Next.js',
                        'nuxt': 'Nuxt',
                        'gatsby': 'Gatsby',
                        'react': 'React',
                        'vue': 'Vue',
                        'svelte': 'Svelte',
                        'angular': 'Angular',
                        # Python frameworks
                        'flask': 'Flask',
                        'django': 'Django',
                        'fastapi': 'FastAPI',
                        'python': 'Python'
                    }
                    framework_name = framework_map.get(detected_framework, detected_framework)

                error_response = {
                    "success": False,
                    "need_custom_path": True,
                    "found_html_files": found_html_files,  # همیشه برگردون
                    "framework_detected": framework_name,
                    # 🔍 Debug info - اطلاعات کامل برای عیب‌یابی
                    "debug": {
                        "github_path": f"{owner}/{repo}",
                        "default_branch": default_branch,
                        "total_files_found": len(all_files),
                        "html_files_count": len(found_html_files),
                        "all_html_files": html_files[:20],
                        "all_package_jsons": all_package_jsons,
                        "search_error": search_error,
                        "detected_framework_raw": detected_framework,
                        "entry_candidates": entry_candidates,
                        "frontend_files": frontend_files[:30],  # 🆕 فایل‌های frontend
                        "pattern_match_files": pattern_match_files[:20],  # 🆕 فایل‌های یافته شده با pattern
                        "pattern_search_reason": pattern_search_reason,  # 🆕 دلیل عدم استفاده از pattern match
                        "files_sample": all_files[:30] if all_files else [],  # نمایش ۳۰ فایل
                        "package_json_found": package_json_found,
                        "package_json_status": package_json_status,
                        "tree_status": tree_status,
                        "deps_sample": deps_found[:10] if isinstance(deps_found, list) else []
                    }
                }

                if is_framework_without_html:
                    error_response["error"] = "این پروژه از فریم‌ورکی استفاده می‌کند که HTML در زمان build ساخته می‌شود"
                    error_response["hint"] = "برای این نوع پروژه‌ها، باید فایل _document.js یا _app.js را ویرایش کنید یا از روش دیگری استفاده کنید"
                    error_response["alternative_hint"] = "می‌توانید اسکریپت Bridge را مستقیماً در کد پروژه اضافه کنید"
                elif found_html_files:
                    error_response["error"] = "فایل HTML اصلی به‌صورت خودکار پیدا نشد"
                    error_response["hint"] = "فایل‌های HTML زیر پیدا شدند - یکی را انتخاب کنید:"
                else:
                    # 🚫 پروژه Backend-only - هیچ HTML ندارد
                    error_response["error"] = "⚠️ این پروژه فرانت‌اند ندارد (Backend-only)"
                    error_response["hint"] = "Bridge Script فقط روی پروژه‌هایی با فایل HTML کار می‌کند"
                    error_response["is_backend_only"] = True
                    error_response["suggestion"] = "اگر فرانت‌اند جداگانه دارید، Bridge را روی آن پروژه فعال کنید"

                return error_response

            # بررسی وجود اسکریپت قبلی
            bridge_marker = "Inspector Bridge Script"
            has_bridge = bridge_marker in index_content

            if request.remove:
                # حذف اسکریپت
                if not has_bridge:
                    return {"success": True, "message": "اسکریپت از قبل حذف شده است"}

                # حذف اسکریپت با regex
                if is_js_file:
                    # حذف نسخه JS
                    new_content = re.sub(
                        r'// 🌉 Inspector Bridge Script - Auto-injected.*?// 🌉 End of Inspector Bridge Script\n?',
                        '',
                        index_content,
                        flags=re.DOTALL
                    )
                else:
                    # حذف نسخه HTML
                    new_content = re.sub(
                        r'<!-- Inspector Bridge Script - Auto-injected -->.*?</script>',
                        '',
                        index_content,
                        flags=re.DOTALL
                    )
                commit_message = "🔧 Remove Inspector Bridge Script"
            else:
                # اضافه کردن اسکریپت
                if has_bridge and not request.force_update:
                    return {"success": True, "message": "اسکریپت از قبل تزریق شده است", "already_injected": True}

                # 🔄 force_update: حذف نسخه قدیمی قبل از تزریق نسخه جدید
                if has_bridge and request.force_update:
                    slog.info(f"Force updating bridge in {index_path}")
                    if is_js_file:
                        index_content = re.sub(
                            r'// 🌉 Inspector Bridge Script - Auto-injected.*?// 🌉 End of Inspector Bridge Script\n?',
                            '',
                            index_content,
                            flags=re.DOTALL
                        )
                    else:
                        index_content = re.sub(
                            r'<!-- Inspector Bridge Script - Auto-injected -->.*?</script>',
                            '',
                            index_content,
                            flags=re.DOTALL
                        )
                    # حذف import InspectorBridge اگر هست
                    index_content = re.sub(
                        r'import\s+InspectorBridge\s+from\s+["\']\.\/InspectorBridge["\'];?\s*\n?',
                        '',
                        index_content
                    )
                    # حذف <InspectorBridge /> از JSX
                    index_content = index_content.replace('{<InspectorBridge />}\n        ', '')
                    index_content = index_content.replace('<InspectorBridge />\n', '')
                    index_content = index_content.replace('<InspectorBridge />', '')
                    slog.info(f"Old bridge code removed from {index_path}")

                # 🌐 ساخت WebSocket URL برای Bridge Script
                import os as _os
                backend_url = _os.environ.get("BACKEND_URL", "").rstrip("/")
                if not backend_url:
                    # Render خودکار این متغیر رو ست میکنه
                    backend_url = _os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
                if not backend_url:
                    render_app_name = _os.environ.get("RENDER_SERVICE_NAME", "")
                    if render_app_name:
                        backend_url = f"https://{render_app_name}.onrender.com"
                if not backend_url:
                    backend_url = "http://localhost:8000"

                # تبدیل http/https به ws/wss
                ws_base = backend_url.replace("https://", "wss://").replace("http://", "ws://")
                bridge_ws_url = f"{ws_base}/api/render/ws/bridge/{request.project_id}"

                slog.info(f"🌐 Bridge WS URL: {bridge_ws_url}")

                # جایگزینی placeholder در تمپلیت‌ها
                def replace_bridge_placeholders(script_content: str) -> str:
                    return script_content.replace("__BRIDGE_WS_URL__", bridge_ws_url).replace("__BRIDGE_PROJECT_ID__", str(request.project_id))

                # 🆕 تشخیص نوع فایل bridge
                is_bridge_component_file = index_path.endswith('InspectorBridge.tsx')
                is_nextjs_app_router = ('/app/layout.tsx' in index_path or '/src/app/layout.tsx' in index_path or
                                        '/app/layout.js' in index_path or '/src/app/layout.js' in index_path)

                if is_bridge_component_file:
                    # 🔄 فایل InspectorBridge.tsx - مستقیماً محتوا رو جایگزین کن
                    slog.info(f"Replacing InspectorBridge.tsx content directly")
                    new_content = replace_bridge_placeholders(INSPECTOR_BRIDGE_CLIENT_COMPONENT)
                    commit_message = "🌉 Update Inspector Bridge Client Component"

                elif is_nextjs_app_router:
                    # 🆕 Next.js App Router: باید فایل جداگانه Client Component بسازیم
                    slog.info(f"Detected Next.js App Router, creating client component")

                    # تعیین مسیر فایل جدید
                    layout_dir = '/'.join(index_path.split('/')[:-1])  # مسیر پوشه layout
                    bridge_file_path = f"{layout_dir}/InspectorBridge.tsx"

                    # 1️⃣ ابتدا فایل InspectorBridge.tsx را بساز
                    create_res = await client.put(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{bridge_file_path}",
                        headers=headers,
                        json={
                            "message": "🌉 Add Inspector Bridge Client Component",
                            "content": base64.b64encode(replace_bridge_placeholders(INSPECTOR_BRIDGE_CLIENT_COMPONENT).encode('utf-8')).decode('utf-8'),
                            "branch": "main"
                        },
                        timeout=15.0
                    )

                    if create_res.status_code not in [200, 201]:
                        # شاید فایل از قبل وجود داره - سعی کن update کنی
                        get_res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/contents/{bridge_file_path}",
                            headers=headers,
                            timeout=10.0
                        )
                        if get_res.status_code == 200:
                            existing_sha = get_res.json().get("sha")
                            create_res = await client.put(
                                f"https://api.github.com/repos/{owner}/{repo}/contents/{bridge_file_path}",
                                headers=headers,
                                json={
                                    "message": "🌉 Update Inspector Bridge Client Component",
                                    "content": base64.b64encode(replace_bridge_placeholders(INSPECTOR_BRIDGE_CLIENT_COMPONENT).encode('utf-8')).decode('utf-8'),
                                    "sha": existing_sha,
                                    "branch": "main"
                                },
                                timeout=15.0
                            )

                    slog.info(f"Bridge component created: {create_res.status_code}")

                    # 2️⃣ اضافه کردن import به layout.tsx
                    import_line = 'import InspectorBridge from "./InspectorBridge";\n'
                    component_jsx = "<InspectorBridge />"

                    # اضافه کردن import اگر وجود نداره
                    if 'InspectorBridge' not in index_content:
                        # پیدا کردن آخرین import
                        last_import_match = list(re.finditer(r'^import\s+.+?["\'];?\s*$', index_content, re.MULTILINE))

                        if last_import_match:
                            last_import_end = last_import_match[-1].end()
                            new_content = index_content[:last_import_end] + '\n' + import_line + index_content[last_import_end:]
                        else:
                            # اگر import نداره، در ابتدا اضافه کن
                            new_content = import_line + index_content

                        # اضافه کردن کامپوننت در body
                        # در Next.js App Router، باید داخل {children} قرار بگیره
                        if '{children}' in new_content:
                            new_content = new_content.replace('{children}', f'{{{component_jsx}}}\n        {{children}}')
                        elif '<body' in new_content:
                            # بعد از تگ body اضافه کن
                            body_match = re.search(r'<body[^>]*>', new_content)
                            if body_match:
                                insert_pos = body_match.end()
                                new_content = new_content[:insert_pos] + f'\n        {component_jsx}' + new_content[insert_pos:]
                    else:
                        new_content = index_content  # تغییری نمیخواد

                    commit_message = "🌉 Add Inspector Bridge Script (Next.js App Router)"

                elif is_js_file:
                    # تزریق نسخه JS/TS - در ابتدای فایل (برای پروژه‌های غیر App Router)
                    slog.info(f"Injecting JS version into {index_path}")
                    new_content = replace_bridge_placeholders(INSPECTOR_BRIDGE_SCRIPT_JS) + "\n" + index_content
                    commit_message = "🌉 Add Inspector Bridge Script (JS version)"
                else:
                    # تزریق نسخه HTML - قبل از </head> یا </body>
                    bridge_html = replace_bridge_placeholders(INSPECTOR_BRIDGE_SCRIPT)
                    if "</head>" in index_content:
                        new_content = index_content.replace("</head>", bridge_html + "\n</head>")
                    elif "</body>" in index_content:
                        new_content = index_content.replace("</body>", bridge_html + "\n</body>")
                    else:
                        new_content = index_content + "\n" + bridge_html
                    commit_message = "🌉 Add Inspector Bridge Script for live tracking"

            # آپدیت فایل در GitHub
            update_res = await client.put(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{index_path}",
                headers=headers,
                json={
                    "message": commit_message,
                    "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                    "sha": index_sha,
                    "branch": "main"
                },
                timeout=15.0
            )

            if update_res.status_code in [200, 201]:
                slog.info(f"Bridge script {'removed' if request.remove else 'injected'} successfully",
                    project_id=request.project_id,
                    file_path=index_path
                )

                return {
                    "success": True,
                    "message": "اسکریپت با موفقیت حذف شد" if request.remove else "اسکریپت با موفقیت تزریق شد (با WebSocket)",
                    "file_path": index_path,
                    "commit_url": update_res.json().get("commit", {}).get("html_url"),
                    "ws_url": bridge_ws_url if not request.remove else None,
                    "note": "پس از deploy مجدد، Bridge از طریق WebSocket به Inspector متصل خواهد شد"
                }
            else:
                error_msg = update_res.json().get("message", "خطای ناشناخته")
                return {
                    "success": False,
                    "error": f"خطا در آپدیت فایل: {error_msg}"
                }

    except Exception as e:
        slog.error("Inject bridge script failed", exception=e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/inspector/bridge-status/{project_id}")
async def check_bridge_status(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    🔍 بررسی وضعیت Bridge Script در پروژه
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import httpx
    import base64

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            return {"success": False, "has_bridge": False, "error": "توکن GitHub تنظیم نشده"}

        github_path = getattr(project, 'github_path', None)
        if not github_path:
            return {"success": False, "has_bridge": False, "error": "پروژه به GitHub متصل نیست"}

        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            return {"success": False, "error": f"فرمت GitHub path نامعتبر: {github_path}"}

        owner, repo = parts[0], parts[1]

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # مسیرهای HTML و همچنین فایل‌های فریم‌ورک (Next.js, React, etc.)
        possible_paths = [
            "index.html", "public/index.html", "src/index.html",
            # Next.js App Router
            "src/app/InspectorBridge.tsx", "app/InspectorBridge.tsx",
            "frontend/src/app/InspectorBridge.tsx", "frontend/app/InspectorBridge.tsx",
            # Next.js Pages Router
            "pages/_app.tsx", "pages/_app.js", "src/pages/_app.tsx",
            # React
            "src/main.tsx", "src/main.jsx", "src/index.tsx",
            # Layout files (check for import)
            "src/app/layout.tsx", "app/layout.tsx",
            "frontend/src/app/layout.tsx", "frontend/app/layout.tsx",
        ]
        # مارکرهای بررسی وجود bridge
        bridge_markers = ["Inspector Bridge Script", "InspectorBridge", "__inspectorBridgeLoaded", "__BRIDGE_WS_URL__"]

        async with httpx.AsyncClient() as client:
            for path in possible_paths:
                try:
                    res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                        headers=headers,
                        timeout=10.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("encoding") == "base64":
                            content = base64.b64decode(data["content"]).decode('utf-8')
                            has_bridge = any(marker in content for marker in bridge_markers)
                            if has_bridge:
                                # بررسی اینکه نسخه WebSocket هست یا قدیمی
                                has_websocket = "__BRIDGE_WS_URL__" not in content and "WebSocket" in content
                                # 🔍 بررسی نسخه و مشکلات شناخته شده
                                needs_update = False
                                update_reasons = []
                                # چک نسخه
                                import re as _re
                                version_match = _re.search(r'// Version:\s*([\d.]+)', content)
                                current_version = version_match.group(1) if version_match else "1.0"
                                if current_version != INSPECTOR_BRIDGE_VERSION:
                                    needs_update = True
                                    update_reasons.append(f"نسخه قدیمی ({current_version} → {INSPECTOR_BRIDGE_VERSION})")
                                # چک باگ‌های شناخته شده
                                if 'shouldSend' not in content:
                                    needs_update = True
                                    update_reasons.append("تابع shouldSend موجود نیست")
                                if 'lastEventTime' not in content:
                                    needs_update = True
                                    update_reasons.append("متغیر lastEventTime موجود نیست")
                                if 'declare global' not in content and path.endswith('.tsx'):
                                    needs_update = True
                                    update_reasons.append("declare global برای Window نیست")
                                # چک مشکل escape quote
                                if '" \\"" + text + "\\""' in content or '" "" + text + """' in content:
                                    needs_update = True
                                    update_reasons.append("مشکل escape quote در getElementInfo")
                                return {
                                    "success": True,
                                    "has_bridge": True,
                                    "file_path": path,
                                    "has_websocket": has_websocket,
                                    "version": current_version,
                                    "latest_version": INSPECTOR_BRIDGE_VERSION,
                                    "needs_update": needs_update,
                                    "update_reasons": update_reasons
                                }
                except:
                    continue

        return {
            "success": True,
            "has_bridge": False,
            "error": "فایل bridge یافت نشد"
        }

    except Exception as e:
        slog.error("Check bridge status failed", exception=e)
        return {"success": False, "error": str(e)}


class SetGitHubPathRequest(BaseModel):
    """درخواست تنظیم آدرس GitHub برای پروژه"""
    project_id: str
    github_path: str  # مثال: owner/repo یا https://github.com/owner/repo


@router.post("/inspector/set-github-path")
async def set_project_github_path(
    request: SetGitHubPathRequest,
    db: Session = Depends(get_db)
):
    """
    🔗 تنظیم آدرس GitHub برای پروژه

    این endpoint برای پروژه‌هایی که github_path ندارند یا اشتباه است.
    """
    from ...models.project import Project

    slog.api_request("POST", "/inspector/set-github-path",
        project_id=request.project_id,
        github_path=request.github_path
    )

    try:
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # نرمال‌سازی github_path
        github_path = request.github_path.strip()
        github_path = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")

        # اعتبارسنجی فرمت
        parts = github_path.split("/")
        if len(parts) < 2:
            return {"success": False, "error": "فرمت نامعتبر. باید به شکل owner/repo باشد"}

        # ذخیره
        project.github_path = github_path
        db.commit()

        slog.info(f"GitHub path set for project", project_id=request.project_id, github_path=github_path)

        return {
            "success": True,
            "message": f"آدرس GitHub با موفقیت تنظیم شد: {github_path}",
            "github_path": github_path
        }

    except Exception as e:
        slog.error("Set GitHub path failed", exception=e)
        return {"success": False, "error": str(e)}


@router.get("/inspector/debug-bridge/{project_id}")
async def debug_bridge_injection(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    🔍 Debug endpoint برای بررسی وضعیت Bridge Script

    نشان می‌دهد:
    - آیا پروژه به GitHub متصل است
    - کدام فایل HTML پیدا شده
    - آیا Bridge Script در فایل هست
    - محتوای فایل (قسمتی از آن)
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import httpx
    import base64

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        result = {
            "project_id": project_id,
            "project_name": project.name,
            "github_path": project.github_path,
            "project_type": project.project_type,
        }

        # چک توکن
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""

        if not github_token:
            result["error"] = "توکن GitHub تنظیم نشده"
            return result

        github_path = project.github_path
        if not github_path:
            # تلاش برای استخراج از extra_data
            extra_data = getattr(project, 'extra_data', None)
            if extra_data:
                try:
                    extra = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                    if extra.get('owner') and extra.get('repo'):
                        github_path = f"{extra['owner']}/{extra['repo']}"
                        result["github_path_source"] = "extra_data"
                except:
                    pass

        if not github_path:
            result["error"] = "github_path یافت نشد"
            return result

        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            result["error"] = f"فرمت نامعتبر: {github_path}"
            return result

        owner, repo = parts[0], parts[1]
        result["owner"] = owner
        result["repo"] = repo

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient() as client:
            # دریافت لیست فایل‌ها
            tree_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1",
                headers=headers,
                timeout=15.0
            )

            if tree_res.status_code == 404:
                tree_res = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1",
                    headers=headers,
                    timeout=15.0
                )

            if tree_res.status_code != 200:
                result["error"] = f"خطا در دریافت فایل‌ها: {tree_res.status_code}"
                return result

            tree_data = tree_res.json()
            all_files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]
            html_files = [f for f in all_files if f.endswith('.html')]

            result["total_files"] = len(all_files)
            result["html_files"] = html_files

            # بررسی هر فایل HTML برای وجود Bridge
            files_with_bridge = []
            for html_path in html_files[:10]:  # حداکثر 10 فایل
                try:
                    content_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{html_path}",
                        headers=headers,
                        timeout=10.0
                    )
                    if content_res.status_code == 200:
                        data = content_res.json()
                        if data.get("encoding") == "base64":
                            content = base64.b64decode(data["content"]).decode('utf-8')
                            has_bridge = "Inspector Bridge Script" in content
                            if has_bridge:
                                files_with_bridge.append({
                                    "path": html_path,
                                    "has_bridge": True,
                                    "preview": content[:500] + "..." if len(content) > 500 else content
                                })
                except:
                    continue

            result["files_with_bridge"] = files_with_bridge
            result["bridge_injected"] = len(files_with_bridge) > 0

            if not files_with_bridge:
                result["message"] = "Bridge Script در هیچ فایل HTML یافت نشد!"
            else:
                result["message"] = f"Bridge Script در {len(files_with_bridge)} فایل یافت شد"

            # 🔍 بررسی سایت دیپلوی شده
            preview_url = getattr(project, 'deploy_url', None) or getattr(project, 'preview_url', None)
            if preview_url:
                result["preview_url"] = preview_url
                try:
                    deployed_res = await client.get(
                        preview_url,
                        timeout=15.0,
                        follow_redirects=True
                    )
                    if deployed_res.status_code == 200:
                        deployed_html = deployed_res.text
                        result["deployed_has_bridge"] = "Inspector Bridge Script" in deployed_html
                        result["deployed_has_bridge_marker"] = "__inspectorBridgeLoaded" in deployed_html

                        # اگر در سورس هست ولی در دیپلوی نیست
                        if result["bridge_injected"] and not result["deployed_has_bridge"]:
                            result["diagnosis"] = "⚠️ اسکریپت در GitHub هست ولی در سایت دیپلوی شده نیست! احتمالاً deploy هنوز انجام نشده یا build process اسکریپت را حذف کرده"
                        elif result["deployed_has_bridge"]:
                            result["diagnosis"] = "✅ اسکریپت در سایت دیپلوی شده موجود است"
                        else:
                            result["diagnosis"] = "❌ اسکریپت نه در GitHub و نه در سایت دیپلوی شده موجود است"
                    else:
                        result["deployed_check_error"] = f"HTTP {deployed_res.status_code}"
                except Exception as deploy_check_err:
                    result["deployed_check_error"] = str(deploy_check_err)
            else:
                result["preview_url"] = None
                result["diagnosis"] = "⚠️ URL پیش‌نمایش پروژه تنظیم نشده"

        return result

    except Exception as e:
        slog.error("Debug bridge failed", exception=e)
        return {"success": False, "error": str(e)}


@router.post("/inspector/update-bridge/{project_id}")
async def update_bridge_to_latest(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    🔄 به‌روزرسانی Bridge Script به آخرین نسخه

    این endpoint:
    1. InspectorBridge.tsx را در ریپو پیدا می‌کند
    2. محتوای آن را با آخرین تمپلیت جایگزین می‌کند
    3. تغییرات را commit می‌کند
    4. deploy جدید trigger می‌شود
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import httpx
    import base64

    slog.api_request("POST", "/inspector/update-bridge", project_id=project_id)

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""
        if not github_token:
            return {"success": False, "error": "توکن GitHub تنظیم نشده"}

        github_path = getattr(project, 'github_path', None)
        if not github_path:
            extra_data = getattr(project, 'extra_data', None)
            if extra_data:
                try:
                    extra = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                    github_path = extra.get('github_path') or extra.get('github_url') or extra.get('repository_url')
                    if not github_path and extra.get('owner') and extra.get('repo'):
                        github_path = f"{extra['owner']}/{extra['repo']}"
                except:
                    pass
        if not github_path:
            return {"success": False, "error": "پروژه به GitHub متصل نیست"}

        github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
        parts = github_path_clean.split("/")
        if len(parts) < 2:
            return {"success": False, "error": f"فرمت GitHub path نامعتبر: {github_path}"}

        owner, repo = parts[0], parts[1]
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # مسیرهای ممکن برای InspectorBridge.tsx
        bridge_paths = [
            "src/app/InspectorBridge.tsx", "app/InspectorBridge.tsx",
            "frontend/src/app/InspectorBridge.tsx", "frontend/app/InspectorBridge.tsx",
        ]

        bridge_markers = ["Inspector Bridge Script", "InspectorBridge", "__inspectorBridgeLoaded"]

        # همچنین مسیرهای HTML و JS/TS
        other_paths = [
            "index.html", "public/index.html", "src/index.html",
            "pages/_app.tsx", "pages/_app.js", "src/pages/_app.tsx",
            "src/main.tsx", "src/main.jsx", "src/index.tsx",
            "src/app/layout.tsx", "app/layout.tsx",
        ]

        async with httpx.AsyncClient() as client:
            # 🔍 اول دنبال InspectorBridge.tsx بگرد
            for path in bridge_paths:
                try:
                    res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                        headers=headers, timeout=10.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("encoding") == "base64":
                            content = base64.b64decode(data["content"]).decode('utf-8')
                            if any(marker in content for marker in bridge_markers):
                                # پیدا شد! آپدیت کن
                                slog.info(f"Found bridge at {path}, updating to v{INSPECTOR_BRIDGE_VERSION}")

                                # ساخت WebSocket URL
                                import os as _os
                                backend_url = _os.environ.get("BACKEND_URL", "").rstrip("/")
                                if not backend_url:
                                    backend_url = _os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
                                if not backend_url:
                                    render_app_name = _os.environ.get("RENDER_SERVICE_NAME", "")
                                    if render_app_name:
                                        backend_url = f"https://{render_app_name}.onrender.com"
                                if not backend_url:
                                    backend_url = "http://localhost:8000"

                                ws_base = backend_url.replace("https://", "wss://").replace("http://", "ws://")
                                bridge_ws_url = f"{ws_base}/api/render/ws/bridge/{project_id}"

                                # جایگزینی محتوا با آخرین تمپلیت
                                new_content = INSPECTOR_BRIDGE_CLIENT_COMPONENT.replace(
                                    "__BRIDGE_WS_URL__", bridge_ws_url
                                ).replace(
                                    "__BRIDGE_PROJECT_ID__", str(project_id)
                                )

                                update_res = await client.put(
                                    f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                                    headers=headers,
                                    json={
                                        "message": f"🔄 Update Inspector Bridge to v{INSPECTOR_BRIDGE_VERSION}",
                                        "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                                        "sha": data["sha"],
                                        "branch": "main"
                                    },
                                    timeout=15.0
                                )

                                # اگر main نبود، master رو امتحان کن
                                if update_res.status_code == 404 or update_res.status_code == 422:
                                    update_res = await client.put(
                                        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                                        headers=headers,
                                        json={
                                            "message": f"🔄 Update Inspector Bridge to v{INSPECTOR_BRIDGE_VERSION}",
                                            "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                                            "sha": data["sha"],
                                            "branch": "master"
                                        },
                                        timeout=15.0
                                    )

                                if update_res.status_code in [200, 201]:
                                    slog.info(f"Bridge updated successfully at {path}")
                                    return {
                                        "success": True,
                                        "message": f"Bridge به نسخه {INSPECTOR_BRIDGE_VERSION} به‌روزرسانی شد",
                                        "file_path": path,
                                        "commit_url": update_res.json().get("commit", {}).get("html_url"),
                                        "version": INSPECTOR_BRIDGE_VERSION
                                    }
                                else:
                                    error_detail = update_res.json().get("message", "خطای ناشناخته")
                                    return {
                                        "success": False,
                                        "error": f"خطا در آپدیت فایل: {error_detail}",
                                        "file_path": path
                                    }
                except Exception as e:
                    slog.warning(f"Error checking {path}: {e}")
                    continue

            # 🔍 اگر InspectorBridge.tsx پیدا نشد، فایل‌های دیگر رو چک کن
            for path in other_paths:
                try:
                    res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                        headers=headers, timeout=10.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("encoding") == "base64":
                            content = base64.b64decode(data["content"]).decode('utf-8')
                            if any(marker in content for marker in bridge_markers):
                                # فایل bridge اینجاست - ولی نوع HTML/JS هست
                                # برای اینها از inject-bridge با force_update استفاده بشه
                                return {
                                    "success": False,
                                    "error": f"Bridge در فایل {path} است (نوع HTML/JS) - از دکمه «به‌روزرسانی» استفاده کنید",
                                    "file_path": path,
                                    "bridge_type": "html_or_js",
                                    "hint": "use_force_update"
                                }
                except:
                    continue

            return {
                "success": False,
                "error": "فایل Bridge در ریپو پیدا نشد",
                "searched_paths": bridge_paths + other_paths
            }

    except Exception as e:
        slog.error("Update bridge failed", exception=e)
        return {"success": False, "error": str(e)}


@router.post("/inspector/fix-all-bridges")
async def fix_all_bridges(
    db: Session = Depends(get_db)
):
    """
    🔧 اصلاح همه Bridge Script های قدیمی در همه پروژه‌ها

    این endpoint:
    1. تمام پروژه‌هایی که GitHub متصل دارند را پیدا می‌کند
    2. InspectorBridge.tsx آنها را بررسی می‌کند
    3. نسخه‌های قدیمی را به آخرین نسخه به‌روزرسانی می‌کند
    """
    from ...models.project import Project
    from ...models.setting import Setting
    import httpx
    import base64

    slog.api_request("POST", "/inspector/fix-all-bridges")

    try:
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            github_token = Setting.get_value(db, "api_key_github") or ""
        if not github_token:
            return {"success": False, "error": "توکن GitHub تنظیم نشده"}

        # دریافت همه پروژه‌ها
        projects = db.query(Project).all()
        results = []
        updated_count = 0
        skipped_count = 0
        error_count = 0

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        bridge_paths = [
            "src/app/InspectorBridge.tsx", "app/InspectorBridge.tsx",
            "frontend/src/app/InspectorBridge.tsx", "frontend/app/InspectorBridge.tsx",
        ]
        bridge_markers = ["Inspector Bridge Script", "InspectorBridge", "__inspectorBridgeLoaded"]

        async with httpx.AsyncClient() as client:
            for project in projects:
                github_path = getattr(project, 'github_path', None)
                if not github_path:
                    extra_data = getattr(project, 'extra_data', None)
                    if extra_data:
                        try:
                            extra = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                            github_path = extra.get('github_path') or extra.get('github_url')
                            if not github_path and extra.get('owner') and extra.get('repo'):
                                github_path = f"{extra['owner']}/{extra['repo']}"
                        except:
                            pass

                if not github_path:
                    continue

                github_path_clean = github_path.replace("https://github.com/", "").replace(".git", "").strip("/")
                parts = github_path_clean.split("/")
                if len(parts) < 2:
                    continue

                owner, repo = parts[0], parts[1]
                project_result = {
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "github": f"{owner}/{repo}"
                }

                found_bridge = False
                for path in bridge_paths:
                    try:
                        res = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                            headers=headers, timeout=10.0
                        )
                        if res.status_code == 200:
                            data = res.json()
                            if data.get("encoding") == "base64":
                                content = base64.b64decode(data["content"]).decode('utf-8')
                                if any(marker in content for marker in bridge_markers):
                                    found_bridge = True
                                    # چک نسخه
                                    import re as _re
                                    version_match = _re.search(r'// Version:\s*([\d.]+)', content)
                                    current_version = version_match.group(1) if version_match else "1.0"

                                    # چک مشکلات
                                    has_issues = (
                                        current_version != INSPECTOR_BRIDGE_VERSION or
                                        'shouldSend' not in content or
                                        'lastEventTime' not in content or
                                        ('declare global' not in content and path.endswith('.tsx')) or
                                        '" \\"" + text + "\\""' in content or
                                        '" "" + text + """' in content
                                    )

                                    if not has_issues:
                                        project_result["status"] = "up_to_date"
                                        project_result["version"] = current_version
                                        skipped_count += 1
                                    else:
                                        # آپدیت کن
                                        slog.info(f"Fixing bridge for {owner}/{repo} at {path} (v{current_version} → v{INSPECTOR_BRIDGE_VERSION})")

                                        import os as _os
                                        backend_url = _os.environ.get("BACKEND_URL", "").rstrip("/")
                                        if not backend_url:
                                            backend_url = _os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
                                        if not backend_url:
                                            render_app_name = _os.environ.get("RENDER_SERVICE_NAME", "")
                                            if render_app_name:
                                                backend_url = f"https://{render_app_name}.onrender.com"
                                        if not backend_url:
                                            backend_url = "http://localhost:8000"

                                        ws_base = backend_url.replace("https://", "wss://").replace("http://", "ws://")
                                        bridge_ws_url = f"{ws_base}/api/render/ws/bridge/{project.id}"

                                        new_content = INSPECTOR_BRIDGE_CLIENT_COMPONENT.replace(
                                            "__BRIDGE_WS_URL__", bridge_ws_url
                                        ).replace(
                                            "__BRIDGE_PROJECT_ID__", str(project.id)
                                        )

                                        update_res = await client.put(
                                            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                                            headers=headers,
                                            json={
                                                "message": f"🔄 Update Inspector Bridge to v{INSPECTOR_BRIDGE_VERSION}",
                                                "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                                                "sha": data["sha"],
                                                "branch": "main"
                                            },
                                            timeout=15.0
                                        )

                                        if update_res.status_code in [200, 201]:
                                            project_result["status"] = "updated"
                                            project_result["old_version"] = current_version
                                            project_result["new_version"] = INSPECTOR_BRIDGE_VERSION
                                            project_result["file_path"] = path
                                            updated_count += 1
                                            slog.info(f"✅ Bridge fixed for {owner}/{repo}")
                                        else:
                                            error_msg = update_res.json().get("message", "unknown")
                                            project_result["status"] = "error"
                                            project_result["error"] = error_msg
                                            error_count += 1
                                            slog.warning(f"❌ Failed to fix bridge for {owner}/{repo}: {error_msg}")
                                    break
                    except Exception as e:
                        continue

                if not found_bridge:
                    project_result["status"] = "no_bridge"

                if found_bridge or project_result.get("status") != "no_bridge":
                    results.append(project_result)

        return {
            "success": True,
            "message": f"بررسی تمام شد: {updated_count} آپدیت شد، {skipped_count} به‌روز بود، {error_count} خطا",
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total_with_bridge": updated_count + skipped_count + error_count,
            "details": results,
            "latest_version": INSPECTOR_BRIDGE_VERSION
        }

    except Exception as e:
        slog.error("Fix all bridges failed", exception=e)
        return {"success": False, "error": str(e)}


# =====================================
# 🆕 ایجاد هوشمند سرویس Render
# =====================================

async def _read_github_file(owner: str, repo: str, path: str, branch: str = "main", github_token: str = None) -> Optional[str]:
    """خواندن محتوای فایل از GitHub API (با پشتیبانی ریپوهای خصوصی)"""
    import aiohttp
    import base64 as _b64

    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
        headers["Accept"] = "application/vnd.github.v3+json"

    # روش ۱: GitHub API (کار میکنه برای private repos)
    if github_token:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("encoding") == "base64" and data.get("content"):
                            return _b64.b64decode(data["content"]).decode("utf-8")
                        elif data.get("download_url"):
                            async with session.get(data["download_url"], headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as dl_resp:
                                if dl_resp.status == 200:
                                    return await dl_resp.text()
        except:
            pass

    # روش ۲: raw.githubusercontent (فقط public repos)
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.text()
    except:
        pass

    return None


RENDER_SERVICE_AI_PROMPT = """تو یک DevOps Engineer هستی. وظیفه‌ات تحلیل ساختار یک پروژه GitHub و تولید تنظیمات دقیق برای ایجاد سرویس‌ها در Render.com هست.

## فایل‌های پروژه:
{files_content}

## اطلاعات پروژه:
- GitHub: {github_url}
- Branch: {branch}
- ساختار دایرکتوری: {dir_structure}

## وظیفه:
تحلیل کن و خروجی JSON بده. دقت کن:
1. اگر frontend/ و backend/ هر دو وجود دارند → دو سرویس جداگانه ایجاد کن
2. اگر پروژه Vite/CRA (بدون SSR) هست → نوع سرویس حتماً static_site باشه
3. اگر Next.js/Nuxt/Express/FastAPI هست → نوع web_service
4. برای static_site: فقط buildCommand و publishPath لازمه (startCommand نده یا null بذار)
5. برای static_site حتماً SPA rewrite rule رو به انتهای buildCommand اضافه کن: echo '/*    /index.html   200' > [publishPath]/_redirects
6. برای Python: حتماً pip install --upgrade pip setuptools && رو قبل از pip install بذار
7. برای Python: env var PYTHON_VERSION=3.11.11 اضافه کن
8. env vars مورد نیاز رو از .env/.env.example/.env.sample استخراج کن (فقط VITE_ و REACT_APP_ و NEXT_PUBLIC_ و SERVER-side vars)
9. اگر فرانت به بکند وصل میشه، VITE_API_URL یا معادلش رو با مقدار خالی اضافه کن (باید بعداً توسط کاربر پر بشه)
10. rootDir باید نسبت به root ریپو باشه (مثلاً frontend یا backend یا .)
11. اگر Dockerfile وجود داره، ترجیحاً از Docker استفاده کن (service_type=web_service, runtime=docker)
12. نام سرویس باید کوتاه و معنادار باشه (فقط حروف کوچک، اعداد و -)
13. 🔴 خیلی مهم: اگر در vite.config.ts/js مقدار base به یک URL خارجی (مثل https://storage.googleapis.com یا هر CDN دیگه) تنظیم شده، حتماً build command رو با --base=/ اجرا کن تا asset ها از خود سرور Render سرو بشن. مثال: npx vite build --base=/
14. 🔴 خیلی مهم: اگر پروژه قبلاً روی Google Cloud Run/Firebase/Vercel/Netlify دیپلوی بوده و config هایش به اون سرویس‌ها اشاره دارن (مثل base URL، CDN، bucket)، حتماً اونها رو برای Render override کن
15. برای Vite: همیشه از npx vite build --base=/ استفاده کن (مگر اینکه مطمئن باشی base تنظیم نشده)
16. همه env var هایی که به URL سرویس‌های خارجی اشاره دارن (مثل VITE_CDN_URL, VITE_STORAGE_URL) رو خالی بذار و در notes بنویس باید پر بشن

## فرمت خروجی (فقط JSON، بدون هیچ متن اضافه):
```json
{{
  "services": [
    {{
      "name": "project-name-frontend",
      "role": "frontend",
      "service_type": "static_site",
      "root_dir": "frontend",
      "build_command": "npm install && npx vite build --base=/ && echo '/*    /index.html   200' > dist/_redirects",
      "start_command": null,
      "publish_path": "dist",
      "env_vars": {{"VITE_API_URL": ""}},
      "notes": "Vite + React SPA - حتماً VITE_API_URL رو بعد از ایجاد بکند پر کنید"
    }}
  ],
  "analysis": "توضیح کوتاه فارسی از ساختار پروژه و تصمیمات گرفته شده"
}}
```"""


# فایل‌های کلیدی که AI باید بررسی کنه
_KEY_FILES_TO_READ = [
    "package.json",
    "frontend/package.json",
    "backend/package.json",
    "client/package.json",
    "server/package.json",
    "requirements.txt",
    "backend/requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "Dockerfile",
    "frontend/Dockerfile",
    "backend/Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "vite.config.ts",
    "vite.config.js",
    "frontend/vite.config.ts",
    "frontend/vite.config.js",
    "next.config.js",
    "next.config.mjs",
    "nuxt.config.ts",
    ".env",
    ".env.example",
    ".env.sample",
    "frontend/.env.example",
    "backend/.env.example",
    "render.yaml",
    "Procfile",
    "tsconfig.json",
    "frontend/tsconfig.json",
]


async def _ai_analyze_project(owner: str, repo: str, branch: str, github_token: str, github_url: str, project_id: str, db) -> dict:
    """
    تحلیل پروژه توسط AI — فایل‌های کلیدی رو از GitHub میخونه و به مدل میده
    Returns: { services: [...], analysis: "..." }
    """
    import aiohttp

    # ── 1. دریافت ساختار دایرکتوری از GitHub Tree API ──
    dir_structure = []
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
        headers["Accept"] = "application/vnd.github.v3+json"

    try:
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(tree_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    tree_data = await resp.json()
                    for item in tree_data.get("tree", [])[:500]:
                        dir_structure.append(item.get("path", ""))
    except Exception as e:
        slog.warning(f"Failed to get tree: {e}")

    # ── 2. خواندن فایل‌های کلیدی ──
    files_content_parts = []
    for file_path in _KEY_FILES_TO_READ:
        content = await _read_github_file(owner, repo, file_path, branch, github_token)
        if content:
            truncated = content[:3000] if len(content) > 3000 else content
            files_content_parts.append(f"### 📄 {file_path}\n```\n{truncated}\n```")

    if not files_content_parts:
        return {"services": [], "analysis": "هیچ فایل قابل شناسایی‌ای پیدا نشد. ریپو خالی است یا دسترسی وجود ندارد."}

    files_content = "\n\n".join(files_content_parts)
    dir_str = "\n".join(dir_structure[:200]) if dir_structure else "(ساختار دایرکتوری در دسترس نیست)"

    # ── 3. ساخت prompt نهایی ──
    prompt = RENDER_SERVICE_AI_PROMPT.format(
        files_content=files_content,
        github_url=github_url,
        branch=branch,
        dir_structure=dir_str,
    )

    # ── 4. فراخوانی مدل AI ──
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    ai_manager = get_ai_manager()
    primary_model = await _smart_select_model(db, project_id)

    messages = [
        Message(role="system", content="تو یک DevOps Engineer متخصص Render.com هستی. فقط خروجی JSON بده، بدون توضیح اضافه."),
        Message(role="user", content=prompt),
    ]

    try:
        response = await ai_manager.generate(
            model_id=primary_model,
            messages=messages,
            max_tokens=4096,
            temperature=0.2,
            allow_fallback=True,
        )
        ai_text = response.content
        model_used = response.model_id
    except Exception as e:
        slog.error("AI analysis failed", exception=e)
        return {"services": [], "analysis": f"خطا در تحلیل AI: {str(e)}"}

    # ── 5. پارس کردن خروجی JSON ──
    try:
        json_text = ai_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        result = json.loads(json_text.strip())
        if "services" not in result:
            result = {"services": [], "analysis": "خروجی AI فاقد بخش services بود"}
        result["model_used"] = model_used
        return result
    except (json.JSONDecodeError, IndexError) as e:
        slog.warning(f"Failed to parse AI JSON: {e}", ai_text=ai_text[:500])
        return {"services": [], "analysis": f"خطا در پارس خروجی AI. خروجی خام:\n{ai_text[:1000]}"}


@router.post("/inspector/create-render-service")
async def create_render_service(request: Request, db: Session = Depends(get_db)):
    """
    ایجاد هوشمند سرویس‌های Render با استفاده از تحلیل AI
    مدل AI ساختار پروژه رو تحلیل میکنه و تنظیمات دقیق سرویس‌ها رو تولید میکنه
    """
    try:
        data = await request.json()
        project_id = data.get("project_id")

        slog.api_request("POST", "/inspector/create-render-service", project_id=project_id)

        if not project_id:
            return {"success": False, "error": "شناسه پروژه الزامی است"}

        # ── 1. خواندن اطلاعات پروژه از DB ──
        from ...models.project import Project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # ── 2. استخراج GitHub info ──
        extra = {}
        if project.extra_data:
            try:
                extra = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
            except:
                extra = {}

        github_url = extra.get("source_url") or extra.get("clone_url") or ""
        owner = extra.get("owner", "")
        repo = extra.get("repo", "")

        if not github_url and project.github_path:
            parts = project.github_path.strip("/").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                github_url = f"https://github.com/{owner}/{repo}"

        if not owner or not repo:
            if github_url:
                cleaned = github_url.replace("https://github.com/", "").replace(".git", "").strip("/")
                parts = cleaned.split("/")
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]

        if not github_url or not owner or not repo:
            return {"success": False, "error": "آدرس GitHub پروژه یافت نشد."}

        branch = extra.get("branch", "main") or "main"

        # ── 3. دریافت توکن‌ها ──
        github_token = None
        try:
            from ...models.setting import Setting as _S
            gh_setting = db.query(_S).filter(_S.key == "api_key_github").first()
            if gh_setting and gh_setting.value:
                github_token = gh_setting.value
        except:
            pass
        if not github_token:
            github_token = os.getenv("GITHUB_TOKEN", "")

        # ── 4. تحلیل پروژه با AI ──
        ai_result = await _ai_analyze_project(
            owner=owner,
            repo=repo,
            branch=branch,
            github_token=github_token,
            github_url=github_url,
            project_id=project_id,
            db=db,
        )

        services_plan = ai_result.get("services", [])
        analysis_text = ai_result.get("analysis", "")
        model_used = ai_result.get("model_used", "unknown")

        if not services_plan:
            return {
                "success": False,
                "error": "AI نتوانست سرویسی برای این پروژه تشخیص دهد.",
                "analysis": analysis_text,
                "model_used": model_used,
            }

        # ── 5. دریافت Render API Key ──
        from ...models.setting import Setting
        setting = db.query(Setting).filter(Setting.key == "api_key_render").first()
        api_key = setting.value if setting else ""
        if not api_key:
            api_key = os.getenv("RENDER_API_KEY", "")
        if not api_key:
            return {"success": False, "error": "کلید API رندر تنظیم نشده."}

        # ── 6. ایجاد سرویس‌ها بر اساس تحلیل AI ──
        from ...services.deploy_service import RenderDeployService
        deploy_svc = RenderDeployService(api_key)
        created = []
        errors = []
        try:
            for svc_plan in services_plan:
                svc_name = svc_plan.get("name", "app")
                svc_type = svc_plan.get("service_type", "web_service")
                svc_env_vars = svc_plan.get("env_vars", {})

                result = await deploy_svc.create_service(
                    name=svc_name,
                    project_type=svc_plan.get("role", "app"),
                    github_repo_url=github_url,
                    github_branch=branch,
                    root_dir=svc_plan.get("root_dir", "."),
                    build_command=svc_plan.get("build_command"),
                    start_command=svc_plan.get("start_command"),
                    service_type=svc_type,
                    publish_path=svc_plan.get("publish_path"),
                    env_vars=svc_env_vars if svc_env_vars else None,
                )
                if result.get("success"):
                    try:
                        new_svc = RenderService(
                            id=result["service_id"],
                            name=result.get("name", svc_name),
                            type=svc_type,
                            status="deploying",
                            project_id=project_id,
                            service_url=result.get("url", ""),
                        )
                        db.merge(new_svc)
                        db.commit()
                    except Exception as db_err:
                        slog.warning(f"DB save failed: {db_err}")

                    created.append({
                        "name": result.get("name"),
                        "service_id": result.get("service_id"),
                        "role": svc_plan.get("role", "app"),
                        "service_type": svc_type,
                        "dashboard_url": result.get("dashboard_url"),
                        "url": result.get("url"),
                        "notes": svc_plan.get("notes", ""),
                    })
                    slog.info(f"✅ AI Created {svc_plan.get('role')} ({svc_type}): {result.get('name')}")
                else:
                    errors.append({
                        "name": svc_name,
                        "role": svc_plan.get("role", "app"),
                        "error": result.get("error", "unknown"),
                    })
                    slog.warning(f"❌ AI Failed {svc_plan.get('role')}: {result.get('error')}")
        finally:
            await deploy_svc.close()

        # ── 7. ساخت پیام خلاصه برای Inspector Chat ──
        empty_env_vars = []
        for svc in services_plan:
            for k, v in svc.get("env_vars", {}).items():
                if v == "" or v is None:
                    empty_env_vars.append(f"{svc.get('name', '?')}: {k}")

        return {
            "success": len(created) > 0,
            "created": created,
            "errors": errors,
            "analysis": analysis_text,
            "model_used": model_used,
            "project_name": project.name,
            "github_url": github_url,
            "empty_env_vars": empty_env_vars,
            "message": f"✅ {len(created)} سرویس ایجاد شد" + (f" | {len(errors)} خطا" if errors else ""),
        }

    except Exception as e:
        slog.error("AI create render service failed", exception=e)
        return {"success": False, "error": str(e)}



# =====================================
# 🌐 WebSocket Bridge Hub
# ارتباط بین Bridge Script داخل پروژه کاربر و Inspector Frontend
# این روش مشکل cross-origin postMessage را حل می‌کند
# =====================================

import asyncio
from collections import defaultdict
from typing import Set

# نگهداری اتصالات WebSocket به تفکیک project_id و نقش
_bridge_connections: dict = defaultdict(lambda: {"bridges": set(), "inspectors": set()})
_bridge_lock = asyncio.Lock()
# زمان آخرین فعالیت هر پروژه - برای پاکسازی اتصالات بیکار
_bridge_last_activity: dict = {}
_BRIDGE_IDLE_TIMEOUT = 3600  # 1 ساعت بیکاری → پاکسازی


async def _cleanup_idle_bridge_connections():
    """پاکسازی اتصالات WebSocket بیکار برای جلوگیری از memory leak"""
    now = datetime.utcnow()
    async with _bridge_lock:
        idle_projects = []
        for project_id, last_time in list(_bridge_last_activity.items()):
            if (now - last_time).total_seconds() > _BRIDGE_IDLE_TIMEOUT:
                idle_projects.append(project_id)

        for project_id in idle_projects:
            conns = _bridge_connections.get(project_id)
            if conns:
                # بستن اتصالات باقیمانده
                for ws in list(conns.get("bridges", set())):
                    try:
                        await ws.close()
                    except Exception:
                        pass
                for ws in list(conns.get("inspectors", set())):
                    try:
                        await ws.close()
                    except Exception:
                        pass
                del _bridge_connections[project_id]
            _bridge_last_activity.pop(project_id, None)
            slog.info(f"Bridge WS: Cleaned up idle connections for project {project_id}")


@router.websocket("/ws/bridge/{project_id}")
async def websocket_bridge_hub(websocket: WebSocket, project_id: str):
    """
    🌐 WebSocket Bridge Hub

    این endpoint واسط ارتباطی بین Bridge Script (داخل پروژه deploy شده)
    و Inspector Frontend است.

    Protocol:
    1. Client (bridge یا inspector) متصل می‌شود
    2. اولین پیام باید نقش را مشخص کند: {"type": "register", "role": "bridge"} یا {"type": "register", "role": "inspector"}
    3. پیام‌ها از bridge به همه inspector ها relay می‌شود
    4. پیام‌ها از inspector به همه bridge ها relay می‌شود (برای ارسال دستورات)
    5. هر طرف می‌تواند ping ارسال کند: {"type": "ping"}
    """
    await websocket.accept()
    client_id = str(uuid.uuid4())
    role = None

    slog.info("Bridge WS: New connection", project_id=project_id, client_id=client_id)

    try:
        # منتظر پیام register
        try:
            first_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        except asyncio.TimeoutError:
            await websocket.send_json({"type": "error", "message": "Timeout: register message required"})
            await websocket.close()
            return

        if first_msg.get("type") != "register" or first_msg.get("role") not in ("bridge", "inspector"):
            await websocket.send_json({"type": "error", "message": "First message must be: {type: 'register', role: 'bridge'|'inspector'}"})
            await websocket.close()
            return

        role = first_msg["role"]

        async with _bridge_lock:
            _bridge_connections[project_id][f"{role}s"].add(websocket)
            _bridge_last_activity[project_id] = datetime.utcnow()

        slog.info(f"Bridge WS: {role} registered",
            project_id=project_id,
            client_id=client_id,
            bridges=len(_bridge_connections[project_id]["bridges"]),
            inspectors=len(_bridge_connections[project_id]["inspectors"])
        )

        # اعلام اتصال موفق
        await websocket.send_json({
            "type": "registered",
            "role": role,
            "project_id": project_id,
            "client_id": client_id
        })

        # اطلاع‌رسانی به طرف مقابل
        other_role = "inspectors" if role == "bridge" else "bridges"
        notify_msg = {
            "type": "peer_connected",
            "peer_role": role,
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        async with _bridge_lock:
            for ws in list(_bridge_connections[project_id][other_role]):
                try:
                    await ws.send_json(notify_msg)
                except Exception:
                    _bridge_connections[project_id][other_role].discard(ws)

        # حلقه اصلی دریافت و relay پیام‌ها
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                # relay پیام به طرف مقابل
                target_set_name = "inspectors" if role == "bridge" else "bridges"
                data["_from"] = role
                data["_project_id"] = project_id
                data["_timestamp"] = datetime.utcnow().isoformat()
                _bridge_last_activity[project_id] = datetime.utcnow()

                async with _bridge_lock:
                    dead_connections = set()
                    for ws in list(_bridge_connections[project_id][target_set_name]):
                        try:
                            await ws.send_json(data)
                        except Exception:
                            dead_connections.add(ws)
                    # حذف اتصالات مرده
                    _bridge_connections[project_id][target_set_name] -= dead_connections

            except WebSocketDisconnect:
                break
            except Exception as e:
                slog.warning("Bridge WS: message error", client_id=client_id, exception=e)
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        slog.error("Bridge WS: connection error", client_id=client_id, exception=e)
    finally:
        # حذف اتصال
        if role:
            async with _bridge_lock:
                _bridge_connections[project_id][f"{role}s"].discard(websocket)
                # اطلاع‌رسانی قطع اتصال به طرف مقابل
                other_role = "inspectors" if role == "bridge" else "bridges"
                disconnect_msg = {
                    "type": "peer_disconnected",
                    "peer_role": role,
                    "project_id": project_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                for ws in list(_bridge_connections[project_id][other_role]):
                    try:
                        await ws.send_json(disconnect_msg)
                    except Exception:
                        _bridge_connections[project_id][other_role].discard(ws)

                # پاکسازی اگر هیچ اتصالی نمانده
                if not _bridge_connections[project_id]["bridges"] and not _bridge_connections[project_id]["inspectors"]:
                    del _bridge_connections[project_id]

        slog.info(f"Bridge WS: {role or 'unknown'} disconnected",
            project_id=project_id, client_id=client_id)


@router.get("/inspector/bridge-connections/{project_id}")
async def get_bridge_connections(project_id: str):
    """وضعیت اتصالات WebSocket Bridge برای یک پروژه"""
    conns = _bridge_connections.get(project_id, {"bridges": set(), "inspectors": set()})
    # پاکسازی اتصالات بیکار در هر فراخوانی
    await _cleanup_idle_bridge_connections()

    return {
        "success": True,
        "project_id": project_id,
        "bridges_connected": len(conns["bridges"]),
        "inspectors_connected": len(conns["inspectors"]),
        "is_active": len(conns["bridges"]) > 0 and len(conns["inspectors"]) > 0
    }


# ─────────────────────────────────────────────────────────────────────
# 📋 Inspector Session & Message Persistence
# ─────────────────────────────────────────────────────────────────────


@router.post("/inspector/session/create")
async def create_inspector_session(
    project_id: str = Query(..., description="ID پروژه که سشن بازرس برای آن ساخته می‌شود"),
    db: Session = Depends(get_db)
):
    """ایجاد سشن جدید بازرس هوشمند.

    🆕 (Phase 5 — bug 21) — `project_id` صریحاً `Query(...)` علامت‌گذاری شد.
    قبلاً به‌خاطر اینکه فقط `project_id: str` بود، FastAPI آن را به‌عنوان
    body field تفسیر می‌کرد و چون فرانت‌اند بدنه نمی‌فرستد (پارامتر در
    query string است)، درخواست با 422 رد می‌شد و در تب بازرس ویژه «سشن
    ایجاد نمی‌شد». خطا در try/except فرانت silent بود.
    """
    from ...models.inspector_session import InspectorSession

    # بررسی سشن فعال موجود
    active = db.query(InspectorSession).filter(
        InspectorSession.project_id == project_id,
        InspectorSession.status == "active"
    ).first()

    if active:
        return {"success": True, "session": active.to_dict(), "existing": True}

    session = InspectorSession(
        project_id=project_id,
        status="active",
        title=f"سشن بازرسی"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    slog.info("Inspector session created", project_id=project_id, session_id=session.id)
    return {"success": True, "session": session.to_dict(), "existing": False}


@router.get("/inspector/sessions/{project_id}")
async def list_inspector_sessions(
    project_id: str,
    status: str = None,
    db: Session = Depends(get_db)
):
    """لیست سشن‌های بازرس هوشمند (فعال + آرشیو)"""
    from ...models.inspector_session import InspectorSession

    query = db.query(InspectorSession).filter(InspectorSession.project_id == project_id)
    if status:
        query = query.filter(InspectorSession.status == status)
    sessions = query.order_by(InspectorSession.created_at.desc()).all()

    return {
        "success": True,
        "sessions": [s.to_dict() for s in sessions],
        "total": len(sessions)
    }


@router.get("/inspector/session/{session_id}/messages")
async def get_inspector_messages(
    session_id: int,
    db: Session = Depends(get_db)
):
    """دریافت پیام‌های یک سشن"""
    from ...models.inspector_session import InspectorSession, InspectorMessage

    session = db.query(InspectorSession).filter(InspectorSession.id == session_id).first()
    if not session:
        return {"success": False, "error": "سشن یافت نشد"}

    messages = db.query(InspectorMessage).filter(
        InspectorMessage.session_id == session_id
    ).order_by(InspectorMessage.timestamp.asc()).all()

    return {
        "success": True,
        "session": session.to_dict(),
        "messages": [m.to_dict() for m in messages]
    }


class SaveMessageRequest(BaseModel):
    session_id: int
    role: str  # user, assistant, system, action
    content: str
    action_type: str = None  # click, scroll, input, navigate, focus, hover
    model_id: str = None
    tokens_used: int = None
    extra_data: Optional[dict] = None  # visual_debug_packs, action_plan, is_visual_debug_report, enhanced_prompt, ...


@router.post("/inspector/session/message")
async def save_inspector_message(
    request: SaveMessageRequest,
    db: Session = Depends(get_db)
):
    """ذخیره پیام در سشن بازرس"""
    from ...models.inspector_session import InspectorSession, InspectorMessage

    session = db.query(InspectorSession).filter(InspectorSession.id == request.session_id).first()
    if not session:
        return {"success": False, "error": "سشن یافت نشد"}

    msg = InspectorMessage(
        session_id=request.session_id,
        role=request.role,
        content=request.content,
        action_type=request.action_type,
        model_id=request.model_id,
        tokens_used=request.tokens_used,
        backend_verified=None,  # pending
        extra_data=json.dumps(request.extra_data, ensure_ascii=False) if request.extra_data else None,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {"success": True, "message": msg.to_dict()}


@router.post("/inspector/session/{session_id}/archive")
async def archive_inspector_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """آرشیو کردن سشن بازرس و پاک کردن صفحه چت"""
    from ...models.inspector_session import InspectorSession
    from datetime import datetime

    session = db.query(InspectorSession).filter(InspectorSession.id == session_id).first()
    if not session:
        return {"success": False, "error": "سشن یافت نشد"}

    # شمارش پیام‌ها برای عنوان
    msg_count = len(session.messages) if session.messages else 0
    if not session.title or session.title == "سشن بازرسی":
        session.title = f"سشن بازرسی ({msg_count} پیام)"

    session.status = "archived"
    session.closed_at = datetime.utcnow()
    db.commit()

    slog.info("Inspector session archived", session_id=session_id, message_count=msg_count)
    return {"success": True, "message": "سشن آرشیو شد", "session": session.to_dict()}


class VerifyMessageBody(BaseModel):
    """بدنه اختیاری درخواست verify - شامل لاگ‌های کنسول بریدج"""
    console_logs: Optional[List[dict]] = None  # [{level, message, timestamp}]


@router.post("/inspector/message/{message_id}/verify")
async def verify_inspector_message(
    message_id: int,
    project_id: str,
    force: bool = False,
    body: Optional[VerifyMessageBody] = None,
    db: Session = Depends(get_db)
):
    """
    بررسی لاگ‌های بک‌اند برای یک اکشن و زدن تیک تأیید
    - لاگ‌ها بر اساس پنجره زمانی دقیق هر اکشن فیلتر می‌شوند
    - خطاهای کنسول مرورگر از خطاهای واقعی بک‌اند تفکیک می‌شوند
    - force=true: بررسی مجدد حتی اگر قبلاً بررسی شده
    - console_logs: لاگ‌های کنسول دریافت‌شده از Bridge (برای وقتی که Render logs نیست)
    """
    from ...models.inspector_session import InspectorMessage
    from ...models.render_log import RenderLog
    from datetime import datetime, timedelta
    from sqlalchemy import desc, asc

    msg = db.query(InspectorMessage).filter(InspectorMessage.id == message_id).first()
    if not msg:
        return {"success": False, "error": "پیام یافت نشد"}

    # اگر force=true و قبلاً "no-logs" بوده، مجدد بررسی کن
    if force and msg.backend_verified is not None and msg.verified_by_model == "no-logs":
        msg.backend_verified = None
        msg.backend_log_summary = None
        msg.verified_by_model = None
        msg.logs_checked = None
        msg.error_logs_count = None
        msg.checked_logs_data = None
        db.commit()

    # اگر قبلاً بررسی شده، نتیجه رو برگردون (با لاگ‌های ذخیره‌شده)
    if msg.backend_verified is not None:
        stored_logs = []
        if msg.checked_logs_data:
            try:
                stored_logs = json.loads(msg.checked_logs_data)
            except Exception:
                stored_logs = []
        return {
            "success": True,
            "message_id": message_id,
            "verified": msg.backend_verified,
            "summary": msg.backend_log_summary,
            "model_used": msg.verified_by_model,
            "logs_checked": msg.logs_checked or 0,
            "error_logs_count": msg.error_logs_count or 0,
            "checked_logs": stored_logs,
            "already_checked": True
        }

    try:
        # -------------------------------------------------------
        # 🔴 تشخیص نوع خطا: کنسول مرورگر vs بک‌اند
        # -------------------------------------------------------
        is_console_error = msg.action_type in ("error", "console-error")

        # اگر خطای کنسول مرورگر هست، خود محتوای پیام حاوی خطاست
        # لاگ بک‌اند لزوماً مرتبط نیست - ولی بررسی می‌کنیم
        # -------------------------------------------------------

        # پیدا کردن سرویس‌های مرتبط با این پروژه
        project_services = db.query(RenderService).filter(
            RenderService.project_id == project_id
        ).all()
        service_ids = [s.id for s in project_services]

        # ─── تشخیص خودکار سرویس اگر نگاشت مستقیم نبود ───
        if not service_ids:
            from ...models.project import Project as _VerifyProject
            _proj = db.query(_VerifyProject).filter(_VerifyProject.id == project_id).first()
            if _proj:
                # استخراج نام ریپو از github_path
                _repo_name = ""
                _gpath = _proj.github_path or ""
                if "/" in _gpath:
                    _repo_name = _gpath.split("/", 1)[1].lower().strip()
                _proj_name = (_proj.name or "").lower().strip()

                # جستجو در همه سرویس‌ها
                if _repo_name or _proj_name:
                    all_services = db.query(RenderService).all()
                    for svc in all_services:
                        svc_name = (svc.name or "").lower()
                        # تطبیق نام: ریپو یا پروژه در نام سرویس موجود باشه
                        if (_repo_name and _repo_name in svc_name) or \
                           (_proj_name and _proj_name in svc_name) or \
                           (_repo_name and svc_name in _repo_name):
                            service_ids.append(svc.id)
                            # نگاشت خودکار برای دفعات بعد
                            svc.project_id = project_id
                    if service_ids:
                        try:
                            db.commit()
                            slog.info(f"[verify] نگاشت خودکار {len(service_ids)} سرویس به پروژه {project_id}")
                        except Exception:
                            db.rollback()

        if not service_ids:
            # 📦 حتی بدون سرویس Render، لاگ‌های بریدج رو بررسی کن
            bridge_logs = (body.console_logs if body and body.console_logs else []) or []
            bridge_error_count = sum(1 for bl in bridge_logs if bl.get('level', '').lower() in ('error', 'warn'))
            bridge_total = len(bridge_logs)
            bridge_checked = [{
                "level": bl.get("level", "log"),
                "message": (bl.get("message", ""))[:200],
                "timestamp": None,
                "service_id": "bridge-console",
            } for bl in bridge_logs[:30]]

            if is_console_error:
                _summary = f"خطای کنسول مرورگر + {bridge_total} لاگ بریدج" if bridge_total else "خطای کنسول مرورگر (سرویس بک‌اندی متصل نیست)"
                msg.backend_verified = False
                msg.backend_log_summary = _summary
                msg.verified_by_model = "console-error"
                msg.logs_checked = bridge_total
                msg.error_logs_count = bridge_error_count + 1
                if bridge_checked:
                    msg.checked_logs_data = json.dumps(bridge_checked, ensure_ascii=False)
            elif bridge_total > 0 and bridge_error_count > 0:
                _summary = f"⚠️ {bridge_error_count} خطا/هشدار در کنسول مرورگر"
                msg.backend_verified = False
                msg.backend_log_summary = _summary
                msg.verified_by_model = "bridge-console"
                msg.logs_checked = bridge_total
                msg.error_logs_count = bridge_error_count
                msg.checked_logs_data = json.dumps(bridge_checked, ensure_ascii=False)
            elif bridge_total > 0:
                _summary = f"سالم - {bridge_total} لاگ کنسول بررسی شد"
                msg.backend_verified = True
                msg.backend_log_summary = _summary
                msg.verified_by_model = "bridge-console"
                msg.logs_checked = bridge_total
                msg.error_logs_count = 0
                msg.checked_logs_data = json.dumps(bridge_checked, ensure_ascii=False)
            else:
                _summary = "سرویسی برای این پروژه یافت نشد"
                msg.backend_verified = True
                msg.backend_log_summary = _summary
                msg.verified_by_model = "no-services"
                msg.logs_checked = 0
                msg.error_logs_count = 0

            db.commit()
            return {
                "success": True, "message_id": message_id,
                "verified": msg.backend_verified,
                "summary": msg.backend_log_summary,
                "model_used": msg.verified_by_model,
                "logs_checked": msg.logs_checked or 0,
                "error_logs_count": msg.error_logs_count or 0,
                "checked_logs": bridge_checked
            }

        # -------------------------------------------------------
        # 📐 پنجره زمانی دقیق: از زمان این اکشن تا اکشن بعدی
        # -------------------------------------------------------
        msg_time = msg.timestamp
        if not msg_time:
            msg_time = datetime.utcnow() - timedelta(seconds=10)

        # پیام بعدی در همین سشن (برای مشخص کردن انتهای پنجره)
        next_msg = db.query(InspectorMessage).filter(
            InspectorMessage.session_id == msg.session_id,
            InspectorMessage.id > msg.id,
            InspectorMessage.role == 'action'
        ).order_by(asc(InspectorMessage.id)).first()

        # شروع پنجره: 2 ثانیه قبل از اکشن (بافر برای تاخیر شبکه)
        window_start = msg_time - timedelta(seconds=2)
        # پایان پنجره: تا اکشن بعدی، یا حداکثر 15 ثانیه بعد از اکشن
        if next_msg and next_msg.timestamp:
            window_end = next_msg.timestamp
        else:
            window_end = msg_time + timedelta(seconds=15)

        # لاگ‌های این پنجره زمانی دقیق
        action_logs = db.query(RenderLog).filter(
            RenderLog.timestamp >= window_start,
            RenderLog.timestamp <= window_end,
            RenderLog.service_id.in_(service_ids)
        ).order_by(asc(RenderLog.timestamp)).limit(50).all()

        logs_text = ""
        error_logs = []
        checked_logs_list = []
        for log in action_logs:
            log_line = f"[{log.level}] {log.message}"
            logs_text += log_line + "\n"
            checked_logs_list.append({
                "level": log.level or "info",
                "message": (log.message or "")[:200],
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "service_id": log.service_id,
            })
            if log.level and log.level.upper() in ("ERROR", "CRITICAL", "FATAL"):
                error_logs.append(log_line)

        # -------------------------------------------------------
        # 🔴 پیام‌های console-error: خطا قطعی هست (از مرورگر اومده)
        # لاگ بک‌اند رو هم نشون میدیم ولی وضعیت خطا از خود console-error میاد
        # -------------------------------------------------------
        if is_console_error:
            _ce_summary = f"خطای کنسول مرورگر: {msg.content}"
            if error_logs:
                _ce_summary += f" + {len(error_logs)} خطای بک‌اند"
            elif action_logs:
                _ce_summary += f" (بک‌اند سالم - {len(action_logs)} لاگ)"
            else:
                _ce_summary += " (بدون لاگ بک‌اند)"

            msg.backend_verified = False  # خطای کنسول همیشه خطاست
            msg.backend_log_summary = _ce_summary
            msg.verified_by_model = "console-error"
            msg.logs_checked = len(action_logs)
            msg.error_logs_count = len(error_logs) + 1  # +1 برای خود خطای کنسول
            msg.checked_logs_data = json.dumps(checked_logs_list, ensure_ascii=False) if checked_logs_list else None
            db.commit()
            return {
                "success": True,
                "message_id": message_id,
                "verified": False,
                "summary": _ce_summary,
                "model_used": "console-error",
                "logs_checked": len(action_logs),
                "error_logs_count": len(error_logs) + 1,
                "checked_logs": checked_logs_list
            }

        # -------------------------------------------------------
        # ✅ اکشن عادی (کلیک، اسکرول، ...): فقط لاگ بک‌اند مهمه
        # -------------------------------------------------------
        if len(action_logs) == 0:
            # 📦 اگر لاگ Render نیست، لاگ‌های کنسول Bridge رو بررسی کن
            bridge_logs = (body.console_logs if body and body.console_logs else []) or []
            bridge_error_count = sum(1 for bl in bridge_logs if bl.get('level', '').lower() in ('error', 'warn'))
            bridge_total = len(bridge_logs)

            if bridge_total > 0:
                # لاگ‌های بریدج رو به checked_logs اضافه کن
                bridge_checked = [{
                    "level": bl.get("level", "log"),
                    "message": (bl.get("message", ""))[:200],
                    "timestamp": None,
                    "service_id": "bridge-console",
                } for bl in bridge_logs[:30]]

                if bridge_error_count > 0:
                    _summary = f"⚠️ {bridge_error_count} خطا/هشدار در کنسول مرورگر (از {bridge_total} لاگ)"
                    msg.backend_verified = False
                    msg.backend_log_summary = _summary
                    msg.verified_by_model = "bridge-console"
                    msg.logs_checked = bridge_total
                    msg.error_logs_count = bridge_error_count
                    msg.checked_logs_data = json.dumps(bridge_checked, ensure_ascii=False)
                    db.commit()
                    return {
                        "success": True, "message_id": message_id,
                        "verified": False, "summary": _summary,
                        "model_used": "bridge-console",
                        "logs_checked": bridge_total,
                        "error_logs_count": bridge_error_count,
                        "checked_logs": bridge_checked
                    }
                else:
                    _summary = f"سالم - {bridge_total} لاگ کنسول بررسی شد (بدون خطا)"
                    msg.backend_verified = True
                    msg.backend_log_summary = _summary
                    msg.verified_by_model = "bridge-console"
                    msg.logs_checked = bridge_total
                    msg.error_logs_count = 0
                    msg.checked_logs_data = json.dumps(bridge_checked, ensure_ascii=False)
                    db.commit()
                    return {
                        "success": True, "message_id": message_id,
                        "verified": True, "summary": _summary,
                        "model_used": "bridge-console",
                        "logs_checked": bridge_total,
                        "error_logs_count": 0,
                        "checked_logs": bridge_checked
                    }
            else:
                _no_log_summary = f"بدون لاگ - منتظر دریافت ({len(service_ids)} سرویس)"
                msg.backend_verified = None  # None = pending, نه True
                msg.backend_log_summary = _no_log_summary
                msg.verified_by_model = "no-logs"
                msg.logs_checked = 0
                msg.error_logs_count = 0
                db.commit()
                return {
                    "success": True, "message_id": message_id,
                    "verified": None, "summary": _no_log_summary,
                    "model_used": "no-logs",
                    "logs_checked": 0, "error_logs_count": 0,
                    "checked_logs": [],
                    "pending": True
                }

        # اگر خطایی در لاگ‌ها نبود، مستقیم تأیید کن (بدون AI)
        if not error_logs:
            _ok_summary = f"سالم - {len(action_logs)} لاگ بررسی شد"
            msg.backend_verified = True
            msg.backend_log_summary = _ok_summary
            msg.verified_by_model = "rule-based"
            msg.logs_checked = len(action_logs)
            msg.error_logs_count = 0
            msg.checked_logs_data = json.dumps(checked_logs_list, ensure_ascii=False) if checked_logs_list else None
            db.commit()
            return {
                "success": True,
                "message_id": message_id,
                "verified": True,
                "summary": _ok_summary,
                "model_used": "rule-based",
                "logs_checked": len(action_logs),
                "error_logs_count": 0,
                "checked_logs": checked_logs_list
            }

        # -------------------------------------------------------
        # 🤖 فقط وقتی خطایی در لاگ‌ها هست، AI بررسی کنه
        # -------------------------------------------------------
        from ...services.ai_manager import get_ai_manager
        from ...services.ai_base import Message

        ai_manager = get_ai_manager()

        verify_prompt = f"""شما بازرس لاگ هستید. لاگ‌های بک‌اند مربوط به یک اکشن خاص را بررسی کنید.

اکشن کاربر: {msg.content}
زمان اکشن: {msg_time.isoformat()}

لاگ‌های بک‌اند مرتبط ({len(action_logs)} لاگ، {len(error_logs)} خطا):
{logs_text}

وظیفه شما:
1. آیا خطاهای موجود واقعاً مربوط به این اکشن هستند؟
2. اگر خطا مرتبط است، مختصر توضیح دهید.
3. اگر خطا مرتبط نیست (مثلاً خطای عمومی یا تکراری)، بنویسید "سالم"

پاسخ خود را دقیقاً در یکی از این فرمت‌ها بدهید:
OK: سالم
یا
ERROR: [توضیح مختصر خطا]"""

        messages = [
            Message(role="system", content="شما یک بازرس لاگ هستید. فقط وضعیت را گزارش کنید. پاسخ کوتاه و مختصر."),
            Message(role="user", content=verify_prompt)
        ]

        # استفاده از سریع‌ترین مدل موجود
        available = ai_manager.get_available_models()
        available_ids = [m.id for m in available]
        fast_model = None
        for preferred in ["gemini-2.0-flash", "gemini-1.5-flash", "gpt-4o-mini", "claude-3-haiku"]:
            if preferred in available_ids:
                fast_model = preferred
                break
        if not fast_model and available_ids:
            fast_model = available_ids[0]

        if not fast_model:
            # اگر مدلی موجود نیست، فقط بر اساس لاگ‌ها بررسی کن
            msg.backend_verified = False
            msg.backend_log_summary = f"خطا در لاگ بک‌اند: {error_logs[0][:100]}"
            msg.verified_by_model = "rule-based"
            msg.logs_checked = len(action_logs)
            msg.error_logs_count = len(error_logs)
            msg.checked_logs_data = json.dumps(checked_logs_list, ensure_ascii=False) if checked_logs_list else None
            db.commit()
            return {
                "success": True,
                "message_id": message_id,
                "verified": False,
                "summary": msg.backend_log_summary,
                "model_used": "rule-based",
                "logs_checked": len(action_logs),
                "error_logs_count": len(error_logs),
                "checked_logs": checked_logs_list
            }

        response = await ai_manager.generate(
            model_id=fast_model,
            messages=messages,
            max_tokens=150,
            temperature=0.1
        )

        ai_result = response.content.strip() if response and response.content else ""

        if ai_result.startswith("OK:") or "سالم" in ai_result:
            msg.backend_verified = True
            msg.backend_log_summary = ai_result.replace("OK:", "").strip()
        elif ai_result.startswith("ERROR:") or "خطا" in ai_result:
            msg.backend_verified = False
            msg.backend_log_summary = ai_result.replace("ERROR:", "").strip()
        else:
            # اگر فرمت نامشخص بود، خطا فرض کن (چون error_logs وجود داره)
            msg.backend_verified = False
            msg.backend_log_summary = ai_result or f"خطا: {error_logs[0][:100]}"

        msg.verified_by_model = fast_model
        msg.logs_checked = len(action_logs)
        msg.error_logs_count = len(error_logs)
        msg.checked_logs_data = json.dumps(checked_logs_list, ensure_ascii=False) if checked_logs_list else None
        db.commit()

        return {
            "success": True,
            "message_id": message_id,
            "verified": msg.backend_verified,
            "summary": msg.backend_log_summary,
            "model_used": fast_model,
            "logs_checked": len(action_logs),
            "error_logs_count": len(error_logs),
            "checked_logs": checked_logs_list
        }

    except Exception as e:
        slog.error("Verify inspector message failed", exception=e, message_id=message_id)
        _err_model = "error-fallback"
        try:
            msg.backend_verified = True
            msg.backend_log_summary = "سالم (خطای سیستم بررسی)"
            msg.verified_by_model = _err_model
            msg.logs_checked = 0
            msg.error_logs_count = 0
            db.commit()
        except Exception:
            pass
        return {
            "success": True,
            "message_id": message_id,
            "verified": msg.backend_verified,
            "summary": msg.backend_log_summary,
            "model_used": _err_model,
            "logs_checked": 0,
            "error_logs_count": 0,
            "checked_logs": []
        }


# =====================================================
# 📋 Inspector: Prompt Field Management (دستورات، حافظه، آموزش)
# =====================================================

class PromptFieldCreate(BaseModel):
    project_id: str
    category: str  # instruction, memory, training
    title: str
    content: str
    priority: int = 0
    is_active: bool = True

class PromptFieldUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    category: Optional[str] = None

class PromptFieldReorder(BaseModel):
    project_id: str
    field_ids: List[str]  # ترتیب جدید (اولین = بالاترین اولویت)

class PromptFieldTestRequest(BaseModel):
    field_id: str
    model_id: str = "gemini-2.0-flash"
    test_scenario: Optional[str] = None  # سناریوی تست سفارشی


# 🔔 ذخیره اتصالات WebSocket بازرس برای broadcast هایلایت
_prompt_field_highlight_connections: dict = defaultdict(set)


@router.get("/inspector/general-instructions/{project_id}")
async def get_general_instructions(project_id: str, db: Session = Depends(get_db)):
    """دستورات عمومی سیستم که همیشه در پرامپت مدل‌ها فعال هستند — از منبع واحد"""
    from ...models.project import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    # 🆕 از منبع حقیقت واحد استفاده میکنه — هر تغییری اونجا بدی اینجا هم منعکس میشه
    instructions = _build_general_instructions_list(
        project_name=project.name or "نامشخص",
        technologies=project.technologies or "نامشخص",
        github_path=f"{owner}/{repo}" if owner else "نامشخص"
    )

    return {"success": True, "instructions": instructions}


@router.get("/inspector/visual-debug-prompt/{project_id}")
async def get_visual_debug_prompt(project_id: str, db: Session = Depends(get_db)):
    """پرامپت بازرس بصری — از منبع واحد. فرانت بدون نیاز به آپدیت جداگانه خودکار دریافت میکنه."""
    from ...models.project import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    vd_instructions = _build_visual_debug_prompt_list()
    general_instructions = _build_general_instructions_list(
        project_name=project.name or "نامشخص",
        technologies=project.technologies or "نامشخص",
        github_path=f"{owner}/{repo}" if owner else "نامشخص"
    )

    return {
        "success": True,
        "visual_debug_instructions": vd_instructions,
        "general_instructions": general_instructions
    }


# ─────────────────────────────────────────────────────────────────────────────
# 🔗 Bug C7 — Bridge Phase 3: Inspector ↔ Oversight task loading
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/inspector/load-task/{task_id}")
async def inspector_load_task(task_id: str, db: Session = Depends(get_db)):
    """بارگذاری یک تسک مرکز نظارت در صفحهٔ inspector با کانتکست کامل.

    خروجی JSON شامل:
      - task: کل OversightTask.to_dict()
      - project_id: شناسهٔ inspector project مرتبط (برای navigate)
      - inspector_context: محتوای فایل context (در صورت موجود بودن inspector_context_id)
      - verify_history: ۵ report آخر این تسک
      - remaining_parts / done_parts: از آخرین report
      - target_files, acceptance_criteria, task_steps: از خود تسک
      - scan_metadata: created_by_scan_metadata

    خطاها:
      - 404: تسک پیدا نشد
      - 200 با inspector_context=None: تسک از scan آمده، نه از inspector
    """
    from fastapi import HTTPException
    from ...services.oversight_service import get_oversight_service
    from ...models.project import Project as _Proj_lt

    svc = get_oversight_service()
    task = next((t for t in svc.tasks if t.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    watched = svc._find_watched(task.watched_id) if task.watched_id else None

    # یافتن project_id inspector مرتبط (با match روی github_path یا extra_data)
    project_id: Optional[str] = None
    if watched and watched.repo_full_name:
        target = (watched.repo_full_name or "").lower()
        all_projects = db.query(_Proj_lt).all()
        for p in all_projects:
            if (p.github_path or "").lower() == target:
                project_id = p.id
                break
            try:
                ed = p.extra_data
                if isinstance(ed, str):
                    ed = json.loads(ed)
                if isinstance(ed, dict):
                    _o = (ed.get("owner") or "").lower()
                    _r = (ed.get("repo") or "").lower()
                    if _o and _r and f"{_o}/{_r}" == target:
                        project_id = p.id
                        break
            except Exception:
                continue

    # inspector_context (best-effort از فایل ذخیره‌شده)
    inspector_context: Optional[Dict[str, Any]] = None
    ctx_id = getattr(task, "inspector_context_id", None)
    if ctx_id:
        try:
            from ...services.oversight_inspector_bridge import (
                read_inspector_context as _read_ctx,
            )
            inspector_context = _read_ctx(ctx_id)
        except Exception as _ce:
            logger.debug(f"inspector_context load failed: {_ce}")

    # verify_history — آخرین ۵ report
    verify_history: List[Dict[str, Any]] = []
    for r in svc.reports:
        if r.task_id == task_id:
            verify_history.append(r.to_dict())
            if len(verify_history) >= 5:
                break

    # آخرین report برای remaining/done
    last_report = next((r for r in svc.reports if r.task_id == task_id), None)
    remaining_parts: List[Any] = []
    done_parts: List[Any] = []
    if last_report:
        remaining_parts = list(getattr(last_report, "remaining_parts", []) or [])
        done_parts = list(getattr(last_report, "done_parts", []) or [])

    return {
        "task": task.to_dict(),
        "project_id": project_id,
        "inspector_context": inspector_context,
        "verify_history": verify_history,
        "remaining_parts": remaining_parts,
        "done_parts": done_parts,
        "target_files": list(getattr(task, "target_files", []) or []),
        "acceptance_criteria": list(
            getattr(task, "acceptance_criteria", []) or []
        ),
        "task_steps": list(getattr(task, "task_steps", []) or []),
        "scan_metadata": getattr(task, "created_by_scan_metadata", None) or {},
    }


@router.get("/inspector/project-tasks/{project_id}")
async def inspector_project_tasks(project_id: str, db: Session = Depends(get_db)):
    """لیست تسک‌های مرکز نظارت برای یک inspector project (برای panel).

    این endpoint جایگزین panel «۵۱ فیلد» در صفحهٔ inspector است.
    تسک‌های watched مرتبط با همین project را برمی‌گرداند.
    """
    from ...services.oversight_service import get_oversight_service
    from ...models.project import Project as _Proj_pt

    svc = get_oversight_service()
    project = db.query(_Proj_pt).filter(_Proj_pt.id == project_id).first()
    if not project:
        return {"tasks": [], "watched_id": None, "project_id": project_id}

    # github_path یا extra_data → watched_id
    target_path = (project.github_path or "").lower()
    if not target_path and project.extra_data:
        try:
            ed = project.extra_data
            if isinstance(ed, str):
                ed = json.loads(ed)
            if isinstance(ed, dict):
                _o = (ed.get("owner") or "").lower()
                _r = (ed.get("repo") or "").lower()
                if _o and _r:
                    target_path = f"{_o}/{_r}"
        except Exception:
            pass

    matching_watched_id: Optional[str] = None
    for w in svc.watched:
        if (w.repo_full_name or "").lower() == target_path:
            matching_watched_id = w.id
            break

    if not matching_watched_id:
        return {"tasks": [], "watched_id": None, "project_id": project_id}

    # تسک‌های فعال این watched (نه archive، نه done مگر کاربر بخواهد)
    active_tasks: List[Dict[str, Any]] = []
    for t in svc.tasks:
        if t.watched_id != matching_watched_id:
            continue
        if getattr(t, "archived", False):
            continue
        active_tasks.append(t.to_dict())

    return {
        "tasks": active_tasks,
        "watched_id": matching_watched_id,
        "project_id": project_id,
        "count": len(active_tasks),
    }


@router.get("/inspector/prompt-fields/{project_id}")
async def get_prompt_fields(
    project_id: str,
    category: Optional[str] = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    """دریافت همه فیلدهای دستورات/حافظه/آموزش پروژه.

    🆕 (C7v2 Section 1) — به‌صورت پیش‌فرض فیلدهای archived=true حذف می‌شوند.
    برای دیدن آرشیو، include_archived=true را پاس کنید.
    """
    from ...models.inspector_prompt_field import InspectorPromptField

    query = db.query(InspectorPromptField).filter(
        InspectorPromptField.project_id == project_id
    )
    if category:
        query = query.filter(InspectorPromptField.category == category)

    if not include_archived:
        # فیلدهای archived=true را حذف کن (پیش‌فرض). نکته: ستون archived
        # ممکن است در DBهای قدیمی NULL باشد — هر دو NULL و false را قبول
        # کنیم.
        from sqlalchemy import or_
        query = query.filter(
            or_(
                InspectorPromptField.archived.is_(None),
                InspectorPromptField.archived == False,  # noqa: E712
            )
        )

    fields = query.order_by(InspectorPromptField.priority.desc(), InspectorPromptField.created_at).all()
    return {
        "success": True,
        "fields": [f.to_dict() for f in fields],
        "total": len(fields)
    }


@router.post("/inspector/prompt-fields/archive-all-instructions/{project_id}")
async def archive_all_instructions(project_id: str, db: Session = Depends(get_db)):
    """🆕 (C7v2 Section 1) Archive کردن همهٔ فیلدهای instruction پروژه.

    این endpoint idempotent است — اگر دوباره صدا زده شود، فیلدهایی که
    قبلاً archived شده‌اند را دست نمی‌زند. خروجی شامل تعداد فیلدهای
    تبدیل‌شده در این فراخوانی است.
    """
    from ...models.inspector_prompt_field import InspectorPromptField
    from sqlalchemy import or_

    affected = (
        db.query(InspectorPromptField)
        .filter(
            InspectorPromptField.project_id == project_id,
            InspectorPromptField.category == "instruction",
            or_(
                InspectorPromptField.archived.is_(None),
                InspectorPromptField.archived == False,  # noqa: E712
            ),
        )
        .all()
    )
    count = len(affected)
    for f in affected:
        f.archived = True
    if count > 0:
        db.commit()
    logger.info(
        f"archive_all_instructions(project={project_id}): "
        f"{count} instruction field(s) archived"
    )
    return {"success": True, "archived_count": count, "project_id": project_id}


@router.post("/inspector/prompt-fields/archive-all-instructions-everywhere")
async def archive_all_instructions_everywhere(db: Session = Depends(get_db)):
    """🆕 (C7v2 Section 1) Bulk archive برای تمام projects.

    یک‌بار پس از deploy این تغییرات اجرا می‌شود (همچنین در on-startup hook
    خودکار صدا زده می‌شود). idempotent است.
    """
    from ...models.inspector_prompt_field import InspectorPromptField
    from sqlalchemy import or_

    affected = (
        db.query(InspectorPromptField)
        .filter(
            InspectorPromptField.category == "instruction",
            or_(
                InspectorPromptField.archived.is_(None),
                InspectorPromptField.archived == False,  # noqa: E712
            ),
        )
        .all()
    )
    count = len(affected)
    for f in affected:
        f.archived = True
    if count > 0:
        db.commit()
    logger.info(
        f"archive_all_instructions_everywhere: {count} instruction field(s) archived across all projects"
    )
    return {"success": True, "archived_count": count}


class TrainingImpactTestRequest(BaseModel):
    """🆕 (C7v2 Section 3) درخواست سنجش اثر memory + training."""
    prompt: str
    model_id: Optional[str] = None


@router.post("/inspector/seed-memory-training/{project_id}")
async def seed_memory_training(project_id: str, db: Session = Depends(get_db)):
    """🆕 (C7v3/Addendum v5 §1.4) فراخوانی دستی sync + review برای یک inspector project.

    این endpoint برای کاربری که می‌خواهد بدون منتظر ماندن برای scan/verify
    دوره‌ای، فیلدهای memory/training را بلافاصله پر کند. کاربردی برای
    bootstrap پروژه‌های تازه.

    عملیات:
      1) project_id را به watched_id resolve می‌کند
      2) sync_to_inspector_memory_training صدا زده می‌شود
      3) review_auto_synced_fields صدا زده می‌شود
      4) آمار را به همراه فیلدهای جدید برمی‌گرداند

    خطاها:
      - 404: project پیدا نشد یا به watched متصل نیست
    """
    from ...models.project import Project as _Proj_seed
    from ...services.oversight_service import get_oversight_service

    project = db.query(_Proj_seed).filter(_Proj_seed.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    svc = get_oversight_service()
    # یافتن watched متناظر (همان منطق resolver)
    target = (project.github_path or "").lower()
    if not target and project.extra_data:
        try:
            ed = project.extra_data
            if isinstance(ed, str):
                ed = json.loads(ed)
            if isinstance(ed, dict):
                _o = (ed.get("owner") or "").lower()
                _r = (ed.get("repo") or "").lower()
                if _o and _r:
                    target = f"{_o}/{_r}"
        except Exception:
            pass

    watched_id: Optional[str] = None
    for w in svc.watched:
        if (w.repo_full_name or "").lower() == target:
            watched_id = w.id
            break

    if not watched_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "این inspector project به هیچ watched ای در مرکز نظارت متصل نیست. "
                "ابتدا پروژه را در /oversight به نظارت اضافه کنید."
            ),
        )

    sync_result = await svc.sync_to_inspector_memory_training(watched_id)
    review_result = await svc.review_auto_synced_fields(watched_id)

    return {
        "success": True,
        "project_id": project_id,
        "watched_id": watched_id,
        "sync": sync_result,
        "review": review_result,
        "message": (
            f"✨ سینک کامل شد: {sync_result.get('created_memory_count', 0)} memory جدید + "
            f"{sync_result.get('created_training_count', 0)} training جدید + "
            f"{review_result.get('strengthened_count', 0)} تقویت + "
            f"{review_result.get('archived_count', 0)} archive"
        ),
    }


@router.post("/inspector/training-impact-test/{project_id}")
async def training_impact_test(
    project_id: str,
    request: TrainingImpactTestRequest,
    db: Session = Depends(get_db),
):
    """🆕 (C7v2 Section 3) سنجش اثر فیلدهای memory + training بر خروجی مدل.

    دو بار prompt یکسان را به مدل می‌فرستد:
      A) فقط با دستورات عمومی سیستم (بدون memory/training)
      B) با memory + training کامل
    سپس خروجی‌ها را مقایسه می‌کند و گزارش متنی می‌دهد.

    خروجی: dict شامل output_a, output_b, comparison.
    """
    from ...models.project import Project
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}
    owner = extra_data.get("owner", "") or ""
    repo = extra_data.get("repo", "") or ""

    # General instructions (پایه)
    gi_list = _build_general_instructions_list(
        project.name or "نامشخص",
        project.technologies or "نامشخص",
        f"{owner}/{repo}" if owner and repo else "نامشخص",
    )
    base_sys = _build_general_instructions_text(gi_list)

    # Memory + Training blocks
    mem_block, mem_count = _build_memory_block(project_id, db)
    train_block, train_count = _build_training_block(project_id, db)

    # System prompt A: فقط general
    sys_a = base_sys
    # System prompt B: memory + training + general
    sys_b = base_sys
    if train_block:
        sys_b = train_block + "\n\n" + sys_b
    if mem_block:
        sys_b = mem_block + "\n\n" + sys_b

    # انتخاب مدل
    mid = request.model_id or "gpt-4o-mini"

    ai = get_ai_manager()

    try:
        resp_a = await ai.generate(
            model_id=mid,
            messages=[
                Message(role="system", content=sys_a),
                Message(role="user", content=request.prompt),
            ],
            max_tokens=800,
            temperature=0.3,
        )
        text_a = (resp_a.content or "").strip() if hasattr(resp_a, "content") else str(resp_a or "")
    except Exception as e:
        text_a = f"[خطا در فراخوانی A: {e}]"

    try:
        resp_b = await ai.generate(
            model_id=mid,
            messages=[
                Message(role="system", content=sys_b),
                Message(role="user", content=request.prompt),
            ],
            max_tokens=800,
            temperature=0.3,
        )
        text_b = (resp_b.content or "").strip() if hasattr(resp_b, "content") else str(resp_b or "")
    except Exception as e:
        text_b = f"[خطا در فراخوانی B: {e}]"

    # مقایسهٔ ساده — لازم نیست AI دیگری بیاوریم؛ معیارهای کمی کفایت می‌کند
    diff_chars = sum(1 for a, b in zip(text_a, text_b) if a != b) + abs(len(text_a) - len(text_b))
    similarity_pct = (
        round(100.0 * (1.0 - diff_chars / max(len(text_a), len(text_b), 1)), 1)
        if max(len(text_a), len(text_b)) > 0
        else 0.0
    )

    # شناسایی کلمات/جمله‌های جدید در B (کلمه‌هایی که فقط در B هستند)
    words_a = set(text_a.split())
    words_b = set(text_b.split())
    new_in_b = sorted(words_b - words_a)[:30]

    summary_lines = []
    summary_lines.append(
        f"تعداد فیلد memory فعال: {mem_count} "
        f"({len(mem_block.encode('utf-8')) if mem_block else 0} bytes)"
    )
    summary_lines.append(
        f"تعداد فیلد training فعال: {train_count} "
        f"({len(train_block.encode('utf-8')) if train_block else 0} bytes)"
    )
    summary_lines.append(f"شباهت خروجی A و B: {similarity_pct}%")
    summary_lines.append(f"اختلاف کاراکتر: {diff_chars}")
    summary_lines.append(f"کلمات تازه در B: {len(new_in_b)}")
    if new_in_b:
        summary_lines.append(f"نمونه کلمات تازه: {', '.join(new_in_b[:10])}")
    if similarity_pct >= 95:
        summary_lines.append(
            "نتیجه: memory/training تقریباً اثری روی این prompt خاص نداشتند "
            "(شاید موضوع پرامپت با محتوای فیلدها ربط زیادی نداشته)."
        )
    elif similarity_pct >= 75:
        summary_lines.append(
            "نتیجه: memory/training بر بخشی از خروجی اثر داشتند ولی کلیت پاسخ مشابه است."
        )
    else:
        summary_lines.append(
            "نتیجه: memory/training به‌طور معنادار خروجی را تغییر داده‌اند."
        )

    return {
        "success": True,
        "model_id": mid,
        "memory_fields_count": mem_count,
        "training_fields_count": train_count,
        "output_a": text_a[:5000],
        "output_b": text_b[:5000],
        "similarity_pct": similarity_pct,
        "diff_chars": diff_chars,
        "new_in_b_sample": new_in_b[:30],
        "summary": "\n".join(summary_lines),
    }


@router.post("/inspector/prompt-fields")
async def create_prompt_field(request: PromptFieldCreate, db: Session = Depends(get_db)):
    """ایجاد فیلد جدید دستور/حافظه/آموزش"""
    from ...models.inspector_prompt_field import InspectorPromptField

    if request.category not in ("instruction", "memory", "training"):
        return {"success": False, "error": "دسته‌بندی نامعتبر. مقادیر مجاز: instruction, memory, training"}

    field = InspectorPromptField(
        project_id=request.project_id,
        category=request.category,
        title=request.title,
        content=request.content,
        priority=request.priority,
        is_active=request.is_active,
    )
    db.add(field)
    db.commit()
    db.refresh(field)

    return {"success": True, "field": field.to_dict()}


@router.put("/inspector/prompt-fields/{field_id}")
async def update_prompt_field(field_id: str, request: PromptFieldUpdate, db: Session = Depends(get_db)):
    """ویرایش فیلد دستور/حافظه/آموزش"""
    from ...models.inspector_prompt_field import InspectorPromptField

    field = db.query(InspectorPromptField).filter(InspectorPromptField.id == field_id).first()
    if not field:
        return {"success": False, "error": "فیلد یافت نشد"}

    if request.title is not None:
        field.title = request.title
    if request.content is not None:
        field.content = request.content
    if request.priority is not None:
        field.priority = request.priority
    if request.is_active is not None:
        field.is_active = request.is_active
    if request.category is not None:
        if request.category not in ("instruction", "memory", "training"):
            return {"success": False, "error": "دسته‌بندی نامعتبر"}
        field.category = request.category

    db.commit()
    db.refresh(field)

    return {"success": True, "field": field.to_dict()}


@router.delete("/inspector/prompt-fields/{field_id}")
async def delete_prompt_field(field_id: str, db: Session = Depends(get_db)):
    """حذف فیلد"""
    from ...models.inspector_prompt_field import InspectorPromptField

    field = db.query(InspectorPromptField).filter(InspectorPromptField.id == field_id).first()
    if not field:
        return {"success": False, "error": "فیلد یافت نشد"}

    db.delete(field)
    db.commit()
    return {"success": True, "deleted_id": field_id}


@router.post("/inspector/prompt-fields/reorder")
async def reorder_prompt_fields(request: PromptFieldReorder, db: Session = Depends(get_db)):
    """تغییر ترتیب اولویت فیلدها"""
    from ...models.inspector_prompt_field import InspectorPromptField

    for idx, fid in enumerate(request.field_ids):
        field = db.query(InspectorPromptField).filter(
            InspectorPromptField.id == fid,
            InspectorPromptField.project_id == request.project_id
        ).first()
        if field:
            field.priority = len(request.field_ids) - idx  # اول لیست = بالاترین اولویت

    db.commit()
    return {"success": True}


@router.post("/inspector/prompt-fields/test")
async def test_prompt_field(request: PromptFieldTestRequest, db: Session = Depends(get_db)):
    """
    تست زنده فیلد: مدل AI واقعی را با این دستور/حافظه فراخوانی می‌کند
    و تأیید می‌کند که مدل واقعاً آن را خوانده و درک کرده است.
    هیچ چیز موک نیست - درخواست واقعی به مدل ارسال می‌شود.
    """
    from ...models.inspector_prompt_field import InspectorPromptField
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    from datetime import datetime

    field = db.query(InspectorPromptField).filter(InspectorPromptField.id == request.field_id).first()
    if not field:
        return {"success": False, "error": "فیلد یافت نشد"}

    ai_manager = get_ai_manager()

    # ساخت پرامپت تست واقعی
    test_system = f"""تو یک مدل هوش مصنوعی هستی که باید ثابت کنی یک دستور/حافظه/آموزش را واقعاً خوانده‌ای و درک کرده‌ای.

محتوای فیلد ({field.category}):
---
عنوان: {field.title}
محتوا: {field.content}
---

وظیفه تو:
1. اول بگو دقیقاً چه چیزی در این فیلد نوشته شده (خلاصه ۱-۲ جمله‌ای)
2. یک مثال عملی بزن که نشان دهد این دستور/حافظه چطور در عمل استفاده خواهد شد
3. در آخر بنویس: "✅ تأیید: این فیلد توسط مدل خوانده و درک شد"
"""

    test_user = request.test_scenario or f"لطفاً ثابت کن که فیلد «{field.title}» را خوانده‌ای و می‌فهمی. یک مثال عملی از کاربرد آن بزن."

    try:
        response = await ai_manager.generate(
            model_id=request.model_id,
            messages=[
                Message(role="system", content=test_system),
                Message(role="user", content=test_user)
            ],
            max_tokens=1024,
            temperature=0.3
        )

        test_passed = "✅" in response.content and ("تأیید" in response.content or "تایید" in response.content)

        # ذخیره نتیجه تست در دیتابیس
        field.last_tested_at = datetime.utcnow()
        field.last_test_passed = test_passed
        field.last_test_result = json.dumps({
            "model_id": request.model_id,
            "response": response.content,
            "tokens_used": getattr(response, 'tokens_used', 0) or 0,
            "passed": test_passed,
            "tested_at": datetime.utcnow().isoformat()
        }, ensure_ascii=False)
        db.commit()

        return {
            "success": True,
            "test_passed": test_passed,
            "model_id": request.model_id,
            "response": response.content,
            "tokens_used": getattr(response, 'tokens_used', 0) or 0,
            "field": field.to_dict()
        }

    except Exception as e:
        field.last_tested_at = datetime.utcnow()
        field.last_test_passed = False
        field.last_test_result = json.dumps({
            "model_id": request.model_id,
            "error": str(e),
            "passed": False,
            "tested_at": datetime.utcnow().isoformat()
        }, ensure_ascii=False)
        db.commit()

        return {
            "success": False,
            "test_passed": False,
            "error": str(e),
            "field": field.to_dict()
        }


@router.get("/inspector/prompt-fields/usage-log/{project_id}")
async def get_prompt_field_usage_log(project_id: str, db: Session = Depends(get_db)):
    """دریافت لاگ استفاده فیلدها - کدام فیلدها اخیراً توسط مدل‌ها خوانده شده‌اند"""
    from ...models.inspector_prompt_field import InspectorPromptField

    fields = db.query(InspectorPromptField).filter(
        InspectorPromptField.project_id == project_id,
        InspectorPromptField.usage_count > 0
    ).order_by(InspectorPromptField.last_used_at.desc()).all()

    return {
        "success": True,
        "usage_log": [
            {
                "field_id": f.id,
                "title": f.title,
                "category": f.category,
                "usage_count": f.usage_count,
                "last_used_at": f.last_used_at.isoformat() if f.last_used_at else None
            }
            for f in fields
        ]
    }


@router.post("/inspector/prompt-fields/init-defaults/{project_id}")
async def init_default_prompt_fields(project_id: str, db: Session = Depends(get_db)):
    """
    مقداردهی اولیه فیلدهای دستور/حافظه/آموزش از اطلاعات موجود پروژه.
    اگر فیلدی وجود نداشته باشد، فیلدهای پیش‌فرض ایجاد می‌شود.
    همچنین memory_instructions و dynamic_fields پروژه را وارد می‌کند.
    """
    from ...models.inspector_prompt_field import InspectorPromptField
    from ...models.project import Project

    # بررسی وجود فیلدها
    existing = db.query(InspectorPromptField).filter(
        InspectorPromptField.project_id == project_id
    ).count()

    if existing > 0:
        fields = db.query(InspectorPromptField).filter(
            InspectorPromptField.project_id == project_id
        ).order_by(InspectorPromptField.priority.desc(), InspectorPromptField.created_at).all()
        return {"success": True, "fields": [f.to_dict() for f in fields], "already_initialized": True}

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    created_fields = []

    # ─── واردسازی memory_instructions از پروژه ───
    if project.memory_instructions:
        try:
            mem_data = json.loads(project.memory_instructions) if isinstance(project.memory_instructions, str) else project.memory_instructions
            mem_content = mem_data.get("content", "") if isinstance(mem_data, dict) else str(mem_data)
            if mem_content and mem_content.strip():
                f = InspectorPromptField(
                    project_id=project_id,
                    category="memory",
                    title="حافظه اصلی پروژه (وارد شده)",
                    content=mem_content.strip(),
                    priority=10,
                    is_active=True,
                )
                db.add(f)
                created_fields.append(f)
        except Exception:
            pass

    # ─── واردسازی dynamic_fields از پروژه ───
    if project.dynamic_fields:
        try:
            dfields = json.loads(project.dynamic_fields) if isinstance(project.dynamic_fields, str) else project.dynamic_fields
            if isinstance(dfields, list):
                for idx, df in enumerate(dfields):
                    df_name = df.get("name", df.get("title", f"فیلد {idx+1}"))
                    df_value = df.get("value", df.get("content", ""))
                    if df_value and str(df_value).strip():
                        f = InspectorPromptField(
                            project_id=project_id,
                            category="instruction",
                            title=df_name,
                            content=str(df_value).strip(),
                            priority=8 - idx,
                            is_active=True,
                        )
                        db.add(f)
                        created_fields.append(f)
        except Exception:
            pass

    # ─── فیلدهای پیش‌فرض اگر هیچ فیلدی وارد نشد ───
    if not created_fields:
        defaults = [
            {
                "category": "instruction",
                "title": "زبان پاسخ‌دهی",
                "content": "همیشه به فارسی پاسخ بده. کدها و اصطلاحات فنی می‌توانند انگلیسی باشند.",
                "priority": 10,
            },
            {
                "category": "memory",
                "title": "معماری پروژه",
                "content": f"نام پروژه: {project.name}\nتکنولوژی‌ها: {project.technologies or 'نامشخص'}\nGitHub: {project.github_path or 'نامشخص'}",
                "priority": 9,
            },
            {
                "category": "training",
                "title": "سبک کدنویسی",
                "content": "از سبک کدنویسی موجود در پروژه پیروی کن. کامنت‌ها به فارسی باشند.",
                "priority": 5,
            },
        ]
        for d in defaults:
            f = InspectorPromptField(
                project_id=project_id,
                category=d["category"],
                title=d["title"],
                content=d["content"],
                priority=d["priority"],
                is_active=True,
            )
            db.add(f)
            created_fields.append(f)

    db.commit()
    for f in created_fields:
        db.refresh(f)

    return {
        "success": True,
        "fields": [f.to_dict() for f in created_fields],
        "created_count": len(created_fields),
        "already_initialized": False
    }


# =====================================================
# 🔍 Inspector: Error Investigation & Fix Endpoints
# =====================================================

class InvestigateRequest(BaseModel):
    message_id: int
    project_id: str
    model_ids: List[str]  # مدل‌های انتخاب شده


class FixRequest(BaseModel):
    project_id: str
    model_ids: List[str]
    investigation_report: str
    files_to_fix: List[dict]  # [{path, issue, suggested_fix}]
    error_message: str


class BulkInvestigateRequest(BaseModel):
    """درخواست بررسی کلی چند خطا با هم"""
    message_ids: List[int]  # شناسه‌های DB پیام‌های خطا
    project_id: str
    model_ids: List[str]


@router.get("/inspector/models/for-investigation/{project_id}")
async def get_models_for_investigation(project_id: str, db: Session = Depends(get_db)):
    """
    دریافت لیست همه مدل‌ها (فعال و غیرفعال) برای بررسی خطا
    مدل‌های دارای قابلیت CODE و REASONING اولویت بالاتری دارن
    """
    from ...core.models_registry import MODEL_REGISTRY, ModelCapability
    from ...models.ai_profile import ModelSettings
    from ...services.ai_manager import get_ai_manager

    ai_manager = get_ai_manager()
    all_models = []

    # تنظیمات از دیتابیس
    db_settings = db.query(ModelSettings).all()
    db_map = {s.model_id: s for s in db_settings}

    for model_id, model in MODEL_REGISTRY.items():
        if model.is_image_generator:
            continue

        db_setting = db_map.get(model_id)
        is_enabled = bool(db_setting.enabled) if db_setting else model.enabled

        # بررسی اینکه provider فعال هست
        provider_available = False
        try:
            if model.provider in ai_manager._services:
                svc = ai_manager._services[model.provider]
                provider_available = bool(svc.api_key) and not svc.is_in_error_state()
        except Exception:
            pass

        # امتیاز پیشنهاد
        score = 0
        caps = model.capabilities
        if ModelCapability.CODE in caps:
            score += 30
        if ModelCapability.REASONING in caps:
            score += 20
        if model.context_window >= 100000:
            score += 10
        score += (10 - model.priority)

        all_models.append({
            "id": model_id,
            "name": model.name,
            "provider": model.provider.value if hasattr(model.provider, 'value') else str(model.provider),
            "enabled": is_enabled,
            "provider_available": provider_available,
            "capabilities": [c.value for c in model.capabilities],
            "context_window": model.context_window,
            "priority": model.priority,
            "recommendation_score": score,
            "recommended": score >= 30 and is_enabled and provider_available,
        })

    # مرتب‌سازی: پیشنهادی > فعال > غیرفعال
    all_models.sort(key=lambda m: (
        -int(m["recommended"]),
        -int(m["enabled"] and m["provider_available"]),
        -m["recommendation_score"]
    ))

    return {"success": True, "models": all_models}


@router.post("/inspector/models/quick-enable/{model_id}")
async def quick_enable_model(model_id: str, db: Session = Depends(get_db)):
    """فعال‌سازی سریع مدل از تب بازرس"""
    from ...models.ai_profile import ModelSettings

    setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
    if setting:
        setting.enabled = 1
    else:
        setting = ModelSettings(model_id=model_id, enabled=1)
        db.add(setting)
    db.commit()
    return {"success": True, "model_id": model_id, "enabled": True}


@router.post("/inspector/investigate")
async def investigate_error(request: InvestigateRequest, db: Session = Depends(get_db)):
    """
    بررسی ریشه‌ای خطا با AI - خواندن کد از GitHub و تحلیل
    پاسخ به صورت SSE (Server-Sent Events) استریم میشه
    """
    from fastapi.responses import StreamingResponse
    from ...models.inspector_session import InspectorMessage
    from ...models.project import Project
    from ...services.github_import import get_github_import_service
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    # دریافت اطلاعات پیام خطا
    msg = db.query(InspectorMessage).filter(InspectorMessage.id == request.message_id).first()
    if not msg:
        return {"success": False, "error": "پیام یافت نشد"}

    # جمع‌آوری context: خطاهای فرانت‌اند نزدیک + لاگ‌های بک‌اند
    # پیام‌های خطای JS نزدیک (۶۰ ثانیه قبل و بعد) از همین سشن
    from sqlalchemy import or_
    nearby_errors = db.query(InspectorMessage).filter(
        InspectorMessage.session_id == msg.session_id,
        or_(
            InspectorMessage.action_type == 'error',
            InspectorMessage.action_type == 'console-error'
        ),
        InspectorMessage.timestamp >= (msg.timestamp - timedelta(seconds=60)) if msg.timestamp else True,
        InspectorMessage.timestamp <= (msg.timestamp + timedelta(seconds=60)) if msg.timestamp else True,
    ).order_by(InspectorMessage.timestamp).limit(10).all()

    error_context_lines = []
    for em in nearby_errors:
        error_context_lines.append(f"[{em.action_type}] {em.content}")

    # لاگ summary از تیک بررسی
    backend_summary = msg.backend_log_summary or ""

    # دریافت اطلاعات پروژه
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    # استخراج اطلاعات GitHub
    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    if not owner or not repo:
        return {"success": False, "error": "اطلاعات GitHub پروژه یافت نشد. لطفاً پروژه را از GitHub ایمپورت کنید."}

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from ...models.setting import Setting as _InvSetting
        token = _InvSetting.get_value(db, "api_key_github") or ""
    model_ids = request.model_ids

    # ساخت context کامل خطا
    error_content_parts = [f"اکشن کاربر: {msg.content}"]
    if backend_summary:
        error_content_parts.append(f"نتیجه بررسی بک‌اند: {backend_summary}")
    if error_context_lines:
        error_content_parts.append(f"خطاهای فرانت‌اند مرتبط ({len(error_context_lines)} خطا):")
        error_content_parts.extend(error_context_lines)
    else:
        error_content_parts.append("⚠️ هیچ خطای JavaScript فرانت‌اند ضبط نشده. bridge script ممکن است خطاها را دریافت نکرده باشد.")
    error_content = "\n".join(error_content_parts)

    async def event_stream():
        github_svc = get_github_import_service()
        ai_manager = get_ai_manager()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        # --- مرحله ۱: خواندن ساختار پروژه ---
        yield sse("progress", {
            "step": "reading_tree",
            "message": f"📂 در حال خواندن ساختار پروژه {owner}/{repo}..."
        })

        tree_result = await github_svc.get_repo_tree(owner, repo, token=token)
        if not tree_result.get("success"):
            yield sse("error", {"message": f"خطا در دسترسی به ریپازیتوری: {tree_result.get('error', 'unknown')}"})
            yield sse("done", {"success": False})
            return

        all_files = [f for f in tree_result.get("tree", []) if f.get("type") == "blob"]
        yield sse("progress", {
            "step": "tree_loaded",
            "message": f"✅ ساختار پروژه خوانده شد ({len(all_files)} فایل)"
        })

        # --- مرحله ۲: AI تحلیل خطا و انتخاب فایل‌ها ---
        primary_model = model_ids[0] if model_ids else "gemini-2.0-flash"

        # فهرست فایل‌های مرتبط (فیلتر شده)
        code_files = [f["path"] for f in all_files
                      if _is_code_file(f["path"], file_size=f.get("size", 0))]

        file_list_text = "\n".join(code_files[:500])

        yield sse("progress", {
            "step": "analyzing_error",
            "message": f"🤖 مدل {primary_model} در حال تحلیل خطا و شناسایی فایل‌های مرتبط...",
            "model": primary_model
        })

        # از AI بخواه فایل‌های مرتبط رو انتخاب کنه
        select_prompt = f"""شما بازرس خطای پروژه {owner}/{repo} هستید.

⚠️ قوانین مهم:
- فایل‌های InspectorBridge بخش پروژه نیستند (ابزار دیباگ inject شده). آنها را نادیده بگیرید.
- فقط فایل‌های اصلی پروژه را بررسی کنید.

## اطلاعات خطا:
{error_content}

## لیست فایل‌های پروژه:
{file_list_text}

بر اساس خطا و اطلاعات موجود، حداکثر ۸ فایل مرتبط را انتخاب کنید.
فقط مسیر فایل‌ها را بنویسید، هر کدام در یک خط جدید.
هیچ توضیح اضافی ندهید."""

        try:
            select_response = await ai_manager.generate(
                model_id=primary_model,
                messages=[
                    Message(role="system", content="شما بازرس کد هستید. فقط مسیر فایل‌ها را بنویسید."),
                    Message(role="user", content=select_prompt)
                ],
                max_tokens=500,
                temperature=0.3
            )

            # استخراج مسیر فایل‌ها از پاسخ (با پارسر قوی)
            selected_files = _parse_ai_selected_files(select_response.content, code_files, max_files=8)

            # فالبک: اگر AI نتونست فایلی match کنه
            if not selected_files:
                selected_files = _fallback_file_selection(code_files, error_content, max_files=5)

        except Exception as e:
            yield sse("progress", {
                "step": "select_fallback",
                "message": f"⚠️ خطا در تحلیل AI: {str(e)[:80]}. استفاده از فایل‌های پیش‌فرض..."
            })
            selected_files = code_files[:5]

        yield sse("progress", {
            "step": "files_selected",
            "message": f"📋 {len(selected_files)} فایل مرتبط شناسایی شد: {', '.join(f.split('/')[-1] for f in selected_files)}"
        })

        # --- مرحله ۲.۵: اضافه کردن خودکار فایل‌های مدل/اسکیما ---
        # وقتی خطا مربوط به دیتابیس باشه، فایل‌های models/ و schemas/ هم لازمن
        db_keywords = ["column", "table", "migration", "ستون", "جدول", "database", "sql",
                       "column", "field", "model", "schema", "alembic", "migrate"]
        error_lower = error_content.lower()
        has_db_error = any(kw in error_lower for kw in db_keywords)

        if has_db_error:
            model_files = [f for f in code_files
                           if any(p in f.lower() for p in ["models/", "schemas/", "model.", "schema.", "alembic/"])
                           and f not in selected_files]
            if model_files:
                extra = model_files[:5]
                selected_files.extend(extra)
                yield sse("progress", {
                    "step": "auto_add_models",
                    "message": f"🗄️ خطای دیتابیس شناسایی شد - {len(extra)} فایل مدل/اسکیما اضافه شد: {', '.join(f.split('/')[-1] for f in extra)}"
                })

        # --- مرحله ۳: خواندن محتوای فایل‌ها ---
        file_contents = {}
        for i, file_path in enumerate(selected_files):
            yield sse("progress", {
                "step": "reading_file",
                "message": f"📖 مدل {primary_model} در حال خواندن {file_path}...",
                "model": primary_model,
                "file": file_path,
                "progress": f"{i + 1}/{len(selected_files)}"
            })

            try:
                result = await github_svc.get_file_content(owner, repo, file_path, token=token)
                if result.get("success"):
                    content = result.get("content", "")
                    # محدود کردن اندازه
                    if len(content) > 15000:
                        content = content[:15000] + "\n... [truncated]"
                    file_contents[file_path] = content
            except Exception as e:
                yield sse("progress", {
                    "step": "file_error",
                    "message": f"⚠️ خطا در خواندن {file_path}: {str(e)[:60]}"
                })
            await asyncio.sleep(0.2)  # rate limit

        yield sse("progress", {
            "step": "files_read",
            "message": f"✅ {len(file_contents)} فایل خوانده شد. شروع تحلیل ریشه‌ای..."
        })

        # --- مرحله ۴: تحلیل ریشه‌ای توسط AI ---
        code_context = ""
        for path, content in file_contents.items():
            _fl_lines = len(content.split("\n"))
            code_context += f"\n\n=== {path} ({_fl_lines} خط) ===\n{content}"

        investigate_prompt = f"""شما بازرس ارشد کد پروژه {owner}/{repo} هستید.

## ⚠️ قوانین حیاتی:
1. فایل InspectorBridge یک ابزار دیباگ inject شده است و جزو پروژه اصلی نیست. آن را نادیده بگیرید.
2. اگر خطای JavaScript دقیقی در دسترس نیست، صادقانه بگویید "خطای دقیقی ضبط نشده" - حدس نزنید.
3. فقط بر اساس شواهد موجود در کد تحلیل کنید، نه حدس و گمان.
4. اگر مشکل واضح نیست، چند احتمال را با درصد اطمینان ذکر کنید.

## اطلاعات خطا:
{error_content}

## کد پروژه:
{code_context}

## وظیفه شما:
1. آیا خطای JavaScript دقیقی وجود دارد؟ اگر بله، آن را تحلیل کنید.
2. اگر خطای دقیقی نیست، کد را برای مشکلات رایج بررسی کنید (null reference, import errors, routing issues, etc.)
3. هر مشکلی که پیدا کردید را با شماره خط دقیق مشخص کنید.
4. راه‌حل دقیق و عملی ارائه دهید.

## فرمت پاسخ:

### 📊 سطح اطمینان
[بالا / متوسط / پایین - بر اساس اینکه خطای دقیقی دارید یا نه]

### 🔍 علت ریشه‌ای
[فقط بر اساس شواهد واقعی از کد - نه حدس]

### 📍 محل مشکل
- فایل: `[مسیر دقیق]`
- خط: [شماره دقیق]
- کد مشکل‌دار:
```
[کد واقعی از فایل]
```

### 💡 راه‌حل
[راه‌حل مشخص و عملی]

### 🔧 دستورالعمل اصلاح
[دقیقاً در کدام فایل، چه خطی، چه تغییری - به صورت diff]

### 📝 فایل‌های نیاز به تغییر
[فقط فایل‌هایی که واقعاً نیاز به تغییر دارند]"""

        # اگر چند مدل انتخاب شده، از اولی برای تحلیل اصلی استفاده کن
        yield sse("progress", {
            "step": "deep_analysis",
            "message": f"🔬 مدل {primary_model} در حال تحلیل ریشه‌ای خطا در {len(file_contents)} فایل...",
            "model": primary_model
        })

        system_msg = """شما یک بازرس ارشد کد هستید.

قوانین:
- فقط بر اساس شواهد واقعی تحلیل کنید. اگر خطای دقیقی ندارید، صادق باشید.
- فایل InspectorBridge ابزار دیباگ inject شده و مربوط به پروژه نیست. هرگز آن را مقصر ندانید.
- Layout.tsx اصلی پروژه را تغییر ندهید مگر مشکل واضحاً از آنجا باشد.
- حدس نزنید. اگر مطمئن نیستید، بگویید "مطمئن نیستم" با چند احتمال.
- پاسخ فارسی و مختصر."""

        try:
            analysis = await ai_manager.generate(
                model_id=primary_model,
                messages=[
                    Message(role="system", content=system_msg),
                    Message(role="user", content=investigate_prompt)
                ],
                max_tokens=4000,
                temperature=0.2,
                task_type="debugging"
            )

            report = analysis.content

        except Exception as e:
            yield sse("error", {"message": f"خطا در تحلیل AI: {str(e)[:100]}"})
            yield sse("done", {"success": False})
            return

        # --- مرحله ۴.۵: دو مرحله‌ای - اگر AI فایل‌هایی رو لازم داشت که نخونده ---
        # بررسی اینکه آیا AI اشاره به فایل‌هایی کرده که نداشته
        missing_file_markers = ["نداریم", "ارائه نشده", "در دسترس نیست",
                                "نداشتیم", "ندیدیم", "فرضی", "فرض می‌کنیم",
                                "کد مدل را نداریم", "این فایل", "not provided",
                                "not available", "couldn't read"]
        needs_second_pass = any(marker in report for marker in missing_file_markers)

        if needs_second_pass:
            yield sse("progress", {
                "step": "second_pass",
                "message": "🔄 مدل فایل‌های بیشتری نیاز دارد. شناسایی و خواندن فایل‌های ناخوانده..."
            })

            # از AI بخواه بگه دقیقاً چه فایلی لازم داره
            try:
                missing_resp = await ai_manager.generate(
                    model_id=primary_model,
                    messages=[
                        Message(role="system", content="فقط مسیر فایل‌هایی را بنویسید که برای تکمیل تحلیل نیاز دارید. هر مسیر در یک خط."),
                        Message(role="user", content=f"گزارش شما:\n{report[:2000]}\n\nفایل‌هایی که خواندید:\n{chr(10).join(file_contents.keys())}\n\nتمام فایل‌های موجود در پروژه:\n{file_list_text[:3000]}\n\nکدام فایل‌ها را نخوانده‌اید که نیاز دارید؟ فقط مسیر بنویسید.")
                    ],
                    max_tokens=300,
                    temperature=0.1
                )

                extra_files = []
                for line in missing_resp.content.strip().split("\n"):
                    line = line.strip().strip("`").strip("- ").strip()
                    if line and line in code_files and line not in file_contents:
                        extra_files.append(line)

                # خواندن فایل‌های جدید
                extra_contents = {}
                for fp in extra_files[:5]:
                    yield sse("progress", {
                        "step": "reading_extra",
                        "message": f"📖 خواندن فایل اضافی: {fp}...",
                        "file": fp
                    })
                    try:
                        result = await github_svc.get_file_content(owner, repo, fp, token=token)
                        if result.get("success"):
                            content = result.get("content", "")
                            if len(content) > 15000:
                                content = content[:15000] + "\n... [truncated]"
                            extra_contents[fp] = content
                            file_contents[fp] = content
                    except Exception:
                        pass
                    await asyncio.sleep(0.2)

                if extra_contents:
                    # تحلیل مجدد با فایل‌های جدید
                    extra_context = ""
                    for path, content in extra_contents.items():
                        extra_context += f"\n\n=== {path} ===\n{content}"

                    yield sse("progress", {
                        "step": "reanalysis",
                        "message": f"🔬 تحلیل مجدد با {len(extra_contents)} فایل اضافی...",
                        "model": primary_model
                    })

                    reanalysis = await ai_manager.generate(
                        model_id=primary_model,
                        messages=[
                            Message(role="system", content=system_msg),
                            Message(role="user", content=f"تحلیل قبلی شما:\n{report}\n\nفایل‌های جدیدی که درخواست کرده بودید:\n{extra_context}\n\nلطفاً تحلیل خود را با اطلاعات جدید بازنویسی و تکمیل کنید. فرمت قبلی را حفظ کنید.")
                        ],
                        max_tokens=4000,
                        temperature=0.2,
                        task_type="debugging"
                    )
                    report = reanalysis.content

                    yield sse("progress", {
                        "step": "reanalysis_done",
                        "message": "✅ تحلیل مجدد با فایل‌های کامل‌تر انجام شد"
                    })

            except Exception as e:
                yield sse("progress", {
                    "step": "second_pass_error",
                    "message": f"⚠️ خطا در مرحله دوم: {str(e)[:60]}"
                })

        # --- مرحله ۵: اگر مدل دوم هم بود، بررسی متقابل ---
        if len(model_ids) > 1:
            second_model = model_ids[1]
            yield sse("progress", {
                "step": "cross_review",
                "message": f"🔄 مدل {second_model} در حال بررسی متقابل تحلیل...",
                "model": second_model
            })

            try:
                review_response = await ai_manager.generate(
                    model_id=second_model,
                    messages=[
                        Message(role="system", content="شما بازرس متقابل کد هستید. گزارش همکارتان را نقادانه بررسی کنید. آیا تحلیل بر اساس شواهد واقعی است یا حدس؟ آیا InspectorBridge (ابزار inject شده) به اشتباه مقصر شناخته شده؟ اگر مشکلی می‌بینید بگویید."),
                        Message(role="user", content=f"خطا: {error_content}\n\nگزارش مدل اول:\n{report}\n\nآیا این تحلیل صحیح و مبتنی بر شواهد است؟ اگر خطا دارد تصحیح کنید. اگر درست است بنویسید 'تأیید'.")
                    ],
                    max_tokens=1500,
                    temperature=0.3
                )

                if "تأیید" not in review_response.content.lower():
                    report += f"\n\n---\n### 🔄 نظر تکمیلی ({second_model}):\n{review_response.content}"

            except Exception as e:
                yield sse("progress", {
                    "step": "review_error",
                    "message": f"⚠️ بررسی متقابل ناموفق: {str(e)[:60]}"
                })

        # --- مرحله ۶: استخراج فایل‌های نیاز به تغییر ---
        # هم از فایل‌های خوانده شده و هم از تمام فایل‌های پروژه
        files_to_fix = []
        report_lower = report.lower()
        seen_paths = set()
        # اول فایل‌های خوانده شده
        for path in file_contents.keys():
            if path.lower() in report_lower:
                files_to_fix.append({"path": path, "in_report": True})
                seen_paths.add(path)
        # بعد فایل‌هایی که در گزارش اشاره شده ولی نخوانده شدن
        for path in code_files:
            if path not in seen_paths and path.lower() in report_lower:
                files_to_fix.append({"path": path, "in_report": True, "not_read": True})
                seen_paths.add(path)

        # --- ارسال گزارش نهایی ---
        yield sse("report", {
            "report": report,
            "model_used": primary_model,
            "models_used": model_ids,
            "files_investigated": list(file_contents.keys()),
            "files_to_fix": files_to_fix,
            "error_content": error_content,
            "github_repo": f"{owner}/{repo}",
            "tokens_used": getattr(analysis, 'tokens_used', 0)
        })

        yield sse("done", {"success": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/inspector/investigate-bulk")
async def investigate_errors_bulk(request: BulkInvestigateRequest, db: Session = Depends(get_db)):
    """
    بررسی کلی چند خطا با هم — تحلیل اولویت، وابستگی و ریشه مشترک
    SSE streaming
    """
    from fastapi.responses import StreamingResponse
    from ...models.inspector_session import InspectorMessage
    from ...models.project import Project
    from ...services.github_import import get_github_import_service
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    if not request.message_ids or len(request.message_ids) == 0:
        return {"success": False, "error": "هیچ خطایی انتخاب نشده"}

    # دریافت پیام‌های خطا از DB
    from sqlalchemy import or_
    error_messages = db.query(InspectorMessage).filter(
        InspectorMessage.id.in_(request.message_ids)
    ).order_by(InspectorMessage.timestamp).all()

    if not error_messages:
        return {"success": False, "error": "پیام‌های خطا یافت نشد"}

    # ── Deduplication: حذف خطاهای تکراری بر اساس محتوا ──
    _seen_contents = set()
    _unique_messages = []
    _dup_count = 0
    for em in error_messages:
        # نرمال‌سازی: حذف timestamp و whitespace اضافی برای مقایسه بهتر
        _normalized = em.content.strip().lower() if em.content else ""
        if _normalized and _normalized not in _seen_contents:
            _seen_contents.add(_normalized)
            _unique_messages.append(em)
        else:
            _dup_count += 1
    if _dup_count > 0:
        slog.info(f"[investigate-bulk] Deduplicated: {_dup_count} duplicate errors removed, {len(_unique_messages)} unique remaining")
    error_messages = _unique_messages

    # دریافت اطلاعات پروژه
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    if not owner or not repo:
        return {"success": False, "error": "اطلاعات GitHub پروژه یافت نشد"}

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from ...models.setting import Setting as _BulkSetting
        token = _BulkSetting.get_value(db, "api_key_github") or ""

    model_ids = request.model_ids

    # ساخت context کامل تمام خطاها با جزئیات
    errors_detail_parts = []
    all_nearby_errors = set()
    for idx, em in enumerate(error_messages, 1):
        error_type = "خطای کنسول" if em.action_type == "console-error" else "خطای بک‌اند"
        ts = em.timestamp.strftime("%H:%M:%S") if em.timestamp else "نامشخص"
        detail = f"### خطای {idx}: [{error_type}] — زمان: {ts}\n"
        detail += f"**محتوا:** {em.content}\n"

        if em.backend_log_summary:
            detail += f"**خلاصه لاگ بک‌اند:** {em.backend_log_summary}\n"

        # لاگ‌های نزدیک
        nearby = db.query(InspectorMessage).filter(
            InspectorMessage.session_id == em.session_id,
            or_(
                InspectorMessage.action_type == 'error',
                InspectorMessage.action_type == 'console-error'
            ),
            InspectorMessage.timestamp >= (em.timestamp - timedelta(seconds=30)) if em.timestamp else True,
            InspectorMessage.timestamp <= (em.timestamp + timedelta(seconds=30)) if em.timestamp else True,
        ).order_by(InspectorMessage.timestamp).limit(5).all()

        if nearby:
            related = [n.content for n in nearby if n.id not in [e.id for e in error_messages]]
            if related:
                detail += f"**خطاهای نزدیک:** {'; '.join(related[:3])}\n"

        errors_detail_parts.append(detail)
        all_nearby_errors.update(n.content for n in nearby)

    errors_full_context = "\n".join(errors_detail_parts)

    async def event_stream():
        import asyncio
        github_svc = get_github_import_service()
        ai_manager = get_ai_manager()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        _dedup_note = f" ({_dup_count} تکراری حذف شد)" if _dup_count > 0 else ""
        yield sse("progress", {
            "step": "start",
            "message": f"🔍 شروع بررسی کلی {len(error_messages)} خطای یکتا{_dedup_note}..."
        })

        # --- مرحله ۱: ساختار پروژه ---
        yield sse("progress", {
            "step": "reading_tree",
            "message": f"📂 خواندن ساختار پروژه {owner}/{repo}..."
        })

        tree_result = await github_svc.get_repo_tree(owner, repo, token=token)
        if not tree_result.get("success"):
            yield sse("error", {"message": f"خطا در دسترسی GitHub: {tree_result.get('error', 'unknown')}"})
            yield sse("done", {"success": False})
            return

        all_files = [f for f in tree_result.get("tree", []) if f.get("type") == "blob"]
        code_files = [f["path"] for f in all_files if _is_code_file(f["path"], file_size=f.get("size", 0))]
        file_list_text = "\n".join(code_files[:500])

        yield sse("progress", {
            "step": "tree_loaded",
            "message": f"✅ {len(code_files)} فایل کد شناسایی شد"
        })

        # --- مرحله ۲: AI انتخاب فایل‌ها ---
        primary_model = model_ids[0] if model_ids else "gemini-2.0-flash"

        yield sse("progress", {
            "step": "selecting_files",
            "message": f"🤖 مدل {primary_model} در حال شناسایی فایل‌های مرتبط با {len(error_messages)} خطا..."
        })

        select_prompt = f"""شما بازرس خطای پروژه {owner}/{repo} هستید.
{len(error_messages)} خطا برای بررسی کلی ارسال شده:

{errors_full_context}

فایل‌های پروژه:
{file_list_text}

⚠️ فایل‌های InspectorBridge ابزار inject شده‌اند و مربوط به پروژه نیستند.

بر اساس تمام خطاها، حداکثر ۱۵ فایل مرتبط انتخاب کنید.
فایل‌های مرتبط با ریشه مشترک خطاها اولویت دارند.
فقط مسیر فایل‌ها، هر کدام در یک خط."""

        try:
            select_response = await ai_manager.generate(
                model_id=primary_model,
                messages=[
                    Message(role="system", content="بازرس کد. فقط مسیر فایل‌ها."),
                    Message(role="user", content=select_prompt)
                ],
                max_tokens=800,
                temperature=0.3
            )
            selected_files = _parse_ai_selected_files(select_response.content, code_files, max_files=15)
            if not selected_files:
                selected_files = _fallback_file_selection(code_files, errors_full_context, max_files=10)
        except Exception as e:
            yield sse("progress", {"step": "select_fallback", "message": f"⚠️ فالبک: {str(e)[:60]}"})
            selected_files = _fallback_file_selection(code_files, errors_full_context, max_files=10)

        yield sse("progress", {
            "step": "files_selected",
            "message": f"📋 {len(selected_files)} فایل مرتبط: {', '.join(f.split('/')[-1] for f in selected_files[:8])}{'...' if len(selected_files) > 8 else ''}"
        })

        # --- مرحله ۳: خواندن فایل‌ها ---
        # حذف فایل‌های تکراری
        _seen_bulk = set()
        _deduped_bulk = []
        for _sf in selected_files:
            if _sf not in _seen_bulk:
                _seen_bulk.add(_sf)
                _deduped_bulk.append(_sf)
        if len(_deduped_bulk) < len(selected_files):
            slog.info(f"[investigate-bulk] Deduplicated file list: {len(selected_files)} → {len(_deduped_bulk)}")
        selected_files = _deduped_bulk

        file_contents = {}
        for i, file_path in enumerate(selected_files):
            yield sse("progress", {
                "step": "reading_file",
                "message": f"📖 خواندن {file_path} ({i+1}/{len(selected_files)})..."
            })
            try:
                result = await github_svc.get_file_content(owner, repo, file_path, token=token)
                if result.get("success"):
                    content = result.get("content", "")
                    if len(content) > 12000:
                        content = content[:12000] + "\n... [truncated]"
                    file_contents[file_path] = content
            except Exception:
                pass
            await asyncio.sleep(0.2)

        yield sse("progress", {
            "step": "files_read",
            "message": f"✅ {len(file_contents)} فایل خوانده شد. شروع تحلیل کلی..."
        })

        # --- مرحله ۴: تحلیل کلی AI ---
        code_context = ""
        for path, content in file_contents.items():
            _fl_lines = len(content.split("\n"))
            code_context += f"\n\n=== {path} ({_fl_lines} خط) ===\n{content}"

        bulk_investigate_prompt = f"""شما بازرس ارشد پروژه {owner}/{repo} هستید.
{len(error_messages)} خطا برای تحلیل کلی ارسال شده. وظیفه شما تحلیل جامع، اولویت‌بندی و شناسایی وابستگی‌هاست.

## ⚠️ قوانین حیاتی:
1. InspectorBridge ابزار inject شده و جزو پروژه نیست — نادیده بگیرید.
2. فقط بر اساس شواهد واقعی تحلیل کنید.
3. وابستگی بین خطاها مهم‌ترین بخش تحلیل شماست.

## خطاهای ارسالی (به ترتیب زمانی):
{errors_full_context}

## کد پروژه:
{code_context}

## وظیفه شما — تحلیل کلی:

### ۱. 📊 نقشه وابستگی خطاها
- آیا خطاها به هم مرتبط هستند؟ کدام خطا ممکنه علت خطای دیگه باشه؟
- آیا ریشه مشترکی وجود داره؟ (مثلاً یک import خراب که چند خطا ایجاد کرده)
- نمودار وابستگی: خطای X ← خطای Y (Y علت X هست)

### ۲. 🎯 اولویت‌بندی (از مهم‌ترین تا کم‌اهمیت‌ترین)
برای هر خطا مشخص کنید:
- **سطح بحرانی**: بحرانی / بالا / متوسط / پایین
- **دلیل اولویت**: چرا این خطا مهم‌تره؟ (امنیت، عملکرد، UX، ...)
- **توصیه ترتیب رفع**: کدام اول باید رفع بشه (ممکنه رفع یک خطا، خطاهای دیگه رو هم حل کنه)

### ۳. 🔍 تحلیل ریشه‌ای هر خطا
برای هر خطا:
- علت ریشه‌ای (با شماره خط دقیق)
- فایل و محل مشکل
- راه‌حل پیشنهادی

### ۴. 🛠️ برنامه اصلاح یکپارچه
یک برنامه اصلاح منسجم که:
- ترتیب بهینه رفع خطاها رو مشخص کنه
- اگر رفع یک خطا، خطای دیگه‌ای رو هم حل می‌کنه ← مشخص کنه
- فایل‌هایی که باید تغییر کنن با دستورالعمل دقیق

### ۵. 📝 فایل‌های نیاز به تغییر
لیست فایل‌هایی که واقعاً باید تغییر کنن."""

        yield sse("progress", {
            "step": "deep_analysis",
            "message": f"🔬 مدل {primary_model} در حال تحلیل کلی {len(error_messages)} خطا..."
        })

        system_msg = f"""بازرس ارشد کد پروژه. {len(error_messages)} خطا برای تحلیل کلی.
قوانین:
- تحلیل وابستگی و ریشه مشترک خطاها مهم‌ترین بخش کار شماست
- اولویت‌بندی بر اساس: ۱) وابستگی (ریشه‌ای‌ترین خطا اول) ۲) بحرانیت ۳) ترتیب زمانی
- InspectorBridge ابزار inject شده — نادیده بگیرید
- فقط بر اساس شواهد واقعی. حدس نزنید.
- پاسخ فارسی، ساختارمند و جامع."""

        try:
            analysis = await ai_manager.generate(
                model_id=primary_model,
                messages=[
                    Message(role="system", content=system_msg),
                    Message(role="user", content=bulk_investigate_prompt)
                ],
                max_tokens=6000,
                temperature=0.2,
                task_type="debugging"
            )
            report = analysis.content
        except Exception as e:
            yield sse("error", {"message": f"خطا در تحلیل: {str(e)[:100]}"})
            yield sse("done", {"success": False})
            return

        # --- مرحله ۵: بررسی متقابل (اگر مدل دوم هست) ---
        if len(model_ids) > 1:
            second_model = model_ids[1]
            yield sse("progress", {
                "step": "cross_review",
                "message": f"🔄 بررسی متقابل توسط {second_model}..."
            })
            try:
                review = await ai_manager.generate(
                    model_id=second_model,
                    messages=[
                        Message(role="system", content="بازرس متقابل. گزارش همکار را نقادانه بررسی کنید. آیا وابستگی‌ها درست شناسایی شدند؟ آیا اولویت‌بندی منطقی است؟"),
                        Message(role="user", content=f"خطاها:\n{errors_full_context[:3000]}\n\nگزارش:\n{report[:4000]}\n\nتأیید یا اصلاح کنید.")
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                if "تأیید" not in review.content.lower()[:50]:
                    report += f"\n\n---\n### 🔄 نظر تکمیلی ({second_model}):\n{review.content}"
            except Exception:
                pass

        # --- استخراج فایل‌های نیاز به تغییر ---
        files_to_fix = []
        report_lower = report.lower()
        seen = set()
        for path in file_contents.keys():
            if path.lower() in report_lower:
                files_to_fix.append({"path": path, "in_report": True})
                seen.add(path)
        for path in code_files:
            if path not in seen and path.lower() in report_lower:
                files_to_fix.append({"path": path, "in_report": True, "not_read": True})
                seen.add(path)

        yield sse("report", {
            "report": report,
            "model_used": primary_model,
            "models_used": model_ids,
            "files_investigated": list(file_contents.keys()),
            "files_to_fix": files_to_fix,
            "error_content": errors_full_context,
            "github_repo": f"{owner}/{repo}",
            "error_count": len(error_messages),
            "tokens_used": getattr(analysis, 'tokens_used', 0)
        })

        yield sse("done", {"success": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/inspector/fix")
async def fix_error(request: FixRequest, db: Session = Depends(get_db)):
    """
    اصلاح خطا بر اساس گزارش بررسی - ایجاد branch و commit در GitHub
    """
    from fastapi.responses import StreamingResponse
    from ...models.project import Project
    from ...services.github_import import get_github_import_service
    from ...services.github_pr_service import get_github_pr_service
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    if not owner or not repo:
        return {"success": False, "error": "اطلاعات GitHub پروژه یافت نشد"}

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from ...models.setting import Setting as _FixSetting
        token = _FixSetting.get_value(db, "api_key_github") or ""
    model_ids = request.model_ids
    primary_model = model_ids[0] if model_ids else "gemini-2.0-flash"

    async def fix_stream():
        github_svc = get_github_import_service()
        pr_svc = get_github_pr_service()
        ai_manager = get_ai_manager()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield sse("progress", {
            "step": "starting_fix",
            "message": f"🔧 شروع اصلاح خطا توسط {primary_model}..."
        })

        fixed_files = []
        files_to_process = request.files_to_fix if request.files_to_fix else []

        # اگر لیست فایل خالی بود، از AI بخواه استخراج کنه
        if not files_to_process:
            yield sse("progress", {
                "step": "extracting_files",
                "message": "📋 استخراج فایل‌های نیاز به تغییر از گزارش..."
            })

            try:
                extract_resp = await ai_manager.generate(
                    model_id=primary_model,
                    messages=[
                        Message(role="system", content="از گزارش، فقط مسیر فایل‌های نیاز به تغییر را استخراج کنید. هر فایل در یک خط."),
                        Message(role="user", content=request.investigation_report)
                    ],
                    max_tokens=300,
                    temperature=0.1
                )
                for line in extract_resp.content.strip().split("\n"):
                    line = line.strip().strip("`").strip("- ").strip()
                    if line and ("/" in line or "." in line) and len(line) < 200:
                        files_to_process.append({"path": line})
            except Exception:
                pass

        if not files_to_process:
            yield sse("error", {"message": "هیچ فایلی برای اصلاح شناسایی نشد"})
            yield sse("done", {"success": False})
            return

        # --- خواندن فایل‌های فعلی و تولید نسخه اصلاح شده ---
        for i, file_info in enumerate(files_to_process):
            file_path = file_info.get("path", "")
            if not file_path:
                continue

            yield sse("progress", {
                "step": "fixing_file",
                "message": f"📝 مدل {primary_model} در حال اصلاح {file_path}... ({i + 1}/{len(files_to_process)})",
                "model": primary_model,
                "file": file_path
            })

            # خواندن فایل فعلی
            try:
                file_result = await github_svc.get_file_content(owner, repo, file_path, token=token)
                if not file_result.get("success"):
                    yield sse("progress", {
                        "step": "file_not_found",
                        "message": f"⚠️ فایل {file_path} پیدا نشد، رد شد"
                    })
                    continue

                current_content = file_result.get("content", "")
                file_sha = file_result.get("sha", "")

            except Exception as e:
                yield sse("progress", {
                    "step": "read_error",
                    "message": f"⚠️ خطا در خواندن {file_path}: {str(e)[:60]}"
                })
                continue

            # از AI بخواه فایل رو اصلاح کنه
            fix_prompt = f"""فایل زیر را بر اساس گزارش بررسی اصلاح کنید.

## خطا:
{request.error_message}

## گزارش بررسی (مرتبط با این فایل):
{request.investigation_report[:3000]}

## محتوای فعلی {file_path}:
```
{current_content}
```

## وظیفه:
فقط محتوای کامل فایل اصلاح شده را بنویسید. هیچ توضیح اضافی ندهید.
کد را در بلوک ``` قرار دهید."""

            try:
                fix_response = await ai_manager.generate(
                    model_id=primary_model,
                    messages=[
                        Message(role="system", content="شما توسعه‌دهنده ارشد هستید. فقط کد اصلاح شده را برگردانید. فایل InspectorBridge مربوط به سیستم دیباگ inject شده است - هرگز آن را تغییر ندهید."),
                        Message(role="user", content=fix_prompt)
                    ],
                    max_tokens=8000,
                    temperature=0.2,
                    task_type="code_generation"
                )

                # 🧹 حذف بلوک‌های استدلال/reasoning (لایه ایمنی)
                fixed_content = _strip_reasoning_blocks(fix_response.content.strip())

                # استخراج کد از آخرین بلوک کد (نه اولین — ممکنه reasoning هم بلوک کد داشته باشه)
                if "```" in fixed_content:
                    import re as _fix_re
                    # پیدا کردن همه بلوک‌های کد
                    _code_blocks = _fix_re.findall(r'```[\w]*\n(.*?)```', fixed_content, _fix_re.DOTALL)
                    if _code_blocks:
                        # آخرین بلوک کد = خروجی واقعی (نه مثال‌های میانی)
                        fixed_content = _code_blocks[-1].strip()

                # 🛡️ پاکسازی نهایی محتوا
                fixed_content = _sanitize_file_content(fixed_content, file_path)

                if fixed_content and fixed_content != current_content:
                    # 🛡️ بررسی آلودگی reasoning قبل از commit
                    _contamination = _detect_reasoning_contamination(fixed_content, file_path)
                    if _contamination:
                        yield sse("progress", {
                            "step": "contamination_blocked",
                            "message": f"🛡️ محتوای آلوده بلاک شد: {_contamination[:100]}"
                        })
                    else:
                        fixed_files.append({
                            "path": file_path,
                            "content": fixed_content,
                            "original_size": len(current_content),
                            "fixed_size": len(fixed_content)
                        })
                        yield sse("progress", {
                            "step": "file_fixed",
                            "message": f"✅ فایل {file_path} اصلاح شد"
                        })
                else:
                    yield sse("progress", {
                        "step": "no_change",
                        "message": f"ℹ️ تغییری در {file_path} لازم نبود"
                    })

            except Exception as e:
                yield sse("progress", {
                    "step": "fix_error",
                    "message": f"⚠️ خطا در اصلاح {file_path}: {str(e)[:60]}"
                })

            await asyncio.sleep(0.3)

        if not fixed_files:
            yield sse("error", {"message": "هیچ فایلی اصلاح نشد"})
            yield sse("done", {"success": False})
            return

        # --- ایجاد branch و commit در GitHub ---
        branch_name = f"inspector-fix-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        yield sse("progress", {
            "step": "creating_branch",
            "message": f"🌿 ایجاد branch: {branch_name}..."
        })

        try:
            # ایجاد branch
            branch_result = await pr_svc.create_branch(
                owner=owner,
                repo=repo,
                new_branch=branch_name,
                token=token
            )

            if not branch_result.get("success"):
                yield sse("error", {"message": f"خطا در ایجاد branch: {branch_result.get('error', '')}"})
                yield sse("done", {"success": False})
                return

            # commit فایل‌ها
            for i, f in enumerate(fixed_files):
                yield sse("progress", {
                    "step": "committing",
                    "message": f"💾 ذخیره تغییرات {f['path']}... ({i + 1}/{len(fixed_files)})"
                })

                commit_result = await pr_svc.create_or_update_file(
                    owner=owner,
                    repo=repo,
                    path=f["path"],
                    content=f["content"],
                    message=f"fix: Inspector auto-fix for {f['path']}",
                    branch=branch_name,
                    token=token
                )

                if not commit_result.get("success"):
                    yield sse("progress", {
                        "step": "commit_error",
                        "message": f"⚠️ خطا در commit {f['path']}: {commit_result.get('error', '')[:60]}"
                    })

            # ایجاد PR
            yield sse("progress", {
                "step": "creating_pr",
                "message": "📝 ایجاد Pull Request..."
            })

            pr_result = await pr_svc.create_pull_request(
                owner=owner,
                repo=repo,
                title=f"🔧 Inspector Fix: {request.error_message[:60]}",
                body=f"## اصلاح خودکار بازرس ویژه\n\n**خطا:**\n{request.error_message}\n\n**فایل‌های اصلاح شده:**\n" +
                     "\n".join(f"- `{f['path']}`" for f in fixed_files) +
                     f"\n\n---\n*اصلاح شده توسط مدل: {primary_model}*",
                head_branch=branch_name,
                token=token
            )

            pr_url = pr_result.get("pr_url", "")

            yield sse("fix_complete", {
                "success": True,
                "branch": branch_name,
                "pr_url": pr_url,
                "fixed_files": [f["path"] for f in fixed_files],
                "model_used": primary_model,
                "message": f"✅ اصلاح کامل شد! {len(fixed_files)} فایل در branch {branch_name} اصلاح شد."
                           + (f"\n🔗 Pull Request: {pr_url}" if pr_url else "")
                           + "\n\n🧪 الان برو اون قسمت رو تست کن!"
            })

        except Exception as e:
            yield sse("error", {"message": f"خطا در عملیات GitHub: {str(e)[:100]}"})

        yield sse("done", {"success": True})

    return StreamingResponse(
        fix_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================
# 🧠 چت هوشمند - Smart Chat (پس از بررسی/اصلاح)
# ============================================

class SmartChatReplyContext(BaseModel):
    """context پیام ریپلای‌شده"""
    message_id: str
    content: str
    role: str
    model_id: Optional[str] = None
    context_messages: Optional[List[dict]] = None  # پیام‌های اطراف (بدون محدودیت 50 تایی)


class SmartChatRequest(BaseModel):
    """درخواست چت هوشمند با context کامل جلسه"""
    project_id: str
    model_ids: List[str]
    message: str
    chat_history: Optional[List[InspectorChatMessage]] = None
    backend_logs: Optional[List[dict]] = None
    frontend_url: Optional[str] = None
    reply_to: Optional[SmartChatReplyContext] = None  # ریپلای به پیام خاص
    previously_read_files: Optional[List[str]] = None  # فایل‌هایی که قبلاً در مکالمه خوانده شدن
    # 🆕 (inspector-scan, audit C2 fix) — context اضافی برای intent resolver.
    # کاربر گفت screenshots/console/URL هم در دسترس inspector chat است.
    # این فیلدها optional اند و فقط برای بهبود تشخیص intent استفاده می‌شوند.
    console_logs: Optional[List[dict]] = None
    page_url: Optional[str] = None
    api_paths: Optional[List[str]] = None
    linked_task: Optional[dict] = None
    screenshots: Optional[List[dict]] = None
    inspector_mode: Optional[str] = None  # "chat" | "visual_debug"
    # 🆕 (v3 regression fix) — flag برای skip کردن intent detection.
    # وقتی frontend در حالت stepwise execution است، هر step را پشت سرهم
    # به smart-chat می‌فرستد. اگر intent detection این پیام‌ها را
    # scan_initiated کند، executeMultiStep response را نمی‌فهمد و
    # هیچ action_plan ای تولید نمی‌شود. این flag از این conflict جلوگیری
    # می‌کند. default True (رفتار v3 معمولی).
    enable_selective_scan: bool = True
    # 🔗 (Bug C7 — Bridge Phase 2) — اتصال به تسک مرکز نظارت
    # اگر داده شود، system prompt شامل بلوک «🎯 کانتکست تسک متصل» می‌شود با
    # acceptance_criteria + remaining_parts + task_steps + done_parts + scan_metadata.
    # backward compatible: None یعنی chat آزاد مثل قبل.
    task_id: Optional[str] = None
    # 🆕 (anti-stuck-loop) — اگر این retry است (یعنی کاربر روی «درخواست
    # مجدد اصلاح» کلیک کرد چون پاسخ قبلی action_plan نداشت)، شمارهٔ تلاش
    # را اینجا بگذار. backend بر اساس این:
    #   - فایل‌خوانی را skip می‌کند (از previously_read_files استفاده می‌کند)
    #   - system prompt را قوی‌تر می‌کند که حتماً action_plan تولید شود
    #   - در retry≥2 خودکار به fallback model سوئیچ می‌کند
    retry_attempt: Optional[int] = None


class ApplyActionRequest(BaseModel):
    """درخواست اجرای اکشن پیشنهادی"""
    project_id: str
    model_ids: List[str]
    action_description: str
    action_files: List[dict]  # [{path, content, operation: 'modify'|'create'|'delete'|'modify_sections', sections?: [{find, replace}]}]
    commit_message: str
    original_message: str  # پیام اصلی کاربر
    # 🔗 (Bug C7 — Bridge Phase 1+3) — اتصال به تسک مرکز نظارت برای write-back.
    # اگر داده شود، پس از موفقیت apply:
    #   - verify v6 stack روی تسک اجرا می‌شود
    #   - task.action_plan و task.applied_evidence به‌روز می‌شوند
    #   - اگر verify=done، task.verification_status به done می‌رود
    #   - event "task.applied_via_inspector" emit می‌شود
    task_id: Optional[str] = None
    # 🆕 (v3 render-ops) — operations مدیریتی Render که AI می‌تواند پیشنهاد دهد
    # وقتی RENDER_API_KEY تنظیم است. این operations بعد از file commits
    # اجرا می‌شوند.
    # نمونه:
    # [
    #   {"type": "set_env_var", "service_name": "lifemanager", "key": "DATABASE_URL", "value": "..."},
    #   {"type": "restart_service", "service_name": "lifemanager"},
    #   {"type": "trigger_deploy", "service_name": "lifemanager"},
    # ]
    render_actions: Optional[List[dict]] = None
    # 🆕 (review-gate) — اگر smart-chat plan رو با review_blocked=True
    # برگردونده، apply-action باید بدون این acknowledgement رد بشه.
    # frontend بعد از نمایش confirm dialog به کاربر، این flag رو set می‌کنه.
    review_acknowledged: bool = False
    review_critical_signals: Optional[List[str]] = None


class ScreenshotRequest(BaseModel):
    """درخواست عکس‌برداری از صفحه پیش‌نمایش"""
    project_id: str
    url: str  # آدرس صفحه پیش‌نمایش
    viewport_width: int = 1280
    viewport_height: int = 720
    full_page: bool = False
    html_content: Optional[str] = None  # DOM snapshot از iframe (برای SPA بدون تغییر URL)


class VisualDebugRequest(BaseModel):
    """درخواست دیباگ بصری با عکس و لاگ"""
    project_id: str
    model_ids: List[str]  # مدل‌های انتخاب شده (باید vision داشته باشند)
    screenshots: List[str]  # base64 تصاویر
    screenshot_packs: Optional[List[dict]] = None  # 📦 [{index, pageUrl, timestamp, console_logs, backend_logs, related_urls}]
    console_logs: Optional[List[dict]] = None  # [{level, message, timestamp, source}]
    backend_logs: Optional[List[dict]] = None  # [{level, message, timestamp, service_id}]
    related_urls: Optional[List[str]] = None  # آدرس‌های مرتبط
    user_description: Optional[str] = None  # توضیح اختیاری کاربر
    chat_history: Optional[List[InspectorChatMessage]] = None
    previously_read_files: Optional[List[str]] = None


# ─────────────────────────────────────────────────────────────────────────────
# 🔗 Bug C7 — Inspector ↔ Oversight Bridge helpers
# ─────────────────────────────────────────────────────────────────────────────


def _build_task_context_block(task_id: str, *, max_size_bytes: int = 30_000) -> Optional[str]:
    """ساخت بلوک متنی کانتکست تسک برای تزریق به system prompt smart-chat.

    اولویت‌بندی برای cap (در صورت رسیدن به max_size_bytes):
      1) remaining_parts (مهم‌ترین — آنچه هنوز باید انجام شود)
      2) acceptance_criteria
      3) task prompt
      4) chat history / inspector_context

    خروجی: متن بلوک یا None اگر تسک پیدا نشد.
    """
    try:
        from ...services.oversight_service import get_oversight_service
        svc = get_oversight_service()
        task = next((t for t in svc.tasks if t.id == task_id), None)
        if task is None:
            return None

        last_report = next(
            (r for r in svc.reports if r.task_id == task_id), None
        )

        lines: List[str] = []
        lines.append("## 🎯 کانتکست تسک متصل")
        lines.append(
            "شما در حال کار روی تسک زیر از مرکز نظارت هستید. "
            "هرگز از حیطهٔ این تسک خارج نشوید — پاسخ شما باید مستقیماً "
            "به انجام acceptance criteria یا remaining_parts منجر شود."
        )
        lines.append("")
        lines.append(f"### عنوان تسک")
        lines.append(f"{task.title}")
        lines.append("")
        lines.append(f"**وضعیت verify**: {task.verification_status or 'pending'}")
        lines.append(f"**اولویت**: {task.priority}")
        lines.append(f"**نوع**: {task.type}")
        lines.append("")

        # 1) remaining_parts (بالاترین اولویت)
        remaining_parts = []
        if last_report and getattr(last_report, "remaining_parts", None):
            remaining_parts = list(last_report.remaining_parts)
        if remaining_parts:
            lines.append("### ⚠️ remaining_parts (تمرکز روی این‌ها)")
            for i, rp in enumerate(remaining_parts, 1):
                rp_text = str(rp).strip()
                if rp_text:
                    lines.append(f"  {i}. {rp_text}")
            lines.append("")

        # 2) acceptance_criteria
        ac_list = list(task.acceptance_criteria or [])
        if ac_list:
            lines.append("### acceptance_criteria")
            for i, ac in enumerate(ac_list, 1):
                if isinstance(ac, dict):
                    ac_text = ac.get("text", "") or str(ac)
                else:
                    ac_text = str(ac)
                if ac_text.strip():
                    lines.append(f"  {i}. {ac_text.strip()}")
            lines.append("")

        # 3) target_files
        target_files = list(task.target_files or [])
        if target_files:
            lines.append("### فایل‌های هدف (target_files)")
            for tf in target_files[:50]:
                lines.append(f"  - {tf}")
            lines.append("")

        # 4) task_steps با وضعیت
        task_steps = list(task.task_steps or [])
        if task_steps:
            lines.append("### مراحل تسک (task_steps)")
            for s in task_steps[:50]:
                if not isinstance(s, dict):
                    continue
                _status = s.get("status", "pending")
                _title = (s.get("title") or s.get("scope") or "").strip()
                _icon = {
                    "done": "✅", "partial": "🔶",
                    "not_done": "❌", "pending": "⬜",
                }.get(_status, "⬜")
                lines.append(f"  {_icon} [{_status}] {_title[:120]}")
            lines.append("")

        # 5) done_parts (تأیید آنچه انجام شده — تا overwrite نشود)
        done_parts = []
        if last_report and getattr(last_report, "done_parts", None):
            done_parts = list(last_report.done_parts)
        if done_parts:
            lines.append("### ✓ done_parts (قبلاً انجام شده — دوباره تکرار نکنید)")
            for dp in done_parts[:30]:
                dp_text = str(dp).strip()
                if dp_text:
                    lines.append(f"  - {dp_text[:200]}")
            lines.append("")

        # 6) task prompt (پایین‌ترین اولویت)
        if task.prompt:
            lines.append("### متن کامل تسک")
            lines.append(task.prompt[:5000])
            lines.append("")

        # 7) scan_metadata
        scan_meta = getattr(task, "created_by_scan_metadata", None) or {}
        if scan_meta:
            lines.append("### scan_metadata")
            for k in ("model", "depth", "passes", "files_count", "scan_id", "scanned_at"):
                v = scan_meta.get(k)
                if v:
                    lines.append(f"  - {k}: {v}")
            lines.append("")

        full_text = "\n".join(lines)

        # cap با اولویت — اگر بیشتر از max شد، از انتها (prompt + scan_metadata) کم کن
        if len(full_text.encode("utf-8")) > max_size_bytes:
            # تلاش با حذف بخش‌های پایین‌اولویت
            essential_lines: List[str] = []
            for ln in lines:
                essential_lines.append(ln)
                if "### scan_metadata" in ln or "### متن کامل تسک" in ln:
                    # پس از این بخش‌ها cut کن
                    if len("\n".join(essential_lines).encode("utf-8")) > max_size_bytes:
                        break
            full_text = "\n".join(essential_lines)
            # اگر هنوز بزرگ است، truncate نهایی
            if len(full_text.encode("utf-8")) > max_size_bytes:
                full_text = full_text.encode("utf-8")[:max_size_bytes].decode(
                    "utf-8", errors="ignore"
                ) + "\n... [truncated due to size]"

        return full_text
    except Exception as _e:
        logger.warning(f"_build_task_context_block failed: {_e}")
        return None


def _build_memory_block(
    project_id: str,
    db: Session,
    *,
    max_size_bytes: int = 10_000,
) -> tuple[Optional[str], int]:
    """🆕 (C7v2 Section 2) ساخت بلوک «🧠 حافظهٔ ثابت پروژه» برای تزریق به system prompt.

    فیلدهای فعال (is_active=true, archived=false) دستهٔ memory برای project
    خوانده می‌شوند، sort بر اساس priority desc.

    Returns: (block_text, fields_count). در صورت نبودن فیلد → (None, 0).
    """
    try:
        from ...models.inspector_prompt_field import InspectorPromptField
        from sqlalchemy import or_

        fields = (
            db.query(InspectorPromptField)
            .filter(
                InspectorPromptField.project_id == project_id,
                InspectorPromptField.category == "memory",
                InspectorPromptField.is_active == True,  # noqa: E712
                or_(
                    InspectorPromptField.archived.is_(None),
                    InspectorPromptField.archived == False,  # noqa: E712
                ),
            )
            .order_by(InspectorPromptField.priority.desc())
            .all()
        )
        if not fields:
            return None, 0

        lines: List[str] = []
        lines.append("## 🧠 حافظهٔ ثابت پروژه (همیشه فعال — حتماً رعایت کن)")
        lines.append(
            "این موارد، واقعیت‌های ثابت پروژه‌اند که در هر تصمیم باید مدنظر باشند:"
        )
        lines.append("")
        for f in fields:
            lines.append(f"### {f.title}")
            lines.append((f.content or "").strip())
            lines.append("")

        block = "\n".join(lines)
        # cap به max_size_bytes (با truncation از انتها)
        if len(block.encode("utf-8")) > max_size_bytes:
            block = block.encode("utf-8")[:max_size_bytes].decode(
                "utf-8", errors="ignore"
            ) + "\n... [memory truncated]"
        return block, len(fields)
    except Exception as _e:
        logger.warning(f"_build_memory_block failed: {_e}")
        return None, 0


def _build_training_block(
    project_id: str,
    db: Session,
    *,
    max_size_bytes: int = 15_000,
) -> tuple[Optional[str], int]:
    """🆕 (C7v2 Section 3) ساخت بلوک «📚 آموزش‌های پروژه» برای تزریق به system prompt.

    فیلدهای فعال (is_active=true, archived=false) دستهٔ training برای
    project خوانده می‌شوند، sort بر اساس priority desc.

    Returns: (block_text, fields_count).
    """
    try:
        from ...models.inspector_prompt_field import InspectorPromptField
        from sqlalchemy import or_

        fields = (
            db.query(InspectorPromptField)
            .filter(
                InspectorPromptField.project_id == project_id,
                InspectorPromptField.category == "training",
                InspectorPromptField.is_active == True,  # noqa: E712
                or_(
                    InspectorPromptField.archived.is_(None),
                    InspectorPromptField.archived == False,  # noqa: E712
                ),
            )
            .order_by(InspectorPromptField.priority.desc())
            .all()
        )
        if not fields:
            return None, 0

        lines: List[str] = []
        lines.append("## 📚 آموزش‌های پروژه (الگوها و کانوانشن‌ها — به آن‌ها مراجعه کن)")
        lines.append(
            "هرگاه در حل تسک به این الگوها برخوردی، با همین روش پیش برو:"
        )
        lines.append("")
        for f in fields:
            lines.append(f"### {f.title}")
            lines.append((f.content or "").strip())
            lines.append("")

        block = "\n".join(lines)
        if len(block.encode("utf-8")) > max_size_bytes:
            block = block.encode("utf-8")[:max_size_bytes].decode(
                "utf-8", errors="ignore"
            ) + "\n... [training truncated]"
        return block, len(fields)
    except Exception as _e:
        logger.warning(f"_build_training_block failed: {_e}")
        return None, 0


async def _verify_task_via_v6_stack(task_id: str) -> Optional[Dict[str, Any]]:
    """اجرای verify v6 stack روی یک تسک پس از apply موفق در inspector.

    استفاده از همان مسیر oversight_verifier.verify_task که از قبل v6
    integration دارد (build_verify_context + iterative_verify_step +
    reconciliation). در فایل خاص inspector، فقط wrapper روی این صدا
    می‌زنیم تا apply-action ساده بماند.

    خروجی: dict با verdict + confidence + report_id (یا None اگر شکست خورد)
    """
    try:
        from ...services.oversight_verifier import verify_task as _ovt
        result = await _ovt(
            task_id=task_id,
            triggered_by="inspector_apply",
            include_runtime=False,  # فقط static (سریع — runtime probes بعداً اگر لازم)
            verify_v6=True,
        )
        if not isinstance(result, dict):
            return None
        task_dict = result.get("task") or {}
        report_dict = result.get("report") or {}
        return {
            "verdict": task_dict.get("verification_status"),
            "report_id": report_dict.get("id"),
            "done_parts_count": len(report_dict.get("done_parts") or []),
            "remaining_parts_count": len(report_dict.get("remaining_parts") or []),
            "verify_version": report_dict.get("verify_version") or "v6",
            "config_used": report_dict.get("config_used"),
        }
    except Exception as _e:
        logger.warning(f"_verify_task_via_v6_stack failed: {_e}")
        return None


async def _writeback_task_after_apply(
    task_id: str,
    *,
    pr_url: Optional[str],
    branch: Optional[str],
    files_committed: List[str],
    commit_message: str,
    model_ids: List[str],
) -> bool:
    """به‌روزرسانی تسک مرکز نظارت پس از apply موفق در inspector.

    - task.action_plan با خلاصهٔ apply
    - task.applied_evidence با pr_url + files + models
    - emit event task.applied_via_inspector
    """
    try:
        from ...services.oversight_service import get_oversight_service
        from datetime import datetime as _dt_wb
        svc = get_oversight_service()
        task = next((t for t in svc.tasks if t.id == task_id), None)
        if task is None:
            logger.warning(f"writeback: task {task_id} not found")
            return False

        # action_plan (یک خلاصهٔ structured که قابل خواندن باشد)
        try:
            task.action_plan = {
                "applied_via": "inspector_smart_chat",
                "applied_at": _dt_wb.utcnow().isoformat() + "Z",
                "commit_message": commit_message[:300],
                "files_committed": list(files_committed)[:50],
                "pr_url": pr_url or "",
                "branch": branch or "",
                "models_used": list(model_ids)[:10],
            }
        except Exception:
            pass

        # applied_evidence
        try:
            evidence = dict(task.applied_evidence or {})
            evidence["pr_url"] = pr_url or evidence.get("pr_url", "")
            evidence["pr_branch"] = branch or evidence.get("pr_branch", "")
            evidence["files_committed"] = list(files_committed)[:50]
            evidence["model_ids"] = list(model_ids)[:10]
            evidence["executed_via"] = "inspector"
            evidence["executed_at"] = _dt_wb.utcnow().isoformat() + "Z"
            evidence["action_plan_summary"] = commit_message[:200]
            task.applied_evidence = evidence
        except Exception:
            pass

        # updated_at
        try:
            from ...services.oversight_service import now_iso as _now_iso_wb
            task.updated_at = _now_iso_wb()
        except Exception:
            pass

        try:
            svc._save_tasks()
        except Exception as _se:
            logger.debug(f"writeback save_tasks: {_se}")

        # emit event (best-effort)
        try:
            await svc._emit(
                "task.applied_via_inspector",
                {
                    "task_id": task_id,
                    "pr_url": pr_url,
                    "branch": branch,
                    "files_committed": list(files_committed)[:20],
                    "model_ids": list(model_ids)[:5],
                },
            )
        except Exception as _ee:
            logger.debug(f"writeback emit failed: {_ee}")

        return True
    except Exception as _e:
        logger.warning(f"_writeback_task_after_apply failed: {_e}")
        return False


def _parse_ai_selected_files(ai_response: str, valid_files: list, max_files: int = 10) -> list:
    """
    پارس پاسخ AI برای استخراج مسیر فایل‌ها با پشتیبانی از فرمت‌های مختلف:
    - لیست شماره‌دار: 1. src/app/page.tsx
    - بولت: - src/app/page.tsx / * src/app/page.tsx
    - بولد: **src/app/page.tsx**
    - بکتیک: `src/app/page.tsx`
    - کوتیشن: "src/app/page.tsx"
    - با توضیح: src/app/page.tsx (main page)
    """
    selected = []
    for line in ai_response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # حذف شماره‌گذاری: "1. path" یا "1) path"
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        # حذف بولت‌ها: - * • ▸ →
        line = line.lstrip('-*•▸▹◆◇→').strip()
        # حذف backtick، کوتیشن، بولد/ایتالیک
        line = line.strip('`"\'*_ \t')
        # اگر بعد از مسیر توضیح اضافه باشه، حذفش کن
        for sep in [' - ', ' — ', ' :', '\t']:
            if sep in line:
                line = line.split(sep)[0].strip()
        if '(' in line and line.index('(') > 3:
            line = line.split('(')[0].strip()
        # پاکسازی نهایی
        line = line.strip('`"\'*_ \t')
        if line in valid_files:
            selected.append(line)
            if len(selected) >= max_files:
                break
    return selected


def _fallback_file_selection(code_files: list, context_text: str, max_files: int = 5) -> list:
    """
    فالبک انتخاب فایل وقتی AI نتونسته فایلی match کنه.
    ۱) keyword matching از متن درخواست/خطا
    ۲) فایل‌های اصلی پروژه (app, index, main, page, layout)
    """
    selected = []
    # استراتژی ۱: تطبیق کلمات کلیدی با نام فایل
    words = set(w.lower() for w in context_text.split() if len(w) > 3)
    for cf in code_files[:300]:
        cf_name = cf.split("/")[-1].lower()
        if any(w in cf_name for w in words):
            selected.append(cf)
        if len(selected) >= max_files:
            return selected
    # استراتژی ۲: فایل‌های اصلی پروژه
    if not selected:
        priority_patterns = [
            "app.", "index.", "main.", "page.", "layout.", "error.", "_app.", "routes.",
            "server.", "api.", "config.", "store.", "hooks.", "utils.", "components.",
            "middleware.", "schema.", "models.", "service.", "context."
        ]
        for cf in code_files:
            name = cf.split("/")[-1].lower()
            if any(p in name for p in priority_patterns):
                selected.append(cf)
            if len(selected) >= max_files:
                break
    return selected


def _extract_file_paths_from_text(text: str, code_files: list) -> list:
    """
    استخراج مسیر فایل‌ها از متن خطا، stack trace، و پیام کاربر.
    هر مسیری که در لیست فایل‌های واقعی پروژه (code_files) وجود داشته باشه
    برگردانده میشه — اینجوری مطمئنیم فایل‌های ذکر شده در خطا حتماً خونده میشن.
    """
    if not text or not code_files:
        return []

    found = set()
    code_files_set = set(code_files)

    # ۱) Python stack trace: File "path/to/file.py", line 123
    for m in re.finditer(r'File\s+"([^"]+)"', text):
        found.add(m.group(1))

    # ۲) Node.js / JS stack trace: at Something (path/to/file.js:123:45) or at path/to/file.js:123
    for m in re.finditer(r'at\s+(?:[\w.<>]+\s+)?\(?([^\s()]+\.\w{1,5})(?::\d+){0,2}\)?', text):
        found.add(m.group(1))

    # ۳) Webpack/Next.js errors: ./src/components/Foo.tsx or Error in ./path
    for m in re.finditer(r'(?:Error in\s+|Module not found[^\"]*[\'"]|from\s+[\'"]|import\s+[\'"])?\.\/([^\s\'"`,;)]+\.\w{1,5})', text):
        found.add(m.group(1))

    # ۴) Explicit file paths with common extensions (src/..., backend/..., app/..., pages/..., etc.)
    for m in re.finditer(
        r'(?:^|\s|[\'"`(,|])(((?:src|backend|frontend|app|pages|components|lib|utils|services|api|routes|models|config|public|scripts|hooks|store|context|middleware|types|interfaces|styles|assets|tests?|__tests__|spec)(?:/[\w.\-]+)+\.[\w]{1,5}))',
        text
    ):
        found.add(m.group(2))

    # ۵) Generic path patterns: any/thing/with/slashes.ext (at least 2 parts)
    for m in re.finditer(r'(?:^|\s|[\'"`(,|])([\w][\w.\-]*/[\w.\-/]+\.(?:py|js|jsx|ts|tsx|vue|css|scss|html|json|yaml|yml|toml|cfg|env|md|sql|go|rs|rb|php|java|kt|swift|sh|bash))', text):
        found.add(m.group(1))

    # حالا مسیرهای پیدا شده رو با لیست واقعی فایل‌های پروژه مطابقت بده
    matched = []
    for raw_path in found:
        # پاکسازی
        clean = raw_path.strip().strip("'\"`,;)( ").rstrip(".")
        if not clean:
            continue

        # مطابقت دقیق
        if clean in code_files_set:
            matched.append(clean)
            continue

        # مطابقت suffix — شاید مسیر نسبی باشه (مثلاً خطا فقط app/api/routes/foo.py گفته ولی full path بلندتره)
        for cf in code_files:
            if cf.endswith("/" + clean) or cf == clean:
                matched.append(cf)
                break

    return list(dict.fromkeys(matched))  # حذف تکراری با حفظ ترتیب


def _strip_reasoning_blocks(text: str) -> str:
    """
    حذف بلوک‌های استدلال (reasoning/thinking) از پاسخ مدل‌ها.
    دلیگیت به ماژول مرکزی content_sanitizer.
    """
    from ...services.content_sanitizer import strip_reasoning_blocks as _central_strip
    return _central_strip(text)


def _sanitize_file_content(content: str, file_path: str) -> str:
    """
    پاکسازی محتوای فایل از آلودگی reasoning/markdown قبل از نوشتن یا commit.
    دلیگیت به ماژول مرکزی content_sanitizer.
    """
    from ...services.content_sanitizer import sanitize_file_content as _central_sanitize
    return _central_sanitize(content, file_path)


# --- الگوهای آلودگی reasoning در کد منبع (دلیگیت به ماژول مرکزی) ---
from ...services.content_sanitizer import REASONING_CONTAMINATION_PATTERNS as _REASONING_CONTAMINATION_PATTERNS


def _detect_reasoning_contamination(content: str, file_path: str) -> str | None:
    """
    بررسی آلودگی محتوای فایل با خروجی reasoning مدل‌های AI.
    دلیگیت به ماژول مرکزی content_sanitizer.
    """
    from ...services.content_sanitizer import detect_reasoning_contamination as _central_detect
    return _central_detect(content, file_path)


def _normalize_ask_user(raw: dict) -> dict | None:
    """نرمال‌سازی بلوک ask_user — برمی‌گرداند dict تمیز یا None اگر نامعتبر."""
    if not raw or not isinstance(raw, dict):
        return None
    question = (raw.get("question") or "").strip()
    qtype = (raw.get("type") or "single").strip().lower()
    if qtype not in ("single", "multi", "text"):
        qtype = "single"
    if not question:
        return None
    options_raw = raw.get("options") or []
    options = []
    if qtype in ("single", "multi"):
        if not isinstance(options_raw, list) or len(options_raw) < 2:
            return None
        seen_ids = set()
        for idx, opt in enumerate(options_raw):
            if not isinstance(opt, dict):
                continue
            opt_id = (opt.get("id") or f"opt_{idx}").strip()
            if not opt_id or opt_id in seen_ids:
                opt_id = f"opt_{idx}_{len(seen_ids)}"
            seen_ids.add(opt_id)
            label = (opt.get("label") or opt.get("title") or "").strip()
            if not label:
                continue
            options.append({
                "id": opt_id,
                "label": label,
                "description": (opt.get("description") or "").strip(),
            })
        if len(options) < 2:
            return None
    out = {
        "question": question,
        "type": qtype,
        "context": (raw.get("context") or "").strip(),
    }
    if options:
        out["options"] = options
    default_id = (raw.get("default") or "").strip()
    if default_id and qtype in ("single", "multi"):
        if any(o["id"] == default_id for o in options):
            out["default"] = default_id
    return out


def _normalize_route_to(parsed: dict) -> dict | None:
    """نرمال‌سازی بلوک route_to."""
    target = (parsed.get("route_to") or "").strip().lower()
    if target not in ("deep_scan",):
        return None
    return {
        "target": target,
        "reason": (parsed.get("reason") or "").strip(),
        "scan_config": parsed.get("scan_config") if isinstance(parsed.get("scan_config"), dict) else {},
    }


def _normalize_action_plan_json(parsed: dict) -> dict | None:
    """
    نرمال‌سازی فرمت‌های مختلف action_plan JSON.
    مدل‌ها گاهی فرمت‌های متفاوتی برمی‌گردونن — اینجا همه رو به فرمت استاندارد تبدیل می‌کنیم.
    فرمت استاندارد: {"files": [{"path": ..., "content": ..., "operation": ...}], "commit_message": ...}

    🆕 پشتیبانی از ask_user و route_to:
    - اگر parsed["ask_user"] معتبر باشد → برگردان {"ask_user": {...}, "commit_message": ""}
    - اگر parsed["route_to"] معتبر باشد → برگردان {"route_to": {...}, "commit_message": ""}
    """
    if not parsed or not isinstance(parsed, dict):
        return None

    # 🆕 ask_user — اولویت بالاتر از files (اگر هر دو بود، ask_user جلوست)
    if parsed.get("ask_user"):
        norm_q = _normalize_ask_user(parsed["ask_user"])
        if norm_q:
            return {
                "ask_user": norm_q,
                "commit_message": "",
            }

    # 🆕 route_to — مسیریابی به deep_scan
    if parsed.get("route_to"):
        norm_r = _normalize_route_to(parsed)
        if norm_r:
            return {
                "route_to": norm_r,
                "commit_message": "",
            }

    files = None

    # فرمت استاندارد: {"files": [...]}
    if parsed.get("files") and isinstance(parsed["files"], list) and len(parsed["files"]) > 0:
        files = parsed["files"]

    # فرمت جایگزین ۱: {"action_plan": [{"action": "UPDATE_FILE", "file_path": ..., "content": ...}]}
    # یا: {"action_plan": [{"type": "file_update", "file_path": ..., "content": ...}]}
    elif parsed.get("action_plan") and isinstance(parsed["action_plan"], list) and len(parsed["action_plan"]) > 0:
        files = []
        for item in parsed["action_plan"]:
            if not isinstance(item, dict):
                continue
            # فقط آیتم‌هایی که فایل هستن (نه دستورات command)
            item_type = (item.get("type") or item.get("action") or "").lower()
            if item_type in ("command", "run_command", "shell"):
                continue  # دستور shell — در action_plan فایلی جای نداره
            file_path = item.get("file_path") or item.get("path") or ""
            content = item.get("content") or ""
            sections = item.get("sections")
            # modify_sections: فایل بخشی — sections بجای content
            if file_path and sections and item_type in ("modify_sections",):
                files.append({
                    "path": file_path,
                    "operation": "modify_sections",
                    "sections": sections,
                    "description": item.get("description", ""),
                })
            elif file_path and content:
                files.append({
                    "path": file_path,
                    "content": content,
                    "operation": "create" if item_type in ("create_file", "create") else "modify",
                    "description": item.get("description", ""),
                })

    # فرمت جایگزین ۲: {"action_plan": {"files": [...]}}
    elif parsed.get("action_plan") and isinstance(parsed["action_plan"], dict):
        inner = parsed["action_plan"]
        if inner.get("files") and isinstance(inner["files"], list):
            files = inner["files"]

    # فرمت جایگزین ۳: [{"path": ..., "content": ...}] — لیست مستقیم
    # (handled if parsed itself is a list — but parsed is always dict here)

    if not files or len(files) == 0:
        return None

    # اعتبارسنجی: هر فایل باید path و (content یا sections) داشته باشه
    valid_files = [
        f for f in files
        if f.get("path") and (
            f.get("content")  # فایل‌های معمولی (modify/create)
            or (f.get("operation", "").lower() == "modify_sections" and f.get("sections"))  # فایل‌های بخشی
        )
    ]
    if not valid_files:
        return None

    # 🛡️ پاکسازی محتوای فایل‌ها از آلودگی reasoning/markdown
    for f in valid_files:
        if f.get("content") and f.get("path"):
            f["content"] = _sanitize_file_content(f["content"], f["path"])

    return {
        "files": valid_files,
        "commit_message": parsed.get("commit_message", ""),
    }


def _try_repair_truncated_json(raw_json_str: str) -> dict | None:
    """
    تلاش برای تعمیر JSON ناقص (وقتی پاسخ مدل وسط action_plan قطع شده).
    اول JSON کامل رو تست میکنه، اگه ناقص بود سعی میکنه فایل‌های کامل‌شده رو نجات بده.
    """
    if not raw_json_str or not raw_json_str.strip():
        return None

    # ۱) اول تلاش مستقیم
    try:
        return json.loads(raw_json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # ۲) حذف trailing characters ناقص و تلاش برای بستن JSON
    text = raw_json_str.strip()

    # پیدا کردن آخرین آبجکت فایل کامل‌شده (حاوی "path" و "content" و بسته‌شده با })
    # الگو: هر آبجکت {"path": ..., "content": ..., ...} که } بسته‌شده باشه
    import re as _rj_re

    # استخراج تمام آبجکت‌های فایل کامل از متن
    # یک آبجکت فایل کامل باید "path" و "content" داشته باشه و } بسته شده باشه
    completed_files = []
    # مقادیر string در JSON ممکنه شامل \n, \", و ... باشن پس regex ساده کار نمیکنه
    # بهترین روش: مرحله‌مرحله آبجکت‌های کامل رو از اول تا آخرین } پیدا کنیم

    # پیدا کردن "files": [ و سپس هر آبجکت داخلش
    files_start = text.find('"files"')
    if files_start == -1:
        # شاید "action_plan" باشه
        files_start = text.find('"action_plan"')
    if files_start == -1:
        return None

    bracket_start = text.find('[', files_start)
    if bracket_start == -1:
        return None

    # حالا از bracket_start شروع میکنیم و هر آبجکت رو مرحله‌ای parse میکنیم
    pos = bracket_start + 1
    depth = 0
    obj_start = -1

    while pos < len(text):
        ch = text[pos]

        if ch == '"':
            # skip string
            pos += 1
            while pos < len(text):
                if text[pos] == '\\':
                    pos += 2
                    continue
                if text[pos] == '"':
                    break
                pos += 1

        elif ch == '{':
            if depth == 0:
                obj_start = pos
            depth += 1

        elif ch == '}':
            depth -= 1
            if depth == 0 and obj_start >= 0:
                obj_str = text[obj_start:pos + 1]
                try:
                    obj = json.loads(obj_str)
                    if obj.get("path") and (obj.get("content") or obj.get("sections")):
                        # 🛡️ پاکسازی محتوا از آلودگی reasoning
                        if obj.get("content"):
                            obj["content"] = _sanitize_file_content(obj["content"], obj["path"])
                        completed_files.append(obj)
                except (json.JSONDecodeError, ValueError):
                    pass
                obj_start = -1

        pos += 1

    if not completed_files:
        return None

    # ساخت action_plan از فایل‌های نجات‌یافته
    # تلاش برای استخراج commit_message
    commit_msg = ""
    cm_match = _rj_re.search(r'"commit_message"\s*:\s*"([^"]*)"', text)
    if cm_match:
        commit_msg = cm_match.group(1)

    return {
        "files": completed_files,
        "commit_message": commit_msg,
        "_repaired": True,
        "_original_file_count_hint": text.count('"path"'),
        "_recovered_file_count": len(completed_files),
    }


def _extract_all_action_plans_from_response(content: str, is_truncated: bool = False) -> dict | None:
    """
    استخراج و ادغام action_plan از تمام بلوک‌های ```json در پاسخ مدل.
    برخی مدل‌ها (مثل deepseek-reasoner) action_plan رو به چند بلوک JSON جداگانه تقسیم میکنن.
    این تابع همه بلوک‌ها رو پیدا میکنه، parse میکنه و فایل‌هاشون رو ادغام میکنه.
    اگر is_truncated باشه، آخرین بلوک ناقص هم با repair پردازش میشه.
    """
    if '```' not in content:
        return None

    all_files = []
    commit_message = ""

    # پیدا کردن تمام بلوک‌های ```json...``` کامل
    json_blocks = re.findall(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
    # 🆕 short-circuit: اگر بلوکی شامل ask_user یا route_to معتبر بود، همان را برگردان
    for block in json_blocks:
        try:
            parsed = json.loads(block)
            normalized = _normalize_action_plan_json(parsed)
            if normalized and (normalized.get("ask_user") or normalized.get("route_to")):
                return normalized
        except (json.JSONDecodeError, Exception):
            pass
    for block in json_blocks:
        try:
            parsed = json.loads(block)
            normalized = _normalize_action_plan_json(parsed)
            if normalized and normalized.get("files"):
                all_files.extend(normalized["files"])
                if not commit_message and normalized.get("commit_message"):
                    commit_message = normalized["commit_message"]
        except (json.JSONDecodeError, Exception):
            pass

    # اگر truncated هست، آخرین بلوک ```json ممکنه ناقص باشه (بدون ```)
    if is_truncated:
        # پیدا کردن آخرین ```json که ``` پایانی ندارد
        last_json_start = content.rfind('```json')
        if last_json_start >= 0:
            after_last = content[last_json_start + 7:]
            # آیا این بلوک ``` پایانی داره؟
            if '```' not in after_last:
                # بلوک ناقصه — تلاش برای repair
                repaired = _try_repair_truncated_json(after_last.strip())
                if repaired:
                    normalized = _normalize_action_plan_json(repaired)
                    if normalized and normalized.get("files"):
                        # فقط فایل‌هایی که قبلاً اضافه نشدن
                        existing_paths = {f.get("path") for f in all_files}
                        for f in normalized["files"]:
                            if f.get("path") not in existing_paths:
                                all_files.append(f)

    # ── بازیابی فایل‌های بدون content: اتصال به بلوک‌های کد markdown ──
    # بعضی مدل‌ها action_plan JSON رو بدون content مینویسن، ولی کد واقعی رو در بلوک‌های جدا میذارن:
    # مثال: ```tsx\nimport React...\n``` بعد از ذکر مسیر فایل
    _empty_files = [f for f in all_files if f.get("path") and not f.get("content") and not f.get("sections")]
    if _empty_files:
        # پیدا کردن بلوک‌های کد غیر-JSON (tsx, ts, jsx, js, py, json, css, html)
        _code_blocks = re.findall(
            r'(?:####?\s*📄?\s*([^\n]+?)\s*\((?:create|modify|modify_sections)[^)]*\)\s*\n)?```(?:tsx?|jsx?|py|json|css|html|vue)\s*\n(.*?)\n```',
            content, re.DOTALL
        )
        _matched_empty = set()  # ایندکس فایل‌هایی که content گرفتن — جلوگیری از تغییر لیست حین iteration
        for _cb_title, _cb_code in _code_blocks:
            if not _cb_code.strip():
                continue
            # تلاش برای اتصال بلوک کد به فایل بدون content
            for ei, ef in enumerate(_empty_files):
                if ei in _matched_empty:
                    continue
                ef_path = ef.get("path", "")
                ef_fname = ef_path.rsplit("/", 1)[-1] if "/" in ef_path else ef_path
                # اگر عنوان بلوک شامل نام فایل باشه یا کد شامل import/export مرتبط باشه
                if _cb_title and ef_fname and ef_fname.lower() in _cb_title.lower():
                    ef["content"] = _sanitize_file_content(_cb_code.strip(), ef_path)
                    _matched_empty.add(ei)
                    slog.info(f"[action_plan extraction] Recovered content for {ef_path} from markdown code block")
                    break
                # fallback: اگر بلوک کد بلافاصله بعد از ذکر مسیر فایل اومده
                _path_mention_patterns = [ef_path, ef_fname]
                for _pm in _path_mention_patterns:
                    if _pm and _pm in content:
                        _pm_pos = content.find(_pm)
                        _cb_pos = content.find(_cb_code[:50])
                        if _cb_pos > _pm_pos and (_cb_pos - _pm_pos) < 500:
                            ef["content"] = _sanitize_file_content(_cb_code.strip(), ef_path)
                            _matched_empty.add(ei)
                            slog.info(f"[action_plan extraction] Recovered content for {ef_path} by proximity match")
                            break

    if not all_files:
        return None

    # حذف فایل‌های تکراری (حفظ آخرین نسخه)
    seen_paths = {}
    for f in all_files:
        path = f.get("path", "")
        if path:
            seen_paths[path] = f
    unique_files = list(seen_paths.values())

    if not unique_files:
        return None

    result = {
        "files": unique_files,
        "commit_message": commit_message,
    }
    if is_truncated:
        result["_truncated"] = True
    return result


def _apply_section_modifications(original_content: str, sections: list) -> dict:
    """
    اعمال تغییرات بخشی (modify_sections) روی فایل اصلی.
    هر section یک find/replace است که روی محتوای اصلی اعمال میشه.

    پارامترها:
    - original_content: محتوای کامل فایل اصلی
    - sections: لیست دیکشنری‌ها، هرکدام با "find" و "replace"

    بازگشت: {"success": bool, "content": str, "applied": int, "errors": list}
    """
    if not sections or not isinstance(sections, list):
        return {"success": False, "content": original_content, "applied": 0, "errors": ["sections خالی یا نامعتبر"]}

    result_content = original_content
    applied = 0
    errors = []

    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"section[{idx}]: باید دیکشنری باشد")
            continue

        find_str = section.get("find", "")
        replace_str = section.get("replace", "")

        if not find_str:
            errors.append(f"section[{idx}]: فیلد 'find' خالی است")
            continue

        # 🛡️ پاکسازی replace_str از آلودگی reasoning/markdown
        from ...services.content_sanitizer import sanitize_section_content as _sanitize_sec
        if replace_str:
            _clean_replace = _sanitize_sec(replace_str, "section_replace")
            if _clean_replace != replace_str:
                slog.info(f"[modify_sections] section[{idx}]: replace_str پاکسازی شد از آلودگی")
                replace_str = _clean_replace

        # ── تلاش برای پیدا کردن متن (exact match) ──
        if find_str in result_content:
            result_content = result_content.replace(find_str, replace_str, 1)
            applied += 1
            continue

        # ── تلاش دوم: مقایسه بدون فضای خالی اضافی (whitespace-flexible match) ──
        # برای حالتی که مدل AI فضای خالی رو کمی متفاوت تولید کرده
        import re as _sec_re
        find_lines = find_str.strip().split("\n")
        if len(find_lines) >= 1:
            # ساخت regex pattern: هر خط stripped + فضای خالی انعطاف‌پذیر بین خطوط
            pattern_parts = []
            for line in find_lines:
                # هر خط: فضای ابتدایی انعطاف‌پذیر + محتوای exact (escaped) + فضای انتهایی انعطاف‌پذیر
                escaped = _sec_re.escape(line.strip())
                pattern_parts.append(r'[ \t]*' + escaped + r'[ \t]*')
            pattern = r'\n'.join(pattern_parts)
            try:
                match = _sec_re.search(pattern, result_content)
                if match:
                    result_content = result_content[:match.start()] + replace_str + result_content[match.end():]
                    applied += 1
                    continue
            except _sec_re.error:
                pass  # regex خطا داد — ادامه بده

        # ── تلاش سوم: تطبیق بر اساس difflib.SequenceMatcher ──
        # خطوط find رو با خطوط فایل مقایسه میکنه و بهترین محدوده رو پیدا میکنه
        import difflib as _sec_difflib
        _find_lines_stripped = [l.strip() for l in find_str.strip().split("\n") if l.strip()]
        _content_lines = result_content.split("\n")
        _content_lines_stripped = [l.strip() for l in _content_lines]
        _difflib_matched = False

        if len(_find_lines_stripped) >= 1:
            # استفاده از SequenceMatcher برای پیدا کردن بهترین محدوده تطبیقی
            best_ratio = 0.0
            best_start = -1
            best_end = -1
            _window_size = len(_find_lines_stripped)

            for _wi in range(len(_content_lines_stripped) - _window_size + 1):
                _window = _content_lines_stripped[_wi:_wi + _window_size]
                _sm = _sec_difflib.SequenceMatcher(None, _find_lines_stripped, _window)
                _ratio = _sm.ratio()
                if _ratio > best_ratio:
                    best_ratio = _ratio
                    best_start = _wi
                    best_end = _wi + _window_size - 1

            # حداقل ۸۵٪ شباهت لازم — بالاتر از قبلی (۶۰٪) برای دقت بیشتر
            if best_ratio >= 0.85 and best_start >= 0:
                _before = "\n".join(_content_lines[:best_start])
                _after = "\n".join(_content_lines[best_end + 1:])
                result_content = _before + ("\n" if _before else "") + replace_str + ("\n" if _after else "") + _after
                applied += 1
                _difflib_matched = True
                if best_ratio < 1.0:
                    errors.append(f"section[{idx}]: ⚠️ difflib match استفاده شد (خط {best_start+1}-{best_end+1}, شباهت {best_ratio:.0%}) — دقت کمتر از exact match")

        if not _difflib_matched:
            # ── تلاش چهارم: fuzzy line-by-line matching (فالبک) ──
            _fuzzy_matched = False
            if len(_find_lines_stripped) >= 2:
                _first_line = _find_lines_stripped[0]
                _last_line = _find_lines_stripped[-1]
                _start_idx = None
                _end_idx = None
                # پیدا کردن اولین خط (exact match اول، بعد ۷۰٪ شباهت)
                for _ci, _cl_stripped in enumerate(_content_lines_stripped):
                    if _cl_stripped == _first_line:
                        _start_idx = _ci
                        break
                    elif len(_first_line) > 10 and len(_cl_stripped) > 5:
                        _line_ratio = _sec_difflib.SequenceMatcher(None, _first_line, _cl_stripped).ratio()
                        if _line_ratio >= 0.70:
                            _start_idx = _ci
                            break
                if _start_idx is not None:
                    # پیدا کردن آخرین خط (بعد از start)
                    for _ci in range(_start_idx + 1, min(_start_idx + len(_find_lines_stripped) + 10, len(_content_lines))):
                        _cl_stripped = _content_lines_stripped[_ci]
                        if _cl_stripped == _last_line:
                            _end_idx = _ci
                            break
                        elif len(_last_line) > 10 and len(_cl_stripped) > 5:
                            _line_ratio = _sec_difflib.SequenceMatcher(None, _last_line, _cl_stripped).ratio()
                            if _line_ratio >= 0.70:
                                _end_idx = _ci
                                break
                if _start_idx is not None and _end_idx is not None and _end_idx > _start_idx:
                    # اعتبارسنجی اضافی: تعداد خطوط محدوده باید نزدیک به تعداد خطوط find باشه
                    _range_size = _end_idx - _start_idx + 1
                    _expected_size = len(_find_lines_stripped)
                    if abs(_range_size - _expected_size) <= max(3, _expected_size * 0.3):
                        _before = "\n".join(_content_lines[:_start_idx])
                        _after = "\n".join(_content_lines[_end_idx + 1:])
                        result_content = _before + ("\n" if _before else "") + replace_str + ("\n" if _after else "") + _after
                        applied += 1
                        _fuzzy_matched = True
                        errors.append(f"section[{idx}]: ⚠️ fuzzy match استفاده شد (خط {_start_idx+1}-{_end_idx+1}) — دقت کمتر از exact match")

            if not _fuzzy_matched:
                # نمایش سرنخ: اولین خط find را در فایل جستجو کن — شاید خط‌های مشابه وجود داره
                _first_find_line = find_str.strip().split("\n")[0].strip()
                _similar_hint = ""
                if _first_find_line and len(_first_find_line) > 5:
                    for _li, _line in enumerate(_content_lines):
                        if _first_find_line[:30] in _line or _line.strip() == _first_find_line:
                            _similar_hint = f" (خط مشابه در خط {_li + 1}: '{_line.strip()[:60]}')"
                            break
                errors.append(f"section[{idx}]: متن find پیدا نشد: '{find_str[:80]}...'{_similar_hint}")

    success = applied > 0 and len(errors) < len(sections)
    return {
        "success": success,
        "content": result_content,
        "applied": applied,
        "total": len(sections),
        "errors": errors,
    }


def _auto_convert_modify_to_sections(orig_content: str, new_content: str, file_path: str) -> list | None:
    """
    🆕 تبدیل خودکار یک modify مخرب به modify_sections با استفاده از diff.

    وقتی مدل AI فایل بزرگ رو بجای modify_sections با modify می‌نویسه و خروجی ناقص/کوتاهه،
    این تابع تغییرات واقعی رو از تفاوت بین فایل اصلی و خروجی AI استخراج میکنه
    و به فرمت modify_sections (لیست {find, replace}) تبدیل میکنه.

    Returns: لیست sections یا None اگر تبدیل ممکن نبود
    """
    import difflib

    orig_lines = orig_content.split("\n")
    new_lines = new_content.split("\n")

    if not orig_lines or not new_lines:
        return None

    try:
        matcher = difflib.SequenceMatcher(None, orig_lines, new_lines)
        sections = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            elif tag == 'delete':
                # خطوط حذف‌شده — در بازنویسی مخرب معمولاً مدل نتونسته تولید کنه
                # ایمن‌ترین کار: نادیده گرفتن (خطوط اصلی حفظ میشن چون modify_sections فقط بخش‌های find شده رو تغییر میده)
                continue
            elif tag in ('replace', 'insert'):
                # تغییرات واقعی مدل — اینها رو باید استخراج کنیم

                # context: ۳ خط قبل و بعد از تغییر برای matching مطمئن
                ctx_before_start = max(0, i1 - 3)
                ctx_after_end = min(len(orig_lines), i2 + 3)

                # find: خطوط اصلی با context
                find_lines = orig_lines[ctx_before_start:ctx_after_end]
                find_text = "\n".join(find_lines)

                # replace: context قبل + خطوط جدید + context بعد
                if tag == 'replace':
                    replace_lines = (
                        orig_lines[ctx_before_start:i1] +
                        new_lines[j1:j2] +
                        orig_lines[i2:ctx_after_end]
                    )
                else:  # insert
                    replace_lines = (
                        orig_lines[ctx_before_start:i1] +
                        new_lines[j1:j2] +
                        orig_lines[i1:ctx_after_end]
                    )
                replace_text = "\n".join(replace_lines)

                # فقط اگه find در فایل اصلی unique باشه اضافه کن
                if find_text and orig_content.count(find_text) == 1:
                    sections.append({
                        "find": find_text,
                        "replace": replace_text,
                    })
                elif find_text and len(find_lines) >= 3:
                    # تلاش با context بیشتر (۵ خط قبل و بعد)
                    _wider_start = max(0, i1 - 5)
                    _wider_end = min(len(orig_lines), i2 + 5)
                    _wider_find = "\n".join(orig_lines[_wider_start:_wider_end])
                    if orig_content.count(_wider_find) == 1:
                        if tag == 'replace':
                            _wider_replace_lines = (
                                orig_lines[_wider_start:i1] +
                                new_lines[j1:j2] +
                                orig_lines[i2:_wider_end]
                            )
                        else:
                            _wider_replace_lines = (
                                orig_lines[_wider_start:i1] +
                                new_lines[j1:j2] +
                                orig_lines[i1:_wider_end]
                            )
                        sections.append({
                            "find": _wider_find,
                            "replace": "\n".join(_wider_replace_lines),
                        })

        if not sections:
            return None

        # حداکثر ۲۰ section — اگه بیشتر شد یعنی تغییرات خیلی زیاده و auto-convert مناسب نیست
        if len(sections) > 20:
            slog.warning(f"[auto-convert] {file_path}: {len(sections)} sections too many for auto-convert, skipping")
            return None

        slog.info(f"[auto-convert] {file_path}: extracted {len(sections)} sections from destructive modify")
        return sections

    except Exception as e:
        slog.error(f"[auto-convert] {file_path}: failed: {e}")
        return None


# ─── Python import hallucination detection ─────────────────────────
# مدل‌های AI خیلی وقت‌ها فایل‌هایی می‌سازند که `from app.X import Y` می‌کنند
# در حالی که `app/X.py` در پروژه وجود ندارد. این تابع imports را با
# AST تحلیل می‌کند و در صورت hallucination، خطا برمی‌گرداند.
def _validate_python_imports(
    action_plan_files: List[dict],
    original_files: dict = None,
    repo_file_paths: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """
    تشخیص import های hallucinated در فایل‌های Python.

    منطق:
    1. جمع‌آوری تمام ماژول‌های "شناخته‌شده" از action_plan + original_files
    2. تشخیص top-level package(های) داخلی پروژه (مثلاً 'app', 'backend')
    3. برای هر فایل Python در action_plan، parse imports و چک کن:
       - اگر import از یک ماژول داخلی است ولی آن ماژول هیچ‌جا نیست → hallucination
       - اگر ماژول در action_plan هست ولی نام imported تعریف نشده → hallucination

    🆕 (v3 false-positive fix) — `repo_file_paths` لیست همه فایل‌های repo
    (مثل خروجی GitHub tree). اگر یک ماژول در action_plan یا original_files
    نیست ولی فایل آن در repo واقعاً موجود است، false-positive flag نشود.
    این رفع باگ critical است که `app/main.py` با `from app.middleware import`
    را reject می‌کرد در حالی که `app/middleware.py` در repo موجود بود.
    """
    import ast as _ast
    errors: Dict[str, List[str]] = {}

    # 🆕 (v3 false-positive fix) — ساخت یک set از ماژول‌های repo برای lookup سریع
    _repo_modules: set = set()
    if repo_file_paths:
        for rp in repo_file_paths:
            if not rp or not isinstance(rp, str):
                continue
            if rp.endswith(".py"):
                mod = rp[:-3].replace("/", ".").replace("\\", ".")
                if mod.endswith(".__init__"):
                    mod = mod[:-9]
                _repo_modules.add(mod)

    def _path_to_module(p: str) -> Optional[str]:
        if not p or not p.endswith(".py"):
            return None
        m = p[:-3].replace("/", ".").replace("\\", ".")
        if m.endswith(".__init__"):
            m = m[:-9]
        return m

    def _extract_defs(content: str) -> set:
        """نام‌های top-level که در یک فایل تعریف شده‌اند (func/class/var).

        🆕 (v3 fix) — قبلاً فقط `tree.body` (top-level مستقیم) را اسکن
        می‌کرد و assignments داخل `try/except`/`if`/`with` را نمی‌دید.
        مثال: `engine = create_async_engine(...)` در try block. این
        باعث false-positive «engine hallucinated» می‌شد.
        الان helper recursive نام‌های تعریف‌شده در همه containers را
        جمع می‌کند.
        """
        defs = set()
        try:
            tree = _ast.parse(content)
        except Exception:
            return defs

        def _collect_names_from_target(target, into: set) -> None:
            if isinstance(target, _ast.Name):
                into.add(target.id)
            elif isinstance(target, (_ast.Tuple, _ast.List)):
                for elt in target.elts:
                    _collect_names_from_target(elt, into)

        def _walk_module_body(stmts) -> None:
            """recursive walk که containers مثل Try/If/With را هم می‌گردد."""
            for node in stmts:
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                    defs.add(node.name)
                elif isinstance(node, _ast.Assign):
                    for target in node.targets:
                        _collect_names_from_target(target, defs)
                elif isinstance(node, _ast.AnnAssign) and isinstance(node.target, _ast.Name):
                    defs.add(node.target.id)
                elif isinstance(node, (_ast.Import, _ast.ImportFrom)):
                    for alias in node.names:
                        defs.add(alias.asname or alias.name.split(".")[0])
                # 🆕 containers — assignments داخل این‌ها هم top-level محسوب می‌شوند
                elif isinstance(node, _ast.Try):
                    _walk_module_body(node.body)
                    for handler in node.handlers:
                        _walk_module_body(handler.body)
                    _walk_module_body(node.orelse)
                    _walk_module_body(node.finalbody)
                elif isinstance(node, _ast.If):
                    _walk_module_body(node.body)
                    _walk_module_body(node.orelse)
                elif isinstance(node, (_ast.With, _ast.AsyncWith)):
                    _walk_module_body(node.body)
                elif isinstance(node, (_ast.For, _ast.AsyncFor, _ast.While)):
                    _walk_module_body(node.body)
                    _walk_module_body(node.orelse)

        _walk_module_body(tree.body)
        return defs

    # 1. ساخت map ماژول‌های شناخته‌شده
    known_modules: Dict[str, set] = {}  # module_path → set of defined names

    for f in action_plan_files:
        p = f.get("path", "")
        mod = _path_to_module(p)
        if mod:
            known_modules[mod] = _extract_defs(f.get("content", "") or "")
            # __init__ هم به package parent ست شود
            if p.endswith("/__init__.py") or p == "__init__.py":
                pkg = mod  # already without .__init__ suffix
                known_modules.setdefault(pkg, known_modules[mod])

    if original_files:
        for p, content in original_files.items():
            mod = _path_to_module(p)
            if mod and mod not in known_modules:
                known_modules[mod] = _extract_defs(content or "")

    # 2. تشخیص top-level packages داخلی
    project_roots: set = set()
    for mod in known_modules:
        root = mod.split(".")[0]
        project_roots.add(root)
    # حذف چند نام عمومی که ممکنه false positive بدهند
    project_roots.discard("test")
    project_roots.discard("tests")

    # 3. تحلیل imports هر فایل Python در action_plan
    for f in action_plan_files:
        p = f.get("path", "")
        if not p.endswith(".py"):
            continue
        content = f.get("content", "") or ""
        if not content:
            continue
        try:
            tree = _ast.parse(content)
        except Exception:
            continue  # syntax errors handled elsewhere

        file_errs: List[str] = []
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ImportFrom):
                if node.level and node.level > 0:
                    # relative import (e.g., `from .config import settings`)
                    # محاسبهٔ ماژول هدف بر اساس ماژول فعلی
                    current_mod = _path_to_module(p) or ""
                    parts = current_mod.split(".")
                    # level=1 → همان package، level=2 → یک سطح بالاتر و …
                    if len(parts) < node.level:
                        continue
                    base = ".".join(parts[: -node.level]) if node.level <= len(parts) else ""
                    target_mod = (base + ("." + node.module if node.module else "")).strip(".")
                else:
                    target_mod = node.module or ""

                if not target_mod:
                    continue
                root = target_mod.split(".")[0]
                if root not in project_roots:
                    # احتمالاً stdlib یا third-party — رد شو
                    continue

                # داخلی است — باید در known_modules باشد
                if target_mod not in known_modules:
                    # شاید parent package باشد (مثلاً `from app.routes import auth` که `app/routes/auth.py` موجود است)
                    has_submodule = any(km.startswith(target_mod + ".") for km in known_modules)
                    # 🆕 (v3 false-positive fix) — قبل از reject، چک کن آیا
                    # فایل واقعاً در repo (خارج از scope فایل‌های خوانده‌شده) موجود است
                    exists_in_repo = (
                        target_mod in _repo_modules
                        or any(rm.startswith(target_mod + ".") for rm in _repo_modules)
                    )
                    if not has_submodule and not exists_in_repo:
                        file_errs.append(
                            f"❌ import hallucinated: `from {target_mod} import ...` "
                            f"— ماژول `{target_mod}` نه در action_plan هست و نه در فایل‌های خوانده‌شده و نه در repo موجود"
                        )
                        continue
                    if not has_submodule and exists_in_repo:
                        # ماژول در repo هست ولی محتوای آن خوانده نشده — defs چک نمی‌کنیم
                        continue

                # ماژول هست؛ آیا نام‌های imported تعریف شده‌اند؟
                defs = known_modules.get(target_mod, set())
                if defs:  # فقط اگر defs را داریم چک کن
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        if alias.name not in defs:
                            # ممکن است sub-module باشد (e.g., `from app import routes` که routes یک package است)
                            sub_mod = f"{target_mod}.{alias.name}"
                            if sub_mod in known_modules or any(km.startswith(sub_mod + ".") for km in known_modules):
                                continue
                            file_errs.append(
                                f"❌ import hallucinated: `{alias.name}` در ماژول `{target_mod}` تعریف نشده "
                                f"— احتمالاً مدل نام نمادی را اختراع کرده"
                            )
            elif isinstance(node, _ast.Import):
                for alias in node.names:
                    target_mod = alias.name
                    root = target_mod.split(".")[0]
                    if root not in project_roots:
                        continue
                    if target_mod not in known_modules and not any(km.startswith(target_mod + ".") for km in known_modules):
                        # 🆕 (v3 false-positive fix) — همان منطق ImportFrom
                        if target_mod in _repo_modules or any(rm.startswith(target_mod + ".") for rm in _repo_modules):
                            continue
                        file_errs.append(
                            f"❌ import hallucinated: `import {target_mod}` — ماژول وجود ندارد"
                        )

        if file_errs:
            errors[p] = file_errs

    return errors


def _normalize_repo_paths(files: Optional[List]) -> Optional[List[str]]:
    """🆕 (v3) helper: لیست فایل‌ها (dict یا str) → لیست مسیرها.

    استفاده در call sites `_validate_action_plan_syntax` که `all_files` می‌تواند
    dict (با key=path) یا string باشد.
    """
    if not files:
        return None
    result: List[str] = []
    for f in files:
        if isinstance(f, str):
            result.append(f)
        elif isinstance(f, dict):
            p = f.get("path")
            if p and isinstance(p, str):
                result.append(p)
    return result or None


def _check_stack_traced_files_in_action_plan(
    action_plan: Optional[dict],
    user_message: str,
    code_files: List[str],
    backend_logs: Optional[List[dict]] = None,
) -> Optional[Dict[str, Any]]:
    """🆕 (v3 safety-net) — هشدار اگر فایل ذکر شده در stack trace در
    action_plan نیست.

    این پاسخ به مشکل قابل دیدن کاربر است: AI گفت «main.py صحیح است» در
    حالی که خط ۳۲ همان فایل علت deploy failure بود. ما نمی‌توانیم AI را
    مجبور کنیم درست تشخیص دهد، ولی می‌توانیم یک warning صریح در
    گزارش نهایی نشان دهیم تا کاربر و developer متوجه شوند fix احتمالاً
    ناقص است.

    Returns:
        None اگر هیچ stack-traced file وجود ندارد یا همگی در action_plan
        هستند. در غیر این صورت، dict با لیست missing files.
    """
    if not user_message and not backend_logs:
        return None
    # ساخت متن کلی از پیام + logs
    text_parts: List[str] = [user_message or ""]
    if backend_logs:
        for entry in backend_logs[-30:]:
            if isinstance(entry, dict):
                text_parts.append(
                    " ".join(str(entry.get(k, "")) for k in ("message", "stack", "stack_trace", "text", "msg"))
                )
            elif isinstance(entry, str):
                text_parts.append(entry)
    combined_text = "\n".join(text_parts)
    stack_files = _extract_file_paths_from_text(combined_text, code_files)
    if not stack_files:
        return None
    # کدام فایل‌ها در action_plan هستند؟
    ap_paths = set()
    if action_plan and isinstance(action_plan.get("files"), list):
        for f in action_plan["files"]:
            if isinstance(f, dict) and f.get("path"):
                ap_paths.add(f["path"])
    missing = [f for f in stack_files if f not in ap_paths]
    if not missing:
        return None
    return {
        "stack_traced_files": stack_files,
        "missing_from_action_plan": missing,
        "warning_message": (
            f"⚠️ {len(missing)} فایل که در stack trace خطا ذکر شده‌اند، در action_plan نیستند: "
            f"{', '.join(missing)}. "
            f"AI ممکن است این فایل‌ها را اشتباه «صحیح» تشخیص داده باشد. "
            f"اگر deploy همچنان شکست می‌خورد، محتوای این فایل‌ها را روی GitHub بررسی کنید."
        ),
    }


# 🆕 (pypi-validation) — کش ساده برای جلوگیری از hit مکرر PyPI
_PYPI_EXISTS_CACHE: Dict[str, bool] = {}


def _check_pypi_package_exists(package_name: str, timeout: float = 2.0) -> bool:
    """چک می‌کنه که آیا یک package در PyPI وجود داره.

    Returns True اگر وجود داره یا چک fail شد (fail-open، چون نمی‌خوایم
    network glitch باعث reject شدن همهٔ پکیج‌ها بشه). False فقط وقتی
    PyPI صریحاً 404 می‌ده.
    """
    if not package_name or not package_name.strip():
        return True
    name = package_name.strip().lower()
    # normalize: PyPI با _ و - مشابه هستن
    name_norm = name.replace("_", "-")
    if name_norm in _PYPI_EXISTS_CACHE:
        return _PYPI_EXISTS_CACHE[name_norm]
    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(
            f"https://pypi.org/pypi/{name_norm}/json",
            method="HEAD",
            headers={"User-Agent": "lifemanager-inspector/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                exists = resp.status == 200
        except urllib.error.HTTPError as e:
            exists = e.code != 404
        _PYPI_EXISTS_CACHE[name_norm] = exists
        return exists
    except Exception:
        # network/timeout/dns → fail-open
        _PYPI_EXISTS_CACHE[name_norm] = True
        return True


def _extract_pypi_package_names(requirements_content: str) -> List[str]:
    """استخراج نام پکیج‌ها از محتوای requirements.txt."""
    import re as _re
    packages: List[str] = []
    for raw_line in requirements_content.splitlines():
        line = raw_line.strip()
        # skip comments, empty lines, options like -r, -e, --
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # strip inline comments
        line = line.split("#", 1)[0].strip()
        # extract just the package name (before ==, >=, <=, ~=, !=, ;, [, etc.)
        m = _re.match(r"^([A-Za-z0-9_\-\.]+)", line)
        if m:
            pkg = m.group(1).strip()
            if pkg and pkg.lower() not in ("python", "pip"):
                packages.append(pkg)
    return packages


def _validate_action_plan_syntax(
    action_plan: dict,
    original_files: dict = None,
    repo_file_paths: Optional[List[str]] = None,
    user_message: Optional[str] = None,
    backend_logs: Optional[List[dict]] = None,
    code_files: Optional[List[str]] = None,
) -> dict:
    """
    اعتبارسنجی سینتکس فایل‌های action_plan قبل از ارسال به فرانت.
    فایل‌هایی با خطای بحرانی (❌) از action_plan حذف میشن تا commit نشن.
    فایل‌هایی با هشدار (⚠️) باقی می‌مونن ولی هشدار نمایش داده میشه.
    """
    if not action_plan or not action_plan.get("files"):
        return action_plan

    warnings = []
    rejected_files = []  # فایل‌هایی که به خاطر خطای بحرانی حذف شدن
    safe_files = []  # فایل‌هایی که سالمن یا فقط هشدار دارن

    # 🆕 (anti-hallucination) — تحلیل import های Python قبل از per-file loop
    # تا اگر فایلی imports غیرموجود دارد، در همان فایل علامت بحرانی بزنیم.
    _import_errors_by_file: Dict[str, List[str]] = {}
    try:
        _import_errors_by_file = _validate_python_imports(
            action_plan["files"],
            original_files,
            repo_file_paths=repo_file_paths,
        )
    except Exception as _imp_e:
        slog.warning(f"[action_plan validation] python import analysis failed: {_imp_e}")

    for f in action_plan["files"]:
        path = f.get("path", "")
        operation = f.get("operation", "").lower()
        content = f.get("content", "")

        # ── اعتبارسنجی ویژه modify_sections ──
        if operation == "modify_sections":
            sections = f.get("sections", [])
            sec_errors = []
            if not sections or not isinstance(sections, list):
                sec_errors.append("❌ sections خالی یا نامعتبر — باید لیستی از {find, replace} باشد")
            else:
                for si, sec in enumerate(sections):
                    if not isinstance(sec, dict):
                        sec_errors.append(f"❌ section[{si}]: باید دیکشنری باشد")
                    elif not sec.get("find"):
                        sec_errors.append(f"❌ section[{si}]: فیلد 'find' خالی — چه متنی باید جایگزین شود؟")
                    else:
                        # replace میتونه خالی باشه (حذف بخش)
                        # ── چک: آیا find واقعاً کد هست یا یه توصیف؟ ──
                        _find_text = sec["find"].strip()
                        _descriptive_markers = [
                            "انتهای فایل", "قبل از export", "بعد از import", "در بخش",
                            "end of file", "before export", "after import", "at the end",
                            "// اینجا", "/* اینجا", "در خط", "ابتدای فایل",
                        ]
                        _is_descriptive = any(m in _find_text.lower() for m in _descriptive_markers)
                        # find خیلی کوتاه (<15 کاراکتر) و بدون علائم کد هم مشکوکه
                        _code_indicators = ["{", "}", "(", ")", "=", ";", "import ", "export ", "const ", "function ", "class ", "def ", "return ", "<", "/>"]
                        _has_code = any(ci in _find_text for ci in _code_indicators)
                        if _is_descriptive and not _has_code:
                            sec_errors.append(
                                f"⚠️ section[{si}]: find به نظر **توصیف محل تغییر** است نه **متن واقعی فایل**: "
                                f"'{_find_text[:60]}' — find باید دقیقاً متن کپی‌شده از فایل اصلی باشد"
                            )
                        # ── چک: آیا find شامل markdown code fence هست؟ (خطای رایج AI) ──
                        if "```" in _find_text:
                            sec_errors.append(
                                f"⚠️ section[{si}]: find شامل markdown code fence (```) است — "
                                f"find باید متن خام فایل باشد نه قالب‌بندی markdown: '{_find_text[:60]}'"
                            )
                        # ── چک: آیا find فقط متن فارسی/عربی هست بدون کد؟ ──
                        import re as _val_re
                        _persian_ratio = len(_val_re.findall(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', _find_text))
                        _total_chars = len(_find_text.replace(" ", "").replace("\n", ""))
                        if _total_chars > 10 and _persian_ratio / max(_total_chars, 1) > 0.5 and not _has_code:
                            sec_errors.append(
                                f"⚠️ section[{si}]: find عمدتاً متن فارسی است (نه کد): '{_find_text[:60]}' — "
                                f"احتمالاً محتوای reasoning مدل AI بجای کد واقعی فایل قرار گرفته"
                            )
            if sec_errors:
                f["_warnings"] = sec_errors
                rejected_files.append(f)
                warnings.extend([f"🚫 {path}: {e}" for e in sec_errors])
                slog.error(f"[action_plan validation] REJECTED modify_sections {path}: {sec_errors}")
            else:
                safe_files.append(f)
                warnings.append(f"📄 {path}: ✅ modify_sections با {len(sections)} بخش")
            continue

        if not content:
            safe_files.append(f)
            continue

        file_warnings = []
        file_critical = []  # خطاهای بحرانی که باعث حذف فایل میشن
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""

        # ── چک‌های عمومی ──
        # فایل نیمه‌کاره (placeholder comments)
        _truncation_markers = [
            "// ... rest of", "// ... بقیه", "// remaining code",
            "/* existing code */", "// ... existing", "// ... ادامه",
            "# ... rest of", "# ... بقیه",
            "// TODO: rest", "/* ... */",
        ]
        for marker in _truncation_markers:
            if marker.lower() in content.lower():
                file_critical.append(f"❌ فایل ناقص: محتوا شامل '{marker}' — این فایل حذف شد")
                break

        # 🆕 (pypi-validation) — اگر فایل requirements.txt هست، هر پکیج
        # رو در PyPI چک کن. transcript کاربر نشون داد مدل `autosqlite==0.19.0`
        # نوشت (typo برای `aiosqlite`) و deploy fail شد. این gate جلوش رو می‌گیره.
        # cache در سطح ماژول مدیریت می‌شه؛ timeout 2s؛ fail-open اگر network
        # خراب بود.
        _path_lower = path.lower()
        if _path_lower.endswith("requirements.txt") or _path_lower.endswith("/requirements.txt"):
            _pkgs = _extract_pypi_package_names(content)
            _missing_pkgs: List[str] = []
            for _pkg in _pkgs:
                if not _check_pypi_package_exists(_pkg):
                    _missing_pkgs.append(_pkg)
            if _missing_pkgs:
                file_critical.append(
                    f"❌ پکیج‌های نامعتبر در PyPI: {', '.join(_missing_pkgs[:5])} — "
                    f"این فایل حذف شد. احتمالاً مدل اسم اشتباه نوشته (مثلاً autosqlite→aiosqlite)."
                )

        # تعادل پرانتز/آکولاد/براکت
        # threshold نسبی: فایل‌های بزرگ‌تر اختلاف بیشتری مجازن
        _content_lines = len(content.split("\n"))
        _balance_threshold = max(3, min(8, _content_lines // 100))  # حداقل ۳، حداکثر ۸
        for open_c, close_c, name in [("(", ")", "پرانتز"), ("{", "}", "آکولاد"), ("[", "]", "براکت")]:
            opens = content.count(open_c)
            closes = content.count(close_c)
            diff = abs(opens - closes)
            if diff > _balance_threshold:
                file_critical.append(f"❌ عدم تعادل بحرانی {name}: {open_c}={opens} vs {close_c}={closes} (اختلاف {diff}) — این فایل حذف شد")

        # ── چک‌های خاص Python ──
        if ext == "py":
            try:
                compile(content, path, "exec")
            except SyntaxError as se:
                file_critical.append(f"❌ خطای سینتکس Python خط {se.lineno}: {se.msg} — این فایل حذف شد")

        # ── چک‌های خاص JSON ──
        if ext == "json":
            json_content = content
            # tsconfig.json, jsconfig.json و مشابه‌ها JSONC هستند (کامنت مجاز)
            # قبل از اعتبارسنجی، کامنت‌ها رو حذف میکنیم
            _fname = path.rsplit("/", 1)[-1].lower() if "/" in path else path.lower()
            if _fname.startswith("tsconfig") or _fname.startswith("jsconfig"):
                import re as _json_re
                # حذف کامنت‌های تک‌خطی (//) و چندخطی (/* ... */)
                json_content = _json_re.sub(r'//[^\n]*', '', json_content)
                json_content = _json_re.sub(r'/\*[\s\S]*?\*/', '', json_content)
                # حذف trailing commas قبل از } یا ]
                json_content = _json_re.sub(r',\s*([}\]])', r'\1', json_content)
            try:
                json.loads(json_content)
            except json.JSONDecodeError as je:
                file_critical.append(f"❌ JSON نامعتبر خط {je.lineno}: {je.msg} — این فایل حذف شد")

        # ── چک‌های خاص TypeScript/JavaScript/JSX/TSX ──
        if ext in ("ts", "tsx", "js", "jsx"):
            for line_num, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()
                if stripped.startswith("import ") and "from" not in stripped and ";" in stripped and "{" not in stripped and "type" not in stripped:
                    if not stripped.endswith("';") and not stripped.endswith('";'):
                        file_warnings.append(f"⚠️ خط {line_num}: import بدون from — احتمال خطای سینتکس")
                        break

            # ── بررسی تعادل backtick (template literal) ──
            _bt_count = content.count("`")
            if _bt_count % 2 != 0:
                file_critical.append(f"❌ عدم تعادل backtick (template literal): {_bt_count} عدد (فرد) — یک ` باز یا بسته اضافی — این فایل حذف شد")

            # ── بررسی template literal تو در تو (nested backtick) ──
            import re as _tsx_re
            _nested_bt_pattern = r'`[^`]*\$\{[^}]*`[^`]*`[^}]*\}[^`]*`'
            _nested_bt_matches = _tsx_re.findall(_nested_bt_pattern, content)
            if _nested_bt_matches:
                file_critical.append(
                    f"❌ template literal تو در تو: {len(_nested_bt_matches)} مورد — "
                    f"esbuild قادر به transform نیست — باید از string concatenation استفاده شود — این فایل حذف شد"
                )

            # ── بررسی JSX/TSX — className بدون تگ (خطای رایج AI) ──
            if ext in ("tsx", "jsx"):
                _lines = content.split("\n")
                for _ln, _line in enumerate(_lines, 1):
                    _stripped = _line.strip()
                    if _stripped.startswith("className=") and _ln > 1:
                        # بررسی ۲۰ خط قبل (بجای ۴) — در JSX واقعی تگ باز ممکنه خیلی بالاتر باشه
                        _lookback = 20
                        _prev = "\n".join(_lines[max(0, _ln - 1 - _lookback):_ln - 1])
                        # بررسی وجود تگ JSX یا الگوهای مرتبط JSX
                        _jsx_indicators = [
                            "<", "...", "style=", "onClick=", "onChange=", "onSubmit=",
                            "ref=", "key=", "id=", "data-", "aria-", "htmlFor=",
                            "disabled", "placeholder=", "value=", "type=", "name=",
                            "href=", "src=", "alt=", "role=", "tabIndex=",
                        ]
                        _has_jsx_context = any(ind in _prev for ind in _jsx_indicators)
                        if not _has_jsx_context:
                            # 🔧 تنزل از خطای بحرانی به هشدار: این یک هیوریستیک ناقص‌نگر هست
                            # و در JSX واقعی (تگ با props زیاد، conditional rendering) false positive تولید میکنه
                            file_warnings.append(
                                f"⚠️ خط {_ln}: className بدون تگ JSX — ممکنه کد خارج از کامپوننت قرار گرفته باشه (لطفاً بررسی کنید)"
                            )
                            break

        # ── تشخیص بازنویسی مخرب (Destructive Rewrite Detection) ──
        # اگر operation=modify/update و فایل اصلی رو داریم → مقایسه اندازه + محتوا
        operation = f.get("operation", "").lower()
        if operation in ("modify", "update", "") and original_files:
            # پیدا کردن فایل اصلی (ممکنه مسیر‌ها متفاوت باشن)
            _orig_content = None
            for _orig_path, _orig_c in original_files.items():
                if _orig_path == path or _orig_path.endswith("/" + path) or path.endswith("/" + _orig_path):
                    _orig_content = _orig_c
                    break
            if _orig_content and isinstance(_orig_content, str):
                orig_lines = len(_orig_content.strip().split("\n"))
                new_lines = len(content.strip().split("\n"))
                _is_destructive = False
                _destructive_reason = ""
                # لایه ۱: اگر فایل اصلی بزرگ بوده (>80 خط) و خروجی AI خیلی کوتاه‌تره → بازنویسی مخرب
                if orig_lines > 80 and new_lines < orig_lines * 0.5:
                    _is_destructive = True
                    _destructive_reason = (
                        f"فایل اصلی {orig_lines} خط بود ولی خروجی AI فقط {new_lines} خط دارد "
                        f"({int(new_lines/orig_lines*100)}% از اصل)"
                    )
                # لایه ۲: مقایسه محتوایی — حتی اگه تعداد خطوط مشابه باشه، آیا محتوای واقعی حفظ شده؟
                elif orig_lines > 100:
                    _trivial = {"{", "}", "(", ")", "[", "]", "", "};", ");", "},", "],", "});", "export default", "return (", "return null;"}
                    _orig_meaningful = set()
                    for _ol in _orig_content.strip().split("\n"):
                        _stripped = _ol.strip()
                        if _stripped and _stripped not in _trivial and len(_stripped) > 10:
                            _orig_meaningful.add(_stripped)
                    if len(_orig_meaningful) > 20:
                        _preserved = sum(1 for _om in _orig_meaningful if _om in content)
                        _preserve_ratio = _preserved / len(_orig_meaningful)
                        if _preserve_ratio < 0.25:
                            _is_destructive = True
                            _destructive_reason = (
                                f"فقط {int(_preserve_ratio*100)}% از خطوط معنادار فایل اصلی "
                                f"({_preserved}/{len(_orig_meaningful)}) حفظ شده — مدل فایل رو از صفر نوشته"
                            )

                # 🆕 اگر بازنویسی مخرب شناسایی شد → تلاش برای auto-convert به modify_sections
                if _is_destructive:
                    _converted_sections = _auto_convert_modify_to_sections(_orig_content, content, path)
                    if _converted_sections:
                        # ✅ تبدیل موفق: عملیات modify → modify_sections
                        f["operation"] = "modify_sections"
                        f["sections"] = _converted_sections
                        f.pop("content", None)
                        _conv_msg = (
                            f"🔄 {path}: بازنویسی مخرب شناسایی شد ({_destructive_reason}) — "
                            f"تبدیل خودکار به modify_sections با {len(_converted_sections)} بخش تغییریافته"
                        )
                        file_warnings.append(_conv_msg)
                        warnings.append(_conv_msg)
                        slog.info(f"[action_plan validation] AUTO-CONVERTED destructive modify → modify_sections for {path}: {len(_converted_sections)} sections")
                    else:
                        file_critical.append(
                            f"❌ بازنویسی مخرب: {_destructive_reason} — تبدیل خودکار به modify_sections هم ممکن نبود — این فایل حذف شد"
                        )

        # 🆕 (anti-hallucination) — افزودن خطاهای import به file_critical
        # تا فایل‌هایی با import های جعلی reject شوند.
        if path in _import_errors_by_file:
            file_critical.extend(_import_errors_by_file[path])

        # 🆕 (anti-blind-overwrite) — اگر مدل فایلی را با operation=modify و
        # محتوای کامل می‌نویسد ولی آن را نخوانده (در original_files نیست) و فایل
        # در repo موجود است → محتوا حدسی است و overwrite می‌تواند کد واقعی را
        # پاک کند. این دقیقاً همان اشتباهی است که مدل با گفتن «فایل خالی است»
        # و پر کردن آن با محتوای حدسی مرتکب می‌شود. reject با پیام واضح.
        # توجه: modify_sections (find/replace) و create از این چک معاف‌اند.
        if (
            operation in ("modify", "update", "")
            and content
            and operation != "modify_sections"
        ):
            _read_paths = set((original_files or {}).keys())
            _repo_set = set(repo_file_paths or [])
            if path not in _read_paths and path in _repo_set:
                file_critical.append(
                    "❌ overwrite کور: این فایل در repo موجود است ولی در این تحلیل "
                    "خوانده نشده — محتوای ارائه‌شده حدسی است و می‌تواند کد واقعی را "
                    "پاک کند. باید ابتدا فایل خوانده شود، سپس فقط بخش لازم با "
                    "modify_sections تغییر کند."
                )

        # تصمیم‌گیری: حذف یا نگه‌داشتن
        if file_critical:
            f["_warnings"] = file_critical + file_warnings
            rejected_files.append(f)
            warnings.extend([f"🚫 {path}: {w}" for w in file_critical])
            slog.error(f"[action_plan validation] REJECTED file {path}: {file_critical}")
        else:
            if file_warnings:
                f["_warnings"] = file_warnings
                warnings.extend([f"📄 {path}: {w}" for w in file_warnings])
            safe_files.append(f)

    # جایگزینی لیست فایل‌ها با فایل‌های سالم
    action_plan["files"] = safe_files

    # 🆕 (v3 operation auto-correct) — اگر AI گفت `create` ولی فایل در
    # repo موجود است، به `modify` تبدیل کن (و برعکس). این AI ضعیف را
    # که فایل‌های موجود را re-create می‌کند (و overwrite می‌زند) مهار
    # می‌کند.
    if repo_file_paths:
        _repo_set = set(repo_file_paths)
        _op_corrections: List[str] = []
        for ch in action_plan.get("files", []):
            if not isinstance(ch, dict):
                continue
            path = ch.get("path", "")
            op = (ch.get("operation") or "modify").lower()
            if op == "create" and path in _repo_set:
                ch["operation"] = "modify"
                ch["_op_auto_corrected"] = True
                ch["_op_correction_note"] = (
                    f"AI گفت 'create' ولی `{path}` در repo از قبل موجود است → 'modify' شد"
                )
                _op_corrections.append(
                    f"✏️ `{path}`: create → modify (فایل از قبل موجود)"
                )
            elif op == "modify" and path not in _repo_set:
                ch["operation"] = "create"
                ch["_op_auto_corrected"] = True
                ch["_op_correction_note"] = (
                    f"AI گفت 'modify' ولی `{path}` در repo نیست → 'create' شد"
                )
                _op_corrections.append(
                    f"✏️ `{path}`: modify → create (فایل قبلاً موجود نیست)"
                )
        if _op_corrections:
            action_plan["_op_corrections"] = _op_corrections
            slog.info(f"[action_plan] operation auto-corrections: {_op_corrections}")
            warnings.append(
                f"📝 {len(_op_corrections)} عملیات auto-correct شد: " + " | ".join(_op_corrections[:3])
            )

    if rejected_files:
        action_plan["_rejected_files"] = [
            {"path": f.get("path", ""), "reasons": f.get("_warnings", [])}
            for f in rejected_files
        ]
        rejection_msg = f"🚫 {len(rejected_files)} فایل به خاطر خطای سینتکس بحرانی حذف شدند: " + \
            ", ".join(f.get("path", "") for f in rejected_files)
        warnings.insert(0, rejection_msg)

    if warnings:
        action_plan["_syntax_warnings"] = warnings
        slog.warning(f"[action_plan validation] {len(warnings)} issues ({len(rejected_files)} rejected): {warnings[:5]}")

    # 🆕 (v3 safety-net) — هشدار stack-trace coverage
    if user_message or backend_logs:
        try:
            _coverage = _check_stack_traced_files_in_action_plan(
                action_plan,
                user_message=user_message or "",
                code_files=code_files or [],
                backend_logs=backend_logs,
            )
            if _coverage:
                action_plan["_stack_trace_warning"] = _coverage
                slog.warning(
                    f"[action_plan] stack-traced files NOT in action_plan: "
                    f"{_coverage.get('missing_from_action_plan')}"
                )
        except Exception as _sc_e:
            slog.debug(f"stack-trace coverage check failed: {_sc_e}")

    return action_plan


def _validate_file_content_syntax(content: str, file_path: str) -> dict:
    """
    اعتبارسنجی سینتکس محتوای نهایی یک فایل قبل از commit.
    این تابع بعد از merge شدن modify_sections و قبل از commit فراخوانی میشه
    تا مطمئن بشیم کد سالم وارد ریپو میشه.

    Returns:
        dict: {"valid": bool, "errors": list, "warnings": list}
    """
    errors = []
    warnings = []
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    # ── چک آلودگی reasoning (قبل از هر چک دیگری) ──
    _contamination = _detect_reasoning_contamination(content, file_path)
    if _contamination:
        errors.append(f"آلودگی reasoning: {_contamination}")

    # ── چک placeholder/truncation ──
    _truncation_markers = [
        "// ... rest of", "// ... بقیه", "// remaining code",
        "/* existing code */", "// ... existing", "// ... ادامه",
        "# ... rest of", "# ... بقیه",
        "// TODO: rest", "/* ... */",
    ]
    for marker in _truncation_markers:
        if marker.lower() in content.lower():
            errors.append(f"محتوای ناقص: شامل '{marker}'")
            break

    # ── تعادل پرانتز/آکولاد/براکت ──
    # threshold نسبی: فایل‌های بزرگ‌تر اختلاف بیشتری مجازن
    _v_content_lines = len(content.split("\n"))
    _v_balance_threshold = max(3, min(8, _v_content_lines // 100))  # حداقل ۳، حداکثر ۸
    for open_c, close_c, name in [("(", ")", "پرانتز"), ("{", "}", "آکولاد"), ("[", "]", "براکت")]:
        opens = content.count(open_c)
        closes = content.count(close_c)
        diff = abs(opens - closes)
        if diff > _v_balance_threshold:
            errors.append(f"عدم تعادل {name}: {open_c}={opens} vs {close_c}={closes} (اختلاف {diff})")

    # ── Python syntax ──
    if ext == "py":
        try:
            compile(content, file_path, "exec")
        except SyntaxError as se:
            errors.append(f"خطای سینتکس Python خط {se.lineno}: {se.msg}")

    # ── JSON validation ──
    if ext == "json":
        json_content = content
        _fname = file_path.rsplit("/", 1)[-1].lower() if "/" in file_path else file_path.lower()
        if _fname.startswith("tsconfig") or _fname.startswith("jsconfig"):
            json_content = re.sub(r'//[^\n]*', '', json_content)
            json_content = re.sub(r'/\*[\s\S]*?\*/', '', json_content)
            json_content = re.sub(r',\s*([}\]])', r'\1', json_content)
        try:
            json.loads(json_content)
        except json.JSONDecodeError as je:
            errors.append(f"JSON نامعتبر خط {je.lineno}: {je.msg}")

    # ── TypeScript/JavaScript/JSX/TSX checks ──
    if ext in ("ts", "tsx", "js", "jsx"):
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("import ") and "from" not in stripped and ";" in stripped and "{" not in stripped and "type" not in stripped:
                if not stripped.endswith("';") and not stripped.endswith('";'):
                    warnings.append(f"خط {line_num}: import بدون from — احتمال خطای سینتکس")
                    break

        # ── بررسی تعادل backtick (template literal) ──
        backtick_count = content.count("`")
        if backtick_count % 2 != 0:
            errors.append(f"عدم تعادل backtick (template literal): {backtick_count} عدد (فرد) — یک ` باز یا بسته اضافی وجود دارد")

        # ── بررسی template literal تو در تو (nested backtick) ──
        # الگوی `...${...`...`...}...` باعث خطای esbuild transform میشه
        import re as _tsx_re
        _nested_bt_pattern = r'`[^`]*\$\{[^}]*`[^`]*`[^}]*\}[^`]*`'
        _nested_matches = _tsx_re.findall(_nested_bt_pattern, content)
        if _nested_matches:
            errors.append(
                f"template literal تو در تو (nested backtick): {len(_nested_matches)} مورد شناسایی شد — "
                f"esbuild قادر به transform نیست — از string concatenation استفاده کنید"
            )

        # ── بررسی JSX/TSX — تگ‌های باز بدون بسته ──
        if ext in ("tsx", "jsx"):
            # شمارش className یا attribute بیرون از تگ JSX (خطای رایج AI)
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                # className به عنوان اولین چیز در خط و بدون تگ باز قبلش
                if stripped.startswith("className=") and line_num > 1:
                    # بررسی ۲۰ خط قبل (بجای ۴) — در JSX واقعی تگ باز ممکنه خیلی بالاتر باشه
                    _lookback = 20
                    prev_lines = "\n".join(lines[max(0, line_num - 1 - _lookback):line_num - 1])
                    # بررسی وجود تگ JSX یا الگوهای مرتبط JSX
                    _jsx_indicators = [
                        "<", "...", "style=", "onClick=", "onChange=", "onSubmit=",
                        "ref=", "key=", "id=", "data-", "aria-", "htmlFor=",
                        "disabled", "placeholder=", "value=", "type=", "name=",
                        "href=", "src=", "alt=", "role=", "tabIndex=",
                    ]
                    _has_jsx_context = any(ind in prev_lines for ind in _jsx_indicators)
                    if not _has_jsx_context:
                        # 🔧 تنزل از خطای بحرانی به هشدار: این هیوریستیک در JSX واقعی
                        # (تگ‌های چند خطی با props زیاد) false positive تولید میکنه
                        warnings.append(
                            f"خط {line_num}: className بدون تگ JSX — ممکنه کد خارج از کامپوننت قرار گرفته باشه (لطفاً بررسی کنید)"
                        )
                        break

        # ── بررسی خطاهای رایج esbuild: export/return بیرون از تابع ──
        lines = content.split("\n")
        has_function_or_component = False
        for line in lines:
            stripped = line.strip()
            if any(kw in stripped for kw in ["function ", "const ", "class ", "export default", "export function"]):
                has_function_or_component = True
                break
        if not has_function_or_component and len(lines) > 5:
            warnings.append("فایل فاقد تعریف تابع، کامپوننت یا export — ممکن است ناقص باشد")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def _build_project_tree_summary(code_files: list, max_chars: int = 4000) -> str:
    """
    ساخت خلاصه ساختار پروژه از لیست فایل‌ها.
    نشون میده چه دایرکتوری‌هایی وجود دارن و چند فایل دارن.
    مدل با این میفهمه کل پروژه چه شکلیه (حتی فایل‌هایی که نخونده).
    """
    if not code_files:
        return ""
    # گروه‌بندی بر اساس دایرکتوری سطح اول و دوم
    from collections import defaultdict
    dir_counts = defaultdict(int)
    dir_examples = defaultdict(list)
    for f in code_files:
        parts = f.split("/")
        if len(parts) >= 2:
            top = parts[0] + "/" + parts[1]
        else:
            top = parts[0]
        dir_counts[top] += 1
        if len(dir_examples[top]) < 3:
            dir_examples[top].append(f)

    lines = ["ساختار کامل پروژه (همه دایرکتوری‌ها):"]
    for dir_path in sorted(dir_counts.keys()):
        count = dir_counts[dir_path]
        examples = dir_examples[dir_path]
        lines.append(f"  📁 {dir_path}/ ({count} فایل) — مثال: {', '.join(examples[:2])}")

    summary = "\n".join(lines)
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "\n... [truncated]"
    return summary


def _ensure_balanced_selection(selected: list, code_files: list, max_files: int, error_domain: str = "cross") -> list:
    """
    اگر همه فایل‌های انتخاب‌شده از یک دایرکتوری سطح اولن،
    فایل‌هایی از دایرکتوری‌های دیگه هم اضافه کن.
    مثلاً اگر فقط frontend/ انتخاب شده، backend/ هم اضافه شه.

    ⚠️ اگر error_domain مشخص باشد (frontend/backend)، فایل از دامنه نامرتبط اضافه نمیشه.
    """
    if not selected or len(selected) >= max_files:
        return selected

    # 🆕 اگر دامنه خطا مشخصه، فایل‌های نامرتبط رو اضافه نکن
    _fe_dir_hints = {"frontend", "src", "app", "pages", "components", "public", "styles", "client"}
    _be_dir_hints = {"backend", "server", "api", "models", "services", "db", "migrations", "alembic"}

    # تشخیص دایرکتوری‌های سطح اول
    selected_top_dirs = set()
    for f in selected:
        parts = f.split("/")
        if parts:
            selected_top_dirs.add(parts[0])

    all_top_dirs = set()
    for f in code_files:
        parts = f.split("/")
        if parts:
            all_top_dirs.add(parts[0])

    # دایرکتوری‌هایی که اصلاً فایلی ازشون انتخاب نشده
    missing_dirs = all_top_dirs - selected_top_dirs

    if not missing_dirs:
        return selected

    # 🆕 فیلتر دایرکتوری‌ها بر اساس دامنه خطا
    if error_domain == "frontend":
        # خطای frontend — فایل‌های backend اضافه نکن
        missing_dirs = {d for d in missing_dirs if d.lower() not in _be_dir_hints}
    elif error_domain == "backend":
        # خطای backend — فایل‌های frontend اضافه نکن
        missing_dirs = {d for d in missing_dirs if d.lower() not in _fe_dir_hints}

    if not missing_dirs:
        return selected

    # فایل‌های مهم از دایرکتوری‌های نادیده‌گرفته‌شده
    priority_names = [
        "routes.", "main.", "app.", "index.", "server.", "api.", "config.",
        "models.", "schema.", "page.", "layout.", "store.", "hooks.", "utils.",
        "service.", "middleware.", "context.", "components."
    ]
    for missing_dir in sorted(missing_dirs):
        if len(selected) >= max_files:
            break
        dir_files = [f for f in code_files if f.startswith(missing_dir + "/")]
        # اول فایل‌های مهم
        for df in dir_files:
            if len(selected) >= max_files:
                break
            name = df.split("/")[-1].lower()
            if any(p in name for p in priority_names):
                selected.append(df)
        # اگه هنوز جا هست، اولین فایل کد
        if not any(f.startswith(missing_dir + "/") for f in selected):
            for df in dir_files[:1]:
                if len(selected) < max_files:
                    selected.append(df)

    return selected


# ─── تشخیص دامنه (Scope) درخواست کاربر ───
# وقتی کاربر میگه "همه فایل‌ها رو بررسی کن" باید همه رو بخونیم، نه 25 تا
SCOPE_FULL_KEYWORDS = [
    # فارسی — درخواست بررسی کل پروژه
    "تمام فایل", "همه فایل", "کل پروژه", "تمام مسیر", "همه مسیر",
    "همه رو بررسی", "تمام رو بررسی", "سرتاسر", "همه پوشه", "تمام پوشه",
    "از ریشه تا", "از مسیر اصلی", "هر فایل", "هر پوشه", "یه دور کامل",
    "کل ساختار", "کل فولدر", "تمام فولدر", "همه فولدر",
    "فایل‌های اضافه", "فایل‌های اضافی", "فایل زائد", "فایل بلااستفاده",
    "فایل‌های بلااستفاده", "فایل‌های زائد", "فایلهای اضافی", "فایلهای بلااستفاده",
    "بلااستفاده", "استفاده نمیش", "استفاده نمی‌ش", "وصل نیست", "کار نمیکنه",
    "تمیز کردن", "پاکسازی", "حذف اضافه", "بریز تو آرشیو",
    # انگلیسی — بررسی کل پروژه
    "all files", "every file", "entire project", "whole project",
    "full scan", "full project", "clean up", "cleanup",
    "unused files", "dead code", "remove unused",
]
SCOPE_BROAD_KEYWORDS = [
    # فارسی — بررسی وسیع اما نه لزوماً همه
    "بررسی کلی", "ریفکتور", "بهینه‌سازی", "ساختار پروژه",
    "بررسی ساختار", "تحلیل ساختار", "بهبود کلی", "مرور کلی",
    "نگاهی بنداز", "یه نگاه بنداز",
    # انگلیسی
    "refactor", "restructure", "review structure", "overview", "audit",
    "broad review", "code review",
]


def _detect_request_scope(message: str, chat_history_text: str = "") -> str:
    """
    تشخیص دامنه درخواست کاربر:
    - FULL_PROJECT: کاربر صراحتاً گفته همه فایل‌ها / کل پروژه / پاکسازی
    - BROAD: بررسی وسیع (ریفکتور، ساختار، مرور کلی)
    - TARGETED: یک فیچر/فایل/باگ خاص (پیش‌فرض)

    این تابع قبل از انتخاب فایل فراخوانی میشه تا تعداد فایل‌های
    خوانده‌شده متناسب با درخواست واقعی کاربر باشه.
    """
    msg_lower = message.lower()
    # ترکیب پیام + آخرین بخش تاریخچه برای context بهتر
    context = msg_lower + " " + chat_history_text[-1000:].lower()

    # بررسی FULL_PROJECT
    for kw in SCOPE_FULL_KEYWORDS:
        if kw in context:
            return "FULL_PROJECT"

    # بررسی BROAD
    for kw in SCOPE_BROAD_KEYWORDS:
        if kw in context:
            return "BROAD"

    return "TARGETED"


def _get_max_files_for_scope(scope: str, total_code_files: int) -> int:
    """
    تعیین حداکثر فایل‌ها بر اساس دامنه درخواست.
    وقتی scope=FULL_PROJECT، تمام فایل‌ها (تا سقف context مدل) خوانده میشن.
    """
    if scope == "FULL_PROJECT":
        # تمام فایل‌ها — سقف واقعی توسط context window مدل تعیین میشه
        return min(total_code_files, 500)
    elif scope == "BROAD":
        # نیمی تا 70% فایل‌ها
        return min(max(40, int(total_code_files * 0.7)), 200)
    else:
        # TARGETED — مثل قبل
        return 25


# ─── تشخیص دامنه خطا (frontend / backend / cross) ───
# وقتی خطا مربوط به PostCSS/Vite/npm هست نباید فایل‌های Python بخونیم
_FRONTEND_ERROR_SIGNALS = [
    # ابزارها و bundlers
    "postcss", "tailwind", "vite", "webpack", "esbuild", "rollup", "next.js", "nextjs",
    "npm ", "npm:", "npx ", "yarn ", "pnpm ", "node_modules", "package.json",
    # خطاهای JS/TS
    "syntaxerror", "referenceerror", "typeerror", "module not found", "cannot find module",
    "eresolve", "etarget", "peer dep", "peer dependency", "import error", "export default",
    "module.exports", "esm", "commonjs", "cjs", "mjs",
    # فایل‌ها
    ".tsx", ".jsx", ".ts ", ".js ", ".css", ".scss", ".vue", ".svelte",
    "tsconfig", "postcss.config", "tailwind.config", "vite.config", "next.config",
    # کلمات کلیدی
    "react", "angular", "vue", "svelte", "component", "render",
    "build failed", "build error", "compile error",
]
_BACKEND_ERROR_SIGNALS = [
    # Python
    "traceback", "importerror", "modulenotfounderror", "attributeerror", "nameerror",
    "gunicorn", "uvicorn", "fastapi", "django", "flask",
    "requirements.txt", "pip ", "pip:", "pyproject.toml",
    ".py ", ".py:", "python",
    # Docker/Deploy
    "dockerfile", "docker-compose", "docker build",
    # DB
    "sqlalchemy", "alembic", "migration", "database", "psycopg",
]


def _detect_error_domain(error_text: str) -> str:
    """
    تشخیص دامنه خطا:
    - "frontend": خطا فقط مربوط به frontend (npm, PostCSS, Vite, webpack, React, ...)
    - "backend": خطا فقط مربوط به backend (Python, pip, gunicorn, FastAPI, ...)
    - "cross": خطا ممکن است مربوط به هر دو باشد یا مشخص نیست
    """
    text_lower = error_text.lower()
    fe_score = sum(1 for sig in _FRONTEND_ERROR_SIGNALS if sig in text_lower)
    be_score = sum(1 for sig in _BACKEND_ERROR_SIGNALS if sig in text_lower)

    if fe_score >= 3 and be_score <= 1:
        return "frontend"
    if be_score >= 3 and fe_score <= 1:
        return "backend"
    if fe_score >= 2 and be_score == 0:
        return "frontend"
    if be_score >= 2 and fe_score == 0:
        return "backend"
    return "cross"


# ─── خلاصه‌سازی محتوای فایل برای حالت FULL_PROJECT ───
def _condense_file_content(content: str, file_path: str, max_chars: int = 600) -> str:
    """
    استخراج ساختار فایل (imports, exports, تعریف توابع/کلاس‌ها) بدون بدنه.
    برای حالت FULL_PROJECT استفاده میشه تا همه فایل‌ها در context جا بشن.
    """
    if not content or not content.strip():
        return "(empty file)"

    lines = content.split("\n")
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    # فایل‌های کانفیگ و JSON — فقط اول فایل
    if ext in ("json", "yaml", "yml", "toml", "ini", "env", "lock"):
        snippet = "\n".join(lines[:15])
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars]
        return snippet + ("\n..." if len(lines) > 15 else "")

    # فایل‌های CSS/SCSS — فقط سلکتورها
    if ext in ("css", "scss", "sass", "less"):
        structural = []
        for line in lines[:200]:
            stripped = line.strip()
            if stripped and not stripped.startswith(("/*", "*", "//")) and (
                stripped.endswith("{") or stripped.startswith(("@import", "@media", "@keyframes"))
            ):
                structural.append(line)
        result = "\n".join(structural[:30])
        return result[:max_chars] if result else "\n".join(lines[:5])[:max_chars]

    # Python / JS / TS / JSX / TSX — استخراج ساختاری
    structural_lines = []
    # کلمات کلیدی ساختاری برای زبان‌های مختلف
    py_keywords = ("import ", "from ", "class ", "def ", "async def ", "@")
    js_keywords = (
        "import ", "export ", "require(", "module.exports",
        "function ", "async function ", "const ", "let ", "var ",
        "class ", "interface ", "type ", "enum ",
        "export default", "export const", "export function", "export class",
        "export interface", "export type", "export enum",
    )

    is_python = ext in ("py",)
    keywords = py_keywords if is_python else js_keywords

    # همیشه اول ۳ خط فایل رو نگه‌دار (معمولاً shebang, docstring, pragma)
    for line in lines[:3]:
        structural_lines.append(line)

    seen_first_lines = set(range(min(3, len(lines))))
    for i, line in enumerate(lines):
        if i in seen_first_lines:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue
        # خطوط ساختاری
        if any(stripped.startswith(kw) or stripped.lstrip().startswith(kw) for kw in keywords):
            structural_lines.append(line)

    result = "\n".join(structural_lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n..."
    elif not structural_lines or len(result) < 50:
        # اگر خط ساختاری پیدا نشد، اول فایل رو بده
        result = "\n".join(lines[:10])[:max_chars]

    return result


# ─── کاهش هوشمند حجم پرامپت برای تلاش مجدد ───
def _reduce_prompt_for_retry(prompt: str) -> str:
    """کاهش حجم پرامپت با حذف بخشی از تاریخچه، کد و لاگ‌ها"""
    if len(prompt) < 10000:
        return prompt

    result = prompt

    # 1. کاهش تاریخچه مکالمه (بزرگ‌ترین بخش قابل حذف)
    hist_start = result.find("## تاریخچه کامل مکالمه:")
    if hist_start >= 0:
        next_sect = result.find("\n## ", hist_start + 30)
        if next_sect > hist_start:
            old_hist = result[hist_start:next_sect]
            if len(old_hist) > 800:
                new_hist = "## تاریخچه کامل مکالمه:\n" + old_hist[30:][-500:] + "\n"
                result = result[:hist_start] + new_hist + result[next_sect:]

    # 2. کاهش بخش کد (حفظ نیمه اول)
    code_start = result.find("## کد فایل‌های مرتبط")
    if code_start >= 0:
        code_end = result.find("## فرمت پاسخ", code_start)
        if code_end < 0:
            code_end = result.find("## وظیفه:", code_start)
        if code_end > code_start:
            old_code = result[code_start:code_end]
            max_len = max(5000, len(old_code) // 2)
            if len(old_code) > max_len:
                result = result[:code_start] + old_code[:max_len] + "\n\n... [بخشی از فایل‌ها برای بهینه‌سازی حذف شد]\n\n" + result[code_end:]

    # 3. کاهش لاگ‌ها
    for log_marker in ["## لاگ‌های اخیر:", "## لاگ‌های بک‌اند:"]:
        log_start = result.find(log_marker)
        if log_start >= 0:
            next_sect = result.find("\n\n##", log_start + len(log_marker))
            if next_sect > log_start:
                old_logs = result[log_start:next_sect]
                if len(old_logs) > 400:
                    result = result[:log_start] + log_marker + "\n" + old_logs[len(log_marker):][-200:] + "\n" + result[next_sect:]
            break

    return result


# ─── انتخاب هوشمند مدل بر اساس آرشیو چت‌ها ───
async def _smart_select_model(db, project_id: str) -> str:
    """
    انتخاب هوشمند مدل بر اساس:
    1. بیشترین استفاده موفق در آرشیو چت‌های پروژه
    2. فقط مدل‌های فعال و با provider در دسترس
    3. اگر همه غیرفعال بودن → بهترین مدل فعال فعلی
    """
    from ...models.inspector_session import InspectorMessage, InspectorSession
    from ...models.ai_profile import ModelSettings
    from ...core.models_registry import MODEL_REGISTRY
    from ...services.ai_manager import get_ai_manager
    from sqlalchemy import func as sqlfunc, desc

    FALLBACK_MODEL = "gemini-2.0-flash"

    try:
        ai_manager = get_ai_manager()

        # ─── مرحله ۱: بررسی مدل‌های فعال ───
        db_settings = db.query(ModelSettings).all()
        db_map = {s.model_id: s for s in db_settings}

        def _is_model_available(model_id: str) -> bool:
            """بررسی فعال بودن و در دسترس بودن provider"""
            reg = MODEL_REGISTRY.get(model_id)
            if not reg:
                return False
            if reg.is_image_generator:
                return False
            # بررسی enabled
            setting = db_map.get(model_id)
            is_enabled = bool(setting.enabled) if setting else reg.enabled
            if not is_enabled:
                return False
            # بررسی provider
            try:
                if reg.provider in ai_manager._services:
                    svc = ai_manager._services[reg.provider]
                    return bool(svc.api_key) and not svc.is_in_error_state()
            except Exception:
                pass
            return False

        # ─── مرحله ۲: آمار استفاده از مدل‌ها در آرشیو پروژه ───
        # سشن‌های آرشیو شده
        archived_sessions = db.query(InspectorSession.id).filter(
            InspectorSession.project_id == project_id,
            InspectorSession.status == "archived"
        ).subquery()

        # آمار مدل‌ها: تعداد استفاده + تعداد verified=True
        from sqlalchemy import case as sql_case
        model_stats = db.query(
            InspectorMessage.model_id,
            sqlfunc.count(InspectorMessage.id).label("total_uses"),
            sqlfunc.sum(
                sql_case((InspectorMessage.backend_verified == True, 1), else_=0)
            ).label("success_count")
        ).filter(
            InspectorMessage.session_id.in_(archived_sessions),
            InspectorMessage.role == "assistant",
            InspectorMessage.model_id.isnot(None)
        ).group_by(InspectorMessage.model_id).order_by(
            desc("total_uses")
        ).all()

        # از آرشیو: مدل‌هایی که زیاد استفاده شدن و موفق بودن
        for stat in model_stats:
            mid = stat[0]  # model_id
            if mid and _is_model_available(mid):
                slog.info(f"[smart-select] از آرشیو: انتخاب {mid} (استفاده: {stat[1]}, موفق: {stat[2]})")
                return mid

        # ─── مرحله ۳: سشن فعال فعلی ───
        active_sessions = db.query(InspectorSession.id).filter(
            InspectorSession.project_id == project_id,
            InspectorSession.status == "active"
        ).subquery()

        active_model_stats = db.query(
            InspectorMessage.model_id,
            sqlfunc.count(InspectorMessage.id).label("total_uses")
        ).filter(
            InspectorMessage.session_id.in_(active_sessions),
            InspectorMessage.role == "assistant",
            InspectorMessage.model_id.isnot(None)
        ).group_by(InspectorMessage.model_id).order_by(
            desc("total_uses")
        ).all()

        for stat in active_model_stats:
            mid = stat[0]
            if mid and _is_model_available(mid):
                slog.info(f"[smart-select] از سشن فعال: انتخاب {mid} (استفاده: {stat[1]})")
                return mid

        # ─── مرحله ۴: بهترین مدل فعال با بالاترین اولویت ───
        # مدل‌های دارای قابلیت CODE ترجیح دارند
        from ...core.models_registry import ModelCapability

        best_available = None
        best_score = -1
        for model_id, model in MODEL_REGISTRY.items():
            if not _is_model_available(model_id):
                continue
            score = 0
            caps = model.capabilities
            if ModelCapability.CODE in caps:
                score += 10
            if ModelCapability.REASONING in caps:
                score += 5
            setting = db_map.get(model_id)
            if setting and setting.priority:
                score += max(0, 10 - setting.priority)  # اولویت ۱ = بالاترین
            if score > best_score:
                best_score = score
                best_available = model_id

        if best_available:
            slog.info(f"[smart-select] بهترین مدل فعال: {best_available} (امتیاز: {best_score})")
            return best_available

    except Exception as e:
        slog.warning(f"[smart-select] خطا: {e}")

    slog.info(f"[smart-select] فالبک به {FALLBACK_MODEL}")
    return FALLBACK_MODEL


# ── Batch Task Status & Cancel ───────────────────────────────────────

@router.get("/inspector/smart-chat/batch-status/{task_key}")
async def batch_task_status(task_key: str):
    """بررسی وضعیت background batch task"""
    info = _get_batch_task(task_key)
    if not info:
        return {"success": True, "exists": False}
    return {
        "success": True,
        "exists": True,
        "status": info.get("status", "unknown"),
        "batch_count": info.get("batch_count", 0),
        "total_read": info.get("total_read", 0),
        "flow_type": info.get("flow_type", "action"),
        "event_count": len(info.get("events", [])),
    }


@router.get("/inspector/smart-chat/batch-active/{project_id}")
async def batch_task_active(project_id: str):
    """پیدا کردن task فعال برای یک پروژه — frontend هنگام mount صدا میزنه"""
    _cleanup_old_batch_tasks()
    for key, info in _BATCH_TASKS.items():
        if info.get("project_id") == project_id and info.get("status") == "running":
            return {
                "success": True,
                "has_active": True,
                "task_key": key,
                "status": "running",
                "batch_count": info.get("batch_count", 0),
                "total_read": info.get("total_read", 0),
                "flow_type": info.get("flow_type", "action"),
            }
    return {"success": True, "has_active": False}


@router.post("/inspector/smart-chat/batch-cancel/{task_key}")
async def batch_task_cancel(task_key: str):
    """لغو background batch task — دکمه توقف"""
    info = _get_batch_task(task_key)
    if not info:
        return {"success": False, "error": "task not found"}
    task = info.get("task")
    if task and not task.done():
        task.cancel()
    info["status"] = "cancelled"
    info["events"].append(("progress", {"step": "cancelled", "message": "⏹️ پردازش توسط کاربر لغو شد"}))
    info["new_event"].set()
    # پاکسازی
    if task_key in _BATCH_TASKS:
        del _BATCH_TASKS[task_key]
    return {"success": True, "message": "cancelled"}


# ────────────────────────────────────────────────
# 🧠 تبدیل پیام کاربر به پرامپت ساختارمند
# ────────────────────────────────────────────────

class EnhancePromptRequest(BaseModel):
    """درخواست بهینه‌سازی پرامپت"""
    project_id: str
    message: str  # پیام اصلی کاربر
    model_id: str  # مدل بهینه‌ساز (مدل فعال تنظیمات)
    target_model_id: Optional[str] = None  # مدل هدف (که قراره جواب بده)
    target_model_max_output: Optional[int] = None  # ظرفیت خروجی مدل هدف
    chat_history: Optional[List[dict]] = None  # تاریخچه چت
    mode: str = "chat"  # "chat" | "visual_debug"


@router.post("/inspector/enhance-prompt")
async def enhance_prompt_endpoint(request: EnhancePromptRequest, db: Session = Depends(get_db)):
    """تبدیل پیام ساده کاربر به پرامپت ساختارمند و دقیق برای مدل هدف"""
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    from ...core.models_registry import get_model as _ep_get_model

    ai_manager = get_ai_manager()

    # اطلاعات مدل هدف
    target_info = ""
    if request.target_model_id:
        _treg = _ep_get_model(request.target_model_id)
        _tmax = getattr(_treg, 'max_tokens', 8192) if _treg else 8192
        _tctx = getattr(_treg, 'context_window', 128000) if _treg else 128000
        target_info = f"مدل هدف: {request.target_model_id} (خروجی: {_tmax} توکن, context: {_tctx})"
    elif request.target_model_max_output:
        target_info = f"ظرفیت خروجی مدل هدف: {request.target_model_max_output} توکن"

    # تاریخچه چت (خلاصه)
    history_context = ""
    if request.chat_history:
        recent = request.chat_history[-10:]
        history_parts = []
        for msg in recent:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:200]
            history_parts.append(f"[{role}]: {content}")
        history_context = "\n".join(history_parts)

    system_prompt = """تو یک متخصص پرامپت‌نویسی (Prompt Engineer) هستی.
وظیفه‌ات تبدیل پیام ساده کاربر به پرامپت ساختارمند و دقیق برای مدل AI هدف است.

## قوانین:
1. **حفظ هدف اصلی**: معنی و هدف پیام کاربر حفظ شود — فقط ساختارمند کن
2. **ساختار خروجی مدل**: به مدل بگو خروجیش چه ساختاری داشته باشه (تحلیل مختصر + کد کامل)
3. **مدیریت بودجه خروجی**: به مدل تاکید کن تحلیل متنی حداکثر ۱۰ خط باشه و بودجه اصلی برای کد/action_plan باشه
4. **anti-repetition**: تاکید کن "تکرار ممنوع — هر جمله فقط یک بار"
5. **action_plan اجباری**: اگر درخواست کدنویسی/تغییر است، بگو حتما action_plan JSON بده — اما **هرگز** نمونه JSON ننویس و فرمت خاصی تعیین نکن (سیستم خودش فرمت مناسب رو به مدل میده)
6. **زبان فارسی**: پرامپت خروجی فارسی باشه
7. **context چت**: اگر تاریخچه چت هست، مرتبط‌ترین بخش‌ها رو در پرامپت بگنجان
8. **فقط پرامپت**: خروجی فقط متن پرامپت باشه — بدون توضیح اضافه، بدون پیشگفتار
9. **تجزیه درخواست پیچیده**: اگر درخواست شامل چند کار مستقل یا فایل‌های مختلف هست:
   - آخر پرامپت ساختارمند، یک بخش `## مراحل اجرا:` اضافه کن
   - هر مرحله یک خط با فرمت `[STEP N] توضیح مرحله` باشه
   - **هر توضیح مرحله باید کوتاه (≤ ۲۰ کلمه) و فقط task-specific باشد** —
     قوانین سازگاری/anti-rewrite در base prompt هست و در هر step description
     **تکرار نشود** (executeMultiStep خودش این rules را به stepPrompt اضافه می‌کند)
   - مراحل باید مستقل و قابل اجرای جداگانه باشن
   - اگه درخواست ساده هست و نیاز به تجزیه نداره (فقط ۱ کار)، بخش مراحل نذار
   - ⚠️ اگر کاربر صراحتاً گفته «فقط مرحله اول» یا «فقط مرحله X» یا تعداد مراحل مشخص کرده → حتماً رعایت کن و فقط همان تعداد مرحله بساز
   - 🚫 قوانین سازگاری (نام‌گذاری یکسان، ساخت روی مراحل قبلی، عدم بازنویسی)
     فقط **یک بار** در ابتدای base prompt بنویس، نه در هر step description.
     مثال خوب: `[STEP 1] افزودن فیلد API_V1_PREFIX به Settings در app/config.py`
     مثال بد: `[STEP 1] افزودن فیلد ... — تمام نام‌گذاری‌ها باید یکسان ... این مرحله باید روی ... هرگز فایلی را که در مرحله قبل ...`
10. **ایمنی دیپلوی**: در پرامپت تاکید کن:
   - کد تولیدی باید بدون هیچ خطای سینتکس، import و تایپ باشد
   - وابستگی‌ها با نسخه سازگار پین شوند — هرگز نسخه‌ای که مطمئن نیستی وجود داره پین نکن
   - قبل از نوشتن کد، ذهنی مراحل بیلد و دیپلوی رو شبیه‌سازی کن
   - 🚨 **اگر backend_logs دارای error trace است**:
     * **اول** نام دقیق package/symbol/خط که شکست خورده را از log جاری
       استخراج کن — نه از description کاربر
     * کاربر ممکن است error قبلی را تکرار کند یا اشتباه نام بدهد. **log
       منبع حقیقت است**
     * مثال: کاربر می‌گوید «pydantic-core fail شد» ولی log می‌گوید
       `Failed to build tiktoken` → روی tiktoken کار کن، نه pydantic-core
   - 🚨 **اگر error مربوط به wheel/compile در Render/Python deploy است**:
     * چک کن نسخهٔ Python (در log معمولاً `python3.X.Y` آمده)
     * Python 3.13+، به‌خصوص 3.14, اکثر packages هنوز cp31X wheel ندارند
     * **اولین راه‌حل**: ایجاد یا ویرایش `runtime.txt` با `python-3.11.10`
       یا `python-3.12.7` در ریشهٔ پروژه (تنها این یک خط مشکل را حل می‌کند)
     * **هرگز** پیشنهاد نده «maturin و setuptools-rust به requirements اضافه کن»
       چون این‌ها هم Rust compile نیاز دارند و در همان محیط read-only شکست
       می‌خورند
     * Render Native Python runtime از Dockerfile **استفاده نمی‌کند** —
       تغییر Dockerfile روی deploy اثری ندارد مگر اینکه پروژه explicit
       Docker service باشد
11. **حل کامل و یکجا**: در پرامپت تاکید کن:
   - قبل از هر تغییر، کل زنجیره وابستگی رو ردیابی کن
   - اگر فایل config تغییر میکنه، تمام configهای مرتبط هم بررسی بشن
   - قبل از نوشتن فایل .js config، حتماً package.json فیلد "type" رو بررسی کن (ESM vs CJS)
   - مشکل رو نیمه‌کاره حل نکن — تمام فایل‌های تحت تأثیر در action_plan باشن
12. **🆕 Render operations (env vars, restart, deploy)**: اگر مشکل از
   متغیرهای محیطی Render یا نیاز به restart/redeploy است (نه فقط کد):
   - در پرامپت تاکید کن که AI می‌تواند `render_actions` در action_plan
     شامل کند (نه فقط `files`)
   - مثال‌ها: تنظیم DATABASE_URL، تنظیم API_KEY، restart service، trigger deploy
   - format: `{"type": "set_env_var", "service_name": "...", "key": "...", "value": "..."}`
   - این برای موارد deploy fail که از env var missing است (مثل
     `ConnectionRefusedError`) ضروری است
13. **ممنوعیت بازنویسی مخرب**: در پرامپت تاکید کن:
   - هرگز فایل موجود رو از صفر بازننویس — فقط بخش‌های مربوط به درخواست تغییر کنند
   - قابلیت‌های موجود فایل (state, handlers, UI sections) حذف نشوند
   - قبل از ایجاد فایل جدید، بررسی شود آیا کامپوننت مشابه وجود دارد
   - هرگز عملکرد واقعی (iframe, chart, API call) با placeholder خالی جایگزین نشود
   - 🚨 **قانون اساسی state-awareness**: قبل از پیشنهاد ساختن فایل
     جدید، **حتماً** چک کن آیا آن فایل از قبل در repo موجود است:
     * اگر بله → operation باید `modify` باشد، content جدید را با
       حفظ ساختار قبلی بنویس (مثلاً اگر runtime.txt با
       python-3.11.10 موجود است و کاربر می‌خواهد به python-3.12.7
       تغییر دهد، operation=modify نه create)
     * اگر کاربر گفت «بساز» و فایل موجود است، منظورش «به‌روزرسانی کن» است
     * تاکید: «قبل از create، list فایل‌های موجود و previously_read_files
       را چک کن»
13. **فهم دقیق درخواست کاربر**: در پرامپت تاکید کن:
   - کلمات کاربر تحت‌اللفظی خوانده شوند: «فقط» = ONLY، «نباید» = ممنوع
   - معنی درخواست هرگز برعکس تفسیر نشود

## ⛔ ممنوعیت‌ها:
- هرگز بلوک ```json با نمونه action_plan ننویس — فرمت JSON رو سیستم تعیین می‌کنه نه تو
- هرگز از کلید "action_plan" یا "action" در نمونه JSON استفاده نکن
- خروجی فقط متن پرامپت ساختارمند باشه — بدون بلوک‌های کد JSON"""

    user_prompt = f"""## پیام اصلی کاربر:
{request.message}

## حالت: {"دیباگ بصری (تحلیل عکس + لاگ)" if request.mode == "visual_debug" else "چت عادی (سوال/درخواست)"}
{f"## {target_info}" if target_info else ""}
{f"## تاریخچه چت اخیر:{chr(10)}{history_context}" if history_context else ""}

## دستور:
این پیام رو به پرامپت ساختارمند تبدیل کن. فقط متن پرامپت بهینه‌شده رو برگردون."""

    try:
        response = await ai_manager.generate(
            model_id=request.model_id,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ],
            max_tokens=2048,
            temperature=0.3,
        )
        enhanced = response.content.strip()
        # 🧹 حذف بلوک‌های استدلال/reasoning (مدل‌هایی مثل deepseek-reasoner)
        enhanced = _strip_reasoning_blocks(enhanced)
        # حذف بکتیک‌ها اگه مدل داخل بلوک کد گذاشته
        if enhanced.startswith("```") and enhanced.endswith("```"):
            enhanced = enhanced.strip("`").strip()
            if enhanced.startswith("markdown\n") or enhanced.startswith("text\n"):
                enhanced = enhanced.split("\n", 1)[1] if "\n" in enhanced else enhanced

        # استخراج مراحل اگه درخواست تجزیه شده
        steps = []
        import re as _ep_re
        _step_pattern = _ep_re.compile(r'\[STEP\s*(\d+)\]\s*(.+)', _ep_re.IGNORECASE)
        for _line in enhanced.split('\n'):
            _m = _step_pattern.match(_line.strip())
            if _m:
                steps.append({
                    "step_number": int(_m.group(1)),
                    "description": _m.group(2).strip(),
                })

        # اگه مراحل پیدا شد، پرامپت پایه رو بدون بخش مراحل جدا کن
        base_prompt = enhanced
        if steps:
            # حذف بخش مراحل از پرامپت پایه
            _step_section_idx = enhanced.find('## مراحل اجرا')
            if _step_section_idx == -1:
                _step_section_idx = enhanced.find('[STEP 1]')
            if _step_section_idx > 0:
                base_prompt = enhanced[:_step_section_idx].strip()

        return {
            "success": True,
            "enhanced_prompt": enhanced,
            "base_prompt": base_prompt if steps else enhanced,
            "steps": steps if steps else [],
            "original": request.message,
            "enhancer_model": request.model_id,
            "tokens_used": getattr(response, 'tokens_used', 0) or 0,
        }
    except Exception as e:
        return {
            "success": False,
            "enhanced_prompt": request.message,  # فالبک: همون پیام اصلی
            "original": request.message,
            "error": str(e)[:200],
        }


# 🔴 (anti-parallel) — قفل per-project برای smart-chat. وقتی یک agent در
# حال اجراست، درخواست دوم (مثلاً از retry یا double-click) نباید همزمان
# اجرا شود — چون SSE هر دو event می‌فرستن، چت قاتی می‌شود (همان شکایت
# کاربر دربارهٔ ترتیب پیام‌ها).
_SMART_CHAT_ACTIVE: Dict[str, float] = {}  # project_id → start_timestamp
_SMART_CHAT_LOCK_TIMEOUT = 600  # ۱۰ دقیقه — اگر چیزی بیشتر طول کشید، احتمالاً hung است


@router.post("/inspector/smart-chat")
async def smart_chat(request: SmartChatRequest, db: Session = Depends(get_db)):
    """
    چت هوشمند: پیام کاربر رو تحلیل میکنه و:
    1. اگر سؤال باشه: با اشراف کامل پاسخ میده
    2. اگر درخواست اقدام باشه: تحلیل + پیشنهاد اصلاح + دکمه اعمال
    SSE streaming برای گزارش لحظه‌ای
    """
    import time as _time_sc
    from fastapi.responses import StreamingResponse
    from ...models.project import Project
    from ...services.github_import import get_github_import_service
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    # 🔴 (anti-parallel) — اگر چت دیگری برای همین project در حال اجراست،
    # درخواست جدید را رد کن. این جلوی interleaved SSE events را می‌گیرد که
    # چت را به‌هم می‌ریخت.
    _now_sc = _time_sc.time()
    _pid_key = str(request.project_id or "")
    _active_since = _SMART_CHAT_ACTIVE.get(_pid_key)
    if _active_since and (_now_sc - _active_since) < _SMART_CHAT_LOCK_TIMEOUT:
        slog.info(f"[smart-chat] rejecting concurrent request for project {_pid_key} (active for {_now_sc - _active_since:.1f}s)")
        async def _reject_stream():
            _msg = (
                "⏳ یک درخواست قبلی هنوز در حال پردازش است. لطفاً صبر کن تا تمام شود "
                "(یا صفحه را reload کن اگر بیش از حد طول کشید)."
            )
            yield f"event: error\ndata: {json.dumps({'message': _msg}, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps({'success': False, 'reason': 'concurrent_request'})}\n\n"
        return StreamingResponse(_reject_stream(), media_type="text/event-stream")
    _SMART_CHAT_ACTIVE[_pid_key] = _now_sc

    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    # استخراج اطلاعات GitHub
    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from ...models.setting import Setting as _ChatSetting
        token = _ChatSetting.get_value(db, "api_key_github") or ""

    # 🆕 (inspector-scan) — تشخیص intent برای trigger خودکار scan موردی.
    # اگر کاربر در حال درخواست بررسی/اصلاح است، به‌جای single-shot smart-chat
    # (که سطحی است)، یک deep selective scan trigger می‌کنیم. خروجی به همان
    # session لاگ می‌شود و فرانت‌اند با reload messages آن را نمایش می‌دهد.
    # اگر intent تشخیص نشد → smart-chat معمولی ادامه می‌یابد.
    # 🆕 (v3 regression fix) — اگر frontend درخواست کرده intent disable
    # باشد (مثلاً stepwise execution در حال اجراست)، intent path کاملاً
    # skip می‌شود. بدون این، executeMultiStep response های scan_initiated
    # را نمی‌فهمد و هیچ action_plan ای تولید نمی‌شود → 0 file changed.
    _selective_scan_disabled = not getattr(request, "enable_selective_scan", True)
    # 🔴 (anti-overreach) — روی retry هرگز intent-path/scan اجرا نشود.
    # retry یعنی «همان کار قبلی را دوباره کن»، نه «یک scan جدید راه بنداز».
    # این یکی از دلایل «scan ناخواسته» در سشن‌های کاربر بود.
    _is_retry_attempt = bool(getattr(request, "retry_attempt", None))
    if _is_retry_attempt:
        _selective_scan_disabled = True
        slog.info("[smart-chat] retry detected — selective scan disabled to prevent unwanted auto-scan")
    if _selective_scan_disabled:
        slog.info("[smart-chat] selective-scan intent path disabled by request flag — direct to chat")
    # یک sentinel exception برای exit تمیز از intent path. توسط except کلی
    # outer گرفته می‌شود و fallback به smart-chat معمولی انجام می‌گیرد.
    class _SkipIntentPath(Exception):
        pass
    try:
        if _selective_scan_disabled:
            raise _SkipIntentPath()
        from ...services.inspector_intent_resolver import resolve_intent_from_chat_context
        from ...services.inspector_scan_bridge import (
            trigger_inspector_selective_scan,
            get_or_create_active_session_for_project,
            is_scan_active_for_session,
        )

        # 🆕 (v3 chat-history) — chat_history را به resolver پاس بده تا
        # continuation detection ممکن شود. در حالت smart-chat تنها
        # request.chat_history در دسترس است (که از frontend می‌آید).
        _hist_for_intent: List[Dict[str, Any]] = []
        if request.chat_history:
            try:
                _hist_for_intent = [
                    {"role": m.role, "content": m.content}
                    for m in request.chat_history
                    if hasattr(m, "role") and hasattr(m, "content")
                ]
            except Exception:
                _hist_for_intent = []

        intent = resolve_intent_from_chat_context(
            user_message=request.message,
            backend_logs=request.backend_logs,
            console_logs=request.console_logs,
            frontend_url=request.frontend_url,
            page_url=request.page_url,
            api_paths=request.api_paths,
            linked_task=request.linked_task,
            screenshots=request.screenshots,
            mode=request.inspector_mode or "chat",
            chat_history=_hist_for_intent or None,
        )

        if intent.should_scan:
            sess_id = get_or_create_active_session_for_project(request.project_id)
            if sess_id and not is_scan_active_for_session(sess_id):
                _scan_res = await trigger_inspector_selective_scan(
                    session_id=sess_id,
                    project_id=request.project_id,
                    user_message=request.message,
                    intent=intent,
                    model_id=request.model_ids[0] if request.model_ids else None,
                )
                # 🆕 (clarify-first) — اگر deep scan قبل از شروع، scope را
                # مبهم تشخیص داد و ask_user log کرد، یک پیام scan_clarify
                # به فرانت می‌فرستیم تا UI پیام جدید را از DB load کند.
                if _scan_res.get("status") == "needs_clarification":
                    async def _scan_clarify_stream():
                        payload = {
                            "kind": "scan_clarification_needed",
                            "session_id": sess_id,
                            "content": (
                                "🤔 قبل از شروع اسکن عمیق، یک سوال کوتاه دارم — "
                                "لطفاً به سوال در چت پاسخ بده."
                            ),
                        }
                        yield f"event: scan_clarification_needed\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    return StreamingResponse(_scan_clarify_stream(), media_type="text/event-stream")
                if _scan_res.get("success"):
                    async def _scan_init_stream():
                        payload = {
                            "kind": "scan_initiated",
                            "scan_id": _scan_res.get("scan_id"),
                            "session_id": sess_id,
                            "content": (
                                "🔍 **در حال اسکن موردی عمیق...**\n\n"
                                f"بر اساس پیامتان و context (logs/URL) تشخیص داده شد که نیاز به "
                                f"بررسی عمیق دارد. دلیل: `{intent.reason}` — "
                                f"اطمینان: {int(intent.confidence * 100)}%.\n\n"
                                f"تعداد {len(intent.custom_paths)} مسیر را scope کردم. "
                                "پیشنهاد‌ها چند دقیقه دیگر در همین چت ظاهر می‌شوند."
                            ),
                            "intent": {
                                "reason": intent.reason,
                                "matched_keywords": intent.matched_keywords[:5],
                                "custom_paths": intent.custom_paths[:10],
                                "selected_sections": intent.selected_sections,
                                "visual_debug": intent.visual_debug,
                                "confidence": intent.confidence,
                            },
                        }
                        # SSE فرمت با event prefix که frontend smart-chat انتظار دارد
                        yield f"event: scan_initiated\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

                    return StreamingResponse(_scan_init_stream(), media_type="text/event-stream")
            elif sess_id and is_scan_active_for_session(sess_id):
                async def _scan_busy_stream():
                    payload = {
                        "kind": "scan_already_running",
                        "session_id": sess_id,
                        "content": (
                            "⚠️ یک اسکن موردی دیگر در این session در حال اجراست. "
                            "لطفاً منتظر بمانید تا کامل شود."
                        ),
                    }
                    yield f"event: scan_already_running\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                return StreamingResponse(_scan_busy_stream(), media_type="text/event-stream")
    except Exception as _intent_e:
        slog.warning(f"[smart-chat] selective-scan path failed; fallback to chat: {_intent_e}")

    model_ids = request.model_ids

    # ─── انتخاب هوشمند مدل بر اساس آرشیو چت‌ها ───
    if not model_ids:
        primary_model = await _smart_select_model(db, request.project_id)
    else:
        primary_model = model_ids[0]

    # 🆕 (anti-stuck-loop) — اگر retry است و مدل قبلی نتوانست action_plan
    # تولید کند، خودکار به fallback model سوئیچ کن. این از حلقه‌ای که در
    # آن همان مدل با همان context همان جواب ناقص می‌دهد جلوگیری می‌کند.
    _is_retry = bool(request.retry_attempt and request.retry_attempt >= 1)
    if _is_retry and request.retry_attempt and request.retry_attempt >= 2:
        try:
            _fb_model = ai_manager.find_fallback_model(primary_model) if 'ai_manager' in dir() else None
            if not _fb_model:
                from ...services.ai_manager import get_ai_manager as _gam
                _fb_model = _gam().find_fallback_model(primary_model)
            if _fb_model and _fb_model != primary_model:
                slog.info(f"[smart-chat retry≥2] auto-switching {primary_model} → {_fb_model}")
                primary_model = _fb_model
        except Exception as _e:
            slog.warning(f"[smart-chat retry] fallback model lookup failed: {_e}")

    # 🆕 اگر ریپلای به پیام مدل خاصی زده شده، از همون مدل استفاده کن
    reply_model_used = False
    reply_model_status = None  # None | "used" | "not_found" | "no_credit"
    if request.reply_to and request.reply_to.model_id:
        reply_model_id = request.reply_to.model_id
        try:
            from ...core.models_registry import get_model as get_registry_model
            from ...services.ai_manager import get_ai_manager as get_aim
            aim = get_aim()
            registry_model = get_registry_model(reply_model_id)

            if registry_model is None:
                # الف: مدل از رجیستری حذف شده
                reply_model_status = "not_found"
            else:
                # بررسی اینکه provider در دسترسه (کلید API معتبر)
                from ...core.models_registry import ModelProvider
                provider = registry_model.provider
                if isinstance(provider, str):
                    try:
                        provider = ModelProvider(provider)
                    except ValueError:
                        provider = None

                if provider and provider not in aim._services:
                    # ب: provider (کلید API) در دسترس نیست
                    reply_model_status = "no_credit"
                else:
                    # مدل وجود داره و provider فعاله
                    # بررسی فعال بودن مدل
                    is_enabled = aim.get_enabled_status(reply_model_id)
                    if not is_enabled:
                        # مدل غیرفعاله → فعالش کن (temporary)
                        from ...models.ai_profile import ModelSettings
                        setting = db.query(ModelSettings).filter(
                            ModelSettings.model_id == reply_model_id
                        ).first()
                        if setting:
                            setting.enabled = 1
                        else:
                            setting = ModelSettings(model_id=reply_model_id, enabled=1)
                            db.add(setting)
                        db.commit()

                    primary_model = reply_model_id
                    reply_model_used = True
                    reply_model_status = "used"
        except Exception:
            pass  # خطا در بررسی → از مدل پیش‌فرض استفاده میشه

    async def event_stream():
        github_svc = get_github_import_service()
        ai_manager = get_ai_manager()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        nonlocal primary_model  # 🆕 (فاز ۲) — اجازهٔ override به Claude برای کارهای کد/خطا

        # 🆕 محاسبه ظرفیت مدل برای محدود کردن حجم پرامپت
        from ...core.models_registry import get_model as get_reg_model
        reg_model = get_reg_model(primary_model)
        model_context_window = 32000  # پیش‌فرض
        model_max_output = 16384  # پیش‌فرض سخاوتمند (مدل‌های رجیستری مقدار واقعی دارند)
        if reg_model:
            model_context_window = getattr(reg_model, 'context_window', 32000)
            model_max_output = getattr(reg_model, 'max_tokens', 16384)

        # حداکثر کاراکتر ورودی ≈ (context_window - max_output) × 3 (تقریب توکن به کاراکتر)
        max_input_chars = max(8000, (model_context_window - model_max_output) * 3)

        # 🆕 اطلاع‌رسانی درباره انتخاب مدل ریپلای
        if reply_model_used:
            yield sse("progress", {
                "step": "reply_model",
                "message": f"↩️ ریپلای به پیام مدل {primary_model} — از همان مدل استفاده می‌شود"
            })
        elif reply_model_status == "not_found":
            yield sse("progress", {
                "step": "reply_model_fallback",
                "message": f"⚠️ مدل {request.reply_to.model_id} دیگر در دسترس نیست — از مدل {primary_model} استفاده می‌شود"
            })
        elif reply_model_status == "no_credit":
            yield sse("progress", {
                "step": "reply_model_fallback",
                "message": f"⚠️ اعتبار مدل {request.reply_to.model_id} به پایان رسیده — از مدل {primary_model} استفاده می‌شود"
            })

        yield sse("progress", {
            "step": "analyzing",
            "message": f"🤖 مدل {primary_model} در حال تحلیل درخواست شما..."
        })

        # 📋 دستورات عمومی سیستم — از منبع حقیقت واحد (_build_general_instructions_list)
        # هر تغییری در اون تابع بدی، هم اینجا (پرامپت مدل) و هم در فرانت (پنل دستورات) منعکس میشه
        _proj_name = project.name or "نامشخص"
        _proj_tech = project.technologies or "نامشخص"
        _proj_github = f"{owner}/{repo}" if owner and repo else "نامشخص"

        _gi_list = _build_general_instructions_list(_proj_name, _proj_tech, _proj_github)
        general_instructions_text = _build_general_instructions_text(_gi_list)

        # 🔗 (Bug C7 Bridge Phase 2) — task context block (اگر task_id بود)
        # ترتیب نهایی system prompt (به ترتیب تزریق به prefix):
        #   1. task context (اگر باشد) — جدیدترین، بالاترین اولویت
        #   2. memory (همیشه فعال)
        #   3. training (الگوها و کانوانشن‌ها)
        #   4. general_instructions_text (دستورات عمومی سیستم)
        # ما از انتها به ابتدا prefix می‌کنیم تا ترتیب صحیح حفظ شود.

        # 🆕 (C7v2 Section 3) — Training block (الگوها و کانوانشن‌ها)
        _training_block, _training_count = _build_training_block(request.project_id, db)
        _training_size = 0
        if _training_block:
            general_instructions_text = _training_block + "\n\n" + general_instructions_text
            _training_size = len(_training_block.encode("utf-8"))
            logger.info(
                f"smart-chat: training block injected — "
                f"fields={_training_count}, size={_training_size}B"
            )

        # 🆕 (C7v2 Section 2) — Memory block (حافظهٔ ثابت پروژه)
        _memory_block, _memory_count = _build_memory_block(request.project_id, db)
        _memory_size = 0
        if _memory_block:
            general_instructions_text = _memory_block + "\n\n" + general_instructions_text
            _memory_size = len(_memory_block.encode("utf-8"))
            logger.info(
                f"smart-chat: memory block injected — "
                f"fields={_memory_count}, size={_memory_size}B"
            )

        # 🔗 (C7 Phase 2) — Task context block (highest priority)
        task_context_block: Optional[str] = None
        if getattr(request, "task_id", None):
            task_context_block = _build_task_context_block(request.task_id)
            if task_context_block:
                general_instructions_text = (
                    task_context_block + "\n\n" + general_instructions_text
                )
                logger.info(
                    f"smart-chat: task_id={request.task_id} — "
                    f"context block injected ({len(task_context_block)} chars), "
                    f"memory_fields_count={_memory_count}, "
                    f"memory_block_size_bytes={_memory_size}, "
                    f"training_fields_count={_training_count}, "
                    f"training_block_size_bytes={_training_size}"
                )
            else:
                logger.warning(
                    f"smart-chat: task_id={request.task_id} provided but "
                    f"_build_task_context_block returned None"
                )

        # ساخت تاریخچه غنی برای مدل (تا ۲۰۰ پیام آخر)
        history_text = ""
        if request.chat_history:
            for msg in request.chat_history[-200:]:
                role_label = "کاربر" if msg.role == "user" else "AI" if msg.role == "assistant" else "سیستم"
                history_text += f"[{role_label}]: {msg.content}\n"

        # ساخت لیست فایل‌های قبلاً خوانده‌شده — هم برای آگاهی و هم برای گسترش دامنه
        prev_read_files = request.previously_read_files or []
        prev_files_hint = ""
        if prev_read_files:
            prev_files_hint = "\n## 📂 فایل‌های قبلاً بررسی‌شده در این مکالمه:\n"
            prev_files_hint += "\n".join(f"  ✓ {f}" for f in prev_read_files[-60:])
            prev_files_hint += f"\n(مجموعاً {len(prev_read_files)} فایل)\n"
            prev_files_hint += "\n### 🔴 نکته مهم درباره این فایل‌ها:\n"
            prev_files_hint += "- اگر مشکل **هنوز حل نشده**: مشکل احتمالاً در فایلی **خارج از این لیست** است\n"
            prev_files_hint += "- فایل‌های وابسته، config ها، types، و لایه‌های دیگر را بررسی کن\n"
            prev_files_hint += "- اگر لازم شد فایل قبلی را هم ببینی ببین، ولی حتماً فایل‌های جدید هم اضافه کن\n"
            prev_files_hint += "- **دامنه بررسی هر بار باید بزرگ‌تر شود نه کوچک‌تر**\n"

        # ساخت context ریپلای (بدون محدودیت 50 پیامی)
        reply_context_text = ""
        if request.reply_to:
            reply_role = "کاربر" if request.reply_to.role == "user" else "AI" if request.reply_to.role == "assistant" else "سیستم"
            reply_context_text = f"\n## ⬆️ پیام ریپلای‌شده (کاربر دارد به این پیام پاسخ می‌دهد):\n"
            reply_context_text += f"[{reply_role}]: {request.reply_to.content}\n"
            if request.reply_to.model_id:
                reply_context_text += f"(مدل: {request.reply_to.model_id})\n"

            # پیام‌های اطراف برای context بیشتر
            if request.reply_to.context_messages:
                reply_context_text += "\n### پیام‌های اطراف (context):\n"
                for ctx_msg in request.reply_to.context_messages:
                    ctx_role = "کاربر" if ctx_msg.get("role") == "user" else "AI" if ctx_msg.get("role") == "assistant" else "سیستم"
                    reply_context_text += f"[{ctx_role}]: {ctx_msg.get('content', '')[:500]}\n"

        # ساخت context لاگ‌ها
        logs_text = ""
        if request.backend_logs:
            errors = [l for l in request.backend_logs if l.get('level') in ('error', 'warn')]
            for log in errors[-15:]:
                logs_text += f"[{log.get('level', 'info').upper()}] {log.get('message', '')[:200]}\n"

        # --- مرحله ۲: طبقه‌بندی پیام (سؤال vs اقدام) ---
        classify_prompt = f"""## وظیفه: منظور واقعی کاربر را بفهم و طبقه‌بندی کن.

## تاریخچه مکالمه:
{history_text[-4000:]}
{reply_context_text if reply_context_text else ''}
## پیام جدید کاربر:
{request.message}

## اصل کلیدی: به معنا و نیت پیام توجه کن، نه فقط کلمات ظاهری.
کاربران اغلب منظورشان را غیرمستقیم بیان می‌کنند. باید لابلای حرفشان را بخوانی:
- "کار نمیکنه" = می‌خواهد اصلاح شود → ACTION
- "چرا اینجوری شد؟" + اشاره به مشکل = می‌خواهد علت مشکل پیدا و حل شود → ACTION
- "باز هم همون مشکل" = مشکل قبلی حل نشده، باید دوباره بررسی شود → ACTION
- "چرا اینجوری شد؟" بدون اشاره به مشکل خاص = سؤال نظری → QUESTION
- "این چیه؟"، "توضیح بده"، "فرقشون چیه؟" = سؤال دانشی → QUESTION
- لحن عصبانی/ناراحت (مثل "دوباره خراب شد!") = مشکل دارد → ACTION
- پیام کوتاه بعد از گزارش خطا ("آره"، "همونه"، "درستش کن") = ادامه بحث قبلی → ACTION
- لاگ خطا، stack trace، TypeError، console error = گزارش خطا → ERROR_LOG
- ریپلای به لاگ خطا = گزارش خطا → ERROR_LOG

## توجه به تاریخچه:
- اگر پیام کوتاه و مبهم است (مثل "آره"، "نه هنوز"، "همونه") حتماً تاریخچه را بخوان تا بفهمی در ادامه چه بحثی است
- اگر آخرین پیام AI راجع به خطا/اصلاح بوده و کاربر ادامه داده → همان نوع قبلی
- اگر کاربر به پاسخ AI ریپلای زده و مشکل جدیدی مطرح کرده → ACTION

## نتیجه‌گیری:
- ⚠️ اگر بین QUESTION و ACTION شک داری و پیام به مشکل/خطا/عدم کارکرد اشاره دارد → ACTION
- ⚠️ اگر واقعاً فقط سؤال دانشی/نظری است و هیچ اشاره‌ای به مشکل ندارد → QUESTION
- فقط یک کلمه بنویس: QUESTION یا ACTION یا ERROR_LOG"""

        try:
            classify_response = await ai_manager.generate(
                model_id=primary_model,
                messages=[
                    Message(role="system", content="تو یک طبقه‌بند باهوش پیام هستی. وظیفه‌ات فهمیدن منظور واقعی کاربر است — نه فقط جستجوی کلمات کلیدی. لابلای حرف کاربر را بخوان، لحن و context مکالمه را در نظر بگیر. فقط یک کلمه بنویس: QUESTION یا ACTION یا ERROR_LOG"),
                    Message(role="user", content=classify_prompt)
                ],
                max_tokens=20,
                temperature=0.1
            )
            raw_type = classify_response.content.strip().upper()
            # بررسی کلمات کلیدی انگلیسی و فارسی
            if "ACTION" in raw_type or "FIX" in raw_type or "MODIFY" in raw_type:
                msg_type = "ACTION"
            elif "ERROR" in raw_type or "LOG" in raw_type:
                msg_type = "ERROR_LOG"
            elif "QUESTION" in raw_type or "QUEST" in raw_type:
                # فقط اگر صراحتاً QUESTION گفته، سؤال بدان
                msg_type = "QUESTION"
            else:
                # اگر مدل چیز عجیبی برگردوند → ACTION (بهتره فایل بخونه تا نخونه)
                msg_type = "ACTION"
        except Exception:
            # خطا در طبقه‌بندی → فرض ACTION (بهتره تحلیل عمیق انجام بشه)
            msg_type = "ACTION"

        yield sse("progress", {
            "step": "classified",
            "message": f"📋 نوع درخواست: {'سؤال' if msg_type == 'QUESTION' else 'لاگ خطا' if msg_type == 'ERROR_LOG' else 'درخواست اقدام'}",
            "msg_type": msg_type
        })

        # 🆕🆕 (فاز ۲) — مسیریابی خودکار کارهای کد/خطا به Claude (حالت عامل).
        # وقتی کاربر مدل خاصی انتخاب نکرده و درخواست از نوع ACTION/ERROR_LOG
        # است، خودکار به Claude سوئیچ کن تا حلقهٔ عامل tool-calling فعال شود.
        # انتخاب صریح کاربر (model_ids) یا reply-model را هرگز override نمی‌کند.
        # مدلی که باید برای این کار موقتاً فعال شود (و بعد revert گردد). None یعنی
        # نیازی نیست. در consumerهای agent (ACTION/ERROR_LOG) اعمال/revert می‌شود.
        _inspector_temp_model = None
        _user_picked_model = bool(request.model_ids) or reply_model_used
        if (not _user_picked_model) and msg_type in ("ACTION", "ERROR_LOG"):
            # نقش orchestrator (عاملِ tool-calling) را resolve کن: بهترین Claude
            # که کلید دارد. اگر فعال است → ready؛ اگر خاموش است → needs_enable
            # (در consumer موقتاً فعال و بعد revert می‌شود).
            try:
                from ...services.inspector_roles import resolve_role_assignments
                from ...services.inspector_agent import supports_tool_calling as _stc
                _orch = resolve_role_assignments(ai_manager, roles=["orchestrator"]).get("orchestrator")
            except Exception as _re:
                slog.warning(f"[smart-chat phase2] role resolve failed: {_re}")
                _orch = None
            if _orch and _orch.model_id and _stc(_orch.model_id):
                if primary_model != _orch.model_id:
                    slog.info(
                        f"[smart-chat phase2] auto-routing {msg_type} to {_orch.model_id} "
                        f"(status={_orch.status})"
                    )
                    primary_model = _orch.model_id
                if _orch.status == "needs_enable":
                    _inspector_temp_model = _orch.model_id
                    yield sse("progress", {
                        "step": "agent_model_selected",
                        "message": f"🧠 برای این کار از {primary_model} (حالت عامل) استفاده می‌شود — موقتاً فعال می‌شود و بعد به حالت قبل برمی‌گردد",
                        "model": primary_model,
                    })
                else:
                    yield sse("progress", {
                        "step": "agent_model_selected",
                        "message": "🧠 برای این کار از Claude (حالت عامل) استفاده می‌شود — تحلیل دقیق‌تر و خواندن هوشمند فایل‌ها",
                        "model": primary_model,
                    })

        # 🆕🆕 (agent-loop) — helper مشترک ACTION و ERROR_LOG.
        # اگر مدل tool-calling دارد (Claude)، به‌جای pipeline تک‌شات حلقهٔ عامل
        # واقعی را اجرا می‌کند: مدل خودش فایل‌ها را on-demand می‌خواند و قدم‌به‌قدم
        # به action_plan می‌رسد. sse-ها را yield می‌کند و آخرین مورد yield شده
        # یک tuple ("__handled__", bool) است — اگر True بود caller باید return کند.
        async def _try_agent_loop(code_files, all_files):
            try:
                from ...services.inspector_agent import (
                    run_inspector_agent,
                    supports_tool_calling,
                    is_complex_plan,
                    run_reviewer_pass,
                )
            except Exception:
                yield ("__handled__", False)
                return

            if not (run_inspector_agent and supports_tool_calling(primary_model) and code_files):
                yield ("__handled__", False)
                return

            yield sse("progress", {
                "step": "agent_start",
                "message": f"🧠 حالت عامل (agent) با {primary_model} — خواندن هوشمند فایل‌ها قدم‌به‌قدم تا حل مشکل...",
                "model": primary_model,
            })

            _act_tree = _build_project_tree_summary(code_files)
            _agent_sys = f"""تو یک توسعه‌دهندهٔ ارشد و بازرس پروژهٔ {owner}/{repo} هستی — دقیق، کاربلد و عمل‌گرا.

{general_instructions_text}

## ابزارهای تو

### دسترسی به کد:
- `read_file(path)`: محتوای کامل یک فایل را می‌خوانی. **قبل از هر پیشنهاد تغییری، فایل‌های مرتبط را بخوان — هرگز محتوای فایل را حدس نزن.**
- `list_files(filter)`: فهرست فایل‌های پروژه (با فیلتر اختیاری) را می‌بینی.

### دسترسی به Render (پلتفرم دیپلوی) — اگر RENDER_API_KEY در env باشد:
- `render_list_services()`: لیست سرویس‌های Render. اول این را صدا بزن تا service_id پروژهٔ {owner}/{repo} را پیدا کنی.
- `render_get_service(service_id)`: جزئیات سرویس (runtime، buildCommand، startCommand، branch، region، etc.).
- `render_get_env_vars(service_id)`: env vars تنظیم‌شده. 🔴 **اگر PYTHON_VERSION یا NODE_VERSION در env باشد، runtime.txt را override می‌کند!**
- `render_set_env_var(service_id, key, value)`: یک env var را تنظیم/بروزرسانی می‌کند (مثلاً PYTHON_VERSION=3.12.7). بعد باید deploy بزنی. ⛔ برای buildCommand/startCommand از این استفاده نکن — آن‌ها env var نیستند.
- 🔴 `render_update_service_settings(service_id, build_command?, start_command?, auto_deploy?)`: برای ست‌کردن `serviceDetails.buildCommand` یا `startCommand` (همان فیلدهای Render UI > Settings > Build & Deploy). **این تنها راه فعال‌سازی build فرانت** وقتی Render فقط backend را build می‌کند.
- `render_trigger_deploy(service_id, clear_cache)`: deploy جدید اجرا می‌کند. اگر env یا dependency یا buildCommand عوض کردی clear_cache=true.
- `render_get_deploys(service_id, limit)`: فهرست deploy های اخیر با وضعیت — برای فهمیدن «آیا آخرین deploy موفق بود؟».
- 🔴 `render_get_deploy_logs(service_id, deploy_id?, log_type?)`: **مهم‌ترین وقتی deploy fail شده** — لاگ‌های واقعی Render را مستقیماً می‌خواند. **قبل از حدس‌زدن از روی config files، این را صدا بزن تا با چشم خودت ببینی build چه خطایی داد.**

### 🆕 revert/recovery — وقتی کاربر می‌گوید «برگرد به branch X» یا «این فایل را از branch قدیمی بازیابی کن»:
- 🔴 `revert_to_branch(target_branch, file_paths?, commit_message?)`: **بهترین راه** برای revert کامل به یک branch. این ابزار خودش با GitHub compare API تفاوت‌ها رو پیدا می‌کنه، محتوا رو از target branch می‌خونه، و action_plan رو می‌سازه و submit می‌کنه. **فقط همین یک ابزار رو صدا بزن** وقتی کاربر می‌گه «منو برگردون به branch X». نیازی به list_branches یا read_file_from_branch تک‌تک نیست.
- `list_branches()`: لیست branchها (فقط برای discovery، اگر اسم branch مطمئن نیستی).
- `read_file_from_branch(path, branch)`: خواندن یک فایل از branch مرجع (برای revert تک‌فایلی یا inspection).

  ❗ این operations explicit هستند — کاربر صریحاً revert خواسته. بدون درخواست صریح کاربر از این‌ها استفاده نکن.

### بررسی پیش از ثبت (CRITICAL — جلوگیری از whack-a-mole deploy fail):
- 🔴 `preflight_check(files)`: **قبل از submit_action_plan حتماً این را صدا بزن**. این ابزار **کلِ repo را اسکن می‌کند** (نه فقط فایل‌های action_plan): به‌طور خودکار فایل‌های critical (routes/schemas/services/dependencies/models) را از repo می‌کشد و سه نوع مشکل رایج را پیدا می‌کند:
  1. import از فایل خالی (مثل `from notification_schema import X` وقتی فایل خالی است) — **حتی در فایل‌هایی که تو دست‌نزدی**
  2. تعارض module.py vs module/__init__.py
  3. پکیج خارجی import شده ولی در requirements.txt نیست (مثل `EmailStr` بدون `email-validator`)
  🔴 **اگر preflight ایرادی در فایلی پیدا کرد که در action_plan تو نیست**، آن فایل را هم به action_plan اضافه کن — چون اگر نکنی، deploy روی همان شکست می‌خورد و کاربر مجبور می‌شود دوباره به تو خبر دهد (همان whack-a-mole). تمام ایرادات preflight را در یک action_plan رفع کن.

### ثبت نهایی:
- `submit_action_plan(analysis, files, commit_message)`: وقتی preflight «هیچ مشکلی پیدا نشد» را برگرداند، آن را ثبت می‌کنی. این حلقه را تمام می‌کند.

## 🔴🔴 قاعدهٔ صفر — تشخیص علائم پلتفرمی (قبل از هر چیز)
**اگر علائم اینها هست، احتمالاً مشکل از Render است نه کد:**
- صفحه فقط placeholder/loading/«در حال آماده‌سازی» نشان می‌دهد
- backend logs پاسخ ۲۰۰ OK می‌دهد، هیچ خطایی نیست، ولی صفحه خالی است
- HTML برگشتی بسیار کوچک است (<2KB، احتمالاً placeholder از main.py)
- frontend/dist در repo نیست (در .gitignore هست — این طبیعی است)
- deploy موفق است ولی app کار نمی‌کند

در این حالت **اول این کارها را بکن، نه فیکس کد**:
1. `render_get_service(service_id)` → فیلد `buildCommand` را چک کن
2. اگر `buildCommand` خالی است یا فقط `pip install ...` دارد (بدون `npm run build`):
   - **این علت اصلی است** — Render فرانت را build نمی‌کند، main.py به fallback می‌رود و placeholder می‌دهد
   - راه‌حل: `render_update_service_settings(service_id, build_command="cd frontend && npm install && npm run build && cd .. && pip install -r requirements.txt")` — این `serviceDetails.buildCommand` را روی سرویس ست می‌کند (همان فیلد Render UI > Settings > Build Command)
   - ⛔ از `render_set_env_var(BUILD_COMMAND=...)` استفاده نکن — buildCommand در serviceDetails است نه env var
   - بعد `render_trigger_deploy(clear_cache=true)`
3. **هیچ فیکس کدی نده** برای این کلاس مشکل — اضافه‌کردن کد به main.py یا تغییر render.yaml کمکی نمی‌کند چون سرویس Render از UI ساخته شده و `buildCommand` در render.yaml را نادیده می‌گیرد

🔴 اگر این قاعده را رد کنی و بروی سراغ فیکس کد، چندین round whack-a-mole خواهی داشت و کاربر را خسته خواهی کرد.

## روش کار (مثل یک مهندس واقعی)
1. **متن خطا/لاگ کاربر را با دقت بخوان — این منبع حقیقت است.** هر کلمه/عدد/خط مهم است.
2. با read_file فایل‌های مرتبط را **یکی‌یکی** بخوان — از فایل‌هایی که در خطا/لاگ ذکر شده‌اند شروع کن.
3. علت ریشه‌ای را پیدا کن (نه علائم سطحی).
4. ⚠️ **CONTRADICTION CHECK** — اگر چیزی در config می‌گوید X ولی log می‌گوید Y، **اول این تضاد را بفهم** قبل از پیشنهاد فیکس. مثال: `runtime.txt` می‌گوید `python-3.12.7` ولی log می‌گوید `python3.14` → یعنی runtime.txt به دلیلی نادیده گرفته می‌شود. باید بررسی کنی چرا (شاید PYTHON_VERSION env var override کرده، شاید format فایل غلط است، شاید Render UI manually override کرده). از ابزارهای render_* استفاده کن!
5. **قبل از submit، چک کن:** فیکست دقیقاً همان چیزی را که در error log واقعی آمده هدف می‌گیرد؟
6. 🔴 **preflight_check بزن** — اگر مشکلی پیدا شد در همان action_plan رفع کن و دوباره preflight. **بدون preflight هرگز submit نکن.**
7. وقتی preflight ✅ گفت، submit_action_plan را صدا بزن.

## قوانین حیاتی
- 🔴 **منبع حقیقت = error log واقعی، نه config files.** اگر runtime.txt یا render.yaml می‌گوید X ولی build log می‌گوید Y، **به log اعتماد کن** و **بفهم چرا config نادیده گرفته شده**. ابزارهای render_* را برای کشف حقیقت پلتفرم به کار ببر.
- 🔴 وقتی مشکل از **پلتفرم** است (Python version اشتباه، env var ناقص، runtime مشکل‌دار)، **فیکس‌اش هم باید روی پلتفرم باشد** (render_set_env_var)، نه فقط روی فایل کد. فیکس فایلی برای مشکل پلتفرمی = شکست تضمینی.
- 🔴 فقط فایل‌هایی را در action_plan بگذار که با read_file **واقعاً خوانده‌ای** — محتوای حدسی ممنوع.
- 🔴 فایل‌های بزرگ (>۲۰۰ خط): از operation=modify_sections با find/replace دقیق (COPY از متن واقعی) استفاده کن — نه بازنویسی کامل.
- فایل‌های کوچک: operation=modify با content کامل. فایل جدید: operation=create.
- مشکل را با کمترین تغییر و هدفمند حل کن — scope را بی‌دلیل گسترش نده.
- اگر بعد از بررسی واقعاً نمی‌توانی fix قطعی بدهی، submit_action_plan را با files=[] صدا بزن و در analysis دقیق توضیح بده چرا و کاربر چه اطلاعاتی باید بدهد — هرگز بی‌نتیجه متوقف نشو.
- 🔴 **اگر فیکس پیشنهادی‌ات موضوع متفاوتی از error log را حل می‌کند**، آن را در analysis صریحاً اعلام کن.

## خلاصهٔ ساختار پروژه (برای جهت‌گیری — برای دیدن محتوا باید read_file بزنی)
{_act_tree}"""

            _parts = [f"## درخواست کاربر:\n{request.message}"]
            if reply_context_text:
                _parts.append(reply_context_text)
            if history_text and history_text.strip():
                _parts.append(f"## تاریخچهٔ مکالمه (برای context):\n{history_text[-6000:]}")
            if logs_text and logs_text.strip():
                _parts.append(f"## لاگ‌های اخیر:\n{logs_text[-4000:]}")
            _parts.append("حالا شروع کن: فایل‌های لازم را بخوان، علت را پیدا کن، و submit_action_plan بزن.")
            _agent_user = "\n\n".join(_parts)

            _agent_result = None
            try:
                async for _ev_type, _ev_payload in run_inspector_agent(
                    ai_manager=ai_manager,
                    github_svc=github_svc,
                    model_id=primary_model,
                    owner=owner,
                    repo=repo,
                    token=token,
                    branch=None,
                    system_prompt=_agent_sys,
                    user_prompt=_agent_user,
                    file_list=code_files,
                ):
                    if _ev_type == "agent_result":
                        _agent_result = _ev_payload
                    else:
                        yield sse(_ev_type, _ev_payload)
            except Exception as _ae:
                slog.error(f"[smart-chat agent] failed: {_ae}")
                yield sse("progress", {
                    "step": "agent_fallback",
                    "message": "⚠️ حالت عامل خطا داد — برگشت به روش معمول",
                })
                _agent_result = None

            _ap = _agent_result.get("action_plan") if _agent_result else None
            _agent_ok = bool(
                _agent_result is not None
                and _agent_result.get("stop_reason") != "error"
                and (
                    (_ap and _ap.get("files"))
                    or (_agent_result.get("content") and len(_agent_result["content"].strip()) > 30)
                )
            )
            if not _agent_ok:
                yield ("__handled__", False)
                return

            _files_read = _agent_result.get("files_read") or {}
            _content = _agent_result.get("content") or "تحلیل انجام شد."
            _has_files = bool(_ap and _ap.get("files"))
            _agent_tokens = _agent_result.get("tokens_used", 0)

            # 🆕🆕 (قدم ۲ — multi-agent) نقش بازبین: برای کارهای پیچیده، یک مدلِ
            # نقشِ reviewer تغییرات را بازبینی می‌کند و نظرش به پاسخ ضمیمه می‌شود.
            # هر خطا = skip امن (پاسخ orchestrator بدون تغییر برمی‌گردد).
            _review = None
            if _has_files and is_complex_plan(_ap):
                yield sse("progress", {
                    "step": "agent_review",
                    "message": f"🔎 [{primary_model}] بازبینی تغییرات توسط نقش reviewer...",
                })
                try:
                    _review = await run_reviewer_pass(
                        ai_manager=ai_manager,
                        user_message=request.message,
                        analysis=_content,
                        action_plan=_ap,
                        files_read=_files_read,
                        exclude_model=primary_model,
                    )
                except Exception as _rev_e:
                    slog.warning(f"[smart-chat reviewer] failed: {_rev_e}")
                    _review = None
                if _review:
                    _agent_tokens += _review.get("tokens_used", 0)
                    _verdict = _review.get("verdict", "approve")
                    _icon = "✅" if _verdict == "approve" else "⚠️"
                    yield sse("progress", {
                        "step": "agent_review_done",
                        "message": f"{_icon} [reviewer: {_review.get('reviewer_model')}] {'تأیید شد' if _verdict == 'approve' else 'نکاتی دارد'}",
                    })
                    if _review.get("notes"):
                        _content += (
                            f"\n\n---\n🔎 **بازبینی ({_review.get('reviewer_model')}):** "
                            f"{'✅ تأیید' if _verdict == 'approve' else '⚠️ نکات'}\n{_review.get('notes')}"
                        )

            # 🆕🆕 (قدم ۳ — حلقهٔ بازنگری) اگر reviewer ایراد گرفت، orchestrator
            # **یک‌بار** طرح را بر اساس نکات بازنویسی می‌کند (collaboration واقعی).
            # فقط یک دور — برای جلوگیری از حلقهٔ بی‌پایان و هزینهٔ زیاد.
            _revised = False
            if _review and _review.get("verdict") == "concerns" and _review.get("notes"):
                yield sse("progress", {
                    "step": "agent_revise",
                    "message": f"🔧 [{primary_model}] اعمال بازخورد reviewer و بازنگری طرح...",
                })
                _rev_user = (
                    f"## درخواست اصلی کاربر:\n{request.message}\n\n"
                    f"## طرح فعلی تو (پیش‌نویس):\n{(_agent_result.get('content') or '')[:2000]}\n\n"
                    f"## ایرادهای بازبین (با دقت بررسی کن):\n{_review.get('notes')}\n\n"
                    "طرح را با توجه به این ایرادها بازنگری کن. در صورت نیاز فایل‌های "
                    "بیشتری بخوان، سپس submit_action_plan با نسخهٔ اصلاح‌شده بزن. "
                    "اگر ایرادهای بازبین وارد نیستند، همان طرح قبلی را با توضیح کوتاهِ دلیل دوباره submit کن — هرگز بی‌نتیجه متوقف نشو."
                )
                _rev_result = None
                try:
                    async for _ev_t, _ev_p in run_inspector_agent(
                        ai_manager=ai_manager,
                        github_svc=github_svc,
                        model_id=primary_model,
                        owner=owner,
                        repo=repo,
                        token=token,
                        branch=None,
                        system_prompt=_agent_sys,
                        user_prompt=_rev_user,
                        file_list=code_files,
                        max_iterations=8,
                    ):
                        if _ev_t == "agent_result":
                            _rev_result = _ev_p
                        else:
                            yield sse(_ev_t, _ev_p)
                except Exception as _re3:
                    slog.warning(f"[smart-chat revise] failed: {_re3}")
                    _rev_result = None

                _rev_ap = _rev_result.get("action_plan") if _rev_result else None
                if _rev_ap and _rev_ap.get("files"):
                    _ap = _rev_ap
                    _content = (_rev_result.get("content") or _content)
                    _files_read = {**_files_read, **(_rev_result.get("files_read") or {})}
                    _has_files = True
                    _agent_tokens += _rev_result.get("tokens_used", 0)
                    _revised = True
                    _content += f"\n\n---\n🔧 این طرح پس از بازبینی ({_review.get('reviewer_model')}) یک‌بار بازنگری شد."
                    yield sse("progress", {"step": "agent_revise_done", "message": f"✅ [{primary_model}] طرح بر اساس بازخورد بازنگری شد"})
                else:
                    yield sse("progress", {"step": "agent_revise_skip", "message": "ℹ️ بازنگری نتیجهٔ جدیدی نداد — طرح اولیه حفظ شد"})

            # 🆕 (review-gate) — اگر reviewer issue critical پیدا کرده و
            # revision هم نتونسته حلش کنه (یا اصلاً revise نشد)، plan رو
            # برای apply-all مارک می‌کنیم. این به frontend می‌گه که قبل از
            # commit باید کاربر تصمیم بگیره. (در transcript کاربر هر مرحله
            # critical issue داشت ولی apply ادامه پیدا می‌کرد.)
            _review_blocked = False
            _review_critical_signals: List[str] = []
            if _review and _review.get("has_critical_issues"):
                # اگر revision نکرده‌ایم یا revision کم بوده، block
                if not _revised:
                    _review_blocked = True
                    _review_critical_signals = _review.get("critical_signals", [])
                else:
                    # revision شد — ولی نمی‌دونیم آیا حل شد. به‌جای دوبار review
                    # (هزینهٔ دوبرابر)، notes اولیه رو نگه می‌داریم و فقط
                    # کاربر رو با warning ملایم‌تر مطلع می‌کنیم.
                    _review_critical_signals = _review.get("critical_signals", [])
                    _content += (
                        "\n\n⚠️ **توجه**: بازبینی اولیه issue critical پیدا کرد "
                        f"({', '.join(_review_critical_signals[:3])}). طرح "
                        "بازنگری شد ولی قبل از «اعمال همهٔ تغییرات» نگاه دقیق کن."
                    )

            yield sse("response", {
                "type": "action",
                "content": _content,
                "model_used": _agent_result.get("model_used"),
                "tokens_used": _agent_tokens,
                "has_action": _has_files,
                "action_plan": _validate_action_plan_syntax(
                    _ap,
                    original_files=_files_read,
                    repo_file_paths=_normalize_repo_paths(all_files),
                    user_message=request.message,
                    backend_logs=request.backend_logs,
                    code_files=code_files,
                ) if _has_files else None,
                "files_were_read": bool(_files_read),
                "selected_file_paths": list(_files_read.keys()),
                "agent_mode": True,
                "agent_stop_reason": _agent_result.get("stop_reason"),
                "revised": _revised,
                "review": ({
                    "model": _review.get("reviewer_model"),
                    "verdict": _review.get("verdict"),
                    "notes": _review.get("notes"),
                    # 🆕 (review-gate) — flagهای جدید برای frontend
                    "has_critical_issues": _review.get("has_critical_issues", False),
                    "critical_signals": _review.get("critical_signals", []),
                    "blocked": _review_blocked,
                } if _review else None),
                # 🆕 (review-gate) — flag سطح بالا تا frontend بتونه قبل از
                # apply-all کاربر رو با confirm dialog حساس کنه (یا apply رو
                # ببنده تا تأیید صریح بگیره).
                "review_blocked": _review_blocked,
                "review_critical_signals": _review_critical_signals,
            })
            yield sse("done", {"success": True})
            yield ("__handled__", True)

        async def _run_agent_section(code_files, all_files):
            """مدل لازم را (اگر خاموش بود) موقتاً فعال می‌کند، حلقهٔ عامل را اجرا
            می‌کند، و در پایان (حتی روی exception) دقیقاً به حالت قبل برمی‌گرداند."""
            _revert_info = []
            if _inspector_temp_model:
                try:
                    from ...services.inspector_roles import apply_temp_enables
                    _revert_info = apply_temp_enables([_inspector_temp_model])
                    if _revert_info:
                        yield sse("progress", {
                            "step": "agent_temp_enable",
                            "message": f"🔌 {_inspector_temp_model} موقتاً فعال شد (بعد از کار به حالت قبل برمی‌گردد)",
                        })
                except Exception as _te:
                    slog.warning(f"[smart-chat] temp-enable failed: {_te}")
                    _revert_info = []
            try:
                async for _chunk in _try_agent_loop(code_files, all_files):
                    yield _chunk
            finally:
                if _revert_info:
                    try:
                        from ...services.inspector_roles import revert_temp_enables
                        revert_temp_enables(_revert_info)
                    except Exception as _re2:
                        slog.warning(f"[smart-chat] revert temp-enable failed: {_re2}")

        # --- مرحله ۳: پاسخ بر اساس نوع پیام ---

        if msg_type == "QUESTION":
            # سؤال: پاسخ با context کامل + خواندن فایل‌های مرتبط
            question_code_context = ""
            file_contents = {}  # دیکشنری فایل‌های اصلی برای تشخیص بازنویسی مخرب
            q_tree_summary = ""
            if not owner or not repo:
                yield sse("progress", {
                    "step": "no_github_info",
                    "message": "⚠️ اطلاعات ریپوی GitHub ناقص — پاسخ بدون دسترسی به فایل‌ها..."
                })
            if owner and repo:
                try:
                    yield sse("progress", {
                        "step": "reading_project_question",
                        "message": f"📂 در حال خواندن فایل‌های مرتبط برای پاسخ دقیق‌تر..."
                    })
                    tree_result = await github_svc.get_repo_tree(owner, repo, token=token)
                    if tree_result.get("success"):
                        all_files = [f for f in tree_result.get("tree", []) if f.get("type") == "blob"]
                        q_code_files = [f["path"] for f in all_files
                                        if _is_code_file(f["path"], file_size=f.get("size", 0))]
                        # ساخت خلاصه ساختار پروژه
                        q_tree_summary = _build_project_tree_summary(q_code_files)

                        # 🆕 تشخیص دامنه برای سؤال
                        q_scope = _detect_request_scope(request.message, history_text)
                        q_dynamic_max = _get_max_files_for_scope(q_scope, len(q_code_files))
                        # سؤال‌ها معمولاً نیاز به فایل کمتری دارن — سقف رو تنظیم کن
                        if q_scope == "TARGETED":
                            q_dynamic_max = 12  # مثل قبل
                        elif q_scope == "BROAD":
                            q_dynamic_max = min(q_dynamic_max, 40)

                        if q_scope == "FULL_PROJECT":
                            # سؤال درباره کل پروژه — همه فایل‌ها
                            q_selected = q_code_files[:q_dynamic_max]
                        else:
                            q_select_prompt = f"""بر اساس سؤال کاربر، فایل‌های مرتبط را انتخاب کن:

سؤال: {request.message}

تاریخچه مکالمه (تا ۳۰۰۰ کاراکتر آخر):
{history_text[-3000:]}

{q_tree_summary}
{prev_files_hint}

فایل‌های پروژه:
{chr(10).join(q_code_files[:500])}

## راهنمای انتخاب هوشمند:
- اول منظور واقعی سؤال کاربر را بفهم — شاید کلمات دقیق استفاده نکرده باشد
- نام فایل‌ها، مسیرها و کلمات کلیدی در سؤال را تحلیل کن — مثلاً اگر از "احراز هویت" صحبت کرده، فایل‌های auth/login/register/middleware را پیدا کن
- اگر کاربر از یک فیچر/صفحه/کامپوننت صحبت کرده، فایل‌های مرتبط با آن + وابستگی‌هایشان (imports, types, configs) را انتخاب کن
- اگر پروژه هم frontend و هم backend دارد، از هر دو بخش فایل مرتبط انتخاب کن
- تاریخچه مکالمه را بخوان — شاید سؤال در ادامه بحث قبلی باشد
- اگر فایل‌هایی قبلاً بررسی شده‌اند (لیست بالا)، فایل‌های جدید و بررسی‌نشده را اولویت بده — مگر اینکه سؤال واقعاً به همان فایل‌ها مربوط باشد
- فایل‌های entry point (main, app, index, page, layout)، API routes و config را در نظر بگیر
حداکثر {q_dynamic_max} فایل. فقط مسیرها، هر کدام در یک خط."""
                            q_sel_resp = await ai_manager.generate(
                                model_id=primary_model,
                                messages=[
                                    Message(role="system", content=f"انتخاب‌گر فایل هوشمند. منظور سؤال کاربر را بفهم و تا {q_dynamic_max} فایل مرتبط انتخاب کن. فقط مسیرها."),
                                    Message(role="user", content=q_select_prompt)
                                ],
                                max_tokens=max(600, q_dynamic_max * 40),
                                temperature=0.2
                            )
                            q_selected = _parse_ai_selected_files(q_sel_resp.content, q_code_files, max_files=q_dynamic_max)
                            if not q_selected:
                                q_selected = _fallback_file_selection(q_code_files, request.message, max_files=q_dynamic_max)
                            q_selected = _ensure_balanced_selection(q_selected, q_code_files, max_files=q_dynamic_max)

                        # 🆕 فایل‌های ذکرشده در پیام/تاریخچه حتماً خونده بشن
                        _q_extracted = _extract_file_paths_from_text(
                            request.message + "\n" + history_text[-5000:], q_code_files
                        )
                        if _q_extracted:
                            for _ep in _q_extracted:
                                if _ep not in q_selected:
                                    q_selected.insert(0, _ep)

                        max_q_code = int(max_input_chars * 0.55)
                        # 🆕 پردازش دسته‌ای برای FULL_PROJECT
                        q_use_batch = (q_scope == "FULL_PROJECT" and len(q_selected) > 30)
                        if q_use_batch:
                            # ── Background Batch Processing — QUESTION ──
                            q_batch_budget = int(max_input_chars * 0.50)
                            per_file_q_limit = min(8000, max(2000, q_batch_budget // 25))
                            q_batch_size = max(10, min(30, q_batch_budget // max(per_file_q_limit, 1)))
                            q_batches = [q_selected[i:i+q_batch_size] for i in range(0, len(q_selected), q_batch_size)]

                            _qproj_id = str(request.project_id) if request.project_id else ""
                            q_task_key, q_bg_info, q_is_reconnect = _start_bg_batch(
                                _qproj_id, request.message, q_selected, q_batches,
                                per_file_q_limit, github_svc, ai_manager, owner, repo, token,
                                primary_model, model_max_output, history_text, q_tree_summary,
                                flow_type="question"
                            )

                            if q_is_reconnect:
                                yield sse("progress", {"step": "reconnect", "message": "♻️ اتصال مجدد — ادامه پردازش سؤال..."})
                            else:
                                yield sse("progress", {"step": "batch_mode", "message": f"🔄 پردازش دسته‌ای سؤال: {len(q_selected)} فایل در {len(q_batches)} دسته..."})
                            yield sse("progress", {"step": "batch_task_key", "task_key": q_task_key})

                            async for evt in _follow_bg_batch(q_bg_info, sse):
                                yield evt

                            question_code_context = q_bg_info.get("code_context", "")
                            file_contents = q_bg_info.get("file_contents", {})
                        else:
                            per_file_q_limit = min(10000, max(3000, max_q_code // max(len(q_selected), 1)))
                            q_read_failures = 0
                            for fp in q_selected:
                                if len(question_code_context) >= max_q_code:
                                    break
                                try:
                                    result = await github_svc.get_file_content(owner, repo, fp, token=token)
                                    if result.get("success"):
                                        content = result.get("content", "")
                                        file_contents[fp] = content  # ذخیره اصلی برای تشخیص بازنویسی مخرب
                                        _total_lines = len(content.split("\n"))
                                        _size_hint = ""
                                        if _total_lines > 200:
                                            _size_hint = f" ⚠️ فایل بزرگ — حتماً از modify_sections استفاده کن — find فقط از همین بخش نمایش‌داده‌شده COPY شود"
                                        if len(content) > per_file_q_limit:
                                            content = content[:per_file_q_limit] + f"\n... [truncated — فایل اصلی {_total_lines} خط دارد{_size_hint}]"
                                        question_code_context += f"\n\n=== {fp} ({_total_lines} خط) ===\n{content}"
                                    else:
                                        q_read_failures += 1
                                        slog.warning(f"[smart-chat QUESTION] Failed to read file {fp}: {result.get('error', 'unknown')}")
                                except Exception as e:
                                    q_read_failures += 1
                                    slog.warning(f"[smart-chat QUESTION] Exception reading file {fp}: {e}")
                                await asyncio.sleep(0.2)
                        if q_read_failures > 0 and q_read_failures == len(q_selected):
                            yield sse("progress", {
                                "step": "file_read_warning",
                                "message": f"⚠️ خواندن فایل‌ها ناموفق بود — پاسخ بدون دسترسی به کد..."
                            })
                    else:
                        yield sse("progress", {
                            "step": "tree_failed",
                            "message": f"⚠️ دسترسی به ساختار پروژه ناموفق — پاسخ بدون فایل‌ها..."
                        })
                        slog.warning(f"[smart-chat QUESTION] get_repo_tree failed: {tree_result.get('error', 'unknown')}")
                except Exception as e:
                    yield sse("progress", {
                        "step": "github_error",
                        "message": f"⚠️ خطا در دسترسی GitHub: {str(e)[:60]}"
                    })
                    slog.warning(f"[smart-chat QUESTION] GitHub access exception: {e}")

            has_q_code = bool(question_code_context and question_code_context.strip())
            q_structure_text = q_tree_summary

            answer_prompt = f"""شما بازرس هوشمند پروژه {owner}/{repo} هستید.
{general_instructions_text}
## ⚠️ اصل اول: فهم عمیق منظور کاربر
قبل از هر کاری، منظور واقعی کاربر را بفهم:
- کاربران همیشه دقیق و رسمی صحبت نمی‌کنند — ممکن است غیرمستقیم، کوتاه، عصبانی یا عامیانه بنویسند
- "کار نمیکنه" یعنی مشکلی هست که باید پیدا و حل شود
- "باز همون مشکل" یعنی راه‌حل قبلی جواب نداده — تاریخچه را بخوان و رویکرد متفاوتی پیشنهاد بده
- اگر پیام کوتاه یا مبهم است (مثل "آره"، "نه"، "همونه")، حتماً تاریخچه مکالمه را بخوان تا بفهمی در ادامه چه بحثی است
- اگر کاربر ناراحت یا عصبانی به نظر می‌رسد، با درک و همدلی پاسخ بده — نه رسمی و خشک

## 🔑 دسترسی کامل به پروژه:
{'تو دسترسی کامل به تمام فایل‌های پروژه داری. سیستم به صورت هوشمند مرتبط‌ترین فایل‌ها را از کل مخزن پروژه خوانده و در پایین آورده. هرگز نگو «دسترسی ندارم» یا «در اختیارم نیست» یا «دوباره ارسال کنید». همیشه با همین فایل‌ها کار کن و بهترین پاسخ را بده.' if has_q_code else 'فایل‌های پروژه در این لحظه خوانده نشده — اما بر اساس تاریخچه مکالمه و لاگ‌ها بهترین تحلیل ممکن را ارائه بده.'}
هرگز از کاربر نخواه که خودش فایل‌ها را بررسی کند یا دستوراتی را اجرا کند.
{'اگر کاربر مشکلی گزارش کرده، مستقیماً در کد بررسی کن و راه‌حل مشخص ارائه بده.' if has_q_code else 'حتی بدون خواندن فایل‌ها، بر اساس اطلاعات موجود بهترین تحلیل ممکن را ارائه بده — هرگز نگو "نمی‌توانم کمک کنم".'}

{f'## ساختار کلی پروژه (تو به همه این بخش‌ها دسترسی داری):{chr(10)}{q_structure_text}' if q_structure_text else ''}

## تاریخچه کامل مکالمه:
{history_text[-5000:]}
{reply_context_text if reply_context_text else ''}
## لاگ‌های اخیر:
{logs_text[-1500:] if logs_text else 'لاگی موجود نیست'}

## URL فرانت‌اند: {request.frontend_url or 'نامشخص'}

{f'## کد فایل‌های مرتبط:{question_code_context}' if has_q_code else ''}

## پیام جدید کاربر:
{request.message}

## دستورالعمل پاسخ‌دهی:
- اول منظور واقعی کاربر را بفهم — سپس بر اساس تمام اطلاعات موجود (تاریخچه + لاگ‌ها{' + کد فایل‌ها' if has_q_code else ''} + گزارش‌های قبلی) پاسخ بده
- اگر پیام در ادامه مکالمه قبلی است، حتماً context قبلی را در نظر بگیر
- اگر پیام مربوط به خطای قبلی است، به گزارش بررسی قبلی ارجاع بده
- اگر لاگ خطایی paste شده، آن را دقیق تحلیل کن و ارتباطش با مکالمات قبلی را بگو
- هرگز کاربر را به انجام کار دستی راهنمایی نکن — تو باید تحلیل کنی و راه‌حل ارائه بدی
- اگر نیاز به تغییر کد هست، action_plan با محتوای کامل فایل‌های اصلاح‌شده ارائه بده (files خالی ممنوع)
{('- ⬆️ کاربر به پیام خاصی ریپلای زده - حتماً در ارتباط با آن پیام پاسخ بده' + chr(10)) if request.reply_to else ''}- پاسخ دقیق، عملی و به فارسی بده — با لحنی صمیمی و حرفه‌ای (نه خشک و رسمی)"""

            try:
                # 🆕 اجرای AI با heartbeat برای جلوگیری از قطع اتصال (QUIC timeout)
                gen_task = asyncio.create_task(ai_manager.generate(
                    model_id=primary_model,
                    messages=[
                        Message(role="system", content="تو بازرس هوشمند پروژه هستی با دسترسی کامل به تمام فایل‌های پروژه. مهم‌ترین وظیفه‌ات فهمیدن منظور واقعی کاربر است — حتی وقتی مبهم، کوتاه یا غیرمستقیم صحبت می‌کند. تاریخچه مکالمه را بخوان تا context را بفهمی. مستقیماً تحلیل کن و راه‌حل عملی ارائه بده. هرگز از کاربر نخواه کار دستی انجام دهد. ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «دوباره ارسال کنید». ⛔ هرگز فایل موجود را از صفر بازننویس — فقط بخش مربوط به درخواست تغییر کن. قابلیت‌های موجود را حذف نکن. کلمات کاربر را دقیق بخوان: «فقط»=ONLY، «نباید»=ممنوع. با لحن صمیمی و حرفه‌ای پاسخ بده."),
                        Message(role="user", content=answer_prompt)
                    ],
                    max_tokens=model_max_output,
                    temperature=0.5
                ))
                while not gen_task.done():
                    done_set, _ = await asyncio.wait({gen_task}, timeout=8.0)
                    if not done_set:
                        yield sse("heartbeat", {"message": "⏳ مدل در حال پردازش..."})
                response = gen_task.result()
                # 🧹 حذف بلوک‌های استدلال/reasoning
                if response.content:
                    response.content = _strip_reasoning_blocks(response.content)

                # بررسی وجود action_plan در پاسخ سؤال هم (با پشتیبانی فرمت‌های مختلف)
                q_action_plan = None
                try:
                    json_match = re.search(r'```json\s*\n(.*?)\n```', response.content, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(1))
                        q_action_plan = _normalize_action_plan_json(parsed)
                except Exception:
                    pass

                # لایه ۲: اگر فایل‌ها خوانده نشدن، action_plan حذف شود
                # 🆕 (clarify-first) — استثنا: اگر action_plan فقط ask_user/route_to
                # است (هیچ فایل تولیدی ندارد)، نباید strip شود — این طبیعی است.
                _q_is_clarify = bool(q_action_plan and (q_action_plan.get("ask_user") or q_action_plan.get("route_to")))
                if not has_q_code and q_action_plan is not None and not _q_is_clarify:
                    slog.warning(f"[smart-chat QUESTION] AI generated action_plan without reading files — stripped")
                    q_action_plan = None

                yield sse("response", {
                    "type": "answer",
                    "content": response.content,
                    "model_used": response.model_id,
                    "tokens_used": response.tokens_used,
                    "has_action": q_action_plan is not None,
                    "action_plan": _validate_action_plan_syntax(q_action_plan, original_files=file_contents, repo_file_paths=_normalize_repo_paths(locals().get("all_files")), user_message=request.message, backend_logs=request.backend_logs, code_files=locals().get("code_files")) if q_action_plan else None,
                    "files_were_read": has_q_code,
                    "selected_file_paths": q_selected if has_q_code else [],
                })

            except Exception as e:
                slog.error(f"[smart-chat] QUESTION model={primary_model} error={str(e)[:200]}")
                yield sse("error", {"message": f"❌ خطا در پاسخ‌دهی مدل {primary_model}: {str(e)[:150]}"})

        elif msg_type == "ERROR_LOG":
            # لاگ خطا: تحلیل و ارتباط با مکالمات قبلی
            yield sse("progress", {
                "step": "analyzing_error_log",
                "message": "🔍 در حال تحلیل لاگ خطا و ارتباط آن با مکالمات قبلی..."
            })

            # خواندن فایل‌های مرتبط از GitHub اگر دسترسی داریم
            code_context = ""
            file_contents = {}  # دیکشنری فایل‌های اصلی برای تشخیص بازنویسی مخرب
            err_tree_summary = ""
            if not owner or not repo:
                yield sse("progress", {
                    "step": "no_github_info",
                    "message": "⚠️ اطلاعات ریپوی GitHub ناقص — تحلیل بدون دسترسی به فایل‌ها..."
                })
            if owner and repo:
                try:
                    tree_result = await github_svc.get_repo_tree(owner, repo, token=token)
                    if tree_result.get("success"):
                        all_files = [f for f in tree_result.get("tree", []) if f.get("type") == "blob"]
                        code_files = [f["path"] for f in all_files
                                      if _is_code_file(f["path"], file_size=f.get("size", 0))]

                        # 🆕🆕 (agent-loop / فاز ۲) — اگر مدل tool-calling دارد
                        # (Claude)، حلقهٔ عامل واقعی اجرا کن؛ وگرنه fallback به
                        # pipeline تک‌شات پایین.
                        _agent_handled = False
                        async for _chunk in _run_agent_section(code_files, all_files):
                            if isinstance(_chunk, tuple) and _chunk and _chunk[0] == "__handled__":
                                _agent_handled = _chunk[1]
                            else:
                                yield _chunk
                        if _agent_handled:
                            return

                        # ساخت خلاصه ساختار پروژه
                        err_tree_summary = _build_project_tree_summary(code_files)

                        # 🆕 تشخیص دامنه برای خطا
                        err_scope = _detect_request_scope(request.message, history_text)
                        err_dynamic_max = _get_max_files_for_scope(err_scope, len(code_files))
                        # خطاها معمولاً هدفمندن ولی اگر کاربر بررسی کلی خواسته...
                        if err_scope == "TARGETED":
                            err_dynamic_max = 20  # مثل قبل

                        # 🆕 تشخیص دامنه خطا (frontend/backend/cross) — جلوگیری از خواندن فایل‌های نامرتبط
                        _err_domain = _detect_error_domain(request.message)
                        _domain_hint = ""
                        if _err_domain == "frontend":
                            _domain_hint = "\n⚠️ این خطا مربوط به فرانت‌اند/build است — فقط فایل‌های فرانت‌اند، config، و package.json انتخاب کن. فایل‌های Python/backend نامرتبطند."
                            err_dynamic_max = min(err_dynamic_max, 15)  # خطای frontend نیاز به 20 فایل ندارد
                        elif _err_domain == "backend":
                            _domain_hint = "\n⚠️ این خطا مربوط به بک‌اند است — فقط فایل‌های Python/backend، config، و requirements.txt انتخاب کن. فایل‌های frontend نامرتبطند."
                            err_dynamic_max = min(err_dynamic_max, 15)

                        select_prompt = f"""بر اساس خطا و context مکالمه، فایل‌های مرتبط را انتخاب کن:

خطا/لاگ:
{request.message[:3000]}

تاریخچه مکالمه (تا ۴۰۰۰ کاراکتر آخر):
{history_text[-4000:]}

{err_tree_summary}
{prev_files_hint}

فایل‌های پروژه:
{chr(10).join(code_files[:500])}

## راهنمای انتخاب هوشمند:
- اول خطا را بخوان و بفهم ریشه مشکل کجاست — سپس فایل‌های مرتبط را انتخاب کن
- stack trace را دقیق تحلیل کن — هر مسیر فایلی که در خطا ذکر شده حتماً انتخاب شود
- تاریخچه مکالمه را هم بخوان — شاید کاربر قبلاً توضیح داده کدام بخش مشکل دارد
- فایل‌های config مرتبط را حتماً شامل کن: package.json, tsconfig.json, postcss.config, vite.config, tailwind.config, next.config, requirements.txt, Dockerfile
- فایل‌های import/dependency chain مرتبط با فایل خطادار را هم بررسی کن
- اگر فایل‌هایی قبلاً بررسی شده‌اند (لیست بالا)، فایل‌های جدید و بررسی‌نشده را اولویت بده — مگر اینکه خطا واقعاً به همان فایل‌ها مربوط باشد
{_domain_hint}

⛔ مهم: فقط فایل‌هایی که واقعاً به این خطا مرتبطند انتخاب کن — خواندن فایل‌های نامرتبط باعث هدررفت بودجه و کاهش دقت تحلیل میشود.

حداکثر {err_dynamic_max} فایل مرتبط. فقط مسیرها، هر کدام در یک خط."""

                        _err_sys_domain_note = ""
                        if _err_domain == "frontend":
                            _err_sys_domain_note = " خطا فرانت‌اند/build است — فقط فایل‌های فرانت‌اند و config انتخاب کن، نه backend."
                        elif _err_domain == "backend":
                            _err_sys_domain_note = " خطا بک‌اند است — فقط فایل‌های Python/backend و config انتخاب کن، نه frontend."

                        select_response = await ai_manager.generate(
                            model_id=primary_model,
                            messages=[
                                Message(role="system", content=f"انتخاب‌گر فایل هوشمند. ریشه خطا را با تحلیل stack trace و context تشخیص بده، سپس تا {err_dynamic_max} فایل مرتبط + زنجیره وابستگی‌ها انتخاب کن.{_err_sys_domain_note} فقط مسیرها."),
                                Message(role="user", content=select_prompt)
                            ],
                            max_tokens=max(800, err_dynamic_max * 40),
                            temperature=0.2
                        )

                        selected = _parse_ai_selected_files(select_response.content, code_files, max_files=err_dynamic_max)
                        if not selected:
                            selected = _fallback_file_selection(code_files, request.message, max_files=err_dynamic_max)
                        selected = _ensure_balanced_selection(selected, code_files, max_files=err_dynamic_max, error_domain=_err_domain)

                        # 🆕 فایل‌های ذکرشده در خطا/stack trace حتماً خونده بشن
                        _err_extracted = _extract_file_paths_from_text(
                            request.message + "\n" + history_text[-5000:], code_files
                        )
                        if _err_extracted:
                            _before_err = len(selected)
                            for _ep in _err_extracted:
                                if _ep not in selected:
                                    selected.insert(0, _ep)
                            if len(selected) > _before_err:
                                yield sse("progress", {
                                    "step": "extracted_files_added",
                                    "message": f"📌 {len(selected) - _before_err} فایل ذکرشده در خطا به لیست اضافه شد"
                                })

                        # ── حذف فایل‌های تکراری از لیست (حفظ ترتیب) ──
                        _seen_err_files = set()
                        _deduped_err = []
                        for _sf in selected:
                            if _sf not in _seen_err_files:
                                _seen_err_files.add(_sf)
                                _deduped_err.append(_sf)
                        if len(_deduped_err) < len(selected):
                            slog.info(f"[smart-chat ERROR_LOG] Deduplicated file list: {len(selected)} → {len(_deduped_err)}")
                        selected = _deduped_err

                        # محدود کردن حجم کد بر اساس ظرفیت مدل
                        max_err_code_chars = int(max_input_chars * 0.65)
                        # 🆕 پردازش دسته‌ای برای FULL_PROJECT
                        err_use_batch = (err_scope == "FULL_PROJECT" and len(selected) > 30)
                        if err_use_batch:
                            # ── Background Batch Processing — ERROR_LOG ──
                            e_batch_budget = int(max_input_chars * 0.50)
                            per_file_err_limit = min(8000, max(2000, e_batch_budget // 25))
                            e_batch_size = max(10, min(30, e_batch_budget // max(per_file_err_limit, 1)))
                            e_batches = [selected[i:i+e_batch_size] for i in range(0, len(selected), e_batch_size)]

                            _eproj_id = str(request.project_id) if request.project_id else ""
                            e_task_key, e_bg_info, e_is_reconnect = _start_bg_batch(
                                _eproj_id, request.message, selected, e_batches,
                                per_file_err_limit, github_svc, ai_manager, owner, repo, token,
                                primary_model, model_max_output, history_text, tree_summary,
                                flow_type="error_log"
                            )

                            if e_is_reconnect:
                                yield sse("progress", {"step": "reconnect", "message": "♻️ اتصال مجدد — ادامه تحلیل خطا..."})
                            else:
                                yield sse("progress", {"step": "batch_mode", "message": f"🔄 پردازش دسته‌ای خطا: {len(selected)} فایل در {len(e_batches)} دسته..."})
                            yield sse("progress", {"step": "batch_task_key", "task_key": e_task_key})

                            async for evt in _follow_bg_batch(e_bg_info, sse):
                                yield evt

                            code_context = e_bg_info.get("code_context", "")
                            file_contents = e_bg_info.get("file_contents", {})
                        else:
                            per_file_err_limit = min(12000, max(3000, max_err_code_chars // max(len(selected), 1)))
                            err_read_failures = 0
                            for file_path in selected:
                                if len(code_context) >= max_err_code_chars:
                                    break
                                yield sse("progress", {
                                    "step": "reading_file",
                                    "message": f"📖 خواندن {file_path}..."
                                })
                                try:
                                    result = await github_svc.get_file_content(owner, repo, file_path, token=token)
                                    if result.get("success"):
                                        content = result.get("content", "")
                                        file_contents[file_path] = content  # ذخیره اصلی برای تشخیص بازنویسی مخرب
                                        _total_lines = len(content.split("\n"))
                                        _size_hint = ""
                                        if _total_lines > 200:
                                            _size_hint = f" ⚠️ فایل بزرگ — حتماً از modify_sections استفاده کن — find فقط از همین بخش نمایش‌داده‌شده COPY شود"
                                        if len(content) > per_file_err_limit:
                                            content = content[:per_file_err_limit] + f"\n... [truncated — فایل اصلی {_total_lines} خط دارد{_size_hint}]"
                                        code_context += f"\n\n=== {file_path} ({_total_lines} خط) ===\n{content}"
                                    else:
                                        err_read_failures += 1
                                        slog.warning(f"[smart-chat ERROR_LOG] Failed to read file {file_path}: {result.get('error', 'unknown')}")
                                except Exception as e:
                                    err_read_failures += 1
                                    slog.warning(f"[smart-chat ERROR_LOG] Exception reading file {file_path}: {e}")
                                await asyncio.sleep(0.2)
                        if err_read_failures > 0 and err_read_failures == len(selected):
                            yield sse("progress", {
                                "step": "file_read_warning",
                                "message": f"⚠️ خواندن فایل‌ها ناموفق بود — تحلیل بدون دسترسی به کد..."
                            })
                    else:
                        yield sse("progress", {
                            "step": "tree_failed",
                            "message": f"⚠️ دسترسی به ساختار پروژه ناموفق — تحلیل بدون فایل‌ها..."
                        })
                        slog.warning(f"[smart-chat ERROR_LOG] get_repo_tree failed: {tree_result.get('error', 'unknown')}")

                except Exception as e:
                    yield sse("progress", {
                        "step": "github_error",
                        "message": f"⚠️ دسترسی به GitHub محدود: {str(e)[:60]}"
                    })

            has_err_code_files = bool(code_context and code_context.strip())

            if has_err_code_files:
                err_code_section = f"## کد فایل‌های مرتبط (از GitHub خوانده شده):{code_context}"
                if err_tree_summary:
                    err_code_section += f"\n\n## ساختار کلی پروژه (تو به همه این بخش‌ها دسترسی داری — فایل‌های بالا فقط بخشی از پروژه‌اند):\n{err_tree_summary}"
                err_code_note = """- تو دسترسی کامل به تمام فایل‌های پروژه داری — سیستم مرتبط‌ترین فایل‌ها را خوانده و در بالا آورده
- مستقیماً کد مشکل‌دار را پیدا کن و action_plan بنویس
- 🔴 هرگز محتوای فایلی را حدس نزن — فقط بر اساس فایل‌هایی که واقعاً می‌بینی
- ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «دوباره ارسال کنید» — همیشه با فایل‌های موجود action_plan بنویس
- اگر فایلی وجود ندارد → آن را با operation: "create" بساز"""
            else:
                err_code_section = "## ⚠️ فایل‌های پروژه قابل خواندن نبودند"
                if err_tree_summary:
                    err_code_section += f"\n\nاما ساختار پروژه شناخته شده:\n{err_tree_summary}"
                err_code_note = """- فایل‌های پروژه خوانده نشدند — تحلیل خطا و تشخیص علت را بر اساس اطلاعات موجود ارائه بده
- اگر بتوانی مسیر دقیق فایل مشکل‌دار را تشخیص بدهی (از ساختار پروژه بالا)، بگو کدام فایل باید بررسی شود
- هرگز محتوای فایل حدس نزن — فقط تحلیل متنی ارائه بده"""

            # ── محاسبه بودجه هوشمند بخش‌های متغیر پرامپت خطا ──
            _err_code_len = len(err_code_section)
            _err_inst_len = len(general_instructions_text)
            _err_msg_len = len(request.message)
            _err_reply_len = len(reply_context_text) if reply_context_text else 0
            _err_fixed = _err_code_len + _err_inst_len + _err_msg_len + _err_reply_len + 4000
            _err_var_budget = max(2000, max_input_chars - _err_fixed)
            _err_hist_limit = min(5000, int(_err_var_budget * 0.75))
            _err_logs_limit = min(1500, int(_err_var_budget * 0.25))

            error_analysis_prompt = f"""شما بازرس ارشد پروژه {owner}/{repo} هستید.
{general_instructions_text}
## ⚠️ اصل اول: فهم عمیق منظور کاربر
قبل از هر کاری، بفهم کاربر دقیقاً چه مشکلی دارد و چه می‌خواهد:
- ممکن است فقط لاگ خطا paste کرده باشد بدون توضیح — یعنی می‌خواهد تو تحلیل کنی و حلش کنی
- ممکن است بگوید "باز همون مشکل" — تاریخچه را بخوان و بفهم کدام مشکل
- ممکن است عصبانی باشد ("دوباره خراب شد!") — با درک پاسخ بده و سریع‌تر به راه‌حل برس
- اگر قبلاً راه‌حلی پیشنهاد شده و کاربر دوباره خطا فرستاده، یعنی راه‌حل قبلی جواب نداده — رویکرد متفاوتی بگیر

## قوانین حیاتی:
{err_code_note}
- هرگز از کاربر نخواه کاری دستی انجام دهد (مثل grep، بررسی فایل، اجرای دستور)
- {'حتماً action_plan با محتوای کامل فایل اصلاح‌شده ارائه بده تا کاربر بتواند با یک کلیک اعمال کند' if has_err_code_files else 'فقط تحلیل متنی ارائه بده — action_plan ممنوع است چون فایل‌ها خوانده نشدند'}
- هرگز نگو "نمی‌توانم کمک کنم" — همیشه بهترین تحلیل ممکن را ارائه بده

## ⚠️ این پیام کاربر حاوی لاگ خطا یا گزارش مشکل است.
آن را در ارتباط با تمام مکالمات قبلی این جلسه تحلیل کنید.

## تاریخچه کامل مکالمه:
{history_text[-_err_hist_limit:]}
{reply_context_text if reply_context_text else ''}
## پیام جدید کاربر (حاوی لاگ خطا):
{request.message}

## لاگ‌های بک‌اند:
{logs_text[-_err_logs_limit:] if logs_text else 'موجود نیست'}

{err_code_section}

## وظیفه:
1. اول تاریخچه مکالمه را بخوان و بفهم context چیست
2. لاگ خطا را دقیق بخوان
3. {'در کد فایل‌های مرتبط (بالا) خط مشکل‌دار را پیدا کن' if has_err_code_files else 'بر اساس خطا و تجربه، محل احتمالی مشکل را تشخیص بده'}
4. ارتباط آن را با بررسی/اصلاح قبلی در این جلسه شناسایی کن — اگر قبلاً اصلاحی پیشنهاد شده و جواب نداده، رویکرد متفاوت بگیر
5. علت دقیق خطا را بگو
6. کد اصلاح‌شده را در action_plan ارائه بده (نه فقط توصیه)

## فرمت:
### 🔗 ارتباط با مکالمات قبلی
[توضیح ارتباط]

### 🔍 تحلیل خطا
[تحلیل دقیق]

### 🛠️ راه‌حل پیشنهادی
[کد اصلاحی و مراحل]

### 📁 فایل‌هایی که باید تغییر کنند
[لیست فایل‌ها با توضیح تغییرات - هر فایل در فرمت: `مسیر/فایل`: توضیح]

### 📝 action_plan

🔴 **فرمت ۱ — فایل‌های کوچک (<200 خط):** operation: "modify"
```json
{{
  "files": [
    {{
      "path": "مسیر/فایل-کوچک",
      "operation": "modify",
      "description": "توضیح تغییر",
      "content": "محتوای کامل فایل (فقط برای فایل‌های <200 خط)"
    }}
  ],
  "commit_message": "پیام کامیت مناسب"
}}
```

🔴 **فرمت ۲ — فایل‌های بزرگ (>200 خط) — الزامی:** operation: "modify_sections"
```json
{{
  "files": [
    {{
      "path": "مسیر/فایل-بزرگ.tsx",
      "operation": "modify_sections",
      "description": "توضیح تغییر",
      "sections": [
        {{"find": "متن دقیق از فایل اصلی (چند خط)", "replace": "متن جایگزین"}},
        {{"find": "بخش دوم فایل اصلی", "replace": "جایگزین دوم"}}
      ]
    }}
  ],
  "commit_message": "پیام کامیت مناسب"
}}
```
- 🔴🔴🔴 `find` باید **COPY-PASTE دقیق** از متن فایل اصلی (بالاتر) باشد — شامل تمام فاصله‌ها، tab ها و کامنت‌ها
- ⛔ **هرگز find رو حدس نزن یا از حافظه بنویس** — حتماً از متن فایل که بالاتر آمده COPY کن
- ⛔ اگر find حتی ۱ کاراکتر با فایل واقعی فرق داشته باشه → section **شکست میخوره** و تغییرات اعمال نمیشه
- ✅ find باید حداقل ۲-۳ خط کامل و یکتا از فایل باشه (نه ۱ خط کوتاه)
- ✅ اگر مطمئن نیستی متن دقیقه → find رو بزرگ‌تر بگیر (۵-۱۰ خط)
- سیستم خودش فایل اصلی رو از ریپو میخونه و sections رو اعمال میکنه

⚠️ قوانین action_plan:
- 🔴 **فایل‌های >200 خط**: حتماً از `modify_sections` استفاده کن — سیستم بازنویسی‌های مخرب (<50% اصل) رو **خودکار حذف** میکنه!
- فایل‌های کوچک: content باید محتوای کامل فایل باشد
- اگر نمی‌توانی محتوای کامل فایل بزرگ را بدهی → از modify_sections استفاده کن
- files خالی (`"files": []`) ممنوع است — یا فایل با محتوا/sections بذار، یا action_plan نذار
{'- اگر فایل‌ها خوانده نشدند، action_plan با محتوای حدسی تولید نکن — فقط تحلیل متنی ارائه بده.' if not has_err_code_files else ''}

🚫 ممنوعیت مطلق حدس‌زنی: هرگز محتوای فایلی را که ندیده‌ای حدس نزن. اما **همیشه** با فایل‌های موجود action_plan بنویس. هرگز نگو «فایل در اختیارم نیست» یا «دوباره ارسال کنید».

🏗️ قوانین بیلد و دیپلوی (بسیار مهم):
- فایل‌های کوچک (<200 خط): content باید محتوای کامل و قابل جایگزینی باشد
- 🔴 **فایل‌های بزرگ (>200 خط): از modify_sections استفاده کن** — بازنویسی ممنوع!
- هرگز «// ... بقیه کد» یا «// rest of file» ننویس — یا کل فایل بده یا modify_sections
- imports، پرانتزها، تایپ‌ها و export ها را قبل از نوشتن بررسی کن — هر خطا = شکست دیپلوی
- وابستگی‌ها (requirements.txt, package.json) را با نسخه سازگار پین کن
- ⛔ هرگز نسخه پکیجی پین نکن که مطمئن نیستی وجود دارد — اگر مطمئن نیستی، از caret range (^X.Y.Z) استفاده کن
- قبل از نوشتن هر تغییر، ذهنی بیلد و دیپلوی رو شبیه‌سازی کن: آیا بعد از اعمال این تغییرات، اپلیکیشن بدون خطا بالا میاد؟
- اگر مشکل مربوط به نسخه وابستگی‌هاست، هم نسخه مشکل‌ساز رو پین کن، هم سایر وابستگی‌های مرتبط رو بررسی کن

🎯 حل کامل و یکجا (بسیار مهم — عدم رعایت = حلقه خطاهای متوالی):
- ⛔ هرگز یک مشکل رو نیمه‌کاره حل نکن — قبل از نوشتن action_plan، کل زنجیره وابستگی رو ردیابی کن
- اگر فایل config (postcss.config, vite.config, ...) تغییر میکنه → حتماً package.json و سایر configها هم بررسی بشن
- قبل از نوشتن هر فایل .js config → حتماً package.json فیلد "type" رو بررسی کن: "type": "module" = ESM (export default) / بدون type = CJS (module.exports)
- اگر وابستگی تغییر میکنه → حتماً نسخه‌های مرتبط هم بررسی بشن (مثلاً Tailwind v3 vs v4 پلاگین‌های متفاوتی دارند)
- اگر قبلاً راه‌حلی ارائه شده و جواب نداده → مشکل عمیق‌تر از چیزیه که فکر میکنی — رویکرد کاملاً متفاوت بگیر

🛡️ ممنوعیت بازنویسی مخرب:
- ⛔ هرگز فایل موجود را از صفر بازننویس — فقط بخش مربوط به خطا را تغییر بده و باقی فایل دست‌نخورده بماند
- ⛔ هرگز قابلیت‌های موجود (state, handlers, UI sections) را حذف نکن مگر مستقیماً مشکل‌ساز باشند
- ⛔ قبل از create فایل جدید → بررسی کن آیا مشابهش در پروژه وجود داره
- 🔴 **فایل‌های بزرگ >200 خط**: حتماً از `modify_sections` استفاده کن — سیستم فایل‌هایی که کمتر از 50% اصل باشند رو خودکار حذف میکنه!
- ⚠️ تعداد خطوط هر فایل در عنوان نوشته شده (مثلاً `=== file.tsx (1321 خط) ===`) — از این اطلاعات برای تصمیم‌گیری استفاده کن

🎯 فهم دقیق درخواست: کلمات کاربر را تحت‌اللفظی بخوان. «فقط» = ONLY، «نباید» = ممنوع. هرگز معنی درخواست را برعکس تفسیر نکن."""

            try:
                # 🆕 اجرای AI با heartbeat + timeout کلی
                gen_task = asyncio.create_task(ai_manager.generate(
                    model_id=primary_model,
                    messages=[
                        Message(role="system", content=f"تو بازرس ارشد پروژه هستی. مهم‌ترین کارت فهمیدن منظور واقعی کاربر و ارتباط آن با تاریخچه مکالمه است. {'مستقیماً کد مشکل‌دار را پیدا کن، اصلاحش را بنویس و action_plan ارائه بده.' if has_err_code_files else 'فایل‌ها خوانده نشدند — فقط تحلیل خطا و تشخیص علت ارائه بده. هرگز action_plan با محتوای حدسی تولید نکن.'} اگر قبلاً راه‌حلی پیشنهاد شده و جواب نداده، رویکرد متفاوتی بگیر. هرگز کاربر را به کار دستی ارجاع نده. ⛔ هرگز فایل موجود را از صفر بازننویس — فقط بخش مشکل‌ساز تغییر کن. هرگز قابلیت‌های موجود را حذف نکن. 🔴 فایل‌های بزرگ (>200 خط): حتماً از modify_sections استفاده کن — سیستم بازنویسی‌های مخرب رو خودکار حذف میکنه! تعداد خطوط هر فایل در عنوان نوشته شده. کلمات کاربر را تحت‌اللفظی بخوان: «فقط» = ONLY، «نباید» = ممنوع. ⛔ هرگز نگو «دسترسی ندارم» یا «دوباره ارسال کنید». با لحن صمیمی و حرفه‌ای پاسخ بده."),
                        Message(role="user", content=error_analysis_prompt)
                    ],
                    max_tokens=model_max_output,
                    temperature=0.4
                ))
                total_wait_err = 0
                initial_wait_err = 300  # هشدار اولیه در 5 دقیقه
                max_wait_err = 600  # حداکثر مطلق 10 دقیقه
                warned_err = False
                timed_out_err = False
                while not gen_task.done():
                    done_set, _ = await asyncio.wait({gen_task}, timeout=5.0)
                    if not done_set:
                        total_wait_err += 5
                        if total_wait_err >= max_wait_err:
                            gen_task.cancel()
                            yield sse("error", {
                                "message": f"⏱️ مدل {primary_model} بعد از {max_wait_err} ثانیه پاسخ نداد. لطفاً مدل سریع‌تری انتخاب کنید."
                            })
                            timed_out_err = True
                            break
                        if total_wait_err >= initial_wait_err and not warned_err:
                            warned_err = True
                            yield sse("timeout_warning", {
                                "message": f"⏱️ مدل {primary_model} نیاز به زمان بیشتری دارد... مهلت تا {max_wait_err} ثانیه تمدید شد.",
                                "elapsed": total_wait_err,
                                "max_wait": max_wait_err
                            })
                        yield sse("heartbeat", {"message": f"⏳ مدل در حال تحلیل خطا... ({total_wait_err}s)"})
                if timed_out_err:
                    yield sse("done", {"success": False})
                    return
                response = gen_task.result()

                # 🧹 حذف بلوک‌های استدلال/reasoning + بررسی پاسخ خالی
                _err_content = _strip_reasoning_blocks(response.content) if response.content else ""
                _err_model_used = response.model_id
                _err_tokens = response.tokens_used
                # 🆕 تشخیص truncation
                _err_finish = getattr(response, 'finish_reason', '') or ''
                _err_is_truncated = _err_finish.lower() in ('length', 'max_tokens')

                if not _err_content or not _err_content.strip():
                    slog.warning(f"[smart-chat] Empty ERROR_LOG response, model={primary_model}, prompt_len={len(error_analysis_prompt)}")
                    _err_sys_msg = f"تو بازرس ارشد پروژه هستی. {'مستقیماً کد مشکل‌دار را پیدا کن، اصلاحش را بنویس و action_plan ارائه بده.' if has_err_code_files else 'فایل‌ها خوانده نشدند — فقط تحلیل خطا ارائه بده.'} ⛔ فایل موجود از صفر بازننویس نکن. قابلیت‌های موجود حذف نکن. کلمات کاربر دقیق بخوان. با لحن صمیمی و حرفه‌ای پاسخ بده."
                    _reduced_err = _reduce_prompt_for_retry(error_analysis_prompt)
                    _retry_models = [primary_model]
                    _fb = ai_manager.find_fallback_model(primary_model)
                    if _fb and _fb != primary_model:
                        _retry_models.append(_fb)
                    for _ri, _rm in enumerate(_retry_models):
                        _rl = "پرامپت کاهش‌یافته" if _ri == 0 else f"مدل جایگزین ({_rm})"
                        yield sse("progress", {"step": "retry_empty", "message": f"⚠️ پاسخ خالی — تلاش مجدد با {_rl}..."})
                        try:
                            _rr = await ai_manager.generate(
                                model_id=_rm,
                                messages=[Message(role="system", content=_err_sys_msg), Message(role="user", content=_reduced_err)],
                                max_tokens=model_max_output,
                                temperature=0.4,
                            )
                            if _rr.content and _rr.content.strip():
                                _err_content = _rr.content
                                _err_model_used = _rr.model_id
                                _err_tokens = _rr.tokens_used
                                _err_finish = getattr(_rr, 'finish_reason', '') or ''
                                _err_is_truncated = _err_finish.lower() in ('length', 'max_tokens')
                                slog.info(f"[smart-chat] ERROR_LOG retry succeeded: model={_rm}")
                                yield sse("progress", {"step": "retry_success", "message": f"✅ تلاش مجدد موفق — مدل {_rm} پاسخ داد"})
                                break
                        except Exception as _re:
                            slog.warning(f"[smart-chat] ERROR_LOG retry {_ri+1} failed: {_re}")
                    if not _err_content or not _err_content.strip():
                        yield sse("error", {
                            "message": f"❌ مدل {primary_model} پاسخ خالی برگرداند (حتی بعد از تلاش مجدد) | حجم: ~{len(error_analysis_prompt)} کاراکتر",
                            "detail": f"مدل: {primary_model} | حجم: ~{len(error_analysis_prompt)} | context: {model_context_window}"
                        })
                if _err_content and _err_content.strip():
                    # 🆕 استخراج و ادغام تمام بلوک‌های JSON (پشتیبانی از بلوک‌های متعدد + تعمیر ناقص)
                    action_plan = _extract_all_action_plans_from_response(_err_content, is_truncated=_err_is_truncated)

                    # لایه ۲: اگر فایل‌ها خوانده نشدن، action_plan حذف شود
                    # 🆕 (clarify-first) — ask_user/route_to استثنا است
                    _err_is_clarify = bool(action_plan and (action_plan.get("ask_user") or action_plan.get("route_to")))
                    if not has_err_code_files and action_plan is not None and not _err_is_clarify:
                        slog.warning(f"[smart-chat ERROR_LOG] AI generated action_plan without reading files — stripped")
                        action_plan = None

                    has_code_action = action_plan is not None or any(marker in _err_content for marker in [
                        "```", "فایل‌هایی که باید تغییر", "اصلاح کنید"
                    ])

                    # 🆕 هشدار truncation به کاربر
                    if _err_is_truncated:
                        _trunc_msg = ""
                        if action_plan:
                            _trunc_msg = f"\n\n---\n⚠️ **هشدار:** پاسخ مدل ناقص بود — {len(action_plan.get('files', []))} فایل از action_plan نجات یافت."
                        else:
                            _trunc_msg = "\n\n---\n⚠️ **هشدار:** پاسخ مدل به دلیل محدودیت خروجی ناقص قطع شد. لطفاً با مدل دیگری تلاش کنید."
                        _err_content += _trunc_msg

                    yield sse("response", {
                        "type": "error_analysis",
                        "content": _err_content,
                        "model_used": _err_model_used,
                        "tokens_used": _err_tokens,
                        "has_action": has_code_action,
                        "action_plan": _validate_action_plan_syntax(action_plan, original_files=file_contents, repo_file_paths=_normalize_repo_paths(locals().get("all_files")), user_message=request.message, backend_logs=request.backend_logs, code_files=locals().get("code_files")) if action_plan else None,
                        "files_were_read": has_err_code_files,
                        "selected_file_paths": selected if has_err_code_files else [],
                        "truncated": _err_is_truncated,
                    })

            except asyncio.CancelledError:
                slog.error(f"[smart-chat] CancelledError ERROR_LOG model={primary_model}")
                yield sse("error", {"message": f"❌ عملیات مدل {primary_model} لغو شد. لطفاً دوباره تلاش کنید."})
            except Exception as e:
                slog.error(f"[smart-chat] ERROR_LOG model={primary_model} error={str(e)[:200]}")
                yield sse("error", {"message": f"❌ خطا در تحلیل خطا توسط مدل {primary_model}: {str(e)[:150]}"})

        else:  # ACTION
            # درخواست اقدام: تحلیل عمیق + آماده‌سازی تغییرات

            # 🆕 تشخیص دامنه درخواست — آیا کاربر همه فایل‌ها رو میخواد یا فقط بخشی؟
            request_scope = _detect_request_scope(request.message, history_text)
            scope_labels = {
                "FULL_PROJECT": "کل پروژه",
                "BROAD": "بررسی گسترده",
                "TARGETED": "هدفمند"
            }

            yield sse("progress", {
                "step": "reading_project",
                "message": f"📂 در حال خواندن ساختار پروژه {owner}/{repo}... (دامنه: {scope_labels.get(request_scope, request_scope)})"
            })

            code_context = ""
            code_files = []
            file_contents = {}  # دیکشنری فایل‌های اصلی برای تشخیص بازنویسی مخرب
            act_tree_summary = ""
            use_batch_processing = False
            _batch_count = 0
            _batch_total_read = 0
            if owner and repo:
                try:
                    tree_result = await github_svc.get_repo_tree(owner, repo, token=token)
                    if tree_result.get("success"):
                        all_files = [f for f in tree_result.get("tree", []) if f.get("type") == "blob"]
                        code_files = [f["path"] for f in all_files
                                      if _is_code_file(f["path"], file_size=f.get("size", 0))]

                        # 🆕 تعداد فایل‌ها بر اساس دامنه درخواست
                        dynamic_max_files = _get_max_files_for_scope(request_scope, len(code_files))

                        yield sse("progress", {
                            "step": "tree_loaded",
                            "message": f"✅ ساختار پروژه خوانده شد ({len(code_files)} فایل) — بررسی تا {dynamic_max_files} فایل"
                        })

                        # ساخت خلاصه ساختار پروژه
                        act_tree_summary = _build_project_tree_summary(code_files)

                        # 🆕🆕 (agent-loop / فاز ۱) — اگر مدل tool-calling دارد
                        # (Claude)، حلقهٔ عامل واقعی اجرا کن؛ وگرنه fallback به
                        # pipeline تک‌شات پایین.
                        _agent_handled = False
                        async for _chunk in _run_agent_section(code_files, all_files):
                            if isinstance(_chunk, tuple) and _chunk and _chunk[0] == "__handled__":
                                _agent_handled = _chunk[1]
                            else:
                                yield _chunk
                        if _agent_handled:
                            return

                        # 🆕 استخراج فایل‌های ذکرشده در پیام/خطا/تاریخچه — حتماً باید خونده بشن
                        _msg_extracted = _extract_file_paths_from_text(
                            request.message + "\n" + history_text[-5000:], code_files
                        )

                        # 🆕 اگر دامنه FULL_PROJECT باشه، همه فایل‌ها رو بخون بدون انتخاب AI
                        if request_scope == "FULL_PROJECT":
                            selected = code_files[:dynamic_max_files]
                            yield sse("progress", {
                                "step": "files_selected",
                                "message": f"📋 دامنه کل پروژه: {len(selected)} فایل از {len(code_files)} فایل انتخاب شد"
                            })
                        elif request_scope == "BROAD":
                            # BROAD: AI انتخاب میکنه ولی با سقف بالاتر
                            yield sse("progress", {
                                "step": "selecting_files",
                                "message": f"🤖 مدل {primary_model} در حال شناسایی فایل‌های مرتبط (دامنه گسترده: تا {dynamic_max_files} فایل)..."
                            })

                            select_prompt = f"""بر اساس درخواست کاربر و تاریخچه مکالمه، فایل‌های مرتبط را انتخاب کن:

درخواست کاربر:
{request.message}

تاریخچه مکالمه (تا ۵۰۰۰ کاراکتر آخر):
{history_text[-5000:]}

{act_tree_summary}
{prev_files_hint}

فایل‌های پروژه:
{chr(10).join(code_files[:500])}

## راهنمای انتخاب — دامنه گسترده:
- کاربر درخواست بررسی گسترده دارد — فایل‌های بیشتری انتخاب کن
- اول منظور واقعی کاربر را بفهم — ممکن است مستقیم نگفته باشد کدام فایل‌ها
- تاریخچه مکالمه را بخوان
- از هر بخش پروژه (frontend/backend/shared/config/test) فایل انتخاب کن
- فایل‌های config، types، test و utility هم مهمن

حداکثر {dynamic_max_files} فایل. فقط مسیرها، هر کدام در یک خط."""

                            select_response = await ai_manager.generate(
                                model_id=primary_model,
                                messages=[
                                    Message(role="system", content=f"انتخاب‌گر فایل حرفه‌ای. درخواست کاربر بررسی گسترده پروژه است. تا {dynamic_max_files} فایل مرتبط انتخاب کن. فقط مسیرها."),
                                    Message(role="user", content=select_prompt)
                                ],
                                max_tokens=2000,
                                temperature=0.2
                            )

                            selected = _parse_ai_selected_files(select_response.content, code_files, max_files=dynamic_max_files)
                            if not selected:
                                selected = _fallback_file_selection(code_files, request.message, max_files=dynamic_max_files)
                            selected = _ensure_balanced_selection(selected, code_files, max_files=dynamic_max_files)

                            yield sse("progress", {
                                "step": "files_selected",
                                "message": f"📋 {len(selected)} فایل مرتبط شناسایی شد (دامنه گسترده)"
                            })
                        else:
                            # TARGETED: مثل قبل — AI انتخاب با سقف 25
                            yield sse("progress", {
                                "step": "selecting_files",
                                "message": f"🤖 مدل {primary_model} در حال شناسایی فایل‌های مرتبط..."
                            })

                            # 🆕 تشخیص دامنه درخواست (frontend/backend/cross)
                            _act_domain = _detect_error_domain(request.message + "\n" + history_text[-2000:])
                            _act_domain_hint = ""
                            if _act_domain == "frontend":
                                _act_domain_hint = "\n⚠️ این درخواست مربوط به فرانت‌اند/build است — فقط فایل‌های فرانت‌اند و config انتخاب کن. فایل‌های Python/backend نامرتبطند."
                            elif _act_domain == "backend":
                                _act_domain_hint = "\n⚠️ این درخواست مربوط به بک‌اند است — فقط فایل‌های Python/backend و config انتخاب کن. فایل‌های frontend نامرتبطند."

                            select_prompt = f"""بر اساس درخواست کاربر و تاریخچه مکالمه، فایل‌های مرتبط را انتخاب کن:

درخواست کاربر:
{request.message}

تاریخچه مکالمه (تا ۵۰۰۰ کاراکتر آخر):
{history_text[-5000:]}

{act_tree_summary}
{prev_files_hint}

فایل‌های پروژه:
{chr(10).join(code_files[:500])}

## راهنمای انتخاب هوشمند:
- اول منظور واقعی کاربر را بفهم — ممکن است مستقیم نگفته باشد کدام فایل‌ها باید تغییر کنند
- تاریخچه مکالمه را بخوان — شاید درخواست در ادامه بحث قبلی باشد و فایل‌های مرتبط قبلاً ذکر شده باشند
- فایل‌هایی که مستقیماً باید تغییر کنند + وابستگی‌هایشان (imports, types, configs, API routes, database models)
- فایل‌های config مرتبط حتماً شامل شوند: package.json, tsconfig.json, postcss.config, vite.config, tailwind.config, requirements.txt, Dockerfile
- اگر فایل‌هایی قبلاً بررسی شده‌اند (لیست بالا)، فایل‌های جدید و بررسی‌نشده را اولویت بده — مگر اینکه تغییرات واقعاً به همان فایل‌ها مربوط باشد
- فایل‌های تست مرتبط با فایل‌های تغییردهنده را هم شامل کن
- اگر تغییر API endpoint باشد، هم route و هم فرانت‌اند caller و هم types مرتبط را انتخاب کن
{_act_domain_hint}

⛔ فقط فایل‌های واقعاً مرتبط — خواندن فایل‌های نامرتبط باعث هدررفت بودجه میشود.

حداکثر ۲۵ فایل. فقط مسیرها، هر کدام در یک خط."""

                            select_response = await ai_manager.generate(
                                model_id=primary_model,
                                messages=[
                                    Message(role="system", content="انتخاب‌گر فایل هوشمند و حرفه‌ای. اول منظور واقعی درخواست کاربر و تاریخچه مکالمه را عمیقاً بفهم، سپس فایل‌های مرتبط + زنجیره وابستگی‌ها + فایل‌های تست را انتخاب کن. فایل‌های جدید و بررسی‌نشده اولویت دارند. فقط مسیرها."),
                                    Message(role="user", content=select_prompt)
                                ],
                                max_tokens=1000,
                                temperature=0.2
                            )

                            selected = _parse_ai_selected_files(select_response.content, code_files, max_files=25)
                            if not selected:
                                selected = _fallback_file_selection(code_files, request.message, max_files=20)
                            selected = _ensure_balanced_selection(selected, code_files, max_files=25, error_domain=_act_domain)

                            yield sse("progress", {
                                "step": "files_selected",
                                "message": f"📋 {len(selected)} فایل مرتبط شناسایی شد"
                            })

                        # 🆕 اطمینان از اینکه فایل‌های ذکرشده در پیام/خطا حتماً در لیست هستند
                        if _msg_extracted:
                            _before_merge = len(selected)
                            for _ep in _msg_extracted:
                                if _ep not in selected:
                                    selected.insert(0, _ep)  # اولویت بالا — اول لیست
                            if len(selected) > _before_merge:
                                yield sse("progress", {
                                    "step": "extracted_files_added",
                                    "message": f"📌 {len(selected) - _before_merge} فایل ذکرشده در پیام/خطا به لیست اضافه شد"
                                })

                        # ── حذف فایل‌های تکراری از لیست (حفظ ترتیب) ──
                        _seen_files = set()
                        _deduped_selected = []
                        for _sf in selected:
                            if _sf not in _seen_files:
                                _seen_files.add(_sf)
                                _deduped_selected.append(_sf)
                        if len(_deduped_selected) < len(selected):
                            slog.info(f"[smart-chat ACTION] Deduplicated file list: {len(selected)} → {len(_deduped_selected)}")
                        selected = _deduped_selected

                        # خواندن فایل‌ها (با رعایت حد context window مدل)
                        max_code_chars = int(max_input_chars * 0.70)

                        # 🆕 پردازش دسته‌ای (Batch Processing) — مثل منطق Claude Code
                        # وقتی فایل‌ها زیادن، به جای خلاصه‌خوانی، فایل‌ها رو دسته‌دسته
                        # با محتوای کامل میخونیم و هر دسته رو جداگانه تحلیل می‌کنیم
                        use_batch_processing = (request_scope == "FULL_PROJECT" and len(selected) > 30)

                        if use_batch_processing:
                            # ── Background Batch Processing — مستقل از SSE ──
                            batch_budget = int(max_input_chars * 0.55)
                            per_file_limit = min(8000, max(2000, batch_budget // 25))
                            batch_size = max(10, min(30, batch_budget // max(per_file_limit, 1)))
                            batches = [selected[i:i+batch_size] for i in range(0, len(selected), batch_size)]

                            _proj_id = str(request.project_id) if request.project_id else ""
                            task_key, bg_info, is_reconnect = _start_bg_batch(
                                _proj_id, request.message, selected, batches,
                                per_file_limit, github_svc, ai_manager, owner, repo, token,
                                primary_model, model_max_output, history_text, act_tree_summary,
                                flow_type="action"
                            )
                            _batch_count = len(batches)

                            if is_reconnect:
                                yield sse("progress", {
                                    "step": "reconnect",
                                    "message": f"♻️ اتصال مجدد — پردازش در حال اجرا ({bg_info.get('total_read', 0)} فایل تا الان)"
                                })
                            else:
                                yield sse("progress", {
                                    "step": "batch_mode",
                                    "message": f"🔄 پردازش دسته‌ای بک‌گراند: {len(selected)} فایل در {_batch_count} دسته"
                                })
                            yield sse("progress", {"step": "batch_task_key", "task_key": task_key})

                            # دنبال کردن event‌های background task
                            async for evt in _follow_bg_batch(bg_info, sse):
                                yield evt

                            # نتایج
                            code_context = bg_info.get("code_context", "")
                            file_contents = bg_info.get("file_contents", {})
                            _batch_total_read = bg_info.get("total_read", 0)
                            _batch_count = bg_info.get("batch_count", _batch_count)

                        else:
                            # ── BROAD / TARGETED — خواندن عادی ──
                            per_file_limit = min(15000, max(3000, max_code_chars // max(len(selected), 1)))
                            act_read_failures = 0
                            for i, file_path in enumerate(selected):
                                if len(code_context) >= max_code_chars:
                                    yield sse("progress", {
                                        "step": "context_limit",
                                        "message": f"⚠️ به حد ظرفیت مدل رسیدیم — {len(selected) - i} فایل باقیمانده خوانده نشد"
                                    })
                                    break
                                yield sse("progress", {
                                    "step": "reading_file",
                                    "message": f"📖 خواندن {file_path} ({i+1}/{len(selected)})..."
                                })
                                try:
                                    result = await github_svc.get_file_content(owner, repo, file_path, token=token)
                                    if result.get("success"):
                                        content = result.get("content", "")
                                        file_contents[file_path] = content  # ذخیره اصلی برای تشخیص بازنویسی مخرب
                                        _total_lines = len(content.split("\n"))
                                        _size_hint = ""
                                        if _total_lines > 200:
                                            _size_hint = f" ⚠️ فایل بزرگ — حتماً از modify_sections استفاده کن — find فقط از همین بخش نمایش‌داده‌شده COPY شود"
                                        if len(content) > per_file_limit:
                                            content = content[:per_file_limit] + f"\n... [truncated — فایل اصلی {_total_lines} خط دارد{_size_hint}]"
                                        code_context += f"\n\n=== {file_path} ({_total_lines} خط) ===\n{content}"
                                    else:
                                        act_read_failures += 1
                                        slog.warning(f"[smart-chat ACTION] Failed to read file {file_path}: {result.get('error', 'unknown')}")
                                except Exception as e:
                                    act_read_failures += 1
                                    slog.warning(f"[smart-chat ACTION] Exception reading file {file_path}: {e}")
                                await asyncio.sleep(0.2)

                            if act_read_failures > 0 and act_read_failures == len(selected):
                                yield sse("progress", {
                                    "step": "file_read_warning",
                                    "message": f"⚠️ خواندن فایل‌ها ناموفق بود — تحلیل بدون دسترسی به کد..."
                                })
                    else:
                        yield sse("progress", {
                            "step": "tree_failed",
                            "message": f"⚠️ دسترسی به ساختار پروژه ناموفق — تحلیل بدون فایل‌ها..."
                        })
                        slog.warning(f"[smart-chat ACTION] get_repo_tree failed: {tree_result.get('error', 'unknown')}")

                except Exception as e:
                    yield sse("progress", {
                        "step": "github_error",
                        "message": f"⚠️ خطا در دسترسی GitHub: {str(e)[:60]}"
                    })

            # --- تحلیل عمیق و تولید پاسخ + اکشن ---
            has_code_files = bool(code_context and code_context.strip())

            if not has_code_files:
                yield sse("progress", {
                    "step": "no_files_warning",
                    "message": f"⚠️ فایل‌های پروژه خوانده نشد (GitHub Token یا اطلاعات ریپو ناقص) — تحلیل بر اساس اطلاعات موجود..."
                })

            yield sse("progress", {
                "step": "deep_analysis",
                "message": f"🧠 مدل {primary_model} در حال تحلیل عمیق و آماده‌سازی تغییرات..."
            })

            # ساخت بخش کد فایل‌ها بر اساس دسترسی
            if has_code_files:
                if use_batch_processing:
                    # 🆕 حالت دسته‌ای — یافته‌های تحلیل AI از هر دسته (فایل‌ها کامل خوانده شدن)
                    code_section = f"""## 🔄 تحلیل دسته‌ای کل پروژه ({len(selected)} فایل — محتوای کامل خوانده شد):
فایل‌ها در {_batch_count} دسته با محتوای کامل خوانده و تحلیل شدند.
یافته‌های هر دسته در زیر آمده — وظیفه تو جمع‌بندی نهایی و پاسخ جامع است.

{code_context}"""
                    if act_tree_summary:
                        code_section += f"\n\n## ساختار درختی پروژه:\n{act_tree_summary}"
                    code_instructions = f"""- تحلیل‌های بالا از بررسی دسته‌ای {_batch_total_read} فایل پروژه (با محتوای کامل) به دست آمده
- تمام یافته‌های {_batch_count} دسته را جمع‌بندی و ترکیب کن
- پاسخ نهایی جامع و کامل ارائه بده — هیچ دسته‌ای را نادیده نگیر
- اگر یک فایل در دسته‌های مختلف ذکر شده، اطلاعات رو ترکیب کن
- لیست کامل و مرتب نتایج ارائه بده
- تحلیل قابل اتکاست چون فایل‌ها کامل خوانده شده‌اند — نیازی به حدس نیست
- 🔴 ممنوعیت مطلق: هرگز محتوای فایلی را حدس نزن — فقط بر اساس محتوای واقعی خوانده‌شده"""
                else:
                    code_section = f"""## کد فایل‌های مرتبط (از GitHub خوانده شده):
{code_context}"""
                    if act_tree_summary:
                        code_section += f"\n\n## ساختار کلی پروژه (تو به همه این بخش‌ها دسترسی داری — فایل‌های بالا فقط بخشی از پروژه‌اند):\n{act_tree_summary}"
                    code_instructions = """- 🔑 تو دسترسی کامل به تمام فایل‌های پروژه داری — سیستم هوشمند مرتبط‌ترین فایل‌ها را از کل مخزن انتخاب و خوانده
- ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «دوباره ارسال کنید»، «قادر به نوشتن action_plan نیستم»
- ✅ **همیشه** با فایل‌های موجود action_plan کامل بنویس — حتی اگر فکر کنی فایلی کم است
- مستقیماً کد مشکل‌دار را پیدا کن و اصلاحش را ارائه بده
- حتماً action_plan کامل با محتوای کامل فایل اصلاح‌شده ارائه بده
- 🔴 محتوای فایلی را حدس نزن — فقط فایل‌هایی که واقعاً محتوایشان را می‌بینی در action_plan بگذار
- فایل‌هایی که وجود ندارند → با operation: "create" بساز
- از عبارات «فرض می‌کنیم»، «احتمالاً»، «ساختارش باید اینطوری باشه» استفاده نکن
- فقط بر اساس کدی که واقعاً در بالا آمده کار کن — نه بر اساس حافظه، حدس، یا الگوهای رایج"""
            else:
                code_section = """## ⚠️ دسترسی به فایل‌های پروژه:
فایل‌های پروژه قابل خواندن نبودند (احتمالاً GitHub Token تنظیم نشده یا اطلاعات ریپو ناقص)."""
                if act_tree_summary:
                    code_section += f"\n\nاما ساختار پروژه شناخته شده:\n{act_tree_summary}"
                code_instructions = """- فایل‌های پروژه خوانده نشدند — تحلیل و تشخیص مشکل بر اساس تاریخچه مکالمه و لاگ‌ها ارائه بده
- اگر بتوانی مسیر دقیق فایل مشکل‌دار را تشخیص بدهی (از ساختار پروژه)، بگو کدام فایل باید بررسی شود
- هرگز محتوای فایل حدس نزن — فقط تحلیل متنی ارائه بده
- بگو برای ارائه کد اصلاحی به دسترسی GitHub نیاز داری"""

            # ── محاسبه بودجه هوشمند بخش‌های متغیر پرامپت اصلی ──
            _act_code_len = len(code_section)
            _act_inst_len = len(general_instructions_text)
            _act_msg_len = len(request.message)
            _act_reply_len = len(reply_context_text) if reply_context_text else 0
            _act_fixed = _act_code_len + _act_inst_len + _act_msg_len + _act_reply_len + 4000
            _act_var_budget = max(2000, max_input_chars - _act_fixed)
            _act_hist_limit = min(5000, int(_act_var_budget * 0.70))
            _act_logs_limit = min(1000, int(_act_var_budget * 0.15))

            # اگر حجم کل هنوز بیش از ظرفیته، code_section رو کاهش بده
            _total_est = _act_code_len + _act_inst_len + _act_msg_len + _act_reply_len + _act_hist_limit + _act_logs_limit + 4000
            if _total_est > max_input_chars and _act_code_len > 5000:
                _allowed_code = max(5000, max_input_chars - (_act_inst_len + _act_msg_len + _act_reply_len + _act_hist_limit + _act_logs_limit + 4000))
                if _allowed_code < _act_code_len:
                    code_section = code_section[:_allowed_code] + "\n\n... [بخشی از فایل‌ها به دلیل محدودیت ظرفیت مدل حذف شد]"
                    slog.warning(f"[smart-chat] Code section truncated: {_act_code_len} -> {_allowed_code}")
                    yield sse("progress", {
                        "step": "prompt_truncation",
                        "message": f"⚠️ حجم کد ({_act_code_len:,}) بیش از ظرفیت مدل — بهینه‌سازی شد"
                    })

            action_prompt = f"""شما بازرس ارشد و توسعه‌دهنده پروژه {owner}/{repo} هستید.
{general_instructions_text}
## ⚠️ اصل اول: فهم عمیق منظور کاربر
قبل از هر کاری، منظور واقعی کاربر را بفهم:
- کاربران اغلب دقیق و فنی صحبت نمی‌کنند — "این دکمه کار نمیکنه" یعنی باید onClick handler و API call مربوطه بررسی شود
- "مثل قبلی درستش کن" یعنی تاریخچه مکالمه را بخوان و بفهم الگوی اصلاح قبلی چه بوده
- "باز هم مشکل داره" یعنی راه‌حل قبلی جواب نداده — رویکرد متفاوتی بگیر
- اگر پیام کوتاه و مبهم است، حتماً تاریخچه مکالمه را بخوان تا context کامل را بفهمی
- وقتی کاربر ناراحت یا عصبانی است، سریع‌تر به راه‌حل عملی برس — توضیحات طولانی نده
- هرگز نپرس "آیا می‌خواهید اصلاح کنم؟" — اگر کاربر مشکلی گزارش کرده، یعنی می‌خواهد حل شود

## قوانین حیاتی:
{code_instructions}
- هرگز از کاربر نخواه کاری دستی انجام دهد (مثل grep زدن، بررسی فایل، اجرای دستور در ترمینال)
- تمام وابستگی‌ها (imports, types, configs) را بررسی کن
- تغییرات باید با ساختار فعلی پروژه سازگار باشد
- ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «دوباره بپرسید»، «دوباره ارسال کنید» — همیشه با فایل‌های موجود action_plan بنویس. محتوای حدسی ننویس

## تاریخچه کامل مکالمه:
{history_text[-_act_hist_limit:]}
{reply_context_text if reply_context_text else ''}
## درخواست جدید کاربر:
{request.message}

## لاگ‌های اخیر:
{logs_text[-_act_logs_limit:] if logs_text else 'موجود نیست'}

{code_section}

## فرمت پاسخ (حتماً JSON معتبر در بلوک action_plan):

### 📋 تحلیل درخواست
[توضیح دقیق چه چیزی باید تغییر کنه]

### 🔍 بررسی وابستگی‌ها
[چه فایل‌هایی تحت تأثیر قرار می‌گیرند]

### 🛠️ تغییرات پیشنهادی
[توضیح کامل هر تغییر]

### 📝 action_plan

🔴 **فرمت ۱ — فایل‌های کوچک (<200 خط):** operation: "modify" با محتوای کامل
```json
{{
  "files": [
    {{
      "path": "مسیر/فایل-کوچک",
      "operation": "modify",
      "description": "توضیح تغییر",
      "content": "محتوای کامل فایل (فقط برای فایل‌های <200 خط)"
    }}
  ],
  "commit_message": "پیام کامیت مناسب"
}}
```

🔴 **فرمت ۲ — فایل‌های بزرگ (>200 خط) — الزامی:** operation: "modify_sections"
```json
{{
  "files": [
    {{
      "path": "مسیر/فایل-بزرگ.tsx",
      "operation": "modify_sections",
      "description": "توضیح تغییر",
      "sections": [
        {{"find": "متن دقیق از فایل اصلی (چند خط)", "replace": "متن جایگزین"}},
        {{"find": "بخش دوم فایل اصلی", "replace": "جایگزین دوم"}}
      ]
    }}
  ],
  "commit_message": "پیام کامیت مناسب"
}}
```
- 🔴🔴🔴 `find` باید **COPY-PASTE دقیق** از متن فایل اصلی باشد — شامل تمام فاصله‌ها، tab ها و کامنت‌ها
- ⛔ **هرگز find رو حدس نزن** — حتماً از متن فایل COPY کن — حتی ۱ کاراکتر فرق = شکست
- ✅ find حداقل ۲-۳ خط یکتا — اگر مطمئن نیستی، بزرگ‌تر بگیر (۵-۱۰ خط)
- سیستم خودش فایل اصلی رو از ریپو میخونه و sections رو اعمال میکنه — هیچ بخشی حذف نمیشه

⚠️ قوانین action_plan:
- 🔴 **فایل‌های >200 خط**: حتماً از `modify_sections` استفاده کن — سیستم بازنویسی‌های مخرب (<50% اصل) رو **خودکار حذف** میکنه!
- فایل‌های کوچک (<200 خط): content باید محتوای کامل فایل باشد (نه تکه‌ای)
- اگر نمی‌توانی محتوای کامل فایل بزرگ را بدهی → از modify_sections استفاده کن بجای حذف از action_plan
- files خالی (`"files": []`) ممنوع است — یا فایل با محتوا/sections بذار، یا action_plan نذار
{'- اگر فایل‌ها خوانده نشدند، action_plan با محتوای حدسی تولید نکن — فقط تحلیل متنی ارائه بده.' if not has_code_files else ''}

🔑🔴 دسترسی کامل — ممنوعیت مطلق امتناع از action_plan:
- تو دسترسی کامل به تمام فایل‌های پروژه داری — سیستم مرتبط‌ترین فایل‌ها را از کل مخزن انتخاب و خوانده
- ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «در اختیارم قرار نگرفته»، «دوباره ارسال کنید»، «دوباره بپرسید»
- ⛔ هرگز نگو «قادر به نوشتن action_plan نیستم» — **همیشه** action_plan بنویس
- ✅ بر اساس فایل‌های ارائه‌شده تحلیل و کدنویسی کن — اینها با هوش مصنوعی از کل پروژه انتخاب شده‌اند
- ✅ فایل‌هایی که محتوایشان را می‌بینی → operation: "update" | فایل‌هایی که وجود ندارند → operation: "create"
- محتوای فایلی را حدس نزن — ولی **حتماً** action_plan کامل بنویس
- از عبارات «فرض می‌کنیم»، «احتمالاً»، «ساختارش باید اینطوری باشه» استفاده نکن

🏗️ قوانین حیاتی بیلد و دیپلوی (عدم رعایت = شکست دیپلوی):
- فایل‌های کوچک (<200 خط): content باید **محتوای کامل و قابل جایگزینی** باشد — نه بخشی از فایل
- 🔴 **فایل‌های بزرگ (>200 خط): از modify_sections استفاده کن** — بازنویسی کامل فایل بزرگ ممنوع و خودکار حذف میشه!
- هرگز «// ... بقیه کد»، «// rest of file»، «/* existing code */» ننویس — یا کل فایل بده (اگر <200 خط) یا modify_sections بنویس
- قبل از نوشتن هر فایل، بررسی کن: imports صحیح؟ پرانتز/آکولاد بسته؟ تایپ‌ها درست؟ export سازگار؟
- اگر فایل بزرگ‌تر از توان تولید توست، آن را در action_plan نگذار — به جایش بنویس چه تغییری لازم است
- تمام وابستگی‌های بین فایلی: اگر type/interface تغییر کرد، تمام فایل‌های مصرف‌کننده هم باید آپدیت شوند
- JSX/TSX: تمام تگ‌ها بسته شوند، className نه class، htmlFor نه for
- JSON: بدون trailing comma، کلیدها string باشند
- Python: indentation یکدست (4 spaces)، import ها valid، async/await صحیح
- وابستگی‌ها (requirements.txt, package.json) با نسخه سازگار پین شوند
- ⛔ هرگز نسخه پکیجی پین نکن که مطمئن نیستی وجود دارد — اگر مطمئن نیستی از caret range (^X.Y.Z) استفاده کن

🎯 حل کامل و یکجا — مهم‌ترین قانون:
- ⛔ مشکل را نیمه‌کاره حل نکن — قبل از action_plan، کل زنجیره وابستگی رو ردیابی کن
- قبل از نوشتن هر فایل .js config → package.json فیلد "type" رو بررسی کن: "type": "module" = ESM / بدون type = CJS
- اگر config تغییر میکنه → تمام configهای مرتبط هم بررسی بشن (postcss → package.json → vite.config → tailwind.config)
- اگر وابستگی تغییر میکنه → نسخه‌های مرتبط بررسی بشن (Tailwind v3 vs v4 پلاگین‌های متفاوت دارند)

🛡️ ممنوعیت بازنویسی مخرب:
- ⛔ هرگز فایل موجود را از صفر بازننویس — فقط بخش‌های مربوط به درخواست را تغییر بده
- ⛔ هرگز قابلیت‌های موجود (state, handlers, API calls, UI sections, styles) را حذف نکن — مگر مستقیماً مشکل‌ساز باشند
- ⛔ هرگز عملکرد واقعی (iframe, chart, widget) را با placeholder خالی جایگزین نکن
- ⛔ قبل از create فایل جدید → بررسی کن آیا کامپوننت مشابه در ساختار پروژه وجود داره

🎯 فهم دقیق درخواست: کلمات کاربر را تحت‌اللفظی بخوان. «فقط» = ONLY، «نباید» = ممنوع، «اضافه کن» = بدون حذف موارد موجود. هرگز معنی درخواست را برعکس تفسیر نکن."""

            try:
                # 🆕 اجرای AI با heartbeat برای جلوگیری از QUIC timeout
                # بدون سقف مصنوعی — از ظرفیت واقعی مدل استفاده شود
                safe_max_tokens = model_max_output
                # 🆕 (anti-stuck-loop) — اگر retry است، system prompt را قوی‌تر کن
                # تا مدل اجباراً action_plan تولید کند یا صراحتاً اعلام کند که نمی‌تواند.
                _base_sys = f"تو توسعه‌دهنده ارشد پروژه هستی با دسترسی کامل به تمام فایل‌های پروژه. مهم‌ترین کارت فهمیدن دقیق منظور کاربر است — حتی وقتی مبهم، کوتاه یا غیرمستقیم صحبت می‌کند. تاریخچه مکالمه را بخوان تا context کامل را بفهمی. {'مستقیماً مشکل را پیدا کن، کد اصلاح‌شده بنویس و action_plan معتبر JSON ارائه بده.' if has_code_files else 'فایل‌ها در این دور خوانده نشدند — فقط تحلیل و تشخیص ارائه بده. هرگز action_plan با محتوای حدسی تولید نکن.'} اگر قبلاً راه‌حلی پیشنهاد شده و جواب نداده، رویکرد متفاوتی بگیر. هرگز از کاربر نخواه کار دستی انجام دهد. 🔴 هرگز محتوای فایلی را حدس نزن — فقط بر اساس فایل‌هایی که واقعاً دیده‌ای کد بنویس. ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «دوباره ارسال کنید». ⛔ هرگز فایل موجود را از صفر بازننویس — فقط بخش مربوط به درخواست تغییر کن. قابلیت‌های موجود (state, handlers, UI) حذف نکن. 🔴 فایل‌های بزرگ (>200 خط): حتماً از modify_sections استفاده کن — سیستم بازنویسی‌های مخرب رو خودکار حذف میکنه! تعداد خطوط هر فایل در عنوان نوشته شده. کلمات کاربر را دقیق بخوان: «فقط»=ONLY، «نباید»=ممنوع. با لحن صمیمی و حرفه‌ای پاسخ بده."
                if _is_retry:
                    _retry_addon = (
                        f"\n\n🚨 این RETRY شمارهٔ {request.retry_attempt} است. "
                        "پاسخ قبلی شما action_plan نداشت — کاربر در حلقهٔ بی‌نتیجه گیر کرده. "
                        "این بار **حتماً** یکی از این دو خروجی را تولید کن:\n"
                        "  ✅ یک action_plan JSON معتبر با حداقل ۱ فایل modify/modify_sections که مشکل را حل می‌کند\n"
                        "  ✅ یا اگر واقعاً نمی‌توانی fix را تشخیص دهی، صراحتاً action_plan = "
                        "`{\"files\":[],\"commit_message\":\"cannot_determine_fix:<دلیل>\"}` بزن "
                        "تا کاربر بداند و مدل دیگری امتحان کند.\n"
                        "❌ فقط تحلیل بدون action_plan ممنوع است — این loop را ادامه می‌دهد."
                    )
                    _base_sys += _retry_addon
                gen_task = asyncio.create_task(ai_manager.generate(
                    model_id=primary_model,
                    messages=[
                        Message(role="system", content=_base_sys),
                        Message(role="user", content=action_prompt)
                    ],
                    max_tokens=safe_max_tokens,
                    temperature=0.35
                ))
                # heartbeat هر 5 ثانیه + timeout با مهلت اضافی برای مدل‌هایی با خروجی بزرگ
                total_wait = 0
                # مدل‌هایی مثل gemini-2.5-pro با 65K خروجی نیاز به زمان بیشتری دارند
                initial_wait = 300  # هشدار اولیه در 5 دقیقه
                max_wait = 600  # حداکثر مطلق 10 دقیقه
                warned = False
                timed_out = False
                while not gen_task.done():
                    done_set, _ = await asyncio.wait({gen_task}, timeout=5.0)
                    if not done_set:
                        total_wait += 5
                        if total_wait >= max_wait:
                            gen_task.cancel()
                            yield sse("error", {
                                "message": f"⏱️ مدل {primary_model} بعد از {max_wait} ثانیه پاسخ نداد. لطفاً مدل سریع‌تری انتخاب کنید.",
                                "detail": f"مدل: {primary_model} | timeout: {max_wait}s"
                            })
                            timed_out = True
                            break
                        if total_wait >= initial_wait and not warned:
                            warned = True
                            yield sse("timeout_warning", {
                                "message": f"⏱️ مدل {primary_model} نیاز به زمان بیشتری دارد... مهلت تا {max_wait} ثانیه تمدید شد.",
                                "elapsed": total_wait,
                                "max_wait": max_wait
                            })
                        yield sse("heartbeat", {"message": f"⏳ مدل در حال آماده‌سازی تغییرات... ({total_wait}s)"})
                if timed_out:
                    yield sse("done", {"success": False})
                    return
                response = gen_task.result()

                # 🧹 حذف بلوک‌های استدلال/reasoning + بررسی پاسخ خالی
                content = _strip_reasoning_blocks(response.content) if response.content else ""
                _act_model_used = response.model_id
                _act_tokens = response.tokens_used
                # 🆕 تشخیص truncation
                _act_finish = getattr(response, 'finish_reason', '') or ''
                _act_is_truncated = _act_finish.lower() in ('length', 'max_tokens')

                # 🆕 (chunked editing fix) — Auto-continuation: اگر پاسخ به‌خاطر
                # token limit truncate شد، خودکار از مدل بخواه ادامه دهد و
                # خروجی را merge کن. حداکثر ۳ continuation تا از حلقه بی‌نهایت
                # جلوگیری شود.
                _continuation_count = 0
                _MAX_CONTINUATIONS = 3
                while _act_is_truncated and content and content.strip() and _continuation_count < _MAX_CONTINUATIONS:
                    _continuation_count += 1
                    yield sse("progress", {
                        "step": "truncated_continuation",
                        "message": (
                            f"⏳ پاسخ مدل ناقص بود (truncated). در حال گرفتن "
                            f"ادامه — تلاش {_continuation_count}/{_MAX_CONTINUATIONS}..."
                        ),
                    })
                    # ساخت یک پرامپت continuation با آخرین ۲۰۰۰ کاراکتر تولیدشده
                    # تا مدل بداند کجا قطع شد
                    _last_tail = content[-2000:] if len(content) > 2000 else content
                    _cont_user = (
                        "پاسخ قبلی شما به دلیل token limit ناقص قطع شد. "
                        "از همان جایی که قطع شد ادامه دهید — هیچ توضیح اضافه "
                        "ندهید، تکرار نکنید، فقط ادامه‌ٔ متن قبلی را تولید کنید "
                        "تا action_plan کامل شود.\n\n"
                        f"## ۲۰۰۰ کاراکتر آخر پاسخ شما (محل قطع):\n```\n{_last_tail}\n```\n\n"
                        "ادامه را اینجا بنویس:"
                    )
                    try:
                        _cont_resp = await ai_manager.generate(
                            model_id=primary_model,
                            messages=[
                                Message(role="system", content=(
                                    "تو در حال ادامهٔ یک پاسخ قبلی هستی که به دلیل "
                                    "token limit ناقص قطع شد. فقط ادامه را بنویس "
                                    "— هیچ مقدمه، توضیح، عذرخواهی، یا تکرار از "
                                    "محتوای قبلی نباشد. مستقیم از همان نقطه ادامه بده."
                                )),
                                Message(role="user", content=_cont_user),
                            ],
                            max_tokens=safe_max_tokens,
                            temperature=0.2,
                        )
                        _cont_content = _strip_reasoning_blocks(_cont_resp.content) if _cont_resp.content else ""
                        if _cont_content and _cont_content.strip():
                            content = content + _cont_content
                            _act_tokens = (_act_tokens or 0) + (_cont_resp.tokens_used or 0)
                            _cont_finish = getattr(_cont_resp, 'finish_reason', '') or ''
                            _act_is_truncated = _cont_finish.lower() in ('length', 'max_tokens')
                            yield sse("progress", {
                                "step": "continuation_success",
                                "message": (
                                    f"✅ ادامه دریافت شد ({len(_cont_content):,} کاراکتر). "
                                    f"وضعیت truncate: {'هنوز ناقص' if _act_is_truncated else 'کامل شد ✓'}"
                                ),
                            })
                        else:
                            slog.warning(f"[smart-chat] continuation {_continuation_count} returned empty")
                            break
                    except Exception as _ce:
                        slog.warning(f"[smart-chat] continuation {_continuation_count} failed: {_ce}")
                        break

                if not content or not content.strip():
                    slog.warning(f"[smart-chat] Empty response, model={primary_model}, prompt_len={len(action_prompt)}")
                    _act_sys_msg = f"تو توسعه‌دهنده ارشد پروژه هستی با دسترسی کامل به تمام فایل‌ها. {'مستقیماً مشکل را پیدا کن، کد اصلاح‌شده کامل بنویس و action_plan معتبر JSON ارائه بده.' if has_code_files else 'فایل‌ها در این دور خوانده نشدند — فقط تحلیل ارائه بده.'} ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «دوباره ارسال کنید». ⛔ فایل موجود از صفر بازننویس نکن. قابلیت‌های موجود حذف نکن. کلمات کاربر دقیق بخوان: «فقط»=ONLY. با لحن صمیمی و حرفه‌ای پاسخ بده."
                    _reduced_act = _reduce_prompt_for_retry(action_prompt)
                    _retry_models = [primary_model]
                    _fb = ai_manager.find_fallback_model(primary_model)
                    if _fb and _fb != primary_model:
                        _retry_models.append(_fb)
                    for _ri, _rm in enumerate(_retry_models):
                        _rl = "پرامپت کاهش‌یافته" if _ri == 0 else f"مدل جایگزین ({_rm})"
                        yield sse("progress", {"step": "retry_empty", "message": f"⚠️ پاسخ خالی — تلاش مجدد با {_rl}..."})
                        try:
                            _rr = await ai_manager.generate(
                                model_id=_rm,
                                messages=[Message(role="system", content=_act_sys_msg), Message(role="user", content=_reduced_act)],
                                max_tokens=safe_max_tokens,
                                temperature=0.35,
                            )
                            if _rr.content and _rr.content.strip():
                                content = _rr.content
                                _act_model_used = _rr.model_id
                                _act_tokens = _rr.tokens_used
                                slog.info(f"[smart-chat] ACTION retry succeeded: model={_rm}")
                                yield sse("progress", {"step": "retry_success", "message": f"✅ تلاش مجدد موفق — مدل {_rm} پاسخ داد"})
                                break
                        except Exception as _re:
                            slog.warning(f"[smart-chat] ACTION retry {_ri+1} failed: {_re}")
                    if not content or not content.strip():
                        yield sse("error", {
                            "message": f"❌ مدل {primary_model} پاسخ خالی برگرداند (حتی بعد از تلاش مجدد) | حجم: ~{len(action_prompt)} کاراکتر",
                            "detail": f"مدل: {primary_model} | حجم: ~{len(action_prompt)} | context: {model_context_window}"
                        })
                # --- مرحله دو مرحله‌ای: اگر AI فایل‌هایی رو لازم داشت که نخونده ---
                if content and content.strip() and has_code_files and not use_batch_processing:
                    _missing_markers = [
                        "نداریم", "ارائه نشده", "در دسترس نیست",
                        "نداشتیم", "ندیدیم", "فرضی", "فرض می‌کنیم",
                        "فرض می‌کنم", "فرض کنیم", "این فایل را نداریم",
                        "کد مدل را نداریم", "not provided", "not available",
                        "couldn't read", "we don't have", "we assume",
                        "از کدهای بالا نیست", "در کدهای بالا نیست",
                        "محتوای این فایل", "دسترسی به این فایل"
                    ]
                    _needs_2nd_pass = any(m in content for m in _missing_markers)

                    if _needs_2nd_pass:
                        yield sse("progress", {
                            "step": "second_pass",
                            "message": "🔄 مدل فایل‌های بیشتری نیاز دارد. شناسایی و خواندن فایل‌های ناخوانده..."
                        })
                        try:
                            _missing_req = await ai_manager.generate(
                                model_id=primary_model,
                                messages=[
                                    Message(role="system", content="فقط مسیر فایل‌هایی را بنویسید که برای تکمیل تحلیل و نوشتن action_plan نیاز دارید. هر مسیر در یک خط. حداکثر ۱۰ فایل."),
                                    Message(role="user", content=f"پاسخ شما:\n{content[:3000]}\n\nفایل‌هایی که خوانده شدند:\n{chr(10).join(selected)}\n\nتمام فایل‌های پروژه:\n{chr(10).join(code_files[:500])}\n\nکدام فایل‌ها را نخوانده‌اید و لازم دارید؟ فقط مسیر بنویسید.")
                                ],
                                max_tokens=400,
                                temperature=0.1
                            )

                            _extra_files = []
                            for _line in _missing_req.content.strip().split("\n"):
                                _line = _line.strip().strip("`- ").strip()
                                if _line and _line in code_files and _line not in selected:
                                    _extra_files.append(_line)

                            # همچنین فایل‌هایی که خود پاسخ AI بهشون اشاره کرده رو هم استخراج کن
                            _resp_extracted = _extract_file_paths_from_text(content, code_files)
                            for _rp in _resp_extracted:
                                if _rp not in selected and _rp not in _extra_files:
                                    _extra_files.append(_rp)

                            if _extra_files:
                                _extra_contents = {}
                                for _fp in _extra_files[:10]:
                                    yield sse("progress", {
                                        "step": "reading_extra",
                                        "message": f"📖 خواندن فایل اضافی: {_fp}...",
                                        "file": _fp
                                    })
                                    try:
                                        _res = await github_svc.get_file_content(owner, repo, _fp, token=token)
                                        if _res.get("success"):
                                            _fc = _res.get("content", "")
                                            file_contents[_fp] = _fc  # ذخیره اصلی برای تشخیص بازنویسی مخرب
                                            if len(_fc) > 15000:
                                                _fc = _fc[:15000] + "\n... [truncated]"
                                            _extra_contents[_fp] = _fc
                                    except Exception:
                                        pass
                                    await asyncio.sleep(0.2)

                                if _extra_contents:
                                    _extra_ctx = ""
                                    for _path, _cnt in _extra_contents.items():
                                        _extra_ctx += f"\n\n=== {_path} ===\n{_cnt}"

                                    yield sse("progress", {
                                        "step": "reanalysis",
                                        "message": f"🔬 تحلیل مجدد با {len(_extra_contents)} فایل اضافی...",
                                        "model": primary_model
                                    })

                                    _reanalysis = await ai_manager.generate(
                                        model_id=primary_model,
                                        messages=[
                                            Message(role="system", content=f"تو توسعه‌دهنده ارشد پروژه {owner}/{repo} هستی. فایل‌های جدیدی که درخواست کرده بودی حالا در دسترس هستند. پاسخ قبلی‌ات رو با اطلاعات واقعی فایل‌ها بازنویسی کن. هرگز حدس نزن — فقط بر اساس کد واقعی تحلیل و action_plan بنویس."),
                                            Message(role="user", content=f"تحلیل قبلی شما:\n{content[:4000]}\n\nفایل‌های جدید:\n{_extra_ctx}\n\nلطفاً تحلیل و action_plan خود را با اطلاعات واقعی فایل‌ها بازنویسی کنید. فرمت قبلی (action_plan با JSON) را حفظ کنید. هرگز محتوای حدسی ننویسید.")
                                        ],
                                        max_tokens=safe_max_tokens,
                                        temperature=0.3
                                    )
                                    if _reanalysis.content and _reanalysis.content.strip():
                                        content = _reanalysis.content
                                        _act_model_used = _reanalysis.model_id
                                        _act_tokens = _reanalysis.tokens_used
                                        yield sse("progress", {
                                            "step": "reanalysis_done",
                                            "message": f"✅ تحلیل مجدد با {len(_extra_contents)} فایل واقعی انجام شد — حدس‌ها حذف شد"
                                        })
                        except Exception as _2pe:
                            slog.warning(f"[smart-chat] Second-pass failed: {_2pe}")

                if content and content.strip():
                    # 🆕 استخراج و ادغام تمام بلوک‌های JSON (پشتیبانی از بلوک‌های متعدد + تعمیر ناقص)
                    action_plan = _extract_all_action_plans_from_response(content, is_truncated=_act_is_truncated)

                    # 🆕 (force-action-plan) — اگر مدل تحلیل نوشت ولی هیچ
                    # action_plan تولید نکرد و پاسخ truncate هم نشده (یعنی مدل
                    # طبیعی ایستاد، نه به‌خاطر token limit) → یک ادامهٔ هدفمند
                    # بزن که فقط JSON action_plan را بخواهد. این همان loopِ
                    # بی‌نتیجه‌ای را می‌شکند که مدل ضعیف بعد از تحلیل می‌ایستد و
                    # هرگز به action_plan نمی‌رسد (و retry فقط همان را تکرار می‌کند).
                    if (
                        action_plan is None
                        and has_code_files
                        and not _act_is_truncated
                        and len(content.strip()) > 200
                        and not use_batch_processing
                    ):
                        yield sse("progress", {
                            "step": "force_action_plan",
                            "message": "📝 تحلیل نوشته شد ولی action_plan تولید نشد — درخواست تولید فقط action_plan...",
                        })
                        try:
                            _force_resp = await ai_manager.generate(
                                model_id=primary_model,
                                messages=[
                                    Message(role="system", content=(
                                        "تو در حال تکمیل یک پاسخ هستی. تحلیل قبلاً نوشته شده. "
                                        "حالا فقط و فقط action_plan را به‌صورت JSON معتبر در یک "
                                        "بلوک ```json تولید کن — هیچ توضیح، تحلیل، مقدمه یا متن "
                                        "اضافه ننویس. بر اساس تحلیلی که ارائه شد، فایل‌هایی که "
                                        "باید تغییر کنند را بنویس: operation=modify با content "
                                        "کامل (فایل <۲۰۰ خط) یا modify_sections با find/replace "
                                        "دقیق (فایل بزرگ). فقط فایل‌هایی که محتوایشان را دیده‌ای. "
                                        "اگر واقعاً نمی‌توانی fix را تشخیص دهی، صراحتاً "
                                        "{\"files\":[],\"commit_message\":\"cannot_determine_fix:<دلیل کوتاه>\"} "
                                        "بزن — هرگز بدون action_plan متوقف نشو."
                                    )),
                                    Message(role="user", content=(
                                        f"تحلیلی که نوشتی:\n{content[-4000:]}\n\n"
                                        "حالا فقط action_plan JSON را تولید کن (بدون هیچ متن دیگر):"
                                    )),
                                ],
                                max_tokens=safe_max_tokens,
                                temperature=0.2,
                            )
                            _force_content = _strip_reasoning_blocks(_force_resp.content) if _force_resp.content else ""
                            if _force_content and _force_content.strip():
                                content = content + "\n\n" + _force_content
                                _act_tokens = (_act_tokens or 0) + (_force_resp.tokens_used or 0)
                                action_plan = _extract_all_action_plans_from_response(content, is_truncated=False)
                                yield sse("progress", {
                                    "step": "force_action_plan_done",
                                    "message": ("✅ action_plan تولید شد" if action_plan else "⚠️ مدل نتوانست action_plan بدهد — fix قطعی تشخیص داده نشد"),
                                })
                        except Exception as _fe:
                            slog.warning(f"[smart-chat] force-action-plan failed: {_fe}")

                    # لایه ۲: اگر فایل‌ها خوانده نشدن، action_plan حذف شود (جلوگیری از محتوای ساختگی)
                    # 🆕 (clarify-first) — ask_user/route_to استثنا
                    _act_is_clarify = bool(action_plan and (action_plan.get("ask_user") or action_plan.get("route_to")))
                    if not has_code_files and action_plan is not None and not _act_is_clarify:
                        slog.warning(f"[smart-chat ACTION] AI generated action_plan without reading files — stripped. Files in plan: {[f.get('path') for f in (action_plan.get('files') or [])]}")
                        action_plan = None

                    # لایه ۳: فایل‌هایی که واقعاً خوانده نشدن ولی AI محتوا حدس زده — حذف
                    if action_plan and not _act_is_clarify and has_code_files and selected:
                        _read_set = set(selected)
                        _plan_files = action_plan.get("files", [])
                        _verified = [f for f in _plan_files if f.get("path") in _read_set or f.get("operation") == "create"]
                        _guessed = [f for f in _plan_files if f not in _verified]
                        if _guessed:
                            slog.warning(f"[smart-chat ACTION] Stripped {len(_guessed)} guessed files from action_plan: {[f.get('path') for f in _guessed]}")
                            if _verified:
                                action_plan["files"] = _verified
                            else:
                                action_plan = None

                    # 🆕 هشدار truncation به کاربر
                    if _act_is_truncated:
                        _trunc_msg = ""
                        if action_plan:
                            _trunc_msg = f"\n\n---\n⚠️ **هشدار:** پاسخ مدل ناقص بود — {len(action_plan.get('files', []))} فایل از action_plan نجات یافت."
                        else:
                            _trunc_msg = "\n\n---\n⚠️ **هشدار:** پاسخ مدل به دلیل محدودیت خروجی ناقص قطع شد. لطفاً با مدل دیگری تلاش کنید."
                        content += _trunc_msg

                    yield sse("response", {
                        "type": "action",
                        "content": content,
                        "model_used": _act_model_used,
                        "tokens_used": _act_tokens,
                        "has_action": action_plan is not None,
                        "action_plan": _validate_action_plan_syntax(action_plan, original_files=file_contents, repo_file_paths=_normalize_repo_paths(locals().get("all_files")), user_message=request.message, backend_logs=request.backend_logs, code_files=locals().get("code_files")) if action_plan else None,
                        "files_were_read": has_code_files,
                        "selected_file_paths": selected if has_code_files else [],
                        "truncated": _act_is_truncated,
                    })

            except asyncio.CancelledError:
                slog.error(f"[smart-chat] CancelledError model={primary_model}")
                yield sse("error", {
                    "message": f"❌ عملیات مدل {primary_model} لغو شد. لطفاً دوباره تلاش کنید.",
                    "detail": f"مدل: {primary_model} | CancelledError"
                })
            except Exception as e:
                err_detail = str(e)[:200]
                tb_str = traceback.format_exc()[-500:]
                slog.error(f"[smart-chat] model={primary_model} prompt_len={len(action_prompt)} error={err_detail}")
                slog.error(f"[smart-chat] traceback: {tb_str}")
                yield sse("error", {
                    "message": f"❌ خطا در تحلیل عمیق مدل {primary_model}: {err_detail}",
                    "detail": f"مدل: {primary_model} | حجم پرامپت: ~{len(action_prompt)} کاراکتر | context window: {model_context_window} توکن"
                })

        # اعلان پایان استفاده از فیلدها (فیلدهای prompt از طریق دکمه «ارسال به چت» ارسال می‌شوند)

        yield sse("done", {"success": True})

    # 🆕 wrapper برای گرفتن خطاهای ناشناخته generator
    async def safe_event_stream():
        try:
            async for chunk in event_stream():
                yield chunk
        except BaseException as e:
            # 🐛 (C7v2 Section 8) — traceback کامل log شود برای رفع debug
            # مشکلات multi-step (مثل NameError قبلی). قبلاً فقط آخرین ۵۰۰
            # کاراکتر می‌رفت که اغلب کافی نبود.
            _full_tb = traceback.format_exc()
            slog.error(f"[smart-chat] FATAL error in event_stream: {type(e).__name__}: {str(e)[:300]}")
            slog.error(f"[smart-chat] FATAL traceback (full):\n{_full_tb}")
            try:
                yield f"event: error\ndata: {json.dumps({'message': f'❌ خطای غیرمنتظره ({type(e).__name__}): {str(e)[:150]}'}, ensure_ascii=False)}\n\n"
                yield f"event: done\ndata: {json.dumps({'success': False})}\n\n"
            except GeneratorExit:
                pass
        finally:
            # 🔴 (anti-parallel) — قفل را همیشه آزاد کن، حتی روی exception یا
            # cancellation. بدون این، session تا timeout قفل می‌ماند.
            try:
                _SMART_CHAT_ACTIVE.pop(_pid_key, None)
            except Exception:
                pass

    return StreamingResponse(
        safe_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# 🆕 (v3 render-ops) — helper برای اجرای render_actions
async def _execute_render_actions(render_actions: List[dict]) -> Dict[str, Any]:
    """اجرای دستورات مدیریتی Render (set_env_var, restart, trigger_deploy).

    Returns: {success: bool, results: [...], errors: [...]}
    """
    if not render_actions:
        return {"success": True, "results": [], "errors": []}
    try:
        from ...services.render_service import get_render_service
        from ...services.oversight_service import get_render_token
    except Exception as e:
        return {"success": False, "results": [], "errors": [f"render_service import failed: {e}"]}

    if not get_render_token():
        return {
            "success": False,
            "results": [],
            "errors": ["RENDER_API_KEY در تنظیمات یافت نشد. لطفاً در settings تنظیم کنید."],
        }

    rs = get_render_service()
    # ابتدا list services بگیر برای lookup name → service_id
    services_resp = await rs.get_services()
    services = services_resp.get("services", []) if services_resp.get("success") else []
    name_to_id = {s.get("name", "").lower(): s.get("id") for s in services if s.get("id")}

    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for action in render_actions:
        if not isinstance(action, dict):
            continue
        atype = action.get("type", "").strip().lower()
        service_name = (action.get("service_name") or "").strip().lower()
        service_id = name_to_id.get(service_name)
        if not service_id:
            # تلاش برای fuzzy match (substring)
            for nm, sid in name_to_id.items():
                if service_name in nm or nm in service_name:
                    service_id = sid
                    break
        if not service_id:
            errors.append(
                f"سرویس '{service_name}' در Render پیدا نشد. "
                f"سرویس‌های موجود: {list(name_to_id.keys())[:5]}"
            )
            results.append({"action": atype, "service_name": service_name, "success": False, "error": "service_not_found"})
            continue

        try:
            if atype == "set_env_var":
                key = action.get("key", "")
                value = action.get("value", "")
                if not key:
                    errors.append(f"set_env_var: key خالی است")
                    continue
                r = await rs.set_env_var(service_id, key, str(value))
                results.append({"action": "set_env_var", "service": service_name, "key": key, **r})
                if not r.get("success"):
                    errors.append(f"set_env_var {key}: {r.get('error')}")
            elif atype == "set_env_vars_bulk":
                vars_dict = action.get("vars", {}) or {}
                if not vars_dict:
                    errors.append(f"set_env_vars_bulk: vars خالی است")
                    continue
                r = await rs.set_env_vars_bulk(service_id, vars_dict)
                results.append({"action": "set_env_vars_bulk", "service": service_name, **r})
            elif atype == "restart_service":
                r = await rs.restart_service(service_id)
                results.append({"action": "restart_service", "service": service_name, **r})
            elif atype == "trigger_deploy":
                clear_cache = bool(action.get("clear_cache", False))
                r = await rs.trigger_deploy(service_id, clear_cache=clear_cache)
                results.append({"action": "trigger_deploy", "service": service_name, **r})
            else:
                errors.append(f"action type ناشناخته: {atype}")
                results.append({"action": atype, "success": False, "error": "unknown_action_type"})
        except Exception as e:
            errors.append(f"{atype} failed: {str(e)[:200]}")
            results.append({"action": atype, "success": False, "error": str(e)[:300]})

    overall_success = all(r.get("success", False) for r in results) if results else False
    return {"success": overall_success, "results": results, "errors": errors}


@router.post("/inspector/apply-action")
async def apply_action(request: ApplyActionRequest, db: Session = Depends(get_db)):
    """
    اعمال تغییرات پیشنهادی: ساخت branch، commit و PR
    SSE streaming برای گزارش لحظه‌ای
    """
    from fastapi.responses import StreamingResponse
    from ...models.project import Project
    from ...services.github_pr_service import get_github_pr_service

    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    if not owner or not repo:
        return {"success": False, "error": "اطلاعات GitHub پروژه یافت نشد"}

    # 🆕 (review-gate) — اگر کلاینت critical_signals می‌فرسته ولی
    # review_acknowledged=False، apply رو رد می‌کنیم تا کاربر صراحتاً
    # هشدارها رو ببینه. این جلوی commit شدن plan با bug شناخته‌شده رو می‌گیره
    # (همان چیزی که در transcript کاربر ۲۳ فایل با ۴-۵ critical issue اتفاق افتاد).
    _crit_signals = (request.review_critical_signals or [])
    if _crit_signals and not request.review_acknowledged:
        return {
            "success": False,
            "code": "review_acknowledgement_required",
            "error": (
                f"بازبینی این طرح {len(_crit_signals)} مشکل critical پیدا کرد: "
                f"{', '.join(_crit_signals[:5])}. قبل از apply باید "
                "review_acknowledged=true بفرستی (یعنی کاربر هشدارها رو دیده)."
            ),
            "critical_signals": _crit_signals,
        }

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from ...models.setting import Setting
        token = Setting.get_value(db, "api_key_github") or ""
    if not token:
        return {"success": False, "error": "توکن GitHub تنظیم نشده است. لطفاً در تنظیمات وارد کنید."}

    async def event_stream():
        pr_svc = get_github_pr_service()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        # --- ساخت branch ---
        branch_name = f"inspector/smart-fix-{int(datetime.now().timestamp())}"
        yield sse("progress", {
            "step": "creating_branch",
            "message": f"🌿 در حال ساخت branch: {branch_name}..."
        })

        try:
            branch_result = await pr_svc.create_branch(
                owner=owner,
                repo=repo,
                new_branch=branch_name,
                token=token
            )
            if not branch_result.get("success"):
                yield sse("error", {"message": f"خطا در ساخت branch: {branch_result.get('error', 'unknown')}"})
                yield sse("done", {"success": False})
                return

            yield sse("progress", {
                "step": "branch_created",
                "message": f"✅ Branch ساخته شد: {branch_name}"
            })
        except Exception as e:
            yield sse("error", {"message": f"خطا: {str(e)[:80]}"})
            yield sse("done", {"success": False})
            return

        # --- اعتبارسنجی فایل‌ها قبل از commit ---
        validated_files = []
        for f in request.action_files:
            file_path = f.get("path", "").strip()
            file_content = f.get("content", "")
            file_operation = f.get("operation", "").lower()
            file_sections = f.get("sections")
            # modify_sections فقط sections داره (نه content) — نباید فیلتر بشه
            has_payload = bool(file_content) or (file_operation == "modify_sections" and file_sections)
            if not file_path or not has_payload:
                continue
            # بررسی path traversal و مسیرهای خطرناک
            if ".." in file_path or file_path.startswith("/") or file_path.startswith("\\"):
                yield sse("progress", {
                    "step": "validation_error",
                    "message": f"🚫 مسیر نامعتبر رد شد: {file_path}"
                })
                continue
            # بررسی مسیرهای حساس
            dangerous_paths = [".github/workflows/", ".github/actions/", ".env", "secrets", ".ssh/"]
            if any(d in file_path.lower() for d in dangerous_paths):
                yield sse("progress", {
                    "step": "validation_error",
                    "message": f"🚫 مسیر حساس رد شد: {file_path}"
                })
                continue
            validated_files.append(f)

        if not validated_files:
            yield sse("error", {"message": "هیچ فایل معتبری برای commit وجود ندارد"})
            yield sse("done", {"success": False})
            return

        # بررسی وجود فایل‌ها در ریپو (جلوگیری از ساخت فایل‌های ساختگی)
        from ...services.github_import import get_github_import_service
        github_svc = get_github_import_service()
        yield sse("progress", {
            "step": "validating_files",
            "message": f"🔍 بررسی وجود {len(validated_files)} فایل در ریپو..."
        })
        final_files = []
        dropped_files = []  # فایل‌هایی که اعمال نشدن — برای گزارش به کاربر
        for f in validated_files:
            file_path = f.get("path", "").strip()
            operation = f.get("operation", "modify")
            if operation == "create":
                # فایل‌های جدید مجازند — ولی باید پاکسازی + سینتکس‌شون سالم باشه
                _create_content = f.get("content", "")
                if _create_content:
                    # 🛡️ پاکسازی محتوا از آلودگی reasoning/markdown (لایه ایمنی)
                    from ...services.content_sanitizer import sanitize_file_content as _cs_sanitize, detect_reasoning_contamination as _cs_detect
                    _create_content = _cs_sanitize(_create_content, file_path)
                    f["content"] = _create_content
                    # 🛡️ بررسی آلودگی بعد از پاکسازی
                    _contamination = _cs_detect(_create_content, file_path)
                    if _contamination:
                        yield sse("progress", {
                            "step": "contamination_blocked",
                            "message": f"🛡️ فایل جدید {file_path}: محتوای آلوده بلاک شد: {_contamination[:100]}"
                        })
                        dropped_files.append({"path": file_path, "reason": f"آلودگی reasoning: {_contamination[:120]}"})
                        slog.error(f"[apply-action] BLOCKED reasoning contamination in new file {file_path}: {_contamination}")
                        continue
                    _syntax_check = _validate_file_content_syntax(_create_content, file_path)
                    if not _syntax_check["valid"]:
                        _errs = "; ".join(_syntax_check["errors"][:3])
                        yield sse("progress", {
                            "step": "syntax_error_create",
                            "message": f"⚠️ {file_path}: خطای سینتکس در فایل جدید — شروع تصحیح خودکار... — {_errs}"
                        })
                        # 🔧 تلاش برای تصحیح خودکار خطای سینتکس در فایل جدید با AI
                        _create_fixed = False
                        try:
                            from ...services.ai_manager import get_ai_manager as _cfx_get_aim
                            from ...services.ai_base import Message as _CfxMsg
                            _cfx_aim = _cfx_get_aim()
                            _cfx_preview = _create_content[:5000]
                            _cfx_prompt = f"""فایل جدید زیر خطای سینتکس دارد. لطفاً فقط خطاهای سینتکس را رفع کن.

خطاها: {_errs}

فایل ({file_path}):
```
{_cfx_preview}
```

⚠️ فقط خطاهای سینتکس رو رفع کن — تغییر منطقی ایجاد نکن.
⚠️ فایل کامل رو برگردون — فقط کد خالص بدون markdown."""
                            _cfx_model = request.model_ids[0] if request.model_ids else "gemini-2.0-flash"
                            _cfx_resp = await _cfx_aim.generate(
                                model_id=_cfx_model,
                                messages=[
                                    _CfxMsg(role="system", content="تو ابزار تصحیح سینتکس هستی. فقط خطاهای سینتکس رو رفع کن. کد کامل فایل رو بدون markdown برگردون."),
                                    _CfxMsg(role="user", content=_cfx_prompt)
                                ],
                                max_tokens=8000,
                                temperature=0.1,
                            )
                            _cfx_result = _cfx_resp.content.strip()
                            import re as _cfx_re
                            _cfx_code_match = _cfx_re.search(r'```(?:tsx?|jsx?|py|json|css|html)?\s*\n(.*?)\n```', _cfx_result, _cfx_re.DOTALL)
                            if _cfx_code_match:
                                _cfx_result = _cfx_code_match.group(1).strip()
                            if _cfx_result and len(_cfx_result) > 50:
                                _cfx_check = _validate_file_content_syntax(_cfx_result, file_path)
                                if _cfx_check["valid"]:
                                    f["content"] = _cfx_result
                                    _create_fixed = True
                                    yield sse("progress", {
                                        "step": "syntax_fix_create_success",
                                        "message": f"✅ {file_path}: تصحیح خودکار AI موفق — خطای سینتکس فایل جدید رفع شد"
                                    })
                                    slog.info(f"[apply-action] AI syntax fix success for new file {file_path}")
                        except Exception as _cfx_err:
                            slog.warning(f"[apply-action] AI syntax fix failed for new file {file_path}: {_cfx_err}")
                        if not _create_fixed:
                            yield sse("progress", {
                                "step": "syntax_error_rejected",
                                "message": f"🚫 {file_path}: خطای سینتکس در فایل جدید (تصحیح خودکار هم ناموفق بود) — {_errs}"
                            })
                            dropped_files.append({"path": file_path, "reason": f"خطای سینتکس: {_errs[:120]}"})
                            slog.error(f"[apply-action] REJECTED create {file_path}: syntax errors: {_errs}")
                            continue
                    elif _syntax_check["warnings"]:
                        _warns = "; ".join(_syntax_check["warnings"][:3])
                        yield sse("progress", {
                            "step": "syntax_warning_info",
                            "message": f"⚠️ {file_path}: هشدار سینتکس (فایل commit میشه ولی چک کنید) — {_warns}"
                        })
                        slog.warning(f"[apply-action] WARNING (not rejected) create {file_path}: syntax warnings: {_warns}")
                        # هشدارها دیگه فایل رو بلاک نمیکنن — ادامه بده
                final_files.append(f)
                continue
            try:
                existing = await github_svc.get_file_content(owner, repo, file_path, token=token)
                if existing.get("success"):
                    # ── modify_sections: اعمال تغییرات بخشی روی فایل اصلی ──
                    if operation == "modify_sections" and f.get("sections"):
                        original_content = existing.get("content", "")
                        if not original_content:
                            yield sse("progress", {
                                "step": "file_empty",
                                "message": f"⚠️ {file_path}: فایل اصلی خالی است — modify_sections ممکن نیست"
                            })
                            dropped_files.append({"path": file_path, "reason": "فایل اصلی خالی"})
                            continue
                        merge_result = _apply_section_modifications(original_content, f["sections"])
                        if merge_result["applied"] > 0:
                            f["content"] = merge_result["content"]
                            f["_sections_applied"] = merge_result["applied"]
                            f["_sections_total"] = merge_result["total"]
                            msg_parts = [f"🔧 {file_path}: {merge_result['applied']}/{merge_result['total']} بخش اعمال شد"]
                            if merge_result["errors"]:
                                msg_parts.append(f" (⚠️ {len(merge_result['errors'])} خطا: {merge_result['errors'][0][:60]})")
                            yield sse("progress", {
                                "step": "sections_applied",
                                "message": "".join(msg_parts)
                            })
                            # 🛡️ بررسی آلودگی reasoning بعد از merge (لایه ایمنی)
                            from ...services.content_sanitizer import detect_reasoning_contamination as _cs_detect_ms
                            _merge_contamination = _cs_detect_ms(f["content"], file_path)
                            if _merge_contamination:
                                yield sse("progress", {
                                    "step": "contamination_blocked_after_merge",
                                    "message": f"🛡️ {file_path}: محتوای merge شده آلوده به reasoning — بلاک شد: {_merge_contamination[:100]}"
                                })
                                dropped_files.append({"path": file_path, "reason": f"آلودگی reasoning بعد از merge: {_merge_contamination[:120]}"})
                                slog.error(f"[apply-action] BLOCKED reasoning contamination after merge in {file_path}: {_merge_contamination}")
                                continue
                            # ── اعتبارسنجی سینتکس محتوای merge شده قبل از commit ──
                            _syntax_check = _validate_file_content_syntax(f["content"], file_path)
                            if not _syntax_check["valid"]:
                                _errs = "; ".join(_syntax_check["errors"][:3])
                                yield sse("progress", {
                                    "step": "syntax_error_after_merge",
                                    "message": f"⚠️ {file_path}: خطای سینتکس بعد از merge — شروع بازیابی خودکار... — {_errs}"
                                })
                                slog.warning(f"[apply-action] Syntax errors after merge in {file_path}: {_errs} — attempting recovery...")

                                # ── 🔧 مرحله بازیابی ۱: اعمال تدریجی sections (تک‌تک) ──
                                _recovery_success = False
                                _sections_list = f.get("sections", [])
                                if len(_sections_list) > 1:
                                    yield sse("progress", {
                                        "step": "syntax_recovery_incremental",
                                        "message": f"🔄 {file_path}: تلاش بازیابی — اعمال تدریجی {len(_sections_list)} بخش..."
                                    })
                                    _incr_content = original_content
                                    _incr_applied = 0
                                    _incr_skipped = []
                                    for _si, _sec in enumerate(_sections_list):
                                        _single_merge = _apply_section_modifications(_incr_content, [_sec])
                                        if _single_merge["applied"] > 0:
                                            _single_check = _validate_file_content_syntax(_single_merge["content"], file_path)
                                            if _single_check["valid"]:
                                                _incr_content = _single_merge["content"]
                                                _incr_applied += 1
                                            else:
                                                _incr_skipped.append(_si)
                                                slog.info(f"[apply-action] incremental recovery: section[{_si}] breaks syntax, skipping")
                                        else:
                                            _incr_skipped.append(_si)
                                    if _incr_applied > 0:
                                        _incr_final_check = _validate_file_content_syntax(_incr_content, file_path)
                                        if _incr_final_check["valid"]:
                                            f["content"] = _incr_content
                                            f["_sections_applied"] = _incr_applied
                                            f["_recovery_method"] = "incremental"
                                            _recovery_success = True
                                            yield sse("progress", {
                                                "step": "syntax_recovery_incremental_success",
                                                "message": f"✅ {file_path}: بازیابی تدریجی موفق — {_incr_applied}/{len(_sections_list)} بخش اعمال شد"
                                                    + (f" (⚠️ {len(_incr_skipped)} بخش به خاطر خطای سینتکس رد شد)" if _incr_skipped else "")
                                            })
                                            slog.info(f"[apply-action] RECOVERY incremental success for {file_path}: {_incr_applied}/{len(_sections_list)} sections, skipped {_incr_skipped}")

                                # ── 🔧 مرحله بازیابی ۲: تصحیح خودکار با AI ──
                                if not _recovery_success:
                                    try:
                                        from ...services.ai_manager import get_ai_manager as _sfx_get_aim
                                        from ...services.ai_base import Message as _SfxMsg
                                        _sfx_aim = _sfx_get_aim()
                                        _sfx_merged_preview = f["content"][:5000]
                                        if len(f["content"]) > 5000:
                                            _sfx_merged_preview += f"\n... [ادامه فایل — مجموعاً {len(f['content'].split(chr(10)))} خط]"
                                        _sfx_prompt = f"""فایل زیر بعد از merge تغییرات، خطای سینتکس دارد. لطفاً فقط خطاهای سینتکس را رفع کن و کد اصلاح‌شده را برگردان.

خطاهای شناسایی‌شده: {_errs}

محتوای فایل ({file_path}):
```
{_sfx_merged_preview}
```

⚠️ فقط خطاهای سینتکس رو رفع کن — هیچ تغییر منطقی یا عملکردی ایجاد نکن.
⚠️ فایل کامل رو برگردون (نه فقط بخش تغییریافته).
⚠️ هیچ توضیح یا markdown ننویس — فقط کد خالص."""

                                        yield sse("progress", {
                                            "step": "syntax_recovery_ai",
                                            "message": f"🤖 {file_path}: تلاش تصحیح خودکار خطای سینتکس با AI..."
                                        })
                                        _sfx_model = request.model_ids[0] if request.model_ids else "gemini-2.0-flash"
                                        _sfx_resp = await _sfx_aim.generate(
                                            model_id=_sfx_model,
                                            messages=[
                                                _SfxMsg(role="system", content="تو ابزار تصحیح سینتکس هستی. فقط خطاهای سینتکس رو رفع کن. کد کامل فایل رو بدون markdown و توضیح برگردون."),
                                                _SfxMsg(role="user", content=_sfx_prompt)
                                            ],
                                            max_tokens=8000,
                                            temperature=0.1,
                                        )
                                        _sfx_fixed = _sfx_resp.content.strip()
                                        # حذف احتمالی markdown code fences
                                        import re as _sfx_re
                                        _sfx_code_match = _sfx_re.search(r'```(?:tsx?|jsx?|py|json|css|html)?\s*\n(.*?)\n```', _sfx_fixed, _sfx_re.DOTALL)
                                        if _sfx_code_match:
                                            _sfx_fixed = _sfx_code_match.group(1).strip()
                                        if _sfx_fixed and len(_sfx_fixed) > 50:
                                            _sfx_check = _validate_file_content_syntax(_sfx_fixed, file_path)
                                            if _sfx_check["valid"]:
                                                f["content"] = _sfx_fixed
                                                f["_recovery_method"] = "ai_syntax_fix"
                                                _recovery_success = True
                                                yield sse("progress", {
                                                    "step": "syntax_recovery_ai_success",
                                                    "message": f"✅ {file_path}: تصحیح خودکار AI موفق — خطای سینتکس رفع شد"
                                                })
                                                slog.info(f"[apply-action] RECOVERY AI syntax fix success for {file_path}")
                                            else:
                                                _sfx_new_errs = "; ".join(_sfx_check["errors"][:2])
                                                yield sse("progress", {
                                                    "step": "syntax_recovery_ai_failed",
                                                    "message": f"⚠️ {file_path}: تصحیح AI هم خطای سینتکس داره: {_sfx_new_errs}"
                                                })
                                                slog.warning(f"[apply-action] AI syntax fix still has errors for {file_path}: {_sfx_new_errs}")
                                    except Exception as _sfx_err:
                                        slog.warning(f"[apply-action] AI syntax fix failed for {file_path}: {_sfx_err}")

                                # اگر هیچ بازیابی موفق نبود → حذف فایل
                                if not _recovery_success:
                                    yield sse("progress", {
                                        "step": "syntax_error_final_drop",
                                        "message": f"🚫 {file_path}: تمام تلاش‌های بازیابی شکست خوردند — فایل commit نمیشه — {_errs}"
                                    })
                                    dropped_files.append({"path": file_path, "reason": f"خطای سینتکس بعد از merge (بازیابی ناموفق): {_errs[:120]}"})
                                    slog.error(f"[apply-action] REJECTED merged {file_path} after all recovery attempts: {_errs}")
                                    continue
                            elif _syntax_check["warnings"]:
                                _warns = "; ".join(_syntax_check["warnings"][:3])
                                yield sse("progress", {
                                    "step": "syntax_warning_info_after_merge",
                                    "message": f"⚠️ {file_path}: هشدار سینتکس بعد از merge (فایل commit میشه ولی چک کنید) — {_warns}"
                                })
                                slog.warning(f"[apply-action] WARNING (not rejected) merged {file_path}: syntax warnings: {_warns}")
                                # هشدارها دیگه فایل رو بلاک نمیکنن — فقط خطاهای بحرانی
                            final_files.append(f)
                        else:
                            _errs = "; ".join(str(e)[:80] for e in merge_result['errors'][:3])
                            yield sse("progress", {
                                "step": "sections_failed",
                                "message": f"🚫 {file_path}: هیچ بخشی اعمال نشد — {_errs}"
                            })
                            # نمایش نمونه محتوای واقعی فایل برای دیباگ — چرا find مطابقت نداشت؟
                            _orig_lines = original_content.split("\n")
                            _total_lines = len(_orig_lines)
                            if _total_lines > 30:
                                _preview = "\n".join(_orig_lines[:10]) + f"\n... ({_total_lines - 20} خط میانی) ...\n" + "\n".join(_orig_lines[-10:])
                            else:
                                _preview = original_content[:1500]
                            yield sse("progress", {
                                "step": "sections_failed_preview",
                                "message": f"📄 {file_path} ({_total_lines} خط) — نمونه محتوای واقعی:\n{_preview[:1500]}"
                            })
                            # ── Fallback: اگر تمام sections شکست خورد، بررسی آیا replace ها بتنهایی فایل معتبری میسازن ──
                            # مورد خاص: وقتی find = محتوای آلوده (reasoning) و replace = کد تمیز
                            # سعی کن محتوای آلوده رو شناسایی و حذف کن
                            _fallback_applied = False
                            if len(f["sections"]) == 1 and f["sections"][0].get("replace", "").strip():
                                _section = f["sections"][0]
                                _replace_content = _section["replace"].strip()
                                # آیا replace محتوای کد معتبر هست؟ (شامل import/export/function)
                                _code_markers = ["import ", "export ", "function ", "const ", "class ", "def ", "from ", "return "]
                                _is_code = any(m in _replace_content[:200] for m in _code_markers)
                                # آیا فایل اصلی آلوده به reasoning هست؟
                                _contamination = _detect_reasoning_contamination(original_content, file_path)
                                _starts_with_non_code = original_content.strip().startswith("**") or original_content.strip().startswith("##") or original_content.strip().startswith("```")
                                if _is_code and (_contamination or _starts_with_non_code):
                                    # Fallback: replace محتوای کامل فایل با replace_content
                                    f["content"] = _replace_content
                                    f["_fallback_full_replace"] = True
                                    _syntax_check = _validate_file_content_syntax(f["content"], file_path)
                                    if _syntax_check["valid"] and not _syntax_check.get("warnings"):
                                        yield sse("progress", {
                                            "step": "sections_fallback_applied",
                                            "message": f"🔄 {file_path}: فایل اصلی آلوده بود — fallback: جایگزینی کامل با کد تمیز"
                                        })
                                        final_files.append(f)
                                        _fallback_applied = True
                                        slog.info(f"[apply-action] FALLBACK full-replace for contaminated {file_path}")
                                    else:
                                        _fb_errs = "; ".join((_syntax_check.get("errors") or _syntax_check.get("warnings", []))[:2])
                                        yield sse("progress", {
                                            "step": "sections_fallback_syntax_error",
                                            "message": f"🚫 {file_path}: fallback هم شکست — کد replace خطای سینتکس داره: {_fb_errs}"
                                        })
                            # ── Fallback 2: AI auto-retry — تصحیح خودکار find/replace با استفاده از محتوای واقعی فایل ──
                            if not _fallback_applied and len(f["sections"]) <= 5:
                                try:
                                    from ...services.ai_manager import get_ai_manager as _retry_get_aim
                                    from ...services.ai_base import Message as _RetryMsg
                                    _retry_aim = _retry_get_aim()
                                    # ساخت context محتوای واقعی فایل (حداکثر ۴۰۰۰ کاراکتر)
                                    _retry_file_preview = original_content[:4000]
                                    if len(original_content) > 4000:
                                        _retry_file_preview += f"\n... [ادامه فایل — مجموعاً {_total_lines} خط]"
                                    _failed_sections_info = json.dumps(f["sections"], ensure_ascii=False, indent=2)[:2000]
                                    _retry_prompt = f"""find/replace زیر روی فایل اعمال نشد چون متن find در فایل واقعی پیدا نشد.
محتوای واقعی فایل:
```
{_retry_file_preview}
```

section‌های شکست‌خورده:
{_failed_sections_info}

لطفاً section‌ها رو تصحیح کن. find باید **دقیقاً** از متن واقعی فایل بالا کپی بشه (حتی فاصله‌ها و tab ها).
فقط JSON خالص برگردون:
{{"sections": [{{"find": "متن دقیق از فایل", "replace": "کد جدید"}}]}}"""

                                    yield sse("progress", {
                                        "step": "sections_auto_retry",
                                        "message": f"🔄 {file_path}: تلاش خودکار برای تصحیح find/replace..."
                                    })
                                    # استفاده از مدل سریع برای تصحیح
                                    _retry_model = request.model_ids[0] if request.model_ids else "gemini-2.0-flash"
                                    _retry_resp = await _retry_aim.generate(
                                        model_id=_retry_model,
                                        messages=[
                                            _RetryMsg(role="system", content="تو ابزار تصحیح find/replace هستی. فقط JSON خالص برگردون. find باید دقیقاً از متن فایل کپی بشه."),
                                            _RetryMsg(role="user", content=_retry_prompt)
                                        ],
                                        max_tokens=2000,
                                        temperature=0.1,
                                    )
                                    # استخراج JSON از پاسخ
                                    _retry_text = _retry_resp.content.strip()
                                    _retry_json_match = re.search(r'\{[\s\S]*"sections"[\s\S]*\}', _retry_text)
                                    if _retry_json_match:
                                        _retry_parsed = json.loads(_retry_json_match.group(0))
                                        _retry_sections = _retry_parsed.get("sections", [])
                                        if _retry_sections:
                                            _retry_merge = _apply_section_modifications(original_content, _retry_sections)
                                            if _retry_merge["applied"] > 0:
                                                f["content"] = _retry_merge["content"]
                                                f["_auto_retry_applied"] = True
                                                _retry_syntax = _validate_file_content_syntax(f["content"], file_path)
                                                if _retry_syntax["valid"]:
                                                    yield sse("progress", {
                                                        "step": "sections_auto_retry_success",
                                                        "message": f"✅ {file_path}: تصحیح خودکار موفق — {_retry_merge['applied']} بخش اعمال شد"
                                                    })
                                                    final_files.append(f)
                                                    _fallback_applied = True
                                                    slog.info(f"[apply-action] AUTO-RETRY success for {file_path}: {_retry_merge['applied']} sections applied")
                                                else:
                                                    _r_errs = "; ".join(_retry_syntax["errors"][:2])
                                                    yield sse("progress", {
                                                        "step": "sections_auto_retry_syntax_fail",
                                                        "message": f"🚫 {file_path}: تصحیح خودکار اعمال شد ولی سینتکس خطا داره: {_r_errs}"
                                                    })
                                except Exception as _retry_err:
                                    slog.warning(f"[apply-action] AUTO-RETRY failed for {file_path}: {_retry_err}")

                            if not _fallback_applied:
                                dropped_files.append({"path": file_path, "reason": f"modify_sections شکست: {_errs[:100]}"})
                    else:
                        # 🛡️ پاکسازی محتوا از آلودگی reasoning/markdown قبل از بررسی‌ها
                        _file_content = f.get("content", "")
                        if _file_content:
                            from ...services.content_sanitizer import sanitize_file_content as _cs_sanitize_mod
                            _file_content = _cs_sanitize_mod(_file_content, file_path)
                            f["content"] = _file_content
                        # ── تشخیص بازنویسی مخرب در apply_action (لایه دوم) ──
                        _orig_content = existing.get("content", "")
                        if _file_content and _orig_content:
                            _orig_lines = len(_orig_content.strip().split("\n"))
                            _new_lines = len(_file_content.strip().split("\n"))
                            _is_destructive = False
                            # لایه ۱: فایل بزرگ خیلی کوچک شده
                            if _orig_lines > 80 and _new_lines < _orig_lines * 0.5:
                                _is_destructive = True
                                _reason = (
                                    f"بازنویسی مخرب: فایل اصلی {_orig_lines} خط بود ولی خروجی AI فقط {_new_lines} خط "
                                    f"({int(_new_lines/_orig_lines*100)}% از اصل) — احتمال حذف قابلیت‌های موجود"
                                )
                            # لایه ۲: محتوای واقعی حفظ نشده
                            elif _orig_lines > 100:
                                _trivial = {"{", "}", "(", ")", "[", "]", "", "};", ");", "},", "],", "});", "export default", "return (", "return null;"}
                                _orig_meaningful = set()
                                for _ol in _orig_content.strip().split("\n"):
                                    _stripped_ol = _ol.strip()
                                    if _stripped_ol and _stripped_ol not in _trivial and len(_stripped_ol) > 10:
                                        _orig_meaningful.add(_stripped_ol)
                                if len(_orig_meaningful) > 20:
                                    _preserved = sum(1 for _om in _orig_meaningful if _om in _file_content)
                                    _preserve_ratio = _preserved / len(_orig_meaningful)
                                    if _preserve_ratio < 0.25:
                                        _is_destructive = True
                                        _reason = (
                                            f"بازنویسی مخرب (محتوایی): فقط {int(_preserve_ratio*100)}% از خطوط معنادار "
                                            f"({_preserved}/{len(_orig_meaningful)}) حفظ شده — مدل فایل رو از صفر نوشته"
                                        )
                            if _is_destructive:
                                # ── Auto-recovery: merge AI changes into original instead of dropping ──
                                import difflib as _difflib
                                _orig_lines_list = _orig_content.split("\n")
                                _new_lines_list = _file_content.split("\n")
                                try:
                                    _matcher = _difflib.SequenceMatcher(None, _orig_lines_list, _new_lines_list)
                                    _merged_lines = []
                                    _kept_deleted = 0
                                    _changes_applied = 0
                                    for _tag, _i1, _i2, _j1, _j2 in _matcher.get_opcodes():
                                        if _tag == 'equal':
                                            _merged_lines.extend(_orig_lines_list[_i1:_i2])
                                        elif _tag == 'replace':
                                            # AI changed these lines — keep the changes
                                            _merged_lines.extend(_new_lines_list[_j1:_j2])
                                            _changes_applied += 1
                                        elif _tag == 'insert':
                                            # AI added new lines — keep them
                                            _merged_lines.extend(_new_lines_list[_j1:_j2])
                                            _changes_applied += 1
                                        elif _tag == 'delete':
                                            # AI removed these lines — RESTORE from original (this is the recovery!)
                                            _merged_lines.extend(_orig_lines_list[_i1:_i2])
                                            _kept_deleted += (_i2 - _i1)
                                    _recovery_content = "\n".join(_merged_lines)
                                    _recovery_lines = len(_recovery_content.split("\n"))
                                    if _kept_deleted > 0 and _recovery_lines >= _orig_lines * 0.8 and _changes_applied > 0:
                                        # Validate syntax of recovered content
                                        _recov_syntax = _validate_file_content_syntax(_recovery_content, file_path)
                                        if _recov_syntax["valid"] and not _recov_syntax.get("warnings"):
                                            f["content"] = _recovery_content
                                            final_files.append(f)
                                            yield sse("progress", {
                                                "step": "destructive_rewrite_recovered",
                                                "message": f"🔄 {file_path}: بازنویسی مخرب شناسایی شد — بازیابی خودکار: {_kept_deleted} خط حذف‌شده بازگردانده شد ({_recovery_lines} خط نهایی از {_orig_lines} اصلی)"
                                            })
                                            slog.info(f"[apply-action] RECOVERED destructive rewrite {file_path}: restored {_kept_deleted} deleted lines, applied {_changes_applied} changes, final={_recovery_lines}")
                                            continue
                                        else:
                                            _recov_errs = "; ".join((_recov_syntax.get("errors") or _recov_syntax.get("warnings", []))[:2])
                                            yield sse("progress", {
                                                "step": "recovery_syntax_error",
                                                "message": f"⚠️ {file_path}: بازیابی خودکار هم با خطای سینتکس مواجه شد — {_recov_errs}"
                                            })
                                            slog.warning(f"[apply-action] Recovery syntax failed {file_path}: {_recov_errs}")
                                except Exception as _merge_err:
                                    slog.warning(f"[apply-action] Auto-recovery (merge) failed for {file_path}: {_merge_err}")

                                # 🆕 Fallback دوم: auto-convert به modify_sections با diff
                                _fallback_sections = _auto_convert_modify_to_sections(_orig_content, _file_content, file_path)
                                if _fallback_sections:
                                    # اعمال sections روی فایل اصلی
                                    _sec_result = _apply_section_modifications(_orig_content, _fallback_sections)
                                    # 🔴 (partial-apply-bug) — قبلاً اگر فقط بخشی از sections اعمال می‌شد
                                    # (مثلاً 3/4)، نتیجه partial **بی‌سروصدا** پذیرفته می‌شد. در transcript
                                    # کاربر این باعث شد `security = HTTPBearer()` گم بشه و deploy با
                                    # `NameError: name 'security' is not defined` کرش کرد. حالا
                                    # **همهٔ** sections باید apply بشن وگرنه فایل drop می‌شه.
                                    _total_sections = len(_fallback_sections)
                                    _applied_count = _sec_result.get("applied", 0)
                                    if _applied_count > 0 and _applied_count == _total_sections:
                                        _sec_syntax = _validate_file_content_syntax(_sec_result["content"], file_path)
                                        if _sec_syntax["valid"]:
                                            f["content"] = _sec_result["content"]
                                            final_files.append(f)
                                            yield sse("progress", {
                                                "step": "destructive_rewrite_section_converted",
                                                "message": f"🔄 {file_path}: بازنویسی مخرب → تبدیل خودکار به modify_sections: "
                                                           f"{_applied_count}/{_total_sections} بخش اعمال شد"
                                            })
                                            slog.info(f"[apply-action] AUTO-CONVERTED destructive rewrite {file_path}: {_applied_count}/{_total_sections} sections applied")
                                            continue
                                        else:
                                            _sec_errs = "; ".join(_sec_syntax.get("errors", [])[:2])
                                            slog.warning(f"[apply-action] Section-convert syntax failed {file_path}: {_sec_errs}")
                                    elif _applied_count > 0 and _applied_count < _total_sections:
                                        # partial — جلوگیری از commit ناقص که bug شناخته‌شده تولید می‌کنه
                                        _missing = _total_sections - _applied_count
                                        yield sse("progress", {
                                            "step": "destructive_rewrite_partial_rejected",
                                            "message": (
                                                f"🚫 {file_path}: auto-convert فقط {_applied_count} از {_total_sections} "
                                                f"بخش رو اعمال کرد ({_missing} بخش گم شده) — این می‌تونه قابلیت‌های "
                                                f"حذف‌شده تولید کنه (مثل تعریف ناقص متغیر). فایل drop شد."
                                            ),
                                        })
                                        slog.warning(
                                            f"[apply-action] PARTIAL section apply rejected for {file_path}: "
                                            f"{_applied_count}/{_total_sections} (dropped to avoid silent bugs)"
                                        )

                                # If all recovery methods failed, drop the file
                                yield sse("progress", {
                                    "step": "destructive_rewrite_rejected",
                                    "message": f"🚫 {file_path}: {_reason} — بازیابی خودکار (merge + sections) ناموفق بود"
                                })
                                dropped_files.append({"path": file_path, "reason": _reason[:150]})
                                slog.error(f"[apply-action] REJECTED destructive rewrite {file_path}: {_reason}")
                                continue
                        # ── بررسی آلودگی reasoning قبل از هر چیز ──
                        if _file_content:
                            _contamination = _detect_reasoning_contamination(_file_content, file_path)
                            if _contamination:
                                yield sse("progress", {
                                    "step": "contamination_blocked",
                                    "message": f"🛡️ محتوای آلوده بلاک شد: {_contamination[:100]}"
                                })
                                dropped_files.append({"path": file_path, "reason": f"آلودگی reasoning: {_contamination[:120]}"})
                                slog.error(f"[apply-action] BLOCKED reasoning contamination in {file_path}: {_contamination}")
                                continue

                        # ── اعتبارسنجی سینتکس محتوای نهایی قبل از commit ──
                        if _file_content:
                            _syntax_check = _validate_file_content_syntax(_file_content, file_path)
                            if not _syntax_check["valid"]:
                                _errs = "; ".join(_syntax_check["errors"][:3])
                                yield sse("progress", {
                                    "step": "syntax_error_modify",
                                    "message": f"⚠️ {file_path}: خطای سینتکس — شروع تصحیح خودکار... — {_errs}"
                                })
                                # 🔧 تلاش تصحیح خودکار سینتکس با AI
                                _mod_fixed = False
                                try:
                                    from ...services.ai_manager import get_ai_manager as _mfx_get_aim
                                    from ...services.ai_base import Message as _MfxMsg
                                    _mfx_aim = _mfx_get_aim()
                                    _mfx_preview = _file_content[:5000]
                                    if len(_file_content) > 5000:
                                        _mfx_preview += f"\n... [ادامه — {len(_file_content.split(chr(10)))} خط]"
                                    _mfx_prompt = f"""فایل زیر خطای سینتکس دارد. فقط خطاهای سینتکس را رفع کن.

خطاها: {_errs}

فایل ({file_path}):
```
{_mfx_preview}
```

⚠️ فقط خطاهای سینتکس — تغییر منطقی ایجاد نکن. فایل کامل، بدون markdown."""
                                    _mfx_model = request.model_ids[0] if request.model_ids else "gemini-2.0-flash"
                                    _mfx_resp = await _mfx_aim.generate(
                                        model_id=_mfx_model,
                                        messages=[
                                            _MfxMsg(role="system", content="ابزار تصحیح سینتکس. فقط خطاهای سینتکس رو رفع کن. کد کامل بدون markdown."),
                                            _MfxMsg(role="user", content=_mfx_prompt)
                                        ],
                                        max_tokens=8000,
                                        temperature=0.1,
                                    )
                                    _mfx_result = _mfx_resp.content.strip()
                                    import re as _mfx_re
                                    _mfx_code_match = _mfx_re.search(r'```(?:tsx?|jsx?|py|json|css|html)?\s*\n(.*?)\n```', _mfx_result, _mfx_re.DOTALL)
                                    if _mfx_code_match:
                                        _mfx_result = _mfx_code_match.group(1).strip()
                                    if _mfx_result and len(_mfx_result) > 50:
                                        _mfx_check = _validate_file_content_syntax(_mfx_result, file_path)
                                        if _mfx_check["valid"]:
                                            f["content"] = _mfx_result
                                            _mod_fixed = True
                                            yield sse("progress", {
                                                "step": "syntax_fix_modify_success",
                                                "message": f"✅ {file_path}: تصحیح خودکار AI موفق — خطای سینتکس رفع شد"
                                            })
                                            slog.info(f"[apply-action] AI syntax fix success for modify {file_path}")
                                except Exception as _mfx_err:
                                    slog.warning(f"[apply-action] AI syntax fix failed for modify {file_path}: {_mfx_err}")
                                if not _mod_fixed:
                                    yield sse("progress", {
                                        "step": "syntax_error_rejected",
                                        "message": f"🚫 {file_path}: خطای سینتکس (تصحیح خودکار ناموفق) — {_errs}"
                                    })
                                    dropped_files.append({"path": file_path, "reason": f"خطای سینتکس: {_errs[:120]}"})
                                    slog.error(f"[apply-action] REJECTED modify {file_path}: syntax errors: {_errs}")
                                    continue
                            # هشدارها فایل رو بلاک نمیکنن — فقط لاگ میشن
                            if _syntax_check.get("warnings"):
                                _warns = "; ".join(_syntax_check["warnings"][:3])
                                yield sse("progress", {
                                    "step": "syntax_warning_info",
                                    "message": f"⚠️ {file_path}: هشدار سینتکس (فایل commit میشه ولی چک کنید) — {_warns}"
                                })
                                slog.warning(f"[apply-action] WARNING (not rejected) modify {file_path}: syntax warnings: {_warns}")
                            final_files.append(f)
                        else:
                            final_files.append(f)
                else:
                    yield sse("progress", {
                        "step": "file_not_found",
                        "message": f"🚫 فایل {file_path} در ریپو وجود ندارد — رد شد (احتمالاً محتوای ساختگی)"
                    })
                    dropped_files.append({"path": file_path, "reason": "فایل در ریپو وجود ندارد"})
            except Exception:
                yield sse("progress", {
                    "step": "file_check_error",
                    "message": f"⚠️ بررسی وجود {file_path} ناموفق — رد شد برای ایمنی"
                })
                dropped_files.append({"path": file_path, "reason": "خطا در بررسی وجود فایل"})

        # هشدار به کاربر اگه فایل‌هایی حذف شدن
        if dropped_files:
            _drop_msg = f"⚠️ {len(dropped_files)} فایل از {len(validated_files)} اعمال نشد:\n"
            _drop_msg += "\n".join(f"  🚫 {d['path']}: {d['reason']}" for d in dropped_files)
            yield sse("progress", {
                "step": "dropped_files_warning",
                "message": _drop_msg
            })

        if not final_files:
            yield sse("error", {"message": "🚫 هیچ‌یک از فایل‌ها در ریپو وجود ندارند — احتمالاً محتوای ساختگی AI. اعمال لغو شد."})
            yield sse("done", {"success": False})
            return

        # 🛡️ (atomic-apply fix) — اگر فایلی به دلایل بحرانی (آلودگی، سینتکس،
        # hallucination، modify_sections شکست) رد شده، ادامهٔ commit برای
        # فایل‌های باقی‌مانده خطرناک است چون ممکن است به symbols/imports از
        # فایل‌های رد شده وابسته باشند. مثال واقعی: app/config.py به‌خاطر
        # contamination رد شد ولی app/main.py با `from app.config import settings`
        # commit شد → دیپلوی با ImportError شکست می‌خورد.
        # سیاست جدید: اگر هر فایلی به دلیل بحرانی رد شد، کل apply لغو می‌شود.
        _critical_drop_keywords = (
            "آلودگی reasoning",
            "خطای سینتکس",
            "modify_sections شکست",
            "hallucinated",
            "بازنویسی مخرب",
            "merge",
        )
        _critical_drops = [
            d for d in dropped_files
            if any(kw in (d.get("reason") or "") for kw in _critical_drop_keywords)
        ]
        if _critical_drops:
            _crit_msg = (
                f"🚫 apply لغو شد: {len(_critical_drops)} فایل به دلایل بحرانی رد شدند و کامیت بقیه فایل‌ها "
                f"وابسته به آن‌ها است (خطر import غیرموجود یا state ناقص). "
                f"لطفاً از مدل بخواهید فایل‌های رد شده را اصلاح کند و دوباره تلاش کنید.\n"
                + "\n".join(f"  🚫 {d['path']}: {d['reason']}" for d in _critical_drops)
            )
            yield sse("error", {"message": _crit_msg})
            yield sse("done", {"success": False, "reason": "critical_files_dropped"})
            slog.error(f"[apply-action] ABORTED due to {len(_critical_drops)} critical file drops: " +
                       ", ".join(d["path"] for d in _critical_drops))
            return

        # --- Commit فایل‌ها ---
        committed_files = []
        for i, f in enumerate(final_files):
            file_path = f.get("path", "").strip()
            file_content = f.get("content", "")
            operation = f.get("operation", "modify")

            if not file_path or not file_content:
                continue

            yield sse("progress", {
                "step": "committing_file",
                "message": f"📝 Commit {file_path} ({i+1}/{len(final_files)})...",
                "file": file_path
            })

            try:
                commit_result = await pr_svc.create_or_update_file(
                    owner=owner,
                    repo=repo,
                    path=file_path,
                    content=file_content,
                    message=f"fix: {request.commit_message} - {file_path}",
                    branch=branch_name,
                    token=token
                )

                if commit_result.get("success"):
                    committed_files.append(file_path)
                    yield sse("progress", {
                        "step": "file_committed",
                        "message": f"✅ {file_path} commit شد"
                    })
                else:
                    yield sse("progress", {
                        "step": "file_error",
                        "message": f"⚠️ خطا در commit {file_path}: {commit_result.get('error', '')[:60]}"
                    })
            except Exception as e:
                yield sse("progress", {
                    "step": "file_error",
                    "message": f"⚠️ خطا: {str(e)[:60]}"
                })
            await asyncio.sleep(0.3)

        if not committed_files:
            yield sse("error", {"message": "هیچ فایلی commit نشد"})
            yield sse("done", {"success": False})
            return

        # --- ساخت PR ---
        yield sse("progress", {
            "step": "creating_pr",
            "message": "📋 در حال ساخت Pull Request..."
        })

        try:
            _dropped_section = ""
            if dropped_files:
                _dropped_section = f"""

**⚠️ فایل‌هایی که اعمال نشدند ({len(dropped_files)} فایل):**
{chr(10).join(f'- `{d["path"]}`: {d["reason"]}' for d in dropped_files)}
"""
            pr_body = f"""## 🔧 اعمال تغییرات بازرس ویژه

**درخواست کاربر:**
{request.original_message[:200]}

**توضیح تغییرات:**
{request.commit_message}

**فایل‌های تغییر یافته:**
{chr(10).join(f'- `{f}`' for f in committed_files)}
{_dropped_section}
---
_ساخته شده توسط بازرس ویژه (Inspector)_"""

            pr_result = await pr_svc.create_pull_request(
                owner=owner,
                repo=repo,
                title=f"🔧 Inspector: {request.commit_message[:60]}",
                body=pr_body,
                head_branch=branch_name,
                token=token
            )

            pr_url_final: str = ""
            if pr_result.get("success"):
                pr_url_final = pr_result.get("html_url", pr_result.get("url", ""))
                yield sse("apply_complete", {
                    "success": True,
                    "message": f"✅ Pull Request ساخته شد!\n\n🔗 {pr_url_final}",
                    "pr_url": pr_url_final,
                    "branch": branch_name,
                    "files_committed": committed_files,
                })
            else:
                yield sse("apply_complete", {
                    "success": True,
                    "message": f"✅ فایل‌ها commit شدند در branch {branch_name}\n⚠️ ساخت PR ناموفق: {pr_result.get('error', '')[:80]}",
                    "branch": branch_name,
                    "files_committed": committed_files,
                })
        except Exception as e:
            pr_url_final = ""
            yield sse("apply_complete", {
                "success": True,
                "message": f"✅ فایل‌ها commit شدند در branch {branch_name}\n⚠️ خطا در ساخت PR: {str(e)[:80]}",
                "branch": branch_name,
                "files_committed": committed_files,
            })

        # 🆕 (v3 render-ops) — اجرای render_actions اگر داده شده
        # (مثلاً set DATABASE_URL، restart_service، trigger_deploy)
        if request.render_actions:
            yield sse("progress", {
                "step": "render_actions",
                "message": f"⚙️ در حال اجرای {len(request.render_actions)} عملیات Render...",
            })
            try:
                ra_result = await _execute_render_actions(request.render_actions)
                _ra_summary_lines: List[str] = []
                for r in ra_result.get("results", []):
                    icon = "✅" if r.get("success") else "❌"
                    desc = r.get("action", "?")
                    if r.get("key"):
                        desc += f" {r.get('key')}"
                    if r.get("service"):
                        desc += f" @ {r.get('service')}"
                    _ra_summary_lines.append(f"{icon} {desc}")
                msg_text = (
                    "⚙️ نتیجه عملیات Render:\n" + "\n".join(_ra_summary_lines)
                    if _ra_summary_lines else "⚙️ هیچ عملیات Render اجرا نشد"
                )
                if ra_result.get("errors"):
                    msg_text += "\n\n⚠️ خطاها:\n" + "\n".join(
                        f"- {e}" for e in ra_result["errors"][:5]
                    )
                yield sse("render_actions_complete", {
                    "success": ra_result.get("success", False),
                    "message": msg_text,
                    "results": ra_result.get("results", []),
                    "errors": ra_result.get("errors", []),
                })
            except Exception as ra_e:
                yield sse("render_actions_complete", {
                    "success": False,
                    "message": f"❌ خطا در اجرای عملیات Render: {str(ra_e)[:200]}",
                    "errors": [str(ra_e)[:300]],
                })

        # 🔗 (Bug C7 Bridge Phase 1 + 3) — اگر task_id داده شده، write-back و
        # verify v6 اجرا کن. این مسیر فقط با task_id فعال است و backward
        # compatible: اگر task_id نباشد یا تسک پیدا نشود، خطایی ندارد.
        if getattr(request, "task_id", None):
            yield sse("progress", {
                "step": "writing_back",
                "message": "📝 در حال به‌روزرسانی تسک مرکز نظارت...",
            })
            try:
                _wb_ok = await _writeback_task_after_apply(
                    request.task_id,
                    pr_url=pr_url_final or None,
                    branch=branch_name,
                    files_committed=committed_files,
                    commit_message=request.commit_message,
                    model_ids=request.model_ids or [],
                )
                if _wb_ok:
                    yield sse("progress", {
                        "step": "writeback_done",
                        "message": "✅ تسک به‌روز شد (action_plan + applied_evidence)",
                    })
            except Exception as _wbe:
                logger.warning(f"apply-action writeback failed: {_wbe}")

            # verify v6 stack
            yield sse("progress", {
                "step": "verifying",
                "message": "🔬 در حال اجرای verify v6 روی تسک...",
            })
            try:
                _verify_result = await _verify_task_via_v6_stack(request.task_id)
                if _verify_result:
                    _verdict = _verify_result.get("verdict") or "unknown"
                    _done_n = _verify_result.get("done_parts_count", 0)
                    _rem_n = _verify_result.get("remaining_parts_count", 0)
                    yield sse("verify_complete", {
                        "success": True,
                        "task_id": request.task_id,
                        "verdict": _verdict,
                        "done_parts_count": _done_n,
                        "remaining_parts_count": _rem_n,
                        "report_id": _verify_result.get("report_id"),
                        "verify_version": _verify_result.get("verify_version"),
                        "message": (
                            f"🔬 verify: {_verdict} "
                            f"(done={_done_n}, remaining={_rem_n})"
                        ),
                    })

                    # 🔗 (C7 Bridge Phase 4) — allow_push gate.
                    # اگر تسک به watched متصل است و watched.allow_push=False،
                    # یا verdict in (not_done, partial), یک هشدار به کاربر
                    # برسد که PR ساخته شده ولی verify confidence کافی نیست.
                    # حذف خودکار PR انجام نمی‌شود (ریسک از دست رفتن کار)؛ فقط
                    # notify می‌فرستیم تا کاربر دستی بررسی کند.
                    try:
                        from ...services.oversight_service import (
                            get_oversight_service as _get_ovs,
                        )
                        _svc = _get_ovs()
                        _t_obj = next(
                            (tt for tt in _svc.tasks if tt.id == request.task_id),
                            None,
                        )
                        if _t_obj and _t_obj.watched_id:
                            _w_obj = _svc._find_watched(_t_obj.watched_id)
                            if (
                                _w_obj
                                and not getattr(_w_obj, "allow_push", False)
                                and pr_url_final
                                and _verdict not in ("done",)
                            ):
                                yield sse("progress", {
                                    "step": "allow_push_warning",
                                    "message": (
                                        "⚠️ allow_push=false و verify=" + _verdict +
                                        " — PR ساخته شد ولی توصیه می‌شود قبل از merge "
                                        "دستی بررسی کنید."
                                    ),
                                })
                    except Exception as _age:
                        logger.debug(f"allow_push gate check failed: {_age}")
            except Exception as _ve:
                logger.warning(f"apply-action verify failed: {_ve}")
                yield sse("verify_complete", {
                    "success": False,
                    "error": str(_ve)[:200],
                })

        yield sse("done", {"success": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# 🔀 Inspector Page Proxy - پروکسی برای رفع مشکل cross-origin iframe
# ─────────────────────────────────────────────────────────────────────────────

# 🔗 اسکریپت تزریقی — رصد URL + ناوبری از طریق proxy + رفع fetch/XHR
# __BASE__ و __PROXY__ در زمان inject جایگزین میشوند
_PROXY_MONITOR_SCRIPT_TEMPLATE = """<script data-inspector-proxy="true">
(function(){
  var BASE='__BASE__', PROXY='__PROXY__';
  var _ps=history.pushState,_rs=history.replaceState;
  function _r(){try{window.parent.postMessage({type:'proxy-url-change',href:location.href,path:location.pathname+location.search+location.hash},'*');}catch(e){}}
  history.pushState=function(){_ps.apply(this,arguments);_r();};
  history.replaceState=function(){_rs.apply(this,arguments);_r();};
  window.addEventListener('popstate',_r);
  window.addEventListener('hashchange',_r);

  /* رهگیری کلیک لینک‌ها — تبدیل URL واقعی به proxy */
  document.addEventListener('click',function(e){
    var a=e.target&&e.target.closest?e.target.closest('a'):null;
    if(!a||!a.href)return;
    var h=a.href;
    if(h.indexOf(BASE)===0){
      e.preventDefault();
      var rest=h.slice(BASE.length);
      location.href=PROXY+(rest.charAt(0)==='/'?rest:'/'+rest);
    }
  },true);

  /* رهگیری fetch — مسیرهای مطلق (/) از طریق proxy ارسال شوند (same-origin = بدون CORS) */
  var _fetch=window.fetch;
  window.fetch=function(url,opts){
    if(typeof url==='string'&&url.charAt(0)==='/'&&url.indexOf(PROXY)!==0){url=PROXY+url;}
    return _fetch.call(this,url,opts);
  };

  /* رهگیری XMLHttpRequest.open */
  var _xopen=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(m,url){
    if(typeof url==='string'&&url.charAt(0)==='/'&&url.indexOf(PROXY)!==0){arguments[1]=PROXY+url;}
    return _xopen.apply(this,arguments);
  };

  _r();
})();
</script>"""


@router.get("/inspector/proxy/{project_id}/{path:path}")
@router.get("/inspector/proxy/{project_id}")
async def inspector_page_proxy(
    project_id: str,
    request: Request,
    path: str = "",
    db: Session = Depends(get_db),
):
    """
    پروکسی معکوس — محتوای فرانت‌اند پروژه را از طریق origin خود سرور بازمیگرداند
    تا iframe همیشه same-origin باشد و URL قابل خواندن باشد.
    """
    from fastapi.responses import Response as FastAPIResponse

    # 1. پیدا کردن frontend_url پروژه
    services = db.query(RenderService).filter(
        RenderService.project_id == project_id
    ).all()
    if not services:
        from ...models.project import Project
        proj = db.query(Project).filter(Project.id == project_id).first()
        if proj:
            st = proj.name.lower().replace(" ", "-").replace("_", "-")
            all_svc = db.query(RenderService).all()
            services = [s for s in all_svc if st in s.name.lower() or s.name.lower() in st]

    frontend_url = None
    for s in services:
        surl = s.service_url if hasattr(s, 'service_url') and s.service_url else None
        if not surl and s.type in ("web_service", "static_site"):
            slug = s.name.lower().replace(" ", "-").replace("_", "-")
            surl = f"https://{slug}.onrender.com"
        if surl:
            nm = s.name.lower()
            is_fe = any(x in nm for x in ("frontend", "front", "client", "ui", "static"))
            is_be = any(x in nm for x in ("backend", "back", "api", "server"))
            if is_fe and not is_be:
                frontend_url = surl
                break
            if not frontend_url:
                frontend_url = surl

    if not frontend_url:
        return FastAPIResponse(
            content="<html><body><h3>فرانت‌اند یافت نشد</h3></body></html>",
            status_code=404,
            media_type="text/html",
        )

    # 2. ساخت URL هدف
    target_url = frontend_url.rstrip("/")
    if path:
        target_url += "/" + path
    qs = str(request.query_params)
    if qs:
        target_url += "?" + qs

    # 3. ارسال درخواست به سرور واقعی
    import httpx
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
            resp = await client.get(target_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
    except Exception as exc:
        return FastAPIResponse(
            content=f"<html><body><h3>خطا در اتصال به {frontend_url}</h3><p>{str(exc)[:200]}</p></body></html>",
            status_code=502,
            media_type="text/html",
        )

    ct = resp.headers.get("content-type", "")

    # 4. اگر HTML است: بازنویسی مسیرهای مطلق + تزریق اسکریپت رصد
    if "text/html" in ct:
        html = resp.text
        base_url = frontend_url.rstrip("/")
        proxy_prefix = f"/api/render/inspector/proxy/{project_id}"

        # ✅ بازنویسی مسیرهای مطلق در attribute های HTML
        # src="/_next/..." → src="/api/render/inspector/proxy/projId/_next/..."
        # href="/styles..." → href="/api/render/inspector/proxy/projId/styles..."
        import re as _re
        html = _re.sub(
            r'((?:src|href|action)\s*=\s*["\'])(\/(?!\/|api\/render\/inspector\/proxy))',
            f'\\1{proxy_prefix}/',
            html,
        )
        # srcset="/_next/image 1x, ..." — بازنویسی
        html = _re.sub(
            r'(srcset\s*=\s*["\'])(/)',
            f'\\1{proxy_prefix}/',
            html,
        )

        # ساخت اسکریپت با مقادیر واقعی
        monitor_script = _PROXY_MONITOR_SCRIPT_TEMPLATE.replace("__BASE__", base_url).replace("__PROXY__", proxy_prefix)
        if "</head>" in html:
            html = html.replace("</head>", monitor_script + "</head>", 1)
        elif "<head>" in html:
            html = html.replace("<head>", "<head>" + monitor_script, 1)
        elif "<html" in html:
            html = html.replace("<html", f"<html>\n<head>{monitor_script}</head>", 1)
        else:
            html = f"<head>{monitor_script}</head>\n" + html

        # حذف هدرهایی که iframe را بلاک میکنند
        return FastAPIResponse(
            content=html,
            status_code=resp.status_code,
            media_type="text/html; charset=utf-8",
            headers={
                "X-Frame-Options": "ALLOWALL",
                "Cache-Control": "no-cache",
            },
        )

    # 5. سایر انواع (JS, CSS, تصاویر) — عبور بدون تغییر
    return FastAPIResponse(
        content=resp.content,
        status_code=resp.status_code,
        media_type=ct or "application/octet-stream",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 📸 Screenshot & Visual Debug - عکس‌برداری و دیباگ بصری
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/inspector/screenshot")
async def take_screenshot(request: ScreenshotRequest, db: Session = Depends(get_db)):
    """عکس‌برداری از صفحه پیش‌نمایش پروژه با استفاده از Playwright"""
    if not request.url:
        return {"success": False, "error": "آدرس صفحه مشخص نشده"}
    try:
        from ...services.browser_automation import BrowserSession, PLAYWRIGHT_AVAILABLE
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright نصب نیست. لطفاً pip install playwright && playwright install chromium اجرا کنید."}
        session = BrowserSession(
            session_id=f"screenshot_{request.project_id}_{int(datetime.now().timestamp())}",
            url=request.url
        )
        session.viewport = {"width": request.viewport_width, "height": request.viewport_height}

        # 🔀 اگر DOM snapshot ارسال شده → رندر HTML فعلی بجای navigation به URL
        if request.html_content:
            await session._start_browser_only()
            import re as _re_ss
            # حذف اسکریپت‌ها (فقط نمای بصری — بدون اجرای مجدد JS)
            static_html = _re_ss.sub(r'<script[\s\S]*?</script>', '', request.html_content)
            # route interception — Playwright به URL واقعی میره ولی HTML ما رو نشون میده
            # اینطوری origin درسته و CSS/تصاویر با مسیر مطلق (/_next/...) درست لود میشن
            _fulfilled = False
            async def _intercept(route):
                nonlocal _fulfilled
                if not _fulfilled:
                    _fulfilled = True
                    await route.fulfill(body=static_html, content_type='text/html; charset=utf-8')
                else:
                    await route.continue_()
            await session.page.route(request.url.rstrip('/') + '**', _intercept)
            try:
                await session.page.goto(request.url, wait_until='networkidle', timeout=20000)
            except Exception:
                pass  # timeout OK — ادامه بده
        else:
            await session.start()

        await asyncio.sleep(2)
        screenshot_b64 = await session.take_screenshot()
        page_info = await session.get_page_info()
        await session.close()
        return {
            "success": True, "screenshot": screenshot_b64,
            "page_info": page_info, "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": f"خطا در عکس‌برداری: {str(e)[:200]}"}


@router.get("/inspector/vision-models")
async def get_vision_models(db: Session = Depends(get_db)):
    """لیست مدل‌هایی که قابلیت تحلیل تصویر (Vision) دارند"""
    from ...core.models_registry import MODEL_REGISTRY, ModelCapability
    from ...services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()
    vision_models = []
    for model_id, model in MODEL_REGISTRY.items():
        has_vision = (
            ModelCapability.VISION in model.capabilities or
            ModelCapability.IMAGE_ANALYSIS in model.capabilities or
            model.supports_images
        )
        if has_vision:
            is_enabled = ai_manager.get_enabled_status(model_id)
            vision_models.append({
                "id": model.id, "name": model.name,
                "provider": model.provider.value if hasattr(model.provider, 'value') else str(model.provider),
                "enabled": is_enabled, "supports_images": model.supports_images,
                "capabilities": [c.value if hasattr(c, 'value') else str(c) for c in model.capabilities],
                "context_window": model.context_window,
                "recommended": ModelCapability.CODE in model.capabilities and has_vision,
            })
    vision_models.sort(key=lambda m: (not m['enabled'], not m['recommended'], m['name']))
    return {"success": True, "models": vision_models}


# ── منبع حقیقت واحد برای پرامپت بازرس بصری ──────────────────────
# هر تغییر در این تابع، هم در فرانت (پنل پرامپت بصری) و هم در پرامپت مدل‌ها
# خودکار منعکس میشه — نیازی به آپدیت جداگانه نیست.
def _build_visual_debug_prompt_list() -> list:
    """
    لیست ساختاریافته پرامپت بازرس بصری.
    ⚠️ این تابع تنها منبع حقیقت (single source of truth) است:
    - اندپوینت /visual-debug-prompt ازش استفاده میکنه (نمایش در فرانت)
    - _build_visual_debug_prompt_text ازش ساخته میشه (تزریق در پرامپت مدل‌ها)
    هر تغییری اینجا بدی، خودکار همه جا منعکس میشه.
    """
    return [
        {
            "id": "vd_role",
            "title": "نقش و هویت",
            "content": "مهندس ارشد نرم‌افزار — تحلیل بصری عکس + لاگ + کد → پیاده‌سازی کامل",
            "icon": "🔍",
            "prompt_detail": "شما یک **مهندس ارشد نرم‌افزار** هستید با تسلط کامل بر فرانت‌اند و بکند. از طریق عکس‌ها، لاگ‌ها، مسیرهای API و کد فعلی، وضعیت دقیق پروژه را درک می‌کنید و هر درخواستی — از رفع باگ تا ایجاد قابلیت کاملاً جدید — را با دقت بالا پیاده‌سازی می‌کنید.",
        },
        {
            "id": "vd_honesty",
            "title": "🔴 صداقت تشخیصی — قاعدهٔ بنیادی",
            "content": "Placeholder ≠ سالم. اگر صفحه فقط لوگو/متن/«در حال آماده‌سازی» دارد، صریحاً «ناقص» اعلام کن.",
            "icon": "⚖️",
            "prompt_detail": """⚠️ **این مهم‌ترین قاعده است**: شکست‌های قبلی ناشی از این بود که مدل وقتی build/deploy موفق بوده، اعلام «همه چیز OK است» می‌کرد — حتی وقتی صفحه عملاً خالی بود.

### ✅ معیار «سالم بودن واقعی» یک صفحه
صفحه فقط وقتی «سالم» است که **حداقل یکی** از این‌ها را داشته باشد:
- داده/فهرست واقعی (لیست آیتم، جدول، چارت با داده)
- فرم یا تعامل عملی (ورودی، دکمهٔ کارا، modal)
- ناوبری عملی به صفحه‌ای که خودش دادهٔ واقعی دارد
- محتوای پویا که از API می‌آید و نمایش داده می‌شود

### ❌ نشانه‌های «ناقص بودن» (نه «سالم بودن دقیقاً همان‌طور که باید»)
- صفحه فقط لوگو + عنوان + شعار + «در حال آماده‌سازی»/«coming soon» دارد
- دکمه‌هایی که فقط لینک به /api/docs یا گزارش وضعیت بکند می‌دهند
- هیچ ورودی/فرم/جدول/لیست واقعی نیست
- "Backend در حال آماده‌سازی" نمایش داده می‌شود = اپ به فاز عملیاتی نرسیده

### 🚫 ممنوعیت‌های صریح در پاسخ
- 🚫 هرگز نگو «هیچ مشکلی نیست» وقتی صفحه عمدتاً placeholder است
- 🚫 هرگز نگو «این دقیقاً همان چیزی است که باید باشد» وقتی کاربر گفت «خالی است»
- 🚫 هرگز success build/deploy را با «اپ کامل است» اشتباه نگیر — build فقط می‌گوید «کامپایل شد»، نه «قابلیت‌ها پیاده شده‌اند»

### ✅ روش درست تشخیص
1. عکس را با چشم باز ببین: چه قابلیت‌های **کاربری** هست؟ (نه فقط چه چیز رنگارنگی هست)
2. اگر کاربر گفت «خالی است» یا «هیچ امکاناتی نیست»، **حرفش را تحت‌اللفظی بگیر** — حتی اگر build موفق است
3. کد را بخوان: آیا فقط `<div>عنوان</div>` است یا واقعاً state + handler + API call دارد؟
4. اگر فرانت placeholder است، صریحاً اعلام کن «این صفحه placeholder است، قابلیت‌های زیر باید پیاده شود: ...» و action_plan کامل بنویس""",
        },
        {
            "id": "vd_inputs",
            "title": "اطلاعات دریافتی",
            "content": "عکس‌ها، لاگ‌ها، URL، API paths، کد فایل‌ها، ساختار پروژه",
            "icon": "📥",
            "prompt_detail": """🔑 **دسترسی کامل به پروژه**: شما به **تمام فایل‌های پروژه** دسترسی کامل دارید. سیستم به صورت هوشمند درخواست کاربر را تحلیل کرده و مرتبط‌ترین فایل‌ها را از **کل مخزن پروژه** (فرانت‌اند و بکند) انتخاب و خوانده و در اختیار شما گذاشته. هرگز نگویید «دسترسی ندارم» یا «محتوای فایل X را در اختیار ندارم» — شما دسترسی دارید.

اطلاعاتی که دریافت می‌کنید:
1. **عکس‌های صفحه** (شماره‌دار): اسکرین‌شات از UI فعلی — ساختار، چیدمان، المان‌ها، رنگ‌ها
2. **پک لاگ هر عکس**: کنسول مرورگر (error, warn, log) + لاگ‌های بکند + آدرس صفحه + مسیرهای API
3. **کد فایل‌های پروژه** (انتخاب هوشمند از کل مخزن): فرانت و بکند — سیستم مرتبط‌ترین فایل‌ها را خودش انتخاب کرده
4. **ساختار کامل پروژه**: درخت فایل‌ها — نشان‌دهنده تمام فایل‌های قابل دسترسی
5. **درخواست کاربر**: مهم‌ترین بخش

⛔ **ممنوعیت مطلق**: هرگز نگویید «دسترسی ندارم»، «در اختیارم نیست»، «دوباره ارسال کنید»، «قادر به نوشتن action_plan نیستم».
✅ **همیشه** با فایل‌های موجود action_plan کامل بنویسید. فایل‌هایی که وجود ندارند را با operation: "create" بسازید.""",
        },
        {
            "id": "vd_request_types",
            "title": "انواع درخواست",
            "content": "رفع باگ • قابلیت جدید • تغییر ظاهر • بهبود/ریفکتور • تحلیل",
            "icon": "🎯",
            "prompt_detail": """### 🐛 رفع باگ / خطا
- عکس‌ها و لاگ‌ها → **علت ریشه‌ای** → مسیرهای API و فایل‌های بکند → کد اصلاح‌شده کامل

### ✨ اضافه کردن قابلیت جدید
- **ابتدا** عکس‌ها: ساختار فعلی UI، کامپوننت‌ها، استایل‌ها، الگوی طراحی
- **سپس** مسیرهای API و لاگ‌ها: endpoint ها و ساختار بکند
- **بعد** کد فعلی: الگوهای کدنویسی، state management، convention ها
- **نهایت** قابلیت جدید **دقیقاً در ادامه معماری موجود**:
  - React/Next.js → همان الگوی کامپوننت و state
  - FastAPI/Express → endpoint جدید با همان convention
  - CSS/Tailwind مطابق استایل فعلی صفحه (از عکس ببین)
  - RTL بودن UI رعایت شود

### 🎨 تغییر ظاهری / UI
- از عکس‌ها **دقیقاً** المان مورد نظر → CSS/JSX تغییر → responsive

### 🔧 بهبود / ریفکتور
- عملکرد فعلی حفظ + کد تمیزتر

### 📖 توضیح / تحلیل
- بدون تغییر کد، تحلیل بصری و فنی""",
        },
        {
            "id": "vd_workflow",
            "title": "روش کار هوشمند",
            "content": "شناخت محیط → شناخت کد → پیاده‌سازی کامل",
            "icon": "🧠",
            "prompt_detail": """### مرحله ۱: شناخت محیط
- هر عکس: چه صفحه‌ای؟ چه المان‌هایی؟ چه وضعیتی؟
- URL هر عکس: در کدام route هستیم؟
- مسیرهای API مرتبط: کدام endpoint ها فراخوانی شده‌اند؟

### مرحله ۲: شناخت کد
- **دقیقاً** بفهم: کدام کامپوننت/فایل مسئول آن بخش از UI
- کدام endpoint بکند مسئول آن API path
- state management چگونه کار می‌کند
- الگوهای نام‌گذاری و convention ها

### مرحله ۳: پیاده‌سازی
- کد **کامل و آماده اجرا** — نه فقط snippet
- import ها فراموش نشود
- type/interface ها (TypeScript) صحیح
- error handling مناسب
- فایل‌های فرانت و بکند هر دو در صورت نیاز""",
        },
        {
            "id": "vd_response_format",
            "title": "قالب پاسخ",
            "content": "وضعیت فعلی → تحلیل → فایل‌های مرتبط → تغییرات کد → action_plan",
            "icon": "📋",
            "prompt_detail": """### ۱. وضعیت فعلی
(توضیح کوتاه: چه می‌بینم در عکس‌ها، لاگ‌ها و کد)

### ۲. تحلیل درخواست
(درخواست چیست؟ چه فایل‌هایی باید تغییر کنند؟ چرا؟)

### ۳. فایل‌های مرتبط
| فایل | عملیات | توضیح |
|------|--------|-------|
| `path/to/file.tsx` | modify | توضیح تغییر |

### ۴. تغییرات کد + action_plan
(برای هر فایل، کد کامل در قالب action_plan — ببین بخش «فرمت action_plan»)""",
        },
        {
            "id": "vd_action_plan",
            "title": "فرمت action_plan (اجباری)",
            "content": "JSON ساختاریافته: path + content + operation — محتوای کامل اجباری",
            "icon": "📦",
            "prompt_detail": """🔴 **اجباری**: برای هر درخواستی که نیاز به تغییر کد دارد، **حتماً** بلوک action_plan بنویس:

### فرمت ۱: modify/create (محتوای کامل فایل)
```json
{
  "files": [
    {
      "path": "مسیر/فایل.tsx",
      "operation": "modify",
      "description": "توضیح تغییر",
      "content": "محتوای کامل فایل (نه فقط تکه‌ای)"
    }
  ],
  "commit_message": "پیام کامیت مناسب"
}
```

### فرمت ۲: modify_sections (فقط بخش‌های تغییریافته — ویژه فایل‌های بزرگ >200 خط)
```json
{
  "files": [
    {
      "path": "مسیر/فایل-بزرگ.tsx",
      "operation": "modify_sections",
      "description": "توضیح تغییرات",
      "sections": [
        {"find": "متن دقیق بخشی از فایل اصلی", "replace": "متن جایگزین"},
        {"find": "import { useState } from 'react';", "replace": "import { useState, useEffect } from 'react';"}
      ]
    }
  ],
  "commit_message": "پیام کامیت"
}
```

⚠️ قوانین action_plan:
- operation: "modify" (ویرایش — محتوای کامل) یا "create" (فایل جدید) یا "modify_sections" (تغییر بخشی)
- **modify**: content = محتوای کامل و قابل جایگزینی فایل — فقط برای فایل‌های کوچک (<200 خط)
- **modify_sections**: sections = لیست تغییرات {find, replace} — سیستم خودش فایل اصلی رو میخونه و sections رو اعمال میکنه
- 🔴🔴🔴 **find باید COPY-PASTE دقیق از متن فایل اصلی باشد** — شامل تمام فاصله‌ها، tab ها، نام متغیرها و حتی کامنت‌ها
- ⛔ **هرگز find رو حدس نزن یا از حافظه بنویس** — حتماً از متن فایل که بالاتر داده شده COPY کن
- ⛔ اگر find حتی ۱ کاراکتر با فایل واقعی فرق داشته باشه → section **شکست میخوره** و تغییرات اعمال نمیشه
- ✅ find باید حداقل ۲-۳ خط کامل و یکتا از فایل باشه — نه فقط یک خط کوتاه که ممکنه تکراری باشه
- ✅ اگر مطمئن نیستی متن دقیقه → find رو بزرگ‌تر بگیر (۵-۱۰ خط) تا شانس تطبیق بالا بره
- 🔴 **تمام** فایل‌ها و content/sections باید **داخل** یک بلوک JSON باشد — هرگز کد رو جدا از action_plan ننویس
- files خالی ممنوع — یا فایل با محتوا/sections بذار، یا action_plan نذار
- بدون action_plan = بدون دکمه «اعمال تغییرات» ← کاربر نمی‌تواند تغییرات را اعمال کند

🚨🚨🚨 **قانون اجباری modify_sections — عدم رعایت = حذف خودکار فایل**:
- سیستم تعداد خطوط هر فایل را در هدر (`--- فایل (N خط)`) نوشته — آن عدد را ببین!
- ⛔ فایل بالای ۲۰۰ خط + operation: "modify" = **سیستم خودکار فایل را حذف میکند**
- ⛔ فایل بالای ۸۰ خط + content کمتر از ۵۰٪ اصل = **سیستم خودکار فایل را حذف میکند**
- ✅ فایل بالای ۲۰۰ خط → **باید** از `modify_sections` استفاده شود
- ✅ فایل زیر ۲۰۰ خط → از `modify` با content کامل استفاده شود
- ✅ فایل جدید → از `create` با content کامل استفاده شود
- مثال: اگر فایل ۸۰۰ خط دارد و ۱۵ خط تغییر میخواهد → ۳ تا section با find/replace بنویس، نه ۸۰۰ خط content""",
        },
        {
            "id": "vd_rules",
            "title": "قوانین حیاتی",
            "content": "جواب کامل، فارسی، ممنوعیت حدس، محافظت بیلد/دیپلوی، تحلیل عمیق‌تر",
            "icon": "⚠️",
            "prompt_detail": """- به **فارسی** پاسخ بده. کدها و اصطلاحات فنی انگلیسی مجاز
- **هرگز** جواب ناقص نده — اگر فایل بزرگ است، از `modify_sections` استفاده کن
- 🚨 **فایل‌های بزرگ (>200 خط)**: **اجباری** از `operation: "modify_sections"` استفاده کن — اگر modify بنویسی سیستم **خودکار فایل رو حذف میکنه** و تغییراتت از دست میره!
- 🚨 **بالای ۸۰ خط**: اگر content خروجی < ۵۰٪ فایل اصلی باشه → سیستم آن فایل رو **حذف** میکنه!
- ✅ راه‌حل: هر فایلی که در هدر نوشته شده «⚠️ فایل بزرگ» → حتماً modify_sections بنویس
- اگر اطلاعات کافی نیست، **دقیقاً** بگو چه اطلاعات بیشتری نیاز داری

🔴 تحلیل عمیق‌تر در هر تلاش مجدد:
اگر کاربر دوباره مشکل مشابه مطرح کرد:
- فیکس قبلی ناکافی بوده — فقط تکرار کافی نیست
- دامنه بررسی وسیع‌تر: فایل‌های جدید مرتبط
- زنجیره وابستگی: route → service → model → config → types → middleware
- ریشه‌یابی قبل از کدنویسی
- هرگز همان راه‌حل را تکرار نکن

🔑 دسترسی کامل — ممنوعیت مطلق امتناع از action_plan:
- سیستم هوشمند مرتبط‌ترین فایل‌های پروژه را از کل مخزن انتخاب و خوانده و در اختیار تو گذاشته
- ⛔ هرگز نگو «دسترسی ندارم»، «در اختیارم نیست»، «در اختیارم قرار نگرفته»، «فایل خوانده نشده»، «سیستم فایل‌ها را نداده»
- ⛔ هرگز نگو «دوباره ارسال کنید»، «دوباره بپرسید»، «دوباره تلاش کنید»
- ⛔ هرگز نگو «قادر به نوشتن action_plan نیستم»
- ✅ **همیشه** با فایل‌های موجود action_plan کامل بنویس — حتی اگر فکر کنی فایل خاصی کم است
- ✅ فایل‌هایی که محتوایشان را می‌بینی → operation: "update"
- ✅ فایل‌هایی که وجود ندارند → operation: "create" بر اساس الگوهای پروژه و دانشت
- هرگز محتوای فایلی را حدس نزن — ولی action_plan را حتماً بنویس

🏗️ محافظت بیلد/دیپلوی (عدم رعایت = شکست دیپلوی):
- content هر فایل باید کامل و قابل جایگزینی باشد
- هرگز «// ... بقیه کد»، «// rest of file»، «/* existing code */» ننویس — کل فایل را بده
- قبل از نوشتن: imports صحیح؟ پرانتز/آکولاد بسته؟ تایپ‌ها درست؟ export سازگار؟
- JSX/TSX: تمام تگ‌ها بسته، className نه class، htmlFor نه for
- JSON: بدون trailing comma
- Python: indentation یکدست (4 spaces)
- اگر فایل بزرگ‌تر از توان تولید توست، آن را در action_plan نگذار — بنویس چه تغییری لازم است

🛡️ ممنوعیت بازنویسی مخرب (بسیار مهم):
- ⛔ هرگز فایل موجود را از صفر بازننویس — فقط بخش‌های مربوط به درخواست را تغییر بده
- ⛔ هرگز قابلیت‌های موجود را حذف نکن — اگر صفحه ۱۰ بخش دارد و درخواست ۱ بخش است، ۹ بخش دیگر دست‌نخورده بمانند
- ⛔ هرگز عملکرد واقعی (iframe, API call, event handler) را با placeholder جایگزین نکن
- ⛔ قبل از ایجاد فایل جدید، بررسی کن آیا کامپوننت مشابه در پروژه وجود داره

🎯 فهم دقیق درخواست کاربر:
- کلمات کاربر را تحت‌اللفظی بخوان: «فقط» = ONLY، «نباید» = MUST NOT
- هرگز معنی درخواست را برعکس تفسیر نکن
- مثال: «فقط در مانیتورینگ باشه» ≠ «در همه صفحات باشه»

🔄 قانون ویژه multi-step (اجرای مرحله‌ای):
- اگر در پرامپت «فایل‌های تغییر یافته تا الان» آمده → آن محتوا خروجی مراحل قبلی است
- اگر فایلی قبلاً تغییر یافته → تمام محتوای مرحله قبل حفظ شود + فقط تغییرات جدید اضافه شود
- ⛔ URL‌ها، API base، نام event‌ها، نام متغیرها: دقیقاً مثل مراحل قبلی — تغییر ندهید
- ⛔ هرگز فایل مرحله قبل را دور بینداز و از صفر بنویس""",
        },
    ]


def _build_visual_debug_prompt_text(general_instructions_text: str = "") -> str:
    """
    ساخت متن کامل پرامپت بازرس بصری از منبع واحد + دستورات عمومی.
    از prompt_detail (جزئیات کامل) استفاده می‌کنه.
    """
    vd_list = _build_visual_debug_prompt_list()
    lines = ["## 🔍 بازرس بصری هوشمند پروژه (Visual Inspector AI)\n"]
    for item in vd_list:
        icon = item.get("icon", "")
        title = item["title"]
        detail = item.get("prompt_detail", item["content"])
        lines.append(f"### {icon} {title}")
        lines.append(detail)
        lines.append("")
    prompt_text = "\n".join(lines)
    if general_instructions_text:
        prompt_text += f"\n\n{general_instructions_text}\n"
    prompt_text += """\n## فایل‌های پروژه (دسترسی کامل):
شما دسترسی کامل به تمام فایل‌های این پروژه دارید. سیستم به صورت هوشمند مرتبط‌ترین فایل‌ها را از کل مخزن پروژه انتخاب و خوانده و در زیر ارائه کرده است.
بر اساس این فایل‌ها تحلیل کنید و کد بنویسید. **همیشه** action_plan کامل بنویسید — هرگز نگویید «فایل در اختیارم نیست» یا «دوباره ارسال کنید»."""
    return prompt_text


@router.post("/inspector/visual-debug")
async def visual_debug_endpoint(request: VisualDebugRequest, db: Session = Depends(get_db)):
    """دیباگ بصری: ترکیب عکس‌ها + لاگ‌ها + توضیح کاربر و ارسال به مدل Vision. SSE streaming"""
    from fastapi.responses import StreamingResponse
    from ...models.project import Project
    from ...services.github_import import get_github_import_service
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}
    if not request.screenshots:
        return {"success": False, "error": "حداقل یک عکس لازم است"}

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from ...models.setting import Setting as _VDSetting
        token = _VDSetting.get_value(db, "api_key_github") or ""

    model_ids = request.model_ids
    if not model_ids:
        from ...core.models_registry import MODEL_REGISTRY, ModelCapability
        ai_mgr = get_ai_manager()
        for mid, m in MODEL_REGISTRY.items():
            has_vis = ModelCapability.VISION in m.capabilities or ModelCapability.IMAGE_ANALYSIS in m.capabilities or m.supports_images
            if has_vis and ai_mgr.get_enabled_status(mid):
                model_ids = [mid]
                break
        if not model_ids:
            model_ids = ["gpt-4o"]
    primary_model = model_ids[0]

    async def event_stream():
        ai_manager = get_ai_manager()
        github_svc = get_github_import_service()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield sse("progress", {"step": "starting", "message": f"🔍 شروع تحلیل بصری هوشمند با {len(request.screenshots)} عکس..."})
        yield sse("fields_in_use", {"field_ids": ["visual_debug_prompt"], "count": 1, "message": "📋 پرامپت بازرس بصری هوشمند فعال"})

        # ساخت دستورات عمومی برای تزریق در پرامپت بازرس بصری
        _vd_instructions_list = _build_general_instructions_list(
            project_name=project.name or "نامشخص",
            technologies=project.technologies or "نامشخص",
            github_path=f"{owner}/{repo}" if owner else "نامشخص"
        )
        _vd_general_text = _build_general_instructions_text(_vd_instructions_list)

        # ── بودجه‌بندی هوشمند بر اساس context window مدل ──
        from ...core.models_registry import get_model as _vd_get_model
        _vd_reg = _vd_get_model(primary_model)
        _vd_context_window = getattr(_vd_reg, 'context_window', 32000) if _vd_reg else 32000
        _vd_model_max_output = getattr(_vd_reg, 'max_tokens', 16384) if _vd_reg else 16384
        # بدون سقف مصنوعی — از ظرفیت واقعی مدل استفاده شود
        _vd_max_output = _vd_model_max_output

        # 🔑 تخمین حجم اسکرین‌شات‌ها (توکن)
        # Gemini/OpenAI: تصاویر به صورت image-part ارسال میشن ≈ 258-1292 توکن
        # ولی base64 داخل پرامپت خیلی سنگین‌تره — محافظه‌کارانه حساب کنیم
        _vd_screenshot_tokens = 0
        for _ss_b64 in (request.screenshots or [])[:10]:
            # هر عکس حداقل 5000 توکن (محافظه‌کارانه برای جلوگیری از سرریز)
            _vd_screenshot_tokens += max(5000, len(_ss_b64) // 40)
        slog.info("VD screenshot budget", count=len(request.screenshots or []), estimated_tokens=_vd_screenshot_tokens)

        # 🔑 حاشیه ایمنی بزرگ: ۲۵٪ context window
        _vd_safety_margin = max(10000, _vd_context_window // 4)

        # توکن‌های قابل استفاده برای ورودی
        _vd_available_tokens = _vd_context_window - _vd_max_output - _vd_screenshot_tokens - _vd_safety_margin
        _vd_max_input_chars = max(10000, _vd_available_tokens * 3)

        # 🔑 سقف عملی: حتی اگه context window بزرگه، بیشتر از 150K کاراکتر کد نخون
        # دلیل: ۱) مدل نمیتونه ۳۸ فایل رو معنادار پردازش کنه ۲) خروجی محدوده
        _VD_MAX_CODE_BUDGET = 150000  # 150K chars ≈ 50K tokens — عملی و قابل پردازش

        # تخمین فضای ثابت (پرامپت سیستم + دستورات عمومی + user description)
        _vd_prompt_overhead = len(_vd_general_text) + 5000
        _vd_user_estimate = min(10000, len(request.user_description or '') + 2000)

        # بودجه کد = حداقل(نظری, عملی)
        _vd_code_budget = min(
            _VD_MAX_CODE_BUDGET,
            max(10000, _vd_max_input_chars - _vd_prompt_overhead - _vd_user_estimate)
        )

        # تعداد فایل و سقف هر فایل — محدودیت عملی
        _vd_max_files = max(5, min(15, _vd_code_budget // 8000))  # حداکثر ۱۵ فایل (عملی)
        _vd_per_file_limit = max(3000, min(15000, _vd_code_budget // max(_vd_max_files, 1)))

        yield sse("progress", {"step": "budget", "message": f"📊 بودجه: {_vd_context_window // 1000}K ctx, 📸 {_vd_screenshot_tokens // 1000}K img, 📁 {_vd_max_files} فایل × {_vd_per_file_limit // 1000}K (کد: {_vd_code_budget // 1000}K)"})

        # ساخت پرامپت - اگر screenshot_packs موجود است، هر عکس را با لاگ‌های مربوطه ارسال کن
        user_parts = [f"## 📸 عکس‌های صفحه ({len(request.screenshots)} عکس)"]

        # Collect all API paths from all packs for file selection
        all_api_paths = []

        if request.screenshot_packs and len(request.screenshot_packs) == len(request.screenshots):
            # 📦 حالت Pack: هر عکس با لاگ‌ها و آدرس‌های مربوط به خودش
            for i, pack in enumerate(request.screenshot_packs):
                user_parts.append(f"\n### 📸 عکس {i+1} [تصویر ضمیمه شده]")
                pack_url = pack.get('pageUrl', '')
                if pack_url:
                    user_parts.append(f"🔗 آدرس صفحه: {pack_url}")
                pack_ts = pack.get('timestamp', '')
                if pack_ts:
                    user_parts.append(f"⏰ زمان عکس‌برداری: {pack_ts}")

                # لاگ‌های کنسول مربوط به این عکس
                pack_console = pack.get('console_logs', [])
                if pack_console:
                    user_parts.append(f"\n📋 لاگ‌های کنسول مرتبط با عکس {i+1} ({len(pack_console)} لاگ):")
                    for log in pack_console[-30:]:
                        user_parts.append(f"  [{log.get('level','log').upper()}] {log.get('message','')[:300]}")

                # لاگ‌های بک‌اند مربوط به این عکس
                pack_backend = pack.get('backend_logs', [])
                if pack_backend:
                    user_parts.append(f"\n🖥️ لاگ‌های بک‌اند مرتبط با عکس {i+1} ({len(pack_backend)} لاگ):")
                    for log in pack_backend[-20:]:
                        user_parts.append(f"  [{log.get('level','info').upper()}] {log.get('message','')[:300]}")

                # آدرس‌های مرتبط با این عکس
                pack_urls = pack.get('related_urls', [])
                if pack_urls:
                    user_parts.append(f"\n🔗 آدرس‌های مرتبط با عکس {i+1}:")
                    for url in pack_urls:
                        user_parts.append(f"  - {url}")

                # 🛤️ مسیرهای API بکند مرتبط با این عکس
                pack_api_paths = pack.get('api_paths', [])
                if pack_api_paths:
                    user_parts.append(f"\n🛤️ مسیرهای API بکند مرتبط با عکس {i+1}:")
                    for ap in pack_api_paths:
                        user_parts.append(f"  - {ap}")
                    all_api_paths.extend(pack_api_paths)

        else:
            # حالت قدیمی (بدون pack): عکس‌ها و لاگ‌ها جدا
            for i in range(len(request.screenshots)):
                user_parts.append(f"### عکس {i+1}: [تصویر ضمیمه شده]")

            if request.console_logs:
                user_parts.append(f"\n## 📋 لاگ‌های کنسول ({len(request.console_logs)} لاگ)")
                for log in request.console_logs[-50:]:
                    user_parts.append(f"[{log.get('level','log').upper()}] {log.get('message','')[:300]}")

            if request.backend_logs:
                user_parts.append(f"\n## 🖥️ لاگ‌های بک‌اند ({len(request.backend_logs)} لاگ)")
                for log in request.backend_logs[-30:]:
                    user_parts.append(f"[{log.get('level','info').upper()}] {log.get('message','')[:300]}")

        if request.related_urls:
            user_parts.append(f"\n## 🔗 آدرس‌های مرتبط (همه عکس‌ها)")
            for url in request.related_urls:
                user_parts.append(f"- {url}")

        if request.user_description:
            user_parts.append(f"\n## 💬 توضیح کاربر:\n{request.user_description}")

        user_text = "\n".join(user_parts)

        yield sse("progress", {"step": "analyzing", "message": f"🤖 مدل {primary_model} در حال تحلیل عکس‌ها و لاگ‌ها..."})

        # خواندن فایل‌های مرتبط
        project_tree_summary = ""
        code_context = ""
        if owner and repo:
            try:
                yield sse("progress", {"step": "reading_project", "message": "📂 خواندن ساختار پروژه..."})
                tree_result = await github_svc.get_repo_tree(owner, repo, token=token)
                if tree_result.get("success"):
                    all_files = [f for f in tree_result.get("tree", []) if f.get("type") == "blob"]
                    code_files = [f["path"] for f in all_files
                                  if _is_code_file(f["path"], file_size=f.get("size", 0))]
                    project_tree_summary = _build_project_tree_summary(code_files)

                    # 🆕 هوشمند: URL صفحه → فایل‌های فرانت مرتبط
                    _vd_url_files = []
                    _all_page_urls = []
                    if request.screenshot_packs:
                        for pack in request.screenshot_packs:
                            pu = pack.get('pageUrl', '')
                            if pu:
                                _all_page_urls.append(pu)
                    # تبدیل URL به مسیر فایل: /projects/123 → projects/[id]/page.tsx
                    for _pu in _all_page_urls:
                        try:
                            from urllib.parse import urlparse
                            parsed = urlparse(_pu)
                            pathname = parsed.path.strip("/")
                            if pathname:
                                # حذف segment های عددی/uuid و تبدیل به [id]
                                segments = pathname.split("/")
                                _patterns = []
                                for seg in segments:
                                    if re.match(r'^[0-9a-f\-]{8,}$', seg) or seg.isdigit():
                                        _patterns.append("[id]")
                                    else:
                                        _patterns.append(seg)
                                # ساخت الگوهای ممکن
                                _route_pattern = "/".join(_patterns)
                                _route_keywords = [s for s in segments if not s.isdigit() and not re.match(r'^[0-9a-f\-]{8,}$', s)]

                                for cf in code_files:
                                    cf_lower = cf.lower()
                                    # Next.js: app/route/page.tsx or pages/route.tsx
                                    if _route_pattern and _route_pattern.lower() in cf_lower:
                                        _vd_url_files.append(cf)
                                    # Keyword match: projects → projects/*, dashboard → dashboard/*
                                    elif any(kw.lower() in cf_lower for kw in _route_keywords if len(kw) > 2):
                                        if any(p in cf_lower for p in ['page.', 'index.', 'layout.', 'route.', 'view.', 'component']):
                                            _vd_url_files.append(cf)
                        except Exception:
                            pass

                    # 🆕 استخراج فایل‌ها از لاگ‌های خطا و متن
                    _all_log_text = user_text[:5000]
                    if request.user_description:
                        _all_log_text += "\n" + request.user_description
                    _log_extracted = _extract_file_paths_from_text(_all_log_text, code_files)

                    # 🆕 AI file selection (مثل smart-chat)
                    api_path_context = " ".join(all_api_paths) if all_api_paths else ""
                    _vd_context = (request.user_description or "") + " " + api_path_context
                    # _vd_max_files محاسبه شده از بودجه داینامیک مدل

                    yield sse("progress", {"step": "selecting_files", "message": f"🤖 مدل {primary_model} در حال انتخاب فایل‌های مرتبط..."})
                    try:
                        _vd_select_prompt = f"""بر اساس درخواست کاربر، عکس صفحه و مسیرهای API، فایل‌های مرتبط را انتخاب کن:

درخواست کاربر: {request.user_description or '(بدون توضیح)'}

آدرس صفحه‌ها: {', '.join(_all_page_urls) if _all_page_urls else 'نامشخص'}

مسیرهای API فعال: {chr(10).join(all_api_paths) if all_api_paths else 'نامشخص'}

{project_tree_summary}

فایل‌های پروژه:
{chr(10).join(code_files[:500])}

## راهنما:
- فایل‌های فرانت مرتبط با URL صفحه (page, layout, component)
- فایل‌های بکند مرتبط با API paths (route, service, model)
- فایل‌های استایل (CSS, Tailwind config)
- فایل‌های تایپ/اینترفیس مرتبط
- حداکثر {_vd_max_files} فایل. فقط مسیرها، هر کدام در یک خط."""

                        _vd_sel_resp = await ai_manager.generate(
                            model_id=primary_model,
                            messages=[
                                Message(role="system", content=f"انتخاب‌گر فایل هوشمند بصری. بر اساس URL صفحه و مسیرهای API، فایل‌های فرانت و بکند مرتبط را انتخاب کن. حداکثر {_vd_max_files} فایل. فقط مسیرها."),
                                Message(role="user", content=_vd_select_prompt)
                            ],
                            max_tokens=800,
                            temperature=0.2
                        )
                        selected_files = _parse_ai_selected_files(_vd_sel_resp.content, code_files, max_files=_vd_max_files)
                    except Exception:
                        selected_files = []

                    if not selected_files:
                        selected_files = _fallback_file_selection(code_files, _vd_context + " " + user_text[:2000], max_files=12)

                    # 🆕 ادغام فایل‌های URL-mapped و log-extracted
                    for _uf in (_vd_url_files + _log_extracted):
                        if _uf not in selected_files:
                            selected_files.insert(0, _uf)

                    # API path matching (بهبود یافته)
                    if all_api_paths:
                        api_keywords = set()
                        for ap in all_api_paths:
                            parts = [p for p in ap.strip('/').split('/') if p and p != 'api' and p != 'v1' and p != 'v2' and not p.isdigit()]
                            api_keywords.update(parts)
                        if api_keywords:
                            for cf in code_files:
                                if len(selected_files) >= _vd_max_files:
                                    break
                                cf_lower = cf.lower()
                                if any(kw.lower() in cf_lower for kw in api_keywords):
                                    if cf not in selected_files:
                                        selected_files.append(cf)

                    selected_files = _ensure_balanced_selection(selected_files, code_files, _vd_max_files)
                    # اولویت فایل‌های جدید بررسی‌نشده
                    prev_files = set(request.previously_read_files or [])
                    if prev_files:
                        new_files = [f for f in selected_files if f not in prev_files]
                        old_files = [f for f in selected_files if f in prev_files]
                        selected_files = (new_files + old_files)[:_vd_max_files]
                    _vd_file_contents = {}  # دیکشنری فایل‌های اصلی برای تشخیص بازنویسی مخرب
                    if selected_files:
                        yield sse("progress", {"step": "reading_files", "message": f"📖 خواندن {len(selected_files)} فایل (بودجه {_vd_code_budget // 1000}K)..."})
                        _vd_read_count = 0
                        for fp in selected_files:
                            if len(code_context) >= _vd_code_budget:
                                yield sse("progress", {"step": "budget_cap", "message": f"📊 بودجه کد پر شد ({len(code_context) // 1000}K) — {len(selected_files) - _vd_read_count} فایل باقیمانده نادیده گرفته شد"})
                                break
                            try:
                                file_result = await github_svc.get_file_content(owner, repo, fp, token=token)
                                if file_result.get("success"):
                                    _file_content = file_result.get('content', '')
                                    # سقف هر فایل: داینامیک بر اساس بودجه باقیمانده
                                    _remaining = _vd_code_budget - len(code_context)
                                    _this_limit = min(_vd_per_file_limit, max(3000, _remaining))
                                    # 🆕 اضافه کردن اندازه فایل و اخطار modify_sections برای فایل‌های بزرگ
                                    _vd_total_lines = len(_file_content.split("\n"))
                                    _vd_size_note = ""
                                    if _vd_total_lines > 200:
                                        _vd_size_note = f" ⚠️ فایل بزرگ ({_vd_total_lines} خط) — حتماً از modify_sections استفاده کن"
                                    _truncated_content = _file_content[:_this_limit]
                                    if len(_file_content) > _this_limit:
                                        _truncated_content += f"\n... [truncated — فایل اصلی {_vd_total_lines} خط{_vd_size_note}]"
                                    code_context += f"\n--- {fp} ({_vd_total_lines} خط){_vd_size_note} ---\n{_truncated_content}\n"
                                    _vd_file_contents[fp] = _file_content  # ذخیره برای مقایسه بازنویسی مخرب
                                    _vd_read_count += 1
                            except Exception:
                                pass
            except Exception as e:
                yield sse("progress", {"step": "github_error", "message": f"⚠️ خطا GitHub: {str(e)[:80]}"})

        full_system = _build_visual_debug_prompt_text(_vd_general_text)
        # لیست ساختاریافته فایل‌های پروژه (فرانت + بکند)
        if selected_files:
            full_system += f"\n\n## 📂 فایل‌های پروژه خوانده‌شده ({len(selected_files)} فایل از کل مخزن):\n"
            for sf in selected_files:
                full_system += f"  - `{sf}`\n"
        if all_api_paths:
            full_system += f"\n## 🛤️ مسیرهای API بکند فعال:\n"
            for ap in all_api_paths:
                full_system += f"  - `{ap}`\n"
        if project_tree_summary:
            full_system += f"\n\n## ساختار پروژه:\n{project_tree_summary}"
        if code_context:
            full_system += f"\n\n## کد فایل‌ها:\n{code_context[:_vd_code_budget]}"

        # ── بررسی نهایی: آیا کل ورودی (متن + عکس) در بودجه مدل جا میشه؟ ──
        _vd_text_tokens = (len(full_system) + len(user_text)) // 3
        _vd_total_input_tokens = _vd_text_tokens + _vd_screenshot_tokens
        _vd_safe_input_limit = _vd_context_window - _vd_max_output - max(500, _vd_context_window // 100)
        if _vd_total_input_tokens > _vd_safe_input_limit:
            # کد فایل‌ها در انتهای full_system هست — از انتها کوتاه کن
            _vd_excess_tokens = _vd_total_input_tokens - _vd_safe_input_limit
            _vd_trim_chars = _vd_excess_tokens * 3 + 3000  # اضافه‌تر حذف برای حاشیه ایمنی
            if _vd_trim_chars > 0 and len(full_system) > 10000:
                full_system = full_system[:max(10000, len(full_system) - _vd_trim_chars)] + "\n\n... [بخشی از فایل‌ها به دلیل محدودیت ظرفیت مدل حذف شد]"
                yield sse("progress", {"step": "prompt_truncation", "message": f"⚠️ ورودی ({_vd_total_input_tokens // 1000}K توکن) بیش از ظرفیت ({_vd_safe_input_limit // 1000}K) — {_vd_trim_chars // 1000}K حذف شد"})

        try:
            yield sse("progress", {"step": "sending_to_model", "message": f"📤 ارسال به {primary_model}..."})
            import time as _time
            messages = [
                Message(role="system", content=full_system),
                Message(role="user", content=user_text, images=request.screenshots[:10])
            ]
            response_task = asyncio.create_task(
                ai_manager.generate(model_id=primary_model, messages=messages, max_tokens=_vd_max_output, temperature=0.3, task_type="code_analysis")
            )
            while not response_task.done():
                yield sse("heartbeat", {"ts": int(_time.time())})
                await asyncio.sleep(8)
            response = response_task.result()
            # 🧹 حذف بلوک‌های استدلال/reasoning
            if response.content:
                response.content = _strip_reasoning_blocks(response.content)
            yield sse("fields_done", {"field_ids": ["visual_debug_prompt"]})

            # 🆕 تشخیص truncation
            _vd_finish = getattr(response, 'finish_reason', '') or ''
            _vd_is_truncated = _vd_finish.lower() in ('length', 'max_tokens')

            # 🆕 استخراج و ادغام تمام بلوک‌های JSON (پشتیبانی از بلوک‌های متعدد + تعمیر ناقص)
            action_plan = _extract_all_action_plans_from_response(response.content, is_truncated=_vd_is_truncated)

            # فالبک: استخراج از بلوک‌های کد + نام فایل
            if action_plan is None:
                code_blocks = re.findall(r'```[\w]*\n(.*?)```', response.content, re.DOTALL)
                if code_blocks:
                    action_plan = {"files": [], "commit_message": f"fix: دیباگ بصری - {(request.user_description or 'اصلاح')[:50]}"}
                    fpm = re.findall(r'(?:فایل|file|path|مسیر|`)[:\s]*[`"]?([a-zA-Z0-9_./\-]+(?:\.[a-zA-Z]{1,10}))[`"]?', response.content)
                    fpm = [p for p in fpm if '/' in p or '.' in p.split('/')[-1]]
                    for i, block in enumerate(code_blocks[:5]):
                        action_plan["files"].append({"path": fpm[i] if i < len(fpm) else f"file_{i+1}", "content": block.strip(), "operation": "modify"})
                    if all(f["path"].startswith("file_") for f in action_plan["files"]):
                        action_plan = None

            # هشدار truncation به کاربر
            if _vd_is_truncated:
                _n_files = len(action_plan.get('files', [])) if action_plan else 0
                if action_plan:
                    response.content += f"\n\n---\n⚠️ **هشدار:** پاسخ مدل ناقص بود — {_n_files} فایل از action_plan نجات یافت."
                else:
                    response.content += "\n\n---\n⚠️ **هشدار:** پاسخ مدل به دلیل محدودیت خروجی ناقص قطع شد. لطفاً با مدل دیگری تلاش کنید."

            yield sse("response", {
                "content": response.content, "model_used": primary_model,
                "tokens_used": getattr(response, 'tokens_used', 0) or 0,
                "type": "visual_debug", "screenshots_count": len(request.screenshots),
                "action_plan": _validate_action_plan_syntax(action_plan, original_files=_vd_file_contents, repo_file_paths=_normalize_repo_paths(locals().get("all_files")), user_message=getattr(request, "message", "") or getattr(request, "user_request", "") or "", backend_logs=getattr(request, "backend_logs", None), code_files=locals().get("code_files")) if action_plan else None, "has_action": action_plan is not None,
                "truncated": _vd_is_truncated,
            })
        except Exception as e:
            yield sse("error", {"message": f"خطا: {str(e)[:200]}", "detail": type(e).__name__})

        yield sse("done", {"success": True})

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


# ────────────────────────────────────────────────
# 🔄 بازتحلیل دیباگ بصری با مدل دوم
# ────────────────────────────────────────────────

class VisualDebugReanalyzeRequest(BaseModel):
    """درخواست بازتحلیل گزارش دیباگ بصری با مدل دیگر"""
    project_id: str
    model_id: str  # مدل جدید برای بازتحلیل
    vision_report: str  # گزارش کامل مدل Vision (متن)
    vision_model_id: str  # مدل Vision اولیه
    vision_action_plan: Optional[dict] = None  # action_plan مدل Vision (اگر موجود)
    user_description: Optional[str] = None  # توضیح اصلی کاربر
    previously_read_files: Optional[List[str]] = None


@router.post("/inspector/visual-debug-reanalyze")
async def visual_debug_reanalyze_endpoint(request: VisualDebugReanalyzeRequest, db: Session = Depends(get_db)):
    """بازتحلیل گزارش مدل Vision توسط مدل دوم: خواندن فایل‌ها + بررسی مستقل + گزارش نهایی. SSE streaming"""
    from fastapi.responses import StreamingResponse
    from ...models.project import Project
    from ...services.github_import import get_github_import_service
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}
    if not request.vision_report:
        return {"success": False, "error": "گزارش مدل Vision خالی است"}

    extra_data = {}
    if project.extra_data:
        try:
            extra_data = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
        except Exception:
            extra_data = {}

    owner = extra_data.get("owner", "")
    repo = extra_data.get("repo", "")
    github_path = project.github_path or ""
    if not owner and "/" in github_path:
        owner, repo = github_path.split("/", 1)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from ...models.setting import Setting as _RASetting
        token = _RASetting.get_value(db, "api_key_github") or ""

    reanalyze_model = request.model_id

    async def event_stream():
        ai_manager = get_ai_manager()
        github_svc = get_github_import_service()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield sse("progress", {"step": "starting", "message": f"🔄 شروع بازتحلیل با مدل {reanalyze_model}..."})

        # دستورات عمومی
        _ra_instructions_list = _build_general_instructions_list(
            project_name=project.name or "نامشخص",
            technologies=project.technologies or "نامشخص",
            github_path=f"{owner}/{repo}" if owner else "نامشخص"
        )
        _ra_general_text = _build_general_instructions_text(_ra_instructions_list)

        # بودجه‌بندی بر اساس مدل جدید — با حد عملی
        from ...core.models_registry import get_model as _ra_get_model
        _ra_reg = _ra_get_model(reanalyze_model)
        _ra_context_window = getattr(_ra_reg, 'context_window', 32000) if _ra_reg else 32000
        _ra_model_max_output = getattr(_ra_reg, 'max_tokens', 16384) if _ra_reg else 16384
        _ra_max_output = _ra_model_max_output
        _ra_safety = max(10000, _ra_context_window // 4)
        _ra_max_input_chars = max(10000, (_ra_context_window - _ra_max_output - _ra_safety) * 3)

        # 🆕 محاسبه حجم واقعی vision_action_plan (قبلاً حساب نمی‌شد → سرریز)
        _ra_action_plan_size = 0
        if request.vision_action_plan:
            try:
                _ra_action_plan_size = min(5000, len(json.dumps(request.vision_action_plan, ensure_ascii=False)))
            except Exception:
                _ra_action_plan_size = 3000
        _ra_prompt_overhead = len(_ra_general_text) + len(request.vision_report) + _ra_action_plan_size + 5000
        _ra_user_estimate = min(5000, len(request.user_description or '') + 1000 + _ra_action_plan_size)
        _ra_code_budget = min(
            150000,  # سقف عملی
            max(10000, _ra_max_input_chars - _ra_prompt_overhead - _ra_user_estimate)
        )

        # بودجه reanalyze: فایل‌های کمتر با محتوای بیشتر (مدل باید متن واقعی ببینه برای modify_sections)
        _ra_max_files = max(3, min(10, _ra_code_budget // 15000))
        _ra_per_file_limit = max(5000, min(30000, _ra_code_budget // max(_ra_max_files, 1)))

        yield sse("progress", {"step": "budget", "message": f"📊 بودجه: {_ra_context_window // 1000}K context → {_ra_max_files} فایل, {_ra_per_file_limit // 1000}K/فایل"})

        # خواندن فایل‌های پروژه
        project_tree_summary = ""
        code_context = ""
        selected_files = []

        if owner and repo:
            try:
                yield sse("progress", {"step": "reading_project", "message": "📂 خواندن ساختار پروژه..."})
                tree_result = await github_svc.get_repo_tree(owner, repo, token=token)
                if tree_result.get("success"):
                    all_files = [f for f in tree_result.get("tree", []) if f.get("type") == "blob"]
                    code_files = [f["path"] for f in all_files
                                  if _is_code_file(f["path"], file_size=f.get("size", 0))]
                    project_tree_summary = _build_project_tree_summary(code_files)

                    # استخراج فایل‌ها از گزارش Vision و action_plan
                    _ra_report_files = _extract_file_paths_from_text(request.vision_report, code_files)

                    if request.vision_action_plan and request.vision_action_plan.get("files"):
                        for af in request.vision_action_plan["files"]:
                            ap = af.get("path", "")
                            if ap and ap in code_files and ap not in _ra_report_files:
                                _ra_report_files.append(ap)

                    # AI file selection با context گزارش
                    _ra_context = (request.user_description or "") + " " + request.vision_report[:3000]

                    yield sse("progress", {"step": "selecting_files", "message": f"🤖 مدل {reanalyze_model} در حال انتخاب فایل‌های مرتبط..."})
                    try:
                        _ra_select_prompt = f"""بر اساس گزارش مدل Vision زیر، فایل‌های مرتبط را برای بررسی مستقل انتخاب کن:

## گزارش مدل Vision ({request.vision_model_id}):
{request.vision_report[:4000]}

## توضیح اصلی کاربر:
{request.user_description or '(بدون توضیح)'}

{project_tree_summary}

فایل‌های پروژه:
{chr(10).join(code_files[:500])}

## راهنما:
- فایل‌هایی که در گزارش Vision ذکر شده (مسیرهای دقیق)
- فایل‌های مرتبط دیگر برای بررسی کامل
- فایل‌های فرانت و بکند مرتبط
- حداکثر {_ra_max_files} فایل. فقط مسیرها، هر کدام در یک خط."""

                        _ra_sel_resp = await ai_manager.generate(
                            model_id=reanalyze_model,
                            messages=[
                                Message(role="system", content=f"انتخاب‌گر فایل هوشمند. بر اساس گزارش Vision، فایل‌های فرانت و بکند مرتبط را انتخاب کن. حداکثر {_ra_max_files} فایل. فقط مسیرها."),
                                Message(role="user", content=_ra_select_prompt)
                            ],
                            max_tokens=800,
                            temperature=0.2
                        )
                        selected_files = _parse_ai_selected_files(_ra_sel_resp.content, code_files, max_files=_ra_max_files)
                    except Exception:
                        selected_files = []

                    if not selected_files:
                        selected_files = _fallback_file_selection(code_files, _ra_context[:3000], max_files=12)

                    # ادغام فایل‌های استخراج‌شده از گزارش
                    for _rf in _ra_report_files:
                        if _rf not in selected_files:
                            selected_files.insert(0, _rf)

                    selected_files = _ensure_balanced_selection(selected_files, code_files, _ra_max_files)

                    # اولویت فایل‌های جدید
                    prev_files = set(request.previously_read_files or [])
                    if prev_files:
                        new_files = [f for f in selected_files if f not in prev_files]
                        old_files = [f for f in selected_files if f in prev_files]
                        selected_files = (new_files + old_files)[:_ra_max_files]

                    _ra_file_contents = {}  # دیکشنری فایل‌های اصلی برای تشخیص بازنویسی مخرب
                    # فایل‌های action_plan (اولویت بالا) — مدل باید محتوای کامل‌تر ببینه
                    _ra_priority_files = set(_ra_report_files)
                    if request.vision_action_plan and request.vision_action_plan.get("files"):
                        for _apf in request.vision_action_plan["files"]:
                            _apfp = _apf.get("path", "")
                            if _apfp:
                                _ra_priority_files.add(_apfp)
                    if selected_files:
                        yield sse("progress", {"step": "reading_files", "message": f"📖 خواندن {len(selected_files)} فایل (بودجه {_ra_code_budget // 1000}K, فایل‌های اولویت: {len(_ra_priority_files)})"})
                        _ra_read_count = 0
                        for fp in selected_files:
                            if len(code_context) >= _ra_code_budget:
                                yield sse("progress", {"step": "budget_cap", "message": f"📊 بودجه کد پر شد — {len(selected_files) - _ra_read_count} فایل نادیده گرفته شد"})
                                break
                            try:
                                file_result = await github_svc.get_file_content(owner, repo, fp, token=token)
                                if file_result.get("success"):
                                    _file_content = file_result.get('content', '')
                                    _remaining = _ra_code_budget - len(code_context)
                                    # فایل‌های اولویت‌دار بودجه ۲ برابر دارن (نیاز به دیدن کامل برای modify_sections)
                                    if fp in _ra_priority_files:
                                        _this_limit = min(_ra_per_file_limit * 2, max(5000, _remaining))
                                    else:
                                        _this_limit = min(_ra_per_file_limit, max(3000, _remaining))
                                    _ra_total_lines = len(_file_content.split("\n"))
                                    _ra_size_note = ""
                                    if _ra_total_lines > 200:
                                        _ra_size_note = f" ⚠️ فایل بزرگ — حتماً از modify_sections استفاده کن"
                                    _truncated_content = _file_content[:_this_limit]
                                    if len(_file_content) > _this_limit:
                                        _truncated_content += f"\n... [truncated — فایل اصلی {_ra_total_lines} خط{_ra_size_note}]"
                                    code_context += f"\n--- {fp} ({_ra_total_lines} خط) ---\n{_truncated_content}\n"
                                    _ra_file_contents[fp] = _file_content
                                    _ra_read_count += 1
                            except Exception:
                                pass
            except Exception as e:
                yield sse("progress", {"step": "github_error", "message": f"⚠️ خطا GitHub: {str(e)[:80]}"})

        # ساخت پرامپت سیستم
        full_system = _ra_general_text
        full_system += f"""

## 🔄 بازتحلیل مستقل گزارش مدل Vision

### وظیفه شما:
مدل Vision ({request.vision_model_id}) عکس‌های صفحه را بررسی کرده و گزارش زیر را تولید کرده.
شما باید:
1. گزارش مدل Vision را کامل و دقیق بخوانید
2. فایل‌های ذکرشده را خودتان بررسی کنید (فایل‌ها در زیر ارائه شده‌اند)
3. تحلیل مستقل خودتان را انجام دهید و اگر اشتباهی در گزارش Vision هست اصلاح کنید
4. گزارش نهایی و دقیق با action_plan کامل تولید کنید

### 🔑 دسترسی کامل به پروژه:
شما دسترسی کامل به تمام فایل‌های این پروژه دارید. سیستم مرتبط‌ترین فایل‌ها را خوانده و ارائه کرده.

### فرمت action_plan (ضروری):
حتماً در پایان گزارش، **یک** بلوک JSON با فرمت زیر قرار بدهید. تمام فایل‌ها و محتوا/sections باید **داخل** همین JSON باشد:

فرمت ۱ — modify/create (محتوای کامل):
```json
{{
  "files": [
    {{"path": "مسیر/فایل", "content": "محتوای کامل فایل", "operation": "modify"}}
  ],
  "commit_message": "توضیح تغییرات"
}}
```

فرمت ۲ — modify_sections (فقط بخش‌های تغییریافته — ویژه فایل‌های بزرگ >200 خط):
```json
{{
  "files": [
    {{"path": "مسیر/فایل-بزرگ.tsx", "operation": "modify_sections", "sections": [
      {{"find": "متن دقیق کپی‌شده از فایل اصلی", "replace": "متن جایگزین"}}
    ]}}
  ],
  "commit_message": "توضیح تغییرات"
}}
```

⚠️ **قوانین مهم action_plan**:
- **تمام** فایل‌ها و محتوا/sections باید **داخل** یک بلوک JSON باشد — هرگز content رو جدا از JSON ننویس
- 🔴🔴🔴 `find` باید **COPY-PASTE دقیق** از متن فایل اصلی باشد — شامل فاصله‌ها، tab ها و کامنت‌ها
- ⛔ **هرگز find رو حدس نزن یا از حافظه بنویس** — حتماً از متن فایل COPY کن
- ⛔ حتی ۱ کاراکتر فرق = section شکست میخوره و تغییرات اعمال نمیشه
- ✅ find حداقل ۲-۳ خط کامل و یکتا باشه — اگر مطمئن نیستی، ۵-۱۰ خط بگیر
- ❌ غلط: `"find": "// انتهای فایل — قبل از export"` (این توصیف است، نه کد واقعی!)
- ✅ صحیح: `"find": "export default MonitoringPage;"` (این متن واقعی فایل است)

🚨🚨🚨 **قانون اجباری modify_sections — عدم رعایت = حذف خودکار فایل**:
- سیستم تعداد خطوط هر فایل را در هدر (`--- فایل (N خط)`) نوشته — آن عدد را ببین!
- ⛔ فایل بالای ۲۰۰ خط + operation: "modify" = **سیستم خودکار فایل را حذف میکند**
- ⛔ فایل بالای ۸۰ خط + content کمتر از ۵۰٪ اصل = **سیستم خودکار فایل را حذف میکند**
- ✅ فایل بالای ۲۰۰ خط → **باید** از `modify_sections` استفاده شود
- ✅ فایل زیر ۲۰۰ خط → از `modify` با content کامل استفاده شود

### ⚠️ مدیریت بودجه خروجی:
- فایل‌های کوچک (<200 خط): از modify با content کامل استفاده کن
- فایل‌های بزرگ (>200 خط): **اجباری** از modify_sections — فقط بخش‌های تغییریافته
- 🔴 ترتیب: اول فایل‌های **جدید** (create) و **کوچک** را بنویس، بعد فایل‌های بزرگ‌تر
- 🔴 اگر فایل‌ها زیادند (بیش از ۵)، تحلیل متنی کوتاه بنویس و action_plan فقط مهم‌ترین فایل‌ها

### 🛡️ ممنوعیت بازنویسی مخرب (حیاتی):
- ⛔ هرگز فایل موجود پروژه را از صفر بازننویس — فقط بخش‌های مربوط به درخواست کاربر تغییر کنند
- ⛔ هرگز قابلیت‌های موجود فایل (state, event handlers, API calls, UI sections, styles) را حذف نکن
- ⛔ اگر فایل ۳۰۰ خط دارد و تو ۲۰ خط تغییر میدی → از modify_sections با ۳-۵ section استفاده کن (نه ۳۰۰ خط content)
- ⛔ هرگز عملکرد واقعی (iframe, chart, widget فعال) را با placeholder خالی جایگزین نکن
- ⛔ قبل از create فایل جدید → بررسی کن آیا کامپوننت مشابه در ساختار پروژه وجود داره (ساختار پروژه بالا آمده)

### 🎯 فهم دقیق درخواست کاربر (حیاتی):
- کلمات کاربر را **تحت‌اللفظی** بخوان: «فقط» = ONLY، «نباید» = MUST NOT، «اضافه کن» = بدون حذف موارد موجود
- ❌ اگر کاربر بگه «ویجت فقط در صفحه X باشه» → هرگز آن را global در همه صفحات نکن
- ❌ اگر کاربر بگه «ارتفاع رو کم کن» → فقط height تغییر بده، نه کل کامپوننت از صفر

### 🔄 قوانین ویژه بازتحلیل (بسیار حیاتی):

🔴 **قانون شماره ۱: ابتدا درخواست اصلی کاربر رو بخون — بالای پیام آمده**
- قبل از هر کاری، درخواست اصلی کاربر را دقیقاً بخوان (بخش «🎯 درخواست اصلی کاربر» در بالای پیام)
- **معیار صحت هر تصمیم: آیا مستقیماً به درخواست کاربر مربوط است؟**
- اگر مدل Vision کاری انجام داده که مستقیماً به درخواست کاربر مربوط است → **تأیید کن و تغییر نده**
- اگر مدل Vision چیزی انجام داده که به درخواست کاربر ربطی ندارد → آن بخش را اصلاح کن

🔴 **قانون شماره ۲: هرگز کار درست مدل قبلی رو برعکس نکن**
- ❌ اگر کاربر خواسته «ارتباط شورای AI با ویجت» و مدل Vision store شورای AI ساخته → **صحیح است** — برعکسش نکن
- ❌ اگر مدل Vision فایل‌های درست تغییر داده → آن‌ها رو حذف نکن و فایل‌های نامربوط جایگزین نکن
- ❌ هرگز یک تفسیر متفاوت (ولی غلط) از درخواست کاربر ارائه نده فقط به خاطر «متفاوت بودن»

🔴 **قانون شماره ۳: action_plan مدل قبلی رو حفظ + تکمیل کن**
- ✅ اگر action_plan مدل Vision فایل‌های صحیح دارد → آن‌ها رو نگه‌دار و اگر نیاز هست تکمیل کن
- ✅ اگر فایلی کم است → اضافه کن. اگر فایلی اضافی است → حذف کن. ولی فایل‌های صحیح رو دست نزن
- ❌ هرگز کل action_plan رو دور بینداز و از صفر بنویس — مگر واقعاً همه فایل‌ها غلط باشن"""

        if selected_files:
            full_system += f"\n\n## 📂 فایل‌های پروژه خوانده‌شده ({len(selected_files)} فایل):\n"
            for sf in selected_files:
                full_system += f"  - `{sf}`\n"
        if project_tree_summary:
            full_system += f"\n\n## ساختار پروژه:\n{project_tree_summary}"
        if code_context:
            full_system += f"\n\n## کد فایل‌ها:\n{code_context[:_ra_code_budget]}"

        # پرامپت کاربر: گزارش Vision + توضیح اصلی
        # 🔑 درخواست اصلی کاربر باید اول باشه تا مدل بازتحلیل آن را فراموش نکنه
        user_text = ""
        if request.user_description:
            user_text += f"""## 🎯 درخواست اصلی کاربر (مهم‌ترین بخش — تمام تصمیمات باید بر اساس این باشد):
**«{request.user_description}»**

⚠️ معیار صحت: آیا هر تغییر مستقیماً به این درخواست مربوط است؟ اگر نه → آن تغییر غلط است.

"""
        user_text += f"""## 📋 گزارش مدل Vision ({request.vision_model_id}):

{request.vision_report}
"""
        if request.vision_action_plan:
            user_text += f"""
## 📦 action_plan پیشنهادی مدل Vision:
```json
{json.dumps(request.vision_action_plan, ensure_ascii=False, indent=2)[:5000]}
```
"""

        user_text += """
## 📝 دستور:
گزارش مدل Vision را بخوانید، فایل‌های ارائه‌شده را بررسی کنید، و گزارش نهایی مستقل خودتان را با action_plan کامل (شامل محتوای کامل فایل‌ها) تولید کنید.
اگر تحلیل مدل Vision درست بود، آن را تأیید و تکمیل کنید. اگر اشتباهاتی دارد، اصلاح کنید."""

        # بررسی بودجه نهایی
        _ra_total_len = len(full_system) + len(user_text)
        if _ra_total_len > _ra_max_input_chars:
            _ra_allowed_system = max(10000, _ra_max_input_chars - len(user_text) - 1000)
            if len(full_system) > _ra_allowed_system:
                full_system = full_system[:_ra_allowed_system] + "\n\n... [بخشی از فایل‌ها حذف شد]"
                yield sse("progress", {"step": "prompt_truncation", "message": f"⚠️ حجم پرامپت ({_ra_total_len // 1000}K) بهینه‌سازی شد"})

        try:
            yield sse("progress", {"step": "sending_to_model", "message": f"📤 ارسال به {reanalyze_model}..."})
            import time as _time
            messages = [
                Message(role="system", content=full_system),
                Message(role="user", content=user_text)
            ]
            response_task = asyncio.create_task(
                ai_manager.generate(model_id=reanalyze_model, messages=messages, max_tokens=_ra_max_output, temperature=0.3, task_type="code_analysis")
            )
            while not response_task.done():
                yield sse("heartbeat", {"ts": int(_time.time())})
                await asyncio.sleep(8)
            response = response_task.result()
            # 🧹 حذف بلوک‌های استدلال/reasoning
            if response.content:
                response.content = _strip_reasoning_blocks(response.content)

            # 🆕 تشخیص truncation — آیا پاسخ مدل ناقص قطع شده؟
            _ra_finish = getattr(response, 'finish_reason', '') or ''
            _ra_is_truncated = _ra_finish.lower() in ('length', 'max_tokens')

            # 🆕 استخراج و ادغام تمام بلوک‌های JSON (برخی مدل‌ها action_plan رو تکه‌تکه میدن)
            action_plan = _extract_all_action_plans_from_response(response.content, is_truncated=_ra_is_truncated)

            # فالبک: استخراج از بلوک‌های کد + نام فایل
            if action_plan is None:
                code_blocks = re.findall(r'```[\w]*\n(.*?)```', response.content, re.DOTALL)
                if code_blocks:
                    action_plan = {"files": [], "commit_message": f"fix: بازتحلیل - {(request.user_description or 'اصلاح')[:50]}"}
                    fpm = re.findall(r'(?:فایل|file|path|مسیر|`)[:\s]*[`"]?([a-zA-Z0-9_./\-]+(?:\.[a-zA-Z]{1,10}))[`"]?', response.content)
                    fpm = [p for p in fpm if '/' in p or '.' in p.split('/')[-1]]
                    for i, block in enumerate(code_blocks[:5]):
                        action_plan["files"].append({"path": fpm[i] if i < len(fpm) else f"file_{i+1}", "content": block.strip(), "operation": "modify"})
                    if all(f["path"].startswith("file_") for f in action_plan["files"]):
                        action_plan = None

            # هشدار truncation به کاربر
            if _ra_is_truncated:
                _ra_n_files = len(action_plan.get('files', [])) if action_plan else 0
                if action_plan:
                    response.content += f"\n\n---\n⚠️ **هشدار:** پاسخ مدل به دلیل محدودیت خروجی ({_ra_max_output} توکن) ناقص بود. {_ra_n_files} فایل از action_plan نجات یافت — ممکن است برخی فایل‌ها ناقص یا غایب باشند."
                else:
                    response.content += f"\n\n---\n⚠️ **هشدار:** پاسخ مدل به دلیل محدودیت خروجی ({_ra_max_output} توکن) ناقص قطع شد و action_plan کامل نشد. لطفاً با مدل دیگری دوباره تلاش کنید یا درخواست را ساده‌تر کنید."

            yield sse("response", {
                "content": response.content, "model_used": reanalyze_model,
                "tokens_used": getattr(response, 'tokens_used', 0) or 0,
                "type": "visual_debug_reanalyze", "vision_model": request.vision_model_id,
                "action_plan": _validate_action_plan_syntax(action_plan, original_files=_ra_file_contents, repo_file_paths=_normalize_repo_paths(locals().get("all_files")), user_message=getattr(request, "message", "") or getattr(request, "user_request", "") or "", backend_logs=getattr(request, "backend_logs", None), code_files=locals().get("code_files")) if action_plan else None, "has_action": action_plan is not None,
                "truncated": _ra_is_truncated,
            })
        except Exception as e:
            yield sse("error", {"message": f"خطا: {str(e)[:200]}", "detail": type(e).__name__})

        yield sse("done", {"success": True})

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


# ============================================================
# 🆕 Phase 2 — Render mutation endpoints (Inspector independence)
# ============================================================

class _RenderEnvVarRequest(BaseModel):
    service_id: str
    key: str
    value: str


class _RenderEnvVarsBulkRequest(BaseModel):
    service_id: str
    vars: Dict[str, str]


class _RenderServiceActionRequest(BaseModel):
    service_id: str
    clear_cache: Optional[bool] = False


@router.get("/inspector/render/env-vars/{service_id}")
async def inspector_render_get_env_vars(service_id: str):
    """دریافت لیست متغیرهای محیطی یک سرویس Render."""
    if not service_id or not service_id.startswith("srv-"):
        raise HTTPException(status_code=400, detail="service_id نامعتبر است")
    svc = get_render_service()
    return await svc.get_env_vars(service_id)


@router.post("/inspector/render/env-var")
async def inspector_render_set_env_var(payload: _RenderEnvVarRequest):
    """تنظیم/به‌روزرسانی یک متغیر محیطی."""
    if not payload.service_id.startswith("srv-"):
        raise HTTPException(status_code=400, detail="service_id نامعتبر است")
    if not payload.key:
        raise HTTPException(status_code=400, detail="کلید env_var لازم است")
    svc = get_render_service()
    return await svc.set_env_var(payload.service_id, payload.key, payload.value)


@router.post("/inspector/render/env-vars/bulk")
async def inspector_render_set_env_vars_bulk(payload: _RenderEnvVarsBulkRequest):
    """تنظیم چندین متغیر محیطی به‌طور همزمان."""
    if not payload.service_id.startswith("srv-"):
        raise HTTPException(status_code=400, detail="service_id نامعتبر است")
    if not payload.vars:
        raise HTTPException(status_code=400, detail="هیچ متغیری ارائه نشده")
    svc = get_render_service()
    return await svc.set_env_vars_bulk(payload.service_id, payload.vars)


@router.post("/inspector/render/restart")
async def inspector_render_restart(payload: _RenderServiceActionRequest):
    """ری‌استارت یک سرویس Render."""
    if not payload.service_id.startswith("srv-"):
        raise HTTPException(status_code=400, detail="service_id نامعتبر است")
    svc = get_render_service()
    return await svc.restart_service(payload.service_id)


@router.post("/inspector/render/deploy")
async def inspector_render_deploy(payload: _RenderServiceActionRequest):
    """آغاز دیپلوی جدید برای یک سرویس Render."""
    if not payload.service_id.startswith("srv-"):
        raise HTTPException(status_code=400, detail="service_id نامعتبر است")
    svc = get_render_service()
    return await svc.trigger_deploy(payload.service_id, clear_cache=bool(payload.clear_cache))


# ============================================================
# 🆕 Phase 3 — Telegram bot setup automation
# ============================================================

class _TelegramBotSetupRequest(BaseModel):
    bot_token: str
    webhook_url: Optional[str] = None
    set_commands: Optional[bool] = True


@router.post("/inspector/setup-telegram-bot")
async def inspector_setup_telegram_bot(payload: _TelegramBotSetupRequest):
    """راه‌اندازی خودکار ربات تلگرام: اعتبارسنجی توکن، تنظیم webhook، و دستورها.

    مراحل:
    1. getMe → اعتبارسنجی توکن و دریافت اطلاعات ربات
    2. setWebhook (اگر webhook_url داده شده باشد)
    3. setMyCommands (اگر set_commands=True)
    """
    bot_token = (payload.bot_token or "").strip()
    if not bot_token or ":" not in bot_token:
        raise HTTPException(status_code=400, detail="توکن ربات نامعتبر است")

    result: Dict[str, Any] = {
        "success": False,
        "validated": False,
        "bot_info": None,
        "webhook_set": False,
        "commands_set": False,
        "errors": [],
    }

    base = f"https://api.telegram.org/bot{bot_token}"

    try:
        import aiohttp as _aiohttp
        timeout = _aiohttp.ClientTimeout(total=15)
        async with _aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{base}/getMe") as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("ok"):
                        result["validated"] = True
                        result["bot_info"] = data.get("result", {})
                    else:
                        result["errors"].append(f"getMe failed: {data.get('description', 'unknown')}")
                        return result
            except Exception as e:
                result["errors"].append(f"getMe exception: {str(e)[:200]}")
                return result

            if payload.webhook_url:
                wh = payload.webhook_url.strip()
                if not wh.startswith("https://"):
                    result["errors"].append("webhook_url باید با https:// شروع شود")
                else:
                    try:
                        async with session.post(f"{base}/setWebhook", json={"url": wh, "drop_pending_updates": False}) as resp:
                            data = await resp.json()
                            if resp.status == 200 and data.get("ok"):
                                result["webhook_set"] = True
                                result["webhook_url"] = wh
                            else:
                                result["errors"].append(f"setWebhook failed: {data.get('description', 'unknown')}")
                    except Exception as e:
                        result["errors"].append(f"setWebhook exception: {str(e)[:200]}")

            if payload.set_commands:
                commands = [
                    {"command": "start", "description": "شروع و راهنما"},
                    {"command": "help", "description": "راهنما"},
                    {"command": "menu", "description": "منوی اصلی"},
                    {"command": "create", "description": "ساخت پروژه جدید"},
                    {"command": "my_projects", "description": "پروژه‌های من"},
                    {"command": "status", "description": "وضعیت سیستم"},
                    {"command": "cancel", "description": "لغو عملیات جاری"},
                ]
                try:
                    async with session.post(f"{base}/setMyCommands", json={"commands": commands}) as resp:
                        data = await resp.json()
                        if resp.status == 200 and data.get("ok"):
                            result["commands_set"] = True
                            result["commands_count"] = len(commands)
                        else:
                            result["errors"].append(f"setMyCommands failed: {data.get('description', 'unknown')}")
                except Exception as e:
                    result["errors"].append(f"setMyCommands exception: {str(e)[:200]}")
    except Exception as e:
        result["errors"].append(f"global exception: {str(e)[:200]}")

    result["success"] = result["validated"] and (not payload.webhook_url or result["webhook_set"]) and (not payload.set_commands or result["commands_set"])
    return result


@router.get("/inspector/telegram-bot/info")
async def inspector_telegram_bot_info(bot_token: str = Query(...)):
    """بازیابی اطلاعات ربات و وضعیت webhook فعلی."""
    bot_token = (bot_token or "").strip()
    if not bot_token or ":" not in bot_token:
        raise HTTPException(status_code=400, detail="توکن ربات نامعتبر است")

    base = f"https://api.telegram.org/bot{bot_token}"
    out: Dict[str, Any] = {"success": False, "bot_info": None, "webhook_info": None, "errors": []}

    try:
        import aiohttp as _aiohttp
        timeout = _aiohttp.ClientTimeout(total=15)
        async with _aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{base}/getMe") as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("ok"):
                        out["bot_info"] = data.get("result", {})
                    else:
                        out["errors"].append(f"getMe: {data.get('description', 'unknown')}")
            except Exception as e:
                out["errors"].append(f"getMe exception: {str(e)[:200]}")

            try:
                async with session.get(f"{base}/getWebhookInfo") as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("ok"):
                        out["webhook_info"] = data.get("result", {})
                    else:
                        out["errors"].append(f"getWebhookInfo: {data.get('description', 'unknown')}")
            except Exception as e:
                out["errors"].append(f"getWebhookInfo exception: {str(e)[:200]}")
    except Exception as e:
        out["errors"].append(f"global exception: {str(e)[:200]}")

    out["success"] = out["bot_info"] is not None
    return out


# ============================================================
# 🆕 (inspector-scan) Endpointهای اسکن موردی Inspector
# ============================================================

class InspectorScanProgressResponse(BaseModel):
    """پاسخ progress برای polling از UI."""
    pass


@router.get("/inspector/selective-scan/{session_id}/progress")
async def inspector_selective_scan_progress(session_id: int):
    """progress جاری scan موردی در یک session.

    UI با polling هر ۲ ثانیه این endpoint را می‌خواند. وقتی status=completed،
    آخرین scan_complete message شامل proposals است که UI با reload messages
    از مسیر معمول /sessions/{id}/messages می‌خواند.
    """
    from ...services.inspector_scan_bridge import read_inspector_scan_progress
    return read_inspector_scan_progress(session_id)


@router.post("/inspector/selective-scan/{session_id}/cancel")
async def inspector_selective_scan_cancel(session_id: int):
    """🆕 (v3 UX) — لغو scan موردی فعال برای یک session.

    UI این endpoint را وقتی کاربر روی «✕ لغو scan» می‌زند صدا می‌کند.
    background task با asyncio.CancelledError متوقف می‌شود و یک پیام
    scan_cancelled در session لاگ می‌شود.
    """
    from ...services.inspector_scan_bridge import cancel_inspector_scan
    cancelled = cancel_inspector_scan(session_id)
    return {"success": cancelled, "session_id": session_id}


@router.get("/inspector/selective-scan/{session_id}/debug")
async def inspector_selective_scan_debug(session_id: int):
    """🆕 (v3 diagnostic) — نمایش وضعیت دقیق scan + آخرین messages.

    این endpoint برای debug است وقتی scan تمام می‌شود ولی هیچ پیامی
    در chat ظاهر نمی‌شود. شامل:
    - وضعیت _ACTIVE_SCANS[session_id]
    - تعداد کل messages در session
    - آخرین ۱۰ پیام (id, role, action_type, timestamp, content[:200])
    - آیا scan_complete (یا scan_complete_fallback) موجود است
    """
    from ...services.inspector_scan_bridge import _ACTIVE_SCANS, read_inspector_scan_progress
    info = read_inspector_scan_progress(session_id)
    active_raw = _ACTIVE_SCANS.get(session_id)
    out = {
        "session_id": session_id,
        "active_scan_state": info,
        "active_scan_raw_keys": list(active_raw.keys()) if active_raw else [],
    }
    # خواندن messages
    try:
        from ...core.database import SessionLocal
        from ...models.inspector_session import InspectorMessage
        db = SessionLocal()
        try:
            total = db.query(InspectorMessage).filter(InspectorMessage.session_id == int(session_id)).count()
            recent = (
                db.query(InspectorMessage)
                .filter(InspectorMessage.session_id == int(session_id))
                .order_by(InspectorMessage.id.desc())
                .limit(10)
                .all()
            )
            out["total_messages"] = total
            out["recent_messages"] = [
                {
                    "id": m.id,
                    "role": m.role,
                    "action_type": m.action_type,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "content_preview": (m.content or "")[:200],
                    "has_extra_data": bool(m.extra_data),
                    "extra_data_size": len(m.extra_data) if m.extra_data else 0,
                }
                for m in recent
            ]
            # چک خاص: آیا scan_complete یا fallback لاگ شده؟
            for at in ("scan_complete", "scan_complete_fallback", "scan_error", "scan_cancelled"):
                m = (
                    db.query(InspectorMessage)
                    .filter(InspectorMessage.session_id == int(session_id))
                    .filter(InspectorMessage.action_type == at)
                    .order_by(InspectorMessage.id.desc())
                    .first()
                )
                if m:
                    out[f"latest_{at}"] = {
                        "id": m.id,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                        "content_preview": (m.content or "")[:300],
                    }
        finally:
            db.close()
    except Exception as e:
        out["db_error"] = str(e)[:300]
    return out


class RunProposalRequest(BaseModel):
    model_id: Optional[str] = None


@router.post("/inspector/session/{session_id}/proposals/{proposal_id}/run")
async def inspector_run_proposal(
    session_id: int,
    proposal_id: str,
    payload: Optional[RunProposalRequest] = None,
):
    """یک proposal از scan موردی را با AI به code-ready تبدیل می‌کند.

    تغییرات locally staged می‌شوند (در InspectorMessage). commit/push بعداً
    با endpoint apply-all انجام می‌شود.
    """
    from ...services.inspector_proposal_executor import run_proposal
    payload = payload or RunProposalRequest()
    try:
        result = await run_proposal(
            session_id=session_id,
            proposal_id=proposal_id,
            model_id=payload.model_id,
        )
        if not result.get("success") and result.get("code") == "proposal_not_found":
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        slog.error("run_proposal failed", exception=e, session_id=session_id, proposal_id=proposal_id)
        raise HTTPException(status_code=500, detail=str(e)[:300])


class ApplyAllRequest(BaseModel):
    commit_message: Optional[str] = None
    include_unexecuted: bool = False
    branch_strategy: str = "new_pr"  # "new_pr" | "default_branch_commit"
    model_id: Optional[str] = None
    # 🆕 (v3) — override consistency check اگر کاربر بخواهد علی‌رغم
    # warnings ادامه دهد (مثلاً warnings جزئی هستند یا کاربر می‌داند
    # چه می‌کند)
    force_apply: bool = False
    # 🆕 (v3) — selected_proposal_ids: اگر داده شد، فقط همان proposals
    # apply می‌شوند نه همه staged
    selected_proposal_ids: Optional[List[str]] = None


# 🆕 idempotency برای apply-all — جلوگیری از ساخت چند PR یکسان وقتی کاربر
# دوبار کلیک می‌کند یا client retry می‌کند. lock per-session + کش نتیجه.
_APPLY_ALL_LOCKS: Dict[int, asyncio.Lock] = {}
_APPLY_ALL_RECENT: Dict[int, Tuple[float, Dict[str, Any]]] = {}  # session_id → (timestamp, result)
_APPLY_ALL_DEDUP_WINDOW_SECONDS = 60  # درخواست دوم در این پنجره نتیجهٔ قبل را برمی‌گرداند


def _get_apply_all_lock(session_id: int) -> asyncio.Lock:
    lk = _APPLY_ALL_LOCKS.get(session_id)
    if lk is None:
        lk = asyncio.Lock()
        _APPLY_ALL_LOCKS[session_id] = lk
    return lk


@router.post("/inspector/session/{session_id}/apply-all")
async def inspector_apply_all(
    session_id: int,
    payload: Optional[ApplyAllRequest] = None,
):
    """همهٔ proposalهای staged این session را در یک PR/commit به GitHub می‌فرستد.

    اگر include_unexecuted=True، ابتدا proposalهای pending را اجرا می‌کند.
    اگر force_apply=True، consistency check warnings را override می‌کند.
    اگر selected_proposal_ids داده شد، فقط همان‌ها apply می‌شوند.

    🆕 idempotency: هر session تنها یک apply-all همزمان دارد. اگر درخواست دومی
    در پنجرهٔ ۶۰ ثانیه‌ای رسید، نتیجهٔ قبلی برگردانده می‌شود (با علامت deduped).
    """
    import time as _time
    from ...services.inspector_proposal_executor import apply_all_staged
    payload = payload or ApplyAllRequest()

    # ── دزدگیر: اگر همین session در ۶۰ ثانیهٔ گذشته apply-all موفق داشته،
    # نتیجه را دوباره برگردان (deduped) — جلوگیری از PR تکراری.
    _recent = _APPLY_ALL_RECENT.get(session_id)
    if _recent:
        _ts, _res = _recent
        if (_time.time() - _ts) < _APPLY_ALL_DEDUP_WINDOW_SECONDS:
            slog.info(f"[apply-all] dedup hit for session {session_id} — returning cached result")
            return {**_res, "deduped": True, "dedup_reason": "duplicate request within window"}

    _lk = _get_apply_all_lock(session_id)
    if _lk.locked():
        slog.info(f"[apply-all] concurrent request for session {session_id} — rejecting")
        return {
            "success": False,
            "deduped": True,
            "dedup_reason": "another apply-all is in progress for this session",
            "branch_url": None,
        }

    async with _lk:
        try:
            result = await apply_all_staged(
                session_id=session_id,
                commit_message=payload.commit_message,
                include_unexecuted=payload.include_unexecuted,
                branch_strategy=payload.branch_strategy,
                model_id=payload.model_id,
                force_apply=payload.force_apply,
                selected_proposal_ids=payload.selected_proposal_ids,
            )
            # نتیجه را برای dedup در پنجرهٔ بعدی کش کن (فقط روی موفقیت)
            if isinstance(result, dict) and result.get("success"):
                _APPLY_ALL_RECENT[session_id] = (_time.time(), result)
                # cleanup قدیمی‌ها — جلوگیری از رشد بی‌محدود
                if len(_APPLY_ALL_RECENT) > 500:
                    _now = _time.time()
                    _APPLY_ALL_RECENT.clear()
                    if isinstance(result, dict):
                        _APPLY_ALL_RECENT[session_id] = (_now, result)
            return result
        except Exception as e:
            slog.error("apply_all failed", exception=e, session_id=session_id)
            raise HTTPException(status_code=500, detail=str(e)[:300])
