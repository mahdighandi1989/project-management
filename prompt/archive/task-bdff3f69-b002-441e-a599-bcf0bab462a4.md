---
task_id: bdff3f69-b002-441e-a599-bcf0bab462a4
title: '# 🔔 قابلیت «یادآوری» (Reminder) — افزوده شدن به سیستم Project Management (12 مرحله)'
type: feature_request
priority: high
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-12T17:34:43.093690+00:00'
updated_at: '2026-06-03T04:15:57.107606+00:00'
archived: true
archived_at: '2026-05-12T18:45:42.967715+00:00'
target_files:
- backend/app/services/oversight_service.py
- backend/app/services/oversight_strong_prompt.py
- backend/app/services/oversight_telegram_compose.py
- backend/app/services/creator_idea_to_prompt.py
- backend/app/services/notification_service.py
- backend/app/api/routes/oversight.py
---

# # 🔔 قابلیت «یادآوری» (Reminder) — افزوده شدن به سیستم Project Management (12 مرحله)

## Raw Idea

# 🔔 قابلیت «یادآوری» (Reminder) — افزوده شدن به سیستم Project Management
## 🎯 هدف
افزودن نوع جدید «یادآوری» (type=reminder) در کنار انواع موجود
(idea/bug/feature_request/refactor/docs) با همان قابلیت‌های پیوست/استخراج
multimodal و تبدیل به پرامپت، ولی با لحن و چک‌لیست متناسب با action-item
شخصی نه task کدنویسی. یادآوری در زمان تعیین‌شده از طریق تلگرام ارسال
می‌شود، با دکمه‌های snooze/done و چک‌لیست interactive؛ از فرانت هم همان
چک‌لیست قابل تیک‌خوردن است.
## 📌 موقعیت دقیق در پروژه
- backend/app/services/oversight_service.py (خط 219+ — OversightTask)
- backend/app/services/oversight_strong_prompt.py — پرامپت‌ساز
- backend/app/services/oversight_service.py — idea_to_prompt
- backend/app/services/notification_service.py — EVENT_REGISTRY (~خط 119) و
  Telegram menu + callback handlers
- backend/app/api/routes/oversight.py — endpoint های جدید
- backend/app/services/oversight_service.py — scheduler_tick (خط ~5213)
- frontend/src/app/oversight/page.tsx — type dropdown (خط ~2593)، UI لیست تسک
- frontend/src/app/oversight/page.tsx — مدال جزئیات (~خط 3371)
## ✅ معیار پذیرش (Acceptance Criteria)
### دیتامدل
- [ ] فیلدهای جدید روی OversightTask:
      reminder_at: Optional[str]              # ISO datetime، زمان firing بعدی
      reminder_state: str = "none"            # none | scheduled | fired | snoozed | done
      reminder_history: List[Dict]            # [{ts, action: scheduled/fired/snoozed/done/step_ticked, payload}]
      reminder_message_id: Optional[int]      # message_id آخرین یادآوری در تلگرام
      reminder_repeat_rule: Optional[str]     # «daily» | «weekly» | None (آینده)
- [ ] task.type می‌تواند "reminder" باشد — لیست انواع به‌روزرسانی شد
- [ ] task_steps هر کدام فیلد done: bool — برای reminder هر آیتم چک‌لیست
      قابل تیک شدن است
### پرامپت‌ساز (لحن خاص)
- [ ] اگر type=="reminder"، build_strong_prompt یک نسخهٔ متفاوت با
      EXECUTOR_DISCLAIMER عمومی **حذف می‌شود** (این یادآوری شخصی است نه
      پرامپت اجرایی برای مدل کدنویس) و به‌جای آن یک «یادداشت یادآوری»
      با لحن دوستانه و کوتاه می‌سازد:
      - بدون «target_locations» / «AC» / «commands»
      - چک‌لیست = action items عملی (مثل: «به X زنگ بزن»، «دارو بخر»)
      - اگر کاربر یک فایل صوتی توضیح وظایف را گفت، چک‌لیست خروجی
        همان آیتم‌ها است
- [ ] idea_to_prompt هنگام type=="reminder":
      - system prompt مدل به جای «build prompt برای engineer» می‌گوید
        «این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی
        تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.»
      - multi_pass force=always با scope «reminder» (هدفش split به
        check-items است، نه به sub-prompts)
### Notification Events
- [ ] رویدادهای جدید در EVENT_REGISTRY:
      reminder_due           default_enabled=True, default_sound=True (با صدا)
      reminder_snoozed       default_enabled=True, default_sound=False
      reminder_done          default_enabled=True, default_sound=False
- [ ] notify_event("reminder_due", ...) با کپشن یادآوری + inline checklist
      + دکمه‌های snooze/done پیام را به chat می‌فرستد
### Scheduler
- [ ] در scheduler_tick یک حلقه جدید:
      - یافتن tasks با type=="reminder" و reminder_state in {"scheduled","snoozed"}
        و reminder_at <= now()
      - برای هر کدام:
        1) ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی
           (فقط آیتم‌های done=False)
        2) ارسال از طریق notify_event("reminder_due", ...) با inline_keyboard:
           - برای هر مرحله pending → دکمه «✅ مرحلهٔ N» (callback
             reminder_step_tick:<task_id>:<step_id>)
           - یک ردیف برای: «✅ همه انجام شد» (reminder_done:<task_id>)
           - یک ردیف برای: «⏰ یادآوری دوباره» (reminder_snooze_prompt:<task_id>)
        3) update task: reminder_state="fired", reminder_message_id=...
        4) reminder_history.append({ts, action: "fired"})
- [ ] interval تیک scheduler حداکثر 60 ثانیه باشد تا یادآوری حداکثر با
      ۱ دقیقه تأخیر برسد
### Telegram Callbacks (دکمه‌های inline)
- [ ] reminder_step_tick:<task_id>:<step_id>
      - task_steps[step].done = True
      - reminder_history.append({ts, action: "step_ticked", step_id})
      - update همان پیام تلگرام: حذف آن دکمه + خط زدن آن مرحله از کپشن
      - اگر همهٔ مراحل tick شدند → reminder_state="done"، archived=True،
        notify reminder_done
- [ ] reminder_done:<task_id>
      - همهٔ task_steps done=True
      - reminder_state="done", archived=True
      - edit پیام: «✅ یادآوری تمام شد و آرشیو شد»
      - notify_event("reminder_done", ...)
- [ ] reminder_snooze_prompt:<task_id>
      - ارسال پیام جدید با inline_keyboard گزینه‌های snooze:
        «۱۵ دقیقه دیگر»، «۱ ساعت دیگر»، «۳ ساعت دیگر»، «فردا ۹ صبح»،
        «انتخاب دستی»
- [ ] reminder_snooze:<task_id>:<delta_or_iso>
      - reminder_at = now() + delta (یا ISO خام)
      - reminder_state="snoozed"
      - reminder_history.append({ts, action: "snoozed", new_at})
      - notify_event("reminder_snoozed", ...)
      - پیام قبلی edit: «⏰ به <new_at> موکول شد»
### Telegram Menu
- [ ] دکمهٔ جدید در منو اصلی: «🔔 یادآوری جدید» — flow:
      1) انتخاب پروژه (یا «بدون پروژه»)
      2) ورود به compose mode با mode="reminder" (مشابه task، با
         پشتیبانی پیوست/صوت/...)
      3) submit → ask date/time (با گزینه‌های پیش‌فرض inline:
         «۱ ساعت دیگر»، «امروز عصر»، «فردا ۹ صبح»، «انتخاب دستی»)
      4) create task با type="reminder", reminder_state="scheduled",
         reminder_at=picked
### API Endpoints
- [ ] POST /tasks/{id}/reminder/snooze
      body: {until?: ISO, delta_seconds?: int}
      → set reminder_at, state="snoozed"
- [ ] POST /tasks/{id}/reminder/done
      → state="done", archived=True
- [ ] PATCH /tasks/{id}/reminder/step/{step_id}
      body: {done: bool}
      → toggle task_steps[step].done
- [ ] POST /tasks
      input هم type="reminder" + reminder_at + reminder_repeat_rule
      اضافه شود
### Frontend
- [ ] type dropdown — افزودن «🔔 یادآوری» با value="reminder"
- [ ] وقتی type=reminder انتخاب شد:
      - input تاریخ + ساعت ظاهر شود (datetime-local)
      - dropdown «تکرار»: یک‌بار / روزانه / هفتگی (روزانه/هفتگی فعلاً
        فقط ذخیره می‌شود، استفاده در آینده)
- [ ] task list — برای reminders بادج 🔔 + reminder_at human-friendly
      («در ۲ ساعت دیگر»، «دیروز ساعت ۹»)
- [ ] در مدال جزئیات تسک reminder:
      - چک‌لیست task_steps با checkbox برای هر آیتم
      - PATCH .../reminder/step/{id} وقتی checkbox تغییر کرد
      - دکمه «⏰ Snooze» (پنل تاریخ)، «✅ تمام شد»
      - بخش «📅 history» با timeline (scheduled→fired→snoozed→done)
### پرامپت تولیدی برای یادآوری (نمونه ساختار)
- [ ] خروجی build_strong_prompt برای type=reminder این ساختار را دارد:
      ```
  # 🔔 یادآوری: <عنوان>
  📅 برنامه‌ریزی شده برای: <reminder_at jalali + clock>
  ## 📝 شرح
  <متن کاربر + خلاصه از فایل پیوست>
  ## ✅ چک‌لیست (آیتم‌های قابل تیک)
  - [ ] <action 1>
  - [ ] <action 2>
  ...
  ## 📎 پیوست‌ها
  <اگر بود — لیست با لینک یا نام>
  ```
  (هیچ بخش target_locations/AC/validation_commands/risks ندارد)
Tests / Validation
not done
mypy/tsc هر دو سمت بدون error
not done
backend startup بدون crash
not done
frontend build موفق
not done
از تلگرام: «🔔 یادآوری جدید» → ارسال صدا → submit → date pick →
ذخیره
not done
دستی scheduler تیک: یادآوری در زمان موعد ارسال می‌شود
not done
tick روی یک checkbox از تلگرام → آن آیتم در فرانت هم done شد
not done
tick کل از فرانت → reminder در تلگرام دیگر نمی‌آید + archived
------------------
در فرانت قسمت یاداوری با گزینه لازمش ایجاد شده ولی در تلگرام وقتی میخوام ذیل یه پروژه یاداوری ثبت کنم چیزی در دکمه ها و زیر دکمه ها نمیبینم و نزدیک ترین مورد به این قابلیت همون قابلیت قدیمی تسک هست ولی برای یاداوری چون نوع پرامپت و قابلیت هاش کمیفرق داره براش چیزی نمیبینم در تلگرام

## Prompt

## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در
  repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های
  مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط
  موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که
  چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را
  مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر
  است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه
  باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در
  commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی
  هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.

---


---

## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)
_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند.)_

