/**
 * The «بازرس ویژه» screen behind the login wall (owner plan item 12, 2026-11-15).
 *
 * The iframe beside the chat loads /api/render/inspector/proxy/{project}/… — a page load (and its scripts, CSS,
 * images) cannot carry the session's Authorization header, so since 2026-10-08 the screen showed the wall's 401.
 * The backend gives a signed-in user a short-lived ticket bound to ONE project; we keep it in a cookie whose
 * path is exactly that project's proxy prefix, so only those requests carry it (core/auth.preview_allowed).
 * Refreshed well before it expires, so a long session never falls back to the 401 page.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const timers: Record<string, ReturnType<typeof setTimeout>> = {};

export async function ensurePreviewTicket(projectId: string): Promise<boolean> {
  if (!projectId || typeof document === 'undefined') return false;
  try {
    const r = await fetch(`${API_BASE}/api/auth/preview-ticket`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId }),
    });
    if (!r.ok) return false;
    const t = await r.json();
    const secure = window.location.protocol === 'https:' ? '; secure' : '';
    document.cookie = `${t.cookie}=${t.ticket}; path=${t.path}; max-age=${t.expires_in}; samesite=strict${secure}`;
    clearTimeout(timers[projectId]);
    // renew at ~2/3 of the lifetime
    timers[projectId] = setTimeout(() => { ensurePreviewTicket(projectId); }, Math.max(60, t.expires_in * 0.66) * 1000);
    return true;
  } catch {
    return false;
  }
}
