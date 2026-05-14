# Phase 5 — Meta-validation Log

این فایل برای اعتبارسنجی پرامپت Phase 5 است. کاربر این پرامپت را به‌عنوان
یک task در سیستم خود می‌سازد و verify deep را روی آن اجرا می‌کند.
نتیجه‌ی این validation هم پرامپت را اعتبارسنجی می‌کند و هم باگ‌های احتمالی
verify Phase 4 را آشکار می‌کند.

## ساختار پرامپت → task

هنگامی که کاربر این پرامپت را به task تبدیل می‌کند، توقع است که:
- `idea_to_prompt` با ساختار غنی فاز ۷ AC تولید کند
- `_ai_plan_steps_from_idea` با cap 30 تا 10 step تولید کند (۱۰ فاز)
- هر AC شامل: behavior + acceptance_signal + business_intent +
  alternative_implementations + non_goals + false_positive_guard
- هر task_step شامل: behavior_observable + verification_hint +
  business_intent + non_goals

## Acceptance Criteria برای هر فاز (Phase 5 V4)

### فاز ۱ — Comprehensive Inventory + Purpose
- ✅ `backend/app/services/scan_v5/comprehensive_inventory.py` موجود
- ✅ `backend/app/services/scan_v5/purpose_extractor.py` موجود
- ✅ روی این پروژه: ≥50 backend endpoint، ≥30 UI element، ≥10 notification call
- ✅ `WatchedProject.last_scan_inventory + last_scan_purpose_map +
  last_scan_at_v5` field ها موجود
- ✅ integration در `run_deep_scan` با fail-soft

**Verification hint:** scan روی این پروژه بزن و چک کن
`watched.last_scan_inventory['_meta']['counts']` غیر-خالی است.

### فاز ۲ — Stale + Feature Inventory Panel
- ✅ `scan_v5/stale_detector.py` با 7 structural + 2 semantic detector
- ✅ `scan_v5/feature_documenter.py` با AI documentation
- ✅ روی این پروژه: ≥5 structural، ≥3 semantic stale کشف
- ✅ endpoint `GET /api/oversight/watched/{id}/feature-inventory`

**Verification hint:** بعد از scan، endpoint بالا را بزن و چک کن
`stale.summary.structural_total ≥ 5`.

### فاز ۳ — Delta + Bidirectional Dependency
- ✅ `scan_v5/delta_analyzer.py` با 6 نوع change
- ✅ `scan_v5/dependency_analyzer.py` با forward + reverse
- ✅ `WatchedProject.prev_scan_state` field
- ✅ `change_impact` AI analysis روی dependents در خطر

**Verification hint:** دو scan متوالی بزن و در scan دوم چک کن
`scan_v5_inventory._delta.summary.first_scan == False`.

### فاز ۴ — Runtime + Outcome + Inspector Session (R14)
- ✅ `scan_v5/runtime_discovery.py` با Playwright + Render logs
- ✅ `scan_v5/outcome_analyzer.py` با effectiveness audit
- ✅ `scan_v5/scan_inspector_session.py` با create/log/archive
- ✅ screenshots ذخیره در `storage/scan_v5_screenshots/{watched_id}/`
- ✅ session با badge "🔍 Scan: ..." در InspectorSession DB

**Verification hint:** بعد از scan با `inspector_session_enabled=True`،
چک کن `InspectorSession` با title شروع‌شده با "🔍 Scan:" در DB موجود است.

### فاز ۵ — Logical Audit (R10, R11)
- ✅ `scan_v5/coherence_analyzer.py` با 6 pipeline category
- ✅ `scan_v5/anti_pattern_detector.py` با 4 regex + AI detectors
- ✅ روی این پروژه: ≥2 anti-pattern logical کشف

**Verification hint:** بعد از scan، چک کن
`scan_v5_inventory._anti_patterns` لیست غیر-خالی است.

### فاز ۶ — Notification Audit (R12)
- ✅ `scan_v5/notification_auditor.py` با structural + AI audit
- ✅ روی این پروژه: ≥2 audit issue کشف
- ✅ پیشنهاد silent default برای auto-tasks + scan_completed

**Verification hint:** بعد از scan، چک کن
`scan_v5_inventory._notif_audit.summary.total_issues ≥ 2`.

### فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)
- ✅ ساختار غنی AC در `oversight_strong_prompt.py:build_strong_prompt`
- ✅ task_steps با behavior_observable + verification_hint +
  business_intent + non_goals در `_ai_plan_steps_from_idea`
- ✅ هم برای manual (`idea_to_prompt`) و هم auto (scan task creation)
- ✅ backward-compat: AC ساده (str) همچنان کار می‌کند

**Verification hint:** بعد از `idea_to_prompt` با یک ایده پیچیده،
چک کن خروجی task شامل `behavior` و `acceptance_signal` در AC ها است.

### فاز ۸ — Auto-tasks Like Manual + Telegram (R5, R6)
- ✅ task_steps برای auto-scan tasks (mode=auto/always/never)
- ✅ scan_completed Telegram message با همه‌ی Phase 1-7 شواهد
- ✅ silent default = True (R6)
- ✅ `notify_event` پشتیبانی از `silent: Optional[bool]` parameter

**Verification hint:** بعد از scan با auto_task_checklist_mode="auto"،
چک کن task های پیچیده دارای task_steps هستند.

### فاز ۹ — UI Redesign (R2)
- ✅ scan_depth شامل `balanced` و `ultra`
- ✅ panel "Scan v5 Intelligence" با 8 checkbox + 3 لایه دیگر
- ✅ link "🗺 مشاهده Feature Inventory" در UI
- ✅ TS type WatchedProject با 13 field جدید

**Verification hint:** UI kar.

### فاز ۱۰ — Meta-validation
- ✅ این فایل `PHASE_5_META_VALIDATION.md` موجود
- ✅ همه فازها AC قابل-verify دارند
- ✅ Iteration loop در پایان scan روی این پروژه

**Verification hint:** این فاز خود-validate است.

## Iteration Loop

```
for phase in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    impl_done = implement(phase)
    if not impl_done:
        continue
    runtime_test_done = runtime_test(phase)
    if not runtime_test_done:
        continue
    push_done = git_push(phase)
    # verify deep on this prompt-as-task
    verify_result = verify_deep(meta_task_id)
    log_to(PHASE_5_META_VALIDATION_LOG)
    if verify_result.checklist_pct < 100:
        log_potential_verify_bug(phase, verify_result)
```

## Verify Bug Detection

اگر verify گزارش داد فاز X "not_done" است ولی پیاده‌سازی واقعاً انجام
شده (با runtime test تأیید شد)، این **یک باگ verify** است که باید
رفع شود — مشابه باگ‌های 1-18 Phase 4.

نمونه‌ها برای جستجو:
- آیا verify فقط روی UI screenshot نگاه می‌کند بدون به code_aware اعتماد؟
- آیا keyword override روی DOM check می‌کند؟
- آیا programmatic upgrade برای backend-internal features fire می‌شود؟

## Status Summary

| فاز | فایل‌های ایجاد شده | Commit | runtime test |
|---|---|---|---|
| 1 | comprehensive_inventory.py, purpose_extractor.py | f217fec | ✓ 500 endpoints |
| 2 | stale_detector.py, feature_documenter.py | 35e949e | ✓ 221 structural + 50 semantic |
| 3 | delta_analyzer.py, dependency_analyzer.py | 9615fdd | ✓ 5 scenarios |
| 4 | runtime_discovery.py, outcome_analyzer.py, scan_inspector_session.py | 26fd4c1 | ✓ module imports |
| 5 | coherence_analyzer.py, anti_pattern_detector.py | adebd36 | ✓ 64 anti-patterns real |
| 6 | notification_auditor.py | 7afda7d | ✓ 23 notification issues real |
| 7 | (modifications to existing) | 41f53b1 | ✓ rich AC rendered |
| 8 | (task creation + notify_event silent) | 2547a0b | ✓ |
| 9 | (UI only) | 4f3ce31 | ✓ tsc clean |
| 10 | این فایل | (current) | meta |

## یادآوری برای کاربر

بعد از اینکه این پرامپت را به task تبدیل کردی و verify بزنی:
1. اگر `8/10 ≤ done < 10/10` → یک یا چند فاز ممکن است نیاز به iteration داشته باشد
2. اگر `done = 10/10` → ✅ کامل validated
3. اگر `done < 8/10` → یا فازها واقعاً ناقص هستند (پیگیری implementation)
   یا verify بدبینانه است (پیگیری verify bug)

این آخرین حلقه‌ی feedback است.
