# راهنمای راه‌اندازی قدم به قدم

این راهنما به شما کمک می‌کند تا پروژه را به راحتی راه‌اندازی کنید.

---

## 🎯 پیش‌نیازها

### چیزهایی که باید نصب کنید:

1. **Python** (نسخه 3.11 یا بالاتر)
   - دانلود از: https://www.python.org/downloads/
   - موقع نصب تیک "Add to PATH" را بزنید

2. **Node.js** (نسخه 20 یا بالاتر)
   - دانلود از: https://nodejs.org/
   - LTS version را انتخاب کنید

3. **Git** (برای clone کردن کد)
   - دانلود از: https://git-scm.com/

---

## 📋 مرحله 1: دانلود پروژه

```bash
# در ترمینال یا CMD بزنید:
git clone https://github.com/mahdighandi1989/project-management.git
cd project-management
```

---

## 📋 مرحله 2: راه‌اندازی Backend

### ویندوز:
```cmd
cd backend

# ساخت محیط مجازی
python -m venv venv

# فعال کردن محیط مجازی
venv\Scripts\activate

# نصب پکیج‌ها
pip install -r requirements.txt

# کپی فایل تنظیمات
copy .env.example .env

# ویرایش .env و اضافه کردن API Keys
notepad .env
```

### مک/لینوکس:
```bash
cd backend

# ساخت محیط مجازی
python3 -m venv venv

# فعال کردن محیط مجازی
source venv/bin/activate

# نصب پکیج‌ها
pip install -r requirements.txt

# کپی فایل تنظیمات
cp .env.example .env

# ویرایش .env
nano .env
```

### 🔑 تنظیم API Keys

فایل `.env` را باز کنید و کلیدهای API را وارد کنید:

```
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-claude-key-here
GOOGLE_API_KEY=AIza-your-gemini-key-here
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
```

### اجرای Backend:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ اگر موفق بود، می‌بینید:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

## 📋 مرحله 3: راه‌اندازی Frontend

در یک ترمینال **جدید** (Backend را باز بگذارید):

```bash
cd frontend

# نصب پکیج‌ها
npm install

# اجرا
npm run dev
```

✅ اگر موفق بود، می‌بینید:
```
▲ Next.js 14.x.x
- Local:        http://localhost:3000
```

---

## 🌐 مرحله 4: استفاده از برنامه

1. مرورگر را باز کنید
2. به آدرس `http://localhost:3000` بروید
3. می‌توانید:
   - از صفحه تنظیمات API Keys را وارد کنید
   - مناظره جدید ایجاد کنید
   - مدل‌ها را مشاهده کنید

---

## 🔧 رفع مشکلات رایج

### 1. خطای "python not found"
- مطمئن شوید Python نصب شده
- ترمینال را ببندید و دوباره باز کنید

### 2. خطای "npm not found"
- Node.js را نصب کنید
- ترمینال را ببندید و دوباره باز کنید

### 3. خطای "port already in use"
```bash
# برای Backend (پورت 8000):
# ویندوز:
netstat -ano | findstr :8000
taskkill /PID [PID_NUMBER] /F

# مک/لینوکس:
lsof -i :8000
kill -9 [PID]
```

### 4. خطای CORS
مطمئن شوید Backend روی پورت 8000 و Frontend روی پورت 3000 اجرا می‌شود.

### 5. API Key نامعتبر
- کلیدها را دوباره چک کنید
- مطمئن شوید اعتبار کافی دارید

---

## 📡 آدرس‌های مهم

| سرویس | آدرس |
|-------|------|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## 🐳 راه‌اندازی با Docker (آسان‌تر)

اگر Docker نصب دارید:

```bash
# در پوشه اصلی پروژه:
docker-compose up -d

# بررسی وضعیت:
docker-compose ps

# مشاهده لاگ‌ها:
docker-compose logs -f
```

همین! حالا می‌توانید به `http://localhost:3000` بروید.

---

## ❓ سوالات متداول

**س: آیا باید همه API Keys را داشته باشم؟**
ج: نه، حداقل یکی کافی است. ولی برای مناظره بین مدل‌ها، بهتر است چند تا داشته باشید.

**س: هزینه API چقدر است؟**
ج: بستگی به مدل و استفاده دارد:
- OpenAI GPT-4: حدود $0.01-0.03 per 1K tokens
- Claude: حدود $0.003 per 1K tokens
- Gemini: رایگان (محدود)
- DeepSeek: خیلی ارزان

**س: می‌توانم روی سرور اجرا کنم؟**
ج: بله! با Docker یا مستقیم. فقط پورت‌ها را در فایروال باز کنید.

---

## 📞 پشتیبانی

اگر مشکلی داشتید:
1. Issue بزنید در GitHub
2. لاگ‌های Backend و Frontend را بررسی کنید
