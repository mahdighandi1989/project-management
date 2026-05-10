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
    channels: Record<string, { enabled: boolean }>;
    min_priority: 'low' | 'medium' | 'high' | 'critical';
  };
  channels: Record<string, ChannelStatus>;
};

const EVENT_LABELS: Record<string, { label: string; help: string }> = {
  verify_done: {
    label: 'پایان verify',
    help: 'پس از هر verify (done/partial/not_done) پیام ارسال می‌شود',
  },
  scan_done: {
    label: 'پایان Deep Scan',
    help: 'وقتی یک Deep Scan تمام می‌شود (با شمار یافته‌ها/تسک‌های جدید)',
  },
  task_failed: {
    label: 'تسک regressed',
    help: 'فقط وقتی verify status = regressed باشد (مشکل جدی)',
  },
  manual_test: {
    label: 'تست دستی',
    help: 'برای دکمهٔ «تست ارسال» — معمولاً همیشه روشن',
  },
};

export default function NotificationSettingsPanel() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string>('');
  const [error, setError] = useState<string>('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/notifications/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus(data);
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
      await load();
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
        r.ok ? `✅ ${r.channel}: ارسال شد` : `❌ ${r.channel}: ${r.error || 'failed'}`
      );
      setTestResult(lines.join('\n') || 'هیچ کانال آماده‌ای پیدا نشد');
    } catch (e: any) {
      setTestResult(`خطا: ${e.message}`);
    } finally {
      setTesting(null);
    }
  };

  if (loading) {
    return <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 text-center text-gray-400">در حال بارگذاری...</div>;
  }
  if (!status) {
    return <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 text-red-500">{error || 'data در دسترس نیست'}</div>;
  }

  const tg = status.channels.telegram;
  const em = status.channels.email;
  const events = status.prefs.events;

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
          credentials (token‌ها و SMTP) از <b>environment variables</b> سرور خوانده می‌شوند —
          نه اینجا. اینجا فقط کنترل می‌کنید کدام رویداد notify شود و کدام کانال فعال باشد.
          برای دیدن متغیرهای محیطی لازم، پایین صفحه را ببینید.
        </p>
      </div>

      {/* وضعیت Telegram */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-lg flex items-center gap-2 dark:text-white">
            <span>📨</span> Telegram
          </h3>
          <div className="flex items-center gap-2">
            {tg.configured_via_env ? (
              <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 rounded">
                env پیکربندی‌شده
              </span>
            ) : (
              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 rounded">
                env خالی
              </span>
            )}
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
        </div>
        <div className="text-xs text-gray-600 dark:text-gray-300 mb-2">
          {tg.ready
            ? '✅ آمادهٔ ارسال — credentials و enable هر دو ست شده‌اند'
            : tg.configured_via_env
              ? '⚠️ env تنظیم شده ولی فعال نیست'
              : '⚠️ TELEGRAM_BOT_TOKEN یا TELEGRAM_CHAT_ID در محیط سرور تنظیم نشده'}
        </div>
        <button
          onClick={() => test('telegram')}
          disabled={!tg.ready || testing === 'telegram'}
          className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 disabled:opacity-50 text-sm"
        >
          {testing === 'telegram' ? '⏳ ارسال…' : '🚀 تست ارسال به Telegram'}
        </button>
      </div>

      {/* وضعیت Email */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-lg flex items-center gap-2 dark:text-white">
            <span>📧</span> Email (SMTP)
          </h3>
          <div className="flex items-center gap-2">
            {em.configured_via_env ? (
              <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 rounded">
                env پیکربندی‌شده
              </span>
            ) : (
              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 rounded">
                env خالی
              </span>
            )}
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
        </div>
        <div className="text-xs text-gray-600 dark:text-gray-300 mb-2">
          {em.ready
            ? '✅ آمادهٔ ارسال'
            : em.configured_via_env
              ? '⚠️ env تنظیم شده ولی فعال نیست'
              : '⚠️ SMTP credentials کامل نیست (host/user/password/to لازم است)'}
        </div>
        <button
          onClick={() => test('email')}
          disabled={!em.ready || testing === 'email'}
          className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 disabled:opacity-50 text-sm"
        >
          {testing === 'email' ? '⏳ ارسال…' : '🚀 تست ارسال ایمیل'}
        </button>
      </div>

      {/* تست همگانی */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <h3 className="font-bold text-lg mb-2 dark:text-white">🧪 تست همگانی</h3>
        <p className="text-xs text-gray-600 dark:text-gray-300 mb-2">
          ارسال پیام تست به تمام کانال‌های ready — برای تأیید نهایی پیکربندی
        </p>
        <button
          onClick={() => test()}
          disabled={testing !== null}
          className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 text-sm"
        >
          {testing === 'all' ? '⏳ در حال ارسال…' : '🚀 تست به همه'}
        </button>
        {testResult && (
          <pre className="mt-3 text-xs bg-gray-50 dark:bg-gray-900 dark:text-gray-200 p-3 rounded whitespace-pre-wrap border dark:border-gray-700">
{testResult}
          </pre>
        )}
      </div>

      {/* کنترل رویدادها */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <h3 className="font-bold text-lg mb-3 dark:text-white">📋 رویدادها</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          فقط رویدادهای انتخاب‌شده باعث ارسال نوتیفیکیشن می‌شوند.
        </p>
        <div className="space-y-2">
          {Object.entries(EVENT_LABELS).map(([key, info]) => (
            <label key={key} className="flex items-start gap-3 p-2 hover:bg-gray-50 dark:hover:bg-gray-700/30 rounded cursor-pointer">
              <input
                type="checkbox"
                checked={!!events[key]}
                disabled={saving}
                onChange={(e) =>
                  updatePrefs({ events: { [key]: e.target.checked } })
                }
                className="mt-0.5"
              />
              <div className="flex-1">
                <div className="font-medium dark:text-gray-100">{info.label}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">{info.help}</div>
              </div>
            </label>
          ))}
        </div>

        <div className="mt-4 pt-3 border-t dark:border-gray-700">
          <label className="block">
            <span className="block text-sm font-medium mb-1 dark:text-gray-200">حداقل اولویت</span>
            <select
              value={status.prefs.min_priority}
              disabled={saving}
              onChange={(e) => updatePrefs({ min_priority: e.target.value })}
              className="w-full max-w-xs p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
            >
              <option value="low">low (همه چیز notify شود)</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical (فقط بحرانی)</option>
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              فقط تسک‌ها/یافته‌هایی با اولویت برابر یا بالاتر notify می‌شوند.
            </p>
          </label>
        </div>
      </div>

      {/* راهنمای env vars */}
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-5 text-sm">
        <h3 className="font-bold mb-3 text-amber-900 dark:text-amber-200">📝 متغیرهای محیطی لازم</h3>

        <div className="mb-4">
          <h4 className="font-semibold mb-1 text-amber-800 dark:text-amber-300">📨 Telegram</h4>
          <pre className="bg-white dark:bg-gray-900 p-3 rounded text-xs border dark:border-gray-700 dark:text-gray-200">
{`TELEGRAM_BOT_TOKEN=123456:ABC-DEF...   # از @BotFather
TELEGRAM_CHAT_ID=123456789             # از @userinfobot یا API`}
          </pre>
          <ol className="text-xs text-gray-700 dark:text-gray-300 mt-2 list-decimal list-inside space-y-0.5">
            <li>در Telegram به <code>@BotFather</code> پیام بدهید → <code>/newbot</code> → token دریافت کنید</li>
            <li>یک پیام به ربات خود بفرستید (هر چیزی) تا chat ساخته شود</li>
            <li>برای Chat ID: به <code>@userinfobot</code> پیام بدهید یا از URL زیر استفاده کنید:<br/>
              <code className="block mt-1 bg-white dark:bg-gray-900 p-1 rounded">https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</code></li>
          </ol>
        </div>

        <div>
          <h4 className="font-semibold mb-1 text-amber-800 dark:text-amber-300">📧 Email (SMTP)</h4>
          <pre className="bg-white dark:bg-gray-900 p-3 rounded text-xs border dark:border-gray-700 dark:text-gray-200">
{`SMTP_HOST=smtp.gmail.com
SMTP_PORT=587                          # 587 برای TLS، 465 برای SSL
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx       # برای Gmail: App Password
NOTIFICATION_EMAIL_FROM=you@gmail.com  # اختیاری (default: SMTP_USER)
NOTIFICATION_EMAIL_TO=destination@example.com`}
          </pre>
          <ul className="text-xs text-gray-700 dark:text-gray-300 mt-2 list-disc list-inside space-y-0.5">
            <li>برای Gmail: <b>2FA فعال کنید</b> سپس از <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" className="text-blue-600 underline">myaccount.google.com/apppasswords</a> یک App Password بسازید</li>
            <li>برای سایر providers (Outlook، Yandex، …): SMTP host و port مخصوص خودشان را دارند</li>
          </ul>
        </div>

        <div className="mt-4 p-3 bg-white dark:bg-gray-900 rounded border dark:border-gray-700 text-xs">
          <b className="dark:text-amber-300">📌 نکتهٔ deploy:</b> این متغیرها را در Render/Railway/Vercel در بخش
          Environment Variables ست کنید، سپس سرویس را restart کنید. تغییرات اینجا (toggleها)
          بدون restart اعمال می‌شوند.
        </div>
      </div>
    </div>
  );
}
