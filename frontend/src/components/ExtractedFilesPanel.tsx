'use client';

/**
 * ExtractedFilesPanel — نمایش فایل‌های پیوست + متن استخراج‌شده per task
 *
 * استفاده:
 *   <ExtractedFilesPanel taskId={t.id} apiBase={API_BASE} />
 *
 * - badge بالا با تعداد فایل‌ها
 * - per file: filename + status + total_segments + model_used
 * - collapsible per file → segments (با page/timestamp و text)
 * - دکمهٔ «📋 کپی متن این فایل» و «📋 کپی همه»
 * - search → highlight
 */

import { useEffect, useState, useMemo } from 'react';

interface ExtractionSegment {
  id: string;
  segment_index: number;
  segment_title: string;
  text: string;
  raw_excerpt: string;
  page_or_timestamp: string;
  model_used: string;
  status: string;
}

interface FileExtraction {
  id: string;
  task_id: string | null;
  session_id: string;
  file_order: number;
  original_filename: string;
  mime_type: string;
  total_segments: number;
  completed_segments: number;
  status: string;
  model_used: string;
  started_at: string;
  finished_at: string | null;
  error: string | null;
  full_text_cache?: string;
}

interface Props {
  taskId: string;
  apiBase: string;
}

function pickIcon(mime: string): string {
  if (mime.startsWith('image/')) return '🖼';
  if (mime.startsWith('video/')) return '🎬';
  if (mime.startsWith('audio/')) return '🎵';
  if (mime === 'application/pdf') return '📕';
  if (mime.includes('spreadsheet') || mime.includes('excel')) return '📊';
  if (mime.includes('word') || mime.includes('document')) return '📄';
  if (mime.startsWith('text/')) return '📝';
  return '📎';
}

