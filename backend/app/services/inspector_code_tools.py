"""Code tools that let WEAK models work on big files (owner, 2026-11-15, plan item 12 — «با ضعیف‌ترین مدل‌ها بهترین خروجی»).

Why the «بازرس ویژه» chat was weak (audit, WORKLOG ۱۵-۱۱ (۱۱)): `read_file` cut every file at 18 000 characters
(≈ the first 400 lines — this repo's hot files have ~18 000 lines), there was no way to read a later part, search, or
see a file's outline, and `submit_action_plan` accepted any `find` text — so models copied «find» blocks from code
they never saw and the apply step fuzzy-matched the wrong block.

Pure functions (no I/O) so they are unit-tested; `inspector_agent.py` wires them into the tool loop:
  * numbered line ranges        — `numbered(content, start, end)`
  * a file outline              — `outline(path, content)` (defs/classes/exports with line numbers)
  * search                      — `search(files, pattern)` → `path:line: text`
  * verify find-texts           — `check_sections(content, sections)` → misses with the closest real snippets, so the
                                  model corrects itself instead of the apply step guessing.
"""

from __future__ import annotations

import ast
import difflib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

HEAD_LINES = 220          # what a plain read of a BIG file shows besides its outline
MAX_RANGE_LINES = 600     # one ranged read


def numbered(content: str, start: int = 1, end: Optional[int] = None) -> Tuple[str, int, int, int]:
    """Lines ``start..end`` (1-based, inclusive) with line numbers. Returns (text, start, end, total)."""
    lines = content.split("\n")
    total = len(lines)
    start = max(1, int(start or 1))
    end = min(total, int(end or start + MAX_RANGE_LINES - 1), start + MAX_RANGE_LINES - 1)
    width = len(str(end))
    text = "\n".join(f"{i:>{width}}| {lines[i - 1]}" for i in range(start, end + 1)) if start <= total else ""
    return text, start, end, total


_TS_DEF = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function\s+(\w+)|class\s+(\w+)|interface\s+(\w+)|type\s+(\w+)\s*=|"
    r"(?:const|let)\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\(|function|useCallback|useMemo|React\.|\w+\s*=>))")
_MD_HEAD = re.compile(r"^(#{1,4})\s+(.+)$")


def outline(path: str, content: str, limit: int = 400) -> List[str]:
    """`<line>: <kind> <name>` for the definitions in a file (Python via ast, TS/JS via regex, Markdown headings)."""
    out: List[str] = []
    if path.endswith(".py"):
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(node, ast.ClassDef) else "def"
                    out.append((node.lineno, f"{node.lineno}: {kind} {node.name}"))  # type: ignore[arg-type]
            out = [s for _, s in sorted(out)]  # type: ignore[misc]
        except SyntaxError:
            out = []
        if not out:
            out = [f"{i}: {ln.strip()[:80]}" for i, ln in enumerate(content.split("\n"), 1)
                   if re.match(r"^\s*(async\s+def|def|class)\s+\w+", ln)]
        # FastAPI routes are the most useful landmarks in route files
        out += [f"{i}: route {m.group(1)} {m.group(2)}" for i, ln in enumerate(content.split("\n"), 1)
                for m in [re.match(r'^\s*@\w+\.(get|post|put|patch|delete)\("([^"]+)"', ln)] if m]
    elif re.search(r"\.(tsx?|jsx?|mjs|cjs)$", path):
        for i, ln in enumerate(content.split("\n"), 1):
            m = _TS_DEF.match(ln)
            if m:
                name = next(g for g in m.groups() if g)
                out.append(f"{i}: {ln.strip()[:90]}" if len(ln.strip()) < 90 else f"{i}: {name}")
    elif path.endswith(".md"):
        out = [f"{i}: {m.group(1)} {m.group(2)[:80]}" for i, ln in enumerate(content.split("\n"), 1)
               for m in [_MD_HEAD.match(ln)] if m]
    return out[:limit]


def search(files: Dict[str, str], pattern: str, max_hits: int = 60, context: int = 0) -> List[str]:
    """`path:line: text` for every line matching ``pattern`` (regex, falling back to a literal search)."""
    try:
        rx = re.compile(pattern, re.I)
    except re.error:
        rx = re.compile(re.escape(pattern), re.I)
    hits: List[str] = []
    for path, content in files.items():
        lines = content.split("\n")
        for i, ln in enumerate(lines, 1):
            if rx.search(ln):
                if context:
                    lo, hi = max(1, i - context), min(len(lines), i + context)
                    block = "\n".join(f"  {j}| {lines[j - 1][:200]}" for j in range(lo, hi + 1))
                    hits.append(f"{path}:{i}\n{block}")
                else:
                    hits.append(f"{path}:{i}: {ln.strip()[:200]}")
                if len(hits) >= max_hits:
                    return hits
    return hits


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def find_occurs(content: str, find: str) -> bool:
    """Exact, or equal after collapsing whitespace (what the apply step also accepts without fuzzy guessing)."""
    if not find.strip():
        return False
    return find in content or _norm(find) in _norm(content)


def closest_snippets(content: str, find: str, n: int = 3) -> List[str]:
    """The ``n`` blocks of ``content`` (same number of lines as ``find``) most similar to ``find``, with line numbers."""
    lines = content.split("\n")
    k = max(1, min(len(find.strip().split("\n")), 40))
    first = _norm(find.strip().split("\n")[0])[:120]
    scored: List[Tuple[float, int]] = []
    for i in range(0, max(1, len(lines) - k + 1)):
        head = _norm(lines[i])[:120]
        if not head:
            continue
        r = difflib.SequenceMatcher(None, first, head).quick_ratio()
        if r > 0.45:
            scored.append((r, i))
    scored.sort(reverse=True)
    best: List[Tuple[float, int]] = []
    for _, i in scored[:60]:
        block = "\n".join(lines[i:i + k])
        best.append((difflib.SequenceMatcher(None, _norm(find), _norm(block)).ratio(), i))
    best.sort(reverse=True)
    out, used = [], set()
    for r, i in best:
        if any(abs(i - u) < k for u in used):
            continue
        used.add(i)
        out.append(f"(lines {i + 1}-{i + k}, similarity {r:.0%})\n" + "\n".join(lines[i:i + k]))
        if len(out) >= n:
            break
    return out


def check_sections(content: str, sections: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every section whose ``find`` does not occur in the real file, with the closest real snippets."""
    misses = []
    for idx, sec in enumerate(sections or []):
        find = str((sec or {}).get("find") or "")
        if not find_occurs(content, find):
            misses.append({"index": idx, "find": find[:400], "closest": closest_snippets(content, find)})
    return misses


def explain_misses(path: str, misses: List[Dict[str, Any]]) -> str:
    parts = [f"❌ در {path}، متنِ `find` ِ {len(misses)} بخش عیناً در فایلِ واقعی نیست. find باید کپیِ دقیقِ خطوطِ فعلیِ فایل باشد "
             "(بدونِ شماره‌خط). نزدیک‌ترین متن‌های واقعی:"]
    for m in misses[:5]:
        parts.append(f"\n— بخشِ {m['index'] + 1}، find ِ تو:\n{m['find']}\n— در فایل:")
        parts += m["closest"] or ["(چیزی شبیه پیدا نشد — با read_file و start_line/end_line همان قسمت را بخوان)"]
    parts.append("\naction_plan را با find های درست دوباره submit کن.")
    return "\n".join(parts)
