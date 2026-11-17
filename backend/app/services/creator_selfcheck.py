"""Creator Engine: obey the user's constraints, then RUN what was built and fix it until it works (PM-INS-0025, 2026-11-17).

The coordinator built «test-calculator-coordinator» with DeepSeek: calculator.js was right, but in the browser nothing
worked — index.html loaded the scripts without type="module" while they used `export`, js/app.js was never loaded,
package.json said "type":"commonjs" with "test":"jest" (jest failed), and despite «بدون بک‌اند» it wrote main.py/FastAPI/
requirements.txt. Every file was written blind (no file saw the others) and nothing was ever run before «ساخته شد».

This module:

* `detect_constraints(text)` — explicit constraints («بدون بک‌اند», «فقط HTML/CSS/JS», «بدون فریم‌ورک», …) → hard rules;
* `structure_prompt_rules()` / `filter_planned_files()` — static web apps get a fixed, runnable shape (index.html +
  ES modules + `node --test` tests + package.json "type":"module"); backend files are dropped when there is no backend;
* `deterministic_fixes(root)` — what a weak model keeps getting wrong, fixed without a model: module scripts get
  type="module", an entry module nobody loads gets a <script type="module">, package.json gets "type":"module" and a
  test script that works without installing anything;
* `run_checks(root, steps)` — static checks + `node --test` + a real Chromium on a local static server: page errors,
  failed requests (404), and click/expect steps (e.g. «2 + 3 =» ⇒ «5»), with a screenshot;
* `fix_loop(...)` — up to N rounds: problems + all files → the model returns corrected files → re-run, until green.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import re
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

AIGen = Callable[[str], Awaitable[str]]

# ─────────────────────────── constraints ───────────────────────────

_NO_BACKEND = re.compile(
    r"بدون\s*[‌ ]?\s*(بک\s*[‌ ]?\s*[اإ]ند|بکند|سرور|back\s*-?\s*end|server|api\s*ِ?\s*سرور|دیتابیس|پایگاه\s*[‌ ]?\s*داده)|"
    r"بی\s*[‌ ]?\s*(بک\s*[‌ ]?\s*اند|سرور)|"
    r"\bno\s+(back\s*-?\s*end|server|database)\b|\bwithout\s+(a\s+)?(back\s*-?\s*end|server)\b|"
    r"\b(front\s*-?\s*end|client\s*-?\s*side)\s*-?\s*only\b|\bstatic\s+(site|web\s*app|page|html)\b|"
    r"فقط\s*[‌ ]?\s*(فرانت|front|html|اچ\s*تی\s*ام\s*ال|سمت\s*[‌ ]?\s*کاربر|مرورگر)|"
    r"(سایت|صفحه|اپ)\s*[‌ ]?\s*(ِ\s*)?(استاتیک|ایستا)",
    re.I,
)
# a plain browser app (not a constraint by itself — only shapes the files when no server tech is mentioned)
_WEB_ONLY = re.compile(r"(html\s*[/،,+و]\s*css\s*[/،,+و]\s*(js|javascript|جاوا\s*اسکریپت))|"
                       r"(جاوا\s*اسکریپت|javascript|js)\s*ِ?\s*(خالص|ساده)|\bvanilla\s*(js|javascript)\b", re.I)
_NO_FRAMEWORK = re.compile(r"بدون\s*[‌ ]?\s*(فریم\s*[‌ ]?\s*ورک|کتابخانه|framework|react|npm\s*package)|\bno\s+framework\b"
                           r"|\bwithout\s+(a\s+)?framework\b|vanilla", re.I)
_BACKEND_TECH = re.compile(
    r"fastapi|flask|django|express|nest|node\.?js\s*server|uvicorn|gunicorn|sqlalchemy|postgres|mysql|mongo|sqlite|redis|"
    r"celery|docker|jwt|pydantic|python|spring|laravel|php|\.net|rails|prisma|supabase|firebase", re.I)
_BACKEND_FILE = re.compile(
    r"(\.py|\.pyc|\.php|\.rb|\.go|\.java|\.cs)$|(^|/)(requirements[^/]*\.txt|pyproject\.toml|Pipfile|Dockerfile|"
    r"docker-compose\.ya?ml|Procfile|setup\.py|alembic\.ini|server\.(js|mjs|ts)|app\.py|main\.py|wsgi\.py|asgi\.py|"
    r"\.env(\..*)?|render\.ya?ml|vercel\.json|netlify\.toml)$|(^|/)(backend|server|api|migrations|alembic)/",
    re.I)


def detect_constraints(*texts: str) -> Dict[str, Any]:
    """Hard rules from the user's own words. Only POSITIVE explicit phrases count (nothing is guessed)."""
    blob = "\n".join(t for t in texts if t)
    found: List[str] = []
    for rx in (_NO_BACKEND, _NO_FRAMEWORK):
        for m in rx.finditer(blob):
            frag = m.group(0).strip()
            if frag and frag not in found:
                found.append(frag)
    no_backend = bool(_NO_BACKEND.search(blob))
    web_only = bool(_WEB_ONLY.search(blob)) and not _BACKEND_TECH.search(blob)
    return {"no_backend": no_backend, "no_framework": bool(_NO_FRAMEWORK.search(blob)),
            "static_web": no_backend or web_only, "phrases": found[:10]}


def is_static_web(constraints: Dict[str, Any], project_type: str, technologies: List[str]) -> bool:
    if constraints.get("static_web"):
        return True
    pt = (project_type or "").lower()
    if pt in ("static", "html", "vanilla", "web-static", "static-web", "website", "frontend-static"):
        return True
    techs = {t.strip().lower() for t in (technologies or []) if t and t.strip()}
    web = {"html", "html5", "css", "css3", "js", "javascript", "es6", "es modules", "vanilla js", "vanilla javascript"}
    return bool(techs) and techs <= web


