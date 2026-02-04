/**
 * داده‌های راهنمای جامع برای تمام صفحات و المان‌ها
 * این داده‌ها بر اساس بررسی دقیق کد منبع استخراج شده‌اند
 */

export interface ElementHelp {
  id: string;
  title: string;
  description: string;
  type: 'button' | 'input' | 'section' | 'tab' | 'panel' | 'checkbox' | 'select' | 'area';
  tips?: string[];
  relatedElements?: string[];
}

export interface PageHelp {
  id: string;
  title: string;
  description: string;
  path: string;
  overview: string;
  features: string[];
  elements: ElementHelp[];
  diagram: string; // Mermaid diagram
  subPages?: PageHelp[];
}

// ============================================
// داشبورد اصلی (خانه)
// ============================================
export const dashboardHelp: PageHelp = {
  id: 'dashboard',
  title: 'داشبورد اصلی',
  description: 'صفحه اصلی سیستم مدیریت پروژه با هوش مصنوعی',
  path: '/',
  overview: `داشبورد اصلی نقطه ورود به تمام بخش‌های سیستم است. از اینجا می‌توانید به صفحات مختلف دسترسی پیدا کنید، وضعیت مدل‌های AI را ببینید و عملیات سریع انجام دهید.`,
  features: [
    'دسترسی سریع به تمام بخش‌های سیستم',
    'نمایش وضعیت مدل‌های AI فعال',
    'آمار کلی پروژه‌ها',
    'لینک‌های میانبر به عملیات پرکاربرد',
  ],
  elements: [
    {
      id: 'nav-projects',
      title: 'پروژه‌ها',
      description: 'رفتن به صفحه مدیریت پروژه‌ها. از اینجا می‌توانید پروژه‌های موجود را ببینید، پروژه جدید بسازید یا از GitHub وارد کنید.',
      type: 'button',
      tips: ['پروژه‌های GitHub را می‌توانید با توکن شخصی import کنید'],
    },
    {
      id: 'nav-creator',
      title: 'موتور خالق',
      description: 'صفحه ساخت پروژه جدید با کمک هوش مصنوعی. یک توضیح بدهید و AI پروژه را می‌سازد.',
      type: 'button',
      tips: ['توضیحات دقیق‌تر = نتیجه بهتر', 'می‌توانید نوع پروژه را مشخص کنید'],
    },
    {
      id: 'nav-debate',
      title: 'مناظره AI',
      description: 'صفحه مناظره بین مدل‌های مختلف AI. سوالی بپرسید و چند مدل پاسخ می‌دهند و با هم بحث می‌کنند.',
      type: 'button',
      tips: ['حالت‌های مختلف: مناظره، همکاری، تحقیق عمیق', 'نتیجه توسط داور AI ارزیابی می‌شود'],
    },
    {
      id: 'nav-models',
      title: 'مدل‌های AI',
      description: 'مشاهده و مدیریت تمام مدل‌های هوش مصنوعی. فعال/غیرفعال کردن، تنظیم اولویت و تست توانایی.',
      type: 'button',
      tips: ['از تب مدیریت می‌توانید مدل‌ها را فعال/غیرفعال کنید', 'تست توانایی نمره و نشان می‌دهد'],
    },
    {
      id: 'nav-settings',
      title: 'تنظیمات',
      description: 'تنظیمات سیستم شامل کلیدهای API، توکن‌های Deploy، محدودیت‌ها و لاگ‌ها.',
      type: 'button',
      tips: ['کلیدهای API را اینجا وارد کنید', 'توکن GitHub برای import پروژه‌های خصوصی'],
    },
    {
      id: 'nav-diagrams',
      title: 'نمودارها',
      description: 'تولید نمودارهای مختلف با Mermaid. فلوچارت، ER، sequence و ...',
      type: 'button',
    },
    {
      id: 'nav-archive',
      title: 'آرشیو',
      description: 'آرشیو مناظرات قبلی و فایل‌های ذخیره شده.',
      type: 'button',
    },
    {
      id: 'models-status',
      title: 'وضعیت مدل‌ها',
      description: 'نمایش تعداد مدل‌های فعال از هر Provider. سبز = API فعال، خاکستری = غیرفعال.',
      type: 'section',
      tips: ['کلیک روی هر provider فیلتر می‌کند', 'اگر مدلی قرمز است، کلید API را چک کنید'],
    },
    {
      id: 'page-background',
      title: 'داشبورد',
      description: 'این صفحه اصلی سیستم است. از منوی بالا یا کارت‌ها می‌توانید به بخش‌های مختلف بروید.',
      type: 'area',
    },
  ],
  diagram: `graph TB
    subgraph Dashboard["🏠 داشبورد اصلی"]
        Nav["منوی ناوبری"]
        Stats["آمار مدل‌ها"]
        Quick["دسترسی سریع"]
    end

    subgraph Pages["📄 صفحات"]
        Projects["پروژه‌ها"]
        Creator["موتور خالق"]
        Debate["مناظره AI"]
        Models["مدل‌ها"]
        Settings["تنظیمات"]
        Diagrams["نمودارها"]
        Archive["آرشیو"]
    end

    Nav --> Projects
    Nav --> Creator
    Nav --> Debate
    Nav --> Models
    Nav --> Settings
    Nav --> Diagrams
    Nav --> Archive

    Quick --> Projects
    Quick --> Creator

    Stats --> Models`,
};

