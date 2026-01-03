# ☁️ راهنمای دیپلوی در Cloud

## گزینه‌های دیپلوی

| سرویس | Frontend | Backend | هزینه | سختی |
|-------|----------|---------|-------|------|
| **Vercel + Railway** | Vercel | Railway | رایگان/کم | آسان |
| **Render.com** | Render | Render | رایگان | آسان |
| **Google Cloud Run** | Cloud Run | Cloud Run | Pay-per-use | متوسط |
| **Docker (VPS)** | Docker | Docker | $5-10/mo | متوسط |

---

## 🚀 روش ۱: Vercel + Railway (پیشنهادی)

### مرحله ۱: دیپلوی Backend در Railway

1. به [railway.app](https://railway.app) بروید و با GitHub وارد شوید
2. روی **New Project** کلیک کنید
3. **Deploy from GitHub repo** را انتخاب کنید
4. ریپو `project-management` را انتخاب کنید
5. در تنظیمات:
   - **Root Directory**: `backend`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

6. در تب **Variables** این مقادیر را اضافه کنید:
   ```
   ENVIRONMENT=production
   DEBUG=false
   OPENAI_API_KEY=sk-...
   CLAUDE_API_KEY=sk-ant-...
   GEMINI_API_KEY=...
   ```

7. دیپلوی کنید و URL را کپی کنید (مثلاً `https://your-app.railway.app`)

### مرحله ۲: دیپلوی Frontend در Vercel

1. به [vercel.com](https://vercel.com) بروید
2. **Import Project** → **Import Git Repository**
3. ریپو را انتخاب کنید
4. در تنظیمات:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`

5. در **Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://your-app.railway.app
   ```

6. دیپلوی کنید!

---

## 🎯 روش ۲: Render.com (یک‌جا)

فایل `render.yaml` در پروژه موجود است. فقط:

1. به [render.com](https://render.com) بروید
2. **New** → **Blueprint**
3. ریپو را وصل کنید
4. خودکار هر دو سرویس ایجاد می‌شود
5. API Keys را در تنظیمات وارد کنید

---

## 🐳 روش ۳: Docker روی VPS

### نیازمندی‌ها
- یک VPS با حداقل 1GB RAM (DigitalOcean, Linode, Hetzner)
- Docker و Docker Compose نصب شده

### مراحل

```bash
# 1. Clone کردن
git clone https://github.com/mahdighandi1989/project-management.git
cd project-management

# 2. ایجاد فایل .env
cat > backend/.env << EOF
ENVIRONMENT=production
DEBUG=false
OPENAI_API_KEY=sk-your-key
CLAUDE_API_KEY=sk-ant-your-key
GEMINI_API_KEY=your-key
CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
EOF

# 3. اجرا با Docker Compose
docker-compose up -d

# 4. بررسی وضعیت
docker-compose ps
docker-compose logs -f
```

### با HTTPS (تولید)

```bash
# اجرا با nginx profile
docker-compose --profile production up -d
```

---

## ☁️ روش ۴: Google Cloud Run

### Backend

```bash
# 1. به پوشه backend بروید
cd backend

# 2. ساخت و push image
gcloud builds submit --tag gcr.io/PROJECT_ID/ai-creator-backend

# 3. دیپلوی
gcloud run deploy ai-creator-backend \
  --image gcr.io/PROJECT_ID/ai-creator-backend \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=sk-..."
```

### Frontend

```bash
cd frontend

gcloud builds submit --tag gcr.io/PROJECT_ID/ai-creator-frontend

gcloud run deploy ai-creator-frontend \
  --image gcr.io/PROJECT_ID/ai-creator-frontend \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_API_URL=https://ai-creator-backend-xxx.run.app"
```

---

## 📝 Environment Variables

| متغیر | توضیح | اجباری |
|-------|-------|--------|
| `OPENAI_API_KEY` | کلید OpenAI | ❌ |
| `CLAUDE_API_KEY` | کلید Anthropic | ❌ |
| `GEMINI_API_KEY` | کلید Google Gemini | ❌ |
| `DEEPSEEK_API_KEY` | کلید DeepSeek | ❌ |
| `ENVIRONMENT` | production/development | ✅ |
| `DEBUG` | true/false | ✅ |
| `CORS_ORIGINS` | آدرس‌های مجاز | ✅ |
| `NEXT_PUBLIC_API_URL` | آدرس Backend | ✅ |

---

## 🔒 نکات امنیتی

1. **هرگز** API keys را در کد commit نکنید
2. از **Environment Variables** استفاده کنید
3. **CORS_ORIGINS** را محدود کنید
4. **HTTPS** را فعال کنید
5. **Rate limiting** اضافه کنید

---

## 🛠️ رفع مشکلات

### Backend بالا نمیاد
```bash
# لاگ را بررسی کنید
docker-compose logs backend
# یا در Railway: لاگ‌ها را ببینید
```

### خطای CORS
```bash
# CORS_ORIGINS را چک کنید
# باید شامل آدرس frontend باشد
```

### API Keys کار نمیکند
```bash
# در Railway/Render: Variables را چک کنید
# در Docker: فایل .env را چک کنید
```

---

## 📞 پشتیبانی

اگر مشکلی داشتید:
1. Issues در GitHub باز کنید
2. لاگ‌ها را اضافه کنید
3. محیط دیپلوی را مشخص کنید