def clean_technologies(technologies: List[str], constraints: Dict[str, Any]) -> List[str]:
    if not constraints.get("no_backend"):
        return list(technologies or [])
    return [t for t in (technologies or []) if t and not _BACKEND_TECH.search(t)]


def structure_prompt_rules(constraints: Dict[str, Any], static_web: bool) -> str:
    lines: List[str] = []
    if constraints.get("phrases"):
        lines.append("⛔ محدودیت‌های صریحِ کاربر (قانون — نقض نکن): " + "، ".join(f"«{p}»" for p in constraints["phrases"]))
    if constraints.get("no_backend"):
        lines.append("⛔ هیچ فایلِ سمتِ سرور نساز: نه .py، نه requirements.txt، نه Dockerfile، نه server.js، نه دیتابیس.")
    if static_web:
        lines.append(
            "📐 شکلِ اجباری برای اپِ مرورگری (بدون نصبِ هیچ بسته‌ای اجرا شود):\n"
            "  - index.html در ریشه؛ فقط یک اسکریپتِ ورودی: <script type=\"module\" src=\"js/app.js\"></script>\n"
            "  - منطقِ خالص در js/<name>.js با export (بدون دسترسی به DOM)؛ js/app.js آن را import می‌کند و DOM را وصل می‌کند\n"
            "  - css/style.css\n"
            "  - tests/<name>.test.js با import { test } from 'node:test' و import assert from 'node:assert/strict'\n"
            "    (نه jest، نه mocha) که منطقِ js/<name>.js را import و آزمایش می‌کند\n"
            "  - package.json با \"type\": \"module\" و \"scripts\": {\"test\": \"node --test\"} و بدون dependencies\n"
            "  - README.md\n"
            "  همین؛ فایلِ دیگری نساز.")
    if constraints.get("no_framework"):
        lines.append("⛔ بدونِ فریم‌ورک/کتابخانه (نه React، نه jQuery، نه CDN).")
    return "\n".join(lines)


def static_web_default_structure(name: str) -> Dict[str, Any]:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "app").lower()).strip("-") or "app"
    logic = re.sub(r"-", "_", slug.split("-")[0] or "logic")
    return {
        "directories": ["css", "js", "tests"],
        "files": [
            {"path": f"js/{logic}.js", "description": "منطقِ خالص با export (بدون DOM)"},
            {"path": "js/app.js", "description": f"ورودیِ ES module: import از ./{logic}.js و وصل کردنِ DOM"},
            {"path": "index.html", "description": "صفحه؛ <script type=\"module\" src=\"js/app.js\">"},
            {"path": "css/style.css", "description": "ظاهر"},
            {"path": f"tests/{logic}.test.js", "description": "تست با node:test و node:assert/strict"},
            {"path": "package.json", "description": "type: module، test: node --test"},
            {"path": "README.md", "description": "مستندات"},
        ],
        "entry_point": "index.html",
        "run_command": "open index.html  (یا: python3 -m http.server)  ·  تست: npm test",
    }


def filter_planned_files(files: List[Any], constraints: Dict[str, Any], static_web: bool) -> Tuple[List[Any], List[str]]:
    """Drop what the constraints forbid. Returns (kept, dropped_paths)."""
    kept, dropped = [], []
    for f in files or []:
        path = (f.get("path") if isinstance(f, dict) else str(f) or "").strip().lstrip("/")
        if not path or ".." in path.split("/"):
            continue
        if (constraints.get("no_backend") or static_web) and _BACKEND_FILE.search(path):
            dropped.append(path)
            continue
        kept.append(f)
    if static_web:
        paths = {(f.get("path") if isinstance(f, dict) else f) for f in kept}
        if "index.html" not in paths and not any(str(p).endswith(".html") for p in paths):
            kept.insert(0, {"path": "index.html", "description": "صفحه؛ <script type=\"module\" src=\"js/app.js\">"})
        if "package.json" not in paths:
            kept.append({"path": "package.json", "description": "type: module، test: node --test، بدون dependencies"})
    return kept, dropped


def order_for_generation(files: List[Any]) -> List[Any]:
    """Logic modules first, then the entry module, then HTML/CSS, then tests and config — so every file is written
    with the files it depends on already in front of the model."""
    def rank(f: Any) -> Tuple[int, str]:
        p = (f.get("path") if isinstance(f, dict) else str(f)).lower()
        name = p.rsplit("/", 1)[-1]
        if p.endswith((".js", ".mjs", ".ts")) and "test" not in p and name not in ("app.js", "main.js", "index.js"):
            return (0, p)
        if name in ("app.js", "main.js", "index.js"):
            return (1, p)
        if p.endswith(".html"):
            return (2, p)
        if p.endswith(".css"):
            return (3, p)
        if "test" in p:
            return (4, p)
        if name == "package.json":
            return (5, p)
        return (6, p)
    return sorted(files or [], key=rank)


def context_for_file(written: Dict[str, str], planned: List[str], current: str, budget: int = 14000) -> str:
    """The planned file list + the files already written (newest last, trimmed to a budget)."""
    out = ["## فایل‌های این پروژه (همه با هم کار می‌کنند — مسیرها را دقیقاً همین بنویس)"]
    out += [f"- {p}" + ("  ← همین فایل" if p == current else "") for p in planned]
    used = 0
    blocks: List[str] = []
    for p, c in reversed(list(written.items())):
        chunk = f"\n### {p}\n```\n{c[:6000]}\n```"
        if used + len(chunk) > budget:
            blocks.append(f"\n### {p}\n(طولانی — حذف شد؛ فقط exportها: "
                          + ", ".join(re.findall(r"export\s+(?:default\s+)?(?:function|const|class|let)\s+(\w+)", c))
                          + ")")
            continue
        used += len(chunk)
        blocks.append(chunk)
    if blocks:
        out.append("\n## فایل‌هایی که تا الان نوشته شده‌اند (با همین‌ها هماهنگ باش: نامِ exportها، id ها، مسیرها)")
        out += list(reversed(blocks))
    return "\n".join(out)


