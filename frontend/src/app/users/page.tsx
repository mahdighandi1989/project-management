'use client'
// «کاربران» — who signed in with Google, and who may enter. Owner only (the
// server refuses anyone else). Owners listed in ADMIN_EMAILS on Render are fixed.
import React, { useCallback, useEffect, useState } from 'react'
import { apiBase, useAuth, type AuthUser } from '@/lib/auth'

type Row = AuthUser & { created_at: string | null; last_login_at: string | null; login_count: number }
const STATUS: Record<string, [string, string]> = {
  approved: ['تأییدشده', 'bg-emerald-100 text-emerald-800'],
  pending: ['منتظرِ تأیید', 'bg-amber-100 text-amber-800'],
  blocked: ['مسدود', 'bg-red-100 text-red-800'],
}

export default function UsersPage() {
  const { role, enforced } = useAuth()
  const [rows, setRows] = useState<Row[]>([])
  const [owners, setOwners] = useState<string[]>([])
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${apiBase()}/api/auth/users`)
      const j = await r.json()
      if (!r.ok) throw new Error(j?.detail || `خطا (${r.status})`)
      setRows(j.users); setOwners(j.owners_from_env || []); setErr('')
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
  }, [])
  useEffect(() => { void load() }, [load])

  const patch = async (id: number, body: Record<string, unknown>) => {
    const r = await fetch(`${apiBase()}/api/auth/users/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    })
    const j = await r.json().catch(() => ({}))
    if (!r.ok) setErr(j?.detail || `خطا (${r.status})`)
    await load()
  }

  return (
    <div dir="rtl" className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">کاربران</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        هر کس با گوگل وارد شود این‌جا ثبت می‌شود؛ جز مالکان (متغیرِ ADMIN_EMAILS روی Render) همه تا تأییدِ تو «منتظر» می‌مانند.
        {!enforced && ' — ورود هنوز اجباری نیست چون ADMIN_EMAILS روی سرور تنظیم نشده است.'}
      </p>
      {role !== 'owner' && enforced && <div className="text-sm text-red-600">این صفحه فقط برای مالک است.</div>}
      {err && <div className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{err}</div>}
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
            <tr><th className="p-2 text-right">حساب</th><th className="p-2 text-right">نقش</th><th className="p-2 text-right">وضعیت</th>
              <th className="p-2 text-right">آخرین ورود</th><th className="p-2" /></tr>
          </thead>
          <tbody>
            {rows.map((u) => {
              const fixed = owners.includes(u.email)
              const [label, cls] = STATUS[u.status] || [u.status, '']
              return (
                <tr key={u.id} className="border-t border-gray-100 dark:border-gray-700">
                  <td className="p-2"><div className="font-semibold">{u.name || '—'}</div><div className="text-xs text-gray-500" dir="ltr">{u.email}</div></td>
                  <td className="p-2">{u.role === 'owner' ? 'مالک' : 'کاربر'}{fixed && <span className="mr-1 text-[10px] text-gray-400">(ثابت)</span>}</td>
                  <td className="p-2"><span className={`rounded px-2 py-0.5 text-xs ${cls}`}>{label}</span></td>
                  <td className="p-2 text-xs">{u.last_login_at ? new Date(u.last_login_at).toLocaleString('fa-IR') : '—'}</td>
                  <td className="p-2 text-left text-xs">
                    {!fixed && u.status !== 'approved' && <button onClick={() => void patch(u.id, { status: 'approved' })} className="ml-2 text-emerald-700 hover:underline">تأیید</button>}
                    {!fixed && u.status !== 'blocked' && <button onClick={() => void patch(u.id, { status: 'blocked' })} className="ml-2 text-red-600 hover:underline">مسدود</button>}
                    {!fixed && u.status === 'approved' && <button onClick={() => void patch(u.id, { role: u.role === 'owner' ? 'member' : 'owner' })} className="ml-2 text-blue-600 hover:underline">{u.role === 'owner' ? 'کاربرِ عادی' : 'مالک کن'}</button>}
                    <button onClick={() => void patch(u.id, { revoke_sessions: true })} className="text-gray-600 hover:underline">بستنِ نشست‌ها</button>
                  </td>
                </tr>
              )
            })}
            {!rows.length && <tr><td colSpan={5} className="p-6 text-center text-gray-500">هنوز کسی وارد نشده است.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
