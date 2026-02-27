"""
🛡️ ماژول مرکزی پاکسازی محتوای فایل از آلودگی reasoning/markdown

این ماژول باید در هر جایی که محتوای تولیدشده توسط AI به فایل نوشته میشه استفاده بشه.
هدف: جلوگیری از نوشتن متن تحلیلی/reasoning/markdown به جای کد واقعی.

استفاده:
    from app.services.content_sanitizer import sanitize_file_content, detect_reasoning_contamination, strip_reasoning_blocks
"""

import re
import logging

slog = logging.getLogger("content_sanitizer")


# --- الگوهای آلودگی reasoning در کد منبع ---
REASONING_CONTAMINATION_PATTERNS = [
    r'\*\*استدلال:\*\*',       # فارسی: **استدلال:**
    r'\*\*نتیجه:\*\*',         # فارسی: **نتیجه:**
    r'\*\*Reasoning:\*\*',     # English: **Reasoning:**
    r'\*\*Result:\*\*',        # English: **Result:**
    r'^<think>',               # XML thinking block
    r'^</think>',              # XML thinking block close
    r'\*\*تحلیل:\*\*',         # فارسی: **تحلیل:**
    r'\*\*بررسی:\*\*',         # فارسی: **بررسی:**
    r'\*\*راه‌حل:\*\*',        # فارسی: **راه‌حل:**
    r'\*\*خطا:\*\*',           # فارسی: **خطا:**
    r'\*\*Analysis:\*\*',      # English: **Analysis:**
    r'\*\*Solution:\*\*',      # English: **Solution:**
    r'\*\*Error:\*\*',         # English: **Error:**
    r'\*\*Explanation:\*\*',   # English: **Explanation:**
    r'\*\*Summary:\*\*',       # English: **Summary:**
    r'\*\*توضیح:\*\*',         # فارسی: **توضیح:**
    r'\*\*علت:\*\*',           # فارسی: **علت:**
    r'\*\*مشکل:\*\*',          # فارسی: **مشکل:**
    r'\*\*پیشنهاد:\*\*',       # فارسی: **پیشنهاد:**
    r'\*\*اصلاح:\*\*',         # فارسی: **اصلاح:**
    r'\*\*تغییرات:\*\*',       # فارسی: **تغییرات:**
    r'\*\*کد اصلاح‌شده:\*\*',  # فارسی: **کد اصلاح‌شده:**
    r'\*\*Fix:\*\*',           # English: **Fix:**
    r'\*\*Issue:\*\*',         # English: **Issue:**
    r'\*\*Problem:\*\*',       # English: **Problem:**
    r'\*\*Changes:\*\*',       # English: **Changes:**
    r'\*\*Updated code:\*\*',  # English: **Updated code:**
    r'\*\*Modified code:\*\*', # English: **Modified code:**
    r'\*\*Corrected:\*\*',     # English: **Corrected:**
    r'^<analysis>',            # XML analysis block
    r'^<reasoning>',           # XML reasoning block
    r'^<thinking>',            # XML thinking block
    r'^<reflection>',          # XML reflection block
    r'^#{1,4}\s+[\u0600-\u06FF]',  # Markdown heading followed by Persian text at start of line
    r'^```(?:typescript|tsx|jsx|python|json|javascript|css|html|go|rust|java|kotlin|swift|ruby|php|sql|yaml|csharp|cpp|c)\s*$',
    r'^\*\*\d+[\.\)]\s',      # Numbered list with bold: **1. ..., **2) ...
    r'^\*\*[\u0600-\u06FF]',   # Bold Persian text at start of line: **فارسی
]


# --- اکستنشن‌های کد و الگوهای شروع معتبر ---
CODE_EXTENSIONS = {
    "ts", "tsx", "js", "jsx", "py", "css", "html", "htm", "vue", "json",
    "yaml", "yml", "sql", "go", "rs", "java", "kt", "swift", "rb", "php",
    "c", "cpp", "h", "hpp", "cs", "sh", "bash", "zsh", "dockerfile",
    "toml", "ini", "cfg", "xml", "svg", "md", "txt", "env", "graphql",
}