# ─────────────────────────── static checks + deterministic fixes ───────────────────────────

_ESM = re.compile(r"^\s*(export\s|import\s[\w{*\s,]+\sfrom\s|import\s+['\"])", re.M)
_SCRIPT = re.compile(r"<script\b([^>]*)>\s*</script>", re.I)
_SRC = re.compile(r"\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
_IMPORT_FROM = re.compile(r"(?:import\s[^'\"]*?from\s*|import\s*\(\s*|import\s+)['\"](\.{1,2}/[^'\"]+)['\"]")
_ENTRY_NAMES = ("app.js", "main.js", "index.js", "script.js")
_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".selfcheck"}


def _files(root: Path, *exts: str) -> List[Path]:
    out = []
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts) & _SKIP_DIRS) and p.suffix.lower() in exts:
            out.append(p)
    return sorted(out)


def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def _resolve_src(root: Path, html: Path, src: str) -> Optional[Path]:
    if re.match(r"^(https?:)?//", src) or src.startswith("data:"):
        return None
    src = src.split("?", 1)[0].split("#", 1)[0]
    base = root if src.startswith("/") else html.parent
    return (base / src.lstrip("/")).resolve()


def _module_graph(root: Path, start: List[Path]) -> set:
    seen: set = set()
    stack = list(start)
    while stack:
        p = stack.pop()
        if p in seen or not p.exists():
            continue
        seen.add(p)
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        for spec in _IMPORT_FROM.findall(txt):
            q = (p.parent / spec).resolve()
            if not q.suffix:
                q = q.with_suffix(".js")
            stack.append(q)
    return seen


def static_problems(root: Path) -> List[Dict[str, str]]:
    probs: List[Dict[str, str]] = []
    htmls = _files(root, ".html")
    jss = [p for p in _files(root, ".js", ".mjs") if "test" not in _rel(root, p).lower()]
    loaded: List[Path] = []
    for h in htmls:
        txt = h.read_text(encoding="utf-8", errors="replace")
        for attrs in _SCRIPT.findall(txt):
            m = _SRC.search(attrs)
            if not m:
                continue
            tgt = _resolve_src(root, h, m.group(1))
            if tgt is None:
                continue
            if not tgt.exists():
                probs.append({"file": _rel(root, h), "problem": f"اسکریپتِ «{m.group(1)}» وجود ندارد (404)"})
                continue
            loaded.append(tgt)
            js = tgt.read_text(encoding="utf-8", errors="replace")
            if _ESM.search(js) and not re.search(r"type\s*=\s*[\"']module[\"']", attrs, re.I):
                probs.append({"file": _rel(root, h),
                              "problem": f"«{m.group(1)}» import/export دارد ولی بدونِ type=\"module\" بار می‌شود"})
    reach = _module_graph(root, loaded)
    for j in jss:
        if j.resolve() not in reach and j.name in _ENTRY_NAMES and htmls:
            probs.append({"file": _rel(root, j), "problem": "این فایلِ ورودی را هیچ صفحه‌ای بار نمی‌کند"})
    for j in sorted(reach):
        try:
            txt = j.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        for spec in _IMPORT_FROM.findall(txt):
            q = (j.parent / spec).resolve()
            if not q.exists():
                probs.append({"file": _rel(root, j), "problem": f"import ِ «{spec}» پیدا نمی‌شود"})
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            probs.append({"file": "package.json", "problem": f"JSON نامعتبر: {e}"})
            data = None
        if isinstance(data, dict):
            any_esm = any(_ESM.search(p.read_text(encoding="utf-8", errors="replace"))
                          for p in _files(root, ".js"))
            if any_esm and data.get("type") != "module":
                probs.append({"file": "package.json",
                              "problem": f"کد ES module است ولی \"type\" = {json.dumps(data.get('type'))} (باید \"module\")"})
            test = ((data.get("scripts") or {}).get("test") or "")
            if re.search(r"\b(jest|mocha|vitest|jasmine)\b", test) and not (root / "node_modules").exists():
                probs.append({"file": "package.json",
                              "problem": f"دستورِ تست «{test}» به بسته‌ای نیاز دارد که نصب نیست — از «node --test» استفاده کن"})
    return probs


