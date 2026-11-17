"""PM-INS-0018 — «🩹 خوداصلاح» ِ بازرس ویژه.

با هر خطای تازهٔ پیش‌نمایش (خطای JS، console.error، لایهٔ خطا) فرانت این‌جا را صدا می‌زند؛ این ماژول
فایل‌های مرتبط را از GitHub ِ همان پروژه می‌خواند، از یک مدل تحلیل + **پیشنهادِ diff** می‌گیرد و
برمی‌گرداند. **هیچ‌چیز را اعمال نمی‌کند** — اعمال فقط با تأییدِ مالک و از مسیرِ موجودِ
`/inspector/fix` (شاخه + PR) است. توابعِ خالص جدا هستند تا بی‌شبکه تست شوند.
"""

from __future__ import annotations

import json
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

CODE_EXT = (".js", ".mjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte", ".html", ".css", ".py", ".go", ".rs")
MAX_FILES = 4
MAX_FILE_CHARS = 6000

_URL_RE = re.compile(r"https?://\S+")
_NUM_RE = re.compile(r"\d+")
_HEX_RE = re.compile(r"\b[0-9a-f]{8,}\b", re.I)
_STACK_FILE_RE = re.compile(r"([\w\-./]+\.(?:m?js|tsx?|jsx|vue|svelte|html|css|py))(?::\d+){0,2}", re.I)


def error_signature(message: str) -> str:
    """یک امضای پایدار برای «همان خطا» — عدد، نشانی و هش حذف می‌شوند تا تکرارِ یک خطا دوباره تحلیل نشود."""
    s = (message or "").strip().lower()
    s = _URL_RE.sub("<url>", s)
    s = _HEX_RE.sub("<hex>", s)
    s = _NUM_RE.sub("<n>", s)
    s = re.sub(r"\s+", " ", s)
    return s[:240]