// ============================================
// صفحه پروژه‌ها
// ============================================
export const projectsHelp: PageHelp = {
  id: 'projects',
  title: 'مدیریت پروژه‌ها',
  description: 'لیست و مدیریت تمام پروژه‌های سیستم',
  path: '/projects',
  overview: `در این صفحه تمام پروژه‌های شما نمایش داده می‌شود. می‌توانید پروژه جدید بسازید، از GitHub وارد کنید، یا پروژه‌های موجود را مدیریت کنید.`,
  features: [
    'ساخت پروژه جدید',
    'Import از GitHub (public و private)',
    'مشاهده جزئیات پروژه',
    'حذف پروژه',
    'فیلتر بر اساس نوع (همه / GitHub)',
  ],
  elements: [
    {
      id: 'btn-new-project',
      title: 'پروژه جدید',
      description: 'ساخت یک پروژه خالی جدید. فقط نام و توضیحات وارد کنید.',
      type: 'button',
      tips: ['برای پروژه‌های ساده از این استفاده کنید', 'برای ساخت با AI به موتور خالق بروید'],
    },
    {
      id: 'btn-github-import',
      title: 'Import از GitHub',
      description: 'وارد کردن یک repository از GitHub. هم public و هم private پشتیبانی می‌شود.',
      type: 'button',
      tips: [
        'برای repo های private نیاز به توکن دارید',
        'توکن را می‌توانید در تنظیمات ذخیره کنید',
        'فرمت: https://github.com/owner/repo یا owner/repo',
      ],
    },
    {
      id: 'tab-all',
      title: 'تب همه',
      description: 'نمایش تمام پروژه‌ها (هم دستی و هم GitHub)',
      type: 'tab',
    },
    {
      id: 'tab-github',
      title: 'تب GitHub',
      description: 'فقط پروژه‌های import شده از GitHub',
      type: 'tab',
    },
    {
      id: 'btn-refresh',
      title: 'بروزرسانی',
      description: 'بارگذاری مجدد لیست پروژه‌ها از سرور',
      type: 'button',
    },
    {
      id: 'project-card',
      title: 'کارت پروژه',
      description: 'هر کارت یک پروژه را نشان می‌دهد. کلیک کنید تا جزئیات در سمت چپ نمایش داده شود.',
      type: 'section',
      tips: ['آیکون GitHub = پروژه import شده', 'قفل = پروژه private'],
    },
    {
      id: 'project-status',
      title: 'وضعیت پروژه',
      description: 'وضعیت‌های ممکن: تکمیل شده (سبز)، در حال انجام (آبی)، در انتظار (زرد)، از GitHub (بنفش)',
      type: 'section',
    },
    {
      id: 'project-details',
      title: 'پنل جزئیات',
      description: 'جزئیات پروژه انتخاب شده: نام، توضیحات، وضعیت، آمار GitHub (ستاره، fork، فایل‌ها)',
      type: 'panel',
    },
    {
      id: 'btn-open-project',
      title: 'باز کردن',
      description: 'رفتن به صفحه کامل پروژه با تمام تب‌ها و قابلیت‌ها',
      type: 'button',
    },
    {
      id: 'btn-delete-project',
      title: 'حذف',
      description: 'حذف کامل پروژه. این عمل قابل بازگشت نیست!',
      type: 'button',
      tips: ['قبل از حذف تایید می‌خواهد', 'فایل‌های مرتبط هم حذف می‌شوند'],
    },
    {
      id: 'modal-create',
      title: 'فرم ساخت پروژه',
      description: 'مودال ساخت پروژه جدید با فیلدهای نام و توضیحات',
      type: 'panel',
    },
    {
      id: 'input-project-name',
      title: 'نام پروژه',
      description: 'نام پروژه (اجباری). بهتر است کوتاه و معنادار باشد.',
      type: 'input',
    },
    {
      id: 'input-project-desc',
      title: 'توضیحات',
      description: 'توضیحات پروژه (اختیاری). برای یادآوری هدف پروژه مفید است.',
      type: 'input',
    },
    {
      id: 'modal-github',
      title: 'فرم Import GitHub',
      description: 'مودال import از GitHub با فیلدهای URL و Token',
      type: 'panel',
    },
    {
      id: 'input-github-url',
      title: 'آدرس Repository',
      description: 'آدرس کامل یا کوتاه repo. مثال: https://github.com/owner/repo یا owner/repo',
      type: 'input',
    },
    {
      id: 'input-github-token',
      title: 'توکن GitHub',
      description: 'برای repo های private نیاز است. از Settings > Developer settings > Personal access tokens بسازید.',
      type: 'input',
      tips: ['scope های لازم: repo, read:org', 'توکن را در تنظیمات ذخیره کنید تا هر بار وارد نکنید'],
    },
    {
      id: 'checkbox-global-token',
      title: 'استفاده از توکن ذخیره شده',
      description: 'اگر قبلاً توکن را در تنظیمات ذخیره کرده‌اید، این گزینه فعال می‌شود.',
      type: 'checkbox',
    },
    {
      id: 'btn-check-repo',
      title: 'بررسی دسترسی',
      description: 'قبل از import، دسترسی به repo را چک می‌کند و اطلاعات آن را نمایش می‌دهد.',
      type: 'button',
    },
    {
      id: 'btn-import',
      title: 'Import پروژه',
      description: 'شروع import پروژه. فایل‌ها دانلود و در سیستم ذخیره می‌شوند.',
      type: 'button',
    },
    {
      id: 'page-background',
      title: 'صفحه پروژه‌ها',
      description: 'این صفحه برای مدیریت پروژه‌هاست. از سمت راست لیست و از سمت چپ جزئیات را ببینید.',
      type: 'area',
    },
  ],
  diagram: `graph TB
    subgraph ProjectsPage["📁 صفحه پروژه‌ها"]
        Header["هدر + دکمه‌ها"]
        Tabs["تب‌ها: همه | GitHub"]
        List["لیست پروژه‌ها"]
        Details["پنل جزئیات"]
    end

    subgraph Actions["⚡ عملیات"]
        Create["ساخت پروژه"]
        Import["Import GitHub"]
        Open["باز کردن"]
        Delete["حذف"]
    end

    subgraph Modals["📋 مودال‌ها"]
        CreateModal["فرم ساخت"]
        GitHubModal["فرم GitHub"]
    end

    Header --> Create
    Header --> Import
    Create --> CreateModal
    Import --> GitHubModal

    Tabs --> List
    List --> Details
    Details --> Open
    Details --> Delete

    GitHubModal --> CheckRepo["بررسی دسترسی"]
    CheckRepo --> ImportBtn["Import"]`,
};

