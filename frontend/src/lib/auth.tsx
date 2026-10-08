'use client'
// Sign-in with Google — «بدون لاگین چیزی نشون نده» (the owner, 2026-10-08).
// Modelled on Detective-1's login (Google Identity Services button → the server
// verifies the ID token → this app's own session token).
//
// The app has hundreds of API calls written as plain `fetch(...)`, axios, and a
// few EventSources, all to the backend's absolute URL. Rather than edit every one,
// this installs ONE interceptor at the edge: any request to the backend gets the
// session's `Authorization` header (EventSource cannot send headers, so it gets
// `?access_token=` — the server accepts that on GET only). A 401 from the backend
// ends the session and brings the login screen back.
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

const TOKEN_KEY = 'pm.auth.token'

export type AuthUser = { id: number; email: string; name: string; picture: string; role: string; status: string }
type Ctx = { user: AuthUser | null; role: string; enforced: boolean; logout: () => void }
const AuthCtx = createContext<Ctx>({ user: null, role: '', enforced: false, logout: () => undefined })
export const useAuth = () => useContext(AuthCtx)

export function apiBase(): string {
  const w = typeof window !== 'undefined'
    ? (window as unknown as { __NEXT_PUBLIC_API_URL__?: string }).__NEXT_PUBLIC_API_URL__ : undefined
  return (process.env.NEXT_PUBLIC_API_URL || w || 'http://localhost:8000').replace(/\/+$/, '')
}

