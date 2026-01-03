# اتاق فکر مهندسی هوشمند (AI Think Tank)

یک پلتفرم پیشرفته برای مناظره و همکاری بین مدل‌های هوش مصنوعی مختلف.

## ✨ امکانات

- 🤖 **پشتیبانی از چندین AI Provider**: OpenAI, Claude, Gemini, DeepSeek, Groq, OpenRouter
- 💬 **سیستم مناظره**: برگزاری مناظره بین مدل‌های مختلف با داوری خودکار
- 🎭 **نقش‌های متنوع**: تحلیلگر، منتقد، کدنویس، مناظره‌کننده، داور و...
- 📊 **امتیازدهی هوشمند**: ارزیابی خودکار پاسخ‌ها با معیارهای مختلف
- 🌙 **تم تاریک/روشن**: رابط کاربری مدرن با پشتیبانی از RTL
- 🔧 **مدیریت از Frontend**: تنظیم API Keys و پیکربندی بدون نیاز به restart

## 🏗️ معماری

```
project-management/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/routes/      # API Endpoints
│   │   ├── core/            # Config, Models Registry, Roles
│   │   ├── services/        # AI Services & Debate Logic
│   │   └── main.py          # Application Entry
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Next.js Frontend
│   ├── src/
│   │   ├── app/             # Pages (App Router)
│   │   ├── components/      # React Components
│   │   ├── hooks/           # Custom Hooks (Zustand)
│   │   ├── services/        # API Client
│   │   └── styles/          # Tailwind CSS
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml       # Container Orchestration
└── README.md
```

## 🚀 راه‌اندازی سریع

### پیش‌نیازها

- Python 3.11+
- Node.js 20+
- Docker (اختیاری)

### روش ۱: اجرای مستقیم (Development)

#### Backend:
```bash
cd backend

# ایجاد virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# یا: venv\Scripts\activate  # Windows

# نصب وابستگی‌ها
pip install -r requirements.txt

# تنظیم متغیرهای محیطی
cp .env.example .env
# ویرایش .env و اضافه کردن API Keys

# اجرا
uvicorn app.main:app --reload --port 8000
```

#### Frontend:
```bash
cd frontend

# نصب وابستگی‌ها
npm install

# اجرا
npm run dev
```

سپس مرورگر را در آدرس `http://localhost:3000` باز کنید.

### روش ۲: Docker Compose (Production)

```bash
# ایجاد فایل .env در پوشه backend
cp backend/.env.example backend/.env

# اجرا
docker-compose up -d

# بررسی لاگ‌ها
docker-compose logs -f
```

## 🔑 تنظیم API Keys

### روش ۱: از طریق Frontend (توصیه شده)
1. به صفحه تنظیمات بروید: `http://localhost:3000/settings`
2. API Keys را وارد کنید
3. ذخیره کنید

### روش ۲: فایل Environment
فایل `backend/.env` را ویرایش کنید:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...
```

## 📡 API Endpoints

### مناظره
- `POST /api/debate/session` - ایجاد جلسه مناظره
- `POST /api/debate/start` - شروع مناظره
- `GET /api/debate/session/{id}` - دریافت وضعیت جلسه

### مدل‌ها
- `GET /api/models` - لیست تمام مدل‌ها
- `GET /api/models/available` - مدل‌های فعال
- `GET /api/models/roles` - نقش‌ها
- `GET /api/models/modes` - حالت‌های کاری

### چت
- `POST /api/chat` - ارسال پیام به یک مدل
- `POST /api/chat/stream` - چت با streaming

### تنظیمات
- `GET /api/settings/status` - وضعیت API Keys
- `POST /api/settings/api-keys` - بروزرسانی کلیدها

## 🎭 نقش‌ها

| نقش | شرح |
|-----|-----|
| تحلیلگر | تحلیل عمیق سوال |
| منتقد | نقد و بررسی پاسخ‌ها |
| کدنویس | تولید و بهینه‌سازی کد |
| مناظره‌کننده | شرکت در مناظره |
| داور | قضاوت بی‌طرفانه |
| محقق | تحقیق و جستجو |
| خلاصه‌گر | خلاصه‌سازی نتایج |

## ⚙️ حالت‌های کاری

| حالت | شرح |
|------|-----|
| auto | انتخاب خودکار بهترین روش |
| debate | مناظره چند مدل |
| collab | همکاری تیمی |
| deep | تحقیق عمیق |
| quick | پاسخ سریع |
| creative | خلاقانه |

## 🛠️ توسعه

### اضافه کردن مدل جدید

1. در `backend/app/core/models_registry.py`:
```python
"new-model": {
    "id": "new-model",
    "name": "New Model",
    "provider": "provider-name",
    "maxTokens": 4096,
    ...
}
```

2. سرویس provider در `backend/app/services/` (اگر جدید است)

3. ثبت در `backend/app/services/ai_manager.py`

### اضافه کردن نقش جدید

در `backend/app/core/roles.py`:
```python
"new_role": AIRole(
    id="new_role",
    name="نام نقش",
    emoji="🆕",
    system_prompt="..."
)
```

## 📝 لایسنس

MIT License

## 🙏 تشکر

این پروژه با الهام از نیاز به همکاری بین مدل‌های مختلف AI و بهره‌گیری از نقاط قوت هر کدام ساخته شده است.