// ============================================
// صفحه جزئیات پروژه
// ============================================
export const projectDetailHelp: PageHelp = {
  id: 'project-detail',
  title: 'جزئیات پروژه',
  description: 'صفحه کامل مدیریت یک پروژه با تمام قابلیت‌ها',
  path: '/projects/[id]',
  overview: `صفحه جزئیات پروژه شامل تب‌های مختلف برای مدیریت کامل پروژه است: فایل‌ها، حافظه AI، ساختار، ژورنال تغییرات، سلامت پروژه و بازرس ویژه.`,
  features: [
    'مشاهده و ویرایش فایل‌ها',
    'حافظه هوشمند پروژه',
    'ساختار درختی فایل‌ها',
    'ژورنال تغییرات',
    'تحلیل سلامت پروژه',
    'بازرس ویژه برای تحلیل عمیق',
    'آپلود فایل جدید',
  ],
  elements: [
    {
      id: 'tab-files',
      title: 'تب فایل‌ها',
      description: 'لیست تمام فایل‌های پروژه. می‌توانید فایل‌ها را ببینید، ویرایش کنید یا حذف کنید.',
      type: 'tab',
      tips: ['کلیک روی فایل = نمایش محتوا', 'دابل‌کلیک = ویرایش'],
    },
    {
      id: 'tab-memory',
      title: 'تب حافظه',
      description: 'حافظه هوشمند پروژه. AI اطلاعات مهم پروژه را اینجا ذخیره می‌کند.',
      type: 'tab',
      tips: ['برای بهبود پاسخ‌های AI', 'می‌توانید دستی هم اضافه کنید'],
    },
    {
      id: 'tab-structure',
      title: 'تب ساختار',
      description: 'نمایش ساختار درختی فایل‌ها و پوشه‌های پروژه.',
      type: 'tab',
    },
    {
      id: 'tab-journal',
      title: 'تب ژورنال',
      description: 'تاریخچه تغییرات پروژه. هر تغییر با تاریخ و توضیحات ثبت می‌شود.',
      type: 'tab',
    },
    {
      id: 'tab-health',
      title: 'تب سلامت',
      description: 'تحلیل سلامت پروژه: کیفیت کد، امنیت، پوشش تست، مستندات و ...',
      type: 'tab',
      tips: ['نمره 0-100', 'پیشنهادات بهبود ارائه می‌شود'],
    },
    {
      id: 'tab-inspector',
      title: 'تب بازرس ویژه',
      description: 'ابزار پیشرفته برای بازرسی و تحلیل عمیق پروژه. شامل بررسی‌های تخصصی و گزارش‌های دقیق.',
      type: 'tab',
      tips: ['تحلیل عمیق ساختار پروژه', 'شناسایی مشکلات پنهان', 'پیشنهادات بهینه‌سازی'],
    },
    {
      id: 'btn-upload',
      title: 'آپلود فایل',
      description: 'آپلود فایل جدید به پروژه. انواع فایل‌های متنی پشتیبانی می‌شود.',
      type: 'button',
    },
    {
      id: 'btn-analyze',
      title: 'تحلیل پروژه',
      description: 'شروع تحلیل عمیق پروژه با AI. نتایج در تب سلامت نمایش داده می‌شود.',
      type: 'button',
    },
    {
      id: 'file-list',
      title: 'لیست فایل‌ها',
      description: 'لیست فایل‌های پروژه با نام، نوع و اندازه.',
      type: 'section',
    },
    {
      id: 'file-viewer',
      title: 'نمایشگر فایل',
      description: 'محتوای فایل انتخاب شده با syntax highlighting.',
      type: 'panel',
    },
    {
      id: 'health-score',
      title: 'نمره سلامت',
      description: 'نمره کلی سلامت پروژه از 0 تا 100. سبز = خوب، زرد = متوسط، قرمز = نیاز به بهبود.',
      type: 'section',
    },
    {
      id: 'health-diagram',
      title: 'نمودار سلامت',
      description: 'نمودار رادار نشان‌دهنده نمرات مختلف: کد، امنیت، تست، مستندات.',
      type: 'panel',
    },
    {
      id: 'page-background',
      title: 'صفحه پروژه',
      description: 'این صفحه برای مدیریت کامل یک پروژه است. از تب‌ها برای دسترسی به بخش‌های مختلف استفاده کنید.',
      type: 'area',
    },
  ],
  diagram: `graph TB
    subgraph ProjectPage["📂 صفحه پروژه"]
        Header["هدر: نام + دکمه‌ها"]
        Tabs["تب‌ها"]
    end

    subgraph TabsContent["📑 محتوای تب‌ها"]
        Files["فایل‌ها"]
        Memory["حافظه AI"]
        Structure["ساختار"]
        Journal["ژورنال"]
        Health["سلامت"]
        Inspector["🔍 بازرس ویژه"]
    end

    subgraph FilesTab["📄 تب فایل‌ها"]
        FileList["لیست فایل‌ها"]
        FileViewer["نمایشگر"]
        Upload["آپلود"]
    end

    subgraph HealthTab["💊 تب سلامت"]
        Score["نمره کلی"]
        Diagram["نمودار رادار"]
        Suggestions["پیشنهادات"]
    end

    subgraph InspectorTab["🔍 بازرس ویژه"]
        DeepAnalysis["تحلیل عمیق"]
        Reports["گزارش‌های تخصصی"]
        Issues["مشکلات پنهان"]
    end

    Tabs --> Files
    Tabs --> Memory
    Tabs --> Structure
    Tabs --> Journal
    Tabs --> Health
    Tabs --> Inspector

    Files --> FileList
    Files --> FileViewer
    Files --> Upload

    Health --> Score
    Health --> Diagram
    Health --> Suggestions

    Inspector --> DeepAnalysis
    Inspector --> Reports
    Inspector --> Issues`,
};


