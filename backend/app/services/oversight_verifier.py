"""
Oversight Verifier
==================
موتور verification مستقل از execution.

این موتور **نمی‌داند** کار از چه طریق انجام شده — فقط وضعیت فعلی پروژه را
با acceptance criteria تسک مقایسه می‌کند و یک Report می‌سازد.

اگر done در چند verify متوالی تأیید شد (`confirmation_streak`)، به‌صورت نهایی done.
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from .oversight_service import (
    GITHUB_API,
    STORAGE_DIR,
    get_oversight_service,
    OversightTask,
    OversightReport,
    WatchedProject,
    now_iso,
    get_github_token,
)

logger = logging.getLogger(__name__)

VERIFICATION_DONE = "done"
VERIFICATION_PARTIAL = "partial"
VERIFICATION_NOT_DONE = "not_done"
VERIFICATION_REGRESSED = "regressed"
VERIFICATION_ERROR = "error"


def _gh_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-creator-verifier/1.0",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    }


async def _fetch_file(
    session: aiohttp.ClientSession,
    repo: str,
    path: str,
    headers: Dict[str, str],
    branch: Optional[str] = None,
    max_bytes: int = 40000,
) -> Optional[str]:
    import base64

    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    if branch:
        url += f"?ref={branch}"
    try:
        async with session.get(url, headers=headers, timeout=30) as r:
            if r.status != 200:
                return None
            data = await r.json()
        if not isinstance(data, dict) or data.get("type") != "file" or not data.get("content"):
            return None
        try:
            decoded = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        except Exception:
            return None
        if len(decoded) > max_bytes:
            decoded = decoded[:max_bytes] + "\n... [TRUNCATED]"
        return decoded
    except Exception:
        return None


async def _fetch_target_files(
    repo: str, paths: List[str], branch: Optional[str], token: str
) -> Dict[str, Optional[str]]:
    if not paths:
        return {}
    out: Dict[str, Optional[str]] = {}
    headers = _gh_headers(token)
    async with aiohttp.ClientSession() as session:
        for p in paths[:20]:  # حداکثر ۲۰ فایل
            content = await _fetch_file(session, repo, p, headers, branch)
            out[p] = content
    return out


async def _fetch_repo_tree(
    repo: str, branch: Optional[str], token: str, max_paths: int = 400
) -> List[str]:
    """لیست مسیرهای فایل‌های پروژه از git tree (recursive).

    خروجی فقط شامل code/config files است (نه binaries، نه vendored deps).
    استفاده برای fuzzy matching: اگر AI در پرامپت اسم فایل خاصی ذکر کرده
    ولی آن فایل وجود ندارد، verifier می‌تواند با کمک این لیست فایل‌های
    هم‌ارز با نقش مشابه را پیشنهاد دهد.
    """
    headers = _gh_headers(token)
    url = f"{GITHUB_API}/repos/{repo}/git/trees/{branch or 'main'}?recursive=1"
    skip_prefixes = (
        "node_modules/", "venv/", ".venv/", "vendor/", "dist/", "build/",
        ".next/", ".git/", "__pycache__/", ".pytest_cache/", ".mypy_cache/",
        "coverage/", ".idea/", ".vscode/",
    )
    skip_suffixes = (
        ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".lock",
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf",
        ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3",
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as r:
                if r.status != 200:
                    return []
                data = await r.json()
        tree = data.get("tree") or []
        paths: List[str] = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            p = item.get("path") or ""
            if not p:
                continue
            if any(p.startswith(pre) for pre in skip_prefixes):
                continue
            if any(p.endswith(suf) for suf in skip_suffixes):
                continue
            paths.append(p)
            if len(paths) >= max_paths:
                break
        return paths
    except Exception:
        return []


def _ac_text_of(ac: Any) -> str:
    """🔬 (Runtime Verify Stage 1) — متن AC را برمی‌گرداند، خواه str قدیمی،
    خواه dict جدید با فیلد text."""
    if isinstance(ac, dict):
        return str(ac.get("text") or "").strip()
    return str(ac).strip() if ac is not None else ""


def _evaluate_acs_against_files(
    acceptance_criteria: List[Any],
    file_contents: Dict[str, Optional[str]],
    repo_tree: List[str],
) -> List[Dict[str, Any]]:
    """شواهد ماشینی per-AC: برای هر AC، تعداد hit کلمات کلیدی در هر فایل.
    این یک baseline deterministic به AI verifier می‌دهد — AI نمی‌تواند ادعا
    کند فایل وجود ندارد یا قابلیت پیاده نشده، اگر hit‌ها واقعی هستند.

    🔬 (Runtime Verify Stage 1) — AC می‌تواند str یا dict باشد. متن از
    `_ac_text_of` استخراج می‌شود.

    خروجی per AC:
    {
      "ac": str,                              # متن AC (truncated)
      "keywords": [str],                      # کلمات کلیدی استخراجی
      "hits_in_files": {file: hit_count},     # فایل‌هایی که hit دارند
      "hits_in_tree": [str],                  # فایل‌هایی در tree با اسم مرتبط
      "likely_done": bool,                    # heuristic: hit_count >= 2
      "verdict_hint": str,                    # راهنما برای AI
    }
    """
    out: List[Dict[str, Any]] = []
    for ac in acceptance_criteria:
        ac_text = _ac_text_of(ac)
        ac_keywords = _build_keywords_from_acs([ac_text])
        hits_in_files: Dict[str, int] = {}
        matched_keywords_per_file: Dict[str, List[str]] = {}
        # شمارش hit در محتوای فایل‌ها
        for file_path, content in file_contents.items():
            if not content:
                continue
            content_lower = content.lower()
            file_hit_count = 0
            file_matched: List[str] = []
            for kw in ac_keywords:
                kw_lower = kw.lower()
                if kw_lower in content_lower:
                    file_hit_count += content_lower.count(kw_lower)
                    file_matched.append(kw)
            if file_hit_count > 0:
                hits_in_files[file_path] = file_hit_count
                matched_keywords_per_file[file_path] = file_matched[:5]
        # جستجوی نام فایل‌های مرتبط در tree
        hits_in_tree: List[str] = []
        for kw in ac_keywords[:8]:
            kw_lower = kw.lower()
            for tree_path in repo_tree:
                tp_lower = tree_path.lower()
                if kw_lower in tp_lower and tree_path not in hits_in_tree:
                    hits_in_tree.append(tree_path)
                    if len(hits_in_tree) >= 8:
                        break
            if len(hits_in_tree) >= 8:
                break

        total_hits = sum(hits_in_files.values())
        likely_done = total_hits >= 2 or len(hits_in_files) >= 2 or len(hits_in_tree) >= 2

        verdict_hint = ""
        if likely_done:
            top_files = sorted(hits_in_files.items(), key=lambda x: -x[1])[:3]
            top_str = ", ".join(f"{f}({n})" for f, n in top_files)
            verdict_hint = (
                f"احتمالاً DONE — {total_hits} hit در {len(hits_in_files)} فایل ({top_str}). "
                f"chunks در ادامه را بررسی کن — اگر کد مرتبط دیدی، done بنویس."
            )
        elif hits_in_tree:
            verdict_hint = (
                f"احتمال DONE — اسم {len(hits_in_tree)} فایل با کلمات AC match دارد ({', '.join(hits_in_tree[:3])}). "
                f"اگر content این فایل‌ها در chunks موجود است، بررسی کن."
            )
        else:
            verdict_hint = (
                f"احتمال NOT_DONE — هیچ فایلی hit نداشت و هیچ نام فایلی match نکرد. "
                f"کلمات کلیدی AC: {', '.join(ac_keywords[:8])}"
            )

        out.append({
            "ac": ac_text[:200],
            "keywords": ac_keywords[:8],
            "hits_in_files": hits_in_files,
            "matched_keywords_per_file": matched_keywords_per_file,
            "hits_in_tree": hits_in_tree,
            "likely_done": likely_done,
            "verdict_hint": verdict_hint,
        })
    return out


def _format_machine_evidence_for_prompt(machine_evidence: List[Dict[str, Any]]) -> str:
    """قالب‌بندی شواهد ماشینی برای تزریق به verify_prompt."""
    if not machine_evidence:
        return ""
    lines = ["## 🤖 شواهد ماشینی per-AC (deterministic — این را اول بخوان)\n"]
    lines.append(
        "این تحلیل توسط کد ما (نه AI) انجام شده — کلمات کلیدی هر AC را در محتوای فایل‌ها\n"
        "و در ساختار repo جستجو کرده‌ایم. **اگر hit وجود دارد، پیش‌فرض done است**.\n"
        "تو فقط با شواهد قطعی کد می‌توانی not_done بگویی.\n"
    )
    for i, m in enumerate(machine_evidence, 1):
        lines.append(f"\n### AC {i}: {m['ac'][:150]}")
        lines.append(f"- کلمات کلیدی AC: `{', '.join(m['keywords'])}`")
        if m["hits_in_files"]:
            top = sorted(m["hits_in_files"].items(), key=lambda x: -x[1])[:5]
            lines.append("- 📊 hit در فایل‌ها:")
            for f, n in top:
                kws = m["matched_keywords_per_file"].get(f, [])
                lines.append(f"  - `{f}` → **{n} hit** (کلمات: {', '.join(kws)})")
        else:
            lines.append("- 📊 hit در فایل‌ها: هیچ")
        if m["hits_in_tree"]:
            lines.append(f"- 📁 فایل‌های با نام match: `{', '.join(m['hits_in_tree'][:5])}`")
        lines.append(f"- 🤖 hint: **{m['verdict_hint']}**")
    return "\n".join(lines)


def _extract_relevant_chunks(
    content: str,
    keywords: List[str],
    lines_around: int = 60,
    max_chunks: int = 8,
    max_total_chars: int = 12000,
) -> str:
    """برای فایل‌های بزرگ (مثل page.tsx 4000+ خط)، فقط chunk‌های مرتبط
    با keywords را extract می‌کند به‌جای فقط N کاراکتر اول.

    رویکرد:
    1. فایل را به خط تقسیم کن
    2. خطوطی که حداقل یک keyword (case-insensitive) دارند → "hit lines"
    3. حول هر hit line، lines_around خط بالا/پایین بگیر (chunk)
    4. chunk‌های مجاور را merge کن
    5. حداکثر max_chunks chunk با مهم‌ترین hits برگردان
    """
    if not content or not keywords:
        return content[:max_total_chars] if content else ""

    lines = content.split("\n")
    if len(lines) < 200:
        # فایل کوچک — کل content برگردان
        return content[:max_total_chars]

    keywords_lower = [k.lower() for k in keywords if k and len(k) >= 3]
    if not keywords_lower:
        return content[:max_total_chars]

    # خطوط hit
    hit_lines: List[int] = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords_lower):
            hit_lines.append(i)

    if not hit_lines:
        # هیچ hit ی پیدا نشد — اول و وسط فایل را برگردان
        first_part = "\n".join(lines[:200])
        middle_start = max(0, len(lines) // 2 - 100)
        middle_part = "\n".join(lines[middle_start:middle_start + 200])
        out = f"{first_part}\n\n... [skipped {len(lines) - 400} lines] ...\n\n{middle_part}"
        return out[:max_total_chars]

    # ساخت ranges (start, end) و merge کردن مجاورها
    ranges: List[List[int]] = []
    for h in hit_lines:
        s = max(0, h - lines_around)
        e = min(len(lines), h + lines_around)
        if ranges and s <= ranges[-1][1] + 5:
            # merge با range قبلی
            ranges[-1][1] = max(ranges[-1][1], e)
        else:
            ranges.append([s, e])

    # محدود به max_chunks مهم‌ترین (بر اساس تعداد hit‌ها در range)
    if len(ranges) > max_chunks:
        ranges_with_count: List[tuple] = []
        for r in ranges:
            count = sum(1 for h in hit_lines if r[0] <= h < r[1])
            ranges_with_count.append((count, r))
        ranges_with_count.sort(key=lambda x: -x[0])
        ranges = [r for _, r in ranges_with_count[:max_chunks]]
        ranges.sort()

    # build خروجی با line numbers
    out_parts: List[str] = []
    total = 0
    last_end = 0
    for r in ranges:
        s, e = r
        if last_end and s > last_end:
            skipped = s - last_end
            out_parts.append(f"\n... [پرش {skipped} خط] ...\n")
        chunk_lines = []
        for i in range(s, e):
            chunk_lines.append(f"{i+1:5d} | {lines[i]}")
        chunk_text = "\n".join(chunk_lines)
        if total + len(chunk_text) > max_total_chars:
            chunk_text = chunk_text[: max_total_chars - total]
            out_parts.append(chunk_text)
            break
        out_parts.append(chunk_text)
        total += len(chunk_text)
        last_end = e

    return "\n".join(out_parts)


def _build_keywords_from_acs(acceptance_criteria: List[Any], task_prompt: str = "") -> List[str]:
    """استخراج کلمات کلیدی از معیارهای پذیرش (فارسی + انگلیسی) برای جستجو در فایل‌ها.
    این کلمات کلیدی برای chunk extraction استفاده می‌شوند تا فقط بخش‌های مرتبط
    فایل‌های بزرگ به verifier داده شود.

    🔬 (Runtime Verify Stage 1) — AC می‌تواند str یا dict باشد. text را استخراج می‌کنیم.
    """
    import re
    ac_texts = [_ac_text_of(c) for c in acceptance_criteria]
    text = " ".join(ac_texts) + " " + (task_prompt or "")
    keywords: set = set()
    # کلمات کلیدی انگلیسی (CamelCase + snake_case طولانی)
    for m in re.findall(r"\b[A-Z][a-zA-Z0-9]{3,}\b", text):
        keywords.add(m)
    for m in re.findall(r"\b[a-z][a-z0-9_]{4,}\b", text):
        if "_" in m or len(m) > 6:
            keywords.add(m)
    # کلمات کلیدی فارسی (3+ کاراکتر فارسی)
    for m in re.findall(r"[؀-ۿ]{4,}", text):
        keywords.add(m)
    # حذف stopwords معمول
    stopwords = {
        "function", "class", "import", "export", "return", "const",
        "است", "این", "آن", "های", "هایی", "می‌شود", "شده", "باشد",
        "برای", "وجود", "ندارد", "دارد", "کاربر", "سیستم", "بتواند",
    }
    keywords = {k for k in keywords if k.lower() not in stopwords}
    return sorted(keywords, key=lambda x: -len(x))[:20]


def _extract_keywords_from_prompt(prompt: str, max_keywords: int = 5) -> List[str]:
    """استخراج کلیدواژه‌های کلاس/تابع از prompt (CamelCase + snake_case طولانی)."""
    import re
    if not prompt:
        return []
    # CamelCase identifiers (کلاس‌ها)
    camels = re.findall(r"\b([A-Z][a-zA-Z0-9]{4,})\b", prompt)
    # snake_case identifiers با حداقل ۲ underscore یا طول > 8
    snakes = re.findall(r"\b([a-z][a-z0-9_]{6,})\b", prompt)
    # filter رایج‌ها
    common = {
        "function", "method", "endpoint", "service", "class", "object",
        "request", "response", "result", "return", "param", "value",
        "string", "number", "boolean", "array", "object", "import",
        "export", "default", "async", "await", "promise", "callback",
        "should", "would", "could", "thing", "stuff", "should_not",
    }
    seen: set = set()
    out: List[str] = []
    for kw in camels + snakes:
        kw_low = kw.lower()
        if kw_low in common or kw in seen:
            continue
        seen.add(kw)
        out.append(kw)
        if len(out) >= max_keywords:
            break
    return out


async def _github_code_search(
    repo: str, keywords: List[str], token: str, max_per_keyword: int = 3
) -> Dict[str, List[str]]:
    """GitHub Code Search برای کلیدواژه‌ها — برمی‌گرداند {keyword: [path,...]}."""
    if not keywords or not token or "/" not in repo:
        return {}
    headers = _gh_headers(token)
    results: Dict[str, List[str]] = {}
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for kw in keywords[:5]:  # حداکثر ۵ keyword
            try:
                # GitHub Code Search syntax: <keyword>+repo:<owner>/<repo>
                q = f"{kw}+repo:{repo}"
                url = f"{GITHUB_API}/search/code?q={q}&per_page={max_per_keyword}"
                async with session.get(url, headers=headers) as r:
                    if r.status != 200:
                        continue
                    data = await r.json()
                items = (data.get("items") or [])[:max_per_keyword]
                paths = [it.get("path", "") for it in items if it.get("path")]
                if paths:
                    results[kw] = paths
            except Exception:
                continue
    return results


def _sync_prompt_checkboxes(prompt: str, steps: List[Dict[str, Any]]) -> str:
    """به‌روزرسانی markdown checkbox‌های موجود در `prompt` بر اساس وضعیت `steps`.

    Pattern: `- [ ] **مرحله N: ...**` یا `- [~] **مرحله N: ...**` یا `- [x] **مرحله N: ...**`
    map:  done → [x],  partial → [~],  not_done/pending → [ ]
    """
    if not prompt or not steps:
        return prompt
    import re as _re
    status_to_mark = {
        "done": "x",
        "partial": "~",
        "not_done": " ",
        "pending": " ",
        "error": " ",
    }
    out = prompt
    for s in steps:
        sid = s.get("id")
        if sid is None:
            continue
        mark = status_to_mark.get((s.get("status") or "pending"), " ")
        # pattern: یا [ ] یا [~] یا [x]، بعد فضای خالی، بعد **مرحله N:
        pattern = _re.compile(
            rf"-\s*\[[ x~]\]\s+(\*\*مرحله\s*{_re.escape(str(sid))}\b)",
        )
        out = pattern.sub(lambda m: f"- [{mark}] {m.group(1)}", out, count=1)
    return out


def _recover_partial_json(response: str) -> Dict[str, Any]:
    """تلاش برای استخراج فیلدهای اصلی از JSON ناقص/truncated.

    Strategy: regex برای پیدا کردن آرایه‌های `done_parts`, `remaining_parts`,
    `next_actions` و فیلدهای اسکالر `status`, `summary`, `confidence_score`
    حتی اگر JSON کلی valid نباشد. برای مواردی که `criteria_results` در وسط
    truncate شد ولی فیلدهای قبلی کامل تولید شده‌اند.
    """
    import re
    out: Dict[str, Any] = {}
    if not response:
        return out

    # status
    m = re.search(r'"status"\s*:\s*"([^"]+)"', response)
    if m:
        out["status"] = m.group(1)

    # summary (یک‌خطی، بدون \n داخلی)
    m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', response)
    if m:
        out["summary"] = m.group(1).replace('\\n', '\n').replace('\\"', '"')

    # confidence_score
    m = re.search(r'"confidence_score"\s*:\s*([0-9.]+)', response)
    if m:
        try:
            out["confidence_score"] = float(m.group(1))
        except Exception:
            pass

    # arrays of strings: done_parts, remaining_parts, next_actions
    for key in ("done_parts", "remaining_parts", "next_actions"):
        m = re.search(rf'"{key}"\s*:\s*\[([^\]]*)\]', response, re.DOTALL)
        if m:
            try:
                # parse string items داخل array
                items_blob = m.group(1)
                items = re.findall(r'"((?:[^"\\]|\\.)*)"', items_blob)
                out[key] = [
                    s.replace('\\n', ' ').replace('\\"', '"').strip()
                    for s in items if s.strip()
                ]
            except Exception:
                pass

    # 🆕 (Multi-pass Checklist) — steps_status: لیست dict‌ها
    m = re.search(r'"steps_status"\s*:\s*\[(.*?)\]\s*[,}]', response, re.DOTALL)
    if m:
        try:
            steps_blob = m.group(1)
            # هر object را با brace-matching ساده extract کن
            items: List[Dict[str, Any]] = []
            depth = 0
            buf = []
            for ch in steps_blob:
                if ch == "{":
                    depth += 1
                    buf.append(ch)
                elif ch == "}":
                    depth -= 1
                    buf.append(ch)
                    if depth == 0:
                        obj_str = "".join(buf).strip()
                        buf = []
                        try:
                            import json as _json
                            items.append(_json.loads(obj_str))
                        except Exception:
                            # fallback: regex extract id/status/completion/remaining
                            entry: Dict[str, Any] = {}
                            mid = re.search(r'"id"\s*:\s*"?(\d+)"?', obj_str)
                            if mid:
                                entry["id"] = int(mid.group(1))
                            mst = re.search(r'"status"\s*:\s*"([^"]+)"', obj_str)
                            if mst:
                                entry["status"] = mst.group(1)
                            mcp = re.search(r'"completion_pct"\s*:\s*([0-9]+)', obj_str)
                            if mcp:
                                entry["completion_pct"] = int(mcp.group(1))
                            mre = re.search(r'"remaining"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_str)
                            if mre:
                                entry["remaining"] = mre.group(1).replace('\\"', '"')
                            mev = re.search(r'"evidence"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_str)
                            if mev:
                                entry["evidence"] = mev.group(1).replace('\\"', '"')
                            if entry:
                                items.append(entry)
                elif depth > 0:
                    buf.append(ch)
            if items:
                out["steps_status"] = items
        except Exception:
            pass

    return out


def format_done_remaining_for_message(report: Any, max_per_section: int = 5) -> str:
    """خروجی متن قابل خواندن از done_parts/remaining_parts/next_actions/confidence
    برای پیام Telegram/Email — با truncate و bullet."""
    lines: List[str] = []
    done = list(getattr(report, "done_parts", []) or [])
    remaining = list(getattr(report, "remaining_parts", []) or [])
    next_actions = list(getattr(report, "next_actions", []) or [])
    confidence = float(getattr(report, "confidence_score", 0.0) or 0.0)

    if confidence > 0:
        lines.append(f"🎯 اعتماد: *{int(confidence * 100)}%*")

    if done:
        lines.append(f"\n✅ *انجام‌شده ({len(done)}):*")
        for item in done[:max_per_section]:
            text = str(item).strip().replace("\n", " ")[:180]
            if text:
                lines.append(f"• {text}")
        if len(done) > max_per_section:
            lines.append(f"_… و {len(done) - max_per_section} مورد دیگر_")

    if remaining:
        lines.append(f"\n⏳ *باقی‌مانده ({len(remaining)}):*")
        for item in remaining[:max_per_section]:
            text = str(item).strip().replace("\n", " ")[:180]
            if text:
                lines.append(f"• {text}")
        if len(remaining) > max_per_section:
            lines.append(f"_… و {len(remaining) - max_per_section} مورد دیگر_")

    if next_actions:
        lines.append("\n🪜 *اقدامات بعدی پیشنهادی:*")
        for item in next_actions[:3]:
            text = str(item).strip().replace("\n", " ")[:180]
            if text:
                lines.append(f"• {text}")

    return "\n".join(lines)


def _find_similar_paths(
    missing_path: str, all_paths: List[str], max_results: int = 5
) -> List[str]:
    """برای فایل ذکر‌شده ولی یافت‌نشده، در tree دنبال فایل‌های با نام مشابه می‌گرد.

    معیار شباهت: stem (اسم فایل بدون پسوند و دایرکتوری) به‌صورت substring
    در path هدف بیاید، یا برعکس. همچنین فایل‌های هم‌دایرکتوری بررسی می‌شوند.
    """
    if not missing_path or not all_paths:
        return []
    import os
    stem = os.path.splitext(os.path.basename(missing_path))[0].lower()
    if len(stem) < 3:
        return []
    target_dir = os.path.dirname(missing_path).lower()
    scored: List[tuple] = []
    for p in all_paths:
        p_low = p.lower()
        p_stem = os.path.splitext(os.path.basename(p))[0].lower()
        score = 0
        if stem in p_stem or p_stem in stem:
            score += 10
        # تطابق partial: چند کاراکتر اول/آخر یکسان
        if len(stem) >= 4 and len(p_stem) >= 4:
            if stem[:4] == p_stem[:4]:
                score += 3
        # هم‌دایرکتوری بودن
        if target_dir and os.path.dirname(p_low) == target_dir:
            score += 2
        # کلمات کلیدی مشترک (split by _ / -)
        stem_tokens = set(t for t in stem.replace("-", "_").split("_") if len(t) >= 3)
        p_tokens = set(t for t in p_stem.replace("-", "_").split("_") if len(t) >= 3)
        common = stem_tokens & p_tokens
        score += len(common) * 4
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:max_results]]


async def _fetch_recent_commits(
    repo: str, branch: Optional[str], token: str, limit: int = 15
) -> List[Dict[str, Any]]:
    headers = _gh_headers(token)
    url = f"{GITHUB_API}/repos/{repo}/commits?per_page={limit}"
    if branch:
        url += f"&sha={branch}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                if not isinstance(data, list):
                    return []
                return [
                    {
                        "sha": c.get("sha", "")[:7],
                        "message": (c.get("commit", {}).get("message") or "").split("\n")[0][:200],
                        "date": (c.get("commit", {}).get("author") or {}).get("date", ""),
                    }
                    for c in data
                ]
    except Exception:
        return []


# ============================================================================
# 🔬 (inspector_probe Phase 1) — ضمیمه‌ی screenshot ها به تلگرام + پاک‌سازی
# ============================================================================

def _collect_runtime_screenshot_entries(
    report: "OversightReport",
) -> List[Dict[str, Any]]:
    """لیست screenshot هایی که هنوز روی دیسک هستند را از evidence استخراج کن.

    خروجی: list of dicts با کلیدهای path + label + vision_description.
    """
    out: List[Dict[str, Any]] = []
    try:
        probes = (report.evidence or {}).get("runtime_probes") or []
    except Exception:
        return out
    if not isinstance(probes, list):
        return out
    for p in probes:
        if not isinstance(p, dict):
            continue
        ev = p.get("evidence") or {}
        if not isinstance(ev, dict):
            continue
        shots = ev.get("screenshots") or []
        if not isinstance(shots, list):
            continue
        for s in shots:
            if not isinstance(s, dict):
                continue
            path = s.get("path")
            if not path or s.get("archived_to_telegram"):
                continue
            try:
                import os as _os
                if not _os.path.isfile(path):
                    continue
            except Exception:
                continue
            out.append({
                "path": path,
                "label": s.get("label") or "screenshot",
                "vision_description": s.get("vision_description") or "",
                "ac_text": p.get("ac_text") or "",
                "_ref_probe": p,
                "_ref_shot": s,
            })
    return out


async def _send_runtime_screenshots_and_cleanup(
    task: "OversightTask",
    report: "OversightReport",
    max_send: int = 5,
) -> None:
    """screenshot های runtime را به تلگرام بفرست و در صورت موفقیت پاک کن.

    رفتار:
    - فقط تا max_send screenshot ارسال می‌شود (limit Telegram + reasonable)
    - بقیه روی دیسک می‌مانند، TTL cleanup آن‌ها را برمی‌دارد
    - photo های موفق → از دیسک پاک می‌شوند + در evidence
      archived_to_telegram=True ست می‌شود + path=None (vision_description می‌ماند)
    - اگر کانال تلگرام configured نیست → silent skip
    """
    try:
        from .notification_service import notification_service
    except Exception:
        return

    entries = _collect_runtime_screenshot_entries(report)
    if not entries:
        return
    entries = entries[:max_send]

    paths = [e["path"] for e in entries]
    captions: List[str] = []
    for e in entries:
        ac_excerpt = (e.get("ac_text") or "")[:80]
        vis = (e.get("vision_description") or "")[:300]
        cap = f"📸 {e['label']}\nAC: {ac_excerpt}"
        if vis:
            cap += f"\n👁 {vis}"
        captions.append(cap)

    try:
        results = await notification_service.send_extra_photos(
            paths, captions, silent=True,
        )
    except Exception as _e:
        logger.debug(f"send_extra_photos crashed: {_e}")
        return

    # موفق‌ها را پاک کن، evidence را آپدیت کن
    by_path = {r.get("path"): r for r in (results or []) if isinstance(r, dict)}
    import os as _os
    deleted_count = 0
    for e in entries:
        r = by_path.get(e["path"])
        if not r or not r.get("ok"):
            continue
        try:
            _os.remove(e["path"])
            deleted_count += 1
        except Exception as _de:
            logger.debug(f"unlink screenshot failed: {_de}")
        try:
            e["_ref_shot"]["archived_to_telegram"] = True
            e["_ref_shot"]["path"] = None
        except Exception:
            pass

    # یک نوت در inspector_session
    try:
        sid = (report.evidence or {}).get("auto_verify_session_id")
        if sid is None:
            # یا از اولین probe بگیر
            probes = (report.evidence or {}).get("runtime_probes") or []
            for p in probes:
                ev = (p.get("evidence") if isinstance(p, dict) else None) or {}
                if ev.get("inspector_session_id"):
                    sid = ev["inspector_session_id"]
                    break
        if sid is not None and deleted_count > 0:
            from .verify_runtime.inspector_probe import _msg as _ip_msg
            await _ip_msg(
                int(sid), "system",
                f"📦 {deleted_count} screenshot به تلگرام آرشیو شد و از دیسک پاک شد",
            )
    except Exception:
        pass

    # ذخیره نهایی reports روی دیسک تا evidence جدید (path=None) محفوظ بماند
    try:
        from .oversight_service import get_oversight_service as _gos
        service = _gos()
        async with service._lock:
            service._save_reports()  # type: ignore[attr-defined]
    except Exception:
        # برخی نسخه‌ها _save_reports ندارند یا اسم متفاوت دارند
        try:
            from .oversight_service import get_oversight_service as _gos
            service = _gos()
            async with service._lock:
                if hasattr(service, "_save_reports"):
                    service._save_reports()
                elif hasattr(service, "_save"):
                    service._save()
        except Exception as _se2:
            logger.debug(f"could not persist updated evidence: {_se2}")


# ============================================================================
# 🔬 (inspector_probe Phase 1) — مدیریت چرخه‌حیات auto-verify inspector_session
# ============================================================================

def _resolve_inspector_project_id(
    task: "OversightTask",
    watched: Optional["WatchedProject"],
) -> str:
    """تشخیص project_id که در InspectorSession ذخیره می‌شود.

    inspector_session.project_id همان repo_full_name (مثل
    «mahdighandi1989/project-management») است که از watched گرفته می‌شود.
    در نبود watched، fallback به task.project_full_name است.
    """
    if watched and getattr(watched, "repo_full_name", None):
        return str(watched.repo_full_name)
    return str(getattr(task, "project_full_name", "") or "unknown")


async def _create_auto_verify_inspector_session(
    *, task: "OversightTask", watched: Optional["WatchedProject"],
) -> Optional[int]:
    """ایجاد یک InspectorSession جدید با عنوان «🤖 auto-verify · …».

    خروجی: id session جدید، یا None در صورت شکست.
    این تابع هیچ exception ای بیرون نمی‌اندازد.
    """
    project_id = _resolve_inspector_project_id(task, watched)
    safe_title = (task.title or task.id)[:50]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    title = f"🤖 auto-verify · {safe_title} · {ts}"

    def _create_sync() -> Optional[int]:
        try:
            from ..core.database import SessionLocal
            from ..models.inspector_session import InspectorSession
        except Exception as e:
            logger.debug(f"auto-verify session import failed: {e}")
            return None
        db = SessionLocal()
        try:
            sess = InspectorSession(
                project_id=project_id, status="active", title=title,
            )
            db.add(sess)
            db.commit()
            db.refresh(sess)
            return int(sess.id)
        except Exception as e:
            logger.debug(f"auto-verify session insert failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return None
        finally:
            try:
                db.close()
            except Exception:
                pass

    try:
        import asyncio as _asyncio_local
        sid = await _asyncio_local.to_thread(_create_sync)
        if sid is not None:
            logger.info(f"auto-verify session created id={sid} for task={task.id}")
        return sid
    except Exception as e:
        logger.debug(f"auto-verify session create wrapper failed: {e}")
        return None


async def _archive_auto_verify_inspector_session(session_id: int) -> None:
    """status را به «archived» تغییر بده. silent fail."""
    def _archive_sync() -> None:
        try:
            from ..core.database import SessionLocal
            from ..models.inspector_session import InspectorSession
            from datetime import datetime as _dt
        except Exception:
            return
        db = SessionLocal()
        try:
            sess = db.query(InspectorSession).filter(
                InspectorSession.id == session_id
            ).first()
            if sess is None:
                return
            sess.status = "archived"
            sess.closed_at = _dt.utcnow()
            db.commit()
        except Exception as e:
            logger.debug(f"archive session failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass

    try:
        import asyncio as _asyncio_local
        await _asyncio_local.to_thread(_archive_sync)
    except Exception:
        pass


async def verify_task(
    task_id: str,
    *,
    model_id: Optional[str] = None,
    triggered_by: str = "manual",
    include_runtime: bool = True,
) -> Dict[str, Any]:
    """اجرای verify روی یک تسک — مستقل از execution.

    include_runtime: اگر False، فقط grep + AI (verify سریع، بدون probe).
    اگر True (پیش‌فرض)، probe های runtime نیز اجرا می‌شوند.
    """
    service = get_oversight_service()
    task = next((t for t in service.tasks if t.id == task_id), None)
    if task is None:
        raise ValueError("تسک یافت نشد")
    watched = service._find_watched(task.watched_id) if task.watched_id else None
    if watched is None and task.project_full_name:
        # fallback: شاید watched id ندارد ولی full_name دارد
        watched = next(
            (w for w in service.watched if w.repo_full_name == task.project_full_name),
            None,
        )

    token = get_github_token()

    # 1) فایل‌های هدف
    target_files = list(task.target_files or [])
    if not target_files and task.prompt:
        from .oversight_strong_prompt import extract_target_files
        target_files = extract_target_files(task.prompt)

    # 2) معیارها
    acceptance_criteria = list(task.acceptance_criteria or [])
    if not acceptance_criteria and task.prompt:
        from .oversight_strong_prompt import extract_acceptance_criteria
        acceptance_criteria = extract_acceptance_criteria(task.prompt)

    if not acceptance_criteria:
        acceptance_criteria = [
            "تغییرات لازم در پروژه اعمال شده باشد",
            "هیچ تستی fail نشود",
            "linter بدون warning عبور کند",
        ]

    # 3) محتوای فعلی فایل‌ها
    # PR-aware mode: اگر تسک از طریق Inspector apply-action اجرا شده و PR
    # هنوز merge نشده، فایل‌ها باید از branch همان PR خوانده شوند تا verify
    # **قبل از merge** هم امکان‌پذیر باشد. اگر pr_branch دیگر روی repo
    # موجود نباشد (delete شده پس از merge)، fallback به branch اصلی و
    # از آنجا fetch می‌شود.
    file_contents: Dict[str, Optional[str]] = {}
    recent_commits: List[Dict[str, Any]] = []
    default_branch = (watched.default_branch if watched else None) or "main"
    repo_full_name = watched.repo_full_name if watched else task.project_full_name

    # تشخیص branch مورد استفاده برای verify
    applied_evidence = task.applied_evidence or {}
    pr_branch = applied_evidence.get("pr_branch") or ""
    pr_url = applied_evidence.get("pr_url") or ""
    branch = pr_branch or default_branch
    branch_source = "pr_branch" if pr_branch else "default"

    if token and repo_full_name and "/" in repo_full_name:
        try:
            file_contents = await _fetch_target_files(
                repo_full_name, target_files, branch, token
            )
            # اگر pr_branch ست بود ولی هیچ فایلی fetch نشد، احتمالاً branch
            # دیگر موجود نیست (merge + delete). به default fallback می‌کنیم.
            if pr_branch and (not file_contents or all(v is None for v in file_contents.values())):
                logger.info(
                    f"verify: pr_branch '{pr_branch}' بدون نتیجه — fallback به '{default_branch}'"
                )
                branch = default_branch
                branch_source = "default_fallback_after_pr_branch_missing"
                file_contents = await _fetch_target_files(
                    repo_full_name, target_files, branch, token
                )
        except Exception as e:
            logger.warning(f"verify: fetch files failed: {e}")
            # تلاش fallback اگر pr_branch fetch ناموفق بود
            if pr_branch and branch == pr_branch:
                try:
                    branch = default_branch
                    branch_source = "default_fallback_after_pr_error"
                    file_contents = await _fetch_target_files(
                        repo_full_name, target_files, branch, token
                    )
                except Exception as e2:
                    logger.warning(f"verify: default branch fetch هم شکست خورد: {e2}")
        try:
            recent_commits = await _fetch_recent_commits(repo_full_name, branch, token)
        except Exception as e:
            logger.warning(f"verify: fetch commits failed: {e}")

    # 3.5) repo tree برای fuzzy matching — کمک می‌کند verifier فایل‌های هم‌ارز
    # با نام متفاوت را هم تشخیص دهد (مثلاً پرامپت idea.py خواسته ولی پروژه
    # از oversight_service.py استفاده کرده)
    repo_tree: List[str] = []
    if token and repo_full_name and "/" in repo_full_name:
        try:
            repo_tree = await _fetch_repo_tree(repo_full_name, branch, token)
        except Exception as e:
            logger.warning(f"verify: fetch tree failed: {e}")

    # 3.6) GitHub Code Search — برای کلیدواژه‌های مهم (کلاس‌ها/توابع) که در
    # prompt ذکر شده‌اند، ببین در کجاهای repo استفاده می‌شوند. این کمک می‌کند
    # verifier حتی اگر فایل صریح نباشد، فایل‌های متن‌به‌متن مرتبط را پیدا کند.
    keyword_search: Dict[str, List[str]] = {}
    keywords: List[str] = []
    if token and repo_full_name and "/" in repo_full_name:
        try:
            keywords = _extract_keywords_from_prompt(task.prompt or "", max_keywords=5)
            if keywords:
                keyword_search = await _github_code_search(
                    repo_full_name, keywords, token, max_per_keyword=3
                )
        except Exception as e:
            logger.debug(f"verify: code search failed: {e}")

    # 🆕 کلمات کلیدی برای chunk extraction — هم AC و هم prompt
    # این کلمات برای برش هوشمند فایل‌های بزرگ (مثل page.tsx 4000+ خط) به‌کار می‌روند
    chunk_keywords = _build_keywords_from_acs(acceptance_criteria, task.prompt or "")

    # 3.7) 🆕 UI/frontend file injection — اگر AC یا prompt شامل کلمات
    # frontend-related باشد (UI، component، دکمه، page، نمایش، فرانت‌اند، ...)
    # حتماً فایل‌های اصلی frontend را به context اضافه کن، چون اغلب اوقات
    # target_files فقط backend files بود ولی AC مربوط به UI است.
    frontend_keywords = [
        "ui", "component", "page", "tsx", "frontend", "فرانت", "فرانت‌اند",
        "دکمه", "نمایش", "کپی", "panel", "view", "modal",
    ]
    prompt_lower = (task.prompt or "").lower() + " ".join(_ac_text_of(c) for c in acceptance_criteria).lower()
    needs_frontend = any(kw in prompt_lower for kw in frontend_keywords)
    auto_frontend_files: List[str] = []
    if needs_frontend and repo_tree:
        # فایل‌های page.tsx اصلی + components را پیدا کن (محدود به ۵ فایل)
        candidates = [
            p for p in repo_tree
            if (p.endswith("/page.tsx") or p.endswith("/page.jsx"))
            or "components/" in p and (p.endswith(".tsx") or p.endswith(".jsx"))
        ]
        # اولویت: فایل‌هایی که نام prompt در path است
        prompt_words = set()
        for kw in keywords[:5] if 'keywords' in dir() and keywords else []:
            prompt_words.add(kw.lower())
        scored = []
        for p in candidates:
            score = 1
            p_low = p.lower()
            if "/oversight" in p_low or "oversight" in p_low:
                score += 3
            if any(w in p_low for w in prompt_words):
                score += 2
            scored.append((score, p))
        scored.sort(key=lambda x: -x[0])
        auto_frontend_files = [p for _, p in scored[:5]]
        if auto_frontend_files and token:
            try:
                fe_contents = await _fetch_target_files(
                    repo_full_name, auto_frontend_files, branch, token
                )
                for k, v in fe_contents.items():
                    file_contents[k] = v
            except Exception as e:
                logger.debug(f"verify: fetch frontend files failed: {e}")

    # 4) ساخت پرامپت verifier — برای هر فایل یافت‌نشده، فایل‌های هم‌ارز را
    # از tree پیدا و محتوای آن‌ها را نیز fetch می‌کنیم
    fuzzy_resolved: Dict[str, List[str]] = {}  # missing_path -> similar_paths
    extra_files_to_fetch: List[str] = []
    for p in target_files:
        if file_contents.get(p) is None and repo_tree:
            similar = _find_similar_paths(p, repo_tree, max_results=3)
            if similar:
                fuzzy_resolved[p] = similar
                for sp in similar:
                    if sp not in target_files and sp not in extra_files_to_fetch:
                        extra_files_to_fetch.append(sp)

    if extra_files_to_fetch and token and repo_full_name and "/" in repo_full_name:
        try:
            extra_contents = await _fetch_target_files(
                repo_full_name, extra_files_to_fetch[:10], branch, token
            )
            for k, v in extra_contents.items():
                file_contents[k] = v
        except Exception as e:
            logger.warning(f"verify: fetch fuzzy-matched files failed: {e}")

    files_blob_parts: List[str] = []
    for p in target_files:
        c = file_contents.get(p)
        if c is None:
            similar = fuzzy_resolved.get(p, [])
            if similar:
                files_blob_parts.append(
                    f"=== {p} ===\n[فایل با این نام دقیق وجود ندارد — "
                    f"اما این فایل‌های هم‌نقش/هم‌ارز در repo یافت شدند: {', '.join(similar)}. "
                    f"محتوایشان در ادامه آمده — بررسی کن آیا نقش مورد نظر را برآورده می‌کنند.]"
                )
            else:
                files_blob_parts.append(f"=== {p} ===\n[فایل یافت نشد]")
        else:
            # 🆕 chunk extraction هوشمند — اگر فایل بزرگ است (>10000 char)،
            # فقط بخش‌های مرتبط با کلمات کلیدی AC را بگیر، نه فقط N char اول
            if len(c) > 10000 and chunk_keywords:
                chunk = _extract_relevant_chunks(c, chunk_keywords, lines_around=60, max_total_chars=12000)
                files_blob_parts.append(
                    f"=== {p} ({len(c.splitlines())} line file — chunk‌های مرتبط با AC) ===\n{chunk}"
                )
            else:
                files_blob_parts.append(f"=== {p} ===\n{c[:8000]}")
    # محتوای فایل‌های هم‌ارز را هم اضافه کن (با chunk extraction برای فایل‌های بزرگ)
    for sp in extra_files_to_fetch[:10]:
        c = file_contents.get(sp)
        if c is not None:
            if len(c) > 10000 and chunk_keywords:
                chunk = _extract_relevant_chunks(c, chunk_keywords, lines_around=60, max_total_chars=10000)
                files_blob_parts.append(f"=== {sp} (هم‌ارز — chunk مرتبط) ===\n{chunk}")
            else:
                files_blob_parts.append(f"=== {sp} (فایل هم‌ارز) ===\n{c[:8000]}")
    # فایل‌های کشف‌شده با code search برای keywords مهم
    code_search_files: List[str] = []
    for kw, paths in keyword_search.items():
        for p in paths:
            if p not in target_files and p not in extra_files_to_fetch and p not in code_search_files:
                code_search_files.append(p)
    if code_search_files and token and repo_full_name and "/" in repo_full_name:
        try:
            extra2 = await _fetch_target_files(repo_full_name, code_search_files[:5], branch, token)
            for k, v in extra2.items():
                file_contents[k] = v
                if v is not None:
                    # لیست keywords که این فایل را برگرداندند
                    matched_kws = [kw for kw, ps in keyword_search.items() if k in ps]
                    files_blob_parts.append(
                        f"=== {k} (یافت‌شده با کلیدواژه‌های: {', '.join(matched_kws)}) ===\n{v[:6000]}"
                    )
        except Exception as e:
            logger.debug(f"verify: fetch code-search files failed: {e}")
    # 🆕 فایل‌های frontend که خودکار اضافه شده‌اند (وقتی AC مربوط به UI است)
    # 🚨 برای page.tsx اصلی (که می‌تواند 4000+ خط باشد)، حتماً chunk extraction استفاده کنیم
    for fe_path in auto_frontend_files:
        if fe_path in target_files or fe_path in extra_files_to_fetch:
            continue
        c = file_contents.get(fe_path)
        if c is not None:
            if len(c) > 10000 and chunk_keywords:
                chunk = _extract_relevant_chunks(c, chunk_keywords, lines_around=80, max_chunks=10, max_total_chars=15000)
                files_blob_parts.append(
                    f"=== {fe_path} (UI file — chunk‌های مرتبط با AC از {len(c.splitlines())} خط) ===\n{chunk}"
                )
            else:
                files_blob_parts.append(
                    f"=== {fe_path} (UI file — auto-added چون AC مربوط به فرانت‌اند است) ===\n{c[:8000]}"
                )
    files_blob = "\n\n".join(files_blob_parts) or "(فایل هدفی مشخص نیست — بر اساس کل پرامپت بررسی کن)"

    # خلاصهٔ ساختار repo برای دید کلی AI
    tree_blob = ""
    if repo_tree:
        # محدود به مسیرهای کد (backend/frontend/src/services/...) و حداکثر 200 خط
        meaningful = [p for p in repo_tree if any(
            seg in p for seg in ("backend/", "frontend/", "src/", "app/", "services/",
                                  "routes/", "components/", "pages/", "lib/", "utils/")
        )][:200]
        if meaningful:
            tree_blob = "\n".join(meaningful)

    commits_blob = "\n".join(
        f"- {c['sha']} ({c['date'][:10]}) {c['message']}" for c in recent_commits[:10]
    ) or "(کامیتی یافت نشد)"

    # 🤖 شواهد ماشینی per-AC — قبل از فرستادن به AI، خود ما کلمات AC را در
    # فایل‌ها grep می‌کنیم. این به AI hint قاطع می‌دهد که AC کدام در کجا
    # احتمالاً پیاده شده — و جلوگیری از not_done کاذب.
    machine_evidence = _evaluate_acs_against_files(
        acceptance_criteria, file_contents, repo_tree
    )
    machine_evidence_blob = _format_machine_evidence_for_prompt(machine_evidence)

    # 🔬 (Runtime Verify Stage 5) — probe های runtime را اجرا کن (Playwright/HTTP/pytest)
    # هر probe که شکست خورد، fail-soft می‌شود — verify ادامه می‌دهد.
    # نتایج به prompt verify اضافه می‌شود تا AI شواهد runtime را در ارزیابی
    # خود لحاظ کند.
    runtime_probe_results: List[Any] = []
    runtime_evidence_blob = ""
    runtime_override_hints: Dict[str, str] = {}  # ac_text → "passed" | "failed"
    runtime_run_id: Optional[str] = None
    # 🔬 (debug visibility) — توضیح اینکه چرا/چطور runtime block اجرا شد
    runtime_status_note: str = "did_not_run"
    try:
        import os as _os
        import uuid as _uuid
        from pathlib import Path as _Path
        runtime_enabled = (
            include_runtime and
            _os.environ.get("RUNTIME_VERIFY_ENABLED", "true").lower() != "false"
        )
        if not include_runtime:
            runtime_status_note = "skipped (include_runtime=false)"
        elif not runtime_enabled:
            runtime_status_note = "disabled by RUNTIME_VERIFY_ENABLED env"
        elif not acceptance_criteria:
            runtime_status_note = "no acceptance_criteria to probe"
        if runtime_enabled and acceptance_criteria:
            from .verify_runtime import (
                run_probes_for_task,
                enrich_acs_with_verify_plans,
            )
            from .verify_runtime.ac_enricher import _ac_already_classified
            from .verify_runtime.storage import (
                ensure_run_dir, write_manifest, cleanup_old_runs,
            )

            # 🔬 (Stage 5 fix) — اگر AC این تسک هنوز classify نشده (همه static)
            # و base URL داریم، AI را فراخوانی کن تا method ها را تشخیص دهد
            # (یعنی AC هایی که UI/API هستند درست probe بخورند، نه static skipped).
            try:
                needs_enrich = any(
                    not _ac_already_classified(ac if isinstance(ac, dict) else {"text": str(ac), "verify_method": "static", "verify_plan": {}})
                    for ac in acceptance_criteria
                )
                has_base_url = bool(
                    (watched and (getattr(watched, "frontend_base_url", None) or getattr(watched, "backend_base_url", None)))
                )
                if needs_enrich and has_base_url:
                    logger.info(
                        f"verify {task.id}: AC ها classify نشده‌اند — AI enricher را فراخوانی می‌کنیم"
                    )
                    enriched = await enrich_acs_with_verify_plans(
                        acceptance_criteria,
                        title=task.title,
                        description=task.raw_idea or task.prompt[:500],
                        target_files=list(task.target_files or []),
                        model_id=model_id,
                    )
                    if enriched:
                        # ذخیرهٔ AC جدید روی task (در lock)
                        async with service._lock:
                            task.acceptance_criteria = enriched
                            task.updated_at = now_iso()
                            service._save_tasks()
                        acceptance_criteria = enriched
            except Exception as _ee:
                logger.warning(f"AC on-the-fly enrichment failed: {_ee}")

            runtime_run_id = f"run_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:6]}"
            run_dir = ensure_run_dir(
                _Path(STORAGE_DIR), str(task.id), runtime_run_id,
            )
            runtime_started_at = now_iso()

            # 🔬 (inspector_probe Phase 1) — یک inspector_session موقت بساز
            # تا probe ها بتوانند اقدامات قدم‌به‌قدم را در تب «بازرس ویژه» نشان دهند.
            # اگر ساخت شکست خورد، probe ها بدون session اجرا می‌شوند (graceful).
            auto_verify_session_id: Optional[int] = None
            try:
                auto_verify_session_id = await _create_auto_verify_inspector_session(
                    task=task, watched=watched,
                )
            except Exception as _se:
                logger.debug(f"auto-verify session create failed: {_se}")

            # 🛡 (critical fix) — `run_probes_for_task` فقط `task.acceptance_criteria`
            # را می‌خواند. اگر آن خالی باشد و AC از پرامپت extract شده باشد، probe
            # هرگز fire نمی‌شود. به جای آن، از run_probes_for_acs استفاده می‌کنیم
            # که مستقیماً لیست AC را می‌گیرد.
            from .verify_runtime import run_probes_for_acs, build_probe_context
            _probe_ctx = build_probe_context(
                task_id=str(task.id),
                run_id=runtime_run_id,
                repo_path=(
                    getattr(watched, "runtime_repo_path", None) if watched else None
                ),
                frontend_base_url=(
                    getattr(watched, "frontend_base_url", None) if watched else None
                ),
                backend_base_url=(
                    getattr(watched, "backend_base_url", None) if watched else None
                ),
                auth_type=(
                    (getattr(watched, "runtime_auth", None) or {}).get("type")
                    if watched else None
                ),
                auth_value=(
                    (getattr(watched, "runtime_auth", None) or {}).get("value")
                    if watched else None
                ),
                evidence_dir=str(run_dir),
                inspector_session_id=auto_verify_session_id,
                verify_model_id=model_id,
                watched_id=str(watched.id) if watched else None,
            )
            runtime_probe_results = await run_probes_for_acs(
                acceptance_criteria, _probe_ctx,
            )
            # manifest.json + size cap enforcement
            try:
                from .verify_runtime.storage import enforce_size_cap
                # size cap قبل از manifest، تا اگر حذف شد، manifest تازه باشد
                _cap = enforce_size_cap(run_dir)
                if _cap.get("compressed") or _cap.get("deleted"):
                    logger.info(
                        f"verify {task.id}: size cap — "
                        f"compressed={_cap.get('compressed')}, deleted={_cap.get('deleted')}, "
                        f"{_cap.get('initial_bytes')}b → {_cap.get('final_bytes')}b"
                    )
                write_manifest(
                    run_dir,
                    task_id=str(task.id),
                    run_id=runtime_run_id,
                    probe_results=[r.to_dict() for r in runtime_probe_results],
                    started_at=runtime_started_at,
                    finished_at=now_iso(),
                )
                cleanup_old_runs(_Path(STORAGE_DIR), str(task.id), keep=5)
            except Exception as _me:
                logger.debug(f"manifest write/cleanup failed: {_me}")
            if runtime_probe_results:
                rt_lines = [
                    "# 🔬 شواهد Runtime (probe های اجرا شده)",
                    "",
                    "**این شواهد دقیق‌تر از تحلیل کد است.** اگر probe می‌گوید passed،",
                    "بسیار محتمل است AC done باشد. اگر probe می‌گوید failed، AC nicht done است.",
                    "",
                ]
                for r in runtime_probe_results:
                    rt_lines.append(f"### {r.summary()}")
                    rt_lines.append(f"  - AC: «{r.ac_text[:200]}»")
                    if r.evidence:
                        # خلاصهٔ شواهد بدون ذکر paths فایل (که برای AI mعنی ندارد)
                        ev = {k: v for k, v in r.evidence.items()
                              if k not in ("step_results", "screenshots", "stdout_excerpt", "stderr_excerpt")}
                        if ev:
                            rt_lines.append(f"  - evidence: {ev}")
                    rt_lines.append("")
                    # override hint برای AI
                    if r.status == "passed":
                        runtime_override_hints[r.ac_text[:200]] = "passed"
                    elif r.status == "failed":
                        runtime_override_hints[r.ac_text[:200]] = "failed"
                runtime_evidence_blob = "\n".join(rt_lines)
                runtime_status_note = (
                    f"ran ({len(runtime_probe_results)} probes: "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'passed')}p/"
                    f"{sum(1 for r in runtime_probe_results if r.status == 'failed')}f/"
                    f"{sum(1 for r in runtime_probe_results if r.status == 'skipped')}s/"
                    f"{sum(1 for r in runtime_probe_results if r.status == 'error')}e)"
                )
                logger.info(
                    f"verify {task.id}: runtime probes ran — "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'passed')} passed, "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'failed')} failed, "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'skipped')} skipped, "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'error')} errors"
                )
    except Exception as _re:
        logger.warning(f"runtime probes block failed: {_re}", exc_info=False)
        runtime_probe_results = []
        runtime_evidence_blob = ""
    finally:
        # 🔬 (inspector_probe Phase 1) — session را archive کن (silent fail)
        try:
            _avs_id = locals().get("auto_verify_session_id")
            if _avs_id is not None:
                await _archive_auto_verify_inspector_session(int(_avs_id))
        except Exception as _ae:
            logger.debug(f"archive auto-verify session failed: {_ae}")

    user_goal = (watched.user_notes if watched else "") or ""

    ac_lines = "\n".join(f"- {_ac_text_of(c)}" for c in acceptance_criteria)

    # 🆕 (Multi-pass Checklist) — اگر تسک task_steps دارد، برای verifier هم
    # checklist می‌سازیم تا هر مرحله را جداگانه ارزیابی کند.
    task_steps_list: List[Dict[str, Any]] = list(task.task_steps or [])
    steps_blob = ""
    steps_json_template = ""
    if task_steps_list:
        steps_lines = [
            "# 📋 چک‌لیست مراحل تسک (مهم — هر مرحله را جداگانه ارزیابی کن)",
            "",
            "تسک به مراحل مشخص تقسیم شده. علاوه بر AC کلی، **برای هر مرحله جداگانه**",
            "وضعیت آن را در `steps_status` خروجی برگردان: `done` (کامل)، `partial`",
            "(ناقص — چیزی باقی مانده)، یا `not_done` (هنوز شروع نشده).",
            "اگر `partial` بود، حتماً در فیلد `remaining` بنویس **چه چیزی هنوز باقی مانده**.",
            "",
        ]
        for s in task_steps_list:
            cur = (s.get("status") or "pending")
            steps_lines.append(
                f"- **مرحله {s.get('id')}** ({cur}): "
                f"{(s.get('title') or '')[:120]} — "
                f"{(s.get('scope') or '')[:280]}"
            )
        steps_blob = "\n".join(steps_lines)
        # ساخت template نمونه (id‌ها واقعی) برای کاهش خطای AI
        sample_ids = [str(s.get("id", i + 1)) for i, s in enumerate(task_steps_list[:3])]
        sample_lines = ",\n    ".join(
            f'{{"id": {sid}, "status": "done|partial|not_done", "completion_pct": 0, "remaining": "...", "evidence": "..."}}'
            for sid in sample_ids
        )
        steps_json_template = (
            ',\n  "steps_status": [\n    '
            + sample_lines
            + (",\n    ..." if len(task_steps_list) > 3 else "")
            + "\n  ]"
        )

    verify_prompt = f"""تو یک QA حرفه‌ای هستی. وظیفه‌ات بررسی این است که آیا کارهای خواسته‌شده در پرامپت تسک واقعاً در وضعیت فعلی پروژه انجام شده‌اند یا نه — **بدون اهمیت دادن به اینکه چه کسی یا با چه ابزاری انجام داده**. فقط وضعیت فعلی را با معیارهای پذیرش مقایسه کن.

