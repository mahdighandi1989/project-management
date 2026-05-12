'use client';

/**
 * ExtractionDefaultPicker — انتخاب «مدل پیش‌فرض extraction» در /models
 *
 * این کامپوننت روی صفحهٔ /models نمایش داده می‌شود تا کاربر مدل بصری
 * پیش‌فرض برای استخراج فایل پیوست تسک‌ها را داینامیک عوض کند.
 *
 * اگر کاربر تنظیم نکرده باشد، hard-coded default (gemini-2.5-flash)
 * استفاده می‌شود.
 */

import { useEffect, useState } from 'react';

interface Candidate {
  id: string;
  name: string;
  provider: string;
  priority: number;
  enabled: boolean;
  capabilities: string[];
}

interface Data {
  user_pick: string | null;
  effective_id: string;
  effective_name: string;
  hard_coded_default: string;
  candidates: Candidate[];
}

interface Props {
  apiBase: string;
}

export default function ExtractionDefaultPicker({ apiBase }: Props) {
  const [data, setData] = useState<Data | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const reload = async () => {
    try {
      setLoading(true);
      const r = await fetch(`${apiBase}/api/oversight/models/extraction-default`);
      if (r.ok) {
        const d = await r.json();
        setData(d);
      }
    } catch (e: any) {
      setMsg(`❌ ${e?.message || e}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
  }, []);

  const save = async (modelId: string | null) => {
    setSaving(true);
    setMsg(null);
    try {
      const r = await fetch(`${apiBase}/api/oversight/models/extraction-default`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        setMsg(`❌ ${e.detail || 'ذخیره ناموفق'}`);
      } else {
        setMsg('✅ تنظیمات ذخیره شد');
        await reload();
        setTimeout(() => setMsg(null), 3000);
      }
    } catch (e: any) {
      setMsg(`❌ ${e?.message || e}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading)
    return <div className="text-xs text-gray-500 dark:text-gray-400 p-3">⏳ بارگذاری...</div>;
  if (!data) return null;

  return (
    <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-4 mb-4">
      <h3 className="font-bold text-sm mb-1 text-indigo-800 dark:text-indigo-200">
        🎯 مدل پیش‌فرض برای استخراج فایل پیوست تسک‌ها
      </h3>
      <p className="text-xs text-indigo-700 dark:text-indigo-300 mb-3">
        وقتی فایلی به تسک پیوست می‌کنید، این مدل برای استخراج متن (PDF/Word/Excel/تصویر/صوت/ویدئو)
        استفاده می‌شود. می‌توانید هر مدل multimodal را انتخاب کنید. پیش‌فرض سیستم:
        <code className="ml-1 bg-white dark:bg-gray-700 px-1 rounded">{data.hard_coded_default}</code>
      </p>
      <div className="text-xs mb-2">
        <span className="text-gray-600 dark:text-gray-400">فعلی: </span>
        <b className="text-indigo-900 dark:text-indigo-100">{data.effective_name}</b>
        <code className="text-[10px] ml-1 text-gray-500">({data.effective_id})</code>
        {data.user_pick === null && (
          <span className="text-[10px] text-gray-400 ml-2">(از پیش‌فرض سیستم)</span>
        )}
      </div>
      <select
        value={data.user_pick || ''}
        onChange={(e) => save(e.target.value || null)}
        disabled={saving}
        className="w-full text-xs p-2 border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
      >
        <option value="">— از پیش‌فرض سیستم استفاده کن ({data.hard_coded_default}) —</option>
        {data.candidates.map((c) => (
          <option key={c.id} value={c.id} disabled={!c.enabled}>
            {c.enabled ? '✅' : '❌'} {c.name} ({c.provider} · priority {c.priority})
            {c.id === data.hard_coded_default ? ' ⭐' : ''}
          </option>
        ))}
      </select>
      {msg && <div className="mt-2 text-xs">{msg}</div>}
      <div className="mt-2 text-[10px] text-gray-500 dark:text-gray-400">
        💡 وقتی مدل انتخاب‌شده disabled باشد و فایلی پیوست شود، سیستم خودکار آن را
        موقتاً فعال می‌کند، کار را انجام می‌دهد، و دوباره غیرفعال می‌کند — با
        اطلاع به تلگرام.
      </div>
    </div>
  );
}
