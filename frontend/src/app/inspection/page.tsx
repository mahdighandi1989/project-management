'use client'
// «نظارت و سرکشی» — the owner's inspection board, modelled on the sibling
// projects ALLIN1 and Detective-1 (read-only references).
//
//   برگه‌ها            — every sheet, its conversation, files, colour by state
//   درخواست‌های عمومی  — requests that point at no place on screen (as in ALLIN1)
//   نقشهٔ سامانه       — every page and sub-page, with measured coordinates
//   بایگانی           — binders of ticked sheets, filed by the supervisor's rounds
//   فضای ذخیره‌سازی    — the project's Google Drive folder (no bytes kept here)
//   روتین‌ها           — the two Claude Code Routines and when they come next
import React, { Suspense, useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Board from '@/components/inspection/Board'
import GeneralRequest from '@/components/inspection/GeneralRequest'
import SystemMap from '@/components/inspection/SystemMap'
import { Binders, Routines, StoragePanel } from '@/components/inspection/Panels'
import { useInspection } from '@/lib/inspection/provider'

const TABS = [
  { key: 'board', label: 'برگه‌ها' },
  { key: 'general', label: 'درخواست‌های عمومی' },
  { key: 'map', label: 'نقشهٔ سامانه' },
  { key: 'archive', label: 'بایگانی' },
  { key: 'storage', label: 'فضای ذخیره‌سازی' },
  { key: 'routines', label: 'روتین‌ها' },
] as const

const fa = (n: number) => String(n).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[+d])

function InspectionPage() {
  const params = useSearchParams()
  const router = useRouter()
  const ins = useInspection()
  const tab = (TABS.find((t) => t.key === params.get('tab'))?.key || 'board') as (typeof TABS)[number]['key']
  const [counts, setCounts] = useState({ open: 0, general: 0, urgent: 0 })
  const [generalOpen, setGeneralOpen] = useState(false)
  const [boardKey, setBoardKey] = useState(0)

  const go = useCallback((key: string) => {
    router.replace(key === 'board' ? '/inspection' : `/inspection?tab=${key}`)
  }, [router])
  useEffect(() => { setGeneralOpen(false) }, [tab])

  return (
    <div dir="rtl" className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">نظارت و سرکشی</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            ایراد و پیشنهادی که خودت روی صفحه‌ها ثبت کرده‌ای و آنچه ناظر زیرش نوشته. برای گزارشِ تازه «📝 ثبتِ گزارش» را
            در منو روشن کن و دورِ همان چیز کادر بکش؛ برای چیزی که جای مشخصی ندارد «درخواستِ عمومی».
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setGeneralOpen((o) => !o)} type="button"
            className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-900">
            ＋ درخواستِ عمومی
          </button>
          {ins && (
            <button onClick={() => ins.setActive(!ins.active)} type="button"
              className={`rounded-lg px-3 py-1.5 text-sm ${ins.active ? 'bg-amber-600 text-white' : 'border border-amber-400 text-amber-700 dark:text-amber-300'}`}>
              📝 {ins.active ? 'ثبتِ گزارش روشن است' : 'روشن‌کردنِ ثبتِ گزارش'}
            </button>
          )}
        </div>
      </div>

      {generalOpen && (
        <GeneralRequest onFiled={() => { setGeneralOpen(false); setBoardKey((k) => k + 1) }} />
      )}

      <div role="tablist" className="flex flex-wrap gap-1 border-b border-gray-200 dark:border-gray-700">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => go(t.key)}
            className={`-mb-px rounded-t-lg px-4 py-2 text-sm ${tab === t.key
              ? 'border border-b-white bg-white font-semibold text-gray-900 dark:border-gray-700 dark:border-b-gray-900 dark:bg-gray-900 dark:text-white'
              : 'text-gray-500 hover:text-gray-800 dark:text-gray-400'}`}>
            {t.label}
            {t.key === 'board' && counts.open > 0 && <span className="mr-1 rounded-full bg-amber-500 px-1.5 text-[10px] text-white">{fa(counts.open)}</span>}
            {t.key === 'general' && counts.general > 0 && <span className="mr-1 rounded-full bg-gray-700 px-1.5 text-[10px] text-white">{fa(counts.general)}</span>}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {tab === 'board' && <Board key={`b${boardKey}`} onCounts={setCounts} />}
        {tab === 'general' && (
          <div className="space-y-4">
            <GeneralRequest compact onFiled={() => setBoardKey((k) => k + 1)} />
            <Board key={`g${boardKey}`} kind="general" />
          </div>
        )}
        {tab === 'map' && <SystemMap />}
        {tab === 'archive' && <Binders />}
        {tab === 'storage' && <StoragePanel />}
        {tab === 'routines' && <Routines />}
      </div>
    </div>
  )
}

export default function Page() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-gray-500">…</div>}>
      <InspectionPage />
    </Suspense>
  )
}
