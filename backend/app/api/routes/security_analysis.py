# -*- coding: utf-8 -*-
"""
🔒 API های تحلیل امنیتی
Security Analysis API Routes

قابلیت‌ها:
1. Secret Detection - شناسایی رازها
2. License Analysis - تحلیل مجوز
3. Test Coverage Analysis - تحلیل پوشش تست
4. Sandbox Validation - اعتبارسنجی کد
5. Diff View - پیش‌نمایش تغییرات
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

from ...core.database import get_db
from ...models.project import Project, ProjectFile
from ...services.security_analyzer import get_security_analyzer
from ...services.code_quality_analyzer import (
    get_test_coverage_analyzer,
    get_diff_generator,
    get_sandbox_validator
)
from ...core.logging_utils import StructuredLogger

router = APIRouter(prefix="/projects/{project_id}/security", tags=["Security Analysis"])
slog = StructuredLogger(__name__, "SECURITY")

# ==============================================
# 1. Secret Detection
# ==============================================

@router.post("/scan-secrets")
async def scan_for_secrets(
    project_id: str,
    include_low_confidence: bool = Query(False, description="شامل موارد با اطمینان کم"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    اسکن پروژه برای شناسایی رازها (API Keys, Passwords, Tokens)

    - شناسایی ۱۵+ نوع مختلف راز
    - رتبه‌بندی بر اساس severity
    - پیشنهاد رفع مشکل
    """
    slog.api_request("POST", f"/projects/{project_id}/security/scan-secrets")

    try:
        # Get project files
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        # Get files with content
        files = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id
        ).all()

        file_list = [
            {"path": f.file_path, "content": f.content}
            for f in files if f.content
        ]

        if not file_list:
            # Try to get from project's stored files
            if project.github_files:
                try:
                    stored_files = json.loads(project.github_files) if isinstance(project.github_files, str) else project.github_files
                    file_list = stored_files if isinstance(stored_files, list) else []
                except:
                    pass

        slog.info("Starting secret scan", project_id=project_id, file_count=len(file_list))

        # Run security scan
        analyzer = get_security_analyzer()
        result = analyzer.scan_for_secrets(file_list, include_low_confidence)

        # Save results to project
        project.security_scan_result = json.dumps(result, ensure_ascii=False, default=str)
        project.security_scan_at = datetime.utcnow()
        db.commit()

        slog.success(
            "Secret scan complete",
            project_id=project_id,
            secrets_found=len(result["secrets_found"]),
            score=result["score"]
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        slog.error("Secret scan failed", project_id=project_id, exception=e)
        raise HTTPException(status_code=500, detail=f"خطا در اسکن: {str(e)}")


@router.get("/secrets-report")
async def get_secrets_report(
    project_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    دریافت آخرین گزارش اسکن رازها
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    if project.security_scan_result:
        try:
            result = json.loads(project.security_scan_result)
            result["cached"] = True
            result["scanned_at"] = project.security_scan_at.isoformat() if project.security_scan_at else None
            return result
        except:
            pass

    return {
        "cached": False,
        "message": "اسکن امنیتی انجام نشده - ابتدا /scan-secrets را اجرا کنید"
    }


# ==============================================
# 2. License Analysis
# ==============================================

@router.post("/analyze-licenses")
async def analyze_licenses(
    project_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    تحلیل مجوز پروژه و وابستگی‌ها

    - شناسایی فایل LICENSE
    - استخراج وابستگی‌ها از package.json / requirements.txt
    - بررسی سازگاری مجوزها
    """
    slog.api_request("POST", f"/projects/{project_id}/security/analyze-licenses")

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        files = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id
        ).all()

        file_list = [
            {"path": f.file_path, "content": f.content}
            for f in files if f.content
        ]

        if not file_list and project.github_files:
            try:
                file_list = json.loads(project.github_files) if isinstance(project.github_files, str) else project.github_files
            except:
                pass

        slog.info("Starting license analysis", project_id=project_id)

        analyzer = get_security_analyzer()
        result = analyzer.analyze_licenses(file_list)

        # Save to project
        project.license_analysis_result = json.dumps(result, ensure_ascii=False, default=str)
        db.commit()

        slog.success(
            "License analysis complete",
            project_id=project_id,
            license_found=result["project_license"]["found"],
            dependencies=len(result["dependency_licenses"])
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        slog.error("License analysis failed", project_id=project_id, exception=e)
        raise HTTPException(status_code=500, detail=f"خطا در تحلیل: {str(e)}")


# ==============================================
# 3. Full Security Report
# ==============================================

@router.post("/full-report")
async def generate_full_security_report(
    project_id: str,
    include_low_confidence: bool = Query(False),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    تولید گزارش امنیتی جامع

    شامل:
    - Secret Detection
    - License Analysis
    - امتیاز کلی امنیت
    """
    slog.api_request("POST", f"/projects/{project_id}/security/full-report")

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        files = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id
        ).all()

        file_list = [
            {"path": f.file_path, "content": f.content}
            for f in files if f.content
        ]

        if not file_list and project.github_files:
            try:
                file_list = json.loads(project.github_files) if isinstance(project.github_files, str) else project.github_files
            except:
                pass

        slog.info("Generating full security report", project_id=project_id)

        analyzer = get_security_analyzer()
        result = analyzer.generate_security_report(file_list, include_low_confidence)

        # Save comprehensive result
        project.security_scan_result = json.dumps(result, ensure_ascii=False, default=str)
        project.security_scan_at = datetime.utcnow()
        db.commit()

        slog.success(
            "Full security report generated",
            project_id=project_id,
            overall_score=result["overall_score"],
            total_issues=result["total_issues"]
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        slog.error("Security report generation failed", project_id=project_id, exception=e)
        raise HTTPException(status_code=500, detail=f"خطا: {str(e)}")


# ==============================================
# 4. Test Coverage Analysis
# ==============================================

@router.post("/test-coverage")
async def analyze_test_coverage(
    project_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    تحلیل پوشش تست پروژه

    - شناسایی فایل‌های تست
    - تشخیص فریم‌ورک تست
    - تخمین درصد پوشش
    - شناسایی ماژول‌های بدون تست
    """
    slog.api_request("POST", f"/projects/{project_id}/security/test-coverage")

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        files = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id
        ).all()

        file_list = [
            {"path": f.file_path, "content": f.content}
            for f in files if f.content
        ]

        if not file_list and project.github_files:
            try:
                file_list = json.loads(project.github_files) if isinstance(project.github_files, str) else project.github_files
            except:
                pass

        slog.info("Starting test coverage analysis", project_id=project_id)

        analyzer = get_test_coverage_analyzer()
        result = analyzer.analyze_test_coverage(file_list)

        # Save result
        project.test_coverage_result = json.dumps(result, ensure_ascii=False, default=str)
        db.commit()

        slog.success(
            "Test coverage analysis complete",
            project_id=project_id,
            has_tests=result["has_tests"],
            test_files=len(result["test_files"]),
            coverage_estimate=result["coverage_estimate"]["estimated_percentage"]
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        slog.error("Test coverage analysis failed", project_id=project_id, exception=e)
        raise HTTPException(status_code=500, detail=f"خطا: {str(e)}")


# ==============================================
# 5. Sandbox Validation
# ==============================================

@router.post("/validate-code")
async def validate_code_in_sandbox(
    project_id: str,
    files: Dict[str, str] = Body(..., description="فایل‌ها به صورت {path: content}"),
    project_type: str = Query("python", description="نوع پروژه: python | nodejs | typescript"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    اعتبارسنجی کد در محیط ایزوله (Sandbox)

    قبل از commit، کد را برای خطاهای syntax، import و type بررسی می‌کند.

    ⚠️ این endpoint برای پیش‌نمایش تغییرات قبل از اعمال است
    """
    slog.api_request("POST", f"/projects/{project_id}/security/validate-code")

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        slog.info(
            "Starting sandbox validation",
            project_id=project_id,
            file_count=len(files),
            project_type=project_type
        )

        validator = get_sandbox_validator()
        result = await validator.validate_code(files, project_type)

        slog.success(
            "Sandbox validation complete",
            project_id=project_id,
            valid=result["valid"],
            syntax_errors=len(result["syntax_errors"]),
            warnings=len(result["warnings"])
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        slog.error("Sandbox validation failed", project_id=project_id, exception=e)
        raise HTTPException(status_code=500, detail=f"خطا: {str(e)}")


# ==============================================
# 6. Diff View / Dry Run
# ==============================================

@router.post("/generate-diff")
async def generate_diff_view(
    project_id: str,
    file_path: str = Body(..., description="مسیر فایل"),
    original_content: str = Body(..., description="محتوای اصلی"),
    new_content: str = Body(..., description="محتوای جدید"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    تولید Diff برای پیش‌نمایش تغییرات (Dry Run)

    قبل از هرگونه تغییر در فایل، می‌توانید تفاوت‌ها را مشاهده کنید.

    Returns:
        - unified_diff: فرمت استاندارد diff
        - html_diff: فرمت HTML برای نمایش بهتر
        - stats: تعداد خطوط اضافه/حذف شده
        - changed_lines: شماره خطوط تغییر یافته
    """
    slog.api_request("POST", f"/projects/{project_id}/security/generate-diff")

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        generator = get_diff_generator()
        result = generator.generate_diff(original_content, new_content, file_path)

        slog.success(
            "Diff generated",
            project_id=project_id,
            file_path=file_path,
            has_changes=result["has_changes"],
            additions=result["stats"]["additions"],
            deletions=result["stats"]["deletions"]
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        slog.error("Diff generation failed", project_id=project_id, exception=e)
        raise HTTPException(status_code=500, detail=f"خطا: {str(e)}")


@router.post("/dry-run-changes")
async def dry_run_changes(
    project_id: str,
    changes: List[Dict[str, str]] = Body(
        ...,
        description="لیست تغییرات: [{file_path, old_content, new_content}]"
    ),
    validate_code: bool = Query(True, description="اعتبارسنجی کد قبل از نمایش"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Dry Run: پیش‌نمایش تمام تغییرات قبل از اعمال

    شامل:
    - Diff برای هر فایل
    - اعتبارسنجی Syntax (اختیاری)
    - خلاصه کلی تغییرات
    """
    slog.api_request("POST", f"/projects/{project_id}/security/dry-run-changes")

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        slog.info(
            "Starting dry run",
            project_id=project_id,
            file_count=len(changes)
        )

        diff_generator = get_diff_generator()
        sandbox_validator = get_sandbox_validator()

        result = {
            "project_id": project_id,
            "files": [],
            "total_stats": {
                "additions": 0,
                "deletions": 0,
                "files_changed": 0
            },
            "validation_result": None,
            "safe_to_apply": True,
            "generated_at": datetime.utcnow().isoformat()
        }

        new_files_dict = {}

        for change in changes:
            file_path = change.get("file_path", "")
            old_content = change.get("old_content", "")
            new_content = change.get("new_content", "")

            # Generate diff
            diff = diff_generator.generate_diff(old_content, new_content, file_path)

            result["files"].append({
                "file_path": file_path,
                "diff": diff["unified_diff"],
                "stats": diff["stats"],
                "has_changes": diff["has_changes"]
            })

            if diff["has_changes"]:
                result["total_stats"]["files_changed"] += 1
                result["total_stats"]["additions"] += diff["stats"]["additions"]
                result["total_stats"]["deletions"] += diff["stats"]["deletions"]

            # Collect for validation
            if new_content:
                new_files_dict[file_path] = new_content

        # Validate if requested
        if validate_code and new_files_dict:
            # Detect project type
            has_python = any(f.endswith('.py') for f in new_files_dict.keys())
            has_ts = any(f.endswith(('.ts', '.tsx')) for f in new_files_dict.keys())
            project_type = "typescript" if has_ts else ("python" if has_python else "javascript")

            validation = await sandbox_validator.validate_code(new_files_dict, project_type)
            result["validation_result"] = validation

            if not validation["valid"]:
                result["safe_to_apply"] = False

        slog.success(
            "Dry run complete",
            project_id=project_id,
            files_changed=result["total_stats"]["files_changed"],
            safe_to_apply=result["safe_to_apply"]
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        slog.error("Dry run failed", project_id=project_id, exception=e)
        raise HTTPException(status_code=500, detail=f"خطا: {str(e)}")


# ==============================================
# 7. Combined Analysis Dashboard
# ==============================================

@router.get("/dashboard")
async def get_security_dashboard(
    project_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    داشبورد یکپارچه امنیت و کیفیت کد

    نمایش خلاصه:
    - وضعیت امنیتی
    - وضعیت مجوز
    - پوشش تست
    - توصیه‌های اولویت‌دار
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dashboard = {
        "project_id": project_id,
        "project_name": project.name,
        "security": None,
        "license": None,
        "test_coverage": None,
        "overall_health_score": 0,
        "priority_recommendations": [],
        "last_scan": None
    }

    scores = []

    # Security scan result
    if project.security_scan_result:
        try:
            security_data = json.loads(project.security_scan_result)
            dashboard["security"] = {
                "score": security_data.get("overall_score", security_data.get("score", 0)),
                "critical_count": security_data.get("critical_count", 0),
                "status": security_data.get("status", "unknown")
            }
            scores.append(dashboard["security"]["score"])

            # Add critical recommendations
            for rec in security_data.get("recommendations", [])[:3]:
                if "🔴" in rec:
                    dashboard["priority_recommendations"].append(rec)
        except:
            pass

    # License result
    if project.license_analysis_result:
        try:
            license_data = json.loads(project.license_analysis_result)
            dashboard["license"] = {
                "found": license_data.get("project_license", {}).get("found", False),
                "type": license_data.get("project_license", {}).get("type"),
                "score": license_data.get("score", 0)
            }
            scores.append(dashboard["license"]["score"])

            if not dashboard["license"]["found"]:
                dashboard["priority_recommendations"].append("⚠️ پروژه فاقد فایل LICENSE است")
        except:
            pass

    # Test coverage result
    if project.test_coverage_result:
        try:
            test_data = json.loads(project.test_coverage_result)
            dashboard["test_coverage"] = {
                "has_tests": test_data.get("has_tests", False),
                "estimated_percentage": test_data.get("coverage_estimate", {}).get("estimated_percentage", 0),
                "test_count": len(test_data.get("test_files", []))
            }
            scores.append(dashboard["test_coverage"]["estimated_percentage"])

            if not test_data.get("has_tests"):
                dashboard["priority_recommendations"].append("🔴 پروژه فاقد تست است")
        except:
            pass

    # Calculate overall score
    if scores:
        dashboard["overall_health_score"] = int(sum(scores) / len(scores))

    dashboard["last_scan"] = project.security_scan_at.isoformat() if project.security_scan_at else None

    return dashboard