// ============================================
// صفحه مناظره AI
// ============================================
export const debateHelp: PageHelp = {
  id: 'debate',
  title: 'مناظره AI',
  description: 'مناظره و بحث بین مدل‌های مختلف هوش مصنوعی',
  path: '/debate',
  overview: `در این صفحه می‌توانید سوالی بپرسید و چند مدل AI همزمان پاسخ می‌دهند. سپس با هم بحث می‌کنند و در نهایت یک داور نتیجه را اعلام می‌کند.`,
  features: [
    'پرسش از چند مدل همزمان',
    'حالت‌های مختلف: مناظره، همکاری، تحقیق عمیق',
    'داوری نهایی توسط AI',
    'ذخیره تاریخچه مناظرات',
  ],
  elements: [
    {
      id: 'models-status',
      title: 'وضعیت مدل‌ها',
      description: 'مدل‌های فعال که در مناظره شرکت می‌کنند. اگر خالی است، به تنظیمات بروید.',
      type: 'section',
      tips: ['حداقل 2 مدل فعال نیاز است', 'مدل‌های بیشتر = مناظره غنی‌تر'],
    },
    {
      id: 'select-mode',
      title: 'حالت کار',
      description: 'انتخاب نوع تعامل بین مدل‌ها.',
      type: 'select',
      tips: [
        'خودکار: سیستم بهترین حالت را انتخاب می‌کند',
        'مناظره: مدل‌ها با هم بحث می‌کنند',
        'همکاری: مدل‌ها با هم کار می‌کنند',
        'سریع: پاسخ سریع بدون بحث',
      ],
    },
    {
      id: 'input-prompt',
      title: 'سوال شما',
      description: 'سوال یا موضوع مناظره را بنویسید. هر چه دقیق‌تر، پاسخ‌ها بهتر.',
      type: 'input',
      tips: ['سوالات باز بهتر هستند', 'می‌توانید کد هم بگذارید'],
    },
    {
      id: 'btn-start',
      title: 'شروع مناظره',
      description: 'شروع مناظره. مدل‌ها یکی یکی پاسخ می‌دهند.',
      type: 'button',
    },
    {
      id: 'result-summary',
      title: 'خلاصه نتیجه',
      description: 'خلاصه‌ای از نتیجه مناظره که AI تولید می‌کند.',
      type: 'section',
    },
    {
      id: 'result-rounds',
      title: 'راندهای مناظره',
      description: 'پاسخ هر مدل در هر راند. می‌توانید ببینید هر مدل چه گفته.',
      type: 'panel',
    },
    {
      id: 'result-judge',
      title: 'نتیجه داوری',
      description: 'نتیجه نهایی که داور AI اعلام می‌کند: برنده و دلیل.',
      type: 'panel',
    },
    {
      id: 'recent-debates',
      title: 'مناظرات اخیر',
      description: 'لیست 5 مناظره اخیر. برای دیدن همه به آرشیو بروید.',
      type: 'section',
    },
    {
      id: 'page-background',
      title: 'صفحه مناظره',
      description: 'این صفحه برای مناظره بین مدل‌های AI است. سوال بپرسید و نتیجه را ببینید.',
      type: 'area',
    },
  ],
  diagram: `graph TB
    subgraph DebatePage["🎭 صفحه مناظره"]
        ModelsStatus["وضعیت مدل‌ها"]
        Form["فرم مناظره"]
        Results["نتایج"]
        History["تاریخچه"]
    end

    subgraph FormSection["📝 فرم"]
        ModeSelect["انتخاب حالت"]
        PromptInput["سوال"]
        StartBtn["شروع"]
    end

    subgraph ResultsSection["📊 نتایج"]
        Summary["خلاصه"]
        Rounds["راندها"]
        Judge["داوری"]
    end

    subgraph Modes["🎯 حالت‌ها"]
        Auto["خودکار"]
        Debate["مناظره"]
        Collab["همکاری"]
        Quick["سریع"]
    end

    Form --> ModeSelect
    Form --> PromptInput
    Form --> StartBtn

    ModeSelect --> Modes
    StartBtn --> Results

    Results --> Summary
    Results --> Rounds
    Results --> Judge`,
};

