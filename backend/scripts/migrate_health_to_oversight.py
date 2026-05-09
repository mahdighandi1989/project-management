"""
Migration script: Health analysis → Oversight
══════════════════════════════════════════════

این script برای هر Project با health data:
  1. اگر watched_project متناظر در Oversight موجود است:
     - roadmap_content + ideal_state → storage/oversight/codex/{watched_id}_roadmap.json
     - readme_content → storage/oversight/codex/{watched_id}_readme.json
     - health_scores + file_health_map → یک OversightReport baseline ذخیره می‌شود
     - issues_found → OversightTask های status='archived' (با
       merged_findings)
  2. اگر watched_project ندارد: یک هشدار log می‌کند و skip

این script idempotent است — اجرای دوباره مشکلی نمی‌سازد.
فقط داده‌های موجود overwrite می‌شوند (با فلگ _migrated_from_health).

استفاده:
    cd backend && python -m scripts.migrate_health_to_oversight
    cd backend && python -m scripts.migrate_health_to_oversight --dry-run
    cd backend && python -m scripts.migrate_health_to_oversight --project-id <UUID>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# اضافه کردن backend/ به path تا import های نسبی کار کنند
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_health")


def _safe_json(value, default):
    if not value:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def migrate_one_project(
    project,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """مهاجرت یک پروژه. خروجی: dict با steps انجام شده."""
    from app.services.oversight_service import (
        get_oversight_service, OversightTask, OversightReport,
    )
    from app.services.oversight_codex_service import (
        write_roadmap, write_readme_doc, read_roadmap, read_readme_doc,
    )

    result: Dict[str, Any] = {
        "project_id": project.id,
        "project_name": project.name,
        "github_path": project.github_path,
        "watched_id": None,
        "matched": False,
        "steps": [],
        "warnings": [],
    }

    service = get_oversight_service()
    repo_full_name = project.github_path or ""
    if "/" not in repo_full_name and project.github_url:
        if "github.com/" in project.github_url:
            repo_full_name = project.github_url.split("github.com/")[-1].rstrip("/").replace(".git", "")

    if not repo_full_name or "/" not in repo_full_name:
        result["warnings"].append("github_path نامعتبر — migration skip شد")
        return result

    # match watched
    watched = next(
        (w for w in service.watched if w.repo_full_name == repo_full_name),
        None,
    )
    if not watched:
        result["warnings"].append(
            f"watched project با repo='{repo_full_name}' در Oversight پیدا نشد — "
            "این پروژه را ابتدا در /oversight watch کنید"
        )
        return result

    result["matched"] = True
    result["watched_id"] = watched.id

    # داده‌های Health
    roadmap = (project.roadmap_content or "").strip()
    ideal_state = (getattr(project, "ideal_state", "") or "").strip()
    readme = (getattr(project, "readme_content", "") or "").strip()
    health_scores = _safe_json(getattr(project, "health_scores", None), {})
    file_health_map = _safe_json(getattr(project, "file_health_map", None), {})
    issues_found = _safe_json(getattr(project, "issues_found", None), [])

    # 1) روadmap → codex
    if roadmap or ideal_state:
        existing = read_roadmap(watched.id)
        roadmap_data = {
            "watched_id": watched.id,
            "repo": watched.repo_full_name,
            "roadmap_markdown": roadmap or existing.get("roadmap_markdown", ""),
            "ideal_state": ideal_state or existing.get("ideal_state", ""),
            "phases": existing.get("phases", []),
            "generated_at": existing.get("generated_at") or _now_iso(),
            "updated_at": _now_iso(),
            "model_used": existing.get("model_used", "migrated_from_health"),
            "_migrated_from_health": True,
            "_migration_at": _now_iso(),
        }
        if not dry_run:
            write_roadmap(watched.id, roadmap_data)
        result["steps"].append(f"roadmap: {len(roadmap)} char + ideal_state ذخیره شد")

    # 2) README → codex
    if readme:
        existing_rd = read_readme_doc(watched.id)
        readme_data = {
            "watched_id": watched.id,
            "repo": watched.repo_full_name,
            "readme_markdown": readme,
            "generated_at": existing_rd.get("generated_at") or _now_iso(),
            "updated_at": _now_iso(),
            "model_used": existing_rd.get("model_used", "migrated_from_health"),
            "_migrated_from_health": True,
            "_migration_at": _now_iso(),
        }
        if not dry_run:
            write_readme_doc(watched.id, readme_data)
        result["steps"].append(f"readme: {len(readme)} char ذخیره شد")

    # 3) health_scores + file_health_map → یک OversightReport baseline
    if health_scores or file_health_map:
        report = OversightReport(
            id=str(uuid.uuid4()),
            task_id=None,
            watched_id=watched.id,
            project_full_name=watched.repo_full_name,
            run_at=_now_iso(),
            status="done",
            done_parts=[],
            remaining_parts=[],
            evidence={
                "health_scores": health_scores,
                "file_health_map_count": len(file_health_map) if isinstance(file_health_map, dict) else 0,
                "_migrated_from_health": True,
            },
            next_actions=["در /oversight یک Deep Scan جدید اجرا کنید برای fresh metrics"],
            confidence_score=0.5,
            raw_response=json.dumps({
                "type": "migration_baseline",
                "health_scores": health_scores,
                "file_health_map_sample": dict(list((file_health_map or {}).items())[:5]),
            }, ensure_ascii=False)[:8000],
            model_id="migrated_from_health",
            user_goal=watched.user_notes or "",
        )
        if not dry_run:
            async with service._lock:
                service.reports.insert(0, report)
                service._save_reports()
        result["steps"].append(
            f"baseline report: health_scores + file_health_map "
            f"({len(file_health_map) if isinstance(file_health_map, dict) else 0} files)"
        )

    # 4) issues_found → OversightTask های status='archived'
    if isinstance(issues_found, list) and issues_found:
        archived_count = 0
        for issue in issues_found:
            if not isinstance(issue, dict):
                continue
            title = (issue.get("message") or issue.get("title") or "")[:200].strip()
            if not title:
                continue
            severity = (issue.get("severity") or "medium").lower()
            priority = "critical" if severity == "critical" else \
                       "high" if severity in ("high", "major") else \
                       "low" if severity in ("low", "minor") else "medium"
            target_files = []
            if issue.get("file"):
                target_files = [issue["file"]]

            t = OversightTask(
                id=str(uuid.uuid4()),
                watched_id=watched.id,
                project_full_name=watched.repo_full_name,
                title=f"[migrated] {title}",
                prompt=f"این تسک از Health analysis قدیمی migrate شده.\n\n"
                       f"## شواهد اصلی\n{json.dumps(issue, ensure_ascii=False, indent=2)[:2000]}",
                raw_idea=title,
                type="bug" if severity in ("critical", "high") else "other",
                priority=priority,
                status="archived",
                source="migrated_from_health",
                target_files=target_files,
                acceptance_criteria=[],
                execution_mode="manual",
            )
            if not dry_run:
                async with service._lock:
                    service.tasks.append(t)
            archived_count += 1
        if archived_count > 0 and not dry_run:
            async with service._lock:
                service._save_tasks()
        result["steps"].append(f"{archived_count} issue → archived OversightTask")

    return result


async def main():
    parser = argparse.ArgumentParser(description="Migrate Health → Oversight")
    parser.add_argument("--dry-run", action="store_true", help="فقط نمایش، بدون ذخیره")
    parser.add_argument("--project-id", default=None, help="فقط یک پروژهٔ خاص")
    args = parser.parse_args()

    from app.core.database import SessionLocal
    from app.models.project import Project

    db = SessionLocal()
    try:
        q = db.query(Project)
        if args.project_id:
            q = q.filter(Project.id == args.project_id)
        projects = q.all()
        logger.info(f"📋 {len(projects)} پروژه برای بررسی")

        results = []
        for proj in projects:
            # فقط اگر داده Health دارد
            has_health = any([
                getattr(proj, "health_scores", None),
                getattr(proj, "file_health_map", None),
                getattr(proj, "issues_found", None),
                getattr(proj, "roadmap_content", None),
                getattr(proj, "readme_content", None),
                getattr(proj, "ideal_state", None),
            ])
            if not has_health:
                continue
            try:
                r = await migrate_one_project(proj, dry_run=args.dry_run)
                results.append(r)
                if r["matched"]:
                    logger.info(f"✅ {proj.name}: {len(r['steps'])} مرحله")
                    for s in r["steps"]:
                        logger.info(f"   • {s}")
                else:
                    logger.warning(f"⚠️ {proj.name}: skip - {'; '.join(r['warnings'])}")
            except Exception as e:
                logger.error(f"❌ {proj.name}: خطا — {e}")

        # خلاصه
        matched = sum(1 for r in results if r["matched"])
        logger.info(f"\n📊 خلاصه: {matched}/{len(results)} پروژه با موفقیت migrate شدند")
        if args.dry_run:
            logger.info("⚠️ DRY RUN — هیچ data ذخیره نشد. برای اجرای واقعی، --dry-run را حذف کنید")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
