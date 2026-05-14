"""Phase 5 — Scan V5 modules.

Layer above oversight_deep_scan_service for:
  - Comprehensive inventory (12 structural layers)
  - Purpose extraction
  - Stale detection (structural + semantic)
  - Delta + bidirectional dependency + logical impact
  - Runtime discovery + outcome analysis
  - Inspector session for scans (R14)
  - Logical audit (coherence + anti-patterns)
  - Notification audit
  - Smart prompt + smart checklist (R9, R13)

ساختار خروجی هر ماژول compatible با fail-soft است — اگر یک ماژول
شکست خورد، scan کلی ادامه می‌دهد و آن لایه را skip می‌کند.
"""

from __future__ import annotations