def deterministic_fixes(root: Path, *, static_web: bool) -> List[str]:
    """Fix the mechanical mistakes without a model. Returns a human-readable list of what changed."""
    done: List[str] = []
    htmls = _files(root, ".html")
    for h in htmls:
        txt = h.read_text(encoding="utf-8", errors="replace")
        new = txt

        def _fix(m: "re.Match[str]") -> str:
            attrs = m.group(1)
            sm = _SRC.search(attrs)
            if not sm or re.search(r"type\s*=", attrs, re.I):
                return m.group(0)
            tgt = _resolve_src(root, h, sm.group(1))
            if tgt is None or not tgt.exists():
                return m.group(0)
            if _ESM.search(tgt.read_text(encoding="utf-8", errors="replace")):
                done.append(f"{_rel(root, h)}: type=\"module\" برای {sm.group(1)}")
                return m.group(0).replace("<script", '<script type="module"', 1)
            return m.group(0)

        new = _SCRIPT.sub(_fix, new)
        if new != txt:
            h.write_text(new, encoding="utf-8")
    # an entry module nobody loads → load it from the main page
    main = root / "index.html" if (root / "index.html").exists() else (htmls[0] if htmls else None)
    if main is not None:
        txt = main.read_text(encoding="utf-8", errors="replace")
        loaded = [t for t in (_resolve_src(root, main, s) for s in _SRC.findall(" ".join(_SCRIPT.findall(txt)))) if t]
        reach = _module_graph(root, [p for p in loaded if p.exists()])
        for name in _ENTRY_NAMES:
            cands = [p for p in _files(root, ".js") if p.name == name and "test" not in _rel(root, p).lower()]
            for c in cands[:1]:
                if c.resolve() in reach:
                    break
                src = os.path.relpath(c, main.parent).replace(os.sep, "/")
                tag = f'<script type="module" src="{src}"></script>'
                if re.search(r"</body\s*>", txt, re.I):
                    txt = re.sub(r"</body\s*>", tag + "\n</body>", txt, count=1, flags=re.I)
                else:
                    txt += "\n" + tag + "\n"
                main.write_text(txt, encoding="utf-8")
                done.append(f"{_rel(root, main)}: بارگذاریِ {src} اضافه شد (هیچ صفحه‌ای بارش نمی‌کرد)")
                reach = _module_graph(root, [c.resolve()] + list(reach))
            else:
                continue
            break
    pkg = root / "package.json"
    any_esm = any(_ESM.search(p.read_text(encoding="utf-8", errors="replace")) for p in _files(root, ".js"))
    if static_web or pkg.exists():
        data: Dict[str, Any] = {}
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                data = {}
        if not isinstance(data, dict):
            data = {}
        before = json.dumps(data, sort_keys=True)
        if not data.get("name"):
            data["name"] = re.sub(r"[^a-z0-9-]+", "-", root.name.lower()).strip("-") or "app"
        if any_esm and data.get("type") != "module":
            data["type"] = "module"
        scripts = dict(data.get("scripts") or {})
        test = scripts.get("test") or ""
        has_tests = bool(_files(root, ".js")) and any("test" in _rel(root, p).lower() for p in _files(root, ".js"))
        if has_tests and (not test or "no test specified" in test
                          or (re.search(r"\b(jest|mocha|vitest|jasmine)\b", test) and not (root / "node_modules").exists())):
            scripts["test"] = "node --test"
        data["scripts"] = scripts
        if static_web:
            for k in ("dependencies", "devDependencies"):
                if data.get(k) and re.search(r"\b(jest|mocha|vitest|babel)", json.dumps(data.get(k))):
                    data.pop(k, None)
        if json.dumps(data, sort_keys=True) != before:
            pkg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            done.append("package.json: " + ", ".join(
                x for x in (("type=module" if data.get("type") == "module" else ""),
                            (f"test={scripts.get('test')}" if scripts.get("test") else "")) if x))
    return done


# ─────────────────────────── running ───────────────────────────

def node_bin() -> Optional[str]:
    return shutil.which("node") or shutil.which("nodejs")


def run_tests(root: Path, timeout: int = 90) -> Dict[str, Any]:
    """`npm test` without npm: the package.json test script, with node_modules/.bin on PATH. Only node-based scripts are
    run (nothing is installed)."""
    pkg = root / "package.json"
    if not pkg.exists():
        return {"ran": False, "reason": "package.json نیست"}
    try:
        script = ((json.loads(pkg.read_text(encoding="utf-8")).get("scripts") or {}).get("test") or "").strip()
    except Exception as e:  # noqa: BLE001
        return {"ran": False, "ok": False, "reason": f"package.json نامعتبر: {e}"}
    if not script or "no test specified" in script:
        return {"ran": False, "reason": "دستورِ تست تعریف نشده"}
    node = node_bin()
    if not node:
        return {"ran": False, "reason": "Node روی این سرور نصب نیست"}
    if not re.match(r"^node(\s|$)", script):
        return {"ran": False, "ok": False, "command": script,
                "reason": f"فقط دستورِ «node …» بدونِ نصب اجرا می‌شود؛ این «{script}» است"}
    cmd = [node] + script.split()[1:]
    env = dict(os.environ, NODE_ENV="test", NO_COLOR="1", FORCE_COLOR="0")
    env["PATH"] = str(root / "node_modules" / ".bin") + os.pathsep + env.get("PATH", "")
    try:
        cp = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"ran": True, "ok": False, "command": "npm test → " + script, "reason": f"بیش از {timeout} ثانیه"}
    out = (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
    nums = {k: int(v) for k, v in re.findall(r"^#\s*(tests|pass|fail|cancelled|skipped|todo)\s+(\d+)", out, re.M)}
    if not nums:  # node 18 spec reporter
        for k in ("tests", "pass", "fail"):
            m = re.search(rf"ℹ\s*{k}\s+(\d+)", out)
            if m:
                nums[k] = int(m.group(1))
    # named cases (a file without tests still shows up as one «test» named after the file)
    cases = len([n for n in re.findall(r"^\s*# Subtest: (.+)$", out, re.M)
                 if not n.strip().endswith((".js", ".mjs", ".cjs"))])
    ok = cp.returncode == 0 and nums.get("tests", 1) > 0
    return {"ran": True, "ok": ok, "exit_code": cp.returncode, "command": "npm test → " + script,
            "tests": nums.get("tests"), "passed": nums.get("pass"), "failed": nums.get("fail"), "cases": cases,
            "output": out[-4000:]}


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a: Any) -> None:  # noqa: D401
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