# 🧠 اصل ارزیابی (مهم — قبل از تصمیم بخوان)
- **تطابق معنایی، نه literal**: اگر کد به شکل متفاوت ولی **هم‌ارز** نوشته شده — یعنی همان نتیجه را تولید می‌کند، همان رفتار را دارد، همان معیار پذیرش را برآورده می‌کند — این **done** است. نباید بخواهی exactly مطابق پرامپت باشد.
- **نام فایل‌ها/کلاس‌ها/سرویس‌ها مهم نیست — نقش و رفتار مهم است**: اگر پرامپت گفته «فایل `idea.py` بساز» ولی پروژه از `oversight_service.py` با همان نقش (تعریف Idea/Task) استفاده کرده، این **done** است. اگر پرامپت گفته «کلاس `AITaskExecutor` بساز» ولی پروژه از یک سرویس با نام دیگر (مثل `runtime_executor` یا `apply_action`) که **همان کار** را می‌کند استفاده کرده، **done** است. اگر پرامپت گفته «`SmartVerifier`» ولی پروژه از `oversight_verifier` استفاده می‌کند، **done** است. اگر پرامپت گفته «پیاده‌سازی scheduler» ولی پروژه از `background_scheduler` یا منطق scheduling embedded در service دیگری استفاده می‌کند، **done** است.
- **🎯 الگوی Next.js / SPA — بسیار مهم**: اگر پرامپت گفته «کامپوننت `XyzPanel.tsx` یا `XyzForm.tsx` بساز» ولی پروژه از Next.js App Router استفاده می‌کند، تمام آن منطق ممکن است در یک فایل `app/<route>/page.tsx` پیاده شده باشد (نه فایل کامپوننت جدا). این **done** است. به عنوان مثال:
  - پرامپت: «`OversightPanel.tsx` بساز» → پروژه: `frontend/src/app/oversight/page.tsx` با همان UI = **done**
  - پرامپت: «`IdeaForm.tsx` بساز» → پروژه: form ای داخل `app/oversight/page.tsx` که ایده می‌گیرد = **done**
  - پرامپت: «`SettingsPanel.tsx` بساز» → پروژه: `app/settings/page.tsx` = **done**
