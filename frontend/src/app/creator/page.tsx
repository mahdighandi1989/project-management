'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import TaskFilePicker, { type UploadSessionState } from '@/components/TaskFilePicker';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const PROJECT_TYPES = [
  { id: 'python', name: 'Python', icon: '🐍', desc: 'اسکریپت یا CLI' },
  { id: 'fastapi', name: 'FastAPI', icon: '⚡', desc: 'API سرور' },
  { id: 'nextjs', name: 'Next.js', icon: '▲', desc: 'وب اپلیکیشن' },
  { id: 'react', name: 'React', icon: '⚛️', desc: 'فرانت‌اند' },
  { id: 'flask', name: 'Flask', icon: '🌶️', desc: 'وب ساده' },
  { id: 'node', name: 'Node.js', icon: '🟢', desc: 'بک‌اند JS' },
];

const PROJECT_TEMPLATES: Record<string, { description: string; technologies: string }> = {
  python: {
    description: 'یک ابزار خط فرمان ساده برای پردازش فایل‌های CSV و تولید گزارش متنی.',
    technologies: 'pandas, click',
  },
  fastapi: {
    description: 'یک API برای مدیریت کاربران شامل ثبت‌نام، ورود با JWT و CRUD کامل.',
    technologies: 'PostgreSQL, JWT, SQLAlchemy',
  },
  nextjs: {
    description: 'یک وب‌اپ بلاگ مدرن با احراز هویت، صفحات داینامیک و پنل ادمین.',
    technologies: 'TypeScript, Tailwind, Prisma',
  },
  react: {
    description: 'یک داشبورد مدیریت تسک با Drag & Drop و فیلترهای پیشرفته.',
    technologies: 'TypeScript, Tailwind, Zustand',
  },
  flask: {
    description: 'یک وب‌اپ ساده برای مدیریت لیست کارها با احراز هویت.',
    technologies: 'SQLite, Jinja2',
  },
  node: {
    description: 'یک سرور Express برای آپلود فایل و تولید thumbnail تصاویر.',
    technologies: 'Express, Multer, Sharp',
  },
};

interface AIModel {
  id: string;
  name: string;
  provider: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  project_type: string;
  status: string;
  files: any[];
  created_at?: string;
}