function highlight(text: string, q: string): React.ReactNode {
  if (!q.trim()) return text;
  const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return parts.map((p, i) =>
    p.toLowerCase() === q.toLowerCase() ? (
      <mark key={i} className="bg-yellow-200 dark:bg-yellow-700">
        {p}
      </mark>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}

export default function ExtractedFilesPanel({ taskId, apiBase }: Props) {
  const [extractions, setExtractions] = useState<FileExtraction[] | null>(null);
  const [segmentsByExt, setSegmentsByExt] = useState<Record<string, ExtractionSegment[]>>({});
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${apiBase}/api/oversight/tasks/${encodeURIComponent(taskId)}/extractions`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        setExtractions(data.extractions || []);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [apiBase, taskId]);

  const toggleOpen = async (extId: string) => {
    const newOpen = new Set(openIds);
    if (newOpen.has(extId)) {
      newOpen.delete(extId);
    } else {
      newOpen.add(extId);
      if (!segmentsByExt[extId]) {
        try {
          const r = await fetch(
            `${apiBase}/api/oversight/extractions/${encodeURIComponent(extId)}/segments`,
          );
          if (r.ok) {
            const d = await r.json();
            setSegmentsByExt((prev) => ({ ...prev, [extId]: d.segments || [] }));
          }
        } catch {}
      }
    }
    setOpenIds(newOpen);
  };

  const copyFullText = async (extId: string, filename: string) => {
    try {
      const r = await fetch(
        `${apiBase}/api/oversight/extractions/${encodeURIComponent(extId)}/full-text`,
      );
      if (!r.ok) return;
      const d = await r.json();
      await navigator.clipboard.writeText(d.full_text || '');
      alert(`✅ متن کامل «${filename}» کپی شد (${(d.full_text || '').length} کاراکتر)`);
    } catch (e: any) {
      alert(`❌ خطا: ${e?.message || e}`);
    }
  };

  const copyAll = async () => {
    if (!extractions || extractions.length === 0) return;
    const allParts: string[] = [];
    for (const e of extractions.sort((a, b) => a.file_order - b.file_order)) {
      try {
        const r = await fetch(
          `${apiBase}/api/oversight/extractions/${encodeURIComponent(e.id)}/full-text`,
        );
        if (r.ok) {
          const d = await r.json();
          allParts.push(`# 📎 فایل #${e.file_order}: ${e.original_filename}\n\n${d.full_text || ''}`);
        }
      } catch {}
    }
    const all = allParts.join('\n\n---\n\n');
    try {
      await navigator.clipboard.writeText(all);
      alert(`✅ متن کامل ${extractions.length} فایل کپی شد (${all.length} کاراکتر)`);
    } catch (e: any) {
      alert(`❌ خطا: ${e?.message || e}`);
    }
  };

  if (loading)
    return <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">⏳ بارگذاری فایل‌های پیوست...</div>;
  if (error)
    return <div className="text-xs text-red-500 mt-2">⚠️ {error}</div>;
  if (!extractions || extractions.length === 0) return null;

  const totalSegments = extractions.reduce((a, e) => a + e.completed_segments, 0);

  return (
    <details className="mt-2 text-[11px] bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded p-2" open>
      <summary className="cursor-pointer font-semibold text-cyan-700 dark:text-cyan-300 flex items-center gap-2">
        📎 {extractions.length} فایل پیوست ({totalSegments} segment استخراج شد)
        <button
          onClick={(e) => {
            e.preventDefault();
            copyAll();
          }}
          className="ml-auto text-[10px] px-2 py-0.5 bg-cyan-500 text-white rounded hover:bg-cyan-600"
        >
          📋 کپی همه
        </button>
      </summary>
      <div className="mt-2">
        <input
          type="search"
          placeholder="🔍 جستجو در متن همهٔ فایل‌ها..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full text-[11px] p-1.5 border rounded dark:bg-gray-700 dark:border-gray-600 mb-2"
        />
        <ul className="space-y-2">
          {extractions
            .slice()
            .sort((a, b) => a.file_order - b.file_order)
            .map((e) => {
              const segs = segmentsByExt[e.id] || [];
              const statusEmoji =
                e.status === 'extracted'
                  ? '✅'
                  : e.status === 'extracting'
                  ? '⏳'
                  : e.status === 'failed'
                  ? '❌'
                  : '📦';
              return (
                <li key={e.id} className="border rounded bg-white dark:bg-gray-800 dark:border-gray-700">
                  <div
                    onClick={() => toggleOpen(e.id)}
                    className="flex items-center gap-2 p-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <span className="text-lg">{pickIcon(e.mime_type)}</span>
                    <span className="font-semibold">#{e.file_order}</span>
                    <span className="flex-1 truncate" title={e.original_filename}>
                      {e.original_filename}
                    </span>
                    <span className="text-[10px] text-gray-500">
                      {e.completed_segments}/{e.total_segments} segment
                    </span>
                    <span>{statusEmoji}</span>
                    <button
                      onClick={(ev) => {
                        ev.stopPropagation();
                        copyFullText(e.id, e.original_filename);
                      }}
                      className="text-[10px] px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 dark:text-white rounded hover:bg-gray-300"
                      title="کپی متن کامل این فایل"
                    >
                      📋
                    </button>
                    <span className="text-gray-400 text-xs">{openIds.has(e.id) ? '▾' : '▸'}</span>
                  </div>
                  {e.error && (
                    <div className="px-2 pb-2 text-red-600 dark:text-red-400 text-[10px]">⚠️ {e.error}</div>
                  )}
                  {openIds.has(e.id) && (
                    <div className="border-t dark:border-gray-700 px-2 py-2 space-y-2 max-h-96 overflow-y-auto">
                      {segs.length === 0 ? (
                        <div className="text-gray-500 text-[10px]">⏳ بارگذاری segments...</div>
                      ) : (
                        segs
                          .sort((a, b) => a.segment_index - b.segment_index)
                          .filter((s) => !search.trim() || s.text.toLowerCase().includes(search.toLowerCase()))
                          .map((s) => (
                            <div key={s.id} className="bg-gray-50 dark:bg-gray-900 p-2 rounded">
                              <div className="flex items-center gap-2 mb-1">
                                <b className="text-[11px]">
                                  #{s.segment_index} {s.segment_title}
                                </b>
                                {s.page_or_timestamp && (
                                  <span className="text-[10px] text-gray-500">
                                    ({s.page_or_timestamp})
                                  </span>
                                )}
                                <span className="text-[10px] text-gray-400 ml-auto">
                                  {s.model_used}
                                </span>
                              </div>
                              <pre className="whitespace-pre-wrap break-words text-[11px] text-gray-800 dark:text-gray-200 max-h-60 overflow-y-auto">
                                {highlight(s.text, search)}
                              </pre>
                            </div>
                          ))
                      )}
                    </div>
                  )}
                </li>
              );
            })}
        </ul>
      </div>
    </details>
  );
}