- **الگوی endpoint اختصاصی vs همگانی**: اگر پرامپت گفته «endpoint `/projects/{id}/ideas` بساز» ولی پروژه از `/oversight/tasks` با field `watched_id` (یا معادل project_id) استفاده می‌کند که **همان کار** را می‌کند، **done** است. تخصیص دقیق path مهم نیست؛ توانایی ثبت ایده با اتصال به پروژه مهم است.
- **قبل از گفتن "فایل/کلاس X وجود ندارد"**: حتماً repo tree (که در ادامه می‌آید) را اسکن کن. به دنبال اسامی similar (با substring، token overlap، یا روی نقش مشترک) بگرد. اگر هر سرویسی با نقش مشابه (executor, verifier, scheduler, validator, ...) موجود است، این بخش done است.
- **هرگز** صرفاً به این دلیل که نام دقیقاً همان چیزی نیست که پرامپت اولیه گفته، not_done نگو. پرامپت اولیه ممکن است نام‌گذاری ideal را پیشنهاد داده باشد، ولی تیم ممکن است معماری متفاوتی انتخاب کرده باشد. **رفتار = done، نه نام**.

# 🔬 روش بررسی (بسیار مهم — قبل از تصمیم بخوان)
**ترتیب اعتماد: 🤖 شواهد ماشینی (بالاترین) > chunk‌های فایل > tree > پرامپت اولیه**