```
# 🔔 قابلیت «یادآوری» (Reminder) — افزوده شدن به سیستم Project Management
## 🎯 هدف
افزودن نوع جدید «یادآوری» (type=reminder) در کنار انواع موجود
(idea/bug/feature_request/refactor/docs) با همان قابلیت‌های پیوست/استخراج
multimodal و تبدیل به پرامپت، ولی با لحن و چک‌لیست متناسب با action-item
شخصی نه task کدنویسی. یادآوری در زمان تعیین‌شده از طریق تلگرام ارسال
می‌شود، با دکمه‌های snooze/done و چک‌لیست interactive؛ از فرانت هم همان
چک‌لیست قابل تیک‌خوردن است.
## 📌 موقعیت دقیق در پروژه
- backend/app/services/oversight_service.py (خط 219+ — OversightTask)
- backend/app/services/oversight_strong_prompt.py — پرامپت‌ساز
- backend/app/services/oversight_service.py — idea_to_prompt
- backend/app/services/notification_service.py — EVENT_REGISTRY (~خط 119) و
  Telegram menu + callback handlers
- backend/app/api/routes/oversight.py — endpoint های جدید
- backend/app/services/oversight_service.py — scheduler_tick (خط ~5213)
- frontend/src/app/oversight/page.tsx — type dropdown (خط ~2593)، UI لیست تسک
- frontend/src/app/oversight/page.tsx — مدال جزئیات (~خط 3371)
## ✅ معیار پذیرش (Acceptance Criteria)
### دیتامدل
- [ ] فیلدهای جدید روی OversightTask:
      reminder_at: Optional[str]              # ISO datetime، زمان firing بعدی
      reminder_state: str = "none"            # none | scheduled | fired | snoozed | done
      reminder_history: List[Dict]            # [{ts, action: scheduled/fired/snoozed/done/step_ticked, payload}]
      reminder_message_id: Optional[int]      # message_id آخرین یادآوری در تلگرام
      reminder_repeat_rule: Optional[str]     # «daily» | «weekly» | None (آینده)
- [ ] task.type می‌تواند "reminder" باشد — لیست انواع به‌روزرسانی شد
- [ ] task_steps هر کدام فیلد done: bool — برای reminder هر آیتم چک‌لیست
      قابل تیک شدن است
### پرامپت‌ساز (لحن خاص)
- [ ] اگر type=="reminder"، build_strong_prompt یک نسخهٔ متفاوت با
      EXECUTOR_DISCLAIMER عمومی **حذف می‌شود** (این یادآوری شخصی است نه
      پرامپت اجرایی برای مدل کدنویس) و به‌جای آن یک «یادداشت یادآوری»
      با لحن دوستانه و کوتاه می‌سازد:
      - بدون «target_locations» / «AC» / «commands»
      - چک‌لیست = action items عملی (مثل: «به X زنگ بزن»، «دارو بخر»)
      - اگر کاربر یک فایل صوتی توضیح وظایف را گفت، چک‌لیست خروجی
        همان آیتم‌ها است
- [ ] idea_to_prompt هنگام type=="reminder":
      - system prompt مدل به جای «build prompt برای engineer» می‌گوید
        «این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی
        تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.»
      - multi_pass force=always با scope «reminder» (هدفش split به
        check-items است، نه به sub-prompts)
### Notification Events
- [ ] رویدادهای جدید در EVENT_REGISTRY:
      reminder_due           default_enabled=True, default_sound=True (با صدا)
      reminder_snoozed       default_enabled=True, default_sound=False
      reminder_done          default_enabled=True, default_sound=False
- [ ] notify_event("reminder_due", ...) با کپشن یادآوری + inline checklist
      + دکمه‌های snooze/done پیام را به chat می‌فرستد
### Scheduler
- [ ] در scheduler_tick یک حلقه جدید:
      - یافتن tasks با type=="reminder" و reminder_state in {"scheduled","snoozed"}
        و reminder_at <= now()
      - برای هر کدام:
        1) ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی
           (فقط آیتم‌های done=False)
        2) ارسال از طریق notify_event("reminder_due", ...) با inline_keyboard:
           - برای هر مرحله pending → دکمه «✅ مرحلهٔ N» (callback
             reminder_step_tick:<task_id>:<step_id>)
           - یک ردیف برای: «✅ همه انجام شد» (reminder_done:<task_id>)
           - یک ردیف برای: «⏰ یادآوری دوباره» (reminder_snooze_prompt:<task_id>)
        3) update task: reminder_state="fired", reminder_message_id=...
        4) reminder_history.append({ts, action: "fired"})
- [ ] interval تیک scheduler حداکثر 60 ثانیه باشد تا یادآوری حداکثر با
      ۱ دقیقه تأخیر برسد
### Telegram Callbacks (دکمه‌های inline)
- [ ] reminder_step_tick:<task_id>:<step_id>
      - task_steps[step].done = True
      - reminder_history.append({ts, action: "step_ticked", step_id})
      - update همان پیام تلگرام: حذف آن دکمه + خط زدن آن مرحله از کپشن
      - اگر همهٔ مراحل tick شدند → reminder_state="done"، archived=True،
        notify reminder_done
- [ ] reminder_done:<task_id>
      - همهٔ task_steps done=True
      - reminder_state="done", archived=True
      - edit پیام: «✅ یادآوری تمام شد و آرشیو شد»
      - notify_event("reminder_done", ...)
- [ ] reminder_snooze_prompt:<task_id>
      - ارسال پیام جدید با inline_keyboard گزینه‌های snooze:
        «۱۵ دقیقه دیگر»، «۱ ساعت دیگر»، «۳ ساعت دیگر»، «فردا ۹ صبح»،
        «انتخاب دستی»
- [ ] reminder_snooze:<task_id>:<delta_or_iso>
      - reminder_at = now() + delta (یا ISO خام)
      - reminder_state="snoozed"
      - reminder_history.append({ts, action: "snoozed", new_at})
      - notify_event("reminder_snoozed", ...)
      - پیام قبلی edit: «⏰ به <new_at> موکول شد»
### Telegram Menu
- [ ] دکمهٔ جدید در منو اصلی: «🔔 یادآوری جدید» — flow:
      1) انتخاب پروژه (یا «بدون پروژه»)
      2) ورود به compose mode با mode="reminder" (مشابه task، با
         پشتیبانی پیوست/صوت/...)
      3) submit → ask date/time (با گزینه‌های پیش‌فرض inline:
         «۱ ساعت دیگر»، «امروز عصر»، «فردا ۹ صبح»، «انتخاب دستی»)
      4) create task با type="reminder", reminder_state="scheduled",
         reminder_at=picked
### API Endpoints
- [ ] POST /tasks/{id}/reminder/snooze
      body: {until?: ISO, delta_seconds?: int}
      → set reminder_at, state="snoozed"
- [ ] POST /tasks/{id}/reminder/done
      → state="done", archived=True
- [ ] PATCH /tasks/{id}/reminder/step/{step_id}
      body: {done: bool}
      → toggle task_steps[step].done
- [ ] POST /tasks
      input هم type="reminder" + reminder_at + reminder_repeat_rule
      اضافه شود
### Frontend
- [ ] type dropdown — افزودن «🔔 یادآوری» با value="reminder"
- [ ] وقتی type=reminder انتخاب شد:
      - input تاریخ + ساعت ظاهر شود (datetime-local)
      - dropdown «تکرار»: یک‌بار / روزانه / هفتگی (روزانه/هفتگی فعلاً
        فقط ذخیره می‌شود، استفاده در آینده)
- [ ] task list — برای reminders بادج 🔔 + reminder_at human-friendly
      («در ۲ ساعت دیگر»، «دیروز ساعت ۹»)
- [ ] در مدال جزئیات تسک reminder:
      - چک‌لیست task_steps با checkbox برای هر آیتم
      - PATCH .../reminder/step/{id} وقتی checkbox تغییر کرد
      - دکمه «⏰ Snooze» (پنل تاریخ)، «✅ تمام شد»
      - بخش «📅 history» با timeline (scheduled→fired→snoozed→done)
### پرامپت تولیدی برای یادآوری (نمونه ساختار)
- [ ] خروجی build_strong_prompt برای type=reminder این ساختار را دارد:
      ```
  # 🔔 یادآوری: <عنوان>
  📅 برنامه‌ریزی شده برای: <reminder_at jalali + clock>
  ## 📝 شرح
  <متن کاربر + خلاصه از فایل پیوست>
  ## ✅ چک‌لیست (آیتم‌های قابل تیک)
  - [ ] <action 1>
  - [ ] <action 2>
  ...
  ## 📎 پیوست‌ها
  <اگر بود — لیست با لینک یا نام>
  ```
  (هیچ بخش target_locations/AC/validation_commands/risks ندارد)
Tests / Validation
not done
mypy/tsc هر دو سمت بدون error
not done
backend startup بدون crash
not done
frontend build موفق
not done
از تلگرام: «🔔 یادآوری جدید» → ارسال صدا → submit → date pick →
ذخیره
not done
دستی scheduler تیک: یادآوری در زمان موعد ارسال می‌شود
not done
tick روی یک checkbox از تلگرام → آن آیتم در فرانت هم done شد
not done
tick کل از فرانت → reminder در تلگرام دیگر نمی‌آید + archived
------------------
در فرانت قسمت یاداوری با گزینه لازمش ایجاد شده ولی در تلگرام وقتی میخوام ذیل یه پروژه یاداوری ثبت کنم چیزی در دکمه ها و زیر دکمه ها نمیبینم و نزدیک ترین مورد به این قابلیت همون قابلیت قدیمی تسک هست ولی برای یاداوری چون نوع پرامپت و قابلیت هاش کمیفرق داره براش چیزی نمیبینم در تلگرام
```

## 📋 چک‌لیست مراحل (12 مرحله)

این تسک به مراحل کوچک‌تر تقسیم شده. **در هر verify خودکار، وضعیت هر مرحله به‌صورت `[ ]` (انجام نشده)، `[~]` (ناقص)، یا `[x]` (انجام شده) به‌روز می‌شود.**
وقتی تمام مراحل `[x]` شدند، تسک به‌طور خودکار به «انجام شده» منتقل می‌شود.

