/**
 * PM-INS-0030 — a proxied project that sends the browser to its own sign-in page escapes the inspector proxy.
 *
 * Detective-1's guard does `location.href = "/login?next=" + location.pathname`. Inside the «بازرس ویژه» preview the
 * pathname is `/api/render/inspector/proxy/<project>/…`, and `/login` is relative — so the iframe left the proxy and
 * landed on AI Creator's own `/login`, where AI Creator's sign-in wall (no token inside the sandboxed iframe) showed
 * AI Creator's sign-in screen. The preview and «📸 عکس» showed our own sign-in page instead of Detective-1.
 * (`history` and `fetch` are already rewritten inside the proxied page; `location.href = …` cannot be patched there.)
 *
 * Here: an IFRAME navigation to a non-API path whose `next` / `redirect` / `returnTo` / `callbackUrl` points into the
 * proxy goes back into the SAME proxy, with that parameter made relative to the project. Nothing else is touched.
 */
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PROXY = '/api/render/inspector/proxy/';
const KEYS = ['next', 'redirect', 'redirect_to', 'redirectTo', 'returnTo', 'return_to', 'callbackUrl', 'from'];

export function middleware(req: NextRequest) {
  if (req.headers.get('sec-fetch-dest') !== 'iframe') return NextResponse.next();
  const url = req.nextUrl;
  for (const k of KEYS) {
    const v = url.searchParams.get(k);
    if (!v || !v.startsWith(PROXY)) continue;
    const rest = v.slice(PROXY.length);                    // "<project>/~pt~<ticket>/page?x" or "<project>/page"
    const slash = rest.indexOf('/');
    const project = slash === -1 ? rest : rest.slice(0, slash);
    if (!/^[\w.-]+$/.test(project)) return NextResponse.next();
    let inner = slash === -1 ? '/' : rest.slice(slash);    // "/~pt~…/page" or "/page"
    let ticket = '';
    const t = inner.match(/^\/~pt~[^/]+/);
    if (t) { ticket = t[0]; inner = inner.slice(t[0].length) || '/'; }
    const params = new URLSearchParams(url.search);
    params.set(k, inner);                                  // the project's own path, not the proxy's
    const target = `${PROXY}${project}${ticket}${url.pathname}?${params.toString()}`;
    return NextResponse.redirect(new URL(target, req.url), 307);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api/|_next/|favicon).*)'],
};