🚨 **قانون طلایی**: اگر «🤖 شواهد ماشینی» (بخش بعدی این پرامپت) برای یک AC
نشان دهد hit‌هایی در فایل‌ها وجود دارد، **پیش‌فرض همان AC done است**. تو
فقط در صورتی می‌توانی not_done بگویی که با خواندن chunk‌ها مطمئن شوی کد
موجود آن AC را برآورده نمی‌کند (نه اینکه نام دقیق نمی‌بینی، بلکه کد رفتار
متفاوتی دارد).

برای هر AC این مراحل را به ترتیب انجام بده:
1. **اول**: نگاه کن به «🤖 شواهد ماشینی» — اگر `verdict_hint = "احتمالاً DONE"`
   با hit‌های قابل توجه (≥2)، **done** بنویس مگر اینکه دلیل قوی برای not_done
   داشته باشی.
2. **دوم**: chunk‌های مربوطه را بخوان — اگر متن یا کد مرتبط یافت کردی
   (متن دکمه، نام تابع، JSX، endpoint، …)، **done** را تأیید کن.
3. **سوم**: اگر هم hit صفر بود و هم در tree نام مرتبط نبود، آنگاه not_done.

❌ **هرگز** این بهانه‌ها برای not_done قابل قبول نیستند:
- "فایل با نام دقیق X.py وجود ندارد" (نام مهم نیست — رفتار مهم است)
- "این کد در فایل دیگری است" (مهم نیست کجاست — مهم وجود دارد یا نه)
- "ساختار با پرامپت اولیه فرق دارد" (پرامپت اولیه فقط پیشنهاد بود)
- "پیاده‌سازی متفاوت از انتظار است" (اگر AC را برآورده می‌کند، done است)