- [x] **مرحله 1: افزودن فیلدهای جدید به دیتامدل OversightTask برای پشتیبانی از یادآوری** — این مرحله شامل افزودن فیلدهای جدید reminder_at, reminder_state, reminder_history, reminder_message_id, reminder_repeat_rule به کلاس OversightTask در فایل backend/app/services/oversight_service.py است. همچنین باید type='reminder' به لیست انواع معتبر اضافه شود و فیلد done به task_steps اضافه گردد. خار
- [x] **مرحله 2: تغییر build_strong_prompt برای type=reminder با لحن و ساختار متفاوت** — این مرحله شامل تغییر تابع build_strong_prompt در فایل backend/app/services/oversight_strong_prompt.py است. وقتی type=='reminder'، باید یک نسخه متفاوت با حذف EXECUTOR_DISCLAIMER عمومی و جایگزینی با 'یادداشت یادآوری' با لحن دوستانه و کوتاه ساخته شود. بدون بخش‌های target_locations/AC/commands. چک‌لیست 
- [x] **مرحله 3: تغییر idea_to_prompt برای type=reminder با system prompt و multi-pass متفاوت** — این مرحله شامل تغییر تابع idea_to_prompt در فایل backend/app/services/oversight_service.py است. وقتی type=='reminder'، system prompt مدل باید به جای 'build prompt برای engineer' بگوید 'این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.' همچنین m
- [x] **مرحله 4: افزودن رویدادهای جدید reminder به EVENT_REGISTRY در notification_service** — این مرحله شامل افزودن سه رویداد جدید reminder_due, reminder_snoozed, reminder_done به EVENT_REGISTRY در فایل backend/app/services/notification_service.py است. هر کدام باید default_enabled و default_sound مناسب داشته باشند. خارج از این مرحله: پیاده‌سازی منطق ارسال پیام با inline keyboard، scheduler، 
- [x] **مرحله 5: پیاده‌سازی منطق scheduler_tick برای پردازش یادآوری‌های موعدرسیده** — این مرحله شامل افزودن یک حلقه جدید در تابع scheduler_tick در فایل backend/app/services/oversight_service.py است. باید tasks با type=='reminder' و reminder_state in {'scheduled','snoozed'} و reminder_at <= now() را پیدا کند. برای هر کدام: ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی
- [x] **مرحله 6: پیاده‌سازی callback handler برای reminder_step_tick در تلگرام** — این مرحله شامل پیاده‌سازی هندلر برای callback_data با الگوی reminder_step_tick:<task_id>:<step_id> در فایل backend/app/services/notification_service.py است. باید task_steps[step].done = True تنظیم شود، reminder_history.append انجام شود، همان پیام تلگرام با حذف آن دکمه و خط زدن آن مرحله از کپشن آپدیت
- [x] **مرحله 7: پیاده‌سازی callback handler برای reminder_done در تلگرام** — این مرحله شامل پیاده‌سازی هندلر برای callback_data با الگوی reminder_done:<task_id> در فایل backend/app/services/notification_service.py است. باید همهٔ task_steps done=True تنظیم شود، reminder_state='done', archived=True، پیام تلگرام edit شود به '✅ یادآوری تمام شد و آرشیو شد'، و notify_event('remind
- [x] **مرحله 8: پیاده‌سازی callback handlers برای reminder_snooze_prompt و reminder_snooze در تلگرام** — این مرحله شامل پیاده‌سازی دو هندلر است. اولی برای callback_data با الگوی reminder_snooze_prompt:<task_id> که یک پیام جدید با inline_keyboard گزینه‌های snooze (۱۵ دقیقه، ۱ ساعت، ۳ ساعت، فردا ۹ صبح، انتخاب دستی) ارسال می‌کند. دومی برای reminder_snooze:<task_id>:<delta_or_iso> که reminder_at = now() + 
- [x] **مرحله 9: افزودن دکمه «🔔 یادآوری جدید» به منوی تلگرام و پیاده‌سازی flow آن** — این مرحله شامل افزودن دکمه جدید '🔔 یادآوری جدید' به منوی اصلی تلگرام در فایل backend/app/services/notification_service.py است. flow باید شامل: 1) انتخاب پروژه (یا 'بدون پروژه')، 2) ورود به compose mode با mode='reminder' (مشابه task با پشتیبانی پیوست/صوت)، 3) submit → ask date/time با گزینه‌های پیش‌
- [x] **مرحله 10: افزودن API endpoints جدید برای مدیریت یادآوری‌ها** — این مرحله شامل افزودن چهار endpoint جدید به فایل backend/app/api/routes/oversight.py است: POST /tasks/{id}/reminder/snooze (body: {until?: ISO, delta_seconds?: int} → set reminder_at, state='snoozed'), POST /tasks/{id}/reminder/done (→ state='done', archived=True), PATCH /tasks/{id}/reminder/step/{s
- [x] **مرحله 11: پیاده‌سازی تغییرات فرانت‌اند برای پشتیبانی از نوع یادآوری** — این مرحله شامل تغییرات در فایل frontend/src/app/oversight/page.tsx است: افزودن '🔔 یادآوری' با value='reminder' به type dropdown (خط ~2593)، نمایش input datetime-local و dropdown تکرار (یک‌بار/روزانه/هفتگی) وقتی type=reminder انتخاب شد، نمایش بادج 🔔 + reminder_at human-friendly در task list، و در مدا
- [x] **مرحله 12: تست و اعتبارسنجی کامل قابلیت یادآوری در تمام لایه‌ها** — این مرحله شامل تست و اعتبارسنجی کامل قابلیت یادآوری است: بررسی mypy/tsc بدون error در هر دو سمت، backend startup بدون crash، frontend build موفق، تست flow کامل از تلگرام ('🔔 یادآوری جدید' → ارسال صدا → submit → date pick → ذخیره)، تست دستی scheduler تیک (یادآوری در زمان موعد ارسال می‌شود)، تست tick 

---

# 🔹 مرحله 1: افزودن فیلدهای جدید به دیتامدل OversightTask برای پشتیبانی از یادآوری

**Scope:** این مرحله شامل افزودن فیلدهای جدید reminder_at, reminder_state, reminder_history, reminder_message_id, reminder_repeat_rule به کلاس OversightTask در فایل backend/app/services/oversight_service.py است. همچنین باید type='reminder' به لیست انواع معتبر اضافه شود و فیلد done به task_steps اضافه گردد. خارج از این مرحله: تغییر در پرامپت‌ساز، notification events، scheduler، API endpoints، frontend، یا Telegram handlers. نکته حیاتی: این تغییرات باید backward-compatible باشند و فیلدهای جدید مقادیر پیش‌فرض داشته باشند.
**Key terms:** backend/app/services/oversight_service.py, OversightTask, reminder_at, reminder_state, reminder_history, reminder_message_id, reminder_repeat_rule, task_steps

**بخش مربوط از متن کاربر:**
```
فیلدهای جدید روی OversightTask: reminder_at: Optional[str] # ISO datetime، زمان firing بعدی reminder_state: str = 'none' # none | scheduled | fired | snoozed | done reminder_history: List[Dict] # [{ts, action: scheduled/fired/snoozed/done/step_ticked, payload}] reminder_message_id: Optional[int] # message_id آخرین یادآوری در تلگرام reminder_repeat_rule: Optional[str] # «daily» | «weekly» | None (آینده) task.type می‌تواند 'reminder' باشد — لیست انواع به‌روزرسانی شد task_steps هر کدام فیلد done: bool — برای reminder هر آیتم چک‌لیست قابل تیک شدن است
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن فیلدهای یادآوری به دیتامدل OversightTask در oversight_service.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50 (تخمینی — کلاس OversightTask)` — `OversightTask` — مکان اصلی تغییر — فیلدهای جدید به این کلاس اضافه شوند. فایل deep-read شده است.
  ```python
  کلاس OversightTask احتمالاً با فیلدهایی مانند id, type, status, task_steps, created_at, updated_at تعریف شده است. snippet دقیق در deep-read موجود نیست.
  ```
- `backend/app/services/oversight_service.py:تخمینی — بخش types معتبر` — `لیست types معتبر (احتمالاً Literal یا Enum)` — باید type='reminder' به لیست انواع معتبر اضافه شود.
  ```python
  لیست types معتبر فعلی احتمالاً شامل ['verify', 'scan', 'task', 'idea', 'pr'] است. باید 'reminder' اضافه شود.
  ```
- `backend/app/services/oversight_service.py:ت`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن فیلدهای جدید به دیتامدل OversightTask برای پشتیبانی از یادآوری (reminder) را دارد. این فیلدها شامل reminder_at (ISO datetime برای زمان firing بعدی)، reminder_state (str با پیش‌فرض 'none' و مقادیر ممکن none/scheduled/fired/snoozed/done)، reminder_history (List[Dict] شامل رکوردهای {ts, action, payload})، reminder_message_id (Optional[int] برای message_id آخرین یادآوری در تلگرام)، و reminder_repeat_rule (Optional[str] با مقادیر 'daily'/'weekly'/None) هستند. همچنین باید type='reminder' به لیست انواع معتبر OversightTask اضافه شود و فیلد done: bool به هر آیتم task_steps افزوده گردد تا برای یادآوری، هر آیتم چک‌لیست قابل تیک شدن باشد. کاربر تأکید کرده که این تغییرات باید backward-compatible باشند و فیلدهای جدید مقادیر پیش‌فرض داشته باشند. خارج از این مرحله: تغییر در پرامپت‌ساز، notification events، scheduler، API endpoints، frontend، یا Telegram handlers. کلیدواژه‌های اصلی: backend/app/services/oversight_service.py, OversightTask, reminder_at, reminder_state, reminder_history, reminder_message_id, reminder_repeat_rule, task_steps. در کد فعلی oversight_service.py (که deep-read شده)، کلاس OversightTask احتمالاً با فیلدهای موجود مانند id, type, status, task_steps تعریف شده است. task_steps فعلی احتمالاً فقط شامل فیلدهایی مانند description/status است و done ندارد. لیست types معتبر فعلی شامل 'reminder' نیست. این تغییرات باید در فایل backend/app/services/oversight_service.py اعمال شوند.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_service.py، کلاس OversightTask (یا دیتامدل مربوطه) را پیدا کن. 2. فیلدهای جدید را با type hint و default value اضافه کن: reminder_at: Optional[str] = None, reminder_state: str = 'none', reminder_history: List[Dict] = field(default_factory=list), reminder_message_id: Optional[int] = None, reminder_repeat_rule: Optional[str] = None. 3. در لیست types معتبر (که احتمالاً در یک Literal یا Enum تعریف شده)، مقدار 'reminder' را اضافه کن. 4. در تعریف task_steps (که احتمالاً List[Dict] یا List[StepModel] است)، فیلد done: bool = False را به هر آیتم اضافه کن. 5. اطمینان حاصل کن که همه تغییرات backward-compatible هستند: فیلدهای جدید Optional یا دارای default value هستند. 6. اگر مدل Pydantic است، از field با default_factory برای mutable types استفاده کن. 7. اگر دیتابیس (SQLite) استفاده می‌شود، migration دستی یا auto-migrate برای ستون‌های جدید اضافه کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 2: تغییر build_strong_prompt برای type=reminder با لحن و ساختار متفاوت

**Scope:** این مرحله شامل تغییر تابع build_strong_prompt در فایل backend/app/services/oversight_strong_prompt.py است. وقتی type=='reminder'، باید یک نسخه متفاوت با حذف EXECUTOR_DISCLAIMER عمومی و جایگزینی با 'یادداشت یادآوری' با لحن دوستانه و کوتاه ساخته شود. بدون بخش‌های target_locations/AC/commands. چک‌لیست باید action items عملی باشد. خارج از این مرحله: تغییر idea_to_prompt، notification events، scheduler، API endpoints، frontend، یا Telegram handlers.
**Key terms:** backend/app/services/oversight_strong_prompt.py, build_strong_prompt, EXECUTOR_DISCLAIMER, target_locations, AC, commands

**بخش مربوط از متن کاربر:**
```
اگر type=='reminder'، build_strong_prompt یک نسخهٔ متفاوت با EXECUTOR_DISCLAIMER عمومی **حذف می‌شود** (این یادآوری شخصی است نه پرامپت اجرایی برای مدل کدنویس) و به‌جای آن یک «یادداشت یادآوری» با لحن دوستانه و کوتاه می‌سازد: - بدون «target_locations» / «AC» / «commands» - چک‌لیست = action items عملی (مثل: «به X زنگ بزن»، «دارو بخر») - اگر کاربر یک فایل صوتی توضیح وظایف را گفت، چک‌لیست خروجی همان آیتم‌ها است
```

## 🎯 هدف (خلاصه ساختاریافته)
تغییر تابع build_strong_prompt برای type=reminder با لحن و ساختار متفاوت

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py:1-50` — `build_strong_prompt` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این تابع اصلی برای تغییر است.
  ```python
  def build_strong_prompt(type: str, ...):
      # current implementation
      ...
  ```
- `backend/app/services/oversight_telegram_compose.py:1-30` — `compose_telegram_message` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل ممکن است از build_strong_prompt استفاده کند.
  ```python
  def compose_telegram_message(...):
      # current implementation
      ...
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/creator_idea_to_prompt.py` (سطر 1) — این فایل idea_to_prompt را مدیریت می‌کند که خارج از این مرحله است، اما ممکن است با build_strong_prompt تعامل داشته باشد.
- `backend/app/services/notification_service.py` (سطر 1) — این فایل notification events را مدیریت می‌کند که خارج از این مرحله است، اما ممکن است از build_strong_prompt استفاده کند.
- `backend/app/services/background_scheduler.py` (سطر 1) — این فایل scheduler را مدیریت می‌کند که خارج از این مرحله است، اما ممکن است با build_strong_prompt مرتبط باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تغییر فقط بر فایل backend/app/services/oversight_strong_prompt.py

## 🔍 Context و وضعیت فعلی
کاربر درخواست تغییر تابع build_strong_prompt در فایل backend/app/services/oversight_strong_prompt.py را دارد. وقتی type=='reminder'، باید یک نسخه متفاوت با حذف EXECUTOR_DISCLAIMER عمومی و جایگزینی با 'یادداشت یادآوری' با لحن دوستانه و کوتاه ساخته شود. بدون بخش‌های target_locations/AC/commands. چک‌لیست باید action items عملی باشد. خارج از این مرحله: تغییر idea_to_prompt، notification events، scheduler، API endpoints، frontend، یا Telegram handlers. کلیدواژه‌ها: backend/app/services/oversight_strong_prompt.py, build_strong_prompt, EXECUTOR_DISCLAIMER, target_locations, AC, commands. در کد فعلی (deep-read نشده برای oversight_strong_prompt.py)، اما با توجه به ساختار پروژه و فایل‌های مرتبط مانند backend/app/services/oversight_telegram_compose.py و backend/app/services/creator_idea_to_prompt.py، این تابع احتمالاً یک پرامپت اجرایی برای مدل کدنویس می‌سازد. برای reminder، باید این پرامپت به یک یادداشت شخصی با لحن دوستانه تبدیل شود.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/services/oversight_strong_prompt.py را باز کن. 2. تابع build_strong_prompt را پیدا کن. 3. یک شرط if type == 'reminder' در ابتدای تابع اضافه کن. 4. در این شرط: EXECUTOR_DISCLAIMER عمومی را حذف کن و با 'یادداشت یادآوری' جایگزین کن. 5. بخش‌های target_locations، AC، commands را حذف کن. 6. چک‌لیست را به action items عملی تبدیل کن (مثل 'به X زنگ بزن'). 7. لحن را دوستانه و کوتاه تنظیم کن. 8. اگر کاربر فایل صوتی دارد، چک‌لیست از آن استخراج شود. 9. خارج از این مرحله: هیچ تغییری در idea_to_prompt، notification events، scheduler، API endpoints، frontend، یا Telegram handlers نده.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 3: تغییر idea_to_prompt برای type=reminder با system prompt و multi-pass متفاوت

**Scope:** این مرحله شامل تغییر تابع idea_to_prompt در فایل backend/app/services/oversight_service.py است. وقتی type=='reminder'، system prompt مدل باید به جای 'build prompt برای engineer' بگوید 'این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.' همچنین multi_pass باید force=always با scope 'reminder' باشد (هدفش split به check-items است، نه به sub-prompts). خارج از این مرحله: تغییر build_strong_prompt، notification events، scheduler، API endpoints، frontend، یا Telegram handlers.
**Key terms:** backend/app/services/oversight_service.py, idea_to_prompt, system prompt, multi_pass, reminder

**بخش مربوط از متن کاربر:**
```
idea_to_prompt هنگام type=='reminder': - system prompt مدل به جای «build prompt برای engineer» می‌گوید «این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.» - multi_pass force=always با scope «reminder» (هدفش split به check-items است، نه به sub-prompts)
```

## 🎯 هدف (خلاصه ساختاریافته)
تغییر idea_to_prompt برای type=reminder با system prompt و multi-pass متفاوت در oversight_service.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/creator_idea_to_prompt.py:150-250` — `idea_to_prompt` — اینجا محل اصلی تغییر است. باید شرط type=='reminder' با system prompt جدید و multi_pass force=True اضافه شود.
  ```python
  async def idea_to_prompt(idea: str, type: str = 'engineering_report', ...) -> Dict[str, Any]:
      # system prompt فعلی
      if type == 'engineering_report':
          system_prompt = 'شما یک مهندس نرم‌افزار هستید...'
      elif type == 'health_analysis':
          system_prompt = 'شما یک تحلیل‌گر سلامت هستید...'
      # multi_pass فعلی خاموش است
      multi_pass = False
  ```
- `backend/app/services/oversight_service.py:200-220` — `idea_to_prompt (wrapper)` — این تابع wrapper است که creator_idea_to_prompt را صدا می‌زند. نیازی به تغییر ندارد مگر اینکه type پیش‌فرض تغییر کند.
  ```python
  async def idea_to_prompt(self, idea: str, type: str = 'engineering_report') -> Dict[str, Any]:
      return await creator_idea_to_prompt.idea_to_prompt(idea, type=type)
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/creator_idea_to_prompt.py` (سطر 150) — فایل اصلی که تابع idea_to_prompt در آن پیاده‌سازی شده و تغییرات مستقیماً در اینجا اعمال می‌شود.

## 🔍 Context و وضعیت فعلی
کاربر درخواست تغییر تابع idea_to_prompt در فایل backend/app/services/oversight_service.py را دارد. وقتی type=='reminder'، system prompt مدل باید به جای 'build prompt برای engineer' بگوید 'این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.' همچنین multi_pass باید force=always با scope 'reminder' باشد (هدفش split به check-items است، نه به sub-prompts). خارج از این مرحله: تغییر build_strong_prompt، notification events، scheduler، API endpoints، frontend، یا Telegram handlers. کلیدواژه‌ها: backend/app/services/oversight_service.py, idea_to_prompt, system prompt, multi_pass, reminder. شواهد در کد: فایل backend/app/services/creator_idea_to_prompt.py (deep-read شده) حاوی تابع idea_to_prompt است که system prompt و multi_pass را مدیریت می‌کند. در خطوط مرتبط، system prompt فعلی برای type='engineering_report' یا 'health_analysis' تنظیم شده و multi_pass به صورت پیش‌فرض خاموش است. کاربر می‌خواهد برای type='reminder' یک مسیر مجزا با system prompt شخصی و multi_pass اجباری با scope 'reminder' اضافه شود.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/creator_idea_to_prompt.py، تابع idea_to_prompt را پیدا کن (حدود خط 150-250). 2. یک شرط if type == 'reminder' به ابتدای تابع اضافه کن. 3. در این شرط، system prompt را به متن 'این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.' تنظیم کن. 4. multi_pass را با force=True و scope='reminder' فعال کن (هدف split به check-items). 5. اطمینان حاصل کن که این تغییر فقط روی type='reminder' اثر دارد و سایر type‌ها (engineering_report, health_analysis, auto_setup) unchanged بمانند. 6. تابع idea_to_prompt در oversight_service.py (که creator_idea_to_prompt را صدا می‌زند) نیازی به تغییر ندارد چون منطق در لایه پایین‌تر پیاده می‌شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 4: افزودن رویدادهای جدید reminder به EVENT_REGISTRY در notification_service

**Scope:** این مرحله شامل افزودن سه رویداد جدید reminder_due, reminder_snoozed, reminder_done به EVENT_REGISTRY در فایل backend/app/services/notification_service.py است. هر کدام باید default_enabled و default_sound مناسب داشته باشند. خارج از این مرحله: پیاده‌سازی منطق ارسال پیام با inline keyboard، scheduler، API endpoints، frontend، یا Telegram handlers. نکته حیاتی: reminder_due باید default_sound=True داشته باشد تا با صدا اعلام شود.
**Key terms:** backend/app/services/notification_service.py, EVENT_REGISTRY, reminder_due, reminder_snoozed, reminder_done, default_enabled, default_sound

**بخش مربوط از متن کاربر:**
```
رویدادهای جدید در EVENT_REGISTRY: reminder_due default_enabled=True, default_sound=True (با صدا) reminder_snoozed default_enabled=True, default_sound=False reminder_done default_enabled=True, default_sound=False
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن سه رویداد جدید reminder_due, reminder_snoozed, reminder_done به EVENT_REGISTRY در notification_service

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:119-320` — `EVENT_REGISTRY`
  ```python
  EVENT_REGISTRY: Dict[str, Dict[str, Any]] = {
      # Verify events
      "verify_done": {
          "label": "✅ Verify موفق",
          "help": "وقتی verify status = done باشد",
          "default_enabled": True,
          "default_sound": True,
          "icon": "✅",
      },
      ...
      "ai_balance_low": {
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن سه رویداد جدید reminder_due, reminder_snoozed, reminder_done به EVENT_REGISTRY در فایل backend/app/services/notification_service.py را دارد. هر کدام باید default_enabled و default_sound مناسب داشته باشند. خارج از این مرحله: پیاده‌سازی منطق ارسال پیام با inline keyboard، scheduler، API endpoints، frontend، یا Telegram handlers. نکته حیاتی: reminder_due باید default_sound=True داشته باشد تا با صدا اعلام شود. رویدادهای جدید در EVENT_REGISTRY: reminder_due default_enabled=True, default_sound=True (با صدا) reminder_snoozed default_enabled=True, default_sound=False reminder_done default_enabled=True, default_sound=False. کلیدواژه‌ها: backend/app/services/notification_service.py, EVENT_REGISTRY, reminder_due, reminder_snoozed, reminder_done, default_enabled, default_sound. شواهد در کد واقعی: فایل backend/app/services/notification_service.py از خط 119 تا 320 شامل EVENT_REGISTRY است که یک دیکشنری از رویدادها با کلیدهای label, help, default_enabled, default_sound, icon تعریف می‌کند. در حال حاضر رویدادهای verify, scan, task, idea, model_temp, pr, manual_test, daily_report, project, creator, smart_task, task_from_inspector, ai_balance_low وجود دارند. رویدادهای reminder (reminder_due, reminder_snoozed, reminder_done) در این رجیستری وجود ندارند و باید اضافه شوند. همچنین تابع _build_default_prefs در خط 323-347 از EVENT_REGISTRY برای ساخت prefs پیش‌فرض استفاده می‌کند و تابع _read_prefs در خط 350-369 نیز eventهای جدید را به prefs اضافه می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/notification_service.py، درون دیکشنری EVENT_REGISTRY (خطوط 119-320)، سه رویداد جدید با کلیدهای reminder_due, reminder_snoozed, reminder_done اضافه کن. 2. برای reminder_due: label='🔔 یادآوری موعد رسیده', help='وقتی یک یادآوری به زمان موعدش می‌رسد و باید به کاربر اطلاع داده شود', default_enabled=True, default_sound=True, icon='🔔'. 3. برای reminder_snoozed: label='⏰ یادآوری به تعویق افتاد', help='وقتی کاربر یادآوری را snooze می‌کند', default_enabled=True, default_sound=False, icon='⏰'. 4. برای reminder_done: label='✅ یادآوری انجام شد', help='وقتی یادآوری توسط کاربر done/archived می‌شود', default_enabled=True, default_sound=False, icon='✅'. 5. اطمینان حاصل کن که تابع _read_prefs (خطوط 350-369) به‌طور خودکار eventهای جدید را به prefs موجود اضافه می‌کند (این تابع در خطوط 362-366 حلقه می‌زند و eventهای جدید را از EVENT_REGISTRY به defaults['events'] و defaults['sound'] اضافه می‌کند، بنابراین نیازی به تغییر جداگانه نیست). 6. تابع _build_default_prefs (خطوط 323-347) نیز به‌طور خودکار از EVENT_REGISTRY می‌خواند، بنابراین نیازی به تغییر ندارد.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 5: پیاده‌سازی منطق scheduler_tick برای پردازش یادآوری‌های موعدرسیده

**Scope:** این مرحله شامل افزودن یک حلقه جدید در تابع scheduler_tick در فایل backend/app/services/oversight_service.py است. باید tasks با type=='reminder' و reminder_state in {'scheduled','snoozed'} و reminder_at <= now() را پیدا کند. برای هر کدام: ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی (فقط آیتم‌های done=False)، ارسال از طریق notify_event('reminder_due', ...) با inline_keyboard شامل دکمه‌های مرحله، done و snooze، update task به reminder_state='fired' و ذخیره reminder_message_id، و append به reminder_history. همچنین interval تیک scheduler حداکثر 60 ثانیه باشد. خارج از این مرحله: پیاده‌سازی callback handlers برای دکمه‌ها، API endpoints، frontend.
**Key terms:** backend/app/services/oversight_service.py, scheduler_tick, reminder_state, reminder_at, notify_event, reminder_due, inline_keyboard, reminder_step_tick, reminder_done, reminder_snooze_prompt, reminder_history

**بخش مربوط از متن کاربر:**
```
در scheduler_tick یک حلقه جدید: - یافتن tasks با type=='reminder' و reminder_state in {'scheduled','snoozed'} و reminder_at <= now() - برای هر کدام: 1) ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی (فقط آیتم‌های done=False) 2) ارسال از طریق notify_event('reminder_due', ...) با inline_keyboard: - برای هر مرحله pending → دکمه «✅ مرحلهٔ N» (callback reminder_step_tick:<task_id>:<step_id>) - یک ردیف برای: «✅ همه انجام شد» (reminder_done:<task_id>) - یک ردیف برای: «⏰ یادآوری دوباره» (reminder_snooze_prompt:<task_id>) 3) update task: reminder_state='fired', reminder_message_id=... 4) reminder_history.append({ts, action: 'fired'}) interval تیک scheduler حداکثر 60 ثانیه باشد تا یادآوری حداکثر با ۱ دقیقه تأخیر برسد
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن حلقه پردازش یادآوری‌های موعدرسیده در scheduler_tick در oversight_service.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:318-333` — `OversightTask dataclass (فیلدهای reminder)`
  ```python
  # 🆕 (Reminder feature) — فعال فقط زمانی که type=="reminder":
      # reminder_at: ISO datetime زمان firing بعدی (UTC).
      # reminder_state: گردش کار یادآوری.
      #   none      = نوع reminder نیست
      #   scheduled = منتظر firing
      #   fired     = الان firing شده، منتظر پاسخ کاربر (snooze / done / tick)
      #   snoozed   = کاربر snooze زده، reminder_at به آینده رفته
      #   done      = همهٔ آیتم‌ها انجام شدند، archived
      reminder_at: Optional[str] = None
      reminder_state: str = "none"
      # هر آیتم: {ts, action: "scheduled
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی منطق scheduler_tick برای پردازش یادآوری‌های موعدرسیده در فایل backend/app/services/oversight_service.py را دارد. این مرحله شامل افزودن یک حلقه جدید در تابع scheduler_tick است که باید tasks با type=='reminder' و reminder_state in {'scheduled','snoozed'} و reminder_at <= now() را پیدا کند. برای هر کدام: ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی (فقط آیتم‌های done=False)، ارسال از طریق notify_event('reminder_due', ...) با inline_keyboard شامل دکمه‌های مرحله، done و snooze، update task به reminder_state='fired' و ذخیره reminder_message_id، و append به reminder_history. همچنین interval تیک scheduler حداکثر 60 ثانیه باشد. خارج از این مرحله: پیاده‌سازی callback handlers برای دکمه‌ها، API endpoints، frontend. کلیدواژه‌های اصلی: backend/app/services/oversight_service.py, scheduler_tick, reminder_state, reminder_at, notify_event, reminder_due, inline_keyboard, reminder_step_tick, reminder_done, reminder_snooze_prompt, reminder_history. در کد فعلی oversight_service.py (خطوط 318-333) فیلدهای reminder_at، reminder_state، reminder_history، reminder_message_id، reminder_repeat_rule در dataclass OversightTask تعریف شده‌اند اما هیچ منطق پردازشی برای آن‌ها در scheduler_tick وجود ندارد. تابع scheduler_tick در حال حاضر در این فایل وجود ندارد و باید ایجاد شود. همچنین notify_event باید در oversight_service.py یا یک سرویس اعلان مرکزی پیاده‌سازی شود.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_service.py، یک تابع جدید به نام scheduler_tick اضافه کن که با interval حداکثر 60 ثانیه اجرا شود. 2. در این تابع، یک حلقه برای یافتن tasks با type=='reminder' و reminder_state in {'scheduled','snoozed'} و reminder_at <= now() بنویس. 3. برای هر task یافت‌شده: متن یادآوری را از task.title + task.prompt + task_steps (فقط آیتم‌های done=False) بساز. 4. از notify_event('reminder_due', ...) برای ارسال پیام با inline_keyboard شامل دکمه‌های «✅ مرحلهٔ N» (callback reminder_step_tick:<task_id>:<step_id>)، «✅ همه انجام شد» (reminder_done:<task_id>) و «⏰ یادآوری دوباره» (reminder_snooze_prompt:<task_id>) استفاده کن. 5. task.reminder_state را به 'fired' تغییر بده و reminder_message_id را ذخیره کن. 6. یک آیتم به reminder_history اضافه کن با {ts, action: 'fired'}. 7. تابع _save_tasks را برای ذخیره تغییرات فراخوانی کن. 8. scheduler_tick را در __init__ یا start scheduler ثبت کن تا به‌صورت دوره‌ای اجرا شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 6: پیاده‌سازی callback handler برای reminder_step_tick در تلگرام

