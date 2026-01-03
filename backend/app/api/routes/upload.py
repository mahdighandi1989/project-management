"""
📤 Upload API Routes - مسیرهای آپلود فایل
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import io

from ...services.storage_service import get_storage_service, FileMetadata
from ...core.config import settings

router = APIRouter(prefix="/upload", tags=["Upload & Storage"])


# ===========================================
# Response Models
# ===========================================

class FileInfo(BaseModel):
    id: str
    original_name: str
    stored_name: str
    relative_path: str
    mime_type: str
    size: int
    category: str
    subcategory: Optional[str]
    created_at: str
    tags: List[str]


class UploadResponse(BaseModel):
    success: bool
    file: Optional[FileInfo] = None
    message: str = ""
    error: Optional[str] = None


class MultiUploadResponse(BaseModel):
    success: bool
    files: List[FileInfo] = []
    failed: List[Dict[str, str]] = []
    message: str = ""


# ===========================================
# Endpoints
# ===========================================

@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(default="attachments"),
    subcategory: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None)  # کاما جدا
):
    """آپلود یک فایل"""
    try:
        storage = get_storage_service()

        # بررسی سایز
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
            )

        # پارس تگ‌ها
        tag_list = [t.strip() for t in tags.split(',')] if tags else []

        # ذخیره
        meta = await storage.save_file(
            content=content,
            original_name=file.filename,
            category=category,
            subcategory=subcategory,
            tags=tag_list
        )

        return UploadResponse(
            success=True,
            file=FileInfo(
                id=meta.id,
                original_name=meta.original_name,
                stored_name=meta.stored_name,
                relative_path=meta.relative_path,
                mime_type=meta.mime_type,
                size=meta.size,
                category=meta.category,
                subcategory=meta.subcategory,
                created_at=meta.created_at,
                tags=meta.tags
            ),
            message="File uploaded successfully"
        )

    except ValueError as e:
        return UploadResponse(success=False, error=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files", response_model=MultiUploadResponse)
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    category: str = Form(default="attachments"),
    subcategory: Optional[str] = Form(default=None)
):
    """آپلود چند فایل"""
    storage = get_storage_service()
    uploaded = []
    failed = []

    for file in files:
        try:
            content = await file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE:
                failed.append({"name": file.filename, "error": "File too large"})
                continue

            meta = await storage.save_file(
                content=content,
                original_name=file.filename,
                category=category,
                subcategory=subcategory
            )

            uploaded.append(FileInfo(
                id=meta.id,
                original_name=meta.original_name,
                stored_name=meta.stored_name,
                relative_path=meta.relative_path,
                mime_type=meta.mime_type,
                size=meta.size,
                category=meta.category,
                subcategory=meta.subcategory,
                created_at=meta.created_at,
                tags=meta.tags
            ))

        except Exception as e:
            failed.append({"name": file.filename, "error": str(e)})

    return MultiUploadResponse(
        success=len(uploaded) > 0,
        files=uploaded,
        failed=failed,
        message=f"Uploaded {len(uploaded)} files, {len(failed)} failed"
    )


@router.post("/debate/{debate_id}")
async def upload_for_debate(
    debate_id: str,
    files: List[UploadFile] = File(...)
):
    """آپلود فایل‌ها برای یک مناظره"""
    storage = get_storage_service()

    # ایجاد پوشه مناظره
    storage.create_debate_folder(debate_id)

    uploaded = []
    for file in files:
        try:
            content = await file.read()
            meta = await storage.save_file(
                content=content,
                original_name=file.filename,
                category="debates",
                subcategory=debate_id,
                tags=["debate_input"]
            )
            uploaded.append({
                "id": meta.id,
                "name": meta.original_name,
                "path": meta.relative_path
            })
        except Exception as e:
            uploaded.append({"name": file.filename, "error": str(e)})

    return {"success": True, "debate_id": debate_id, "files": uploaded}


@router.post("/project/{project_id}")
async def upload_for_project(
    project_id: str,
    files: List[UploadFile] = File(...)
):
    """آپلود فایل‌ها برای یک پروژه"""
    storage = get_storage_service()

    # ایجاد پوشه پروژه
    storage.create_project_folder(project_id)

    uploaded = []
    for file in files:
        try:
            content = await file.read()
            meta = await storage.save_file(
                content=content,
                original_name=file.filename,
                category="projects",
                subcategory=project_id,
                tags=["project_source"]
            )
            uploaded.append({
                "id": meta.id,
                "name": meta.original_name,
                "path": meta.relative_path
            })
        except Exception as e:
            uploaded.append({"name": file.filename, "error": str(e)})

    return {"success": True, "project_id": project_id, "files": uploaded}


@router.get("/file/{file_id}")
async def download_file(file_id: str):
    """دانلود فایل"""
    storage = get_storage_service()
    result = await storage.get_file(file_id)

    if not result:
        raise HTTPException(status_code=404, detail="File not found")

    content, meta = result

    return StreamingResponse(
        io.BytesIO(content),
        media_type=meta.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{meta.original_name}"'
        }
    )


@router.get("/file/{file_id}/info", response_model=FileInfo)
async def get_file_info(file_id: str):
    """دریافت اطلاعات فایل"""
    storage = get_storage_service()
    meta = storage.get_metadata(file_id)

    if not meta:
        raise HTTPException(status_code=404, detail="File not found")

    return FileInfo(
        id=meta.id,
        original_name=meta.original_name,
        stored_name=meta.stored_name,
        relative_path=meta.relative_path,
        mime_type=meta.mime_type,
        size=meta.size,
        category=meta.category,
        subcategory=meta.subcategory,
        created_at=meta.created_at,
        tags=meta.tags
    )


@router.get("/files", response_model=List[FileInfo])
async def list_files(
    category: Optional[str] = Query(default=None),
    subcategory: Optional[str] = Query(default=None),
    tags: Optional[str] = Query(default=None)
):
    """لیست فایل‌ها"""
    storage = get_storage_service()

    tag_list = [t.strip() for t in tags.split(',')] if tags else None
    files = storage.list_files(category, subcategory, tag_list)

    return [FileInfo(
        id=m.id,
        original_name=m.original_name,
        stored_name=m.stored_name,
        relative_path=m.relative_path,
        mime_type=m.mime_type,
        size=m.size,
        category=m.category,
        subcategory=m.subcategory,
        created_at=m.created_at,
        tags=m.tags
    ) for m in files]


@router.delete("/file/{file_id}")
async def delete_file(file_id: str):
    """حذف فایل"""
    storage = get_storage_service()
    success = await storage.delete_file(file_id)

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    return {"success": True, "message": "File deleted"}


@router.get("/stats")
async def get_storage_stats():
    """آمار ذخیره‌سازی"""
    storage = get_storage_service()
    stats = storage.get_category_stats()

    total_count = sum(s["count"] for s in stats.values())
    total_size = sum(s["size"] for s in stats.values())

    return {
        "success": True,
        "total_files": total_count,
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "by_category": stats
    }


@router.get("/tree")
async def get_storage_tree(category: Optional[str] = None):
    """ساختار درختی storage"""
    storage = get_storage_service()
    tree = storage.get_folder_tree(category)
    return {"success": True, "tree": tree}


@router.post("/debate/{debate_id}/save-output")
async def save_debate_output(
    debate_id: str,
    filename: str = Form(...),
    content: str = Form(...),
    output_type: str = Form(default="result")
):
    """ذخیره خروجی مناظره"""
    storage = get_storage_service()

    meta = await storage.save_output(
        content=content,
        filename=filename,
        category="debates",
        subcategory=debate_id,
        output_type=output_type
    )

    return {
        "success": True,
        "file_id": meta.id,
        "path": meta.relative_path
    }


@router.post("/project/{project_id}/save-output")
async def save_project_output(
    project_id: str,
    filename: str = Form(...),
    content: str = Form(...),
    output_type: str = Form(default="generated")
):
    """ذخیره خروجی پروژه"""
    storage = get_storage_service()

    meta = await storage.save_output(
        content=content,
        filename=filename,
        category="projects",
        subcategory=project_id,
        output_type=output_type
    )

    return {
        "success": True,
        "file_id": meta.id,
        "path": meta.relative_path
    }
