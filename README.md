# AI Creator Engine - موتور خالق هوشمند

یک پلتفرم جامع برای تولید، مدیریت و استقرار پروژه‌های نرم‌افزاری با هوش مصنوعی

**نسخه:** 2.0.0 | **وضعیت:** در حال توسعه فعال

---

## فهرست مطالب

- [معرفی](#معرفی)
- [قابلیت‌ها](#قابلیت‌ها)
- [پیش‌نیازها](#پیش‌نیازها)
- [نصب و راه‌اندازی](#نصب-و-راه‌اندازی)
- [ساختار پروژه](#ساختار-پروژه)
- [پروایدرهای AI](#پروایدرهای-ai)
- [استفاده](#استفاده)
- [API Reference](#api-reference)
- [تنظیمات](#تنظیمات)
- [استقرار](#استقرار)
- [مشارکت](#مشارکت)

---

## معرفی

**AI Creator Engine** یک سیستم کامل برای:

1. **تولید پروژه با AI** - با یک توضیح ساده، پروژه کامل (backend + frontend) بسازید
2. **مناظره AI** - چند مدل هوش مصنوعی با هم بحث کنند و بهترین راه‌حل را بدهند
3. **مدیریت چند پروایدر** - OpenAI, Claude, Gemini, DeepSeek, Perplexity و بیشتر
4. **استقرار یک‌کلیکی** - مستقیماً به Render, Railway یا Vercel
5. **ایمپورت از GitHub** - پروژه‌های موجود را وارد و مدیریت کنید
6. **تولید نمودار** - دیاگرام‌های Mermaid برای ساختار، جریان و کلاس

---

## قابلیت‌ها

### هسته اصلی

| قابلیت | توضیح | وضعیت |
|--------|-------|-------|
| موتور خالق | تولید پروژه کامل با AI | ✅ |
| مناظره AI | بحث بین چند مدل | ✅ |
| مدیریت پروژه | CRUD کامل + فایل‌ها | ✅ |
| استقرار | Render, Railway, Vercel | ✅ |
| GitHub Import | ورود پروژه از GitHub | ✅ |
| اجرای پروژه | با Docker | ✅ |

### هوش مصنوعی

| قابلیت | توضیح | وضعیت |
|--------|-------|-------|
| Multi-Provider | 7 پروایدر AI | ✅ |
| Smart Select | انتخاب هوشمند مدل | ✅ |
| Fallback | جایگزینی خودکار | ✅ |
| Vision | تحلیل تصویر | ✅ |
| Image Gen | تولید تصویر (DALL-E, Imagen) | ✅ |

### ابزارها

| قابلیت | توضیح | وضعیت |
|--------|-------|-------|
| نمودار Mermaid | 8 نوع دیاگرام | ✅ |
| تحلیل کد | تولید دیاگرام از کد | ✅ |
| ژورنال پروژه | ثبت تاریخچه | ✅ |
| ساختار پروژه | نمایش درختی | ✅ |

### در حال توسعه

| قابلیت | توضیح | وضعیت |
|--------|-------|-------|
| بررسی خودکار | تحلیل سلامت پروژه | 🔄 |
| پروفایل مدل‌ها | نمره‌دهی به AI ها | 🔄 |
| گزارش‌گیری | گزارش جامع | 🔄 |

---

## پیش‌نیازها

### سیستم
- Python 3.11+
- Node.js 18+
- Docker (اختیاری - برای اجرای پروژه‌ها)

### API Keys (حداقل یکی)
- OpenAI API Key
- Anthropic (Claude) API Key
- Google AI (Gemini) API Key
- DeepSeek API Key

### برای استقرار
- Render API Key
- GitHub Token (برای persistence)

---

## نصب و راه‌اندازی

### روش 1: محلی (توسعه)

```bash
# 1. کلون پروژه
git clone https://github.com/your-repo/project-management.git
cd project-management

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# یا: venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend (ترمینال جدید)
cd frontend
npm install
npm run dev
```

### روش 2: Docker Compose

```bash
# Build و اجرا
docker-compose up --build

# یا در پس‌زمینه
docker-compose up -d
```

### روش 3: Deploy به Render

با دکمه زیر یا با استفاده از `render.yaml`:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## ساختار پروژه

```
project-management/
│
├── backend/                     # FastAPI Backend
│   ├── app/
│   │   ├── api/routes/         # API Endpoints (20+ route)
│   │   │   ├── projects.py     # مدیریت پروژه
│   │   │   ├── creator.py      # موتور خالق
│   │   │   ├── debate.py       # مناظره AI
│   │   │   ├── models.py       # مدل‌های AI
│   │   │   ├── settings.py     # تنظیمات
│   │   │   └── ...
│   │   │
│   │   ├── core/               # هسته اصلی
│   │   │   ├── config.py       # تنظیمات
│   │   │   ├── database.py     # SQLite
│   │   │   ├── models_registry.py  # رجیستری مدل‌ها
│   │   │   └── roles.py        # نقش‌های AI
│   │   │
│   │   ├── models/             # مدل‌های دیتابیس
│   │   │   ├── project.py
│   │   │   ├── debate.py
│   │   │   └── setting.py
│   │   │
│   │   ├── services/           # سرویس‌ها (27+ service)
│   │   │   ├── ai_manager.py   # مدیریت مرکزی AI
│   │   │   ├── openai_service.py
│   │   │   ├── claude_service.py
│   │   │   ├── gemini_service.py
│   │   │   ├── deepseek_service.py
│   │   │   ├── creator_engine.py   # موتور تولید
│   │   │   ├── debate_service.py   # سرویس مناظره
│   │   │   ├── deploy_service.py   # استقرار
│   │   │   └── ...
│   │   │
│   │   └── main.py             # نقطه ورود
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                    # Next.js Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # صفحه اصلی
│   │   │   ├── creator/        # موتور خالق
│   │   │   ├── projects/       # پروژه‌ها
│   │   │   ├── debate/         # مناظره
│   │   │   ├── diagrams/       # نمودارها
│   │   │   ├── settings/       # تنظیمات
│   │   │   └── ...
│   │   │
│   │   ├── components/         # کامپوننت‌ها
│   │   ├── services/           # سرویس API
│   │   └── types/              # TypeScript types
│   │
│   ├── package.json
│   └── Dockerfile
│
├── README.md                    # این فایل
├── ROADMAP.md                   # نقشه راه
├── ARCHITECTURE.md              # معماری
├── docker-compose.yml
└── render.yaml
```

---

## پروایدرهای AI

### پشتیبانی‌شده

| پروایدر | مدل‌های اصلی | ویژگی‌ها |
|---------|--------------|----------|
| **OpenAI** | GPT-4o, GPT-4o Mini, GPT-4 Turbo | Vision, DALL-E 3 |
| **Anthropic** | Claude Sonnet 4, Claude 3.5 Sonnet, Claude 3 Haiku | Long Context |
| **Google** | Gemini 2.5 Pro, Gemini 2.5 Flash | 1M Token Context |
| **DeepSeek** | DeepSeek Chat, DeepSeek Coder, DeepSeek Reasoner | کد و استدلال |
| **Perplexity** | Sonar Pro, Sonar Reasoning | جستجو و تحقیق |
| **Groq** | Mixtral, LLaMA | سرعت بالا |
| **OpenRouter** | همه مدل‌ها | Multi-provider |

### انتخاب هوشمند

سیستم به صورت خودکار بهترین مدل را بر اساس:
- نوع درخواست (کد، تحلیل، تصویر)
- هزینه و سرعت
- در دسترس بودن

انتخاب می‌کند.

---

## استفاده

### 1. تنظیم API Keys

1. برو به `http://localhost:3000/settings`
2. کلید API وارد کن (حداقل یکی)
3. ذخیره کن

### 2. ساخت پروژه با AI

1. برو به **موتور خالق** (`/creator`)
2. نام پروژه وارد کن
3. توضیحات دقیق بنویس:
   ```
   یک API برای مدیریت کتابخانه با FastAPI بساز که:
   - اضافه، ویرایش و حذف کتاب
   - جستجو بر اساس نام و نویسنده
   - ذخیره در SQLite
   ```
4. نوع پروژه انتخاب کن (Python, FastAPI, Next.js, ...)
5. کلیک روی "ساخت با AI"

### 3. مناظره AI

1. برو به `/debate`
2. سوال یا موضوع وارد کن
3. مدل‌ها را انتخاب کن
4. حالت کاری انتخاب کن (مناظره، همکاری، تحقیق)
5. شروع کن

### 4. Import از GitHub

1. در صفحه پروژه‌ها، کلیک روی "Import از GitHub"
2. آدرس repo وارد کن
3. توکن وارد کن (برای private repos)
4. Import کن

### 5. استقرار

1. از صفحه پروژه، کلیک روی "Deploy به Render"
2. یا دستی:
   - Push به GitHub
   - اتصال Render به repo

---

## API Reference

### پروژه‌ها

```
GET    /api/projects              # لیست پروژه‌ها
POST   /api/projects              # ایجاد پروژه
GET    /api/projects/{id}         # جزئیات
DELETE /api/projects/{id}         # حذف
POST   /api/projects/{id}/deploy  # استقرار
```

### موتور خالق

```
POST   /api/creator/projects/create  # ساخت با AI
POST   /api/creator/files            # مدیریت فایل
POST   /api/creator/commands         # اجرای دستور
```

### مناظره

```
POST   /api/debate/create         # شروع مناظره
GET    /api/debate/               # لیست مناظره‌ها
GET    /api/debate/{id}           # جزئیات
POST   /api/debate/{id}/run-full  # اجرای کامل
```

### مدل‌ها

```
GET    /api/models                # همه مدل‌ها
GET    /api/models/available      # مدل‌های فعال
POST   /api/models/smart-select   # انتخاب هوشمند
```

### تنظیمات

```
GET    /api/settings/api-keys/status  # وضعیت کلیدها
PUT    /api/settings/api-keys         # ذخیره کلید AI
PUT    /api/settings/deploy-keys      # ذخیره کلید Render
```

### مستندات کامل

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## تنظیمات

### متغیرهای محیطی

```env
# API Keys (حداقل یکی)
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
GEMINI_API_KEY=AI...
DEEPSEEK_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...

# استقرار
RENDER_API_KEY=rnd_...
GITHUB_TOKEN=ghp_...

# سیستم
DEBUG=true
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000

# دیتابیس
DATABASE_URL=sqlite:///./data/app.db

# محدودیت‌ها
MAX_TOKENS_PER_MODEL=0  # 0 = نامحدود
MAX_PROMPT_LENGTH=0     # 0 = نامحدود
REQUEST_TIMEOUT=120
```

### تنظیمات Frontend

در فایل `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## استقرار

### Render (توصیه‌شده)

1. Fork این repo
2. در Render:
   - New > Blueprint
   - انتخاب repo
   - تنظیم environment variables
3. یا با `render.yaml` موجود

### Docker

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Logs
docker-compose logs -f
```

### دستی

1. Backend روی یک سرور با Python 3.11
2. Frontend روی Vercel یا Netlify
3. تنظیم CORS و URL ها

---

## نقشه راه

برای جزئیات کامل به [ROADMAP.md](./ROADMAP.md) مراجعه کنید.

### در حال توسعه

- **سیستم بررسی خودکار:** تحلیل سلامت پروژه با AI
- **پروفایل مدل‌ها:** نمره‌دهی و ردیابی عملکرد
- **گزارش‌گیری پیشرفته:** گزارش جامع با اعتبارسنجی

---

## مشارکت

1. Fork کنید
2. Branch بسازید (`git checkout -b feature/amazing-feature`)
3. Commit کنید (`git commit -m 'Add amazing feature'`)
4. Push کنید (`git push origin feature/amazing-feature`)
5. Pull Request بسازید

---

## مجوز

MIT License - آزاد برای استفاده و توسعه

---

## پشتیبانی

- Issues: [GitHub Issues](https://github.com/your-repo/issues)
- مستندات: این فایل و ROADMAP.md

---

**ساخته شده با ❤️ و AI**