_Quiet.extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".mjs": "text/javascript",
                         ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml"}


class StaticServer:
    def __init__(self, root: Path):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> "StaticServer":
        self.t.start()
        return self

    def __exit__(self, *a: Any) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


async def _locate(page: Any, target: str) -> Any:
    target = (target or "").strip()
    if not target:
        return None
    looks_css = bool(re.match(r"^[#.\[]|^[a-z]+[#.\[:]|^[a-z]+$", target)) and len(target) > 1
    cands = []
    if looks_css:
        cands.append(page.locator(target))
    cands += [page.get_by_role("button", name=target, exact=True), page.get_by_text(target, exact=True),
              page.locator(f"[data-value='{target}'],[data-key='{target}'],[value='{target}']")]
    if not looks_css:
        try:
            cands.append(page.locator(target))
        except Exception:  # noqa: BLE001
            pass
    for c in cands:
        try:
            if await c.count() > 0:
                return c.first
        except Exception:  # noqa: BLE001
            continue
    return None


_ATTR_SEL = re.compile(r"^(.*)\[([\w:-]+)\]$")


async def _read(page: Any, selector: str) -> Optional[str]:
    """Text/value at `selector`; `el[attr]` reads the attribute. A selector that matches nothing ⇒ None (a scenario bug,
    not the app's); no selector ⇒ the usual display/result places."""
    if selector:
        try:
            loc = page.locator(selector)
            if await loc.count() == 0:
                return None
            m = _ATTR_SEL.match(selector.strip())
            if m and "=" not in m.group(2):
                v = await loc.first.get_attribute(m.group(2))
                return (v or "").strip()
            v = await loc.first.evaluate(
                "e => ('value' in e && !['BUTTON','LI','OPTION'].includes(e.tagName)) ? e.value : e.innerText")
            return str(v or "").strip()
        except Exception:  # noqa: BLE001
            return None
    sels: List[str] = []
    sels += ["output", "#display", "#result", "#screen", "#output", ".display", ".result", ".screen", ".output",
             "input[readonly]", "input[type=text]", "[role=status]", "[aria-live]"]
    for s in sels:
        try:
            loc = page.locator(s)
            if await loc.count() == 0:
                continue
            el = loc.first
            v = await el.evaluate("e => ('value' in e && e.tagName !== 'BUTTON' && e.tagName !== 'LI') ? e.value : e.innerText")
            if v is not None and str(v).strip() != "":
                return str(v).strip()
        except Exception:  # noqa: BLE001
            continue
    return ""


def _norm(t: str) -> str:
    return " ".join((t or "").replace("\u200c", " ").split())


def _matches(got: str, want: str, contains: bool = False) -> bool:
    g, w = _norm(got), _norm(want)
    if g == w or _num_equal(g, w):
        return True
    numeric = bool(re.fullmatch(r"[-+]?[\d.,٫]+", w))
    # text (not a bare number) may sit among other text: «2 × 4 = 8» in «2 × 4 = 8 20:34»
    return bool(w) and (contains or (not numeric and len(w) >= 3)) and w in g


def _num_equal(a: str, b: str) -> bool:
    try:
        return abs(float(a.replace("٫", ".").replace(",", "")) - float(b)) < 1e-9
    except Exception:  # noqa: BLE001
        return False


async def run_browser(root: Path, steps: List[Dict[str, Any]], *, page_path: str = "index.html",
                      shot_path: Optional[Path] = None, timeout_ms: int = 8000) -> Dict[str, Any]:
    try:
        from playwright.async_api import async_playwright
    except Exception as e:  # noqa: BLE001
        return {"ran": False, "reason": f"Playwright در دسترس نیست: {e}"}
    if not (root / page_path).exists():
        htmls = _files(root, ".html")
        if not htmls:
            return {"ran": False, "reason": "هیچ صفحهٔ HTML ای نیست"}
        page_path = _rel(root, htmls[0])
    errors: List[str] = []
    failed: List[str] = []
    results: List[Dict[str, Any]] = []
    with StaticServer(root) as srv:
        url = f"http://127.0.0.1:{srv.port}/{page_path}"
        async with async_playwright() as p:
            kw: Dict[str, Any] = {"headless": True, "args": ["--no-sandbox", "--disable-setuid-sandbox"]}
            if os.environ.get("SELFCHECK_CHROMIUM_PATH"):
                kw["executable_path"] = os.environ["SELFCHECK_CHROMIUM_PATH"]
            br = await p.chromium.launch(**kw)
            try:
                page = await br.new_page(viewport={"width": 900, "height": 700})
                page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
                # «Failed to load resource» is reported (with its URL) by the response handler; favicon.ico is not a bug
                page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                        if m.type == "error" and not m.text.startswith("Failed to load resource") else None)
                page.on("requestfailed", lambda r: failed.append(f"{r.url} ({r.failure})"))
                page.on("response", lambda r: failed.append(f"{r.url} → HTTP {r.status}")
                        if r.status >= 400 and not r.url.endswith("favicon.ico") else None)
                await page.goto(url, wait_until="load", timeout=timeout_ms)
                await page.wait_for_timeout(400)
                for i, st in enumerate(steps or []):
                    r: Dict[str, Any] = {"i": i + 1, "step": st}
                    try:
                        if st.get("click") is not None:
                            loc = await _locate(page, str(st["click"]))
                            if loc is None:
                                r.update(ok=False, scenario_error=True, why=f"دکمه/المانِ «{st['click']}» پیدا نشد")
                            else:
                                await loc.click(timeout=3000)
                                await page.wait_for_timeout(120)
                                r["ok"] = True
                        elif st.get("type") is not None:
                            loc = await _locate(page, str(st.get("into") or "input"))
                            if loc is None:
                                r.update(ok=False, scenario_error=True, why=f"ورودیِ «{st.get('into')}» پیدا نشد")
                            else:
                                await loc.fill(str(st["type"]))
                                r["ok"] = True
                        elif st.get("expect") is not None:
                            want = str(st["expect"]).strip()
                            got = await _read(page, str(st.get("in") or ""))
                            if got is None:
                                r.update(ok=False, scenario_error=True, want=want,
                                         why=f"انتخابگرِ «{st.get('in')}» در صفحه نیست")
                            else:
                                ok = _matches(got, want, bool(st.get("contains")))
                                r.update(ok=ok, got=got[:300], want=want)
                                if not ok:
                                    r["why"] = f"انتظار «{want}» بود ولی صفحه «{got[:200]}» نشان داد"
                        else:
                            r.update(ok=True, skipped=True)
                    except Exception as e:  # noqa: BLE001
                        r.update(ok=False, why=f"{type(e).__name__}: {str(e)[:200]}")
                    results.append(r)
                if shot_path is not None:
                    shot_path.parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(shot_path), full_page=True)
                body = (await page.inner_text("body"))[:400]
            finally:
                await br.close()
    steps_ok = all(r.get("ok") for r in results)
    return {"ran": True, "ok": not errors and not failed and steps_ok, "url_path": page_path,
            "errors": errors[:20], "failed_requests": failed[:20], "steps": results,
            "steps_passed": sum(1 for r in results if r.get("ok")), "steps_total": len(results),
            "body_text": body, "screenshot": str(shot_path) if shot_path else None}