**Scope:** این مرحله شامل پیاده‌سازی هندلر برای callback_data با الگوی reminder_step_tick:<task_id>:<step_id> در فایل backend/app/services/notification_service.py است. باید task_steps[step].done = True تنظیم شود، reminder_history.append انجام شود، همان پیام تلگرام با حذف آن دکمه و خط زدن آن مرحله از کپشن آپدیت شود. اگر همهٔ مراحل tick شدند → reminder_state='done', archived=True, notify reminder_done. خارج از این مرحله: هندلرهای reminder_done و reminder_snooze_prompt و reminder_snooze، API endpoints، frontend.
**Key terms:** backend/app/services/notification_service.py, reminder_step_tick, task_steps, reminder_history, reminder_done, callback_data

**بخش مربوط از متن کاربر:**
```
reminder_step_tick:<task_id>:<step_id> - task_steps[step].done = True - reminder_history.append({ts, action: 'step_ticked', step_id}) - update همان پیام تلگرام: حذف آن دکمه + خط زدن آن مرحله از کپشن - اگر همهٔ مراحل tick شدند → reminder_state='done', archived=True, notify reminder_done
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی callback handler برای reminder_step_tick در تلگرام

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:621-661` — `edit_message_text`
  ```python
  async def edit_message_text(
          self, chat_id: Any, message_id: int, text: str, *,
          reply_markup: Optional[Dict[str, Any]] = None,
          parse_mode: Optional[str] = "Markdown",
      ) -> Dict[str, Any]:
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی هندلر برای callback_data با الگوی `reminder_step_tick:<task_id>:<step_id>` در فایل `backend/app/services/notification_service.py` را دارد. این هندلر باید `task_steps[step].done = True` تنظیم کند، `reminder_history.append({ts, action: 'step_ticked', step_id})` انجام دهد، و همان پیام تلگرام را با حذف آن دکمه و خط زدن آن مرحله از کپشن آپدیت کند. اگر همهٔ مراحل tick شدند → `reminder_state='done', archived=True, notify reminder_done`. خارج از این مرحله: هندلرهای `reminder_done` و `reminder_snooze_prompt` و `reminder_snooze`، API endpoints، frontend. کلیدواژه‌ها: `backend/app/services/notification_service.py`, `reminder_step_tick`, `task_steps`, `reminder_history`, `reminder_done`, `callback_data`. در کد فعلی `notification_service.py` (خطوط 1-800 مشاهده شده)، کلاس `TelegramChannel` (خط 466) متدهای `edit_message_text` (خط 621) و `send_document` (خط 513) را دارد که برای آپدیت پیام و ارسال نوتیفیکیشن مناسب هستند. همچنین `EVENT_REGISTRY` (خط 119) شامل eventهای `reminder_due` (خط 201)، `reminder_snoozed` (خط 208)، `reminder_done` (خط 215) است. متد `edit_message_text` در خطوط 621-661 قابلیت ویرایش پیام با `reply_markup` را دارد. برای حذف دکمه از inline_keyboard، باید `reply_markup` جدید با آرایه‌ای فیلتر شده ارسال شود. برای خط زدن مرحله در کپشن، باید متن پیام با افزودن `~~` دور آن مرحله بازنویسی شود. برای notify `reminder_done`، باید از متد `send` کلاس `TelegramChannel` (خط 476) یا متد `send_document` (خط 513) استفاده شود. همچنین نیاز به ذخیره‌سازی state در `_INDEX_STATE_FILE` (خط 61) یا فایل مشابه برای persistence است.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل `backend/app/services/notification_service.py`، یک تابع جدید به نام `handle_reminder_step_tick` اضافه کن که `callback_data` را parse کند (الگوی `reminder_step_tick:<task_id>:<step_id>`). 2. در این تابع، `task_steps[step].done = True` تنظیم شود و `reminder_history.append({'ts': datetime.utcnow().isoformat(), 'action': 'step_ticked', 'step_id': step_id})` انجام شود. 3. با استفاده از `edit_message_text` (خط 621)، همان پیام تلگرام را آپدیت کن: `reply_markup` جدید با حذف دکمه مربوط به آن step (فیلتر کردن inline_keyboard) و متن کپشن با خط زدن آن مرحله (افزودن `~~` دور متن step). 4. اگر همهٔ مراحل `done` شدند → `reminder_state='done'`, `archived=True`, و `notify reminder_done` با فراخوانی `self.send` یا `self.send_document`. 5. هندلرهای مشابه برای `reminder_done`, `reminder_snooze_prompt`, `reminder_snooze` نیز پیاده‌سازی شوند. 6. API endpoints و frontend برای پشتیبانی از این callback_data اضافه شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 7: پیاده‌سازی callback handler برای reminder_done در تلگرام

**Scope:** این مرحله شامل پیاده‌سازی هندلر برای callback_data با الگوی reminder_done:<task_id> در فایل backend/app/services/notification_service.py است. باید همهٔ task_steps done=True تنظیم شود، reminder_state='done', archived=True، پیام تلگرام edit شود به '✅ یادآوری تمام شد و آرشیو شد'، و notify_event('reminder_done', ...) فراخوانی شود. خارج از این مرحله: هندلرهای reminder_step_tick و reminder_snooze_prompt و reminder_snooze، API endpoints، frontend.
**Key terms:** backend/app/services/notification_service.py, reminder_done, task_steps, reminder_state, archived, notify_event

**بخش مربوط از متن کاربر:**
```
reminder_done:<task_id> - همهٔ task_steps done=True - reminder_state='done', archived=True - edit پیام: «✅ یادآوری تمام شد و آرشیو شد» - notify_event('reminder_done', ...)
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی callback handler برای reminder_done در تلگرام در notification_service.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:200-221` — `EVENT_REGISTRY['reminder_done']`
  ```python
  "reminder_done": {
          "label": "✅ یادآوری انجام شد",
          "help": "وقتی یادآوری توسط کاربر done/archived می‌شود",
          "default_enabled": True,
          "default_sound": False,
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی هندلر برای callback_data با الگوی reminder_done:<task_id> در فایل backend/app/services/notification_service.py را دارد. این هندلر باید هنگام دریافت callback_data با پیشوند reminder_done، task_id را استخراج کند، سپس همهٔ task_steps مربوط به آن task را به done=True تنظیم کند، reminder_state را به 'done' و archived=True تغییر دهد. پس از آن، پیام تلگرام موجود باید ویرایش (edit) شود به متن «✅ یادآوری تمام شد و آرشیو شد». در نهایت، notify_event('reminder_done', ...) فراخوانی شود تا رویداد reminder_done در سیستم نوتیفیکیشن ثبت و ارسال شود. کاربر تأکید کرده که خارج از این مرحله، هندلرهای reminder_step_tick، reminder_snooze_prompt، reminder_snooze، API endpoints و frontend قرار دارند و فقط همین callback handler مد نظر است. کلیدواژه‌های اصلی: backend/app/services/notification_service.py, reminder_done, task_steps, reminder_state, archived, notify_event. در کد فعلی notification_service.py (خطوط 200-221) رویداد reminder_done در EVENT_REGISTRY تعریف شده است: label='✅ یادآوری انجام شد', help='وقتی یادآوری توسط کاربر done/archived می‌شود', default_enabled=True, default_sound=False, icon='✅'. همچنین کلاس TelegramChannel (خط 466) متدهای send, edit_message_text, send_document و غیره را دارد. متد edit_message_text در خطوط 621-661 پیاده‌سازی شده که برای ویرایش پیام موجود استفاده می‌شود. notify_event در بخش سرویس (خطوط 800+) احتمالاً تابعی است که event را به کانال‌های مختلف ارسال می‌کند. همچنین در خطوط 89-112 PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES تعریف شده که نشان‌دهنده وجود reply keyboard برای دستورات است. برای پیاده‌سازی این هندلر، باید یک تابع async جدید به نام handle_reminder_done_callback یا مشابه اضافه شود که callback_data را parse کند، task_id را استخراج، task_steps را به‌روزرسانی، پیام را edit و notify_event را صدا بزند.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/notification_service.py، یک تابع async جدید به نام handle_reminder_done_callback اضافه کن که پارامترهای callback_data (رشته‌ای مثل 'reminder_done:task_123') و chat_id و message_id را دریافت کند. 2. داخل تابع، callback_data را با split(':') تجزیه کن تا task_id استخراج شود. 3. با استفاده از یک db_session (یا سرویس task)، همهٔ task_steps مربوط به task_id را پیدا کن و فیلد done را به True تنظیم کن. 4. reminder_state را به 'done' و archived=True در دیتابیس به‌روزرسانی کن. 5. با self.edit_message_text (از TelegramChannel) پیام موجود را به متن «✅ یادآوری تمام شد و آرشیو شد» ویرایش کن. 6. notify_event('reminder_done', task_id=task_id, ...) را فراخوانی کن تا رویداد ثبت شود. 7. هندلر را در webhook handler (احتمالاً در همان فایل یا در oversight_service) ثبت کن تا هنگام دریافت callback_query با data.startswith('reminder_done:') فعال شود. 8. اطمینان حاصل کن که خطاها (مثل task_id نامعتبر) به درستی لاگ و مدیریت شوند.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 8: پیاده‌سازی callback handlers برای reminder_snooze_prompt و reminder_snooze در تلگرام

**Scope:** این مرحله شامل پیاده‌سازی دو هندلر است. اولی برای callback_data با الگوی reminder_snooze_prompt:<task_id> که یک پیام جدید با inline_keyboard گزینه‌های snooze (۱۵ دقیقه، ۱ ساعت، ۳ ساعت، فردا ۹ صبح، انتخاب دستی) ارسال می‌کند. دومی برای reminder_snooze:<task_id>:<delta_or_iso> که reminder_at = now() + delta (یا ISO خام) تنظیم می‌کند، reminder_state='snoozed'، reminder_history.append انجام می‌دهد، notify_event('reminder_snoozed', ...) فراخوانی می‌کند، و پیام قبلی edit می‌شود به '⏰ به <new_at> موکول شد'. خارج از این مرحله: هندلرهای reminder_step_tick و reminder_done، API endpoints، frontend.
**Key terms:** backend/app/services/notification_service.py, reminder_snooze_prompt, reminder_snooze, inline_keyboard, reminder_at, reminder_state, reminder_history, notify_event

**بخش مربوط از متن کاربر:**
```
reminder_snooze_prompt:<task_id> - ارسال پیام جدید با inline_keyboard گزینه‌های snooze: «۱۵ دقیقه دیگر»، «۱ ساعت دیگر»، «۳ ساعت دیگر»، «فردا ۹ صبح»، «انتخاب دستی» reminder_snooze:<task_id>:<delta_or_iso> - reminder_at = now() + delta (یا ISO خام) - reminder_state='snoozed' - reminder_history.append({ts, action: 'snoozed', new_at}) - notify_event('reminder_snoozed', ...) - پیام قبلی edit: «⏰ به <new_at> موکول شد»
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی callback handlers برای reminder_snooze_prompt و reminder_snooze در تلگرام

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی دو هندلر callback در تلگرام را دارد. اولی برای callback_data با الگوی reminder_snooze_prompt:<task_id> که یک پیام جدید با inline_keyboard گزینه‌های snooze (۱۵ دقیقه، ۱ ساعت، ۳ ساعت، فردا ۹ صبح، انتخاب دستی) ارسال می‌کند. دومی برای reminder_snooze:<task_id>:<delta_or_iso> که reminder_at = now() + delta (یا ISO خام) تنظیم می‌کند، reminder_state='snoozed'، reminder_history.append انجام می‌دهد، notify_event('reminder_snoozed', ...) فراخوانی می‌کند، و پیام قبلی edit می‌شود به '⏰ به <new_at> موکول شد'. خارج از این مرحله: هندلرهای reminder_step_tick و reminder_done، API endpoints، frontend. کلیدواژه‌های ذکر شده: backend/app/services/notification_service.py, reminder_snooze_prompt, reminder_snooze, inline_keyboard, reminder_at, reminder_state, reminder_history, notify_event. در کد واقعی پروژه، فایل backend/app/services/notification_service.py حاوی کلاس TelegramChannel با متدهای send, edit_message_text, send_with_reply_keyboard, remove_reply_keyboard و همچنین EVENT_REGISTRY شامل رویدادهای reminder_due (خط 201-207)، reminder_snoozed (خط 208-214)، reminder_done (خط 215-221) است. متد edit_message_text در خطوط 621-661 پیاده‌سازی شده که برای ویرایش پیام قبلی به '⏰ به <new_at> موکول شد' استفاده می‌شود. متد send_with_reply_keyboard در خطوط 663-704 برای ارسال پیام با ReplyKeyboard موجود است اما برای inline_keyboard باید از ساختار reply_markup در sendMessage استفاده کرد. تابع build_inline_keyboard در خطوط 412-444 برای ساخت inline_keyboard context-aware بر اساس event وجود دارد. تابع notify_event در ادامه فایل (بخش سرویس) برای فراخوانی رویدادها استفاده می‌شود. همچنین فایل‌های مرتبط مانند backend/app/api/routes/notifications.py و backend/app/services/oversight_telegram_compose.py برای مدیریت webhook و کامپوز پیام‌ها وجود دارند.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/notification_service.py، یک تابع جدید به نام handle_reminder_snooze_prompt ایجاد کن که callback_data با الگوی reminder_snooze_prompt:<task_id> را پردازش کند. این تابع باید با استفاده از متد send (خطوط 476-511) یک پیام جدید با inline_keyboard شامل گزینه‌های '۱۵ دقیقه دیگر', '۱ ساعت دیگر', '۳ ساعت دیگر', 'فردا ۹ صبح', 'انتخاب دستی' ارسال کند. برای ساخت inline_keyboard از تابع build_inline_keyboard (خطوط 412-444) الگو بگیر اما با callback_data مخصوص. 2. یک تابع جدید به نام handle_reminder_snooze ایجاد کن که callback_data با الگوی reminder_snooze:<task_id>:<delta_or_iso> را پردازش کند. این تابع باید: a) reminder_at = now() + delta (یا ISO خام) محاسبه کند، b) reminder_state را به 'snoozed' تنظیم کند، c) یک رکورد به reminder_history اضافه کند با {ts, action: 'snoozed', new_at}، d) notify_event('reminder_snoozed', ...) را فراخوانی کند، e) با استفاده از متد edit_message_text (خطوط 621-661) پیام قبلی را به '⏰ به <new_at> موکول شد' ویرایش کند. 3. هندلرها را در webhook handler موجود در فایل (بخش webhook handler در خطوط 725-750) ثبت کن تا callback_dataهای مربوطه شناسایی و پردازش شوند. 4. اطمینان حاصل کن که reminder_history به درستی ذخیره و بازیابی می‌شود (احتمالاً از طریق دیتابیس یا فایل JSON).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 9: افزودن دکمه «🔔 یادآوری جدید» به منوی تلگرام و پیاده‌سازی flow آن

**Scope:** این مرحله شامل افزودن دکمه جدید '🔔 یادآوری جدید' به منوی اصلی تلگرام در فایل backend/app/services/notification_service.py است. flow باید شامل: 1) انتخاب پروژه (یا 'بدون پروژه')، 2) ورود به compose mode با mode='reminder' (مشابه task با پشتیبانی پیوست/صوت)، 3) submit → ask date/time با گزینه‌های پیش‌فرض inline ('۱ ساعت دیگر', 'امروز عصر', 'فردا ۹ صبح', 'انتخاب دستی')، 4) create task با type='reminder', reminder_state='scheduled', reminder_at=picked. خارج از این مرحله: API endpoints، frontend، callback handlers دیگر.
**Key terms:** backend/app/services/notification_service.py, 🔔 یادآوری جدید, compose mode, mode='reminder', date/time, reminder_state, reminder_at

**بخش مربوط از متن کاربر:**
```
دکمهٔ جدید در منو اصلی: «🔔 یادآوری جدید» — flow: 1) انتخاب پروژه (یا «بدون پروژه») 2) ورود به compose mode با mode='reminder' (مشابه task، با پشتیبانی پیوست/صوت/...) 3) submit → ask date/time (با گزینه‌های پیش‌فرض inline: «۱ ساعت دیگر»، «امروز عصر»، «فردا ۹ صبح»، «انتخاب دستی») 4) create task با type='reminder', reminder_state='scheduled', reminder_at=picked
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن دکمه «🔔 یادآوری جدید» به منوی تلگرام و پیاده‌سازی flow ایجاد یادآوری با compose mode

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن دکمه جدید «🔔 یادآوری جدید» به منوی اصلی تلگرام در فایل backend/app/services/notification_service.py را دارد. flow باید شامل مراحل زیر باشد: 1) انتخاب پروژه (یا 'بدون پروژه')، 2) ورود به compose mode با mode='reminder' (مشابه task با پشتیبانی پیوست/صوت)، 3) submit → ask date/time با گزینه‌های پیش‌فرض inline ('۱ ساعت دیگر', 'امروز عصر', 'فردا ۹ صبح', 'انتخاب دستی')، 4) create task با type='reminder', reminder_state='scheduled', reminder_at=picked. خارج از این مرحله: API endpoints، frontend، callback handlers دیگر.

