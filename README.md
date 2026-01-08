# AI Creator Engine - موتور خالق هوشمند

یک سیستم تولید پروژه با هوش مصنوعی که پروژه‌های کامل میسازه و Deploy میکنه.

## قابلیت‌ها

- **تولید پروژه با AI** - توضیحات بده، پروژه کامل بگیر
- **Deploy یک کلیکی** - مستقیم به Render
- **مناظره AI** - چند مدل با هم بحث کنن و بهترین جواب
- **Multi-Provider** - OpenAI, Claude, Gemini, DeepSeek, Groq, OpenRouter

---

## شروع سریع

### 1. کلون پروژه
```bash
git clone <repo-url>
cd project-management
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. تنظیم API Keys
از مرورگر برو به: `http://localhost:3000/settings`
- کلید OpenAI یا Claude وارد کن
- کلید Render وارد کن (برای Deploy)

---

## استفاده

### ساخت پروژه
1. برو به **موتور خالق** (`/creator`)
2. نام و توضیحات وارد کن (دقیق بنویس چی میخوای)
3. نوع پروژه انتخاب کن (Python, FastAPI, Next.js, ...)
4. کلیک روی "ساخت پروژه با AI"

### Deploy به Render
1. از تنظیمات کلید Render رو وارد کن
2. از صفحه پروژه کلیک روی "Deploy"

---

## ساختار

```
project-management/
├── backend/           # FastAPI
│   ├── app/
│   │   ├── api/routes/    # API Endpoints
│   │   ├── core/          # Config
│   │   └── services/      # AI Services
│   └── requirements.txt
├── frontend/          # Next.js
│   └── src/app/
│       ├── creator/       # موتور خالق
│       ├── projects/      # پروژه‌ها
│       ├── debate/        # مناظره
│       └── settings/      # تنظیمات
└── archive/           # فایل‌های قدیمی
```

---

## API

| Endpoint | توضیح |
|----------|-------|
| `GET /api/models/available` | مدل‌های فعال |
| `PUT /api/settings/api-keys` | ذخیره کلید AI |
| `PUT /api/settings/deploy-keys` | ذخیره کلید Render |
| `POST /api/creator/projects/create` | ساخت پروژه با AI |
| `POST /api/projects/{id}/deploy/render` | Deploy |

---

## نکات مهم

1. **حداقل یک کلید AI وارد کنید** - بدون کلید، موتور خالق کار نمیکنه
2. **کلیدها مستقیم ذخیره میشن** - بعد از ذخیره فوری فعال میشن
3. **GitHub اختیاری** - برای persistence پروژه‌ها

---

## Deploy به Render

1. از Render یه API Key بگیر:
   - Dashboard → Account Settings → API Keys

2. از Settings کلید رو وارد کن

3. از پروژه Deploy بزن

---

## License

MIT