# ─────────────────────────── model-assisted parts ───────────────────────────

def project_snapshot(root: Path, limit: int = 40000) -> str:
    parts, used = [], 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or (set(p.relative_to(root).parts) & _SKIP_DIRS) or p.name == "project.json":
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        chunk = f"=== FILE: {_rel(root, p)} ===\n{txt}\n=== END FILE ===\n"
        if used + len(chunk) > limit:
            parts.append(f"=== FILE: {_rel(root, p)} === (طولانی — حذف شد)\n")
            continue
        used += len(chunk)
        parts.append(chunk)
    return "\n".join(parts)


_FILE_BLOCK = re.compile(r"===\s*FILE:\s*(.+?)\s*===\s*\n(.*?)\n?===\s*END FILE\s*===", re.S)


def parse_file_blocks(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for path, body in _FILE_BLOCK.findall(text or ""):
        path = path.strip().strip("`").lstrip("/")
        if not path or ".." in path.split("/") or path == "project.json":
            continue
        body = re.sub(r"^```[\w-]*\n", "", body.strip("\n"))
        body = re.sub(r"\n```\s*$", "", body)
        out[path] = body.rstrip() + "\n"
    return out


def _parse_json(text: str) -> Any:
    t = text or ""
    for a, b in (("[", "]"), ("{", "}")):
        s, e = t.find(a), t.rfind(b)
        if s >= 0 and e > s:
            try:
                return json.loads(t[s:e + 1])
            except Exception:  # noqa: BLE001
                continue
    return None


async def plan_browser_steps(ai: AIGen, root: Path, description: str) -> List[Dict[str, Any]]:
    """Ask the model for a click/expect scenario that proves the main feature works, from the real HTML + JS."""
    if not _files(root, ".html"):
        return []
    prompt = (
        "این یک اپِ مرورگری است. یک سناریوی آزمونِ کاربری (۵ تا ۴۰ قدم) بنویس که ثابت کند برنامه واقعاً در مرورگر کار "
        "می‌کند — دقیقاً با همین HTML و JS. اول کارِ اصلی (برای ماشین‌حساب: 2 + 3 = و انتظارِ 5)، بعد **هر ویژگیِ "
        "خواسته‌شده که روی صفحه دیدنی است** (مثلاً پیامِ دقیقِ خطای تقسیم بر صفر، پاک‌کردن، حذفِ آخرین رقم)، و انتظارِ "
        "متنی که کاربر خواسته (نه متنی که کد الان نشان می‌دهد). بینِ دو آزمونِ مستقل وضعیت را پاک کن.\n"
        "قدم‌ها:\n"
        '  {"click": "<متنِ دقیقِ دکمه یا CSS selector>"}\n'
        '  {"type": "<متن>", "into": "<CSS selector>"}\n'
        '  {"expect": "<مقدارِ دقیقِ مورد انتظار>", "in": "<CSS selector ِ جایی که نتیجه نشان داده می‌شود>"}\n'
        "فقط یک آرایهٔ JSON برگردان، بدونِ توضیح.\n\n"
        f"هدفِ برنامه: {description[:1500]}\n\n{project_snapshot(root, 20000)}"
    )
    try:
        data = _parse_json(await ai(prompt))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"selfcheck: plan_browser_steps failed: {e}")
        return []
    if isinstance(data, dict):
        data = data.get("steps") or []
    steps = [s for s in (data or []) if isinstance(s, dict) and ({"click", "type", "expect"} & set(s))]
    return steps[:40]