شواهد در کد واقعی:
- در فایل backend/app/services/notification_service.py، خطوط 89-112، PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES تعریف شده‌اند. دکمه‌های فعلی شامل: «📋 ایندکس», «🆕 تسک جدید», «📚 شناسنامه», «🚀 پروژه جدید», «📊 وضعیت», «📋 منو», «💰 مصرف AI», «❌ بستن منو» هستند. دکمه «🔔 یادآوری جدید» باید به این لیست اضافه شود.
- در خطوط 200-221، EVENT_REGISTRY شامل رویدادهای reminder_due, reminder_snoozed, reminder_done است که نشان‌دهنده پشتیبانی قبلی از reminder در سیستم نوتیفیکیشن است.
- در فایل backend/app/services/oversight_telegram_compose.py، خطوط 83-142، کلاس ComposeBuffer و ComposeItem تعریف شده‌اند. mode='task' و mode='project' پشتیبانی می‌شوند. mode='reminder' باید اضافه شود.
- در خط 91 از oversight_telegram_compose.py، فیلد mode: str = "task" # "task" | "project" تعریف شده که باید به "task" | "project" | "reminder" تغییر کند.
- کلیدواژه‌های کاربر: backend/app/services/notification_service.py, 🔔 یادآوری جدید, compose mode, mode='reminder', date/time, reminder_state, reminder_at

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/notification_service.py:
   - به PERSISTENT_REPLY_KEYBOARD (خط 89-99) دکمه جدید «🔔 یادآوری جدید» اضافه شود.
   - به TEXT_ALIASES (خط 103-112) نگاشت «🔔 یادآوری جدید»: '/new_reminder' اضافه شود.

