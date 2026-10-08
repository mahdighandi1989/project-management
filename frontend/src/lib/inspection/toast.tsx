'use client'
// A tiny toast for «نظارت و سرکشی». The app has no toast library, and the board
// needs one sentence of feedback after every action (the sibling projects learned
// that silence after a click reads as «it did nothing»).
import React, { useEffect, useState } from 'react'

type Kind = 'success' | 'error' | 'info'
type Item = { id: number; kind: Kind; msg: React.ReactNode; until: number }

const EVT = 'pm:inspection-toast'
let seq = 0

function push(kind: Kind, msg: React.ReactNode, duration = 4500) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(EVT, { detail: { id: ++seq, kind, msg, until: Date.now() + duration } }))
}

export const toast = {
  success: (m: React.ReactNode, o?: { duration?: number }) => push('success', m, o?.duration),
  error: (m: React.ReactNode, o?: { duration?: number }) => push('error', m, o?.duration ?? 7000),
  info: (m: React.ReactNode, o?: { duration?: number }) => push('info', m, o?.duration),
}

const TONE: Record<Kind, string> = {
  success: 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:bg-emerald-900/80 dark:text-emerald-50',
  error: 'border-red-300 bg-red-50 text-red-900 dark:bg-red-900/80 dark:text-red-50',
  info: 'border-amber-300 bg-amber-50 text-amber-900 dark:bg-amber-900/80 dark:text-amber-50',
}

export function Toaster() {
  const [items, setItems] = useState<Item[]>([])
  useEffect(() => {
    const on = (e: Event) => setItems((prev) => [...prev.slice(-3), (e as CustomEvent<Item>).detail])
    window.addEventListener(EVT, on)
    const t = window.setInterval(() => setItems((prev) => prev.filter((i) => i.until > Date.now())), 500)
    return () => { window.removeEventListener(EVT, on); window.clearInterval(t) }
  }, [])
  if (!items.length) return null
  return (
    <div dir="rtl" data-inspection-layer="1"
      className="fixed bottom-20 left-1/2 z-[120] flex w-[min(92vw,34rem)] -translate-x-1/2 flex-col gap-2">
      {items.map((i) => (
        <div key={i.id} className={`rounded-xl border px-4 py-2.5 text-sm shadow-lg ${TONE[i.kind]}`}
          onClick={() => setItems((prev) => prev.filter((x) => x.id !== i.id))}>
          {i.msg}
        </div>
      ))}
    </div>
  )
}