def summarize(report: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for p in report.get("static", []):
        lines.append(f"[{p['file']}] {p['problem']}")
    t = report.get("tests") or {}
    if t.get("ran") and not t.get("ok"):
        lines.append(f"[tests] npm test شکست خورد (exit {t.get('exit_code')}):\n{(t.get('output') or '')[-2500:]}")
    elif t.get("ok") is False and t.get("reason"):
        lines.append(f"[tests] {t['reason']}")
    b = report.get("browser") or {}
    for e in b.get("errors", []):
        lines.append(f"[browser] {e}")
    for f in b.get("failed_requests", []):
        lines.append(f"[browser] درخواستِ ناموفق: {f}")
    for s in b.get("steps", []):
        if not s.get("ok") and not s.get("scenario_error"):
            lines.append(f"[browser] قدمِ {s['i']} {json.dumps(s['step'], ensure_ascii=False)}: {s.get('why')}")
    return lines


async def run_checks(root: Path, steps: List[Dict[str, Any]], shot: Optional[Path] = None) -> Dict[str, Any]:
    static = static_problems(root)
    tests = await asyncio.to_thread(run_tests, root)
    try:
        browser = await run_browser(root, steps, shot_path=shot) if _files(root, ".html") else {"ran": False}
    except Exception as e:  # noqa: BLE001
        browser = {"ran": False, "ok": False, "reason": f"{type(e).__name__}: {str(e)[:300]}"}
    rep = {"static": static, "tests": tests, "browser": browser}
    rep["problems"] = summarize(rep)
    # what the SERVER could not run (no Node, no browser) is not the project's fault — but it is not «green» either
    blocked: List[str] = []
    if not tests.get("ran") and tests.get("ok") is not False and (root / "package.json").exists() \
            and "تعریف نشده" not in (tests.get("reason") or ""):
        blocked.append(f"تست‌ها اجرا نشد: {tests.get('reason')}")
    if _files(root, ".html") and not browser.get("ran"):
        blocked.append(f"مرورگر اجرا نشد: {(browser.get('reason') or '')[:300]}")
    # a scenario step that points at nothing could not CHECK anything — not green, but not the app's bug either
    for x in ((browser.get("steps") or []) if isinstance(browser, dict) else []):
        if x.get("scenario_error"):
            blocked.append(f"سناریو، قدمِ {x['i']}: {x.get('why')}")
    rep["blocked"] = blocked
    rep["green"] = not rep["problems"] and not blocked
    return rep


def _scenario_errors(rep: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [x for x in ((rep.get("browser") or {}).get("steps") or []) if x.get("scenario_error")]


async def repair_scenario(ai: AIGen, root: Path, steps: List[Dict[str, Any]], bad: List[Dict[str, Any]],
                          description: str) -> List[Dict[str, Any]]:
    """A step whose element/selector is not in the page is the SCENARIO's bug — fix the scenario, never the app."""
    prompt = (
        "سناریوی آزمونِ مرورگرِ زیر انتخابگرهایی دارد که در این صفحه وجود ندارند. **سناریو** را درست کن (نه برنامه): "
        "فقط انتخابگرهایی که واقعاً در همین HTML/JS هستند (یا متنِ دقیقِ دکمه)؛ برای خواندنِ attribute بنویس "
        "\"in\": \"html[data-theme]\". اگر ویژگیِ خواسته‌شده‌ای واقعاً هیچ المانی در صفحه ندارد، آن قدم را با "
        "\"missing\": true نگه دار. همان قالب؛ فقط آرایهٔ JSON.\n\n"
        "## قدم‌های خراب\n" + "\n".join(f"- قدمِ {x['i']}: {json.dumps(x['step'], ensure_ascii=False)} — {x.get('why')}"
                                       for x in bad[:30])
        + f"\n\n## سناریوی فعلی\n{json.dumps(steps, ensure_ascii=False)}\n\n## هدفِ برنامه\n{description[:1200]}\n\n"
        + project_snapshot(root, 24000)
    )
    try:
        data = _parse_json(await ai(prompt))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"selfcheck: repair_scenario failed: {e}")
        return steps
    if isinstance(data, dict):
        data = data.get("steps") or []
    new = [x for x in (data or []) if isinstance(x, dict) and ({"click", "type", "expect"} & set(x))][:40]
    return new or steps


def _snapshot(root: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts) & _SKIP_DIRS) and p.name != "project.json":
            try:
                out[_rel(root, p)] = p.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                continue
    return out


def _restore(root: Path, snap: Dict[str, str]) -> List[str]:
    changed: List[str] = []
    now = _snapshot(root)
    for path in now:
        if path not in snap:
            (root / path).unlink(missing_ok=True)
            changed.append(path)
    for path, body in snap.items():
        if now.get(path) != body:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(body, encoding="utf-8")
            changed.append(path)
    return changed


def _score(rep: Dict[str, Any], base_cases: int) -> Tuple:
    t = rep.get("tests") or {}
    b = rep.get("browser") or {}
    cases = int(t.get("cases") or 0)
    return (bool(rep.get("green")), bool(t.get("ok")), cases >= base_cases, int(b.get("steps_passed") or 0),
            int(t.get("passed") or 0), -len(rep.get("problems") or []))