2. در فایل backend/app/services/oversight_telegram_compose.py:
   - در خط 91، نوع mode به "task" | "project" | "reminder" تغییر کند.
   - در خط 42-51، SUPPORTED_MEDIA_TYPES برای reminder نیز پشتیبانی شود (همانند task).
   - تابع جدیدی برای handle_reminder_submit اضافه شود که پس از submit، تاریخ/زمان را با inline keyboard بپرسد.

3. در فایل backend/app/services/notification_service.py:
   - EVENT_REGISTRY (خط 119-320) رویداد جدید 'reminder_created' با label "🔔 یادآوری جدید ساخته شد" اضافه شود.
   - در build_inline_keyboard (خط 412-444) برای event='reminder_created' دکمه‌های مناسب اضافه شود.

4. در فایل backend/app/services/oversight_telegram_compose.py:
   - تابع async def ask_reminder_datetime(chat_id: str, buffer: ComposeBuffer) اضافه شود که inline keyboard با گزینه‌های '۱ ساعت دیگر', 'امروز عصر', 'فردا ۹ صبح', 'انتخاب دستی' ارسال کند.
   - تابع async def handle_datetime_selection(chat_id: str, callback_data: str) برای پردازش انتخاب کاربر.

5. در فایل backend/app/services/

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 10: افزودن API endpoints جدید برای مدیریت یادآوری‌ها

**Scope:** این مرحله شامل افزودن چهار endpoint جدید به فایل backend/app/api/routes/oversight.py است: POST /tasks/{id}/reminder/snooze (body: {until?: ISO, delta_seconds?: int} → set reminder_at, state='snoozed'), POST /tasks/{id}/reminder/done (→ state='done', archived=True), PATCH /tasks/{id}/reminder/step/{step_id} (body: {done: bool} → toggle task_steps[step].done), و به‌روزرسانی POST /tasks برای پذیرش type='reminder' + reminder_at + reminder_repeat_rule. خارج از این مرحله: frontend، Telegram handlers، scheduler.
**Key terms:** backend/app/api/routes/oversight.py, POST /tasks/{id}/reminder/snooze, POST /tasks/{id}/reminder/done, PATCH /tasks/{id}/reminder/step/{step_id}, POST /tasks, reminder_at, reminder_repeat_rule

**بخش مربوط از متن کاربر:**
```
POST /tasks/{id}/reminder/snooze body: {until?: ISO, delta_seconds?: int} → set reminder_at, state='snoozed' POST /tasks/{id}/reminder/done → state='done', archived=True PATCH /tasks/{id}/reminder/step/{step_id} body: {done: bool} → toggle task_steps[step].done POST /tasks input هم type='reminder' + reminder_at + reminder_repeat_rule اضافه شود
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن API endpoints جدید برای مدیریت یادآوری‌ها در oversight.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/oversight.py:416-516` — `Reminder endpoints (snooze, done, step toggle)`
  ```python
  class ReminderSnoozeRequest(BaseModel):
      until: Optional[str] = None        # ISO datetime
      delta_seconds: Optional[int] = None  # یا delta از
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن چهار endpoint جدید به فایل backend/app/api/routes/oversight.py را دارد: 1) POST /tasks/{id}/reminder/snooze با body شامل {until?: ISO, delta_seconds?: int} که reminder_at را تنظیم کرده و state را به 'snoozed' تغییر دهد. 2) POST /tasks/{id}/reminder/done که state را به 'done' و archived=True تنظیم کند. 3) PATCH /tasks/{id}/reminder/step/{step_id} با body {done: bool} که task_steps[step].done را toggle کند. 4) به‌روزرسانی POST /tasks برای پذیرش فیلدهای type='reminder'، reminder_at و reminder_repeat_rule. این درخواست بر اساس قابلیت یادآوری (Reminder feature) است که در commit 67441ae اضافه شده و در frontend/src/app/oversight/page.tsx (خطوط 231-236) و backend/app/api/routes/oversight.py (خطوط 416-516) پیاده‌سازی اولیه آن دیده می‌شود. در frontend، تایپ Task شامل فیلدهای reminder_at (خط 232)، reminder_state (خط 233)، reminder_history (خط 234)، reminder_message_id (خط 235) و reminder_repeat_rule (خط 236) است. در backend، endpoint‌های reminder/snooze (خطوط 426-453)، reminder/done (خطوط 456-476) و reminder/step/{step_id} (خطوط 479-515) قبلاً پیاده‌سازی شده‌اند اما کاربر درخواست افزودن مجدد آن‌ها را دارد که نشان‌دهنده نیاز به بازبینی و اطمینان از صحت پیاده‌سازی است. همچنین در TaskCreate (خطوط 81-106) فیلدهای reminder_at و reminder_repeat_rule تعریف شده‌اند (خطوط 104-105).

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی endpoint‌های موجود در backend/app/api/routes/oversight.py: خطوط 426-453 (reminder/snooze)، 456-476 (reminder/done)، 479-515 (reminder/step/{step_id}) و خطوط 328-343 (POST /tasks). 2. اطمینان از اینکه مدل Pydantic ReminderSnoozeRequest (خطوط 417-419) و ReminderStepToggleRequest (خطوط 422-423) به درستی تعریف شده‌اند. 3. بررسی منطق snooze در خطوط 426-453: دریافت task از service.tasks (خط 430)، تنظیم reminder_at (خط 446)، state='snoozed' (خط 447)، ثبت history (خطوط 448-450) و ذخیره (خط 452). 4. بررسی منطق done در خطوط 456-476: تنظیم همه task_steps به done (خطوط 464-467)، state='done' (خط 468)، archived=True (خط 469)، ثبت history (خطوط 471-473) و ذخیره (خط 475). 5. بررسی منطق step toggle در خطوط 479-515: یافتن step با id (خط 491)، toggle done (خط 492)، تنظیم status و completion_pct (خطوط 493-494)، ثبت completed_at (خط 496)، بررسی همه steps برای auto-done (خطوط 506-512). 6. بررسی TaskCreate (خطوط 81-106) برای اطمینان از وجود reminder_at (خط 104) و reminder_repeat_rule (خط 105). 7. تست هر endpoint با curl یا pytest. 8. اطمینان از اینکه frontend (frontend/src/app/oversight/page.tsx خطوط 231-236) با backend هماهنگ است.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 11: پیاده‌سازی تغییرات فرانت‌اند برای پشتیبانی از نوع یادآوری

**Scope:** این مرحله شامل تغییرات در فایل frontend/src/app/oversight/page.tsx است: افزودن '🔔 یادآوری' با value='reminder' به type dropdown (خط ~2593)، نمایش input datetime-local و dropdown تکرار (یک‌بار/روزانه/هفتگی) وقتی type=reminder انتخاب شد، نمایش بادج 🔔 + reminder_at human-friendly در task list، و در مدال جزئیات تسک reminder: چک‌لیست task_steps با checkbox برای هر آیتم که PATCH .../reminder/step/{id} را فراخوانی می‌کند، دکمه '⏰ Snooze' با پنل تاریخ، دکمه '✅ تمام شد'، و بخش '📅 history' با timeline. خارج از این مرحله: backend API endpoints، Telegram handlers، scheduler.
**Key terms:** frontend/src/app/oversight/page.tsx, type dropdown, 🔔 یادآوری, datetime-local, dropdown تکرار, task list, بادج 🔔, مدال جزئیات, task_steps, checkbox, PATCH .../reminder/step/{id}, Snooze, history

**بخش مربوط از متن کاربر:**
```
type dropdown — افزودن «🔔 یادآوری» با value='reminder' وقتی type=reminder انتخاب شد: - input تاریخ + ساعت ظاهر شود (datetime-local) - dropdown «تکرار»: یک‌بار / روزانه / هفتگی task list — برای reminders بادج 🔔 + reminder_at human-friendly («در ۲ ساعت دیگر»، «دیروز ساعت ۹») در مدال جزئیات تسک reminder: - چک‌لیست task_steps با checkbox برای هر آیتم - PATCH .../reminder/step/{id} وقتی checkbox تغییر کرد - دکمه «⏰ Snooze» (پنل تاریخ)، «✅ تمام شد» - بخش «📅 history» با timeline (scheduled→fired→snoozed→done)
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن پشتیبانی فرانت‌اند برای نوع تسک یادآوری (Reminder) در صفحه Oversight

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی تغییرات فرانت‌اند در فایل frontend/src/app/oversight/page.tsx برای پشتیبانی از نوع تسک یادآوری (type='reminder'). این تغییرات شامل موارد زیر است:

