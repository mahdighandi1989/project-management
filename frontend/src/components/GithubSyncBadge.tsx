'use client';
/**
 * (PM-INS-0014) وضعیتِ سینکِ خودکار با GitHub — «آخرین سینک: …»، «N از M فایل» با دلیل، و هشدارِ عقب‌افتادگی.
 * داده از `metadata.github_sync` که حلقهٔ `backend/app/services/github_autosync.py` می‌نویسد.
 */

type Report = {
  tree_total?: number; kept?: number; skipped_dir?: number; skipped_ext?: number;
  skipped_size?: number; capped?: number; budget?: number; failed?: number; truncated?: boolean;
};
export type GithubSync = {
  last_sync_at?: string; last_checked_at?: string; last_synced_sha?: string; head_sha?: string;
  behind?: boolean; error?: string | null; stored_files?: number; repo_files?: number; report?: Report;
  trigger?: string;
};

function ago(iso?: string): string {
  if (!iso) return '—';
  const t = Date.parse(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  if (Number.isNaN(t)) return iso;
  const m = Math.round((Date.now() - t) / 60000);
  if (m < 1) return 'همین الان';
  if (m < 60) return `${m} دقیقه پیش`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h} ساعت پیش`;
  return `${Math.round(h / 24)} روز پیش`;
}

/** دلیلِ هر فایلی که در نسخهٔ AI Creator نیست — صریح، نه پنهان */
export function skippedReasons(r?: Report): string[] {
  if (!r) return [];
  const out: string[] = [];
  if (r.skipped_ext) out.push(`${r.skipped_ext} باینری/تصویر/قفل`);
  if (r.skipped_dir) out.push(`${r.skipped_dir} در node_modules/dist/build/…`);
  if (r.skipped_size) out.push(`${r.skipped_size} بزرگ‌تر از ۵۰۰KB`);
  if (r.capped) out.push(`${r.capped} بیش از سقفِ تعداد`);
  if (r.budget) out.push(`${r.budget} بیش از سقفِ حجم`);
  if (r.failed) out.push(`${r.failed} دانلود ناموفق`);
  if (r.truncated) out.push('درختِ GitHub بریده بود');
  return out;
}

export default function GithubSyncBadge({ sync, compact = false }: { sync?: GithubSync | null; compact?: boolean }) {
  if (!sync || !sync.last_sync_at) {
    return (
      <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
        title="این پروژه هنوز با سینکِ خودکار همگام نشده — دورِ بعدیِ سینکِ خودکار چند دقیقهٔ دیگر">
        ⚠️ هنوز سینکِ خودکار نشده
      </span>
    );
  }
  const stale = !!sync.behind || !!sync.error;
  const reasons = skippedReasons(sync.report);
  const count = sync.repo_files != null ? `${sync.stored_files ?? '?'} از ${sync.repo_files} فایل` : `${sync.stored_files ?? '?'} فایل`;
  const tone = stale
    ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200'
    : 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200';
  const title = [
    `آخرین سینک: ${sync.last_sync_at}`,
    `آخرین بررسی: ${sync.last_checked_at || '—'}`,
    sync.last_synced_sha ? `کامیتِ سینک‌شده: ${sync.last_synced_sha.slice(0, 7)}` : '',
    sync.head_sha && sync.head_sha !== sync.last_synced_sha ? `آخرین کامیتِ GitHub: ${sync.head_sha.slice(0, 7)}` : '',
    reasons.length ? `نیامده: ${reasons.join('، ')}` : '',
    sync.error ? `خطا: ${sync.error}` : '',
  ].filter(Boolean).join('\n');
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${tone}`} title={title} data-testid="github-sync-badge">
      {stale ? '⚠️ عقب‌افتاده' : '🔄'} آخرین سینک: {ago(sync.last_sync_at)}
      {!compact && <> · {count}{reasons.length ? ` (نیامده: ${reasons.join('، ')})` : ''}</>}
      {!compact && sync.error ? ` · خطا: ${sync.error}` : ''}
    </span>
  );
}