// ============================================
// صفحه مدل‌های AI
// ============================================
export const modelsHelp: PageHelp = {
  id: 'models',
  title: 'مدل‌های AI',
  description: 'مشاهده و مدیریت مدل‌های هوش مصنوعی',
  path: '/models',
  overview: `در این صفحه تمام مدل‌های AI پشتیبانی شده را می‌بینید. می‌توانید آن‌ها را فعال/غیرفعال کنید، تنظیمات را تغییر دهید و توانایی‌شان را تست کنید.`,
  features: [
    'مشاهده تمام مدل‌ها با جزئیات',
    'فعال/غیرفعال کردن مدل‌ها',
    'تنظیم اولویت و محدودیت‌ها',
    'تست توانایی هر مدل',
    'فیلتر بر اساس provider',
  ],
  elements: [
    {
      id: 'view-toggle',
      title: 'تغییر حالت نمایش',
      description: 'بین حالت "مشاهده" و "مدیریت" جابجا شوید.',
      type: 'button',
      tips: ['مشاهده: فقط دیدن اطلاعات', 'مدیریت: تغییر تنظیمات'],
    },
    {
      id: 'provider-cards',
      title: 'کارت‌های Provider',
      description: 'آمار هر provider: تعداد مدل‌ها و وضعیت API. کلیک = فیلتر.',
      type: 'section',
      tips: ['تیک سبز = API فعال', 'ضربدر = API غیرفعال یا کلید ندارد'],
    },
    {
      id: 'filter-all',
      title: 'فیلتر همه',
      description: 'نمایش تمام مدل‌ها',
      type: 'button',
    },
    {
      id: 'filter-available',
      title: 'فیلتر فعال',
      description: 'فقط مدل‌هایی که فعال هستند',
      type: 'button',
    },
    {
      id: 'model-card',
      title: 'کارت مدل',
      description: 'اطلاعات یک مدل: نام، provider، context، هزینه، قابلیت‌ها',
      type: 'section',
    },
    {
      id: 'model-context',
      title: 'Context Window',
      description: 'حداکثر طول متن ورودی (به هزار توکن)',
      type: 'section',
    },
    {
      id: 'model-cost',
      title: 'هزینه',
      description: 'هزینه به ازای هر 1000 توکن (دلار)',
      type: 'section',
    },
    {
      id: 'model-capabilities',
      title: 'قابلیت‌ها',
      description: 'لیست قابلیت‌های مدل: chat, code, analysis, ...',
      type: 'section',
    },
    {
      id: 'model-features',
      title: 'ویژگی‌ها',
      description: 'ویژگی‌های خاص: پشتیبانی تصویر، تولید تصویر، وضعیت فعال/غیرفعال',
      type: 'section',
    },
    {
      id: 'btn-test',
      title: 'تست توانایی',
      description: 'اجرای تست‌های مختلف روی مدل و دریافت نمره و نشان.',
      type: 'button',
      tips: ['تست چند دقیقه طول می‌کشد', 'نتایج ذخیره می‌شود'],
    },
    {
      id: 'manage-table',
      title: 'جدول مدیریت',
      description: 'جدول تنظیمات مدل‌ها: وضعیت، اولویت، کارهای مجاز، ترجیحات',
      type: 'panel',
    },
    {
      id: 'toggle-enabled',
      title: 'فعال/غیرفعال',
      description: 'سوئیچ فعال/غیرفعال کردن مدل. غیرفعال = استفاده نمی‌شود.',
      type: 'checkbox',
    },
    {
      id: 'priority-input',
      title: 'اولویت',
      description: 'اولویت مدل از 1 تا 10. عدد کمتر = اولویت بالاتر.',
      type: 'input',
    },
    {
      id: 'allowed-tasks',
      title: 'کارهای مجاز',
      description: 'انواع کارهایی که این مدل می‌تواند انجام دهد.',
      type: 'checkbox',
    },
    {
      id: 'preferred-for',
      title: 'ترجیحی برای',
      description: 'کارهایی که این مدل برای آن‌ها ترجیح داده می‌شود.',
      type: 'checkbox',
    },
    {
      id: 'btn-save',
      title: 'ذخیره',
      description: 'ذخیره تغییرات تنظیمات',
      type: 'button',
    },
    {
      id: 'btn-reset',
      title: 'بازنشانی',
      description: 'برگرداندن تنظیمات به حالت پیش‌فرض',
      type: 'button',
    },
    {
      id: 'bulk-enable',
      title: 'فعال کردن همه',
      description: 'فعال کردن تمام مدل‌ها یکجا',
      type: 'button',
    },
    {
      id: 'bulk-disable',
      title: 'غیرفعال کردن همه',
      description: 'غیرفعال کردن تمام مدل‌ها یکجا',
      type: 'button',
    },
    {
      id: 'test-results',
      title: 'نتایج تست',
      description: 'پنل نمایش نتایج تست توانایی: نمره، نشان‌ها، نقاط قوت و ضعف',
      type: 'panel',
    },
    {
      id: 'page-background',
      title: 'صفحه مدل‌ها',
      description: 'این صفحه برای مشاهده و مدیریت مدل‌های AI است. از تب‌های بالا حالت را عوض کنید.',
      type: 'area',
    },
  ],
  diagram: `graph TB
    subgraph ModelsPage["🤖 صفحه مدل‌ها"]
        Header["هدر + تغییر حالت"]
        Providers["آمار Providers"]
        Filters["فیلترها"]
        Content["محتوا"]
    end

    subgraph ViewMode["👁️ حالت مشاهده"]
        ModelCards["کارت‌های مدل"]
        TestBtn["دکمه تست"]
    end

    subgraph ManageMode["⚙️ حالت مدیریت"]
        Table["جدول تنظیمات"]
        BulkActions["عملیات گروهی"]
    end

    subgraph ModelCard["📋 کارت مدل"]
        Name["نام + Provider"]
        Stats["Context + Cost"]
        Caps["قابلیت‌ها"]
        Features["ویژگی‌ها"]
    end

    subgraph TableRow["📊 ردیف جدول"]
        Toggle["فعال/غیرفعال"]
        Priority["اولویت"]
        Tasks["کارهای مجاز"]
        Preferred["ترجیحات"]
    end

    Header --> ViewMode
    Header --> ManageMode

    ViewMode --> ModelCards
    ModelCards --> ModelCard

    ManageMode --> Table
    Table --> TableRow
    ManageMode --> BulkActions`,
};