✅ **only valid not_done**: کد در هیچ‌جای repo وجود ندارد و هیچ نشانه‌ای
از آن قابلیت در فایل‌ها/tree/code search نیست. حداقل ۲ بار chunks را
دوباره بررسی کن قبل از گفتن not_done.

**مثال واقعی**:
- AC: «قابلیت کپی پرامپت در UI پیاده‌سازی شده»
- اگر در chunk‌های `page.tsx` متن «📋 کپی پرامپت» یا `onCopyPrompt` یا `navigator.clipboard.writeText` پیدا کردی → **done**
- اگر AC: «فرم ثبت ایده» و chunk‌ها `<textarea`, `setIdea`, `generatePrompt` دارند → **done** (حتی بدون فایل `IdeaForm.tsx`)
- اگر AC: «archive خودکار done‌ها» و chunk‌ها `archived`, `auto-archive`, `setArchived` دارند → **done**
- **اگر کاربر دستی تغییر داد** ولی نتیجه به acceptance criteria رسید → **done**.
- **اگر AI نسخهٔ متفاوت ولی قابل قبول‌تر نوشت** (مثلاً استفاده از pattern مدرن‌تر، error handling بهتر، یا decomposition متفاوت) → **done**.
- فقط زمانی **not_done** بگو که AC ها واقعاً (از نظر رفتاری) برآورده نشده‌اند یا کد رفتار غلط دارد.
- اگر بخشی از AC ها برآورده شده ولی بخشی نه → **partial**.
- اگر تغییرات نسبت به قبل وضع را بدتر کرده → **regressed**.

