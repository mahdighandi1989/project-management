"""
📦 Storage Service - سرویس ذخیره‌سازی فایل‌ها
مدیریت آپلود، ذخیره و بازیابی فایل‌ها با ساختار منظم
"""

import os
import uuid
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO
from dataclasses import dataclass, field, asdict
import json
import hashlib
import aiofiles


@dataclass
class FileMetadata:
    """متادیتای فایل"""
    id: str
    original_name: str
    stored_name: str
    path: str
    relative_path: str
    mime_type: str
    size: int
    category: str  # debates, projects, outputs, attachments
    subcategory: Optional[str] = None  # debate_id, project_id, etc.
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None


class StorageService:
    """
    سرویس ذخیره‌سازی فایل‌ها
    ساختار:
    storage/
    ├── debates/
    │   └── {debate_id}/
    │       ├── inputs/
    │       └── outputs/
    ├── projects/
    │   └── {project_id}/
    │       ├── source/
    │       └── generated/
    ├── attachments/
    │   └── {date}/
    └── exports/
        └── {date}/
    """

    # نوع‌های فایل مجاز
    ALLOWED_EXTENSIONS = {
        # متن و کد
        'txt', 'md', 'json', 'yaml', 'yml', 'xml', 'csv', 'html', 'css', 'js', 'ts',
        'py', 'java', 'cpp', 'c', 'h', 'go', 'rs', 'php', 'rb', 'swift', 'kt',
        # اسناد
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
        # تصویر
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico',
        # صوت و ویدیو
        'mp3', 'wav', 'ogg', 'mp4', 'webm', 'avi', 'mov',
        # آرشیو
        'zip', 'tar', 'gz', 'rar', '7z',
        # سایر
        'log', 'sql', 'sh', 'bat', 'env', 'gitignore', 'dockerfile'
    }

    def __init__(self, base_path: str = "./storage"):
        self.base_path = Path(base_path)
        self._ensure_structure()
        self._metadata_file = self.base_path / "metadata.json"
        self._file_index: Dict[str, FileMetadata] = {}
        self._load_metadata()

    def _ensure_structure(self):
        """ایجاد ساختار پوشه‌ها"""
        directories = [
            "debates",
            "projects",
            "attachments",
            "exports",
            "temp"
        ]
        for dir_name in directories:
            (self.base_path / dir_name).mkdir(parents=True, exist_ok=True)

    def _load_metadata(self):
        """بارگذاری متادیتا از فایل"""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for file_id, meta in data.items():
                        self._file_index[file_id] = FileMetadata(**meta)
            except Exception as e:
                print(f"Warning: Could not load metadata: {e}")

    def _save_metadata(self):
        """ذخیره متادیتا در فایل"""
        try:
            data = {fid: asdict(meta) for fid, meta in self._file_index.items()}
            with open(self._metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save metadata: {e}")

    def _get_extension(self, filename: str) -> str:
        """استخراج پسوند فایل"""
        return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    def _is_allowed(self, filename: str) -> bool:
        """بررسی مجاز بودن نوع فایل"""
        ext = self._get_extension(filename)
        return ext in self.ALLOWED_EXTENSIONS or ext == ''

    def _calculate_checksum(self, content: bytes) -> str:
        """محاسبه checksum فایل"""
        return hashlib.sha256(content).hexdigest()

    def _generate_stored_name(self, original_name: str) -> str:
        """ایجاد نام یکتا برای ذخیره"""
        ext = self._get_extension(original_name)
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_part = Path(original_name).stem[:50]  # حداکثر 50 کاراکتر از نام اصلی
        # حذف کاراکترهای غیرمجاز
        name_part = "".join(c for c in name_part if c.isalnum() or c in ('_', '-'))
        return f"{timestamp}_{name_part}_{unique_id}.{ext}" if ext else f"{timestamp}_{name_part}_{unique_id}"

    async def save_file(
        self,
        content: bytes,
        original_name: str,
        category: str,
        subcategory: Optional[str] = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> FileMetadata:
        """ذخیره یک فایل جدید"""

        # بررسی نوع فایل
        if not self._is_allowed(original_name):
            raise ValueError(f"File type not allowed: {original_name}")

        # تعیین مسیر ذخیره
        if category == "debates" and subcategory:
            dir_path = self.base_path / "debates" / subcategory / "inputs"
        elif category == "projects" and subcategory:
            dir_path = self.base_path / "projects" / subcategory / "source"
        elif category == "attachments":
            date_folder = datetime.now().strftime("%Y-%m-%d")
            dir_path = self.base_path / "attachments" / date_folder
        elif category == "exports":
            date_folder = datetime.now().strftime("%Y-%m-%d")
            dir_path = self.base_path / "exports" / date_folder
        else:
            dir_path = self.base_path / category
            if subcategory:
                dir_path = dir_path / subcategory

        dir_path.mkdir(parents=True, exist_ok=True)

        # ایجاد نام فایل
        stored_name = self._generate_stored_name(original_name)
        file_path = dir_path / stored_name

        # ذخیره فایل
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # تشخیص نوع MIME
        mime_type, _ = mimetypes.guess_type(original_name)
        mime_type = mime_type or 'application/octet-stream'

        # ایجاد متادیتا
        file_id = f"file_{uuid.uuid4().hex[:16]}"
        relative_path = str(file_path.relative_to(self.base_path))

        file_meta = FileMetadata(
            id=file_id,
            original_name=original_name,
            stored_name=stored_name,
            path=str(file_path),
            relative_path=relative_path,
            mime_type=mime_type,
            size=len(content),
            category=category,
            subcategory=subcategory,
            tags=tags or [],
            metadata=metadata or {},
            checksum=self._calculate_checksum(content)
        )

        # ذخیره در index
        self._file_index[file_id] = file_meta
        self._save_metadata()

        return file_meta

    async def save_output(
        self,
        content: str,
        filename: str,
        category: str,
        subcategory: Optional[str] = None,
        output_type: str = "output"  # output, result, export
    ) -> FileMetadata:
        """ذخیره خروجی تولید شده (متن، کد، نتیجه)"""

        # تعیین مسیر خروجی
        if category == "debates" and subcategory:
            dir_path = self.base_path / "debates" / subcategory / "outputs"
        elif category == "projects" and subcategory:
            dir_path = self.base_path / "projects" / subcategory / "generated"
        else:
            dir_path = self.base_path / category / "outputs"
            if subcategory:
                dir_path = dir_path / subcategory

        dir_path.mkdir(parents=True, exist_ok=True)

        stored_name = self._generate_stored_name(filename)
        file_path = dir_path / stored_name

        # ذخیره
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)

        content_bytes = content.encode('utf-8')
        mime_type, _ = mimetypes.guess_type(filename)

        file_id = f"file_{uuid.uuid4().hex[:16]}"
        relative_path = str(file_path.relative_to(self.base_path))

        file_meta = FileMetadata(
            id=file_id,
            original_name=filename,
            stored_name=stored_name,
            path=str(file_path),
            relative_path=relative_path,
            mime_type=mime_type or 'text/plain',
            size=len(content_bytes),
            category=category,
            subcategory=subcategory,
            tags=[output_type],
            metadata={"output_type": output_type},
            checksum=self._calculate_checksum(content_bytes)
        )

        self._file_index[file_id] = file_meta
        self._save_metadata()

        return file_meta

    async def get_file(self, file_id: str) -> Optional[tuple[bytes, FileMetadata]]:
        """دریافت فایل با محتوا"""
        meta = self._file_index.get(file_id)
        if not meta:
            return None

        file_path = Path(meta.path)
        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()

        return content, meta

    def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """دریافت فقط متادیتا"""
        return self._file_index.get(file_id)

    def list_files(
        self,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[FileMetadata]:
        """لیست فایل‌ها با فیلتر"""
        results = []

        for meta in self._file_index.values():
            if category and meta.category != category:
                continue
            if subcategory and meta.subcategory != subcategory:
                continue
            if tags and not any(t in meta.tags for t in tags):
                continue
            results.append(meta)

        # مرتب‌سازی بر اساس تاریخ
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    async def delete_file(self, file_id: str) -> bool:
        """حذف فایل"""
        meta = self._file_index.get(file_id)
        if not meta:
            return False

        file_path = Path(meta.path)
        if file_path.exists():
            file_path.unlink()

        del self._file_index[file_id]
        self._save_metadata()
        return True

    def get_category_stats(self) -> Dict[str, Any]:
        """آمار فایل‌ها به تفکیک دسته"""
        stats = {}
        for meta in self._file_index.values():
            cat = meta.category
            if cat not in stats:
                stats[cat] = {"count": 0, "size": 0}
            stats[cat]["count"] += 1
            stats[cat]["size"] += meta.size
        return stats

    def create_debate_folder(self, debate_id: str) -> str:
        """ایجاد پوشه برای یک مناظره"""
        debate_path = self.base_path / "debates" / debate_id
        (debate_path / "inputs").mkdir(parents=True, exist_ok=True)
        (debate_path / "outputs").mkdir(parents=True, exist_ok=True)
        return str(debate_path)

    def create_project_folder(self, project_id: str) -> str:
        """ایجاد پوشه برای یک پروژه"""
        project_path = self.base_path / "projects" / project_id
        (project_path / "source").mkdir(parents=True, exist_ok=True)
        (project_path / "generated").mkdir(parents=True, exist_ok=True)
        return str(project_path)

    def get_folder_tree(self, category: str = None) -> Dict:
        """دریافت ساختار درختی"""
        def build_tree(path: Path, max_depth: int = 3, depth: int = 0) -> Dict:
            if depth > max_depth:
                return {"name": "...", "type": "truncated"}

            result = {
                "name": path.name,
                "type": "directory",
                "children": []
            }

            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith('.'):
                        continue
                    if item.is_dir():
                        result["children"].append(build_tree(item, max_depth, depth + 1))
                    else:
                        result["children"].append({
                            "name": item.name,
                            "type": "file",
                            "size": item.stat().st_size
                        })
            except PermissionError:
                pass

            return result

        target = self.base_path / category if category else self.base_path
        if not target.exists():
            return {"error": "Path not found"}
        return build_tree(target)


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
