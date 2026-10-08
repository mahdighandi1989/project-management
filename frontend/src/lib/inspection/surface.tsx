'use client'
// «بتونه همهٔ صفحات و زیرصفحات و مختصاتِ دقیقِ همه‌جا … چه مواردی که الان هست و
// چه بعداً اضافه میشه رو بشناسه و ثبت کنه در یه قسمتی» — the owner, 2026-10-08.
//
// THE MAP OF THE APP, MEASURED — NOT WRITTEN BY HAND.
//
// Every time a screen settles, its map is taken: headings, tabs, sections,
// buttons, inputs and links, each with a VERIFIED selector (it re-queries to the
// same element, or it is not stored) and its rectangle in document pixels. The
// map is sent to /api/inspection/surfaces, which keeps the latest snapshot per
// route pattern + tab and records what appeared or disappeared since the
// previous one. So:
//   * a page added next month appears in «نقشهٔ سامانه» the first time anyone
//     opens it, with nobody editing a list;
//   * the supervisor's headless scan calls the very same function
//     (`window.__pmSurfaceSnapshot()`), so both observers measure alike;
//   * the code inventory (scripts/supervisor/inventory.py) marks pages that
//     exist in the source but were never opened, so nothing hides.
//
// Cheap on purpose: one scan per screen once it is idle, sent only when the
// map actually changed (or every few hours), capped in size.
import { useEffect } from 'react'
import { inspectionApi } from './api'
import { activeTab, inferSection, isOurOverlay, tabBars, verifiedSelector } from './spot'

export type SurfaceSnapshot = {
  path: string
  tab: string
  label: string
  title: string
  viewport: { w: number; h: number }
  doc_size: { w: number; h: number }
  elements: {
    kind: string
    label: string
    selector: string
    section: string
    rect: { x: number; y: number; w: number; h: number }
    href?: string
  }[]
}

const MAX_ELEMENTS = 1500
const RESEND_MS = 6 * 3600 * 1000
const KINDS: [string, string][] = [
  ['heading', 'h1, h2, h3, h4'],
  ['tab', '[role="tab"]'],
  ['section', 'section, form, table, [role="tabpanel"], [role="region"], dialog, fieldset'],
  ['button', 'button, [role="button"], input[type="submit"], input[type="button"]'],
  ['input', 'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'],
  ['link', 'a[href]'],
]

const clean = (t: string | null | undefined, n = 120) => (t || '').replace(/\s+/g, ' ').trim().slice(0, n)

function labelOf(el: Element): string {
  const h = el as HTMLElement
  return clean(
    el.getAttribute('aria-label') || el.getAttribute('title') || (el as HTMLInputElement).placeholder
    || (el.tagName === 'SECTION' || el.tagName === 'FORM' || el.tagName === 'TABLE'
      ? (el.querySelector('h1, h2, h3, h4, caption, legend')?.textContent || '')
      : (h.innerText || h.textContent || ''))
    || (el as HTMLInputElement).name || el.id,
  )
}

function visible(r: DOMRect): boolean {
  return r.width > 1 && r.height > 1
}

export function scanSurface(root?: Element | null): SurfaceSnapshot {
  const surface = root || document.querySelector('[data-report-surface]') || document.body
  const sx = window.scrollX || 0
  const sy = window.scrollY || 0
  const seen = new Set<Element>()
  const elements: SurfaceSnapshot['elements'] = []
  // buttons that form a tab bar are TABS, not plain buttons
  const tabButtons = new Set<Element>(tabBars(surface).flatMap((b) => b.buttons))
  for (const [kind, sel] of KINDS) {
    const list = kind === 'tab'
      ? [...Array.from(surface.querySelectorAll(sel)), ...Array.from(tabButtons)]
      : Array.from(surface.querySelectorAll(sel))
    for (const el of list) {
      if (elements.length >= MAX_ELEMENTS) break
      if (seen.has(el) || isOurOverlay(el)) continue
      const r = el.getBoundingClientRect()
      if (!visible(r)) continue
      const selector = verifiedSelector(el)
      if (!selector) continue
      seen.add(el)
      const sec = inferSection(el, surface)
      elements.push({
        kind, label: labelOf(el), selector, section: sec?.label || '',
        rect: { x: Math.round(r.left + sx), y: Math.round(r.top + sy), w: Math.round(r.width), h: Math.round(r.height) },
        ...(kind === 'link' ? { href: clean((el as HTMLAnchorElement).getAttribute('href'), 300) } : {}),
      })
    }
  }
  const de = document.documentElement
  return {
    path: `${window.location.pathname}${window.location.search}`,
    tab: activeTab(document, window.location.search),
    label: clean(surface.getAttribute?.('data-report-surface-label') || document.querySelector('h1')?.textContent || document.title, 200),
    title: clean(document.title, 300),
    viewport: { w: window.innerWidth, h: window.innerHeight },
    doc_size: { w: Math.max(de.scrollWidth, window.innerWidth), h: Math.max(de.scrollHeight, window.innerHeight) },
    elements,
  }
}

function signature(s: SurfaceSnapshot): string {
  let h = 0
  const str = s.elements.map((e) => `${e.kind}|${e.label}|${e.selector}`).join('\n')
  for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  return `${s.elements.length}:${h}`
}

/** Mounted once in the Layout; maps each screen when it settles. */
export function SurfaceRecorder({ pathname }: { pathname: string }) {
  useEffect(() => {
    ;(window as unknown as { __pmSurfaceSnapshot?: () => SurfaceSnapshot }).__pmSurfaceSnapshot = () => scanSurface()
  }, [])

  useEffect(() => {
    let alive = true
    let timer: number | undefined
    let lastTab = ''
    const run = () => {
      if (!alive) return
      try {
        const snap = scanSurface()
        lastTab = snap.tab
        if (!snap.elements.length) return
        const key = `pm.inspection.surface:${snap.path.split('?')[0]}|${snap.tab}`
        const sig = signature(snap)
        let prev: { sig: string; at: number } | null = null
        try { prev = JSON.parse(sessionStorage.getItem(key) || 'null') } catch { prev = null }
        if (prev && prev.sig === sig && Date.now() - prev.at < RESEND_MS) return
        void inspectionApi.registerSurface(snap).then(() => {
          try { sessionStorage.setItem(key, JSON.stringify({ sig, at: Date.now() })) } catch { /* private mode */ }
        }).catch(() => { /* the map is a courtesy — never disturb the page */ })
      } catch { /* exotic DOM — skip this screen */ }
    }
    const schedule = (ms: number) => {
      if (timer) window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        const idle = (window as unknown as { requestIdleCallback?: (cb: () => void) => void }).requestIdleCallback
        if (idle) idle(run)
        else run()
      }, ms)
    }
    schedule(2500)
    // a tab switch inside the same route is a different sub-page: map it too
    const mo = new MutationObserver(() => {
      const t = activeTab(document, window.location.search)
      if (t !== lastTab) { lastTab = t; schedule(1500) }
    })
    try { mo.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['aria-selected', 'data-state'] }) } catch { /* old browser */ }
    return () => { alive = false; if (timer) window.clearTimeout(timer); mo.disconnect() }
  }, [pathname])

  return null
}
