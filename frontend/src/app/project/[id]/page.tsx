'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
// ProjectHealthPanel در commit 3.3a حذف شد — به /oversight منتقل شد

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProjectFile {
  path: string;
  content?: string;
  size?: number;
  // 🆕 (model attribution) — which AI model produced this file +
  // when. Empty for legacy projects created before attribution shipped.
  generated_by?: string;
  generated_at?: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  project_type: string;
  status: string;
  created_at: string;
  files: ProjectFile[];
  structure: {
    directories: string[];
    files: { path: string; description: string }[];
  };
}

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [selectedFile, setSelectedFile] = useState<ProjectFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [fileLoading, setFileLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Deploy state
  const [deploying, setDeploying] = useState(false);
  const [deployUrl, setDeployUrl] = useState('');

  // 🆕 Description modal — long descriptions shouldn't be dumped onto the
  // page; user reported the raw idea text was unreadable. Show a truncated
  // preview + "show full" button → modal with proper markdown.
  const [descModalOpen, setDescModalOpen] = useState(false);

  // 🆕 Pre-push audit — user repeatedly asked for this: re-review generated
  // files against the original goal BEFORE pushing to GitHub.
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditing, setAuditing] = useState(false);
  const [auditResult, setAuditResult] = useState<any>(null);
  const [auditError, setAuditError] = useState('');

  // 🆕 Push-to-GitHub button (was missing from this page entirely)
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState<any>(null);

  // 🆕 Auto-fix: apply missing files / upgrade to fullstack based on
  // the audit result. The user's question that motivated this:
  // "این دکمه بررسی مجدد علاوه بر همه مواردی که گفته شد، این موضوع
  // رو هم بررسی و در صورت نیاز اصلاح میکنه؟"
  // Answer: now yes — after viewing audit findings, user can click
  // اعمال اصلاحات and missing files are generated in-place.
  const [fixing, setFixing] = useState(false);
  const [fixResult, setFixResult] = useState<any>(null);

  // 🆕 (per-page model picker) — user complained: "وقتی روی یه پروژه
  // ساخته شده کلیک میکنم، وقتی میخوام بررسی دوباره بزنم، جایی نیست که
  // بتونم انتخاب کنم کدوم مدل کار انجام بده". Now we render a chip-toggle
  // picker right above the audit button. Defaults to whatever the
  // creator page last saved in localStorage (same key) so the cross-page
  // workflow stays consistent; user can override per-project.
  const [availableModels, setAvailableModels] = useState<Array<{id: string; name: string}>>([]);
  const [auditModelIds, setAuditModelIds] = useState<string[]>([]);
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/simple/status`);
        if (!res.ok) return;
        const data = await res.json();
        const models = (data.models || data.available_models || []) as Array<{id: string; name: string}>;
        setAvailableModels(models);
        // Initialize selection from localStorage (creator page key)
        try {
          const saved = localStorage.getItem('creator_selected_models');
          const parsed = saved ? JSON.parse(saved) : [];
          if (Array.isArray(parsed) && parsed.length > 0) {
            setAuditModelIds(parsed.filter((x) => typeof x === 'string'));
          } else if (models.length > 0) {
            // No previous selection → default to first available
            setAuditModelIds([models[0].id]);
          }
        } catch {
          if (models.length > 0) setAuditModelIds([models[0].id]);
        }
      } catch {}
    })();
  }, []);
  const toggleAuditModel = (id: string) => {
    setAuditModelIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      try {
        localStorage.setItem('creator_selected_models', JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  useEffect(() => {
    if (projectId) {
      loadProject();
    }
  }, [projectId]);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 5000);
  };

  const loadProject = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}`);
      const data = await res.json();

      if (res.ok && data.success) {
        setProject(data.project);

        // اگه فایل‌ها وجود داره، اولین فایل رو انتخاب کن
        if (data.project.files?.length > 0) {
          const firstFile = data.project.files[0];
          if (typeof firstFile === 'object' && firstFile.path) {
            loadFileContent(firstFile.path);
          }
        }
      } else {
        showError(data.detail || 'پروژه پیدا نشد');
      }
    } catch (e) {
      showError('خطا در بارگذاری پروژه');
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filePath: string) => {
    setFileLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}/files/${encodeURIComponent(filePath)}`);
      const data = await res.json();

      if (res.ok && data.success) {
        setSelectedFile({ path: filePath, content: data.content });
      } else {
        showError('خطا در خواندن فایل');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setFileLoading(false);
    }
  };

  // 🆕 (model attribution) — read the live in-page picker. Used to be
  // a localStorage-only read from /creator; that was confusing because
  // the user couldn't see/change the choice on this page. Now we use
  // the per-page picker state (which is itself initialized from the
  // same localStorage key, so the cross-page default still works).
  const getSelectedModelIds = (): string[] => auditModelIds;

  const runAudit = async () => {
    setAuditing(true);
    setAuditError('');
    setAuditResult(null);
    setAuditOpen(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/simple/projects/${projectId}/audit`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          // 🆕 honor user's selection (parity with create flow)
          body: JSON.stringify({ model_ids: getSelectedModelIds() }),
        },
      );
      const data = await res.json();
      if (!res.ok) {
        setAuditError(data?.detail || `خطای سرور (${res.status})`);
        return;
      }
      setAuditResult(data);
    } catch (e: any) {
      setAuditError(e?.message || 'خطا در ارتباط با سرور');
    } finally {
      setAuditing(false);
    }
  };

  // 🆕 Per-item selection — user picks which modifies/deletes to apply.
  // Defaults: modify = all selected (safe, AI-driven content rewrite);
  // delete = none selected (destructive, opt-in only).
  const [selectedModifies, setSelectedModifies] = useState<Set<string>>(new Set());
  const [selectedDeletes, setSelectedDeletes] = useState<Set<string>>(new Set());

  // Reset selections each time a fresh audit lands so the UI doesn't
  // carry over choices from a prior audit.
  useEffect(() => {
    if (auditResult?.aggregated) {
      const mods = new Set<string>(
        (auditResult.aggregated.files_to_modify || []).map((m: any) => m.path),
      );
      setSelectedModifies(mods);
      setSelectedDeletes(new Set());  // delete is opt-in only
    }
  }, [auditResult]);

  const applyAuditFixes = async (opts?: {
    upgradeFullstack?: boolean;
    includeMissing?: boolean;   // add audit's missing_critical_files
    includeModifies?: boolean;  // regenerate selected modifies
    includeDeletes?: boolean;   // delete selected files
  }) => {
    setFixing(true);
    setFixResult(null);
    try {
      // 🆕 honor user's model selection from /creator (same as audit)
      const body: any = { model_ids: getSelectedModelIds() };
      // 🐛 (bug fix v2) — switched from negative-flag opts (onlyMissing,
      // upgradeOnly) to positive include* flags. The old form let "فقط
      // حذف" accidentally still send missing_files because the inclusion
      // condition was `!opts.upgradeOnly`. Now each intent is opt-in
      // explicit so granular buttons can't silently send extra work.
      if (opts?.upgradeFullstack) {
        body.upgrade_to_fullstack = true;
      }
      if (
        opts?.includeMissing
        && auditResult?.aggregated?.missing_critical_files?.length
      ) {
        body.missing_files = auditResult.aggregated.missing_critical_files;
      }
      if (opts?.includeModifies) {
        const mods = (auditResult?.aggregated?.files_to_modify || [])
          .filter((m: any) => selectedModifies.has(m.path));
        if (mods.length > 0) body.files_to_modify = mods;
      }
      if (opts?.includeDeletes && selectedDeletes.size > 0) {
        body.files_to_delete = Array.from(selectedDeletes);
      }
      const res = await fetch(
        `${API_BASE}/api/simple/projects/${projectId}/apply-fixes`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      );
      const data = await res.json();
      if (!res.ok) {
        showError(data?.detail || `خطای سرور (${res.status})`);
        return;
      }
      setFixResult(data);
      // Reload the project to pick up the new + modified + deleted files
      await loadProject();
      const parts: string[] = [];
      if (data.files_added?.length) parts.push(`${data.files_added.length} اضافه`);
      if (data.files_modified?.length) parts.push(`${data.files_modified.length} ویرایش`);
      if (data.files_deleted?.length) parts.push(`${data.files_deleted.length} حذف`);
      showSuccess(
        parts.length > 0
          ? `✅ ${parts.join('، ')} انجام شد.`
          : 'هیچ تغییری لازم نبود.',
      );
    } catch (e: any) {
      showError(e?.message || 'خطا در ارتباط با سرور');
    } finally {
      setFixing(false);
    }
  };

  const pushToGithub = async () => {
    setPushing(true);
    setPushResult(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/simple/projects/${projectId}/push-to-github`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ private: true }),
        },
      );
      const data = await res.json();
      if (data?.success) {
        setPushResult(data);
        showSuccess('پروژه با موفقیت به GitHub push شد.');
      } else {
        showError(data?.detail || data?.error || 'خطا در push به GitHub');
      }
    } catch (e: any) {
      showError(e?.message || 'خطا در ارتباط با سرور');
    } finally {
      setPushing(false);
    }
  };

  const deployToRender = async () => {
    setDeploying(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await res.json();
      if (data.success) {
        setDeployUrl(data.deploy_url || '');
        showSuccess('Deploy شروع شد!');
      } else {
        showError(data.detail || 'خطا در Deploy');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setDeploying(false);
    }
  };

  const deleteProject = async () => {
    if (!confirm('آیا مطمئنی میخوای این پروژه رو حذف کنی؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        showSuccess('پروژه حذف شد');
        setTimeout(() => router.push('/creator'), 1000);
      } else {
        showError('خطا در حذف');
      }
    } catch (e) {
      showError('خطا');
    }
  };

  const getFileIcon = (path: string) => {
    if (path.endsWith('.py')) return '🐍';
    if (path.endsWith('.js') || path.endsWith('.ts')) return '📜';
    if (path.endsWith('.tsx') || path.endsWith('.jsx')) return '⚛️';
    if (path.endsWith('.json')) return '📋';
    if (path.endsWith('.md')) return '📝';
    if (path.endsWith('.html')) return '🌐';
    if (path.endsWith('.css')) return '🎨';
    if (path.endsWith('.yaml') || path.endsWith('.yml')) return '⚙️';
    if (path.endsWith('.env') || path.endsWith('.env.example')) return '🔐';
    if (path.includes('Dockerfile') || path.includes('docker')) return '🐳';
    if (path.includes('requirements') || path.includes('package')) return '📦';
    return '📄';
  };

  const getLanguage = (path: string) => {
    if (path.endsWith('.py')) return 'python';
    if (path.endsWith('.js')) return 'javascript';
    if (path.endsWith('.ts')) return 'typescript';
    if (path.endsWith('.tsx')) return 'tsx';
    if (path.endsWith('.jsx')) return 'jsx';
    if (path.endsWith('.json')) return 'json';
    if (path.endsWith('.md')) return 'markdown';
    if (path.endsWith('.html')) return 'html';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml';
    return 'text';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center text-white">
          <div className="animate-spin text-5xl mb-4">*</div>
          <p className="text-xl">در حال بارگذاری پروژه...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center text-white">
          <div className="text-6xl mb-4">!</div>
          <p className="text-xl mb-4">پروژه پیدا نشد</p>
          <Link href="/creator" className="px-6 py-3 bg-blue-500 rounded-lg hover:bg-blue-600">
            برگشت به موتور خالق
          </Link>
        </div>
      </div>
    );
  }

  const files = project.files || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white" dir="rtl">
      {/* پیام‌ها */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-pulse">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50">
          {success}
        </div>
      )}

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-start justify-between mb-6 gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
              <Link href="/creator" className="hover:text-blue-400">موتور خالق</Link>
              <span>/</span>
              <span>{project.name}</span>
            </div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            {/* 🆕 (description fix) — clamp the description to 2 lines and
                offer a "نمایش کامل" button that opens a modal with the full
                formatted text. Previously the raw description was dumped
                onto the header and wrapped awkwardly. */}
            <div className="mt-1 flex items-start gap-3 max-w-3xl">
              <p
                className="text-gray-400 text-sm overflow-hidden"
                style={{
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {project.description}
              </p>
              {project.description && project.description.length > 100 && (
                <button
                  onClick={() => setDescModalOpen(true)}
                  className="shrink-0 text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded hover:bg-blue-500/30 whitespace-nowrap"
                >
                  📄 نمایش کامل
                </button>
              )}
            </div>
          </div>
          <div className="flex gap-2 flex-wrap shrink-0">
            {/* 🆕 Pre-push audit button — re-review with active models */}
            <button
              onClick={runAudit}
              disabled={auditing}
              className="px-4 py-2 bg-amber-500/90 text-black rounded-lg hover:bg-amber-400 disabled:opacity-50 font-medium"
              title="قبل از push، توسط همهٔ مدل‌های فعال audit شود"
            >
              {auditing ? '🔎 در حال بررسی...' : '🔎 بررسی مجدد قبل از push'}
            </button>
            {/* 🆕 Push to GitHub — was missing from this page entirely */}
            <button
              onClick={pushToGithub}
              disabled={pushing}
              className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 font-medium"
            >
              {pushing ? '... در حال push' : '🐙 push به GitHub'}
            </button>
            <button
              onClick={deployToRender}
              disabled={deploying}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 font-medium"
            >
              {deploying ? '... در حال Deploy' : 'Deploy به Render'}
            </button>
            <button
              onClick={deleteProject}
              className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 border border-red-500/50"
            >
              حذف
            </button>
            <Link
              href="/creator"
              className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20"
            >
              برگشت
            </Link>
          </div>
        </div>

        {/* اطلاعات پروژه */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">نوع پروژه</div>
            <div className="font-medium text-lg">{project.project_type}</div>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">وضعیت</div>
            <div className="font-medium text-lg">
              <span className={`inline-block px-2 py-1 rounded text-sm ${
                project.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                project.status === 'generating' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-blue-500/20 text-blue-400'
              }`}>
                {project.status === 'completed' ? 'تکمیل شده' :
                 project.status === 'generating' ? 'در حال تولید' : project.status}
              </span>
            </div>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">تعداد فایل</div>
            <div className="font-medium text-lg">{files.length} فایل</div>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">تاریخ ایجاد</div>
            <div className="font-medium text-sm">
              {new Date(project.created_at).toLocaleDateString('fa-IR')}
            </div>
          </div>
        </div>

        {/* Deploy URL */}
        {deployUrl && (
          <div className="mb-6 p-4 bg-green-500/20 border border-green-500/50 rounded-xl">
            <p className="text-green-400">
              Deploy موفق! آدرس: <a href={deployUrl} target="_blank" rel="noopener noreferrer" className="underline">{deployUrl}</a>
            </p>
          </div>
        )}

        {/* پنل تحلیل سلامت در commit 3.3a حذف شد. کاربران باید برای
            تحلیل پروژه به /oversight بروند. */}

        {/* 🆕 (model picker for audit) — کاربر دقیقاً اینجا می‌تواند
            انتخاب کند کدام مدل‌ها audit/apply-fixes را انجام بدهند.
            انتخاب در همان localStorage که /creator می‌نویسد ذخیره می‌شود
            تا cross-page consistent بماند. */}
        {availableModels.length > 0 && (
          <div className="mb-6 p-4 bg-white/5 backdrop-blur rounded-xl border border-white/10">
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <h3 className="font-bold text-sm flex items-center gap-2">
                🤖 مدل‌های audit / اصلاح
              </h3>
              <p className="text-xs text-gray-400">
                {auditModelIds.length} مدل انتخاب شده — انتخاب چند مدل = اجماع (consensus)
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {availableModels.map((m) => {
                const selected = auditModelIds.includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggleAuditModel(m.id)}
                    className={`px-3 py-1.5 rounded-lg text-sm border transition ${
                      selected
                        ? 'bg-blue-500 text-white border-blue-500'
                        : 'bg-white/5 text-gray-200 border-white/10 hover:bg-white/10'
                    }`}
                  >
                    {selected ? '✓ ' : ''}{m.name || m.id}
                  </button>
                );
              })}
            </div>
            {auditModelIds.length === 0 && (
              <p className="text-xs text-amber-400 mt-2">
                ⚠️ هیچ مدلی انتخاب نشده — audit از همهٔ مدل‌های فعال استفاده می‌کند.
              </p>
            )}
          </div>
        )}

        <div className="grid lg:grid-cols-4 gap-6">
          {/* لیست فایل‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-4 sticky top-6">
              <h2 className="font-bold mb-4 flex items-center gap-2">
                <span>*</span> فایل‌های پروژه
              </h2>

              {files.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">-</div>
                  <p>هنوز فایلی تولید نشده</p>
                </div>
              ) : (
                <div className="space-y-1 max-h-[65vh] overflow-auto">
                  {files.map((file, idx) => {
                    const filePath = typeof file === 'string' ? file : file.path;
                    const generatedBy = typeof file === 'object' && file.generated_by
                      ? file.generated_by : '';
                    return (
                      <button
                        key={idx}
                        onClick={() => loadFileContent(filePath)}
                        className={`w-full text-right p-3 rounded-lg text-sm font-mono transition-all ${
                          selectedFile?.path === filePath
                            ? 'bg-blue-500/30 border border-blue-500'
                            : 'bg-white/5 hover:bg-white/10 border border-transparent'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center min-w-0 flex-1">
                            <span className="ml-2">{getFileIcon(filePath)}</span>
                            <span className="truncate">{filePath}</span>
                          </div>
                          {/* 🆕 model attribution badge — answers user's
                              question "امضاشون پای کار ثبت می‌شه؟" */}
                          {generatedBy && (
                            <span
                              className="px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded text-[10px] font-sans whitespace-nowrap"
                              title={`تولیدشده توسط: ${generatedBy}`}
                            >
                              {generatedBy.length > 18 ? generatedBy.slice(0, 16) + '…' : generatedBy}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* ساختار پروژه */}
            {project.structure?.directories && project.structure.directories.length > 0 && (
              <div className="bg-white/10 backdrop-blur rounded-2xl p-4 mt-4">
                <h2 className="font-bold mb-3">* ساختار پوشه‌ها</h2>
                <div className="space-y-1 text-sm font-mono">
                  {project.structure.directories.map((dir, idx) => (
                    <div key={idx} className="text-blue-400">
                      + {dir}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* محتوای فایل */}
          <div className="lg:col-span-3">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold flex items-center gap-2">
                  {selectedFile ? (
                    <>
                      <span>{getFileIcon(selectedFile.path)}</span>
                      <span className="font-mono">{selectedFile.path}</span>
                    </>
                  ) : (
                    <span>محتوای فایل</span>
                  )}
                </h2>
                {selectedFile && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(selectedFile.content || '');
                      showSuccess('کپی شد!');
                    }}
                    className="px-3 py-1 bg-white/10 rounded text-sm hover:bg-white/20"
                  >
                    کپی
                  </button>
                )}
              </div>

              {fileLoading ? (
                <div className="text-center py-12 text-gray-400">
                  <div className="animate-spin text-3xl mb-2">*</div>
                  <p>در حال بارگذاری...</p>
                </div>
              ) : selectedFile?.content ? (
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-xl overflow-auto max-h-[70vh] text-sm leading-relaxed">
                    <code>{selectedFile.content}</code>
                  </pre>
                  <div className="absolute top-2 left-2 px-2 py-1 bg-gray-700 rounded text-xs text-gray-300">
                    {getLanguage(selectedFile.path)}
                  </div>
                </div>
              ) : (
                <div className="text-center py-16 text-gray-400">
                  <div className="text-6xl mb-4">-</div>
                  <p className="text-lg">یک فایل از سمت راست انتخاب کن</p>
                </div>
              )}
            </div>

            {/* راهنمای Deploy */}
            <div className="bg-white/10 backdrop-blur rounded-2xl p-4 mt-4">
              <h2 className="font-bold mb-3">* راهنمای Deploy</h2>
              <div className="text-sm text-gray-300 space-y-2">
                <p>۱. دکمه "Deploy به Render" رو بزن</p>
                <p>۲. یا فایل‌ها رو دانلود کن و دستی آپلود کن به GitHub</p>
                <p>۳. بعد از Render اتصال بده به repo</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 🆕 Description modal */}
      {descModalOpen && project && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setDescModalOpen(false)}
        >
          <div
            className="bg-gray-900 border border-white/10 rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 flex items-center justify-between p-4 bg-gray-900 border-b border-white/10">
              <h3 className="font-bold text-lg">📄 توضیحات کامل — {project.name}</h3>
              <button
                onClick={() => setDescModalOpen(false)}
                className="px-3 py-1 bg-white/10 rounded hover:bg-white/20"
              >
                بستن
              </button>
            </div>
            <div className="p-6">
              <pre className="whitespace-pre-wrap text-gray-200 text-sm leading-7 font-sans">
                {project.description}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* 🆕 Pre-push audit modal */}
      {auditOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => !auditing && setAuditOpen(false)}
        >
          <div
            className="bg-gray-900 border border-white/10 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 flex items-center justify-between p-4 bg-gray-900 border-b border-white/10 z-10">
              <h3 className="font-bold text-lg">🔎 بررسی مجدد قبل از push</h3>
              <button
                onClick={() => setAuditOpen(false)}
                disabled={auditing}
                className="px-3 py-1 bg-white/10 rounded hover:bg-white/20 disabled:opacity-50"
              >
                بستن
              </button>
            </div>
            <div className="p-6 space-y-4">
              {auditing && (
                <div className="text-center py-10">
                  <p className="text-gray-300">
                    در حال بررسی توسط همهٔ مدل‌های فعال... این ممکن است ۳۰-۹۰ ثانیه طول بکشد.
                  </p>
                </div>
              )}
              {auditError && (
                <div className="bg-red-500/20 border border-red-500/50 rounded p-3 text-red-200">
                  ❌ {auditError}
                </div>
              )}
              {auditResult?.aggregated && (
                <>
                  <div className="bg-white/5 rounded-lg p-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div>
                      <div className="text-xs text-gray-400">امتیاز میانگین</div>
                      <div className="text-2xl font-bold text-blue-300">
                        {auditResult.aggregated.overall_score_avg}/100
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400">آماده push؟</div>
                      <div className={`text-lg font-bold ${
                        auditResult.aggregated.ready_to_push_majority
                          ? 'text-green-300' : 'text-amber-300'
                      }`}>
                        {auditResult.aggregated.ready_to_push_majority ? '✅ بله' : '⚠️ خیر'}
                      </div>
                      <div className="text-xs text-gray-500">
                        ({auditResult.aggregated.ready_to_push_votes})
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400">با هدف می‌خواند؟</div>
                      <div className={`text-lg font-bold ${
                        auditResult.aggregated.matches_goal_majority
                          ? 'text-green-300' : 'text-amber-300'
                      }`}>
                        {auditResult.aggregated.matches_goal_majority ? 'بله' : 'خیر'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400">مدل‌ها</div>
                      <div className="text-lg font-bold">
                        {auditResult.aggregated.models_succeeded}/{auditResult.aggregated.models_consulted}
                      </div>
                    </div>
                  </div>

                  {/* 🆕 (model attribution) — show WHICH models did the
                      audit so user can confirm their /creator selection
                      was honored, not just "all active models". */}
                  {auditResult.aggregated.model_ids_used?.length > 0 && (
                    <div className="text-xs text-gray-400 flex items-center gap-2 flex-wrap">
                      <span>🔖 audit توسط:</span>
                      {auditResult.aggregated.model_ids_used.map((id: string) => (
                        <span
                          key={id}
                          className="px-2 py-0.5 bg-blue-500/20 text-blue-200 rounded-full font-mono"
                        >
                          {id}
                        </span>
                      ))}
                      <span className="text-gray-500">
                        (انتخاب شما)
                      </span>
                    </div>
                  )}

                  {/* 🆕 (regression detection) — کاربر گزارش داد بعد از
                      apply گاهی امتیاز پایین‌تر می‌رود. حالا backend دلتا را
                      محاسبه می‌کند و اگر منفی مهم بود warning می‌فرستد. */}
                  {auditResult.aggregated.regression_warning && (
                    <div className="bg-amber-500/15 border border-amber-500/40 rounded-lg p-4">
                      <h4 className="font-bold text-amber-300 mb-1 flex items-center gap-2">
                        ⚠️ هشدار regression
                      </h4>
                      <p className="text-sm text-amber-100 leading-relaxed">
                        {auditResult.aggregated.regression_warning}
                      </p>
                    </div>
                  )}

                  {/* 🆕 (convergence notice) — وقتی ۳ audit اخیر نوسان دارند
                      و amount کلی issue ها مشابه است، یعنی پروژه به یک
                      «کیفیت قابل قبول» رسیده و audit بیشتر فقط نظر شخصی
                      مدل را اضافه می‌کند. این پیام سبز به کاربر می‌گوید
                      حلقهٔ بی‌پایان نیافتند، آماده push است. */}
                  {auditResult.aggregated.convergence_notice && (
                    <div className="bg-green-500/15 border border-green-500/40 rounded-lg p-4">
                      <h4 className="font-bold text-green-300 mb-1 flex items-center gap-2">
                        🎯 پروژه آماده‌ی push است
                      </h4>
                      <p className="text-sm text-green-100 leading-relaxed whitespace-pre-line">
                        {auditResult.aggregated.convergence_notice}
                      </p>
                    </div>
                  )}

                  {/* 🆕 (audit history) — نشان دادن چند audit/apply اخیر
                      تا کاربر روند را ببیند (افزایش/کاهش امتیاز در طول
                      چند iteration) و metric های مهم را tracking کند. */}
                  {auditResult.audit_history && auditResult.audit_history.length > 1 && (
                    <details className="bg-white/5 border border-white/10 rounded-lg p-3" open>
                      <summary className="cursor-pointer text-sm font-bold text-gray-200">
                        📜 تاریخچهٔ audit / apply ({auditResult.audit_history.length})
                      </summary>
                      <div className="mt-3 space-y-2">
                        {auditResult.audit_history.slice().reverse().map((ev: any, i: number) => (
                          <div key={i} className="flex items-start gap-2 text-xs border-r-2 border-gray-600 pr-3">
                            <span className="shrink-0">{ev.kind === 'audit' ? '🔎' : '🔧'}</span>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 flex-wrap text-gray-300">
                                <span className="font-mono text-gray-500">{ev.run_at}</span>
                                {ev.kind === 'audit' && (
                                  <>
                                    <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-200">
                                      امتیاز: {ev.overall_score}
                                    </span>
                                    {ev.missing_count > 0 && (
                                      <span className="text-red-300">🚫 {ev.missing_count} مفقود</span>
                                    )}
                                    {ev.modify_count > 0 && (
                                      <span className="text-amber-300">✏️ {ev.modify_count} اصلاح</span>
                                    )}
                                  </>
                                )}
                                {ev.kind === 'apply' && (
                                  <>
                                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-200">
                                      ✅ {ev.added_count || 0}+ {ev.modified_count || 0}~ {ev.deleted_count || 0}-
                                    </span>
                                  </>
                                )}
                              </div>
                              {ev.summary && (
                                <p className="text-gray-400 mt-1 leading-relaxed line-clamp-2">{ev.summary}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}

                  {auditResult.aggregated.missing_critical_files?.length > 0 && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
                      <h4 className="font-bold text-red-300 mb-2">
                        🚫 فایل‌های حیاتی مفقود
                      </h4>
                      <ul className="text-sm space-y-1 list-disc pr-5">
                        {auditResult.aggregated.missing_critical_files.map((x: string, i: number) => (
                          <li key={i} className="text-red-200">{x}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {auditResult.aggregated.structural_issues?.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/30 rounded p-3">
                      <h4 className="font-bold text-amber-300 mb-2">
                        🏗 مشکلات ساختاری
                      </h4>
                      <ul className="text-sm space-y-1 list-disc pr-5">
                        {auditResult.aggregated.structural_issues.map((x: string, i: number) => (
                          <li key={i} className="text-amber-200">{x}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {auditResult.aggregated.goal_mismatch_reasons?.length > 0 && (
                    <div className="bg-orange-500/10 border border-orange-500/30 rounded p-3">
                      <h4 className="font-bold text-orange-300 mb-2">
                        🎯 ناهماهنگی با هدف اولیه
                      </h4>
                      <ul className="text-sm space-y-1 list-disc pr-5">
                        {auditResult.aggregated.goal_mismatch_reasons.map((x: string, i: number) => (
                          <li key={i} className="text-orange-200">{x}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {auditResult.aggregated.quality_concerns?.length > 0 && (
                    <div className="bg-white/5 border border-white/10 rounded p-3">
                      <h4 className="font-bold text-gray-300 mb-2">
                        🧪 نگرانی‌های کیفیت
                      </h4>
                      <ul className="text-sm space-y-1 list-disc pr-5">
                        {auditResult.aggregated.quality_concerns.map((x: string, i: number) => (
                          <li key={i} className="text-gray-300">{x}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {auditResult.aggregated.suggestions_before_push?.length > 0 && (
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3">
                      <h4 className="font-bold text-blue-300 mb-2">
                        💡 پیشنهادات قبل از push
                      </h4>
                      <ul className="text-sm space-y-1 list-disc pr-5">
                        {auditResult.aggregated.suggestions_before_push.map((x: string, i: number) => (
                          <li key={i} className="text-blue-200">{x}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <details className="bg-white/5 rounded p-3">
                    <summary className="cursor-pointer text-gray-300 font-medium">
                      نظر هر مدل به‌تفکیک ({auditResult.per_model?.length || 0})
                    </summary>
                    <div className="mt-3 space-y-3">
                      {auditResult.per_model?.map((r: any, i: number) => (
                        <div key={i} className="bg-black/30 rounded p-3 text-sm">
                          <div className="font-mono text-blue-300 mb-1">
                            {r.model_id} {r.ok ? '✅' : '❌'}
                          </div>
                          {r.ok && r.report?.summary && (
                            <p className="text-gray-300 whitespace-pre-wrap">{r.report.summary}</p>
                          )}
                          {!r.ok && (
                            <p className="text-red-300">{r.error}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </details>

                  {/* 🆕 Files-to-modify section — user picks per-file
                      which to regenerate with audit context */}
                  {auditResult.aggregated.files_to_modify?.length > 0 && (
                    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-3 space-y-2">
                      <h4 className="font-bold text-yellow-300">
                        ✏️ فایل‌های نیازمند ویرایش
                      </h4>
                      <p className="text-xs text-gray-400">
                        AI تشخیص داد محتوای این فایل‌ها مطابق هدف نیست. تیک بزن
                        تا regenerate شوند (محتوای فعلی به‌عنوان context
                        به prompt اضافه می‌شود).
                      </p>
                      <ul className="space-y-2">
                        {auditResult.aggregated.files_to_modify.map(
                          (m: any, i: number) => (
                            <li key={i} className="bg-black/20 rounded p-2 text-sm">
                              <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={selectedModifies.has(m.path)}
                                  onChange={(e) => {
                                    const next = new Set(selectedModifies);
                                    if (e.target.checked) next.add(m.path);
                                    else next.delete(m.path);
                                    setSelectedModifies(next);
                                  }}
                                  className="mt-1"
                                />
                                <div className="flex-1">
                                  <div className="font-mono text-yellow-200">{m.path}</div>
                                  {m.issue && (
                                    <div className="text-gray-300 mt-1">
                                      <span className="text-yellow-300">مشکل:</span> {m.issue}
                                    </div>
                                  )}
                                  {m.suggestion && (
                                    <div className="text-gray-300 mt-0.5">
                                      <span className="text-blue-300">پیشنهاد:</span> {m.suggestion}
                                    </div>
                                  )}
                                </div>
                              </label>
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}

                  {/* 🆕 Files-to-delete section — opt-in only because
                      destructive. Defaults to all unchecked. */}
                  {auditResult.aggregated.files_to_delete?.length > 0 && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded p-3 space-y-2">
                      <h4 className="font-bold text-red-300">
                        🗑 فایل‌های پیشنهادی برای حذف
                      </h4>
                      <p className="text-xs text-gray-400">
                        ⚠️ این فایل‌ها بنا به نظر AI زائد/اشتباه‌اند. حذف **فقط
                        با تیک صریح شما** انجام می‌شود — هیچ‌چیز خودکار حذف
                        نمی‌شود.
                      </p>
                      <ul className="space-y-2">
                        {auditResult.aggregated.files_to_delete.map(
                          (d: any, i: number) => (
                            <li key={i} className="bg-black/20 rounded p-2 text-sm">
                              <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={selectedDeletes.has(d.path)}
                                  onChange={(e) => {
                                    const next = new Set(selectedDeletes);
                                    if (e.target.checked) next.add(d.path);
                                    else next.delete(d.path);
                                    setSelectedDeletes(next);
                                  }}
                                  className="mt-1"
                                />
                                <div className="flex-1">
                                  <div className="font-mono text-red-200">{d.path}</div>
                                  {d.reason && (
                                    <div className="text-gray-300 mt-1">
                                      <span className="text-red-300">دلیل:</span> {d.reason}
                                    </div>
                                  )}
                                </div>
                              </label>
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}

                  {/* 🆕 Auto-fix action buttons — the user asked for this
                      explicitly. Audit was previously report-only; now
                      missing files can be added, existing modified, and
                      flagged files deleted (all per-item opt-in for
                      destructive actions). */}
                  {(auditResult.aggregated.missing_critical_files?.length > 0 ||
                    auditResult.aggregated.files_to_modify?.length > 0 ||
                    auditResult.aggregated.files_to_delete?.length > 0 ||
                    !auditResult.aggregated.matches_goal_majority) && (
                    <div className="bg-green-500/10 border border-green-500/30 rounded p-4 space-y-3">
                      <h4 className="font-bold text-green-300">
                        ✨ اعمال اصلاحات خودکار
                      </h4>
                      <p className="text-sm text-gray-300">
                        می‌توانی فایل‌های مفقود را همین‌جا تولید کنی — پروژه پاک
                        نمی‌شود، فقط آن‌چه که هست نگه داشته می‌شود و فایل‌های
                        جدید اضافه می‌شوند.
                      </p>
                      {/* ⭐ THE ONE BUTTON: do everything user wants in one
                          go — promote if applicable + add all audit
                          missing + modify all selected + delete all selected.
                          This is the "right" button for users who reviewed
                          the findings and want everything applied. */}
                      <div className="bg-purple-500/15 border border-purple-500/40 rounded p-3 space-y-2">
                        <h5 className="font-bold text-purple-200 text-sm">
                          ⭐ توصیه شده: یک‌بار همه را اعمال کن
                        </h5>
                        <p className="text-xs text-gray-300">
                          ارتقا (اگر لازم) + همهٔ فایل‌های مفقود audit + همهٔ
                          ویرایش‌های تیک‌خورده + همهٔ حذف‌های تیک‌خورده. این
                          دکمه دقیقاً همان کاری را می‌کند که از audit
                          انتظار داشتی.
                        </p>
                        <button
                          onClick={() => {
                            const delN = selectedDeletes.size;
                            if (delN > 0 && !confirm(
                              `این عملیات شامل حذف ${delN} فایل است که قابل ` +
                              `بازگشت نیست. مطمئنی؟`,
                            )) return;
                            applyAuditFixes({
                              upgradeFullstack:
                                project?.project_type !== 'fullstack'
                                && !auditResult.aggregated.matches_goal_majority,
                              includeMissing: true,
                              includeModifies: true,
                              includeDeletes: true,
                            });
                          }}
                          disabled={fixing}
                          className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 text-sm font-bold"
                        >
                          {fixing
                            ? '... در حال اعمال کامل'
                            : `✅ اعمال کامل: ${
                                (auditResult.aggregated.missing_critical_files?.length || 0)
                              } افزودن + ${selectedModifies.size} ویرایش + ${selectedDeletes.size} حذف${
                                project?.project_type !== 'fullstack'
                                && !auditResult.aggregated.matches_goal_majority
                                  ? ' + ارتقا fullstack' : ''
                              }`}
                        </button>
                      </div>

                      {/* Granular actions — for users who want to apply
                          only one category at a time (preview each effect
                          before committing). */}
                      <details className="bg-white/5 rounded">
                        <summary className="cursor-pointer text-xs text-gray-300 px-3 py-2">
                          ↓ گزینه‌های جداگانه (پیشرفته)
                        </summary>
                        <div className="p-3 space-y-2">
                          <div className="text-xs text-gray-400">
                            هر دکمه فقط یک نوع عملیات انجام می‌دهد. برای
                            دیدن اثر هر بخش به‌تنهایی قبل از اعمال کامل
                            مفید است.
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {/* 1. Just add missing files (no modify, no delete) */}
                            {auditResult.aggregated.missing_critical_files?.length > 0 && (
                              <button
                                onClick={() => applyAuditFixes({ includeMissing: true })}
                                disabled={fixing}
                                className="px-3 py-1.5 bg-green-500/80 text-white rounded hover:bg-green-500 disabled:opacity-50 text-xs"
                                title="فقط افزودن. هیچ ویرایش، حذف یا ارتقا انجام نمی‌شود."
                              >
                                📄 فقط افزودن {auditResult.aggregated.missing_critical_files.length} فایل
                              </button>
                            )}
                            {auditResult.aggregated.files_to_modify?.length > 0 && (
                              <button
                                onClick={() => applyAuditFixes({ includeModifies: true })}
                                disabled={fixing || selectedModifies.size === 0}
                                className="px-3 py-1.5 bg-yellow-500/80 text-black rounded hover:bg-yellow-400 disabled:opacity-50 text-xs"
                                title="فقط ویرایش فایل‌های تیک‌خورده. افزودن یا حذف انجام نمی‌شود."
                              >
                                ✏️ فقط ویرایش {selectedModifies.size}
                              </button>
                            )}
                            {project?.project_type !== 'fullstack' && (
                              <button
                                onClick={() => applyAuditFixes({
                                  upgradeFullstack: true,
                                })}
                                disabled={fixing}
                                className="px-3 py-1.5 bg-blue-500/80 text-white rounded hover:bg-blue-500 disabled:opacity-50 text-xs"
                                title="فقط ارتقا به fullstack با template پیش‌فرض. فایل‌های خاص audit و ویرایش‌ها اعمال نمی‌شوند."
                              >
                                🚀 فقط ارتقا به fullstack
                              </button>
                            )}
                            {selectedDeletes.size > 0 && (
                              <button
                                onClick={() => {
                                  if (!confirm(
                                    `حذف ${selectedDeletes.size} فایل قابل بازگشت نیست. مطمئنی؟`,
                                  )) return;
                                  applyAuditFixes({ includeDeletes: true });
                                }}
                                disabled={fixing}
                                className="px-3 py-1.5 bg-red-500/80 text-white rounded hover:bg-red-500 disabled:opacity-50 text-xs"
                                title="فقط حذف فایل‌های تیک‌خورده. افزودن یا ویرایش انجام نمی‌شود."
                              >
                                🗑 فقط حذف {selectedDeletes.size}
                              </button>
                            )}
                          </div>
                        </div>
                      </details>
                      {fixResult && (
                        <div className="text-sm bg-black/20 rounded p-3 space-y-2">
                          <div className="text-green-300 font-medium">✅ نتیجه:</div>
                          {fixResult.promoted_to_fullstack && (
                            <div>↗ پروژه به fullstack ارتقا یافت</div>
                          )}
                          {fixResult.files_added?.length > 0 && (
                            <div>
                              <div className="text-green-300">📄 اضافه‌شده ({fixResult.files_added.length}):</div>
                              <ul className="list-disc pr-5 text-green-200">
                                {fixResult.files_added.slice(0, 10).map((f: any, i: number) => (
                                  <li key={i} className="font-mono">{f.path}</li>
                                ))}
                                {fixResult.files_added.length > 10 && (
                                  <li>... +{fixResult.files_added.length - 10} فایل دیگر</li>
                                )}
                              </ul>
                            </div>
                          )}
                          {fixResult.files_modified?.length > 0 && (
                            <div>
                              <div className="text-yellow-300">✏️ ویرایش‌شده ({fixResult.files_modified.length}):</div>
                              <ul className="list-disc pr-5 text-yellow-200">
                                {fixResult.files_modified.slice(0, 10).map((f: any, i: number) => (
                                  <li key={i} className="font-mono">{f.path}</li>
                                ))}
                                {fixResult.files_modified.length > 10 && (
                                  <li>... +{fixResult.files_modified.length - 10} فایل دیگر</li>
                                )}
                              </ul>
                            </div>
                          )}
                          {fixResult.files_deleted?.length > 0 && (
                            <div>
                              <div className="text-red-300">🗑 حذف‌شده ({fixResult.files_deleted.length}):</div>
                              <ul className="list-disc pr-5 text-red-200">
                                {fixResult.files_deleted.slice(0, 10).map((f: any, i: number) => (
                                  <li key={i} className="font-mono">{f.path}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {fixResult.files_skipped?.length > 0 && (
                            <div className="text-amber-300">
                              ⚠️ {fixResult.files_skipped.length} مورد skip شد
                            </div>
                          )}
                          <div className="text-xs text-gray-400 pt-1">
                            می‌توانی "🔄 audit دوباره" بزنی تا تأیید شود.
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex justify-end gap-2 pt-4 border-t border-white/10 flex-wrap">
                    <button
                      onClick={() => setAuditOpen(false)}
                      className="px-4 py-2 bg-white/10 rounded hover:bg-white/20"
                    >
                      بستن
                    </button>
                    <button
                      onClick={() => {
                        setAuditOpen(false);
                        runAudit();
                      }}
                      disabled={auditing || fixing}
                      className="px-4 py-2 bg-amber-500/80 text-black rounded hover:bg-amber-400 disabled:opacity-50"
                    >
                      🔄 audit دوباره
                    </button>
                    <button
                      onClick={() => {
                        setAuditOpen(false);
                        pushToGithub();
                      }}
                      disabled={pushing || fixing}
                      className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
                    >
                      🐙 push با وجود این یافته‌ها
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
