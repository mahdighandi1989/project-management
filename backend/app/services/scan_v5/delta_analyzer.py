"""Phase 5 — Delta Analyzer (R7 — تغییر-آگاهی).

تشخیص ۶ نوع تغییر بین scan فعلی و scan قبلی:
  - add: فایل جدید
  - remove: فایل حذف‌شده
  - modify: sha متفاوت
  - rename: sha مشابه، path متفاوت
  - move: محتوای مشابه (token overlap), path متفاوت
  - signature-change: تابع نام ثابت ولی parameters/return-type تغییر

API:
    build_current_state(file_contents) -> Dict[path, state_dict]
    compute_delta(prev_state, current_state) -> Dict[str, List[Dict]]
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def _sha256_hash(content: str) -> str:
    """sha256 از content."""
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _imports_hash(content: str, lang: str) -> str:
    """hash از import statements تنها — برای تشخیص signature/dependency changes."""
    if lang == "py":
        imports = re.findall(
            r"^\s*(?:from\s+[\w.]+\s+import\s+[\w,\s*]+|import\s+[\w.,\s]+)",
            content[:50000], re.MULTILINE,
        )
    else:
        imports = re.findall(
            r"^\s*import\s+[^;]+|^\s*const\s+\{[^}]*\}\s*=\s*require\([^)]+\)",
            content[:50000], re.MULTILINE,
        )
    return _sha256_hash("\n".join(sorted(imports)))


def _extract_function_signatures(content: str, path: str) -> Dict[str, str]:
    """signature های توابع — برای signature-change detection."""
    sigs: Dict[str, str] = {}
    if path.endswith(".py"):
        for m in re.finditer(
            r"^\s*(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)(?:\s*->\s*([^:]+))?:",
            content[:80000], re.MULTILINE,
        ):
            name = m.group(1)
            params = re.sub(r"\s+", " ", m.group(2)).strip()
            ret_type = (m.group(3) or "").strip()
            sigs[name] = f"({params}) -> {ret_type}"
    elif path.endswith((".ts", ".tsx", ".js", ".jsx")):
        # TS/JS function/arrow
        for m in re.finditer(
            r"(?:function|export\s+function|const)\s+([a-zA-Z_]\w*)\s*"
            r"(?:[<:][^=({]*)?\s*\(([^)]*)\)\s*(?::\s*([^={]+))?",
            content[:80000], re.MULTILINE,
        ):
            name = m.group(1)
            params = re.sub(r"\s+", " ", m.group(2)).strip()
            ret_type = (m.group(3) or "").strip()
            sigs[name] = f"({params}): {ret_type}"
    return sigs


def build_current_state(
    file_contents: Dict[str, str],
) -> Dict[str, Dict[str, Any]]:
    """ساخت state فعلی برای ذخیره و مقایسه در scan بعدی."""
    state: Dict[str, Dict[str, Any]] = {}
    for path, content in file_contents.items():
        lang = "py" if path.endswith(".py") else "js"
        sig_dict = _extract_function_signatures(content, path)
        state[path] = {
            "sha": _sha256_hash(content),
            "size": len(content),
            "imports_hash": _imports_hash(content, lang),
            "signatures_hash": _sha256_hash(
                "\n".join(f"{k}:{v}" for k, v in sorted(sig_dict.items()))
            ),
            "signature_count": len(sig_dict),
        }
    return state


def _token_overlap(content_a: str, content_b: str) -> float:
    """جاکارد token overlap (برای detection rename/move)."""
    tokens_a = set(re.findall(r"\b\w{4,}\b", content_a[:30000]))
    tokens_b = set(re.findall(r"\b\w{4,}\b", content_b[:30000]))
    if not tokens_a or not tokens_b:
        return 0.0
    inter = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return inter / union if union else 0.0


def compute_delta(
    prev_state: Optional[Dict[str, Dict[str, Any]]],
    current_state: Dict[str, Dict[str, Any]],
    file_contents: Optional[Dict[str, str]] = None,
    prev_contents: Optional[Dict[str, str]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """compute delta با ۶ نوع تغییر.

    Args:
        prev_state: state از scan قبلی
        current_state: state از scan فعلی
        file_contents: محتوای فایل‌های فعلی (برای move/rename detection)
        prev_contents: محتوای فایل‌های قبلی (اگر داریم)

    Returns:
        {"add": [...], "remove": [...], "modify": [...], "rename": [...],
         "move": [...], "signature_change": [...], "summary": {...}}
    """
    if not prev_state:
        # اولین scan — همه فایل‌ها "add"
        return {
            "add": [{"path": p} for p in current_state.keys()][:200],
            "remove": [],
            "modify": [],
            "rename": [],
            "move": [],
            "signature_change": [],
            "summary": {
                "first_scan": True,
                "add": len(current_state),
                "remove": 0, "modify": 0, "rename": 0,
                "move": 0, "signature_change": 0,
            },
        }

    prev_paths = set(prev_state.keys())
    cur_paths = set(current_state.keys())

    added_paths = cur_paths - prev_paths
    removed_paths = prev_paths - cur_paths
    common_paths = cur_paths & prev_paths

    modified: List[Dict[str, Any]] = []
    signature_changes: List[Dict[str, Any]] = []
    rename_candidates: List[str] = list(added_paths)  # ممکنه rename باشد
    removed_candidates: List[str] = list(removed_paths)

    for path in common_paths:
        prev = prev_state[path]
        cur = current_state[path]
        if prev.get("sha") != cur.get("sha"):
            modified.append({
                "path": path,
                "prev_size": prev.get("size"),
                "cur_size": cur.get("size"),
            })
            # signature-change detection
            if prev.get("signatures_hash") != cur.get("signatures_hash"):
                signature_changes.append({
                    "path": path,
                    "prev_count": prev.get("signature_count", 0),
                    "cur_count": cur.get("signature_count", 0),
                })

    # rename/move detection: file اضافه‌شده با sha شبیه فایل حذف‌شده
    renames: List[Dict[str, Any]] = []
    moves: List[Dict[str, Any]] = []
    matched_removed: Set[str] = set()
    for new_path in list(rename_candidates):
        new_sha = current_state[new_path].get("sha")
        # match بر اساس sha دقیق → rename
        for old_path in removed_candidates:
            if old_path in matched_removed:
                continue
            old_sha = prev_state[old_path].get("sha")
            if new_sha == old_sha:
                # rename (content یکسان، path تغییر)
                renames.append({"from": old_path, "to": new_path})
                matched_removed.add(old_path)
                rename_candidates.remove(new_path)
                break
        else:
            # match بر اساس token overlap → move
            if file_contents and prev_contents:
                new_content = file_contents.get(new_path, "")
                best_match: Optional[str] = None
                best_score = 0.0
                for old_path in removed_candidates:
                    if old_path in matched_removed:
                        continue
                    old_content = prev_contents.get(old_path, "")
                    if not old_content:
                        continue
                    score = _token_overlap(old_content, new_content)
                    if score > best_score and score >= 0.7:
                        best_score = score
                        best_match = old_path
                if best_match:
                    moves.append({
                        "from": best_match, "to": new_path,
                        "token_overlap": round(best_score, 2),
                    })
                    matched_removed.add(best_match)
                    rename_candidates.remove(new_path)

    # نهایی add/remove از candidates باقی‌مانده
    final_added = [
        {"path": p, "size": current_state[p].get("size", 0)}
        for p in rename_candidates
    ]
    final_removed = [
        {"path": p, "prev_size": prev_state[p].get("size", 0)}
        for p in removed_candidates if p not in matched_removed
    ]

    return {
        "add": final_added,
        "remove": final_removed,
        "modify": modified,
        "rename": renames,
        "move": moves,
        "signature_change": signature_changes,
        "summary": {
            "first_scan": False,
            "add": len(final_added),
            "remove": len(final_removed),
            "modify": len(modified),
            "rename": len(renames),
            "move": len(moves),
            "signature_change": len(signature_changes),
        },
    }