# 🎯 هدف اصلی پروژه (از زبان کاربر — معیار راهنما)
{user_goal or '(کاربر یادداشتی ثبت نکرده)'}

# تسک
عنوان: {task.title}
نوع: {task.type}
اولویت: {task.priority}
{('سوابق اجرا: این تسک از طریق Inspector apply-action اجرا شده — PR: ' + pr_url + (' (شاخه: ' + pr_branch + ')' if pr_branch else '') + f'. فایل‌های مرتبط از branch `{branch}` خوانده شده‌اند (منبع: {branch_source}).') if pr_url else ('شاخه‌ای که فایل‌ها از آن خوانده شده: `' + branch + '`.')}

پرامپت کامل تسک:
\"\"\"
{task.prompt[:6000]}
\"\"\"

{runtime_evidence_blob}

# معیارهای پذیرش (Acceptance Criteria)
{ac_lines}

{steps_blob}

{machine_evidence_blob}

# محتوای فعلی فایل‌های مرتبط (از repository)
{files_blob[:20000]}

# 🗂 ساختار پروژه (مسیرهای کلیدی repo — برای کشف فایل‌های هم‌نقش)
**این لیست را با دقت اسکن کن قبل از گفتن "فایل وجود ندارد".**
اگر در پرامپت فایل خاصی ذکر شده ولی در «محتوای فعلی فایل‌ها» یافت نشده،
حتماً در این tree دنبال فایل‌های هم‌نقش بگرد. مثال: اگر پرامپت idea.py
خواسته ولی فقط `oversight_service.py` (که مدل Idea را تعریف می‌کند) وجود
دارد، **این done است نه not_done**.

```
{tree_blob[:8000] if tree_blob else '(tree در دسترس نیست — تنها بر اساس فایل‌های ارائه‌شده قضاوت کن)'}
```

# کامیت‌های اخیر
{commits_blob}

# وظیفه
هر معیار پذیرش را جداگانه بررسی کن:
- آیا در وضعیت فعلی پروژه برآورده شده؟ (بله/خیر/تا حدی)

سپس وضعیت کلی را تعیین کن:
- "done" = همهٔ معیارها برآورده شده
- "partial" = بخشی از معیارها برآورده شده
- "not_done" = هیچ تغییر معناداری انجام نشده
- "regressed" = نسبت به قبل بدتر شده
- "error" = در بررسی خطا داشتی

# 📋 قواعد پر کردن done_parts و remaining_parts (بسیار مهم — رعایت کن)
- **done_parts** = فهرست بخش‌های مشخص (نه paragraph) که در وضعیت فعلی repo
  انجام شده‌اند. هر آیتم یک جملهٔ کوتاه (حداکثر 150 کاراکتر). اگر کاری
  انجام نشده، آرایهٔ خالی `[]` بگذار، نه null.
- **remaining_parts** = فهرست بخش‌هایی که هنوز انجام نشده‌اند. هر آیتم
  یک جملهٔ کوتاه (حداکثر 150 کاراکتر). اگر همه انجام شده، `[]` بگذار.
- **هر معیار پذیرش (AC) باید دقیقاً در یکی از این دو لیست منعکس شود** —
  نه هر دو، نه هیچ‌کدام.
- **next_actions** = اگر status="done" نیست، حداقل یک قدم بعدی concrete.
  هر آیتم یک جمله، حداکثر 150 کاراکتر.
- **confidence_score** = عدد بین 0.0 و 1.0 — اگر مطمئن هستی نزدیک 1.0،
  اگر شک داری 0.5-0.7، اگر نمی‌توانی قضاوت کنی زیر 0.3.
