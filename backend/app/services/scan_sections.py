"""
🆕 Scan section detection + filtering + dependency expansion.

این ماژول مشترک بین quick scan و deep scan است.

سه قابلیت:
1. `detect_sections(all_files)` — از روی ساختار repo بخش‌های منطقی
   (frontend, backend, tests, docs, configs, …) را تشخیص می‌دهد.
2. `filter_files_by_selection(all_files, selected_section_keys, custom_paths)`
   — وقتی کاربر بخش‌هایی را انتخاب کرد، فقط فایل‌های مرتبط را برمی‌گرداند.
3. `expand_with_dependencies(selected_files, all_files, file_contents)`
   — برای هر فایل انتخاب‌شده، فایل‌هایی که به آن متکی‌اند یا که آن
   به آن‌ها متکی است (یک سطح، نه recursive) را هم به مجموعه اضافه می‌کند.
   این مطابق درخواست صریح کاربر در voice است که گفت «هم خود اون صفحه
   و هم چیزایی که به این صفحه وابسته از جاهای دیگه یا چیزایی که این
   به جاهای دیگه وابسته است».
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple


# ─── تعریف الگوهای بخش‌های متداول ─────────────────────────────────
# هر بخش = (key, label_fa, label_en, list of path-prefixes/globs).
# اولویت با اولین prefix که match کند است.
_SECTION_PATTERNS: List[Tuple[str, str, str, List[str]]] = [
    ("frontend", "فرانت‌اند (UI)", "Frontend (UI)", [
        "frontend/", "client/", "web/", "ui/",
        "src/app/", "src/pages/", "src/components/",
        "app/", "pages/", "components/",
    ]),
    ("backend", "بک‌اند (API/سرور)", "Backend (API/Server)", [
        "backend/", "server/", "api/",
        "backend/app/", "src/server/",
    ]),
    ("tests", "تست‌ها", "Tests", [
        "tests/", "test/", "__tests__/",
        "spec/", "specs/", "e2e/",
        "backend/tests/", "frontend/tests/",
    ]),
    ("docs", "مستندات", "Docs", [
        "docs/", "doc/", "documentation/",
    ]),
    ("config", "پیکربندی و infra", "Config & Infra", [
        ".github/", "config/", "infra/",
        "docker/", "scripts/", "ci/",
        "deployment/", "k8s/", ".devcontainer/",
    ]),
    ("database", "دیتابیس / migrations", "Database / Migrations", [
        "migrations/", "alembic/", "db/",
        "backend/migrations/", "prisma/",
    ]),
    ("shared", "shared / common", "Shared / Common", [
        "shared/", "common/", "lib/", "utils/",
    ]),
]


def _normalize_path(p: str) -> str:
    # ⚠️ زمانی `.lstrip("./")` بود — ولی `lstrip` با مجموعه‌کاراکتر کار
    # می‌کند نه prefix، پس `.github/...` به `github/...` تبدیل می‌شد
    # (نقطهٔ ابتدا حذف می‌شد). این برای dotfile های ریشه (`.env`,
    # `.gitignore`, `.github/`) فاجعه است.
    s = p.replace("\\", "/").strip().rstrip("/")
    if s.startswith("./"):
        s = s[2:]
    return s


def detect_sections(all_files: List[str]) -> List[Dict[str, object]]:
    """تشخیص خودکار بخش‌های منطقی پروژه از روی tree.

    خروجی: لیستی از section ها، هر کدام شامل:
        - key (str)            — شناسه ماشین‌خوان مثل 'frontend'
        - label (str)          — برچسب فارسی برای UI
        - label_en (str)       — برچسب انگلیسی
        - paths (List[str])    — prefixهای واقعی این بخش در repo
        - file_count (int)     — تعداد فایل‌های متعلق به این بخش
        - example_paths (List) — تا ۳ نمونه مسیر برای راهنمایی کاربر

    قانون‌ها:
    - فقط بخش‌هایی برمی‌گردند که حداقل ۱ فایل دارند.
    - هر فایل به اولین section که match می‌شود می‌رود (priority با ترتیب).
    - فایل‌های unmatched در یک section "other" گروه می‌شوند (اگر باشند).
    """
    if not all_files:
        return []

    normalized = [_normalize_path(p) for p in all_files if p]
    sections: List[Dict[str, object]] = []
    matched_files: Set[str] = set()

    for key, label, label_en, patterns in _SECTION_PATTERNS:
        # فقط prefixهایی که در repo واقعاً وجود دارند را نگه‌دار
        active_prefixes: List[str] = []
        section_files: List[str] = []
        for prefix in patterns:
            prefix_norm = _normalize_path(prefix) + "/"
            hit = [f for f in normalized if f.startswith(prefix_norm) and f not in matched_files]
            if hit:
                active_prefixes.append(prefix_norm)
                section_files.extend(hit)
        if section_files:
            unique_files = list(dict.fromkeys(section_files))  # de-dup keep order
            matched_files.update(unique_files)
            sections.append({
                "key": key,
                "label": label,
                "label_en": label_en,
                "paths": active_prefixes,
                "file_count": len(unique_files),
                "example_paths": unique_files[:3],
            })

    # هر فایل match-نشده → other
    other_files = [f for f in normalized if f not in matched_files]
    if other_files:
        sections.append({
            "key": "other",
            "label": "سایر",
            "label_en": "Other",
            "paths": [],  # other تطابق نام ندارد — کاربر باید فایل خاص را custom_paths کند
            "file_count": len(other_files),
            "example_paths": other_files[:3],
        })

    return sections


def filter_files_by_selection(
    all_files: List[str],
    selected_section_keys: Optional[List[str]],
    custom_paths: Optional[List[str]],
    detected_sections: Optional[List[Dict[str, object]]] = None,
) -> List[str]:
    """فایل‌های all_files را بر اساس selection کاربر فیلتر می‌کند.

    اگر هم selected_section_keys و هم custom_paths خالی باشند →
    کل all_files برمی‌گردد (یعنی اسکن کلی، رفتار قدیم).

    در غیر این صورت:
    - برای هر section انتخاب‌شده، فایل‌هایی که با prefixهایش شروع می‌شوند
    - بعلاوه فایل‌هایی که با هر custom_path شروع می‌شوند
    """
    if not selected_section_keys and not custom_paths:
        return list(all_files)

    if detected_sections is None:
        detected_sections = detect_sections(all_files)
    section_map = {s["key"]: s.get("paths") or [] for s in detected_sections}

    keep: Set[str] = set()
    normalized_all = {_normalize_path(p): p for p in all_files}

    # 1) بر اساس section keys
    for key in selected_section_keys or []:
        prefixes = section_map.get(key) or []
        for prefix in prefixes:
            prefix = _normalize_path(prefix) + "/"
            for norm, original in normalized_all.items():
                if norm.startswith(prefix):
                    keep.add(original)
        # special: "other" — هر فایلی که در هیچ section دیگری نیست
        if key == "other":
            matched_others: Set[str] = set()
            for s in detected_sections:
                if s["key"] == "other":
                    continue
                for prefix in s.get("paths") or []:
                    prefix = _normalize_path(prefix) + "/"
                    for norm, original in normalized_all.items():
                        if norm.startswith(prefix):
                            matched_others.add(original)
            for original in all_files:
                if original not in matched_others:
                    keep.add(original)

    # 2) بر اساس custom paths
    for cp in custom_paths or []:
        cp = _normalize_path(cp)
        if not cp:
            continue
        for norm, original in normalized_all.items():
            if norm == cp or norm.startswith(cp + "/"):
                keep.add(original)

    # ترتیب اصلی all_files را حفظ کن
    return [f for f in all_files if f in keep]


# ─── Dependency expansion ─────────────────────────────────────────
# پارس ساده import statements برای Python + TS/JS/TSX/JSX.
# هدف: یک سطح وابستگی (نه recursive)، برای پاسخ به درخواست user voice
# که گفت «هم خود اون صفحه و هم چیزایی که به این صفحه وابسته از جاهای
# دیگه یا چیزایی که این به جاهای دیگه وابسته است».

_PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.MULTILINE)
_JS_IMPORT_RE = re.compile(
    # پشتیبانی از:
    #   import X from 'path'
    #   import 'path'
    #   require('path')
    #   export { x } from 'path'       ← (audit fix #5) barrel re-exports
    #   export * from 'path'
    r"""(?:^|[\s;])(?:"""
    r"""import\s+(?:[\w*\s,{}]+\s+from\s+)?"""
    r"""|export\s+(?:\*|\{[^}]*\})\s+from\s+"""
    r"""|require\s*\("""
    r""")['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def _py_module_to_path_candidates(module: str, all_files: Set[str]) -> List[str]:
    """ماژول پایتون (مثل 'app.services.foo') را به مسیر فایل تبدیل کن."""
    if not module:
        return []
    base = module.replace(".", "/")
    candidates = [
        f"{base}.py",
        f"{base}/__init__.py",
        f"backend/{base}.py",
        f"backend/{base}/__init__.py",
    ]
    return [c for c in candidates if c in all_files]


def _js_resolve(importer: str, spec: str, all_files: Set[str]) -> List[str]:
    """مسیر relative یا alias-شده JS/TS را به فایل واقعی تبدیل کن."""
    if not spec:
        return []
    # bare imports (npm packages) — رد کن
    if not spec.startswith("."):
        # alias ها مثل '@/components/Foo' — اگر شروع با @/ باشد، حدس بزن از src
        if spec.startswith("@/"):
            rel = spec[2:]
            base_options = ["frontend/src/", "src/", "app/", "frontend/"]
            extensions = [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"]
            candidates: List[str] = []
            for base in base_options:
                for ext in extensions:
                    candidates.append(f"{base}{rel}{ext}")
            return [c for c in candidates if c in all_files]
        return []

    # relative
    importer_dir = "/".join(importer.split("/")[:-1])
    parts = spec.split("/")
    cur = importer_dir.split("/") if importer_dir else []
    for p in parts:
        if p == "." or p == "":
            continue
        if p == "..":
            if cur:
                cur.pop()
        else:
            cur.append(p)
    resolved = "/".join(cur)
    extensions = [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js", "/index.jsx", ""]
    candidates = [f"{resolved}{ext}" for ext in extensions]
    return [c for c in candidates if c in all_files]


def _find_imports_in_file(path: str, content: str, all_files_set: Set[str]) -> Set[str]:
    """فایل‌هایی که این فایل به آن‌ها متکی است."""
    found: Set[str] = set()
    low = path.lower()
    if low.endswith(".py"):
        for m in _PY_IMPORT_RE.finditer(content):
            mod = m.group(1) or m.group(2) or ""
            for resolved in _py_module_to_path_candidates(mod, all_files_set):
                found.add(resolved)
    elif low.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
        for m in _JS_IMPORT_RE.finditer(content):
            spec = m.group(1) or ""
            for resolved in _js_resolve(path, spec, all_files_set):
                found.add(resolved)
    return found


def expand_with_dependencies(
    selected_files: List[str],
    all_files: List[str],
    file_contents: Dict[str, str],
) -> Dict[str, object]:
    """گسترش انتخاب با وابستگی‌های یک‌سطحی.

    برای هر فایل انتخاب‌شده:
    - فایل‌هایی که آن import می‌کند (downstream/dependencies)
    - فایل‌هایی که آن را import می‌کنند (upstream/dependents)

    این فقط روی فایل‌هایی کار می‌کند که محتوای آن‌ها در `file_contents`
    موجود است (که در deep scan تنها top-N فایل را داریم). برای بقیه،
    upstream/downstream قابل تشخیص نیست و نادیده گرفته می‌شود.

    خروجی:
        {
            "expanded": List[str]      # selected + deps (de-dup)
            "deps_added": List[str]    # فقط دپ‌های اضافه‌شده
            "dependents_added": List[str]
        }
    """
    selected_set: Set[str] = set(selected_files)
    all_files_set: Set[str] = set(all_files)

    # 1) downstream: imports of each selected file
    downstream: Set[str] = set()
    for sf in selected_set:
        content = file_contents.get(sf)
        if content:
            for dep in _find_imports_in_file(sf, content, all_files_set):
                if dep not in selected_set:
                    downstream.add(dep)

    # 2) upstream: files whose imports include any selected file
    upstream: Set[str] = set()
    for other_path, other_content in file_contents.items():
        if other_path in selected_set:
            continue
        if not other_content:
            continue
        imports = _find_imports_in_file(other_path, other_content, all_files_set)
        if imports & selected_set:
            upstream.add(other_path)

    expanded_set = selected_set | downstream | upstream
    expanded_ordered = [f for f in all_files if f in expanded_set]

    return {
        "expanded": expanded_ordered,
        "deps_added": sorted(downstream),
        "dependents_added": sorted(upstream),
        "selection_size": len(selected_set),
        "after_size": len(expanded_set),
    }
