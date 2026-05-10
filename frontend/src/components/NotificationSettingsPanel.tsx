'use client';

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type ChannelStatus = {
  configured_via_env: boolean;
  enabled_pref: boolean;
  ready: boolean;
};

type Status = {
  prefs: {
    events: Record<string, boolean>;
    sound: Record<string, boolean>;
    channels: Record<string, { enabled: boolean }>;
    min_priority: 'low' | 'medium' | 'high' | 'critical';
    include_hashtags: boolean;
    include_inline_buttons: boolean;
    app_base_url: string;
  };
  channels: Record<string, ChannelStatus>;
  events_registry: Record<string, { label: string; help: string; icon: string }>;
};

// گروه‌بندی events برای نمایش بهتر
const EVENT_GROUPS: Array<{ title: string; icon: string; keys: string[] }> = [
  {
    title: 'Verify (نتیجه بازبینی تسک)',
    icon: '🔍',
    keys: ['verify_done', 'verify_partial', 'verify_not_done', 'verify_regressed', 'verify_clarification'],
  },
  {
    title: 'Scan (اسکن پروژه)',
    icon: '🔬',
    keys: ['scan_started', 'scan_done', 'scan_critical_found', 'scan_failed'],
  },
  {
    title: 'Task & Idea (تسک و ایده)',
    icon: '📌',
    keys: ['task_created', 'idea_created', 'pr_created'],
  },
  {
    title: 'سیستم',
    icon: '⚙️',
    keys: ['manual_test'],
  },
];

