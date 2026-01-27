# معماری سیستم - AI Creator Engine
## System Architecture

**آخرین به‌روزرسانی:** 2026-01-27
**نسخه:** 2.0.0

---

## فهرست مطالب

- [نمای کلی](#نمای-کلی)
- [لایه‌بندی معماری](#لایه‌بندی-معماری)
- [جریان داده](#جریان-داده)
- [سرویس‌ها و کامپوننت‌ها](#سرویس‌ها-و-کامپوننت‌ها)
- [مدل‌های داده](#مدل‌های-داده)
- [API Endpoints](#api-endpoints)
- [امنیت](#امنیت)
- [مقیاس‌پذیری](#مقیاس‌پذیری)

---

## نمای کلی

### هدف سیستم

سیستم **AI Creator Engine** یک پلتفرم یکپارچه برای:
1. تولید پروژه‌های نرم‌افزاری با هوش مصنوعی
2. مدیریت و هماهنگی چندین پروایدر AI
3. مناظره و همکاری بین مدل‌های مختلف
4. استقرار خودکار به پلتفرم‌های ابری
5. تحلیل و نظارت بر سلامت پروژه‌ها

### معماری سطح بالا

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                      (Next.js 14 + React)                       │
│   ┌─────────┬─────────┬─────────┬─────────┬─────────┐          │
│   │  Home   │ Creator │ Projects│ Debate  │Settings │          │
│   └────┬────┴────┬────┴────┬────┴────┬────┴────┬────┘          │
└────────┼─────────┼─────────┼─────────┼─────────┼────────────────┘
         │         │         │         │         │
         └─────────┴─────────┴────┬────┴─────────┘
                                  │ HTTP/REST
┌─────────────────────────────────┼───────────────────────────────┐
│                         API GATEWAY                              │
│                      (FastAPI + CORS)                           │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────┐
│                         BACKEND                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    API ROUTES LAYER                        │ │
│  │  ┌─────────┬─────────┬─────────┬─────────┬─────────┐      │ │
│  │  │projects │ creator │ debate  │ models  │settings │      │ │
│  │  │diagrams │ runtime │ upload  │ github  │ reports │      │ │
│  │  └─────────┴─────────┴─────────┴─────────┴─────────┘      │ │
│  └────────────────────────────┬───────────────────────────────┘ │
│                               │                                  │
│  ┌────────────────────────────┼───────────────────────────────┐ │
│  │                    SERVICE LAYER                           │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐    │ │
│  │  │  AI Manager  │  │Creator Engine │  │Debate Service│    │ │
│  │  └──────┬───────┘  └───────────────┘  └──────────────┘    │ │
│  │         │                                                  │ │
│  │  ┌──────┴────────────────────────────────────────────┐    │ │
│  │  │              AI PROVIDER SERVICES                  │    │ │
│  │  │  ┌────────┬────────┬────────┬────────┬────────┐   │    │ │
│  │  │  │OpenAI  │ Claude │ Gemini │DeepSeek│Perplexity  │    │ │
│  │  │  └────────┴────────┴────────┴────────┴────────┘   │    │ │
│  │  └───────────────────────────────────────────────────┘    │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐    │ │
│  │  │Project Service│ │ Deploy Service│  │Runtime Exec  │    │ │
│  │  └──────────────┘  └───────────────┘  └──────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │                                  │
│  ┌────────────────────────────┼───────────────────────────────┐ │
│  │                    DATA LAYER                              │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐    │ │
│  │  │   SQLite     │  │GitHub Storage │  │  File System │    │ │
│  │  │   (SQLAlchemy)│ │ (Persistence) │  │  (Projects)  │    │ │
│  │  └──────────────┘  └───────────────┘  └──────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │  OpenAI  │  Claude  │  Gemini  │  Render  │  GitHub  │      │
│  │   API    │   API    │   API    │   API    │   API    │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## لایه‌بندی معماری

### 1. لایه Frontend (Presentation Layer)

**تکنولوژی:** Next.js 14 + React 18 + TypeScript

```
frontend/src/
├── app/                    # App Router (Next.js 14)
│   ├── page.tsx           # صفحه اصلی (داشبورد)
│   ├── layout.tsx         # لایه‌بندی RTL
│   ├── creator/           # موتور خالق
│   ├── projects/          # مدیریت پروژه‌ها
│   ├── project/[id]/      # جزئیات پروژه
│   ├── debate/            # مناظره AI
│   ├── diagrams/          # نمودارها
│   ├── settings/          # تنظیمات
│   ├── models/            # مدل‌های AI
│   └── archive/           # آرشیو
│
├── components/            # کامپوننت‌های مشترک
│   ├── Layout.tsx        # ناوبری و theme
│   └── FileUpload.tsx    # آپلود فایل
│
├── services/             # سرویس‌های API
│   └── api.ts           # کلاینت API
│
└── types/               # TypeScript definitions
    └── index.ts
```

**مسئولیت‌ها:**
- رابط کاربری RTL (فارسی)
- مدیریت state (Zustand)
- فراخوانی API ها
- نمایش نتایج و خطاها

### 2. لایه API (API Layer)

**تکنولوژی:** FastAPI + Pydantic

```
backend/app/api/routes/
├── projects.py           # CRUD پروژه‌ها
├── creator.py            # موتور خالق
├── debate.py             # مناظره AI
├── models.py             # مدل‌های AI
├── settings.py           # تنظیمات
├── diagrams.py           # نمودارها
├── runtime.py            # اجرای پروژه
├── upload.py             # آپلود فایل
├── github_import.py      # ایمپورت GitHub
├── project_structure.py  # ساختار پروژه
├── project_journal.py    # ژورنال
├── project_memory.py     # حافظه پروژه
├── simple_projects.py    # API ساده
├── unified_api.py        # API یکپارچه
├── orchestrator.py       # هماهنگ‌کننده
├── external.py           # سرویس‌های خارجی
├── external_projects.py  # پروژه‌های خارجی
├── config.py             # پیکربندی
└── chat.py               # چت
```

**مسئولیت‌ها:**
- اعتبارسنجی درخواست‌ها
- مسیریابی به سرویس‌های مناسب
- مدیریت خطا و پاسخ‌دهی
- مستندسازی خودکار (Swagger/OpenAPI)

### 3. لایه سرویس (Service Layer)

**تکنولوژی:** Python + asyncio

```
backend/app/services/
│
├── AI Management
│   ├── ai_manager.py         # مدیریت مرکزی AI (singleton)
│   ├── ai_base.py            # کلاس پایه سرویس AI
│   ├── openai_service.py     # سرویس OpenAI
│   ├── claude_service.py     # سرویس Claude
│   ├── gemini_service.py     # سرویس Gemini
│   ├── deepseek_service.py   # سرویس DeepSeek
│   └── perplexity_service.py # سرویس Perplexity
│
├── Core Business Logic
│   ├── creator_engine.py     # موتور تولید پروژه
│   ├── debate_service.py     # سرویس مناظره
│   ├── project_service.py    # مدیریت پروژه
│   └── smart_orchestrator.py # هماهنگ‌کننده هوشمند
│
├── Storage & Persistence
│   ├── github_storage.py     # ذخیره‌سازی GitHub
│   ├── github_import.py      # ایمپورت از GitHub
│   ├── storage_service.py    # ذخیره‌سازی محلی
│   ├── unified_storage.py    # ذخیره‌سازی یکپارچه
│   └── db_service.py         # عملیات دیتابیس
│
├── Infrastructure
│   ├── deploy_service.py     # استقرار Render/Railway
│   ├── runtime_executor.py   # اجرای Docker
│   ├── capability_detector.py# تشخیص قابلیت‌ها
│   └── external_monitor.py   # مانیتورینگ
│
└── Utilities
    ├── diagram_service.py    # نمودار Mermaid
    ├── dynamic_config.py     # پیکربندی پویا
    ├── simple_creator.py     # ساخت ساده
    └── smart_import.py       # ایمپورت هوشمند
```

**مسئولیت‌ها:**
- منطق کسب‌وکار اصلی
- هماهنگی بین مدل‌های AI
- مدیریت state و session
- ذخیره‌سازی و بازیابی داده

### 4. لایه داده (Data Layer)

**تکنولوژی:** SQLite + SQLAlchemy + GitHub API

```
backend/app/
├── core/
│   ├── database.py       # اتصال SQLite + migrations
│   ├── config.py         # تنظیمات سیستم
│   └── models_registry.py# رجیستری مدل‌های AI
│
└── models/
    ├── project.py        # مدل پروژه
    ├── debate.py         # مدل مناظره
    ├── setting.py        # مدل تنظیمات
    └── ai_log.py         # لاگ AI
```

**ساختار دیتابیس:**

```sql
-- جدول پروژه‌ها
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    project_type TEXT,
    status TEXT DEFAULT 'created',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    metadata JSON
);

-- جدول مناظره‌ها
CREATE TABLE debates (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    work_mode TEXT,
    status TEXT DEFAULT 'created',
    models JSON,
    messages JSON,
    results JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول تنظیمات
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول لاگ AI
CREATE TABLE ai_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT,
    provider TEXT,
    tokens_used INTEGER,
    cost REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## جریان داده

### 1. جریان ساخت پروژه

```
User Input (name, description, type)
         │
         ▼
┌─────────────────┐
│  Frontend UI    │  POST /api/creator/projects/create
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Creator Route  │  Validate input, call service
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Creator Engine  │  Orchestrate project generation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI Manager    │  Select best model
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Provider    │  Generate project structure
│  (GPT-4/Claude) │  Generate file contents
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Project Service │  Save to database
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Storage  │  Persist to GitHub (optional)
└─────────────────┘
```

### 2. جریان مناظره AI

```
User Input (topic, models, mode)
         │
         ▼
┌─────────────────┐
│  Frontend UI    │  POST /api/debate/create
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Debate Route   │  Create debate session
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Debate Service  │  Assign roles to models
└────────┬────────┘
         │
         ▼ (parallel)
┌─────────┴─────────┐
│   │   │   │   │   │
▼   ▼   ▼   ▼   ▼   ▼
┌───┬───┬───┬───┬───┐
│M1 │M2 │M3 │M4 │M5 │  Models generate responses
└───┴───┴───┴───┴───┘
         │
         ▼
┌─────────────────┐
│  Scorer Model   │  Score responses
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Judge Model    │  Select winner
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Summarizer      │  Generate summary
└─────────────────┘
```

### 3. جریان بررسی خودکار (در حال توسعه)

```
Scheduled Trigger / Manual Request
         │
         ▼
┌─────────────────┐
│Analysis Scheduler│  Check schedule
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Project Analyzer │  Load project files
└────────┬────────┘
         │
         ▼ (parallel)
┌─────────┴─────────┐
│   │   │   │   │   │
▼   ▼   ▼   ▼   ▼   ▼
┌───┬───┬───┬───┬───┐
│M1 │M2 │M3 │...│Mn │  Models analyze each file
└───┴───┴───┴───┴───┘
         │
         ▼
┌─────────────────┐
│ Health Scorer   │  Calculate scores
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Report Generator │  Generate report
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Model Validator │  Validate & score models
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update Profiles │  Update model profiles
└─────────────────┘
```

---

## سرویس‌ها و کامپوننت‌ها

### AI Manager (مدیریت مرکزی)

```python
class AIManager:
    """مدیریت مرکزی همه سرویس‌های AI"""

    def __init__(self):
        self._services: Dict[ModelProvider, AIServiceBase] = {}
        self._initialize_services()

    def get_available_providers(self) -> List[str]:
        """لیست provider های فعال"""

    def get_available_models(self) -> List[AIModel]:
        """لیست همه مدل‌های قابل استفاده"""

    def smart_select_models(
        self,
        prompt: str,
        required_capabilities: List[ModelCapability],
        max_models: int = 3
    ) -> List[AIModel]:
        """انتخاب هوشمند مدل‌ها"""

    async def generate(
        self,
        model_id: str,
        messages: List[Message],
        max_tokens: int = 4096
    ) -> AIResponse:
        """تولید پاسخ از یک مدل خاص"""

    async def generate_with_fallback(
        self,
        model_ids: List[str],
        messages: List[Message]
    ) -> AIResponse:
        """تولید با fallback به مدل‌های دیگر"""
```

### Creator Engine (موتور تولید)

```python
class CreatorEngine:
    """موتور تولید پروژه با AI"""

    def __init__(self):
        self.ai_orchestrator = None
        self.project_service = None

    def initialize(self, ai_manager: AIManager):
        """راه‌اندازی با AI Manager"""

    async def create_project(
        self,
        name: str,
        description: str,
        project_type: str,
        model_id: str = None
    ) -> ProjectContext:
        """ساخت پروژه کامل"""

    async def generate_structure(
        self,
        description: str
    ) -> Dict:
        """تولید ساختار پروژه"""

    async def generate_file(
        self,
        file_path: str,
        context: Dict
    ) -> str:
        """تولید محتوای یک فایل"""
```

### Debate Service (سرویس مناظره)

```python
class DebateService:
    """سرویس مناظره بین AI ها"""

    def __init__(self, ai_manager: AIManager):
        self.ai_manager = ai_manager

    async def create_debate(
        self,
        topic: str,
        model_ids: List[str],
        work_mode: str = "debate"
    ) -> Debate:
        """ایجاد مناظره جدید"""

    async def run_round(
        self,
        debate_id: str
    ) -> Dict:
        """اجرای یک دور مناظره"""

    async def score_responses(
        self,
        debate_id: str
    ) -> Dict:
        """امتیازدهی پاسخ‌ها"""

    async def judge(
        self,
        debate_id: str
    ) -> Dict:
        """انتخاب برنده"""
```

### Project Analyzer (در حال توسعه)

```python
class ProjectAnalyzer:
    """تحلیل‌گر پروژه"""

    def __init__(self, ai_manager: AIManager):
        self.ai_manager = ai_manager
        self.health_scorer = HealthScorer()

    async def analyze_project(
        self,
        project_id: str,
        model_ids: List[str]
    ) -> AnalysisReport:
        """تحلیل کامل پروژه"""

    async def analyze_file(
        self,
        file_path: str,
        file_content: str,
        model_id: str
    ) -> FileAnalysis:
        """تحلیل یک فایل"""

    async def compare_with_roadmap(
        self,
        project_id: str
    ) -> ComparisonReport:
        """مقایسه با نقشه راه"""
```

---

## مدل‌های داده

### AIModel (رجیستری مدل)

```python
class AIModel(BaseModel):
    id: str
    provider: ModelProvider
    name: str
    endpoint: str
    capabilities: List[ModelCapability]
    max_tokens: int = 4096
    context_window: int = 8192
    strengths: List[str] = []
    weaknesses: List[str] = []
    cost_per_1k_tokens: float = 0.01
    priority: int = 5
    enabled: bool = True
    supports_images: bool = False
```

### ProjectContext

```python
class ProjectContext(BaseModel):
    id: str
    name: str
    description: str
    project_type: str
    status: str  # created, generating, completed, deployed
    progress: int = 0
    files: List[Dict]
    structure: Dict
    metadata: Dict
    created_at: datetime
    updated_at: datetime
```

### DebateSession

```python
class DebateSession(BaseModel):
    id: str
    topic: str
    work_mode: str  # debate, collaborate, analyze
    models: List[str]
    messages: List[DebateMessage]
    scores: Dict[str, float]
    winner: Optional[str]
    summary: Optional[str]
    status: str  # created, running, completed
```

### AnalysisReport (در حال توسعه)

```python
class AnalysisReport(BaseModel):
    id: str
    project_id: str
    timestamp: datetime
    models_used: List[str]
    overall_score: float  # 0-100
    overall_color: str  # green, yellow, orange, red

    file_analyses: List[FileAnalysis]
    structure_analysis: StructureAnalysis
    roadmap_comparison: RoadmapComparison

    recommendations: List[str]
    model_validations: Dict[str, ModelValidation]
```

---

## API Endpoints

### پروژه‌ها

| Method | Endpoint | توضیح |
|--------|----------|-------|
| GET | `/api/projects` | لیست پروژه‌ها |
| POST | `/api/projects` | ایجاد پروژه |
| GET | `/api/projects/{id}` | جزئیات پروژه |
| PUT | `/api/projects/{id}` | به‌روزرسانی |
| DELETE | `/api/projects/{id}` | حذف |
| POST | `/api/projects/{id}/deploy` | استقرار |
| GET | `/api/projects/{id}/structure` | ساختار |
| GET | `/api/projects/{id}/files` | فایل‌ها |

### موتور خالق

| Method | Endpoint | توضیح |
|--------|----------|-------|
| POST | `/api/creator/projects/create` | ساخت با AI |
| POST | `/api/creator/files` | عملیات فایل |
| POST | `/api/creator/commands` | اجرای دستور |
| POST | `/api/creator/git` | عملیات Git |

### مناظره

| Method | Endpoint | توضیح |
|--------|----------|-------|
| POST | `/api/debate/create` | ایجاد مناظره |
| GET | `/api/debate/` | لیست مناظره‌ها |
| GET | `/api/debate/{id}` | جزئیات |
| POST | `/api/debate/{id}/run-full` | اجرای کامل |
| POST | `/api/debate/{id}/round` | یک دور |
| POST | `/api/debate/{id}/judge` | داوری |

### مدل‌ها

| Method | Endpoint | توضیح |
|--------|----------|-------|
| GET | `/api/models` | همه مدل‌ها |
| GET | `/api/models/available` | فعال‌ها |
| GET | `/api/models/{id}` | جزئیات مدل |
| POST | `/api/models/smart-select` | انتخاب هوشمند |

### تنظیمات

| Method | Endpoint | توضیح |
|--------|----------|-------|
| GET | `/api/settings/api-keys/status` | وضعیت کلیدها |
| PUT | `/api/settings/api-keys` | ذخیره کلید AI |
| PUT | `/api/settings/deploy-keys` | ذخیره کلید Deploy |
| GET | `/api/settings/providers` | پروایدرها |

### تحلیل (در حال توسعه)

| Method | Endpoint | توضیح |
|--------|----------|-------|
| POST | `/api/analysis/run` | اجرای تحلیل |
| GET | `/api/analysis/{id}` | نتیجه تحلیل |
| GET | `/api/analysis/history` | تاریخچه |
| GET | `/api/analysis/schedule` | زمان‌بندی |
| PUT | `/api/analysis/schedule` | تنظیم زمان‌بندی |

---

## امنیت

### احراز هویت

```python
# در حال حاضر بدون احراز هویت
# برنامه‌ریزی‌شده: JWT + API Keys

# تنظیمات آینده:
SECURITY_CONFIG = {
    "jwt_secret": "...",
    "jwt_algorithm": "HS256",
    "token_expire_minutes": 60,
    "api_key_header": "X-API-Key"
}
```

### ذخیره کلیدها

```python
# کلیدها در دیتابیس ذخیره می‌شوند
# توصیه: استفاده از encryption

Setting.set_value(db, "api_key_openai", encrypted_value)
```

### CORS

```python
# تنظیم فعلی (توسعه)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تنظیم تولید (پیشنهادی)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## مقیاس‌پذیری

### افقی (Horizontal)

```yaml
# docker-compose.scale.yml
services:
  backend:
    image: ai-creator-backend
    deploy:
      replicas: 3
    environment:
      - DATABASE_URL=postgresql://...

  frontend:
    image: ai-creator-frontend
    deploy:
      replicas: 2

  nginx:
    image: nginx
    ports:
      - "80:80"
    depends_on:
      - backend
      - frontend
```

### عمودی (Vertical)

```python
# تنظیمات برای سرور قوی‌تر
PERFORMANCE_CONFIG = {
    "workers": 4,  # تعداد worker ها
    "max_concurrent_requests": 100,
    "request_timeout": 120,
    "max_tokens_per_request": 8192,
}
```

### Caching (پیشنهادی)

```python
# استفاده از Redis برای caching
from redis import Redis

cache = Redis(host='localhost', port=6379)

async def get_models_cached():
    cached = cache.get("available_models")
    if cached:
        return json.loads(cached)

    models = await ai_manager.get_available_models()
    cache.setex("available_models", 300, json.dumps(models))
    return models
```

---

## نتیجه‌گیری

این معماری:
- **ماژولار:** هر سرویس مستقل و قابل تست
- **مقیاس‌پذیر:** قابل گسترش افقی و عمودی
- **انعطاف‌پذیر:** اضافه کردن پروایدر جدید آسان
- **قابل نگهداری:** جداسازی مناسب concerns

برای جزئیات بیشتر به [ROADMAP.md](./ROADMAP.md) مراجعه کنید.

---

**آخرین به‌روزرسانی:** 2026-01-27