CODE_START_PATTERNS = {
    "ts": ["import ", "export ", "//", "/*", "'use", '"use', "const ", "var ", "let ", "type ", "interface ", "enum ", "{", "declare ", "namespace ", "module "],
    "tsx": ["import ", "export ", "//", "/*", "'use", '"use', "const ", "var ", "let ", "type ", "interface ", "enum ", "{", "declare ", "namespace ", "module "],
    "js": ["import ", "export ", "//", "/*", "'use", '"use', "const ", "var ", "let ", "{", "module.", "function "],
    "jsx": ["import ", "export ", "//", "/*", "'use", '"use', "const ", "var ", "let ", "{", "function "],
    "py": ["import ", "from ", "#", '"""', "'''", "def ", "class ", "@", "if ", "try:", "async ", '"""', "'''"],
    "css": [".", "#", "@", "*", ":", "/", "body", "html", "div", "span", "a", "p", "h1", "h2", "h3", "h4", "h5", "h6",
            "ul", "ol", "li", "nav", "header", "footer", "main", "section", "article", "button", "input", "form",
            "table", "tr", "td", "th", "img", "video", "audio", "canvas", "svg"],
    "html": ["<", "<!"],
    "htm": ["<", "<!"],
    "json": ["{", "[", '"'],
    "yaml": ["---", "#", "version", "name", "services", "apiVersion"],
    "yml": ["---", "#", "version", "name", "services", "apiVersion"],
    "sql": ["SELECT", "CREATE", "INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "--", "/*", "BEGIN", "PRAGMA"],
    "vue": ["<template", "<script", "<style", "<!--"],
    # --- زبان‌های جدید ---
    "go": ["package ", "import ", "//", "/*", "func ", "type ", "var ", "const "],
    "rs": ["use ", "mod ", "pub ", "fn ", "struct ", "enum ", "impl ", "trait ", "//", "/*", "#[", "extern "],
    "java": ["package ", "import ", "public ", "private ", "protected ", "class ", "interface ", "enum ", "//", "/*", "@"],
    "kt": ["package ", "import ", "fun ", "class ", "object ", "interface ", "val ", "var ", "//", "/*", "@", "sealed ", "data "],
    "swift": ["import ", "func ", "class ", "struct ", "enum ", "protocol ", "let ", "var ", "//", "/*", "@", "extension "],
    "rb": ["require ", "module ", "class ", "def ", "#", "include ", "attr_", "gem "],
    "php": ["<?php", "<?", "namespace ", "use ", "class ", "function ", "//", "/*", "#", "declare("],
    "c": ["#include", "#define", "#pragma", "//", "/*", "int ", "void ", "char ", "struct ", "enum ", "typedef ", "static ", "extern "],
    "cpp": ["#include", "#define", "#pragma", "//", "/*", "int ", "void ", "class ", "struct ", "namespace ", "template", "using ", "auto "],
    "h": ["#ifndef", "#define", "#pragma", "#include", "//", "/*", "typedef ", "struct ", "enum ", "extern "],
    "hpp": ["#ifndef", "#define", "#pragma", "#include", "//", "/*", "class ", "struct ", "namespace ", "template"],
    "cs": ["using ", "namespace ", "public ", "private ", "internal ", "class ", "interface ", "struct ", "enum ", "//", "/*", "["],
    "sh": ["#!/", "#", "set ", "export ", "if ", "for ", "while ", "case ", "function "],
    "bash": ["#!/", "#", "set ", "export ", "if ", "for ", "while ", "case ", "function "],
    "dockerfile": ["FROM ", "RUN ", "CMD ", "ENTRYPOINT ", "COPY ", "ADD ", "WORKDIR ", "ENV ", "EXPOSE ", "ARG ", "#"],
    "toml": ["[", "#", "name", "version", "description"],
    "xml": ["<?xml", "<", "<!--"],
    "svg": ["<?xml", "<svg", "<", "<!--"],
    "graphql": ["type ", "query ", "mutation ", "subscription ", "schema ", "input ", "enum ", "interface ", "union ", "scalar ", "#", "{"],
}


def strip_reasoning_blocks(text: str) -> str:
    """
    حذف بلوک‌های استدلال (reasoning/thinking) از پاسخ مدل‌ها.
    مدل‌هایی مثل deepseek-reasoner بلوک‌های **استدلال:** یا <think> می‌فرستن
    که نباید در خروجی کد باشه.
    """
    if not text:
        return text

    # حذف بلوک **استدلال:** تا **نتیجه:** (حالت کامل)
    text = re.sub(r'\*\*استدلال:\*\*.*?\*\*نتیجه:\*\*\s*', '', text, flags=re.DOTALL)

    # حذف **استدلال:** بدون **نتیجه:** (حالت ناقص)
    text = re.sub(r'\*\*استدلال:\*\*.*$', '', text, flags=re.DOTALL)

    # حذف بلوک‌های <think>...</think>
    text = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)

    # حذف <think> بدون </think> (ناقص)
    text = re.sub(r'<think>.*$', '', text, flags=re.DOTALL)

    # حذف بلوک‌های **Reasoning:**...**Result:** (حالت کامل)
    text = re.sub(r'\*\*Reasoning:\*\*.*?\*\*Result:\*\*\s*', '', text, flags=re.DOTALL | re.IGNORECASE)

    # حذف **Reasoning:** بدون **Result:** (حالت ناقص)
    text = re.sub(r'\*\*Reasoning:\*\*.*$', '', text, flags=re.DOTALL | re.IGNORECASE)

    # حذف بلوک‌های فارسی و انگلیسی مختلف
    for label in ['تحلیل', 'بررسی', 'راه‌حل', 'خطا', 'توضیح', 'علت', 'مشکل', 'پیشنهاد', 'اصلاح', 'تغییرات',
                  'Analysis', 'Solution', 'Error', 'Explanation', 'Summary', 'Fix', 'Issue', 'Problem', 'Changes']:
        text = re.sub(
            r'\*\*' + re.escape(label) + r':\*\*.*?\*\*(?:نتیجه|Result|Output|Code|خروجی):\*\*\s*',
            '', text, flags=re.DOTALL | re.IGNORECASE
        )
        # حالت ناقص (بدون بلوک پایانی)
        text = re.sub(
            r'\*\*' + re.escape(label) + r':\*\*.*$',
            '', text, flags=re.DOTALL | re.IGNORECASE
        )

    # حذف بلوک‌های XML
    for tag in ['analysis', 'reasoning', 'thinking', 'reflection', 'summary']:
        text = re.sub(rf'<{tag}>.*?</{tag}>\s*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(rf'<{tag}>.*$', '', text, flags=re.DOTALL | re.IGNORECASE)

    return text.strip()


def sanitize_file_content(content: str, file_path: str) -> str:
    """
    🛡️ پاکسازی محتوای فایل از آلودگی reasoning/markdown قبل از نوشتن یا commit.
    این تابع باید روی هر محتوای فایل قبل از ذخیره‌سازی اعمال بشه.

    مراحل:
    ۱) حذف بلوک‌های reasoning/thinking (فقط جفتی/بسته‌شده)
    ۲) حذف متن غیرکد (فارسی/عربی/markdown) از ابتدای فایل‌های کد
    ۳) حذف markdown code fences دور کل محتوا
    ۴) حذف متن غیرکد از انتهای فایل (بعد از ```)
    """
    if not content or not content.strip():
        return content

    # ---- مرحله ۱: حذف reasoning blocks (فقط بلوک‌های جفتی — نه orphan) ----
    content = re.sub(r'\*\*استدلال:\*\*.*?\*\*نتیجه:\*\*\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'\*\*Reasoning:\*\*.*?\*\*Result:\*\*\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)
    for tag in ['analysis', 'reasoning', 'thinking', 'reflection', 'summary']:
        content = re.sub(rf'<{tag}>.*?</{tag}>\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    # حذف بلوک‌های فارسی/انگلیسی بیشتر
    for label in ['تحلیل', 'بررسی', 'راه‌حل', 'خطا', 'توضیح', 'علت', 'مشکل', 'پیشنهاد', 'اصلاح', 'تغییرات',
                  'Analysis', 'Solution', 'Error', 'Explanation', 'Summary', 'Fix', 'Issue', 'Problem', 'Changes']:
        content = re.sub(
            r'\*\*' + re.escape(label) + r':\*\*.*?\*\*(?:نتیجه|Result|Output|Code|خروجی):\*\*\s*',
            '', content, flags=re.DOTALL | re.IGNORECASE
        )
    content = content.strip()

    # ---- مرحله ۲: حذف متن غیرکد قبل از کد واقعی ----
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    if ext in CODE_EXTENSIONS:
        lines = content.split('\n')
        valid_starts = CODE_START_PATTERNS.get(ext, [])

        if valid_starts:
            first_valid_idx = 0
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                # خط کد واقعی یا markdown fence
                if any(stripped_line.startswith(s) for s in valid_starts) or stripped_line.startswith("```"):
                    first_valid_idx = i
                    break
                # اگر خط حاوی متن فارسی/عربی + markdown بود → skip
                _has_persian = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', stripped_line))
                _has_markdown = stripped_line.startswith("**") or stripped_line.startswith("##") or stripped_line.startswith("- ") or stripped_line.startswith("* ")
                if _has_persian or _has_markdown:
                    first_valid_idx = i + 1
                    continue
                # خط غیر فارسی، غیر markdown، و غیر کد → ممکنه توضیح انگلیسی باشه
                if i < 5:
                    _code_syntax_chars = ["{", "}", "(", ")", "=", ";", "<", ">", "//", "/*", "=>"]
                    _looks_like_prose = len(stripped_line) > 15 and not any(c in stripped_line for c in _code_syntax_chars)
                    _is_explanation = stripped_line.endswith(":") and not any(
                        stripped_line.startswith(s) for s in [
                            "import", "export", "from", "const", "var", "let", "def", "class",
                            "return", "if", "for", "while", "try", "async", "function",
                            "package", "use ", "pub ", "fn ", "struct", "enum", "impl",
                            "public", "private", "protected", "namespace", "#include",
                        ]
                    )
                    if _looks_like_prose or _is_explanation:
                        first_valid_idx = i + 1
                        continue
                break

            if first_valid_idx > 0:
                lines = lines[first_valid_idx:]
                content = '\n'.join(lines)
                slog.info(f"[sanitize] Stripped {first_valid_idx} non-code lines from start of {file_path}")

    # ---- مرحله ۳: حذف markdown code fence دور محتوا ----
    stripped = content.strip()
    _fence_match = re.match(r'^```[\w]*\s*\n(.*?)```\s*$', stripped, re.DOTALL)
    if _fence_match:
        content = _fence_match.group(1)
    else:
        if stripped.startswith("```"):
            lines = stripped.split('\n')
            lines = lines[1:]  # حذف خط اول (```language)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = '\n'.join(lines)

    # ---- مرحله ۴: حذف متن غیرکد از انتهای فایل ----
    if ext in CODE_EXTENSIONS:
        _trailing_lines = content.split('\n')
        _last_valid = len(_trailing_lines)
        for i in range(len(_trailing_lines) - 1, -1, -1):
            _tl = _trailing_lines[i].strip()
            if not _tl:
                continue
            _has_persian = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', _tl))
            _has_markdown = _tl.startswith("**") or _tl.startswith("##") or _tl.startswith("- ") or _tl.startswith("---")
            if _has_persian or _has_markdown:
                _last_valid = i
                continue
            # خط مثل ```tsx یا ``` در انتها → حذف
            if _tl.startswith("```"):
                _last_valid = i
                continue
            break
        if _last_valid < len(_trailing_lines):
            _removed = len(_trailing_lines) - _last_valid
            content = '\n'.join(_trailing_lines[:_last_valid])
            slog.info(f"[sanitize] Stripped {_removed} non-code lines from end of {file_path}")

    return content.strip()


def detect_reasoning_contamination(content: str, file_path: str) -> str | None:
    """
    🛡️ بررسی آلودگی محتوای فایل با خروجی reasoning مدل‌های AI.
    اگر آلودگی پیدا شد، رشته خطا برمی‌گردونه. اگه تمیز بود None.

    این تابع باید بعد از sanitize_file_content() اجرا بشه — اول تمیزکاری، بعد بررسی.
    """
    if not content:
        return None

    for pattern in REASONING_CONTAMINATION_PATTERNS:
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            return f"محتوای فایل {file_path} با خروجی reasoning مدل AI آلوده شده: الگوی '{pattern}' شناسایی شد"

    # بررسی اضافی: آیا خط اول فایل کد، یک خط معتبر کد هست؟
    first_line = content.split("\n")[0].strip() if content.strip() else ""
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    # ساخت مپ اعتبارسنجی خط اول برای هر زبان
    _first_line_validators = {
        ("ts", "tsx", "js", "jsx"): (
            "import ", "export ", "//", "/*", "'use", '"use', "const ", "var ", "let ",
            "type ", "interface ", "enum ", "{", "declare ", "namespace ", "module ", "function ",
        ),
        ("py",): (
            "import ", "from ", "#", '"""', "'''", "def ", "class ", "@", "if ", "try:",
            "async ", '"""', "'''",
        ),
        ("css",): (
            ".", "#", "@", "*", ":", "/", "body", "html", "div", "span", "a", "p",
            "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "nav", "header",
            "footer", "main", "section", "article", "button", "input", "form",
            "table", "tr", "td", "th", "img", "video", "audio", "canvas", "svg",
        ),
        ("html", "htm"): ("<", "<!",),
        ("json",): ("{", "[", '"',),
        ("vue",): ("<template", "<script", "<style", "<!--",),
        # --- زبان‌های جدید ---
        ("go",): ("package ", "import ", "//", "/*", "func ", "type ", "var ", "const ",),
        ("rs",): ("use ", "mod ", "pub ", "fn ", "struct ", "enum ", "impl ", "trait ", "//", "/*", "#[", "extern ",),
        ("java",): ("package ", "import ", "public ", "private ", "protected ", "class ", "interface ", "enum ", "//", "/*", "@",),
        ("kt",): ("package ", "import ", "fun ", "class ", "object ", "interface ", "val ", "var ", "//", "/*", "@", "sealed ", "data ",),
        ("swift",): ("import ", "func ", "class ", "struct ", "enum ", "protocol ", "let ", "var ", "//", "/*", "@", "extension ",),
        ("rb",): ("require ", "module ", "class ", "def ", "#", "include ", "attr_", "gem ",),
        ("php",): ("<?php", "<?", "namespace ", "use ", "class ", "function ", "//", "/*", "#", "declare(",),
        ("c", "cpp", "h", "hpp"): ("#include", "#define", "#pragma", "//", "/*", "int ", "void ", "char ", "struct ", "enum ", "typedef ", "static ", "extern ", "class ", "namespace ", "template", "using ",),
        ("cs",): ("using ", "namespace ", "public ", "private ", "internal ", "class ", "interface ", "struct ", "enum ", "//", "/*", "[",),
        ("sh", "bash", "zsh"): ("#!/", "#", "set ", "export ", "if ", "for ", "while ", "case ", "function ",),
        ("sql",): ("SELECT", "CREATE", "INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "--", "/*", "BEGIN", "PRAGMA",),
        ("yaml", "yml"): ("---", "#", "version", "name", "services", "apiVersion",),
        ("dockerfile",): ("FROM ", "RUN ", "CMD ", "ENTRYPOINT ", "COPY ", "ADD ", "WORKDIR ", "ENV ", "EXPOSE ", "ARG ", "#",),
        ("xml", "svg"): ("<?xml", "<", "<!--",),
        ("graphql",): ("type ", "query ", "mutation ", "subscription ", "schema ", "input ", "enum ", "interface ", "union ", "scalar ", "#", "{",),
        ("toml",): ("[", "#", "name", "version", "description",),
    }

    if ext and first_line:
        for ext_tuple, valid_starts in _first_line_validators.items():
            if ext in ext_tuple:
                if not any(first_line.startswith(s) for s in valid_starts):
                    return f"خط اول فایل {file_path} معتبر نیست برای {ext}: '{first_line[:80]}'"
                break

    return None


def sanitize_section_content(replace_str: str, file_path: str) -> str:
    """
    پاکسازی محتوای replace در modify_sections.
    سبک‌تر از sanitize_file_content چون فقط بخشی از فایل رو تغییر میده.
    """
    if not replace_str or not replace_str.strip():
        return replace_str

    # حذف reasoning blocks کامل
    replace_str = re.sub(r'\*\*استدلال:\*\*.*?\*\*نتیجه:\*\*\s*', '', replace_str, flags=re.DOTALL)
    replace_str = re.sub(r'\*\*Reasoning:\*\*.*?\*\*Result:\*\*\s*', '', replace_str, flags=re.DOTALL | re.IGNORECASE)
    replace_str = re.sub(r'<think>.*?</think>\s*', '', replace_str, flags=re.DOTALL)
    for tag in ['analysis', 'reasoning', 'thinking', 'reflection', 'summary']:
        replace_str = re.sub(rf'<{tag}>.*?</{tag}>\s*', '', replace_str, flags=re.DOTALL | re.IGNORECASE)

    # حذف بلوک‌های فارسی/انگلیسی
    for label in ['تحلیل', 'بررسی', 'راه‌حل', 'خطا', 'توضیح', 'علت', 'مشکل', 'پیشنهاد', 'اصلاح', 'تغییرات',
                  'Analysis', 'Solution', 'Error', 'Explanation', 'Summary', 'Fix', 'Issue', 'Problem', 'Changes']:
        replace_str = re.sub(
            r'\*\*' + re.escape(label) + r':\*\*.*?\*\*(?:نتیجه|Result|Output|Code|خروجی):\*\*\s*',
            '', replace_str, flags=re.DOTALL | re.IGNORECASE
        )

    # حذف markdown code fence فقط اگه کل replace در fence باشه
    stripped = replace_str.strip()
    _fence_match = re.match(r'^```[\w]*\s*\n(.*?)```\s*$', stripped, re.DOTALL)
    if _fence_match:
        replace_str = _fence_match.group(1)

    return replace_str