export default function CreatorPage() {
  const router = useRouter();

  const [aiReady, setAiReady] = useState(false);
  const [githubReady, setGithubReady] = useState(false);
  const [models, setModels] = useState<AIModel[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [projectType, setProjectType] = useState('fastapi');
  const [autoDetectType, setAutoDetectType] = useState(false);
  const [technologies, setTechnologies] = useState('');

  // 🆕 (Creator file upload) — wireing TaskFilePicker روی creator page
  // تا کاربر بتواند فایل‌های صوت/PDF/تصویر/ویدئو/کد آپلود کند و backend
  // محتوای آن‌ها را با AI extraction به idea ضمیمه کند (همان مسیری که
  // در /oversight موجود است).
  const [creatorDraftId] = useState(
    `creator-draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  );
  const [uploadedSessions, setUploadedSessions] = useState<UploadSessionState[]>([]);
  // برای vision toggle: اگر backend با 409 blocked_no_vision_model برگشت،
  // اطلاعات candidate ها را اینجا نگه می‌داریم تا UI toggle نمایش دهد
  const [visionBlock, setVisionBlock] = useState<{
    mime_type?: string;
    missing_files?: Array<{filename: string; mime_type: string}>;
    candidates?: Array<{id: string; name?: string; provider?: string}>;
  } | null>(null);
  const [tempActivatedModel, setTempActivatedModel] = useState<string | null>(null);

  // 🆕 انتخاب مدل‌ها (multi-select)
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);

  const [creating, setCreating] = useState(false);
  const [progress, setProgress] = useState('');
  const [progressPct, setProgressPct] = useState(0);

  const [detecting, setDetecting] = useState(false);

  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 🆕 GitHub push modal
  const [pushTarget, setPushTarget] = useState<Project | null>(null);

  // 🆕 (creator UX) — checkbox برای auto-push به GitHub در زمان ساخت پروژه
  // به‌جای ساخت محلی و سپس کلیک دستی روی push. اگر githubReady=true
  // (توکن GitHub تنظیم شده) و این فعال، پس از success ساخت پروژه، خودکار
  // push انجام می‌شود.
  const [autoPushToGitHub, setAutoPushToGitHub] = useState<boolean>(false);
  const [pushRepoName, setPushRepoName] = useState('');
  const [pushDescription, setPushDescription] = useState('');
  const [pushPrivate, setPushPrivate] = useState(true);
  const [pushing, setPushing] = useState(false);

  useEffect(() => {
    checkStatus();
    loadProjects();

    // بازیابی انتخاب مدل
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('creator_selected_models');
        if (saved) {
          const arr = JSON.parse(saved);
          if (Array.isArray(arr)) setSelectedModelIds(arr);
        }
      } catch {}
    }
  }, []);

  const persistModelChoice = (ids: string[]) => {
    setSelectedModelIds(ids);
    try {
      localStorage.setItem('creator_selected_models', JSON.stringify(ids));
    } catch {}
  };

  const toggleModel = (id: string) => {
    if (selectedModelIds.includes(id)) {
      persistModelChoice(selectedModelIds.filter((x) => x !== id));
    } else {
      persistModelChoice([...selectedModelIds, id]);
    }
  };

  // شبیه‌سازی پیشرفت تدریجی هنگام تولید
  useEffect(() => {
    if (!creating) {
      setProgressPct(0);
      return;
    }
    const interval = setInterval(() => {
      setProgressPct((p) => (p < 90 ? p + 1.5 : p));
    }, 400);
    return () => clearInterval(interval);
  }, [creating]);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 5000);
  };

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simple/status`);
      if (res.ok) {
        const data = await res.json();
        setAiReady(data.ai_ready);
        setGithubReady(!!data.github_ready);
        setModels(data.models || []);
      }
    } catch (e) {
      console.error('Error checking status:', e);
    } finally {
      setLoading(false);
    }
  };

  // تشخیص خودکار نوع پروژه
  const detectType = async () => {
    if (description.trim().length < 10) {
      showError('برای تشخیص خودکار، حداقل ۱۰ کاراکتر توضیحات بنویسید');
      return;
    }
    setDetecting(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/detect-type`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          name,
          model_id: selectedModelIds[0] || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.primary_type) {
          setProjectType(data.primary_type);
        }
        if (Array.isArray(data.technologies) && data.technologies.length > 0) {
          // ترکیب با موارد فعلی
          const existing = technologies
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean);
          const combined = [...existing];
          for (const t of data.technologies) {
            if (t && !combined.includes(t)) combined.push(t);
          }
          setTechnologies(combined.join(', '));
        }
        showSuccess(
          `AI پیشنهاد می‌دهد: ${data.primary_type}` +
            (data.alternative_types?.length ? ` (یا ${data.alternative_types.join(', ')})` : ''),
        );
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'تشخیص خودکار ناموفق بود');
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setDetecting(false);
    }
  };

  // push به GitHub
  const openPushModal = (p: Project) => {
    setPushTarget(p);
    setPushRepoName(p.name.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''));
    setPushDescription(p.description || '');
    setPushPrivate(true);
  };

  const submitPush = async () => {
    if (!pushTarget) return;
    setPushing(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${pushTarget.id}/push-to-github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_name: pushRepoName,
          description: pushDescription,
          private: pushPrivate,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.repo_url) {
          showSuccess(`${data.uploaded} فایل به GitHub push شد`);
          window.open(data.repo_url, '_blank');
          setPushTarget(null);
        } else if (data.repo_url) {
          showError(`Push با ${data.failed?.length || 0} خطا انجام شد. repo: ${data.repo_url}`);
        } else {
          showError(data.message || 'Push ناموفق');
        }
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در push به GitHub');
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setPushing(false);
    }
  };

  const loadProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch (e) {
      console.error('Error loading projects:', e);
    }
  };

  const useTemplate = () => {
    const tmpl = PROJECT_TEMPLATES[projectType];
    if (tmpl) {
      setDescription(tmpl.description);
      setTechnologies(tmpl.technologies);
    }
  };

  // 🆕 preview state
  const [structuredPrompt, setStructuredPrompt] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string>('');
  const [editablePromptText, setEditablePromptText] = useState<string>('');

  // 🆕 مرحلهٔ ۱: idea → strong prompt (preview)
  const previewPromptFromIdea = async () => {
    setPreviewError('');
    if (!name.trim()) {
      showError('نام پروژه را وارد کنید');
      return;
    }
    if (description.trim().length < 15) {
      showError('ایده/توضیح حداقل ۱۵ کاراکتر');
      return;
    }
    if (!aiReady) {
      showError('ابتدا از تنظیمات کلید API را وارد کنید');
      return;
    }
    // 🆕 enforce model selection
    if (selectedModelIds.length === 0) {
      showError('حداقل یک مدل AI انتخاب کنید — بدون مدل امکان تولید پرامپت نیست');
      return;
    }

    setPreviewLoading(true);
    try {
      // 🆕 (Creator file upload) — session_id های آپلود‌شده‌ای که در وضعیت
      // قابل‌استفاده هستند را به request بفرست تا backend extraction انجام دهد.
      const validSessionIds = uploadedSessions
        .filter((s) => ['completed', 'extracting', 'extracted'].includes(s.status))
        .sort((a, b) => a.file_order - b.file_order)
        .map((s) => s.session_id);
      const res = await fetch(`${API_BASE}/api/simple/projects/idea-to-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea: description.trim() || '[ایدهٔ متنی همراه نیست — درخواست داخل فایل‌های پیوست]',
          name: name.trim(),
          project_type: autoDetectType ? 'auto' : projectType,
          technologies: technologies.split(',').map((t) => t.trim()).filter(Boolean),
          model_ids: selectedModelIds,
          upload_session_ids: validSessionIds.length ? validSessionIds : undefined,
        }),
      });
      const data = await res.json();
      // 🆕 (Creator vision toggle) — اگر backend 409 با blocked_no_vision_model
      // برگشت داد، toggle UI نمایش بده تا کاربر مدل vision را موقتاً فعال کند.
      if (res.status === 409 && data?.detail && typeof data.detail === 'object') {
        const blocked = data.detail;
        if (blocked.error === 'blocked_no_vision_model' || blocked.missing_files) {
          setVisionBlock({
            mime_type: blocked.mime_type,
            missing_files: blocked.missing_files || [],
            candidates: blocked.candidates || [],
          });
          setPreviewError(
            'مدل بصری برای استخراج فایل پیوست لازم است. لطفاً یکی از مدل‌های زیر را فعال کنید.',
          );
          return;
        }
      }
      if (!res.ok || !data.success) {
        setPreviewError(
          typeof data.detail === 'string' ? data.detail :
          JSON.stringify(data.detail || data.error || 'خطا در تولید پرامپت')
        );
        return;
      }
      setStructuredPrompt(data);
      setEditablePromptText(data.full_prompt_text || '');
    } catch (e: any) {
      setPreviewError(e.message || 'خطا در ارتباط با سرور');
    } finally {
      setPreviewLoading(false);
    }
  };

  // 🆕 بازتولید با مدل بعدی (rotation در selectedModelIds)
  const regenerateWithNextModel = async () => {
    if (selectedModelIds.length < 1) return;
    // rotate
    const rotated = [...selectedModelIds.slice(1), selectedModelIds[0]];
    setSelectedModelIds(rotated);
    await previewPromptFromIdea();
  };

  // مرحلهٔ ۲: confirm → ساخت پروژه با structured_prompt
  const createProject = async () => {
    if (!name.trim()) {
      showError('نام پروژه را وارد کنید');
      return;
    }
    // 🆕 اگر structured_prompt موجود نیست، اول preview بساز
    if (!structuredPrompt) {
      await previewPromptFromIdea();
      return;
    }
    if (selectedModelIds.length === 0) {
      showError('حداقل یک مدل AI انتخاب کنید');
      return;
    }
    if (!aiReady) {
      showError('ابتدا از تنظیمات کلید API را وارد کنید');
      return;
    }

    setCreating(true);
    setProgress('در حال ساخت فایل‌ها با AI (1-3 دقیقه)...');
    setProgressPct(10);

    try {
      // اگر کاربر متن پرامپت را ادیت کرده، در structured_prompt جایگزین می‌کنیم
      const finalStructured = {
        ...structuredPrompt,
        full_prompt_text: editablePromptText || structuredPrompt.full_prompt_text,
      };
      const res = await fetch(`${API_BASE}/api/simple/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          project_type: projectType,
          technologies: technologies.split(',').map((t) => t.trim()).filter(Boolean),
          model_ids: selectedModelIds,
          auto_detect_type: autoDetectType,
          structured_prompt: finalStructured,
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setProgressPct(100);
        setProgress('پروژه با موفقیت ساخته شد!');
        showSuccess(data.message || 'پروژه ساخته شد!');

        // 🆕 (auto-push to GitHub) — اگر کاربر زمان ساخت تیک «push خودکار»
        // را زده بود و GitHub token تنظیم شده، خودکار repo بساز و push کن.
        // در غیر این صورت پروژه فقط محلی است و کاربر می‌تواند بعداً
        // دکمهٔ Push را روی کارت پروژه بزند.
        const createdProjectId = data.project?.id;
        if (autoPushToGitHub && githubReady && createdProjectId) {
          setProgress('در حال push خودکار به GitHub...');
          try {
            const pushRes = await fetch(
              `${API_BASE}/api/simple/projects/${createdProjectId}/push-to-github`,
              {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  repo_name: name.trim(),
                  description: description.trim().slice(0, 250),
                  private: true,
                }),
              },
            );
            const pushData = await pushRes.json().catch(() => ({}));
            if (pushRes.ok && pushData.success) {
              showSuccess(
                `🚀 ${pushData.uploaded || 0} فایل به GitHub push شد: ${pushData.repo_url || ''}`,
              );
              if (pushData.repo_url) {
                window.open(pushData.repo_url, '_blank');
              }
            } else {
              showError(
                `پروژه محلی ساخته شد ولی push خودکار ناموفق: ${pushData.detail || pushData.message || 'unknown'}. ` +
                `می‌توانید از کارت پروژه دستی push کنید.`,
              );
            }
          } catch (pe: any) {
            showError(
              `پروژه محلی ساخته شد ولی push خودکار خطا داد: ${pe?.message || pe}. ` +
              `می‌توانید از کارت پروژه دستی push کنید.`,
            );
          }
        }

        setName('');
        setDescription('');
        setTechnologies('');
        setStructuredPrompt(null);
        setEditablePromptText('');
        loadProjects();
        setTimeout(() => {
          router.push(`/project/${data.project.id}`);
        }, 800);
      } else {
        // 🆕 error reporting پربار
        const errObj = data.detail || data;
        if (typeof errObj === 'object' && errObj.primary_error) {
          showError(
            `❌ ${errObj.primary_error}\n\nاقدامات: ${(errObj.suggested_actions || []).join(' | ')}`
          );
        } else {
          showError(typeof errObj === 'string' ? errObj : JSON.stringify(errObj));
        }
      }
    } catch (e: any) {
      showError(e.message || 'خطا در ارتباط با سرور');
    } finally {
      setCreating(false);
      setProgress('');
    }
  };

  const deleteProject = async (id: string, projectName: string) => {
    if (!confirm(`پروژه «${projectName}» حذف شود؟ این عمل قابل بازگشت نیست.`)) return;

    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('پروژه حذف شد');
        loadProjects();
      } else {
        showError('خطا در حذف');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const filteredProjects = useMemo(
    () =>
      projects.filter(
        (p) =>
          !search ||
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.description?.toLowerCase().includes(search.toLowerCase()),
      ),
    [projects, search],
  );

  const charsLeft = description.length;
  const descColor =
    charsLeft < 15 ? 'text-red-400' : charsLeft < 50 ? 'text-yellow-400' : 'text-green-400';

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white"
      dir="rtl"
    >
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-pulse max-w-md">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 max-w-md">
          {success}
        </div>
      )}

      <div className="max-w-6xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
              <span>🛠️</span>
              <span>موتور خالق</span>
            </h1>
            <p className="text-gray-400">با AI پروژه بساز - توضیح بده، کد کامل بگیر</p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/settings"
              className="px-4 py-2 bg-yellow-500/20 text-yellow-300 rounded-lg hover:bg-yellow-500/30 border border-yellow-500/50 transition"
            >
              ⚙️ تنظیمات
            </Link>
            <Link
              href="/"
              className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 transition"
            >
              🏠 خانه
            </Link>
          </div>
        </div>

        {/* وضعیت AI */}
        <div
          className={`mb-6 p-4 rounded-xl backdrop-blur ${
            aiReady
              ? 'bg-green-500/15 border border-green-500/40'
              : 'bg-red-500/15 border border-red-500/40'
          }`}
        >
          {loading ? (
            <p className="text-center text-gray-300">در حال بررسی وضعیت...</p>
          ) : aiReady ? (
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <span className="text-2xl">✅</span>
                <div>
                  <p className="font-medium text-green-300">AI آماده است!</p>
                  <p className="text-sm text-gray-400">
                    {models.length} مدل فعال:{' '}
                    {models
                      .slice(0, 3)
                      .map((m) => m.name)
                      .join('، ')}
                    {models.length > 3 ? ` و ${models.length - 3} مدل دیگر` : ''}
                  </p>
                </div>
              </div>
              <button
                onClick={checkStatus}
                className="text-sm text-blue-300 hover:underline"
              >
                🔄 بروزرسانی
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <span className="text-2xl">⚠️</span>
                <div>
                  <p className="font-medium text-red-300">AI فعال نیست!</p>
                  <p className="text-sm text-gray-400">
                    برای ساخت پروژه، حداقل یک کلید API در تنظیمات وارد کنید.
                  </p>
                </div>
              </div>
              <Link
                href="/settings"
                className="px-4 py-2 bg-yellow-500 text-black rounded-lg font-medium hover:bg-yellow-400"
              >
                تنظیم کلید
              </Link>
            </div>
          )}
        </div>

        {/* انتخاب مدل‌ها */}
        {models.length > 0 && (
          <div className="mb-6 p-4 bg-white/10 backdrop-blur rounded-2xl border border-white/10">
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <h3 className="font-bold flex items-center gap-2">
                🤖 مدل‌های مورد استفاده
              </h3>
              <div className="flex gap-1 text-xs">
                <button
                  type="button"
                  onClick={() => persistModelChoice(models.map((m) => m.id))}
                  className="px-2 py-0.5 bg-blue-500/30 text-blue-200 rounded hover:bg-blue-500/40"
                >
                  انتخاب همه
                </button>
                <button
                  type="button"
                  onClick={() => persistModelChoice([])}
                  className="px-2 py-0.5 bg-white/10 rounded hover:bg-white/20"
                >
                  لغو همه
                </button>
              </div>
            </div>
            <p className="text-xs text-gray-400 mb-2">
              {selectedModelIds.length === 0
                ? 'اولین مدل موجود به‌طور خودکار استفاده می‌شود.'
                : `${selectedModelIds.length} مدل انتخاب شد - با ترتیب fallback (اگر یکی شکست خورد، بعدی امتحان می‌شود)`}
            </p>
            <div className="flex flex-wrap gap-2">
              {models.map((m) => {
                const checked = selectedModelIds.includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggleModel(m.id)}
                    className={`px-3 py-1.5 rounded-full text-xs border transition ${
                      checked
                        ? 'bg-green-500 text-white border-green-500'
                        : 'bg-white/5 border-white/20 hover:bg-white/10'
                    }`}
                  >
                    {checked ? '✓ ' : ''}
                    {m.name}
                    {m.provider ? <span className="opacity-70"> · {m.provider}</span> : null}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* فرم ساخت */}
          <div className="lg:col-span-2">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-6 border border-white/10">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">🆕 ساخت پروژه جدید</h2>
                <button
                  onClick={useTemplate}
                  type="button"
                  className="text-sm px-3 py-1 bg-purple-500/20 text-purple-300 rounded-lg border border-purple-500/40 hover:bg-purple-500/30"
                >
                  💡 استفاده از قالب نمونه
                </button>
              </div>

              {/* نام */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  نام پروژه <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="مثال: فروشگاه آنلاین"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={80}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none transition"
                />
              </div>

              {/* توضیحات */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium">
                    توضیحات پروژه <span className="text-red-400">*</span>
                  </label>
                  <span className={`text-xs ${descColor}`}>
                    {charsLeft} کاراکتر {charsLeft < 15 ? '(کم)' : ''}
                  </span>
                </div>
                <textarea
                  placeholder="چه می‌خواهید بسازید؟ ویژگی‌ها و قابلیت‌ها را دقیق توضیح دهید..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={6}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none resize-none transition"
                />
                <p className="text-xs text-gray-500 mt-1">
                  💡 هر چه دقیق‌تر بنویسید، خروجی AI بهتر می‌شود.
                </p>

                {/* 🆕 (Creator file upload) — بخش آپلود فایل‌های پیوست
                    (صوت، PDF، تصویر، ویدئو، کد). محتوای فایل‌ها با AI
                    extraction (همان مسیر oversight) به ایده ضمیمه می‌شود
                    قبل از تولید پرامپت. */}
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-2 text-blue-300">
                    📎 فایل‌های پیوست (اختیاری)
                  </label>
                  <p className="text-xs text-gray-400 mb-2">
                    می‌توانید فایل صوتی، PDF، تصویر، ویدئو یا کد آپلود کنید.
                    محتوای فایل‌ها خودکار با AI استخراج و به توضیحات اضافه می‌شود.
                    اگر فقط فایل می‌فرستید و متن نمی‌نویسید، AI درخواست شما را
                    از داخل فایل‌ها برداشت می‌کند.
                  </p>
                  <TaskFilePicker
                    taskDraftId={creatorDraftId}
                    apiBase={API_BASE}
                    onSessionsChange={setUploadedSessions}
                    disabled={previewLoading || creating}
                  />
                </div>

                {/* 🆕 (Creator vision toggle) — اگر backend با 409
                    blocked_no_vision_model برگشت داد، اینجا candidate مدل‌ها
                    را نمایش می‌دهیم و کاربر می‌تواند موقتاً یکی را فعال کند
                    و دوباره تلاش کند. */}
                {visionBlock && (visionBlock.candidates || []).length > 0 && (
                  <div className="mt-4 p-4 bg-amber-500/10 border border-amber-500/40 rounded-xl">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-2xl">🔓</span>
                      <div>
                        <h4 className="text-sm font-bold text-amber-200">
                          مدل بصری برای استخراج فایل پیوست لازم است
                        </h4>
                        <p className="text-xs text-amber-300/80 mt-1">
                          {visionBlock.mime_type ? (
                            <>نوع فایل: <code>{visionBlock.mime_type}</code></>
                          ) : (
                            <>فایل‌های پیوست به مدل multimodal نیاز دارند.</>
                          )}
                          {' '}یک مدل را موقتاً فعال کنید — پس از استخراج، خودکار به حالت قبل برمی‌گردد.
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-3">
                      {(visionBlock.candidates || []).slice(0, 4).map((c, i) => (
                        <button
                          key={c.id}
                          onClick={async () => {
                            try {
                              const r = await fetch(
                                `${API_BASE}/api/oversight/models/${encodeURIComponent(c.id)}/temp-activate?trigger=ui-creator-${creatorDraftId}`,
                                { method: 'POST' },
                              );
                              if (r.ok) {
                                setTempActivatedModel(c.id);
                                setVisionBlock(null);
                                setPreviewError('');
                                // alert ساده برای feedback؛ کاربر دوباره «تبدیل به پرامپت» می‌زند
                                alert(`✅ مدل ${c.name || c.id} موقتاً فعال شد. حالا «تبدیل به پرامپت» را دوباره بزنید.`);
                              } else {
                                const e = await r.json().catch(() => ({}));
                                alert(`خطا در فعال‌سازی: ${e?.detail || r.status}`);
                              }
                            } catch (e) {
                              alert(`خطای شبکه: ${e}`);
                            }
                          }}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                            i === 0
                              ? 'bg-amber-500 text-white hover:bg-amber-600'
                              : 'bg-amber-500/20 text-amber-200 hover:bg-amber-500/30 border border-amber-500/40'
                          }`}
                        >
                          {i === 0 && '⭐ '}🔓 {c.name || c.id}
                          {c.provider && <span className="opacity-70 mr-1">({c.provider})</span>}
                        </button>
                      ))}
                      <button
                        onClick={() => setVisionBlock(null)}
                        className="px-3 py-1.5 bg-gray-500/20 text-gray-300 rounded-lg text-xs hover:bg-gray-500/30"
                      >
                        ❌ لغو
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* نوع پروژه */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                  <label className="block text-sm font-medium">نوع پروژه</label>
                  <div className="flex gap-2 items-center">
                    <button
                      type="button"
                      onClick={detectType}
                      disabled={detecting || description.trim().length < 10 || !aiReady}
                      className="text-xs px-3 py-1 bg-cyan-500/20 text-cyan-300 rounded-lg border border-cyan-500/40 hover:bg-cyan-500/30 disabled:opacity-50"
                      title="AI از روی توضیحات شما بهترین نوع و تکنولوژی را پیشنهاد می‌دهد"
                    >
                      {detecting ? '⏳ تشخیص...' : '🪄 تشخیص خودکار'}
                    </button>
                    <label className="flex items-center gap-1 text-xs text-gray-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoDetectType}
                        onChange={(e) => setAutoDetectType(e.target.checked)}
                        className="w-3.5 h-3.5"
                      />
                      <span title="هنگام ساخت پروژه، AI خودش نوع و تکنولوژی‌ها را تشخیص می‌دهد">
                        خودکار هنگام ساخت
                      </span>
                    </label>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {PROJECT_TYPES.map((type) => (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => setProjectType(type.id)}
                      className={`p-4 rounded-xl border text-center transition-all ${
                        projectType === type.id
                          ? 'bg-blue-500/30 border-blue-400 shadow-lg shadow-blue-500/20'
                          : 'bg-white/5 border-white/20 hover:bg-white/10'
                      }`}
                    >
                      <div className="text-2xl mb-1">{type.icon}</div>
                      <div className="font-medium">{type.name}</div>
                      <div className="text-xs text-gray-400">{type.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* تکنولوژی‌ها */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">
                  تکنولوژی‌های اضافی <span className="text-gray-400 text-xs">(اختیاری)</span>
                </label>
                <input
                  type="text"
                  placeholder="با کاما جدا کنید... مثال: PostgreSQL, Redis, JWT"
                  value={technologies}
                  onChange={(e) => setTechnologies(e.target.value)}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none transition"
                />
              </div>

              {/* نوار پیشرفت */}
              {creating && (
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-blue-300">{progress}</span>
                    <span className="text-gray-400">{Math.round(progressPct)}%</span>
                  </div>
                  <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    این کار ممکن است یک تا چند دقیقه طول بکشد. لطفاً صبور باشید.
                  </p>
                </div>
              )}

              {/* 🆕 enforcement: warning اگر مدل انتخاب نشده */}
              {selectedModelIds.length === 0 && (
                <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-200">
                  ⚠️ <b>حداقل یک مدل AI انتخاب کنید</b> — تا قبل از انتخاب، تولید پرامپت/پروژه ممکن نیست.
                  مدل اول fallback اولیه و بقیه به ترتیب اولویت استفاده می‌شوند.
                </div>
              )}

              {/* 🆕 دکمهٔ مرحلهٔ ۱: تولید پرامپت قوی (preview) */}
              {!structuredPrompt && (
                <button
                  onClick={previewPromptFromIdea}
                  disabled={previewLoading || !aiReady || selectedModelIds.length === 0 || !name.trim() || description.trim().length < 15}
                  title={
                    selectedModelIds.length === 0 ? 'حداقل یک مدل انتخاب کنید' :
                    !name.trim() ? 'نام پروژه را وارد کنید' :
                    description.trim().length < 15 ? 'ایده حداقل ۱۵ کاراکتر' :
                    ''
                  }
                  className="w-full py-4 bg-gradient-to-r from-fuchsia-500 to-purple-500 text-white rounded-xl font-bold text-lg hover:from-fuchsia-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {previewLoading ? '⏳ در حال تولید پرامپت قوی...' : '🪄 تولید پرامپت قوی (مرحلهٔ ۱)'}
                </button>
              )}

              {/* 🆕 preview prompt + dکمهٔ ساخت پروژه (مرحلهٔ ۲) */}
              {structuredPrompt && (
                <div className="space-y-3 p-4 bg-purple-50 dark:bg-purple-900/20 border-2 border-purple-300 dark:border-purple-700 rounded-xl">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h3 className="font-bold text-lg dark:text-purple-200">
                      🪄 پرامپت قوی تولید شد
                    </h3>
                    <span className="text-xs text-purple-700 dark:text-purple-300">
                      🤖 با مدل: <code>{structuredPrompt.model_used}</code>
                    </span>
                  </div>

                  {(structuredPrompt.warnings || []).length > 0 && (
                    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-300 rounded p-2 text-xs">
                      <b className="dark:text-amber-200">⚠️ هشدارهای AI:</b>
                      <ul className="list-disc list-inside text-amber-700 dark:text-amber-300 mt-1">
                        {structuredPrompt.warnings.map((w: string, i: number) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    {/* 🐛 (UI fix) — قبلاً label و textarea فقط dark-mode رنگ داشتند
                        و در light-mode سفید روی سفید نمایش داده می‌شدند. الان
                        رنگ‌های صریح برای هر دو حالت ست شده. */}
                    <label className="block text-sm font-medium mb-1 text-purple-800 dark:text-purple-200">
                      📋 متن پرامپت (می‌توانید ویرایش کنید):
                    </label>
                    <textarea
                      value={editablePromptText}
                      onChange={e => setEditablePromptText(e.target.value)}
                      rows={12}
                      className="w-full p-3 border rounded-lg bg-white text-gray-900 border-gray-300 dark:bg-gray-900 dark:text-white dark:border-gray-700 text-xs font-mono"
                    />
                  </div>

                  {/* 🆕 (creator UX) — checkbox برای push خودکار به GitHub
                      هنگام ساخت. اگر تیک خاموش، فقط محلی ساخته می‌شود
                      (کاربر می‌تواند بعداً از کارت پروژه دستی push کند). */}
                  <label
                    className={`flex items-start gap-2 p-3 rounded-lg border ${
                      githubReady
                        ? 'border-emerald-400/40 bg-emerald-50/60 dark:bg-emerald-900/20 cursor-pointer'
                        : 'border-amber-400/40 bg-amber-50/60 dark:bg-amber-900/20 opacity-70 cursor-not-allowed'
                    }`}
                    title={githubReady ? '' : 'برای فعال‌سازی، توکن GitHub را در /settings تنظیم کنید'}
                  >
                    <input
                      type="checkbox"
                      checked={autoPushToGitHub && githubReady}
                      disabled={!githubReady || creating}
                      onChange={(e) => setAutoPushToGitHub(e.target.checked)}
                      className="mt-0.5 w-4 h-4 accent-emerald-500"
                    />
                    <div className="flex-1 text-xs">
                      <div className="font-medium text-emerald-800 dark:text-emerald-200">
                        🚀 پس از ساخت، خودکار به GitHub push کن
                      </div>
                      {githubReady ? (
                        <p className="text-emerald-700 dark:text-emerald-300 mt-1">
                          repo خصوصی با نام پروژه ساخته می‌شود و همه فایل‌ها push می‌شوند.
                          اگر خاموش، پروژه فقط محلی است و بعداً می‌توانید دستی push کنید.
                        </p>
                      ) : (
                        <p className="text-amber-700 dark:text-amber-300 mt-1">
                          ⚠️ توکن GitHub در /settings تنظیم نشده — این گزینه فعلاً غیرفعال است.
                        </p>
                      )}
                    </div>
                  </label>

                  <div className="flex gap-2 flex-wrap mt-2">
                    <button
                      onClick={createProject}
                      disabled={creating}
                      className="flex-1 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-bold hover:from-blue-600 hover:to-purple-600 disabled:opacity-50"
                    >
                      {creating
                        ? '⏳ در حال ساخت...'
                        : (autoPushToGitHub && githubReady
                          ? '✅ ساخت و push به GitHub'
                          : '✅ تأیید و ساخت پروژه')}
                    </button>
                    <button
                      onClick={regenerateWithNextModel}
                      disabled={previewLoading || creating}
                      className="px-4 py-3 bg-fuchsia-500 text-white rounded-lg font-bold hover:bg-fuchsia-600 disabled:opacity-50"
                      title="بازتولید با مدل بعدی در لیست (rotation)"
                    >
                      {previewLoading ? '⏳' : '🔄 بازتولید'}
                    </button>
                    <button
                      onClick={() => { setStructuredPrompt(null); setEditablePromptText(''); }}
                      disabled={creating}
                      className="px-4 py-3 bg-gray-300 dark:bg-gray-700 dark:text-white rounded-lg hover:bg-gray-400 disabled:opacity-50"
                    >
                      ← برگشت
                    </button>
                  </div>
                </div>
              )}

              {previewError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-300 rounded-lg text-sm text-red-700 dark:text-red-300">
                  ❌ {previewError}
                </div>
              )}
            </div>
          </div>

          {/* لیست پروژه‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-6 border border-white/10 sticky top-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">📂 پروژه‌های من ({projects.length})</h2>
                <button
                  onClick={loadProjects}
                  className="text-sm text-blue-400 hover:underline"
                >
                  🔄
                </button>
              </div>

              {projects.length > 0 && (
                <input
                  type="text"
                  placeholder="جستجو..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full p-2 bg-white/5 border border-white/20 rounded-lg text-sm mb-4 focus:border-blue-500 focus:outline-none"
                />
              )}

              {filteredProjects.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">📭</div>
                  <p>{projects.length === 0 ? 'هنوز پروژه‌ای نساختید' : 'نتیجه‌ای پیدا نشد'}</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[60vh] overflow-auto">
                  {filteredProjects.map((p) => {
                    const typeInfo = PROJECT_TYPES.find((t) => t.id === p.project_type);
                    return (
                      <div
                        key={p.id}
                        className="group p-4 bg-white/5 rounded-xl hover:bg-white/10 transition-all border border-transparent hover:border-white/10"
                      >
                        <Link href={`/project/${p.id}`} className="block">
                          <div className="font-medium truncate flex items-center gap-2">
                            <span>{typeInfo?.icon || '📦'}</span>
                            <span>{p.name}</span>
                          </div>
                          {p.description && (
                            <p className="text-xs text-gray-400 line-clamp-2 mt-1">
                              {p.description}
                            </p>
                          )}
                          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                            <span>{p.project_type}</span>
                            {p.files?.length > 0 && (
                              <span className="text-green-400">📄 {p.files.length} فایل</span>
                            )}
                            {p.status && (
                              <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-300 rounded">
                                {p.status}
                              </span>
                            )}
                          </div>
                        </Link>
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 mt-2 text-xs transition">
                          <button
                            onClick={() => openPushModal(p)}
                            disabled={!githubReady}
                            title={
                              githubReady
                                ? 'ساخت repo در GitHub و push همه فایل‌ها'
                                : 'ابتدا توکن GitHub را در /settings تنظیم کنید'
                            }
                            className="text-cyan-300 hover:text-cyan-200 disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            🚀 push به GitHub
                          </button>
                          <button
                            onClick={() => deleteProject(p.id, p.name)}
                            className="text-red-400 hover:text-red-300 mr-auto"
                          >
                            🗑️ حذف
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* مودال push به GitHub */}
      {pushTarget && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => !pushing && setPushTarget(null)}
        >
          <div
            className="bg-gray-800 border border-white/10 rounded-2xl w-full max-w-md p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
              🚀 Push «{pushTarget.name}» به GitHub
            </h3>
            <p className="text-xs text-gray-400 mb-4">
              یک repo جدید ساخته می‌شود (یا اگر وجود داشت، فایل‌ها به‌روزرسانی می‌شوند) و همه فایل‌های پروژه upload می‌شوند.
            </p>

            <label className="block text-sm mb-1 text-gray-300">نام repo</label>
            <input
              type="text"
              value={pushRepoName}
              onChange={(e) =>
                setPushRepoName(
                  e.target.value.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/-+/g, '-'),
                )
              }
              dir="ltr"
              maxLength={80}
              className="w-full p-2 bg-white/5 border border-white/20 rounded-lg mb-3 focus:border-blue-500 focus:outline-none"
            />

            <label className="block text-sm mb-1 text-gray-300">توضیحات</label>
            <textarea
              value={pushDescription}
              onChange={(e) => setPushDescription(e.target.value)}
              rows={2}
              maxLength={300}
              className="w-full p-2 bg-white/5 border border-white/20 rounded-lg mb-3 focus:border-blue-500 focus:outline-none resize-none"
            />

            {/* 🆕 force private — checkbox locked */}
            <div className="flex items-center gap-2 mb-4 p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
              <span className="text-sm text-blue-700 dark:text-blue-300">
                🔒 <b>همیشه repo خصوصی (private)</b> ساخته می‌شود — سیاست امنیتی پروژه
              </span>
            </div>

            <div className="flex gap-2">
              <button
                onClick={submitPush}
                disabled={pushing || !pushRepoName}
                className="flex-1 py-2 bg-cyan-500 text-white rounded-lg font-bold hover:bg-cyan-600 disabled:opacity-50"
              >
                {pushing ? '⏳ در حال push...' : '🚀 شروع push'}
              </button>
              <button
                onClick={() => !pushing && setPushTarget(null)}
                disabled={pushing}
                className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 disabled:opacity-50"
              >
                لغو
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