1. **type dropdown (خط ~2593)**: افزودن گزینه '🔔 یادآوری' با value='reminder' به dropdown انتخاب نوع تسک.
2. **فیلدهای شرطی برای reminder**: وقتی type=reminder انتخاب شد، یک input datetime-local برای انتخاب تاریخ و ساعت و یک dropdown تکرار (یک‌بار/روزانه/هفتگی) نمایش داده شود.
3. **task list**: برای تسک‌های reminder، یک بادج 🔔 و نمایش human-friendly reminder_at (مثلاً «در ۲ ساعت دیگر»، «دیروز ساعت ۹») در لیست تسک‌ها.
4. **مدال جزئیات تسک reminder**: 
   - چک‌لیست task_steps با checkbox برای هر آیتم که با تغییر وضعیت، PATCH /oversight/tasks/{task_id}/reminder/step/{id} را فراخوانی کند.
   - دکمه '⏰ Snooze' که یک پنل انتخاب تاریخ باز کند.
   - دکمه '✅ تمام شد' که PATCH /oversight/tasks/{task_id}/reminder/done را فراخوانی کند.
   - بخش '📅 history' با نمایش timeline از reminder_history.

کلیدواژه‌های کاربر: frontend/src/app/oversight/page.tsx, type dropdown, 🔔 یادآوری, datetime-local, dropdown تکرار, task list, بادج 🔔, مدال جزئیات, task_steps, checkbox, PATCH .../reminder/step/{id}, Snooze, history.

شواهد در کد: در فایل backend/app/api/routes/oversight.py خطوط 103-105 فیلدهای reminder_at و reminder_repeat_rule در مدل TaskCreate تعریف شده‌اند. خطوط 416-515 endpointهای reminder/snooze، reminder/done و reminder/step/{id} پیاده‌سازی شده‌اند. در frontend/src/app/oversight/page.tsx خطوط 231-236 فیلدهای reminder_at، reminder_state، reminder_history و reminder_repeat_rule در interface Task تعریف شده‌اند. خطوط 294-302 TYPE_ICONS شامل 'reminder: 🔔' است.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 12: تست و اعتبارسنجی کامل قابلیت یادآوری در تمام لایه‌ها

**Scope:** این مرحله شامل تست و اعتبارسنجی کامل قابلیت یادآوری است: بررسی mypy/tsc بدون error در هر دو سمت، backend startup بدون crash، frontend build موفق، تست flow کامل از تلگرام ('🔔 یادآوری جدید' → ارسال صدا → submit → date pick → ذخیره)، تست دستی scheduler تیک (یادآوری در زمان موعد ارسال می‌شود)، تست tick روی یک checkbox از تلگرام (آن آیتم در فرانت هم done شد)، تست tick کل از فرانت (reminder در تلگرام دیگر نمی‌آید + archived). خارج از این مرحله: پیاده‌سازی ویژگی‌های جدید دیگر.
**Key terms:** mypy, tsc, backend startup, frontend build, 🔔 یادآوری جدید, scheduler تیک, checkbox, تلگرام, فرانت, archived

**بخش مربوط از متن کاربر:**
```
Tests / Validation not done mypy/tsc هر دو سمت بدون error not done backend startup بدون crash not done frontend build موفق not done از تلگرام: «🔔 یادآوری جدید» → ارسال صدا → submit → date pick → ذخیره not done دستی scheduler تیک: یادآوری در زمان موعد ارسال می‌شود not done tick روی یک checkbox از تلگرام → آن آیتم در فرانت هم done شد not done tick کل از فرانت → reminder در تلگرام دیگر نمی‌آید + archived
```

## 🎯 هدف (خلاصه ساختاریافته)
تست و اعتبارسنجی کامل قابلیت یادآوری (Reminder) در تمام لایه‌ها — mypy/tsc، startup، build، flow تلگرام، scheduler، tick checkbox

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست تست و اعتبارسنجی کامل قابلیت یادآوری (Reminder) را در تمام لایه‌های پروژه داده است. این یک feature_request با اولویت high است. متن خام کاربر شامل موارد زیر است: «تست و اعتبارسنجی کامل قابلیت یادآوری در تمام لایه‌ها — این مرحله شامل تست و اعتبارسنجی کامل قابلیت یادآوری است: بررسی mypy/tsc بدون error در هر دو سمت، backend startup بدون crash، frontend build موفق، تست flow کامل از تلگرام ('🔔 یادآوری جدید' → ارسال صدا → submit → date pick → ذخیره)، تست دستی scheduler تیک (یادآوری در زمان موعد ارسال می‌شود)، تست tick روی یک checkbox از تلگرام (آن آیتم در فرانت هم done شد)، تست tick کل از فرانت (reminder در تلگرام دیگر نمی‌آید + archived). خارج از این مرحله: پیاده‌سازی ویژگی‌های جدید دیگر.» همچنین بخش مربوط از درخواست اصلی کاربر: «Tests / Validation not done mypy/tsc هر دو سمت بدون error not done backend startup بدون crash not done frontend build موفق not done از تلگرام: «🔔 یادآوری جدید» → ارسال صدا → submit → date pick → ذخیره not done دستی scheduler تیک: یادآوری در زمان موعد ارسال می‌شود not done tick روی یک checkbox از تلگرام → آن آیتم در فرانت هم done شد not done tick کل از فرانت → reminder در تلگرام دیگر نمی‌آید + archived». کلیدواژه‌ها: mypy, tsc, backend startup, frontend build, 🔔 یادآوری جدید, scheduler تیک, checkbox, تلگرام, فرانت, archived. بر اساس کد واقعی پروژه، قابلیت یادآوری (Reminder) در کامیت اخیر `67441ae feat(reminder): add reminder task type with Telegram firing + checklist` اضافه شده است. فایل‌های مرتبط شامل `backend/app/services/background_scheduler.py` (خطوط 1-786) است که سرویس زمان‌بندی کارهای پس‌زمینه را مدیریت می‌کند و شامل jobهایی مانند `JOB_AUTO_TRANSFER`، `JOB_HEALTH_ANALYSIS`، `JOB_DYNAMIC_FIELDS`، `JOB_SECURITY_TRANSFER`، `JOB_TEST_COVERAGE_TRANSFER` و `JOB_ENGINEERING_REPORT` است. همچنین فایل `backend/app/services/notification_service.py` و `backend/app/services/oversight_telegram_compose.py` برای ارسال نوتیفیکیشن تلگرام استفاده می‌شوند. فایل `backend/app/api/routes/oversight.py` و `frontend/src/app/oversight/page.tsx` نیز مرتبط هستند. برای اعتبارسنجی، باید flow کامل از تلگرام ('🔔 یادآوری جدید' → ارسال صدا → submit → date pick → ذخیره) تست شود، scheduler تیک (یادآوری در زمان موعد ارسال می‌شود)، tick روی یک checkbox از تلگرام (آن آیتم در فرانت هم done شد)، tick کل از فرانت (reminder در تلگرام دیگر نمی‌آید + archived).

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **بررسی mypy در سمت backend**: دستور `mypy backend/app/` را اجرا کن و تمام errorهای مربوط به فایل‌های reminder/scheduler/notification را رفع کن. فایل‌های هدف: `backend/app/services/background_scheduler.py` (خطوط 1-786)، `backend/app/services/notification_service.py`، `backend/app/services/oversight_telegram_compose.py`. 2. **بررسی tsc در سمت frontend**: دستور `npx tsc --noEmit` را در پوشه `frontend/` اجرا کن و errorهای مربوط به کامپوننت‌های reminder/oversight را رفع کن. فایل‌های هدف: `frontend/src/app/oversight/page.tsx`، `frontend/src/app/InspectorBridge.tsx`. 3. **

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

## ✅ معیارهای پذیرش کلی (همهٔ مراحل)
- [ ] همهٔ مراحل بالا با موفقیت پیاده‌سازی شده‌اند
- [ ] تست‌های موجود pass می‌شوند
- [ ] هیچ regression رخ نداده

## Acceptance Criteria

1. فیلدهای جدید روی OversightTask: _(verify: static)_
2. task.type می‌تواند "reminder" باشد — لیست انواع به‌روزرسانی شد _(verify: static)_
3. task_steps هر کدام فیلد done: bool — برای reminder هر آیتم چک‌لیست _(verify: static)_

## Task Steps

### Step 1: افزودن فیلدهای جدید به دیتامدل OversightTask برای پشتیبانی از یادآوری
**Status:** `done` (100%)
**Scope:** این مرحله شامل افزودن فیلدهای جدید reminder_at, reminder_state, reminder_history, reminder_message_id, reminder_repeat_rule به کلاس OversightTask در فایل backend/app/services/oversight_service.py است. همچنین باید type='reminder' به لیست انواع معتبر اضافه شود و فیلد done به task_steps اضافه گردد. خارج از این مرحله: تغییر در پرامپت‌ساز، notification events، scheduler، API endpoints، frontend، یا Telegram handlers. نکته حیاتی: این تغییرات باید backward-compatible باشند و فیلدهای جدید مقادیر پیش‌فرض داشته باشند.
**Excerpt:**
```
فیلدهای جدید روی OversightTask: reminder_at: Optional[str] # ISO datetime، زمان firing بعدی reminder_state: str = 'none' # none | scheduled | fired | snoozed | done reminder_history: List[Dict] # [{ts, action: scheduled/fired/snoozed/done/step_ticked, payload}] reminder_message_id: Optional[int] # message_id آخرین یادآوری در تلگرام reminder_repeat_rule: Optional[str] # «daily» | «weekly» | None (آینده) task.type می‌تواند 'reminder' باشد — لیست انواع به‌روزرسانی شد task_steps هر کدام فیلد done: bool — برای reminder هر آیتم چک‌لیست قابل تیک شدن است
```

### Step 2: تغییر build_strong_prompt برای type=reminder با لحن و ساختار متفاوت
**Status:** `done` (100%)
**Scope:** این مرحله شامل تغییر تابع build_strong_prompt در فایل backend/app/services/oversight_strong_prompt.py است. وقتی type=='reminder'، باید یک نسخه متفاوت با حذف EXECUTOR_DISCLAIMER عمومی و جایگزینی با 'یادداشت یادآوری' با لحن دوستانه و کوتاه ساخته شود. بدون بخش‌های target_locations/AC/commands. چک‌لیست باید action items عملی باشد. خارج از این مرحله: تغییر idea_to_prompt، notification events، scheduler، API endpoints، frontend، یا Telegram handlers.
**Excerpt:**
```
اگر type=='reminder'، build_strong_prompt یک نسخهٔ متفاوت با EXECUTOR_DISCLAIMER عمومی **حذف می‌شود** (این یادآوری شخصی است نه پرامپت اجرایی برای مدل کدنویس) و به‌جای آن یک «یادداشت یادآوری» با لحن دوستانه و کوتاه می‌سازد: - بدون «target_locations» / «AC» / «commands» - چک‌لیست = action items عملی (مثل: «به X زنگ بزن»، «دارو بخر») - اگر کاربر یک فایل صوتی توضیح وظایف را گفت، چک‌لیست خروجی همان آیتم‌ها است
```