async def fix_loop(root: Path, *, ai: AIGen, description: str, constraints: Dict[str, Any], static_web: bool,
                   max_rounds: int = 3, shot_dir: Optional[Path] = None,
                   on_write: Optional[Callable[[str, str], None]] = None,
                   steps: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Deterministic fixes → plan the browser scenario → run → repair the SCENARIO where it points at nothing →
    (model fixes the app → run)×N → keep the best round (a fix never leaves the project worse than it found it)."""
    rounds: List[Dict[str, Any]] = []
    auto = deterministic_fixes(root, static_web=static_web)
    if not steps:
        steps = await plan_browser_steps(ai, root, description)
    shot = (shot_dir / "selfcheck_0.png") if shot_dir else None
    rep = await run_checks(root, steps, shot)
    scenario_fixes = 0
    for _ in range(2):
        bad = _scenario_errors(rep)
        if not bad:
            break
        new = await repair_scenario(ai, root, steps, bad, description)
        if new == steps:
            break
        steps = new
        scenario_fixes += 1
        rep = await run_checks(root, steps, shot)
    base_cases = int(((rep.get("tests") or {}).get("cases")) or 0)
    bad = _scenario_errors(rep)
    rounds.append({"round": 0, "auto_fixes": auto, "green": rep["green"], "problems": rep["problems"][:30],
                   "blocked": rep["blocked"], "scenario_repairs": scenario_fixes,
                   "scenario_unresolved": [f"قدمِ {x['i']}: {x.get('why')}" for x in bad][:10],
                   "tests": _brief_tests(rep), "browser": _brief_browser(rep)})
    best = (_score(rep, base_cases), 0, _snapshot(root), rep)
    rules = structure_prompt_rules(constraints, static_web)
    for n in range(1, max_rounds + 1):
        if rep["green"] or not rep["problems"]:  # nothing the APP has to fix (only «blocked» / scenario issues)
            break
        prompt = (
            "این پروژه را اجرا کردیم و این ایرادها پیدا شد. فایل‌هایی را که باید عوض شوند **کامل** بازنویسی کن تا همهٔ "
            "ایرادها رفع شوند (تست‌ها سبز، صفحه بی‌خطا، سناریوی مرورگر درست). منطقِ درست را خراب نکن؛ id/class/data-* ِ "
            "موجود را عوض نکن. تست‌ها را حذف یا ضعیف نکن — کد را درست کن؛ تست را فقط وقتی عوض کن که خودش با خواستهٔ "
            "کاربر نمی‌خواند.\n"
            f"{rules}\n\n"
            "## ایرادها\n" + "\n".join(f"- {x}" for x in rep["problems"][:25]) + "\n\n"
            + ("## سناریوی مرورگر (همین باید درست کار کند)\n" + json.dumps(steps, ensure_ascii=False) + "\n\n" if steps else "")
            + f"## هدفِ برنامه\n{description[:1500]}\n\n## همهٔ فایل‌ها\n{project_snapshot(root)}\n\n"
            "## قالبِ خروجی (فقط همین، هر فایلِ تغییر‌کرده یک بلوک):\n=== FILE: مسیر ===\nمحتوای کاملِ فایل\n=== END FILE ===\n"
        )
        try:
            changed = parse_file_blocks(await ai(prompt))
        except Exception as e:  # noqa: BLE001
            rounds.append({"round": n, "error": f"{type(e).__name__}: {str(e)[:200]}"})
            break
        written = []
        for path, body in changed.items():
            if (constraints.get("no_backend") or static_web) and _BACKEND_FILE.search(path):
                continue
            dst = (root / path).resolve()
            if root.resolve() not in dst.parents:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(body, encoding="utf-8")
            written.append(path)
            if on_write:
                on_write(path, body)
        auto = deterministic_fixes(root, static_web=static_web)
        shot = (shot_dir / f"selfcheck_{n}.png") if shot_dir else None
        rep = await run_checks(root, steps, shot)
        # green by deleting tests is not green: the model must fix the code, not shrink the suite
        now_cases = int(((rep.get("tests") or {}).get("cases")) or 0)
        if base_cases and now_cases < base_cases:
            rep["problems"].append(f"[tests] تعدادِ تست‌ها از {base_cases} به {now_cases} کم شد — تست‌ها را حذف/ضعیف نکن؛ "
                                   "کد را درست کن (تست را فقط اگر خودش غلط است اصلاح کن و همان تعداد را نگه دار)")
            rep["green"] = False
        rounds.append({"round": n, "rewritten": written, "auto_fixes": auto, "green": rep["green"], "blocked": rep["blocked"],
                       "problems": rep["problems"][:30], "tests": _brief_tests(rep), "browser": _brief_browser(rep)})
        sc = _score(rep, base_cases)
        if sc > best[0]:
            best = (sc, n, _snapshot(root), rep)
        if not written and not auto:
            break
    restored: Optional[int] = None
    if best[1] != rounds[-1]["round"] and best[0] > _score(rep, base_cases):
        changed = _restore(root, best[2])
        if on_write:
            for path in changed:
                if path in best[2]:
                    on_write(path, best[2][path])
        restored, rep = best[1], best[3]
        if shot_dir and (shot_dir / f"selfcheck_{restored}.png").exists():
            shutil.copyfile(shot_dir / f"selfcheck_{restored}.png", shot_dir / f"selfcheck_{rounds[-1]['round'] + 1}.png")
    return {"green": rep["green"], "rounds": rounds, "steps": steps, "restored_round": restored, "final": {
        "static": rep["static"], "tests": {k: v for k, v in (rep.get("tests") or {}).items() if k != "output"},
        "tests_output": ((rep.get("tests") or {}).get("output") or "")[-3000:],
        "browser": {k: v for k, v in (rep.get("browser") or {}).items() if k != "body_text"},
        "problems": rep["problems"][:40], "blocked": rep["blocked"],
        "scenario_unresolved": [f"قدمِ {x['i']}: {x.get('why')}" for x in _scenario_errors(rep)][:10]}}


def _brief_tests(rep: Dict[str, Any]) -> Dict[str, Any]:
    t = rep.get("tests") or {}
    return {k: t.get(k) for k in ("ran", "ok", "tests", "cases", "passed", "failed", "reason") if k in t}


def _brief_browser(rep: Dict[str, Any]) -> Dict[str, Any]:
    b = rep.get("browser") or {}
    return {"ran": b.get("ran"), "ok": b.get("ok"), "errors": len(b.get("errors") or []),
            "failed_requests": len(b.get("failed_requests") or []),
            "steps": f"{b.get('steps_passed', 0)}/{b.get('steps_total', 0)}", "reason": b.get("reason")}
