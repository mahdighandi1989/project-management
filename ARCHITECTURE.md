# معماری سیستم - AI Creator Engine

## هدف اصلی
یک سیستم تولید پروژه با AI که:
1. با توضیحات ساده، پروژه کامل تولید کند
2. با یک کلیک به Render دیپلوی شود
3. مناظره بین AI ها برای بهترین نتیجه

---

## ساختار ساده

```
project-management/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── models.py      # مدیریت مدل‌های AI
│   │   │   ├── settings.py    # تنظیمات و کلیدها
│   │   │   ├── projects.py    # پروژه‌ها + ساخت + دیپلوی
│   │   │   └── debate.py      # مناظره AI
│   │   ├── core/
│   │   │   ├── config.py      # تنظیمات
│   │   │   └── models_registry.py  # رجیستری مدل‌ها
│   │   ├── services/
│   │   │   ├── ai_manager.py     # مدیریت AI ها
│   │   │   ├── openai_service.py # OpenAI
│   │   │   ├── claude_service.py # Claude
│   │   │   ├── gemini_service.py # Gemini
│   │   │   ├── deepseek_service.py # DeepSeek
│   │   │   ├── project_service.py  # مدیریت پروژه
│   │   │   ├── creator_engine.py   # تولید کد با AI
│   │   │   └── deploy_service.py   # دیپلوی به Render
│   │   └── main.py
│   └── requirements.txt
└── frontend/
    └── src/app/
        ├── page.tsx           # خانه
        ├── creator/page.tsx   # موتور خالق (اصلی)
        ├── projects/page.tsx  # پروژه‌ها
        ├── debate/page.tsx    # مناظره
        └── settings/page.tsx  # تنظیمات
```

---

## جریان کار اصلی

### 1. تنظیم کلیدها
```
User → Settings → Save API Key → Backend updates os.environ → AI Manager reinitializes
```

### 2. ساخت پروژه
```
User → Creator → Name + Description + Type
     → POST /api/creator/projects/create
     → AI generates project structure
     → AI generates each file
     → Save to disk/GitHub
     → Return project with files list
```

### 3. دیپلوی
```
User → Project → Deploy to Render
     → POST /api/projects/{id}/deploy/render
     → Create GitHub repo (if needed)
     → Push code
     → Create Render service
     → Return deploy URL
```

---

## API Endpoints (ساده)

### مدل‌ها
- `GET /api/models` - لیست همه مدل‌ها
- `GET /api/models/available` - مدل‌های فعال

### تنظیمات
- `GET /api/settings/api-keys/status` - وضعیت کلیدها
- `PUT /api/settings/api-keys` - ذخیره کلید AI
- `PUT /api/settings/deploy-keys` - ذخیره کلید Render/GitHub

### پروژه‌ها
- `GET /api/projects` - لیست پروژه‌ها
- `POST /api/creator/projects/create` - ساخت با AI
- `GET /api/projects/{id}` - جزئیات پروژه
- `DELETE /api/projects/{id}` - حذف
- `POST /api/projects/{id}/deploy/render` - دیپلوی

### مناظره
- `POST /api/debate/start` - شروع مناظره
- `GET /api/debate/{id}` - نتایج

---

## فایل‌های ضروری

### Backend Services
| فایل | وظیفه | وضعیت |
|------|-------|-------|
| ai_manager.py | مدیریت مرکزی AI | ✅ |
| openai_service.py | OpenAI | ✅ |
| claude_service.py | Claude | ✅ |
| gemini_service.py | Gemini | ✅ |
| deepseek_service.py | DeepSeek | ✅ |
| creator_engine.py | تولید کد | ✅ |
| deploy_service.py | دیپلوی | ✅ |
| project_service.py | مدیریت پروژه | ✅ |

### فایل‌های بایگانی شده
| فایل | دلیل |
|------|------|
| smart_orchestrator.py | پیچیده (87KB) |
| orchestrator.py | پیچیده (81KB) |
| Code.gs + Index.html | نسخه قدیمی Google Scripts |

---

## نکات مهم

1. **کلیدها از os.environ خوانده میشن** - بعد از update فوری اعمال میشه
2. **AI Manager singleton هست** - بعد از update کلیدها reset میشه
3. **پروژه‌ها در دو جا ذخیره میشن**: disk + GitHub (برای persistence)
4. **Deploy به Render** نیاز به RENDER_API_KEY داره

---

## TODO

- [ ] تست کامل flow ساخت پروژه
- [ ] تست deploy به Render
- [ ] حذف فایل‌های اضافی
- [ ] بهینه‌سازی Creator Engine
