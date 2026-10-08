#!/usr/bin/env python3
"""Docs gate — makes the documentation rules fail the build (run by scripts/ship.sh).

Modelled on Detective-1's scripts/docs_gate.py. Offline, standard library only.

    python3 scripts/docs_gate.py

Exits 1 (listing every problem) when:
  1. an agent entry file is missing or does not point back to AGENTS.md;
  2. AGENTS.md does not name every command scripts/ship.sh actually runs;
  3. a path in the docs map (the '## ساختار' table in CLAUDE.md) does not resolve;
  4. the NEWEST entry of docs/WORKLOG.md (bottom of the file) has no signature;
  5. a file in experiences/ lacks the frontmatter required by experiences/README.md.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
problems: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


def read(rel: str) -> str | None:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


# --- 1. entry files ------------------------------------------------------------
agents = read("AGENTS.md") or ""
for rel, must in {"AGENTS.md": None, "CLAUDE.md": "AGENTS.md", "GEMINI.md": "AGENTS.md",
                  ".github/copilot-instructions.md": "AGENTS.md"}.items():
    text = read(rel)
    if text is None:
        fail(f"[entry] missing agent entry file: {rel}")
    elif must and must not in text:
        fail(f"[entry] {rel} does not point to {must}")
for rel in ("CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"):
    if agents and rel not in agents:
        fail(f"[entry] AGENTS.md does not reference {rel}")

# --- 2. verification commands named in AGENTS.md -------------------------------
ship = read("scripts/ship.sh") or ""
commands: set[str] = set()
for line in ship.splitlines():
    code = line.split("#", 1)[0]
    if re.search(r"-m pytest\b", code):
        commands.add("pytest")
    for m in re.finditer(r"\bnpm (ci|test|run [\w:-]+)", code):
        commands.add(f"npm {m.group(1)}")
    for m in re.finditer(r"\bscripts/[\w.-]+\.(?:py|sh)\b", code):
        commands.add(m.group(0))
if not ship:
    fail("[verify] scripts/ship.sh not found")
for cmd in sorted(commands):
    if cmd not in agents:
        fail(f"[verify] AGENTS.md does not name `{cmd}` (run by scripts/ship.sh)")

# --- 3. docs map paths resolve ---------------------------------------------------
try:
    tracked = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
except (OSError, subprocess.CalledProcessError):
    tracked = []


def resolves(token: str) -> bool:
    tok = token.strip().rstrip("/")
    if not tok or any(c in tok for c in "*<>{} ") or tok.startswith(("http", "$")):
        return True
    if (ROOT / tok).exists():
        return True
    return any(f == tok or f.endswith("/" + tok) or f.startswith(tok + "/") for f in tracked)


claude = read("CLAUDE.md") or ""
section = re.search(r"^## ساختار\s*$(.*?)(?=^## )", claude, re.S | re.M)
if not section:
    fail("[map] docs map ('## ساختار' in CLAUDE.md) not found")
else:
    for row in section.group(1).splitlines():
        if not row.startswith("|") or set(row) <= set("|- "):
            continue
        cells = row.strip("|").split("|")
        if len(cells) >= 2:
            for token in re.findall(r"`([^`]+)`", cells[1]):
                if not resolves(token):
                    fail(f"[map] path in CLAUDE.md docs map does not resolve: {token}")

# --- 4. newest work-log entry is signed ------------------------------------------
worklog = read("docs/WORKLOG.md")
SIG = re.compile(r"^>\s*\*\*(?:امضا|Signed)[^*]*:\*\*\s*`[^`]+`\s*·\s*\d{4}-\d{2}-\d{2}\s*·\s*\S", re.M)
if worklog is None:
    fail("[log] docs/WORKLOG.md missing")
else:
    entries = re.split(r"^## ", worklog, flags=re.M)
    if len(entries) < 2:
        fail("[log] docs/WORKLOG.md has no entries")
    elif not SIG.search(entries[-1]):
        fail(f"[log] newest WORKLOG entry is not signed: '## {entries[-1].splitlines()[0][:80]}'")

# --- 5. experiences frontmatter (experiences/README.md) ---------------------------
REQUIRED = ["title", "tags", "topic_canonical", "source", "created_at", "updated_at", "merged_from"]
for f in sorted((ROOT / "experiences").glob("*.md")):
    if f.name == "README.md":
        continue
    m = re.match(r"---\n(.*?)\n---\n", f.read_text(encoding="utf-8"), re.S)
    if not m:
        fail(f"[lessons] {f.name}: no YAML frontmatter")
        continue
    keys = set(re.findall(r"^([A-Za-z_]+):", m.group(1), re.M))
    for k in REQUIRED:
        if k not in keys:
            fail(f"[lessons] {f.name}: frontmatter missing '{k}'")

if problems:
    print(f"docs gate: {len(problems)} problem(s)")
    for p in problems:
        print("  ✗", p)
    sys.exit(1)
print("docs gate: OK")