- **اگر status="partial"** ولی remaining_parts خالی باشد، در logs ثبت
  می‌شود که AI خطا داشته — باید حتماً remaining_parts را پر کنی.
- **آیتم‌های لیست‌ها فارسی باشند** (مگر نام فایل/کد).
- **محدودیت طول حیاتی برای جلوگیری از truncation**:
  - هر `evidence` در `criteria_results` حداکثر **80 کاراکتر** (فقط نام فایل/تابع کلیدی).
  - هر آیتم `done_parts`/`remaining_parts` حداکثر **140 کاراکتر**.
  - `summary` حداکثر **250 کاراکتر**.
  - **`criteria_results` کاملاً حذف شد** — دیگر آن را در خروجی نگذار. کل اطلاعات معیارها در `done_parts`/`remaining_parts` می‌آید (هر AC یک آیتم در یکی از این دو لیست).
  - **خیلی مهم**: JSON باید کامل (با `}}` نهایی) برگردد و فشرده باشد.

# خروجی فقط JSON (بدون code block markdown — فقط JSON خام)
{{
  "status": "done | partial | not_done | regressed | error",
  "done_parts": ["جملهٔ کوتاه دربارهٔ کار انجام‌شده 1", "..."],
  "remaining_parts": ["جملهٔ کوتاه دربارهٔ کار باقی‌مانده 1", "..."],
  "evidence": {{ "commits": ["sha"], "files": ["path"], "issues": [] }},
  "next_actions": ["قدم بعدی concrete 1", "..."],
  "confidence_score": 0.95,
  "summary": "خلاصه یک‌پاراگرافی"{steps_json_template}
}}"""

    try:
        # 🆕 max_tokens از 7000 به 10000 افزایش — برای task‌هایی با ۱۰+ AC
        # که حتی با محدودیت 80 کاراکتر هر evidence، JSON طولانی می‌شود.
        # همراه با کاهش criteria_results به max 3 (در prompt)، باید کافی باشد.
        response = await service._ai_generate(
            verify_prompt, model_id=model_id, max_tokens=10000, temperature=0.1
        )
        # detection بهبود یافته: اگر هر criterion.evidence به نظر cut شده
        # (مثلاً با کاما تمام نشده، با حرف غیر مرتبط تمام شده)، retry با
        # max_tokens بیشتر و instruction خلاصه‌نویسی
        def _looks_truncated(resp: str) -> bool:
            if not resp or len(resp) < 100:
                return False
            stripped = resp.rstrip()
            # حالت بدیهی: JSON ناتمام
            if not stripped.endswith(("}", "]", "}\n", "]\n")):
                return True
            # حالت ظریف: JSON با } بسته شده ولی string‌های داخلی truncated
            # شاخص: تعداد } و { برابر نیست در نسخهٔ raw
            try:
                opens = stripped.count("{")
                closes = stripped.count("}")
                if opens != closes:
                    return True
            except Exception:
                pass
            return False

        if _looks_truncated(response):
            logger.warning("verify response به نظر truncated است — retry با max_tokens=10000")
            try:
                response = await service._ai_generate(
                    verify_prompt + "\n\n# ⚠️ مهم: evidence هر criterion را حداکثر 100 کاراکتر بنویس تا JSON کامل برگردد.",
                    model_id=model_id,
                    max_tokens=10000,
                    temperature=0.1,
                )
            except Exception:
                pass
    except Exception as e:
        logger.exception("verify ai_generate failed")
        # ذخیرهٔ گزارش error
        report = OversightReport(
            id=str(uuid.uuid4()),
            task_id=task.id,
            watched_id=task.watched_id,
            project_full_name=task.project_full_name,
            run_at=now_iso(),
            status=VERIFICATION_ERROR,
            done_parts=[],
            remaining_parts=[_ac_text_of(c) for c in acceptance_criteria],
            evidence={"error": str(e)},
            next_actions=["تلاش مجدد در دور verify بعدی"],
            confidence_score=0.0,
            raw_response="",
            model_id=model_id or "",
        )
        async with service._lock:
            service.reports.insert(0, report)
            service._save_reports()
        return {"task": task.to_dict(), "report": report.to_dict()}

    parsed = service._extract_json(response) or {}
    # 🆕 partial JSON recovery — اگر کل parse fail کرد یا فیلدهای مهم ناقص است،
    # تلاش کن آرایه‌های اصلی (done_parts, remaining_parts, next_actions, status,
    # summary, confidence_score) را مستقیماً با regex extract کنی. این برای
    # مواردی که JSON در criteria_results truncate شد ولی بقیه فیلدها در ابتدای
    # JSON کامل تولید شده‌اند، ضروری است.
    if not parsed or not parsed.get("status"):
        try:
            recovered = _recover_partial_json(response)
            if recovered:
                # merge: parsed مقدم است (اگر JSON کامل بود) ولی recovered fallback
                for k, v in recovered.items():
                    if k not in parsed or not parsed[k]:
                        parsed[k] = v
        except Exception as _e:
            logger.debug(f"partial JSON recovery failed: {_e}")
    # 🆕 (audit) criteria_results دیگر در خروجی expected نیست — اگر AI همچنان
    # تولید کرد، آن را drop کن (چون ممکن است truncated باشد و JSON ناقص نشان
    # دهد). اطلاعات کامل معیارها در done_parts/remaining_parts است.
    if "criteria_results" in parsed:
        del parsed["criteria_results"]
    status_val = parsed.get("status") or VERIFICATION_PARTIAL
    if status_val not in (
        VERIFICATION_DONE,
        VERIFICATION_PARTIAL,
        VERIFICATION_NOT_DONE,
        VERIFICATION_REGRESSED,
        VERIFICATION_ERROR,
    ):
        status_val = VERIFICATION_PARTIAL

    # 🔬 (Runtime Verify Stage 5) — Runtime probe override policy:
    # اگر probe ها نتیجهٔ روشن دادند، نظر AI را override کن. این برای
    # حذف false-positive (AI گفت done ولی runtime fail است) و
    # false-negative (AI گفت not_done ولی runtime pass است) ضروری است.
    if runtime_probe_results:
        runtime_failed = [
            r for r in runtime_probe_results if r.status == "failed"
        ]
        runtime_passed = [
            r for r in runtime_probe_results if r.status == "passed"
        ]
        # اگر ≥۱ probe runtime fail شد و AI گفت done → به partial تنزل
        if runtime_failed and status_val == VERIFICATION_DONE:
            logger.info(
                f"verify {task.id}: AI گفت done ولی {len(runtime_failed)} probe runtime fail شد — "
                f"به partial override می‌کنیم"
            )
            status_val = VERIFICATION_PARTIAL
            # remaining_parts را با AC هایی که runtime fail شدند پر کن
            failed_acs = [r.ac_text for r in runtime_failed]
            existing_remaining = list(parsed.get("remaining_parts") or [])
            for fa in failed_acs:
                if fa and fa not in existing_remaining:
                    existing_remaining.append(fa)
            parsed["remaining_parts"] = existing_remaining[:10]
        # اگر **همهٔ** probe ها runtime pass شدند (با حداقل 1 probe non-skipped
        # و هیچ failed) و AI گفت not_done یا partial → به done ارتقا.
        # این طبق spec: «اگر runtime ✅ ولی AI گفت not_done → AI override کن به done»
        elif (
            len(runtime_passed) >= 1
            and not runtime_failed
            and not any(r.status == "error" for r in runtime_probe_results)
            and status_val in (VERIFICATION_NOT_DONE, VERIFICATION_PARTIAL)
        ):
            logger.info(
                f"verify {task.id}: AI گفت {status_val} ولی {len(runtime_passed)} probe "
                f"runtime همه pass و هیچ probe fail/error نداریم — به done override می‌کنیم"
            )
            status_val = VERIFICATION_DONE
            # done_parts را با AC هایی که runtime pass شدند پر کن
            existing_done = list(parsed.get("done_parts") or [])
            for rp in runtime_passed:
                if rp.ac_text and rp.ac_text not in existing_done:
                    existing_done.append(rp.ac_text)
            parsed["done_parts"] = existing_done[:20]
            # remaining_parts را خالی کن
            parsed["remaining_parts"] = []

    touched_codex: Dict[str, Any] = {}
    if watched and target_files:
        try:
            from .oversight_codex_service import get_codex_for_files

            touched_codex = get_codex_for_files(watched.id, target_files) or {}
        except Exception:
            touched_codex = {}

    report = OversightReport(
        id=str(uuid.uuid4()),
        task_id=task.id,
        watched_id=task.watched_id,
        project_full_name=task.project_full_name,
        run_at=now_iso(),
        status=status_val,
        done_parts=parsed.get("done_parts") or [],
        remaining_parts=parsed.get("remaining_parts") or [],
        evidence=parsed.get("evidence") or {},
        next_actions=parsed.get("next_actions") or [],
        confidence_score=float(parsed.get("confidence_score") or 0.0),
        raw_response=response[:8000],
        model_id=model_id or "",
        user_goal=user_goal,
        touched_codex=touched_codex,
    )

    # 🆕 criteria_results دیگر ذخیره نمی‌شود (drop شد در parser بالا)
    # تمام اطلاعات معیارها در done_parts/remaining_parts است
    if parsed.get("summary"):
        report.evidence["summary"] = parsed["summary"]

    # 🔬 (Runtime Verify Stage 5+6) — probe results را در evidence ذخیره کن
    # همیشه runtime_status را ذخیره می‌کنیم (حتی وقتی probe نخورد) تا
    # کاربر بفهمد چرا (مثلاً RUNTIME_VERIFY_ENABLED=false یا empty AC).
    report.evidence["runtime_status"] = runtime_status_note
    if runtime_probe_results:
        report.evidence["runtime_probes"] = [
            r.to_dict() for r in runtime_probe_results
        ]
        report.evidence["runtime_probes_summary"] = {
            "total": len(runtime_probe_results),
            "passed": sum(1 for r in runtime_probe_results if r.status == "passed"),
            "failed": sum(1 for r in runtime_probe_results if r.status == "failed"),
            "skipped": sum(1 for r in runtime_probe_results if r.status == "skipped"),
            "error": sum(1 for r in runtime_probe_results if r.status == "error"),
        }
        if runtime_run_id:
            report.evidence["runtime_run_id"] = runtime_run_id

    # 🛡 fallback warning: اگر AI status=partial داد ولی remaining_parts خالی،
    # یا status=not_done ولی همه پر، یک warning log کن
    if status_val == VERIFICATION_PARTIAL and not report.remaining_parts:
        logger.warning(
            f"verify: status=partial ولی remaining_parts خالی است (task={task.id}). "
            f"AI verifier prompt را رعایت نکرده. fallback: استفاده از acceptance_criteria."
        )
        report.remaining_parts = [_ac_text_of(c) for c in acceptance_criteria[:5]]
    if status_val == "not_done" and not report.remaining_parts:
        report.remaining_parts = [_ac_text_of(c) for c in acceptance_criteria[:5]]

    # به‌روزرسانی task
    streak_required = 2
    if watched and getattr(watched, "confirmation_streak_required", None):
        streak_required = max(1, int(watched.confirmation_streak_required))

    # 🆕 (Multi-pass Checklist) — اگر task_steps دارد، استاتوس هر مرحله را
    # از parsed["steps_status"] روی task.task_steps اعمال کن.
    steps_status_raw = parsed.get("steps_status") or []
    all_steps_done = False
    if task_steps_list and isinstance(steps_status_raw, list):
        # index by id
        status_by_id: Dict[Any, Dict[str, Any]] = {}
        for entry in steps_status_raw:
            if not isinstance(entry, dict):
                continue
            sid = entry.get("id")
            if sid is None:
                continue
            try:
                status_by_id[int(sid)] = entry
            except Exception:
                status_by_id[sid] = entry

        updated_steps: List[Dict[str, Any]] = []
        completion_sum = 0
        done_count = 0
        for s in task_steps_list:
            sid = s.get("id")
            try:
                sid_key = int(sid)
            except Exception:
                sid_key = sid
            new_entry = dict(s)
            upd = status_by_id.get(sid_key) or status_by_id.get(str(sid_key)) or {}
            new_status = (upd.get("status") or s.get("status") or "pending").strip().lower()
            if new_status not in ("done", "partial", "not_done", "pending", "error"):
                new_status = "pending"
            # completion_pct
            try:
                pct = int(upd.get("completion_pct", s.get("completion_pct", 0)) or 0)
            except Exception:
                pct = 0
            if new_status == "done":
                pct = 100
            elif new_status == "not_done":
                pct = 0
            elif new_status == "partial":
                pct = max(1, min(99, pct or 50))
            new_entry["status"] = new_status
            new_entry["completion_pct"] = pct
            new_entry["remaining"] = (upd.get("remaining") or "").strip() if new_status != "done" else ""
            if upd.get("evidence"):
                new_entry["evidence"] = str(upd.get("evidence"))[:300]
            new_entry["last_verified_at"] = now_iso()
            if new_status == "done":
                done_count += 1
                if not new_entry.get("completed_at"):
                    new_entry["completed_at"] = now_iso()
            else:
                new_entry["completed_at"] = None
            completion_sum += pct
            updated_steps.append(new_entry)

        # overall %
        total_steps = len(updated_steps)
        overall_pct = int(round(completion_sum / total_steps)) if total_steps else 0
        all_steps_done = total_steps > 0 and done_count == total_steps
        # apply — به‌جای mutation مستقیم روی task، نتایج را در متغیر نگه می‌داریم
        # تا داخل service._lock اعمال شوند (جلوگیری از race با خواننده‌های همزمان).
        _checklist_computed_steps = updated_steps
        _checklist_overall_pct = overall_pct

        # 🆕 اگر AI همه را done نشان داد ولی status کلی را done نگفت، در صورت
        # کامل بودن چک‌لیست، status_val را به done بالا ببر تا transition عادی
        # streak/auto-done اجرا شود (verifier ممکن است محافظه‌کار باشد).
        if all_steps_done and status_val != VERIFICATION_DONE:
            status_val = VERIFICATION_DONE
        # 🆕 برعکس: اگر AI status=done گفت ولی همهٔ مراحل done نیستند،
        # به partial تنزل بده — تسک واقعاً تمام نشده.
        elif (not all_steps_done) and status_val == VERIFICATION_DONE and total_steps > 0:
            logger.info(
                f"verify: AI گفت done ولی {done_count}/{total_steps} مرحله done است — "
                f"به partial تنزل می‌دهیم."
            )
            status_val = VERIFICATION_PARTIAL
            # report.status هم به‌روز شود
            report.status = VERIFICATION_PARTIAL

        # 🆕 markdown checkbox state — محاسبه بیرون lock، اعمال داخل lock
        try:
            _checklist_synced_prompt: Optional[str] = _sync_prompt_checkboxes(
                task.prompt or "", updated_steps
            )
        except Exception as _e:
            logger.debug(f"sync prompt checkboxes failed: {_e}")
            _checklist_synced_prompt = None
    else:
        _checklist_computed_steps = None
        _checklist_overall_pct = None
        _checklist_synced_prompt = None

    async with service._lock:
        # 🔒 اعمال نتایج checklist روی task (داخل lock — atomic با بقیهٔ به‌روزرسانی‌ها)
        if _checklist_computed_steps is not None:
            task.task_steps = _checklist_computed_steps
            if _checklist_overall_pct is not None:
                task.overall_completion_pct = _checklist_overall_pct
            if _checklist_synced_prompt is not None and _checklist_synced_prompt != task.prompt:
                task.prompt = _checklist_synced_prompt

        service.reports.insert(0, report)
        task.last_verification_report_id = report.id
        task.last_verified_at = now_iso()
        task.verification_history.append(
            {
                "report_id": report.id,
                "verified_at": report.run_at,
                "status": status_val,
                "triggered_by": triggered_by,
                "summary": parsed.get("summary") or "",
            }
        )
        # محدودیت تاریخچه
        if len(task.verification_history) > 30:
            task.verification_history = task.verification_history[-30:]

        if status_val == VERIFICATION_DONE:
            task.confirmation_streak += 1
            # 🆕 (audit fix) — وقتی task_steps دارد و *همهٔ* مراحل done شدند
            # (per-step verified)، streak guard دور زده می‌شود. این سیگنال
            # دقیق‌تر از یک verify کلی است و کاربر منتظر «verify بعدی»
            # نمی‌ماند برای کاری که ۱۰۰٪ checklist تأیید شده.
            bypass_streak = bool(
                all_steps_done and (task.task_steps or [])
            )
            if task.confirmation_streak >= streak_required or bypass_streak:
                task.verification_status = "done"
                task.status = "done"
                # 🆕 (P3) auto-archive وقتی هم status هم verification_status = done
                # تسک از فهرست فعال حذف می‌شود ولی در آرشیو قابل مشاهده است
                if not getattr(task, "archived", False):
                    task.archived = True
                    task.archived_at = now_iso()
            else:
                task.verification_status = "partial"
                task.status = "awaiting_review"
        elif status_val == VERIFICATION_PARTIAL:
            task.confirmation_streak = 0
            task.verification_status = "partial"
            task.status = "awaiting_review"
        elif status_val == VERIFICATION_REGRESSED:
            task.confirmation_streak = 0
            task.verification_status = "regressed"
            task.status = "pending"
        elif status_val == VERIFICATION_NOT_DONE:
            task.confirmation_streak = 0
            task.verification_status = "pending"
            # اگر کاربر گفته بود externally applied ولی نتیجه not_done → برگرد به pending
            if task.manually_marked_applied_at:
                task.verification_status = "needs_clarification"
            task.status = "pending" if task.status not in ("running", "cancelled") else task.status
        else:
            task.verification_status = "needs_clarification"

        task.updated_at = now_iso()
        service._save_reports()
        service._save_tasks()

    # 🔁 Follow-up prompt: پس از append تاریخچه، اگر status != done
    # یک پرامپت "ادامه" ساخته و روی task ست می‌شود تا کاربر در دور
    # بعدی بتواند آن را copy/apply کند. اگر done شد، followup reset می‌شود.
    try:
        await service.apply_followup_after_verify(task.id, report)
        # تسک به‌روزشده را دوباره بخوان (followup_prompt حالا ست شده)
        task = next((t for t in service.tasks if t.id == task.id), task)
    except Exception as _e:
        logger.warning(f"apply_followup_after_verify failed: {_e}")

    # event hook
    try:
        await service._emit(
            "task.verified",
            {"task": task.to_dict(), "report": report.to_dict(), "triggered_by": triggered_by},
        )
    except Exception:
        pass

    # 🔔 notification — در background اجرا می‌شود تا API verify بدون انتظار
    # برای PDF generation (که ممکن است چند ثانیه طول بکشد) پاسخ دهد.
    async def _send_verify_notification_bg(_task: "OversightTask", _report: "OversightReport") -> None:
        try:
            from .notification_service import notification_service
            from .oversight_verify_pdf import (
                build_verify_checklist_message,
                build_verify_report_pdf,
            )
            # نگاشت status → event دقیق
            status_to_event = {
                "done": "verify_done",
                "partial": "verify_partial",
                "not_done": "verify_not_done",
                "regressed": "verify_regressed",
                "needs_clarification": "verify_clarification",
            }
            event = status_to_event.get(_task.verification_status, "verify_done")

            # 🆕 (Checklist Notification) — متن چک‌لیستی کوتاه به‌عنوان caption،
            # و PDF کامل (شامل متن کامل پرامپت + جزئیات همهٔ مراحل) به‌عنوان پیوست.
            msg_text = build_verify_checklist_message(_task, _report)
            # streak تکمیلی در caption
            if _task.confirmation_streak and streak_required > 1 and "streak:" not in msg_text:
                msg_text += f"\n🔁 streak: {_task.confirmation_streak}/{streak_required}"

            # تولید PDF (best-effort — اگر failed، attachment=None و فقط متن می‌رود)
            attachment_payload: Optional[Dict[str, Any]] = None
            try:
                pdf_bytes, pdf_filename = await build_verify_report_pdf(_task, _report)
                attachment_payload = {
                    "bytes": pdf_bytes,
                    "filename": pdf_filename,
                }
            except Exception as _pdf_err:
                logger.warning(f"verify pdf generation failed: {_pdf_err}")
                attachment_payload = None

            # PR link اگر موجود — applied_evidence ممکن است dict/None/خراب باشد
            extra_buttons = None
            ae = _task.applied_evidence
            if isinstance(ae, dict):
                pr_url = ae.get("pr_url")
                if pr_url:
                    extra_buttons = [{"text": "🔀 دیدن PR", "url": pr_url}]
            # priority برای gate و hashtag
            priority = _task.priority or "low"
            # regressed همیشه بحرانی محسوب می‌شود
            if _task.verification_status == "regressed":
                priority = "critical"

            await notification_service.notify_event(
                event,
                msg_text,
                subject=f"Verify {_task.verification_status}",
                priority=priority,
                project_name=_task.project_full_name,
                watched_id=_task.watched_id,
                extra_hashtags=[_task.type] if _task.type else None,
                extra_buttons=extra_buttons,
                attachment=attachment_payload,
            )

            # 🔬 (inspector_probe Phase 1) — ضمیمه کردن screenshot های auto-verify
            # به همان نوتیفیکیشن (به‌عنوان پیام‌های پی‌درپی photo). در صورت موفقیت
            # ارسال هر screenshot، فایل آن از دیسک پاک می‌شود و در evidence نشان
            # archived_to_telegram=True ست می‌گردد. اگر تلگرام شکست بخورد، فایل
            # روی دیسک می‌ماند و TTL cleanup در آینده آن را برمی‌دارد.
            try:
                await _send_runtime_screenshots_and_cleanup(_task, _report)
            except Exception as _se:
                logger.debug(f"send runtime screenshots failed: {_se}")
        except Exception as e:
            logger.debug(f"notification skipped: {e}")

    try:
        # snapshot از task فعلی بگیر — اگر بعد از این تغییری روی task شد،
        # background task نسخهٔ خوانده‌شده در همین لحظه را می‌فرستد.
        import asyncio as _asyncio
        _asyncio.create_task(_send_verify_notification_bg(task, report))
    except Exception as _e:
        logger.debug(f"schedule notification failed: {_e}")

    return {
        "task": task.to_dict(),
        "report": report.to_dict(),
        "streak": task.confirmation_streak,
        "streak_required": streak_required,
        "final": task.verification_status == "done",
        "followup_available": bool(task.followup_prompt),
        "followup_round": task.followup_round,
    }