// ============================================
// صفحه تنظیمات
// ============================================
export const settingsHelp: PageHelp = {
  id: 'settings',
  title: 'تنظیمات',
  description: 'تنظیمات کلی سیستم',
  path: '/settings',
  overview: `صفحه تنظیمات شامل تمام پیکربندی‌های سیستم است: کلیدهای API، توکن‌های Deploy، محدودیت‌ها و لاگ‌ها.`,
  features: [
    'مدیریت کلیدهای API',
    'ذخیره توکن‌های Deploy (GitHub, Render)',
    'تنظیم محدودیت‌های درخواست',
    'مشاهده لاگ‌های سیستم',
  ],
  elements: [
    {
      id: 'tab-api-keys',
      title: 'تب کلیدهای API',
      description: 'وارد کردن کلیدهای API برای providers مختلف: OpenAI, Claude, Gemini, ...',
      type: 'tab',
      tips: ['کلیدها رمزنگاری می‌شوند', 'بدون کلید، مدل کار نمی‌کند'],
    },
    {
      id: 'tab-deploy-keys',
      title: 'تب کلیدهای Deploy',
      description: 'توکن‌های GitHub و Render برای deploy و import',
      type: 'tab',
    },
    {
      id: 'tab-config',
      title: 'تب تنظیمات',
      description: 'تنظیمات عمومی سیستم',
      type: 'tab',
    },
    {
      id: 'tab-limits',
      title: 'تب محدودیت‌ها',
      description: 'محدودیت‌های روزانه و ماهانه درخواست‌ها',
      type: 'tab',
    },
    {
      id: 'tab-logs',
      title: 'تب لاگ‌ها',
      description: 'مشاهده لاگ‌های سیستم و خطاها',
      type: 'tab',
    },
    {
      id: 'input-openai-key',
      title: 'کلید OpenAI',
      description: 'کلید API از platform.openai.com',
      type: 'input',
      tips: ['با sk- شروع می‌شود', 'برای GPT-4, GPT-3.5 و DALL-E'],
    },
    {
      id: 'input-claude-key',
      title: 'کلید Claude',
      description: 'کلید API از console.anthropic.com',
      type: 'input',
      tips: ['با sk-ant- شروع می‌شود', 'برای Claude 3 و Claude 2'],
    },
    {
      id: 'input-gemini-key',
      title: 'کلید Gemini',
      description: 'کلید API از Google AI Studio',
      type: 'input',
    },
    {
      id: 'input-deepseek-key',
      title: 'کلید DeepSeek',
      description: 'کلید API از platform.deepseek.com',
      type: 'input',
    },
    {
      id: 'input-github-token',
      title: 'توکن GitHub',
      description: 'Personal Access Token برای import و deploy',
      type: 'input',
      tips: ['از Settings > Developer settings بسازید', 'scope: repo, read:org'],
    },
    {
      id: 'input-render-key',
      title: 'کلید Render',
      description: 'API Key برای deploy در Render.com',
      type: 'input',
    },
    {
      id: 'btn-save-keys',
      title: 'ذخیره',
      description: 'ذخیره کلیدها. کلیدها رمزنگاری می‌شوند.',
      type: 'button',
    },
    {
      id: 'btn-test-key',
      title: 'تست اتصال',
      description: 'تست اینکه کلید معتبر است و API کار می‌کند.',
      type: 'button',
    },
    {
      id: 'page-background',
      title: 'صفحه تنظیمات',
      description: 'این صفحه برای تنظیمات سیستم است. کلیدهای API را وارد کنید تا مدل‌ها کار کنند.',
      type: 'area',
    },
  ],
  diagram: `graph TB
    subgraph SettingsPage["⚙️ صفحه تنظیمات"]
        Tabs["تب‌ها"]
    end

    subgraph TabsContent["📑 محتوای تب‌ها"]
        APIKeys["کلیدهای API"]
        DeployKeys["کلیدهای Deploy"]
        Config["تنظیمات"]
        Limits["محدودیت‌ها"]
        Logs["لاگ‌ها"]
    end

    subgraph APIKeysTab["🔑 کلیدهای API"]
        OpenAI["OpenAI"]
        Claude["Claude"]
        Gemini["Gemini"]
        DeepSeek["DeepSeek"]
        Perplexity["Perplexity"]
        Groq["Groq"]
    end

    subgraph DeployKeysTab["🚀 کلیدهای Deploy"]
        GitHub["GitHub Token"]
        Render["Render Key"]
    end

    Tabs --> APIKeys
    Tabs --> DeployKeys
    Tabs --> Config
    Tabs --> Limits
    Tabs --> Logs

    APIKeys --> OpenAI
    APIKeys --> Claude
    APIKeys --> Gemini
    APIKeys --> DeepSeek

    DeployKeys --> GitHub
    DeployKeys --> Render`,
};