export function getToken(): string {
  try { return localStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
}

/** For <img src> / download links that cannot carry a header. */
export function withToken(url: string): string {
  const t = getToken()
  if (!t) return url
  return `${url}${url.includes('?') ? '&' : '?'}access_token=${encodeURIComponent(t)}`
}

function isBackend(url: string): boolean {
  try {
    const u = new URL(url, window.location.href)
    const b = new URL(apiBase())
    return u.origin === b.origin || (u.origin === window.location.origin && u.pathname.startsWith('/api/'))
  } catch { return false }
}

const UNAUTH = 'pm:auth-401'
let installed = false

function installInterceptors() {
  if (installed || typeof window === 'undefined') return
  installed = true
  const origFetch = window.fetch.bind(window)
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const t = getToken()
    if (t && isBackend(url)) {
      const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined))
      if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${t}`)
      init = { ...(init || {}), headers }
    }
    const res = await origFetch(input as RequestInfo, init)
    if (res.status === 401 && isBackend(url) && !url.includes('/api/auth/')) {
      window.dispatchEvent(new CustomEvent(UNAUTH))
    }
    return res
  }
  // axios (and any XHR) — patch at the XHR level so every axios instance is covered
  const open = XMLHttpRequest.prototype.open
  const send = XMLHttpRequest.prototype.send
  XMLHttpRequest.prototype.open = function (this: XMLHttpRequest & { __pmUrl?: string }, ...args: unknown[]) {
    this.__pmUrl = String(args[1] || '')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (open as any).apply(this, args)
  } as typeof XMLHttpRequest.prototype.open
  XMLHttpRequest.prototype.send = function (this: XMLHttpRequest & { __pmUrl?: string }, body?: Document | XMLHttpRequestBodyInit | null) {
    const t = getToken()
    if (t && this.__pmUrl && isBackend(this.__pmUrl)) {
      try { this.setRequestHeader('Authorization', `Bearer ${t}`) } catch { /* already set */ }
      this.addEventListener('load', () => {
        if (this.status === 401 && !String(this.__pmUrl).includes('/api/auth/')) window.dispatchEvent(new CustomEvent(UNAUTH))
      })
    }
    return send.call(this, body)
  }
  const ES = window.EventSource
  if (ES) {
    const Patched = function (url: string | URL, conf?: EventSourceInit) {
      const s = String(url)
      return new ES(isBackend(s) ? withToken(s) : s, conf)
    } as unknown as typeof EventSource
    Object.assign(Patched, { CONNECTING: ES.CONNECTING, OPEN: ES.OPEN, CLOSED: ES.CLOSED })
    Patched.prototype = ES.prototype
    window.EventSource = Patched
  }
}

// ---------------------------------------------------------------------------
type GoogleId = {
  initialize: (o: Record<string, unknown>) => void
  renderButton: (el: HTMLElement, o: Record<string, unknown>) => void
}
const gsi = (): GoogleId | undefined =>
  (window as unknown as { google?: { accounts?: { id?: GoogleId } } }).google?.accounts?.id

function loadGis(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (gsi()) return resolve()
    const s = document.createElement('script')
    s.src = 'https://accounts.google.com/gsi/client'
    s.async = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('load'))
    document.head.appendChild(s)
  })
}

function LoginScreen({ clientId, onToken, note }: { clientId: string | null; onToken: (t: string) => void; note: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [err, setErr] = useState(note)
  const [busy, setBusy] = useState(false)
  useEffect(() => { setErr(note) }, [note])
  useEffect(() => {
    if (!clientId) return
    let dead = false
    loadGis().then(() => {
      const id = gsi()
      if (dead || !id || !ref.current) return
      id.initialize({
        client_id: clientId,
        ux_mode: 'popup',
        callback: async (resp: { credential?: string }) => {
          if (!resp?.credential) return
          setBusy(true)
          try {
            const r = await fetch(`${apiBase()}/api/auth/google`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ credential: resp.credential }),
            })
            const j = await r.json().catch(() => ({}))
            if (!r.ok) throw new Error(j?.detail || `خطا (${r.status})`)
            onToken(j.access_token)
          } catch (e) { setErr(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
        },
      })
      id.renderButton(ref.current, { theme: 'filled_blue', size: 'large', shape: 'pill', text: 'signin_with', locale: 'fa', width: 280 })
    }).catch(() => !dead && setErr('بارگذاریِ ورود با گوگل ناموفق بود'))
    return () => { dead = true }
  }, [clientId, onToken])
  return (
    <div dir="rtl" className="flex min-h-screen items-center justify-center bg-gray-50 p-4 dark:bg-gray-900">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-xl dark:bg-gray-800">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 text-2xl text-white">🤖</div>
        <h1 className="text-lg font-bold text-gray-900 dark:text-white">ورود به سامانه</h1>
        <p className="mb-6 mt-1 text-sm text-gray-500 dark:text-gray-400">برای دیدنِ برنامه با حسابِ گوگلِ خود وارد شوید.</p>
        {clientId ? <div className="flex justify-center"><div ref={ref} /></div>
          : <p className="text-sm text-red-600">ورود با گوگل روی سرور تنظیم نشده است (GOOGLE_CLIENT_ID).</p>}
        {busy && <p className="mt-3 text-xs text-gray-500">در حالِ ورود…</p>}
        {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
      </div>
    </div>
  )
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<'loading' | 'in' | 'out'>('loading')
  const [cfg, setCfg] = useState<{ google_client_id: string | null; auth_enforced: boolean }>({ google_client_id: null, auth_enforced: false })
  const [user, setUser] = useState<AuthUser | null>(null)
  const [role, setRole] = useState('')
  const [note, setNote] = useState('')

  const check = useCallback(async () => {
    installInterceptors()
    try {
      const c = await (await fetch(`${apiBase()}/api/auth/config`)).json()
      setCfg(c)
      const me = await (await fetch(`${apiBase()}/api/auth/me`)).json()
      setUser(me.user || null)
      setRole(me.role || '')
      if (!c.auth_enforced || me.authenticated) setState('in')
      else setState('out')
    } catch {
      // backend asleep/unreachable: show the app shell; its own calls will retry
      setState(getToken() ? 'in' : 'out')
    }
  }, [])

  useEffect(() => { void check() }, [check])
  useEffect(() => {
    const on = () => {
      try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
      setNote('نشستِ شما تمام شده — دوباره وارد شوید.')
      setState('out')
    }
    window.addEventListener(UNAUTH, on)
    return () => window.removeEventListener(UNAUTH, on)
  }, [])

  const onToken = useCallback((t: string) => {
    try { localStorage.setItem(TOKEN_KEY, t) } catch { /* ignore */ }
    setNote('')
    void check()
  }, [check])

  const logout = useCallback(() => {
    try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
    setUser(null)
    setState(cfg.auth_enforced ? 'out' : 'in')
  }, [cfg.auth_enforced])

  if (state === 'loading') {
    return <div className="flex min-h-screen items-center justify-center text-sm text-gray-400">…</div>
  }
  if (state === 'out') return <LoginScreen clientId={cfg.google_client_id} onToken={onToken} note={note} />
  return <AuthCtx.Provider value={{ user, role, enforced: cfg.auth_enforced, logout }}>{children}</AuthCtx.Provider>
}
