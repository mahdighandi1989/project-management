"""Project memory vs. the project's REAL stack (PM-INS-0026 بندِ ۴, 2026-11-17).

quran-web-app-v1 is Vite + React, but its «حافظه و دستورات AI» said «React و Next.js» and three dynamic fields told every
model to use the Next.js App Router, getStaticProps, next.config.js and NEXT_PUBLIC_API_BASE_URL. The cause: auto-setup
labelled any React dependency «React/Next.js». A model following that memory would rewrite the app into another framework.

`review(db, project_id)` reads the stored package.json / requirements files, and for every framework a memory text
names but the project does NOT have:
* dynamic fields ⇒ archived (quarantine, reversible from «بایگانی»), `archived_reason = stale_stack:<framework>`;
* the memory instructions ⇒ one correction paragraph is put on top (the original text stays; nothing is deleted).
It runs after every GitHub sync that brought new files, and on demand (`POST /api/projects/{id}/memory/review-stack`).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

MARK = "⚠️ اصلاحِ خودکارِ حافظه"

# framework → (what in a memory text points at it, the dependency names that prove it is really used)
RULES: Dict[str, tuple] = {
    "Next.js": (re.compile(r"next\.?js|NEXT_PUBLIC_|getStaticProps|getServerSideProps|next\.config|app\s*router|"
                           r"next/image|next/link|\bISR\b", re.I), {"next"}),
    "Nuxt": (re.compile(r"\bnuxt", re.I), {"nuxt", "nuxt3"}),
    "Angular": (re.compile(r"\bangular\b", re.I), {"@angular/core"}),
    "Vue": (re.compile(r"\bvue(\.js)?\b", re.I), {"vue"}),
    "Svelte": (re.compile(r"\bsvelte(kit)?\b", re.I), {"svelte", "@sveltejs/kit"}),
    "Django": (re.compile(r"\bdjango\b", re.I), {"django"}),
    "Flask": (re.compile(r"\bflask\b", re.I), {"flask"}),
}


def detect_stack(db, project_id: str) -> Dict[str, Any]:
    from ..models.project import ProjectFile
    deps: Set[str] = set()
    manifests: List[str] = []
    rows = db.query(ProjectFile.file_path, ProjectFile.content).filter(ProjectFile.project_id == project_id).filter(
        (ProjectFile.file_path.like("%package.json")) | (ProjectFile.file_path.like("%requirements%.txt"))
        | (ProjectFile.file_path.like("%pyproject.toml"))).all()
    for path, content in rows:
        if "node_modules/" in (path or ""):
            continue
        manifests.append(path)
        txt = content or ""
        if path.endswith("package.json"):
            try:
                d = json.loads(txt)
                for k in ("dependencies", "devDependencies", "peerDependencies"):
                    deps |= {x.lower() for x in (d.get(k) or {})}
            except Exception:  # noqa: BLE001
                continue
        else:
            for line in txt.splitlines():
                name = re.split(r"[<>=~!\[;\s]", line.strip(), 1)[0].lower()
                if name and not name.startswith("#"):
                    deps.add(name)
            deps |= {m.lower() for m in re.findall(r'"([A-Za-z0-9_.-]+)\s*[<>=~]', txt)}
    labels = []
    if "next" in deps:
        labels.append("Next.js")
    elif "react" in deps:
        labels.append("React")
    if "vite" in deps:
        labels.append("Vite")
    return {"deps": deps, "manifests": manifests, "labels": labels}


def _absent(text: str, deps: Set[str]) -> List[str]:
    return [fw for fw, (rx, need) in RULES.items() if rx.search(text or "") and not (need & deps)]


def review(db, project_id: str, *, apply: bool = True) -> Dict[str, Any]:
    from ..models.project import Project
    p = db.query(Project).filter(Project.id == project_id).first()
    if p is None:
        return {"ok": False, "reason": "پروژه پیدا نشد"}
    st = detect_stack(db, project_id)
    if not st["manifests"]:  # nothing to compare with — never guess
        return {"ok": True, "skipped": "package.json/requirements در فایل‌های ذخیره‌شده نیست", "archived": [],
                "instructions_corrected": False}
    deps = st["deps"]
    try:
        fields = json.loads(p.dynamic_fields) if p.dynamic_fields else []
    except Exception:  # noqa: BLE001
        fields = []
    archived = []
    now = datetime.utcnow().isoformat()
    for f in fields if isinstance(fields, list) else []:
        if not isinstance(f, dict) or f.get("archived"):
            continue
        bad = _absent(" ".join(str(f.get(k) or "") for k in ("name", "value", "reason", "description")), deps)
        if bad:
            archived.append({"id": f.get("id"), "name": f.get("name"), "frameworks": bad})
            if apply:
                f["archived"] = True
                f["archived_at"] = now
                f["archived_reason"] = "stale_stack:" + ",".join(bad)
    corrected = False
    raw_mi = p.memory_instructions or ""
    try:
        mi = json.loads(raw_mi) if raw_mi.strip().startswith("{") else {"content": raw_mi}
    except Exception:  # noqa: BLE001
        mi = {"content": raw_mi}
    if not isinstance(mi, dict):
        mi = {"content": str(mi)}
    instr = str(mi.get("content") or "")
    bad_instr = _absent(instr.split(MARK)[-1] if MARK in instr else instr, deps)
    if bad_instr and MARK not in instr:
        real = " + ".join(st["labels"]) or "بدونِ فریم‌ورکِ شناخته‌شده"
        note = (f"{MARK} ({now[:10]}، از روی {', '.join(st['manifests'][:3])}): این پروژه **{real}** است، نه "
                f"{' / '.join(bad_instr)}. هر اشاره‌ای به {' / '.join(bad_instr)} در متنِ زیر کهنه/غلط است — از آن پیروی نکن.\n\n")
        corrected = True
        if apply:
            mi["content"] = note + instr
            mi["stack_corrected_at"] = now
            p.memory_instructions = json.dumps(mi, ensure_ascii=False)
    if apply and (archived or corrected):
        if archived:
            p.dynamic_fields = json.dumps(fields, ensure_ascii=False)
        db.commit()
        logger.info(f"memory_stack_review {project_id}: archived={len(archived)} corrected={corrected}")
    return {"ok": True, "stack": st["labels"], "manifests": st["manifests"][:5], "archived": archived,
            "instructions_corrected": corrected, "applied": apply}