def resolve_repo(project: Any) -> Optional[tuple]:
    """owner/repo ِ پروژه — از extra_data (owner/repo) یا github_path (نشانیِ کامل یا owner/repo)."""
    extra: Dict[str, Any] = {}
    raw = getattr(project, "extra_data", None)
    if isinstance(raw, dict):
        extra = raw
    elif raw:
        try:
            extra = json.loads(raw) or {}
        except Exception:  # noqa: BLE001
            extra = {}
    owner, repo = str(extra.get("owner") or ""), str(extra.get("repo") or "")
    if owner and repo:
        return owner, repo
    gp = str(getattr(project, "github_path", "") or "")
    gp = gp.replace("https://github.com/", "").replace("http://github.com/", "")
    gp = gp[:-4] if gp.endswith(".git") else gp
    parts = [p for p in gp.strip("/").split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def pick_relevant_paths(all_paths: List[str], error_text: str, limit: int = MAX_FILES) -> List[str]:
    """اول فایل‌هایی که در stack/پیامِ خطا نامشان آمده (بر اساسِ نامِ فایل)، بعد امتیازِ کلیدواژه، بعد فایل‌های اصلی."""
    code = [p for p in all_paths if p.lower().endswith(CODE_EXT) and "node_modules/" not in p and ".min." not in p]
    chosen: List[str] = []

    def add(p: str) -> None:
        if p not in chosen and len(chosen) < limit:
            chosen.append(p)

    for ref in _STACK_FILE_RE.findall(error_text or ""):
        base = ref.rsplit("/", 1)[-1].lower()
        # نامِ فایلِ ساخته‌شده (app.3f9a.js) را هم به app.js برگردان
        stem = re.sub(r"\.[0-9a-f]{6,}(?=\.)", "", base)
        for p in code:
            pb = p.rsplit("/", 1)[-1].lower()
            if pb == base or pb == stem or (ref.lower().lstrip("./") and p.lower().endswith(ref.lower().lstrip("./"))):
                add(p)
    if len(chosen) < limit:
        words = {w for w in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{3,}", error_text or "")}
        scored = []
        for p in code:
            pl = p.lower()
            score = sum(1 for w in words if w.lower() in pl)
            if score:
                scored.append((score, p))
        for _, p in sorted(scored, key=lambda x: (-x[0], x[1])):
            add(p)
    if len(chosen) < limit:
        for p in code:
            if any(k in p.lower().rsplit("/", 1)[-1] for k in ("index", "main", "app", "script")):
                add(p)
    return chosen


def build_prompt(error_message: str, log_details: str, page_url: str, files: Dict[str, str]) -> str:
    parts = [
        "خطای زیر همین حالا در پیش‌نمایشِ زندهٔ یک وب‌اپ رخ داد. علت را پیدا کن و کمینه‌ترین اصلاح را به شکلِ unified diff پیشنهاد بده.",
        f"\n## خطا\n{error_message}",
        f"\n## جزئیات / لاگ‌های اطراف\n{log_details or 'ندارد'}",
        f"\n## صفحه\n{page_url or 'نامشخص'}",
        "\n## فایل‌های مرتبط از مخزن",
    ]
    for path, content in files.items():
        parts.append(f"\n### {path}\n```\n{content[:MAX_FILE_CHARS]}\n```")
    if not files:
        parts.append("\n(هیچ فایلی خوانده نشد — اگر بی‌کد نمی‌شود اصلاح را مشخص کرد، diff را خالی بگذار و بگو چه لازم است.)")
    parts.append(
        "\n## قالبِ پاسخ — فقط JSON\n"
        '{"analysis": "علتِ ریشه‌ای به فارسی، کوتاه", '
        '"files": [{"path": "مسیر", "issue": "مشکلِ این فایل"}], '
        '"diff": "unified diff با سربرگ‌های --- a/<path> و +++ b/<path>؛ خالی اگر مطمئن نیستی", '
        '"confidence": "high|medium|low"}\n'
        "diff فقط فایل‌هایی را عوض کند که محتوایشان را دیدی؛ چیزی را حذف نکن که به خطا ربط ندارد."
    )
    return "\n".join(parts)


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        return m.group(1)
    i, j = t.find("{"), t.rfind("}")
    return t[i:j + 1] if i != -1 and j > i else t


def parse_proposal(text: str) -> Dict[str, Any]:
    """پاسخِ مدل ⇒ {analysis, files, diff, confidence}. اگر JSON نبود، diff را از بلوکِ ```diff بیرون می‌کشد."""
    out: Dict[str, Any] = {"analysis": "", "files": [], "diff": "", "confidence": "low"}
    try:
        data = json.loads(_strip_fences(text))
        if isinstance(data, dict):
            out["analysis"] = str(data.get("analysis") or "").strip()
            files = data.get("files") or data.get("source_files") or []
            out["files"] = [{"path": str(f.get("path", "")).strip(), "issue": str(f.get("issue", "")).strip()}
                            for f in files if isinstance(f, dict) and str(f.get("path", "")).strip()]
            out["diff"] = str(data.get("diff") or "").strip()
            c = str(data.get("confidence") or "low").lower()
            out["confidence"] = c if c in ("high", "medium", "low") else "low"
            return _fill_files_from_diff(out)
    except Exception:  # noqa: BLE001
        pass
    m = re.search(r"```(?:diff|patch)\s*\n(.*?)```", text or "", re.S)
    out["diff"] = m.group(1).strip() if m else ""
    out["analysis"] = re.sub(r"```.*?```", "", text or "", flags=re.S).strip()[:4000]
    return _fill_files_from_diff(out)


def _fill_files_from_diff(out: Dict[str, Any]) -> Dict[str, Any]:
    if out["diff"] and not out["files"]:
        seen = []
        for p in re.findall(r"^\+\+\+ (?:b/)?(\S+)", out["diff"], re.M):
            if p != "/dev/null" and p not in seen:
                seen.append(p)
        out["files"] = [{"path": p, "issue": ""} for p in seen]
    return out


Generate = Callable[[str, str], Awaitable[str]]
ListTree = Callable[[str, str], Awaitable[List[str]]]
ReadFile = Callable[[str, str, str], Awaitable[Optional[str]]]


async def propose(*, owner: str, repo: str, error_message: str, log_details: str, page_url: str, model_id: str,
                  list_tree: ListTree, read_file: ReadFile, generate: Generate) -> Dict[str, Any]:
    """تحلیل + پیشنهادِ diff. شبکه و مدل تزریق می‌شوند (تست بی‌شبکه)."""
    try:
        paths = await list_tree(owner, repo)
    except Exception:  # noqa: BLE001
        paths = []
    picked = pick_relevant_paths(paths, f"{error_message}\n{log_details}")
    files: Dict[str, str] = {}
    for p in picked:
        try:
            c = await read_file(owner, repo, p)
        except Exception:  # noqa: BLE001
            c = None
        if c:
            files[p] = c[:MAX_FILE_CHARS]
    raw = await generate(model_id, build_prompt(error_message, log_details, page_url, files))
    prop = parse_proposal(raw)
    return {
        "success": True,
        "signature": error_signature(error_message),
        "analysis": prop["analysis"] or "مدل علتی گزارش نکرد.",
        "files": prop["files"],
        "diff": prop["diff"],
        "confidence": prop["confidence"],
        "files_read": list(files.keys()),
        "github_repo": f"{owner}/{repo}",
        "model_used": model_id,
    }
