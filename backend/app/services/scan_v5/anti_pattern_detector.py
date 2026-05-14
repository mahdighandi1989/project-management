"""Phase 5 — Anti-pattern Detector (R10).

تشخیص ۱۱ نوع anti-pattern منطقی (نه syntactic — linter پیدا نمی‌کند):
  1. داده بی‌مصرف
  2. AI بدون validation
  3. Magic threshold
  4. Conflicting defaults
  5. Silent failure در crucial path
  6. Broken feedback loop (R11)
  7. Stale assumption
  8. Over/under-engineering
  9. Conditional inconsistency
  10. Threshold-Outcome mismatch (R11)
  11. Notification mismatch (R12)

API:
    detect_anti_patterns(file_contents, inventory, purpose_map,
                       verify_model_id) -> List[Dict]
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_AI_TIMEOUT_S = 30
_MAX_FILES_FOR_AI_AUDIT = 8


# ─────────────────────────────────────────────────────────────────────────
# Structural detectors (regex-based — fast)
# ─────────────────────────────────────────────────────────────────────────

def _detect_magic_thresholds(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    """Magic threshold: number literal in conditional without comment."""
    out: List[Dict[str, Any]] = []
    threshold_re = re.compile(
        r"(?:^|\s)(?:if|elif|while|assert)\s+[^:#\n]{0,100}([><=!]=?\s*0\.\d+)",
    )
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        for m in threshold_re.finditer(content[:50000]):
            line_no = content[:m.start()].count("\n") + 1
            line = content.splitlines()[line_no - 1] if line_no <= len(content.splitlines()) else ""
            # has comment? skip
            if "#" in line:
                continue
            out.append({
                "kind": "magic_threshold",
                "file": path,
                "line": line_no,
                "snippet": line.strip()[:120],
                "reason": "number literal in conditional without explanation comment",
            })
            if len(out) >= 30:
                return out
    return out


def _detect_silent_failures(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    """`except Exception: pass` در crucial path."""
    out: List[Dict[str, Any]] = []
    pattern = re.compile(r"except\s+[a-zA-Z_]*[Ee]xception[a-zA-Z_]*:?\s*\n\s*pass")
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        for m in pattern.finditer(content[:50000]):
            line_no = content[:m.start()].count("\n") + 1
            out.append({
                "kind": "silent_failure",
                "file": path,
                "line": line_no,
                "reason": "bare 'except: pass' — هیچ‌چیز handle یا log نمی‌شود",
            })
            if len(out) >= 30:
                return out
    return out


def _detect_unused_data_writes(
    file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """داده‌ای که write می‌شود ولی هرگز read نمی‌شود (heuristic).

    write: `self.X = ...` (با =)
    read: `self.X` که بلافاصله بعدش = نیست (با whitespace هم)
    """
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        truncated = content[:30000]
        # writes: self.X و سپس space/tab/= (شامل =)
        writes = set(re.findall(r"self\.([a-z_]\w*)\s*=(?!=)", truncated))
        # reads: self.X که بعدش = نیست (با whitespace شدید بعدش هم)
        reads = set()
        for m in re.finditer(r"self\.([a-z_]\w*)", truncated):
            end = m.end()
            # نگاه به chars بعدی، skip whitespace
            i = end
            while i < len(truncated) and truncated[i] in " \t":
                i += 1
            # اگر بعد از whitespace = (تنها) یا != و == ، write است نه read
            if i < len(truncated) and truncated[i] == "=":
                # check next char — `==` is read (comparison), `=` alone is write
                if i + 1 < len(truncated) and truncated[i + 1] == "=":
                    reads.add(m.group(1))
                # else: pure write — skip
            else:
                # هر چیز دیگر = read
                reads.add(m.group(1))
        unused = writes - reads - {"__init__", "id", "name"}
        for name in list(unused)[:5]:
            out.append({
                "kind": "unused_data_write",
                "file": path,
                "attribute": f"self.{name}",
                "reason": f"self.{name} write می‌شود ولی هرگز read نشده",
            })
        if len(out) >= 30:
            return out
    return out


def _detect_conflicting_defaults(
    file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """field با default متفاوت در چند جا."""
    out: List[Dict[str, Any]] = []
    # شناسایی dataclass fields با default
    # patterns: `field_name: type = default`
    field_defaults: Dict[str, List[tuple]] = {}  # field → [(path, default_value)]
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        for m in re.finditer(
            r"^\s+([a-z_]\w{3,})\s*:\s*[^=]+\s*=\s*([^\n]+)",
            content[:30000], re.MULTILINE,
        ):
            field, default = m.group(1), m.group(2).strip()
            if "field(" in default or "default_factory" in default:
                continue
            # skip private fields
            if field.startswith("_"):
                continue
            field_defaults.setdefault(field, []).append((path, default))
    # find conflicts
    for field, occurrences in field_defaults.items():
        if len(occurrences) < 2:
            continue
        defaults_set = set(d[1] for d in occurrences)
        if len(defaults_set) > 1:
            out.append({
                "kind": "conflicting_default",
                "field": field,
                "occurrences": [{"file": p, "default": d} for p, d in occurrences[:5]],
                "reason": f"field {field} has different defaults: {list(defaults_set)[:3]}",
            })
            if len(out) >= 20:
                break
    return out


# ─────────────────────────────────────────────────────────────────────────
# AI-driven detectors (slow but smart)
# ─────────────────────────────────────────────────────────────────────────

async def _ai_audit_logic(
    file_contents: Dict[str, str],
    purpose_map: Dict[str, Dict[str, Any]],
    verify_model_id: Optional[str],
) -> List[Dict[str, Any]]:
    """AI روی فایل‌های مهم برای logical anti-patterns audit کند."""
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception:
        return []
    if not verify_model_id:
        try:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            return []

    # انتخاب top-N file بر اساس importance
    sorted_paths = sorted(
        purpose_map.items(),
        key=lambda x: -x[1].get("importance_score", 0),
    )[:_MAX_FILES_FOR_AI_AUDIT]

    issues: List[Dict[str, Any]] = []
    for path, purpose in sorted_paths:
        content = file_contents.get(path, "")[:6000]
        if not content:
            continue
        prompt = (
            f"تو یک Senior Engineer هستی. این فایل را برای anti-pattern های منطقی\n"
            f"audit کن (نه syntactic — linter پیدا نمی‌کند):\n\n"
            f"📄 file: {path}\n"
            f"📋 stated_purpose: {purpose.get('stated_purpose', '')[:300]}\n"
            f"📋 expected_inputs: {purpose.get('expected_inputs', [])}\n"
            f"📋 expected_outputs: {purpose.get('expected_outputs', [])}\n\n"
            f"```python\n{content}\n```\n\n"
            "🔍 anti-patterns مورد جستجو:\n"
            "1. AI بدون validation (response استفاده می‌شود بدون چک)\n"
            "2. Broken feedback loop (outcome لاگ ولی به model برنمی‌گردد)\n"
            "3. Stale assumption (کد فرض می‌کند رفتار X خاصه، ولی X تغییر کرد)\n"
            "4. Over/under-engineering (پیچیدگی بیش/کم از نیاز)\n"
            "5. Conditional inconsistency (شرط‌ها با تغییرات اخیر inconsistent)\n"
            "6. Threshold-Outcome mismatch (parameters → نتیجه مطلوب نمی‌دهند)\n\n"
            "خروجی JSON خالص (اگر هیچ anti-pattern نبود، issues=[] برگردان):\n"
            "{\n"
            '  "issues": [\n'
            '    {"kind": "...", "description": "...", "line_hint": int, "priority": "high|medium|low"},\n'
            '    ...\n'
            '  ]\n'
            "}"
        )
        try:
            mgr = get_ai_manager()
            resp = await asyncio.wait_for(
                mgr.generate(
                    model_id=verify_model_id,
                    messages=[Message(role="user", content=prompt)],
                    max_tokens=1500,
                    temperature=0.1,
                    allow_fallback=True,
                ),
                timeout=_AI_TIMEOUT_S,
            )
            raw = (resp.content or "").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            s = raw.find("{"); e = raw.rfind("}")
            if s == -1 or e <= s:
                continue
            data = json.loads(raw[s:e + 1])
            for issue in (data.get("issues") or []):
                if not isinstance(issue, dict):
                    continue
                issues.append({
                    "kind": str(issue.get("kind", "anti_pattern"))[:50],
                    "file": path,
                    "line_hint": issue.get("line_hint"),
                    "description": str(issue.get("description", ""))[:400],
                    "priority": str(issue.get("priority", "medium")).lower(),
                    "_source": "ai",
                })
        except Exception as e:
            logger.debug(f"AI audit failed for {path}: {e}")
    return issues


# ─────────────────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────────────────

async def detect_anti_patterns(
    file_contents: Dict[str, str],
    inventory: Dict[str, Any],
    purpose_map: Dict[str, Dict[str, Any]],
    verify_model_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """تشخیص anti-pattern های منطقی.

    structural detectors سریع‌اند (regex), AI detector کند ولی هوشمندتر.
    """
    all_issues: List[Dict[str, Any]] = []

    # Fast structural detectors
    for detector_name, fn in [
        ("magic_threshold", lambda: _detect_magic_thresholds(file_contents)),
        ("silent_failure", lambda: _detect_silent_failures(file_contents)),
        ("unused_data_write", lambda: _detect_unused_data_writes(file_contents)),
        ("conflicting_default", lambda: _detect_conflicting_defaults(file_contents)),
    ]:
        try:
            items = fn()
            for it in items:
                it.setdefault("_source", "regex")
            all_issues.extend(items)
        except Exception as e:
            logger.warning(f"anti_pattern detector {detector_name} failed: {e}")

    # AI-driven (slow but covers complex patterns)
    try:
        ai_issues = await _ai_audit_logic(file_contents, purpose_map, verify_model_id)
        all_issues.extend(ai_issues)
    except Exception as e:
        logger.warning(f"AI anti-pattern audit failed: {e}")

    return all_issues