export default function NotificationSettingsPanel() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [appUrlDraft, setAppUrlDraft] = useState<string>('');
  const [webhookSetting, setWebhookSetting] = useState(false);
  const [webhookResult, setWebhookResult] = useState<string>('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/notifications/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus(data);
      setAppUrlDraft(data.prefs?.app_base_url || '');
    } catch (e: any) {
      setError(`خطا در بارگذاری: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const updatePrefs = async (partial: any) => {
    setSaving(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/notifications/prefs`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(partial),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // re-merge
      setStatus(prev => prev ? { ...prev, prefs: data.prefs } : prev);
    } catch (e: any) {
      setError(`ذخیره ناموفق: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const test = async (channel?: string) => {
    setTesting(channel || 'all');
    setTestResult('');
    try {
      const res = await fetch(`${API_BASE}/api/notifications/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: channel || null }),
      });
      const data = await res.json();
      const lines = (data.results || []).map((r: any) =>
        r.ok
          ? `✅ ${r.channel}: ارسال شد${r.silent ? ' (silent)' : ' (با صدا)'}`
          : `❌ ${r.channel}: ${r.error || 'failed'}`
      );
      setTestResult(lines.join('\n') || 'هیچ کانال آماده‌ای پیدا نشد');
    } catch (e: any) {
      setTestResult(`خطا: ${e.message}`);
    } finally {
      setTesting(null);
    }
  };

  const setWebhook = async () => {
    if (!status?.prefs?.app_base_url) {
      setWebhookResult('❌ ابتدا app_base_url را ذخیره کنید');
      return;
    }
    setWebhookSetting(true);
    setWebhookResult('');
    try {
      const backendUrl = API_BASE.replace(/\/$/, '');
      const webhookUrl = `${backendUrl}/api/notifications/telegram/webhook`;
      const res = await fetch(`${API_BASE}/api/notifications/telegram/set-webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl }),
      });
      const data = await res.json();
      if (data.ok) {
        setWebhookResult(`✅ webhook با موفقیت ست شد:\n${webhookUrl}`);
      } else {
        setWebhookResult(`❌ ${JSON.stringify(data.result || data, null, 2)}`);
      }
    } catch (e: any) {
      setWebhookResult(`❌ خطا: ${e.message}`);
    } finally {
      setWebhookSetting(false);
    }
  };

  const deleteWebhook = async () => {
    setWebhookSetting(true);
    setWebhookResult('');
    try {
      const res = await fetch(`${API_BASE}/api/notifications/telegram/delete-webhook`, { method: 'POST' });
      const data = await res.json();
      setWebhookResult(data.ok ? '✅ webhook حذف شد' : `❌ ${JSON.stringify(data, null, 2)}`);
    } catch (e: any) {
      setWebhookResult(`❌ خطا: ${e.message}`);
    } finally {
      setWebhookSetting(false);
    }
  };

  const sendTestEvent = async (event: string) => {
    setTesting(`event:${event}`);
    setTestResult('');
    try {
      const meta = status?.events_registry?.[event];
      const res = await fetch(`${API_BASE}/api/notifications/notify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event,
          message: `${meta?.icon || ''} *تست رویداد*: ${meta?.label || event}\n📁 \`example/test-project\`\n🔖 priority: *medium*\n\n💬 این یک پیام نمونه برای آزمایش رویداد \`${event}\` است.`,
          subject: `Test: ${meta?.label || event}`,
          priority: 'medium',
          project_name: 'example/test-project',
        }),
      });
      const data = await res.json();
      const lines = (data.results || []).map((r: any) =>
        r.ok ? `✅ ${r.channel}: ارسال شد` : `❌ ${r.channel}: ${r.error || 'failed'}`
      );
      setTestResult(lines.join('\n') || 'event disabled یا کانالی آماده نیست');
    } catch (e: any) {
      setTestResult(`خطا: ${e.message}`);
    } finally {
      setTesting(null);
    }
  };

  const setAllEvents = (enabled: boolean) => {
    if (!status) return;
    const events: Record<string, boolean> = {};
    Object.keys(status.events_registry).forEach(k => { events[k] = enabled; });
    updatePrefs({ events });
  };

  const setAllSounds = (sound: boolean) => {
    if (!status) return;
    const soundMap: Record<string, boolean> = {};
    Object.keys(status.events_registry).forEach(k => { soundMap[k] = sound; });
    updatePrefs({ sound: soundMap });
  };

  if (loading) {
    return <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 text-center text-gray-400">در حال بارگذاری...</div>;
  }
  if (!status) {
    return <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 text-red-500">{error || 'data در دسترس نیست'}</div>;
  }

  const tg = status.channels.telegram;
  const em = status.channels.email;

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
          ❌ {error}
        </div>
      )}

      {/* راهنمای کلی */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4 text-sm">
        <h3 className="font-bold mb-2 text-blue-800 dark:text-blue-200">🔔 سیستم نوتیفیکیشن</h3>
        <p className="text-gray-700 dark:text-gray-200 leading-relaxed">
          credentials (token‌ها و SMTP) از <b>environment variables</b> سرور خوانده می‌شوند.
          اینجا کنترل می‌کنید کدام رویداد notify شود، با صدا یا silent، با چه ضمیمه‌ای (هشتگ/دکمه‌ها).
        </p>
      </div>

      {/* وضعیت کانال‌ها */}
      <div className="grid md:grid-cols-2 gap-3">
        {/* Telegram */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-lg flex items-center gap-2 dark:text-white">
              <span>📨</span> Telegram
            </h3>
            <label className="flex items-center gap-1 text-sm dark:text-gray-200">
              <input
                type="checkbox"
                checked={tg.enabled_pref}
                disabled={saving}
                onChange={(e) =>
                  updatePrefs({ channels: { telegram: { enabled: e.target.checked } } })
                }
              />
              فعال
            </label>
          </div>
          <div className="text-xs mb-3">
            {tg.configured_via_env ? (
              <span className="text-green-600 dark:text-green-400">✅ env پیکربندی‌شده</span>
            ) : (
              <span className="text-amber-600 dark:text-amber-400">⚠️ TELEGRAM_BOT_TOKEN/CHAT_ID نیست</span>
            )}
          </div>
          <button
            onClick={() => test('telegram')}
            disabled={!tg.ready || testing === 'telegram'}
            className="w-full px-3 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 disabled:opacity-50 text-sm"
          >
            {testing === 'telegram' ? '⏳ ارسال…' : '🚀 تست Telegram'}
          </button>
        </div>

        {/* Email */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-lg flex items-center gap-2 dark:text-white">
              <span>📧</span> Email
            </h3>
            <label className="flex items-center gap-1 text-sm dark:text-gray-200">
              <input
                type="checkbox"
                checked={em.enabled_pref}
                disabled={saving}
                onChange={(e) =>
                  updatePrefs({ channels: { email: { enabled: e.target.checked } } })
                }
              />
              فعال
            </label>
          </div>
          <div className="text-xs mb-3">
            {em.configured_via_env ? (
              <span className="text-green-600 dark:text-green-400">✅ SMTP پیکربندی‌شده</span>
            ) : (
              <span className="text-amber-600 dark:text-amber-400">⚠️ SMTP credentials کامل نیست</span>
            )}
          </div>
          <button
            onClick={() => test('email')}
            disabled={!em.ready || testing === 'email'}
            className="w-full px-3 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 disabled:opacity-50 text-sm"
          >
            {testing === 'email' ? '⏳ ارسال…' : '🚀 تست Email'}
          </button>
        </div>
      </div>

      {testResult && (
        <pre className="bg-gray-50 dark:bg-gray-900 dark:text-gray-200 p-3 rounded text-xs whitespace-pre-wrap border dark:border-gray-700">
{testResult}
        </pre>
      )}

      {/* تنظیمات عمومی پیام */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <h3 className="font-bold text-lg mb-3 dark:text-white">⚙️ تنظیمات عمومی پیام</h3>

        <label className="block mb-3">
          <span className="block text-sm font-medium mb-1 dark:text-gray-200">آدرس پنل (app_base_url)</span>
          <div className="flex gap-2">
            <input
              type="url"
              value={appUrlDraft}
              onChange={e => setAppUrlDraft(e.target.value)}
              placeholder="https://ai-creator-frontend.onrender.com"
              className="flex-1 p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 text-sm"
            />
            <button
              onClick={() => updatePrefs({ app_base_url: appUrlDraft })}
              disabled={saving || appUrlDraft === status.prefs.app_base_url}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 text-sm"
            >
              ذخیره
            </button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            برای ساخت لینک‌های inline keyboard (دکمه‌های زیر پیام) و command‌های ربات.
            مثلاً: <code>https://ai-creator-frontend.onrender.com</code>
          </p>
        </label>

        <div className="grid sm:grid-cols-2 gap-2 mt-3">
          <label className="flex items-start gap-2 p-2 bg-gray-50 dark:bg-gray-700/30 rounded">
            <input
              type="checkbox"
              checked={status.prefs.include_hashtags}
              disabled={saving}
              onChange={(e) => updatePrefs({ include_hashtags: e.target.checked })}
              className="mt-0.5"
            />
            <div className="text-sm">
              <div className="font-medium dark:text-gray-100">هشتگ خودکار</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                #verify_done #high #project — برای جستجوی سریع در Telegram
              </div>
            </div>
          </label>
          <label className="flex items-start gap-2 p-2 bg-gray-50 dark:bg-gray-700/30 rounded">
            <input
              type="checkbox"
              checked={status.prefs.include_inline_buttons}
              disabled={saving}
              onChange={(e) => updatePrefs({ include_inline_buttons: e.target.checked })}
              className="mt-0.5"
            />
            <div className="text-sm">
              <div className="font-medium dark:text-gray-100">دکمه‌های زیر پیام</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                inline keyboard با لینک به پنل (نیاز به app_base_url)
              </div>
            </div>
          </label>
        </div>

        <div className="mt-3 pt-3 border-t dark:border-gray-700">
          <label className="block">
            <span className="block text-sm font-medium mb-1 dark:text-gray-200">حداقل اولویت</span>
            <select
              value={status.prefs.min_priority}
              disabled={saving}
              onChange={(e) => updatePrefs({ min_priority: e.target.value })}
              className="w-full max-w-xs p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
            >
              <option value="low">low — همه چیز notify شود</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical — فقط بحرانی</option>
            </select>
          </label>
        </div>
      </div>

      {/* رویدادها */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h3 className="font-bold text-lg dark:text-white">📋 رویدادها</h3>
          <div className="flex gap-2 flex-wrap text-xs">
            <button onClick={() => setAllEvents(true)} disabled={saving}
              className="px-2 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 rounded hover:bg-green-200">
              ✅ همه روشن
            </button>
            <button onClick={() => setAllEvents(false)} disabled={saving}
              className="px-2 py-1 bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-200">
              ⬜ همه خاموش
            </button>
            <button onClick={() => setAllSounds(true)} disabled={saving}
              className="px-2 py-1 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 rounded hover:bg-amber-200">
              🔊 همه با صدا
            </button>
            <button onClick={() => setAllSounds(false)} disabled={saving}
              className="px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded hover:bg-blue-200">
              🔇 همه silent
            </button>
          </div>
        </div>

        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          برای هر رویداد دو کلید: <b>فعال</b> (آیا notify شود) و <b>صدا</b> (آیا با صدا یا silent).
          روی 🧪 کلیک کنید تا پیام نمونه برای همان رویداد ارسال شود.
        </p>

        {EVENT_GROUPS.map(group => (
          <div key={group.title} className="mb-4">
            <h4 className="font-semibold text-sm mb-2 text-gray-700 dark:text-gray-200 flex items-center gap-2">
              <span>{group.icon}</span> {group.title}
            </h4>
            <div className="space-y-1">
              {group.keys.map(key => {
                const meta = status.events_registry[key];
                if (!meta) return null;
                const enabled = !!status.prefs.events[key];
                const sound = !!status.prefs.sound[key];
                return (
                  <div key={key}
                    className="flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-700/30 rounded">
                    <label className="flex items-center gap-2 flex-1 cursor-pointer min-w-0">
                      <input
                        type="checkbox"
                        checked={enabled}
                        disabled={saving}
                        onChange={(e) => updatePrefs({ events: { [key]: e.target.checked } })}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium dark:text-gray-100 text-sm truncate">{meta.label}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{meta.help}</div>
                      </div>
                    </label>
                    <label className="flex items-center gap-1 text-xs px-2 py-1 rounded cursor-pointer"
                      title={sound ? 'با صدا' : 'silent (بی‌صدا)'}>
                      <input
                        type="checkbox"
                        checked={sound}
                        disabled={saving || !enabled}
                        onChange={(e) => updatePrefs({ sound: { [key]: e.target.checked } })}
                      />
                      <span className={sound ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400'}>
                        {sound ? '🔊' : '🔇'}
                      </span>
                    </label>
                    <button
                      onClick={() => sendTestEvent(key)}
                      disabled={!enabled || testing === `event:${key}`}
                      title="ارسال پیام نمونه برای این رویداد"
                      className="px-2 py-1 text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 rounded hover:bg-purple-200 disabled:opacity-30"
                    >
                      {testing === `event:${key}` ? '⏳' : '🧪'}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Webhook setup */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <h3 className="font-bold text-lg mb-2 dark:text-white">🔗 ربات Telegram (commands)</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
          برای فعال کردن دستورات <code>/menu</code>, <code>/status</code>, <code>/start</code> در ربات،
          باید webhook ست شود. این یک‌بار کافی است.
        </p>
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3 text-xs mb-3">
          ⚠️ webhook نیاز دارد که <code>NEXT_PUBLIC_API_URL</code> یک آدرس HTTPS عمومی باشد
          (مثلاً <code>https://ai-creator-backend.onrender.com</code>).
          آدرس فعلی: <code className="bg-white dark:bg-gray-900 px-1 rounded">{API_BASE}</code>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={setWebhook}
            disabled={webhookSetting || !tg.configured_via_env}
            title={!tg.configured_via_env ? 'ابتدا TELEGRAM_BOT_TOKEN را در env ست کنید' : ''}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            {webhookSetting ? '⏳ در حال…' : '🔗 ست کردن webhook'}
          </button>
          <button
            onClick={deleteWebhook}
            disabled={webhookSetting || !tg.configured_via_env}
            className="px-4 py-2 bg-gray-300 dark:bg-gray-700 dark:text-white rounded-lg hover:bg-gray-400 disabled:opacity-50 text-sm"
          >
            🗑 حذف webhook
          </button>
        </div>
        {webhookResult && (
          <pre className="mt-3 text-xs bg-gray-50 dark:bg-gray-900 dark:text-gray-200 p-3 rounded whitespace-pre-wrap border dark:border-gray-700">
{webhookResult}
          </pre>
        )}
        <div className="mt-3 text-xs text-gray-600 dark:text-gray-300">
          <b>پس از ست شدن webhook</b>، در chat ربات این دستورات کار می‌کنند:
          <ul className="list-disc list-inside mt-1 space-y-0.5">
            <li><code>/start</code> یا <code>/help</code> — معرفی + منو</li>
            <li><code>/menu</code> — منوی دکمه‌ای دسترسی به همهٔ صفحات پنل</li>
            <li><code>/status</code> — وضعیت سیستم نوتیفیکیشن</li>
          </ul>
        </div>
      </div>

      {/* راهنمای env vars */}
      <details className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-5 text-sm">
        <summary className="cursor-pointer font-bold text-amber-900 dark:text-amber-200">
          📝 راهنمای متغیرهای محیطی (env vars)
        </summary>
        <div className="mt-3 space-y-3">
          <div>
            <h4 className="font-semibold mb-1 text-amber-800 dark:text-amber-300">📨 Telegram</h4>
            <pre className="bg-white dark:bg-gray-900 p-3 rounded text-xs border dark:border-gray-700 dark:text-gray-200">
{`TELEGRAM_BOT_TOKEN=123456:ABC-DEF...   # از @BotFather
TELEGRAM_CHAT_ID=123456789             # از @userinfobot`}
            </pre>
          </div>
          <div>
            <h4 className="font-semibold mb-1 text-amber-800 dark:text-amber-300">📧 Email (SMTP)</h4>
            <pre className="bg-white dark:bg-gray-900 p-3 rounded text-xs border dark:border-gray-700 dark:text-gray-200">
{`SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
NOTIFICATION_EMAIL_FROM=you@gmail.com
NOTIFICATION_EMAIL_TO=destination@example.com`}
            </pre>
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-300">
            برای Render: Dashboard → سرویس backend → Environment → Add Variable.
            پس از ذخیره، Render خودکار redeploy می‌کند.
          </div>
        </div>
      </details>
    </div>
  );
}
