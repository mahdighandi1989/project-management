#!/usr/bin/env python3
"""Enumerate EVERY surface of the app from source — pages, menu entries, buttons,
inputs, API routes, services and models — so the supervisor knows what it is
supposed to exercise, and so anything ADDED later shows up automatically
without editing a list by hand.

Ported from ALLIN1 (`scripts/supervisor/inventory.py`, read-only reference).

    python3 scripts/supervisor/inventory.py           # → docs/supervisor/INVENTORY.md + inventory.json
    python3 scripts/supervisor/inventory.py --post    # … and send the page list to the app
                                                      #     («نظارت و سرکشی › نقشهٔ سامانه»)

A count that could not be TAKEN is ``null`` and the script exits 2 — never 0,
because «0 routes» would read as «every endpoint was deleted».
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"
BE = ROOT / "backend"
OUT_JSON = ROOT / "docs" / "supervisor" / "inventory.json"
OUT_MD = ROOT / "docs" / "supervisor" / "INVENTORY.md"


class MeasurementFailed(RuntimeError):
    """A count could not be TAKEN — distinct from a count that is really 0."""


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""


def _route_of(page: Path) -> str:
    rel = page.relative_to(FE / "app").parent
    route = "/" + str(rel).replace(os.sep, "/")
    route = "/" if route == "/." else route
    # route groups `(x)` do not appear in the URL; every dynamic segment is `[id]`
    route = "/".join(p for p in route.split("/") if not (p.startswith("(") and p.endswith(")"))) or "/"
    return re.sub(r"\[[^\]]+\]", "[id]", route)


def menu() -> list[dict]:
    src = _read(FE / "components" / "Layout.tsx")
    return [{"href": h, "label": l} for h, l in re.findall(r"\{\s*href:\s*'([^']+)',\s*label:\s*'([^']+)'", src)]


def pages() -> list[dict]:
    labels = {m["href"]: m["label"] for m in menu()}
    out = []
    for f in sorted((FE / "app").rglob("page.tsx")):
        src = _read(f)
        route = _route_of(f)
        out.append({
            "route": route,
            "label": labels.get(route, ""),
            "file": str(f.relative_to(ROOT)),
            "lines": src.count("\n") + 1,
            "buttons": len(re.findall(r"<button\b", src)),
            "onclick": len(re.findall(r"onClick=", src)),
            "inputs": len(re.findall(r"<(input|textarea|select)\b", src)),
            "forms": len(re.findall(r"<form\b", src)),
            "links": len(re.findall(r"<(Link|a)\b", src)),
            "tabs": len(re.findall(r"setActiveTab\(|role=\"tab\"|role='tab'", src)),
        })
    return out


def components() -> list[dict]:
    out = []
    for f in sorted((FE / "components").rglob("*.tsx")):
        src = _read(f)
        out.append({"file": str(f.relative_to(ROOT)), "lines": src.count("\n") + 1,
                    "buttons": len(re.findall(r"<button\b", src)),
                    "inputs": len(re.findall(r"<(input|textarea|select)\b", src))})
    return out


def backend_routes() -> list[dict]:
    """Ask FastAPI itself (its OpenAPI), never a regex over the routers."""
    tmp = tempfile.mkdtemp(prefix="pm-inv-")
    code = (
        "import json,os;"
        "from app.main import app;"
        "spec=app.openapi();"
        "print('@@'+json.dumps([{'path':p,'methods':sorted(m.upper() for m in v.keys())} for p,v in spec['paths'].items()]))"
    )
    env = dict(os.environ, ENVIRONMENT="production", DATABASE_DIR=tmp, INSPECTION_SYNC_DISABLED="1",
               INSPECTION_SPOOL_DIR=os.path.join(tmp, "spool"))
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=BE, capture_output=True, text=True,
                           timeout=300, env=env)
    except Exception as e:  # noqa: BLE001
        raise MeasurementFailed(f"could not run the app import: {e}") from e
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("@@")), "")
    if not line:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
        raise MeasurementFailed("importing app.main produced no route list (exit=%s): %s"
                                % (r.returncode, " / ".join(tail) or "no output"))
    return json.loads(line[2:])


def services() -> list[str]:
    return sorted(p.stem for p in (BE / "app" / "services").glob("*.py") if p.stem != "__init__")


def models() -> list[str]:
    return sorted(p.stem for p in (BE / "app" / "models").glob("*.py") if p.stem != "__init__")


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def build() -> dict:
    pg = pages()
    errors: list[str] = []
    try:
        rt = backend_routes()
    except MeasurementFailed as e:
        rt = None
        errors.append(f"routes: {e}")
    comps = components()
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "commit": _commit(),
        "pages": pg, "menu": menu(), "components": comps, "routes": rt,
        "services": services(), "models": models(), "errors": errors,
        "totals": {
            "pages": len(pg), "menu_items": len(menu()),
            "page_buttons": sum(p["buttons"] for p in pg),
            "component_buttons": sum(c["buttons"] for c in comps),
            "inputs": sum(p["inputs"] for p in pg) + sum(c["inputs"] for c in comps),
            "routes": len(rt) if rt is not None else None,
            "services": len(services()), "models": len(models()),
        },
    }


def to_md(inv: dict) -> str:
    t = inv["totals"]
    L = [
        "# فهرستِ سطحِ سامانه (Inventory) — project-management",
        "",
        "> این فایل را **ناظرِ خودکار** در هر اجرا بازتولید می‌کند — دستی ویرایشش نکن.",
        "> هر صفحه/دکمه/endpointی که بعداً اضافه شود، خودکار این‌جا ظاهر می‌شود؛ مختصاتِ دقیقِ",
        "> عنصرهای هر صفحه در برنامه است: «نظارت و سرکشی › نقشهٔ سامانه».",
        "",
        f"تولید: {inv['generated_at']} · کامیت `{(inv.get('commit') or '')[:10]}`",
        "",
        "| سنجه | تعداد |", "|---|---|",
        f"| صفحه‌ها | {t['pages']} |",
        f"| آیتم‌های منو | {t['menu_items']} |",
        f"| دکمه‌ها در صفحه‌ها / در کامپوننت‌ها | {t['page_buttons']} / {t['component_buttons']} |",
        f"| ورودی‌ها | {t['inputs']} |",
        f"| مسیرهای API | {t['routes'] if t['routes'] is not None else '⚠️ اندازه‌گیری نشد'} |",
        f"| سرویس‌ها | {t['services']} |",
        f"| مدل‌ها | {t['models']} |",
        "", "## منوی کناری", "", "| مسیر | برچسب |", "|---|---|",
    ]
    L += [f"| `{m['href']}` | {m['label']} |" for m in inv["menu"]]
    L += ["", "## صفحه‌ها", "", "| مسیر | فایل | خط | دکمه | ورودی | زبانه |", "|---|---|---|---|---|---|"]
    L += [f"| `{p['route']}` | `{p['file']}` | {p['lines']} | {p['buttons']} | {p['inputs']} | {p['tabs']} |"
          for p in inv["pages"]]
    if inv.get("errors"):
        L += ["", "## ⚠️ سنجه‌هایی که اندازه‌گیری نشدند", "",
              "> این‌ها **صفر نیستند** — اندازه‌گیری‌شان شکست خورد. با «حذفِ قابلیت» اشتباه نگیر.", ""]
        L += [f"- {e}" for e in inv["errors"]]
    L += ["", "## مسیرهای API", "", "| متد | مسیر |", "|---|---|"]
    if inv["routes"] is None:
        L.append("| — | ⚠️ اندازه‌گیری نشد |")
    else:
        L += [f"| {','.join(r['methods'])} | `{r['path']}` |" for r in sorted(inv["routes"], key=lambda x: x["path"])]
    return "\n".join(L) + "\n"


def main() -> int:
    inv = build()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_MD.write_text(to_md(inv), encoding="utf-8")
    print(json.dumps(inv["totals"], ensure_ascii=False))
    if "--post" in sys.argv:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from client import Client, SupervisorError  # noqa: E402
        try:
            res = Client().api("/api/inspection/inventory", body={
                "generated_at": inv["generated_at"], "commit": inv["commit"],
                "pages": [{"route": p["route"], "file": p["file"], "label": p["label"]} for p in inv["pages"]],
                "totals": inv["totals"]})
            print(json.dumps({"posted": res.get("declared")}, ensure_ascii=False))
        except SupervisorError as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return 3
    if inv.get("errors"):
        for e in inv["errors"]:
            print(f"MEASUREMENT FAILED — {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