// ============================================
// صفحه موتور خالق
// ============================================
export const creatorHelp: PageHelp = {
  id: 'creator',
  title: 'موتور خالق',
  description: 'ساخت پروژه جدید با کمک هوش مصنوعی',
  path: '/creator',
  overview: `موتور خالق یک ابزار قدرتمند برای ساخت پروژه با AI است. فقط توضیح دهید چه می‌خواهید و AI پروژه را می‌سازد.`,
  features: [
    'ساخت پروژه با توضیحات متنی',
    'انتخاب نوع پروژه',
    'استفاده از مدل‌های مختلف',
    'پیگیری پیشرفت در لحظه',
  ],
  elements: [
    {
      id: 'input-description',
      title: 'توضیحات پروژه',
      description: 'توضیح دهید چه پروژه‌ای می‌خواهید. هر چه دقیق‌تر، نتیجه بهتر.',
      type: 'input',
      tips: [
        'نوع برنامه را مشخص کنید',
        'فیچرهای مورد نظر را لیست کنید',
        'تکنولوژی‌های ترجیحی را بگویید',
      ],
    },
    {
      id: 'select-type',
      title: 'نوع پروژه',
      description: 'انتخاب نوع پروژه: Web App, API, Mobile, Desktop',
      type: 'select',
    },
    {
      id: 'select-model',
      title: 'انتخاب مدل',
      description: 'مدل AI که پروژه را می‌سازد. مدل‌های قوی‌تر = نتیجه بهتر ولی کندتر.',
      type: 'select',
    },
    {
      id: 'btn-create',
      title: 'شروع ساخت',
      description: 'شروع فرآیند ساخت پروژه. ممکن است چند دقیقه طول بکشد.',
      type: 'button',
    },
    {
      id: 'progress-bar',
      title: 'نوار پیشرفت',
      description: 'نمایش پیشرفت ساخت پروژه به درصد',
      type: 'section',
    },
    {
      id: 'progress-log',
      title: 'لاگ پیشرفت',
      description: 'جزئیات مراحل ساخت: تحلیل، طراحی، کدنویسی، ...',
      type: 'panel',
    },
    {
      id: 'page-background',
      title: 'صفحه موتور خالق',
      description: 'این صفحه برای ساخت پروژه جدید با AI است. توضیح دهید و AI می‌سازد.',
      type: 'area',
    },
  ],
  diagram: `graph TB
    subgraph CreatorPage["🚀 موتور خالق"]
        Form["فرم ورودی"]
        Progress["پیشرفت"]
        Result["نتیجه"]
    end

    subgraph FormSection["📝 فرم"]
        Desc["توضیحات"]
        Type["نوع پروژه"]
        Model["انتخاب مدل"]
        Create["شروع ساخت"]
    end

    subgraph ProgressSection["⏳ پیشرفت"]
        Bar["نوار پیشرفت"]
        Log["لاگ مراحل"]
    end

    subgraph Stages["📊 مراحل"]
        Analysis["تحلیل"]
        Design["طراحی"]
        Code["کدنویسی"]
        Test["تست"]
    end

    Form --> Desc
    Form --> Type
    Form --> Model
    Form --> Create

    Create --> Progress
    Progress --> Bar
    Progress --> Log

    Log --> Analysis
    Analysis --> Design
    Design --> Code
    Code --> Test
    Test --> Result`,
};

// ============================================
// لیست کل صفحات
// ============================================
export const allPagesHelp: PageHelp[] = [
  dashboardHelp,
  projectsHelp,
  projectDetailHelp,
  debateHelp,
  modelsHelp,
  settingsHelp,
  creatorHelp,
];

// ============================================
// دریافت راهنمای صفحه بر اساس path
// ============================================
export function getPageHelp(path: string): PageHelp | undefined {
  // حذف query string و normalize کردن path
  const normalizedPath = path.split('?')[0].replace(/\/$/, '') || '/';

  // بررسی exact match
  const exactMatch = allPagesHelp.find(p => p.path === normalizedPath);
  if (exactMatch) return exactMatch;

  // بررسی dynamic routes
  if (normalizedPath.startsWith('/projects/') && normalizedPath !== '/projects') {
    return projectDetailHelp;
  }

  return undefined;
}

// ============================================
// دریافت راهنمای المان بر اساس ID
// ============================================
export function getElementHelp(pageId: string, elementId: string): ElementHelp | undefined {
  const page = allPagesHelp.find(p => p.id === pageId);
  if (!page) return undefined;
  return page.elements.find(e => e.id === elementId);
}