### Step 3: تغییر idea_to_prompt برای type=reminder با system prompt و multi-pass متفاوت
**Status:** `done` (100%)
**Scope:** این مرحله شامل تغییر تابع idea_to_prompt در فایل backend/app/services/oversight_service.py است. وقتی type=='reminder'، system prompt مدل باید به جای 'build prompt برای engineer' بگوید 'این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.' همچنین multi_pass باید force=always با scope 'reminder' باشد (هدفش split به check-items است، نه به sub-prompts). خارج از این مرحله: تغییر build_strong_prompt، notification events، scheduler، API endpoints، frontend، یا Telegram handlers.
**Excerpt:**
```
idea_to_prompt هنگام type=='reminder': - system prompt مدل به جای «build prompt برای engineer» می‌گوید «این یک یادآوری شخصی است؛ آن را به چک‌لیست action items شخصی تبدیل کن. هر آیتم باید کوتاه و قابل تیک باشد.» - multi_pass force=always با scope «reminder» (هدفش split به check-items است، نه به sub-prompts)
```

### Step 4: افزودن رویدادهای جدید reminder به EVENT_REGISTRY در notification_service
**Status:** `done` (100%)
**Scope:** این مرحله شامل افزودن سه رویداد جدید reminder_due, reminder_snoozed, reminder_done به EVENT_REGISTRY در فایل backend/app/services/notification_service.py است. هر کدام باید default_enabled و default_sound مناسب داشته باشند. خارج از این مرحله: پیاده‌سازی منطق ارسال پیام با inline keyboard، scheduler، API endpoints، frontend، یا Telegram handlers. نکته حیاتی: reminder_due باید default_sound=True داشته باشد تا با صدا اعلام شود.
**Excerpt:**
```
رویدادهای جدید در EVENT_REGISTRY: reminder_due default_enabled=True, default_sound=True (با صدا) reminder_snoozed default_enabled=True, default_sound=False reminder_done default_enabled=True, default_sound=False
```

### Step 5: پیاده‌سازی منطق scheduler_tick برای پردازش یادآوری‌های موعدرسیده
**Status:** `done` (100%)
**Scope:** این مرحله شامل افزودن یک حلقه جدید در تابع scheduler_tick در فایل backend/app/services/oversight_service.py است. باید tasks با type=='reminder' و reminder_state in {'scheduled','snoozed'} و reminder_at <= now() را پیدا کند. برای هر کدام: ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی (فقط آیتم‌های done=False)، ارسال از طریق notify_event('reminder_due', ...) با inline_keyboard شامل دکمه‌های مرحله، done و snooze، update task به reminder_state='fired' و ذخیره reminder_message_id، و append به reminder_history. همچنین interval تیک scheduler حداکثر 60 ثانیه باشد. خارج از این مرحله: پیاده‌سازی callback handlers برای دکمه‌ها، API endpoints، frontend.
**Excerpt:**
```
در scheduler_tick یک حلقه جدید: - یافتن tasks با type=='reminder' و reminder_state in {'scheduled','snoozed'} و reminder_at <= now() - برای هر کدام: 1) ساخت متن یادآوری از task.title + task.prompt + task_steps فعلی (فقط آیتم‌های done=False) 2) ارسال از طریق notify_event('reminder_due', ...) با inline_keyboard: - برای هر مرحله pending → دکمه «✅ مرحلهٔ N» (callback reminder_step_tick:<task_id>:<step_id>) - یک ردیف برای: «✅ همه انجام شد» (reminder_done:<task_id>) - یک ردیف برای: «⏰ یادآوری دوباره» (reminder_snooze_prompt:<task_id>) 3) update task: reminder_state='fired', reminder_message_id=... 4) reminder_history.append({ts, action: 'fired'}) interval تیک scheduler حداکثر 60 ثانیه باشد تا یادآوری حداکثر با ۱ دقیقه تأخیر برسد
```

### Step 6: پیاده‌سازی callback handler برای reminder_step_tick در تلگرام
**Status:** `done` (100%)
**Scope:** این مرحله شامل پیاده‌سازی هندلر برای callback_data با الگوی reminder_step_tick:<task_id>:<step_id> در فایل backend/app/services/notification_service.py است. باید task_steps[step].done = True تنظیم شود، reminder_history.append انجام شود، همان پیام تلگرام با حذف آن دکمه و خط زدن آن مرحله از کپشن آپدیت شود. اگر همهٔ مراحل tick شدند → reminder_state='done', archived=True, notify reminder_done. خارج از این مرحله: هندلرهای reminder_done و reminder_snooze_prompt و reminder_snooze، API endpoints، frontend.
**Excerpt:**
```
reminder_step_tick:<task_id>:<step_id> - task_steps[step].done = True - reminder_history.append({ts, action: 'step_ticked', step_id}) - update همان پیام تلگرام: حذف آن دکمه + خط زدن آن مرحله از کپشن - اگر همهٔ مراحل tick شدند → reminder_state='done', archived=True, notify reminder_done
```

### Step 7: پیاده‌سازی callback handler برای reminder_done در تلگرام
**Status:** `done` (100%)
**Scope:** این مرحله شامل پیاده‌سازی هندلر برای callback_data با الگوی reminder_done:<task_id> در فایل backend/app/services/notification_service.py است. باید همهٔ task_steps done=True تنظیم شود، reminder_state='done', archived=True، پیام تلگرام edit شود به '✅ یادآوری تمام شد و آرشیو شد'، و notify_event('reminder_done', ...) فراخوانی شود. خارج از این مرحله: هندلرهای reminder_step_tick و reminder_snooze_prompt و reminder_snooze، API endpoints، frontend.
**Excerpt:**
```
reminder_done:<task_id> - همهٔ task_steps done=True - reminder_state='done', archived=True - edit پیام: «✅ یادآوری تمام شد و آرشیو شد» - notify_event('reminder_done', ...)
```

### Step 8: پیاده‌سازی callback handlers برای reminder_snooze_prompt و reminder_snooze در تلگرام
**Status:** `done` (100%)
**Scope:** این مرحله شامل پیاده‌سازی دو هندلر است. اولی برای callback_data با الگوی reminder_snooze_prompt:<task_id> که یک پیام جدید با inline_keyboard گزینه‌های snooze (۱۵ دقیقه، ۱ ساعت، ۳ ساعت، فردا ۹ صبح، انتخاب دستی) ارسال می‌کند. دومی برای reminder_snooze:<task_id>:<delta_or_iso> که reminder_at = now() + delta (یا ISO خام) تنظیم می‌کند، reminder_state='snoozed'، reminder_history.append انجام می‌دهد، notify_event('reminder_snoozed', ...) فراخوانی می‌کند، و پیام قبلی edit می‌شود به '⏰ به <new_at> موکول شد'. خارج از این مرحله: هندلرهای reminder_step_tick و reminder_done، API endpoints، frontend.
**Excerpt:**
```
reminder_snooze_prompt:<task_id> - ارسال پیام جدید با inline_keyboard گزینه‌های snooze: «۱۵ دقیقه دیگر»، «۱ ساعت دیگر»، «۳ ساعت دیگر»، «فردا ۹ صبح»، «انتخاب دستی» reminder_snooze:<task_id>:<delta_or_iso> - reminder_at = now() + delta (یا ISO خام) - reminder_state='snoozed' - reminder_history.append({ts, action: 'snoozed', new_at}) - notify_event('reminder_snoozed', ...) - پیام قبلی edit: «⏰ به <new_at> موکول شد»
```

### Step 9: افزودن دکمه «🔔 یادآوری جدید» به منوی تلگرام و پیاده‌سازی flow آن
**Status:** `done` (100%)
**Scope:** این مرحله شامل افزودن دکمه جدید '🔔 یادآوری جدید' به منوی اصلی تلگرام در فایل backend/app/services/notification_service.py است. flow باید شامل: 1) انتخاب پروژه (یا 'بدون پروژه')، 2) ورود به compose mode با mode='reminder' (مشابه task با پشتیبانی پیوست/صوت)، 3) submit → ask date/time با گزینه‌های پیش‌فرض inline ('۱ ساعت دیگر', 'امروز عصر', 'فردا ۹ صبح', 'انتخاب دستی')، 4) create task با type='reminder', reminder_state='scheduled', reminder_at=picked. خارج از این مرحله: API endpoints، frontend، callback handlers دیگر.
**Excerpt:**
```
دکمهٔ جدید در منو اصلی: «🔔 یادآوری جدید» — flow: 1) انتخاب پروژه (یا «بدون پروژه») 2) ورود به compose mode با mode='reminder' (مشابه task، با پشتیبانی پیوست/صوت/...) 3) submit → ask date/time (با گزینه‌های پیش‌فرض inline: «۱ ساعت دیگر»، «امروز عصر»، «فردا ۹ صبح»، «انتخاب دستی») 4) create task با type='reminder', reminder_state='scheduled', reminder_at=picked
```

### Step 10: افزودن API endpoints جدید برای مدیریت یادآوری‌ها
**Status:** `done` (100%)
**Scope:** این مرحله شامل افزودن چهار endpoint جدید به فایل backend/app/api/routes/oversight.py است: POST /tasks/{id}/reminder/snooze (body: {until?: ISO, delta_seconds?: int} → set reminder_at, state='snoozed'), POST /tasks/{id}/reminder/done (→ state='done', archived=True), PATCH /tasks/{id}/reminder/step/{step_id} (body: {done: bool} → toggle task_steps[step].done), و به‌روزرسانی POST /tasks برای پذیرش type='reminder' + reminder_at + reminder_repeat_rule. خارج از این مرحله: frontend، Telegram handlers، scheduler.
**Excerpt:**
```
POST /tasks/{id}/reminder/snooze body: {until?: ISO, delta_seconds?: int} → set reminder_at, state='snoozed' POST /tasks/{id}/reminder/done → state='done', archived=True PATCH /tasks/{id}/reminder/step/{step_id} body: {done: bool} → toggle task_steps[step].done POST /tasks input هم type='reminder' + reminder_at + reminder_repeat_rule اضافه شود
```

### Step 11: پیاده‌سازی تغییرات فرانت‌اند برای پشتیبانی از نوع یادآوری
**Status:** `done` (100%)
**Scope:** این مرحله شامل تغییرات در فایل frontend/src/app/oversight/page.tsx است: افزودن '🔔 یادآوری' با value='reminder' به type dropdown (خط ~2593)، نمایش input datetime-local و dropdown تکرار (یک‌بار/روزانه/هفتگی) وقتی type=reminder انتخاب شد، نمایش بادج 🔔 + reminder_at human-friendly در task list، و در مدال جزئیات تسک reminder: چک‌لیست task_steps با checkbox برای هر آیتم که PATCH .../reminder/step/{id} را فراخوانی می‌کند، دکمه '⏰ Snooze' با پنل تاریخ، دکمه '✅ تمام شد'، و بخش '📅 history' با timeline. خارج از این مرحله: backend API endpoints، Telegram handlers، scheduler.
**Excerpt:**
```
type dropdown — افزودن «🔔 یادآوری» با value='reminder' وقتی type=reminder انتخاب شد: - input تاریخ + ساعت ظاهر شود (datetime-local) - dropdown «تکرار»: یک‌بار / روزانه / هفتگی task list — برای reminders بادج 🔔 + reminder_at human-friendly («در ۲ ساعت دیگر»، «دیروز ساعت ۹») در مدال جزئیات تسک reminder: - چک‌لیست task_steps با checkbox برای هر آیتم - PATCH .../reminder/step/{id} وقتی checkbox تغییر کرد - دکمه «⏰ Snooze» (پنل تاریخ)، «✅ تمام شد» - بخش «📅 history» با timeline (scheduled→fired→snoozed→done)
```

### Step 12: تست و اعتبارسنجی کامل قابلیت یادآوری در تمام لایه‌ها
**Status:** `done` (100%)
**Scope:** این مرحله شامل تست و اعتبارسنجی کامل قابلیت یادآوری است: بررسی mypy/tsc بدون error در هر دو سمت، backend startup بدون crash، frontend build موفق، تست flow کامل از تلگرام ('🔔 یادآوری جدید' → ارسال صدا → submit → date pick → ذخیره)، تست دستی scheduler تیک (یادآوری در زمان موعد ارسال می‌شود)، تست tick روی یک checkbox از تلگرام (آن آیتم در فرانت هم done شد)، تست tick کل از فرانت (reminder در تلگرام دیگر نمی‌آید + archived). خارج از این مرحله: پیاده‌سازی ویژگی‌های جدید دیگر.
**Excerpt:**
```
Tests / Validation not done mypy/tsc هر دو سمت بدون error not done backend startup بدون crash not done frontend build موفق not done از تلگرام: «🔔 یادآوری جدید» → ارسال صدا → submit → date pick → ذخیره not done دستی scheduler تیک: یادآوری در زمان موعد ارسال می‌شود not done tick روی یک checkbox از تلگرام → آن آیتم در فرانت هم done شد not done tick کل از فرانت → reminder در تلگرام دیگر نمی‌آید + archived
```
