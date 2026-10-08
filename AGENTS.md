# AGENTS.md

All agents (Claude, Codex, Gemini, Copilot, …) working on this repository must follow
[`CLAUDE.md`](CLAUDE.md): ship every finished task with `scripts/ship.sh`, log every change in
`docs/WORKLOG.md` (signed), keep the app behind Google sign-in, never delete a capability without
the owner's approval, and never write secrets or the owner's e-mail into the repo.
Other tools' entry files — [`GEMINI.md`](GEMINI.md), [`.github/copilot-instructions.md`](.github/copilot-instructions.md) —
only point here. Modelled on the owner's sibling repos Detective-1 and ALLIN1.

`main` auto-deploys to production on Render (backend and frontend): every push to `main` is a
production change.

## 1. Read first, in this order
1. `AGENTS.md` (this file) — wins over any tool-specific file.
2. [`CLAUDE.md`](CLAUDE.md) — the owner's standing directives (Persian) + repo map.
3. every file in [`experiences/`](experiences/) — binding lessons.
4. the **last 5 entries** of [`docs/WORKLOG.md`](docs/WORKLOG.md) — newest is at the BOTTOM.
5. [`docs/supervisor/README.md`](docs/supervisor/README.md) — the supervisor Routines and «نظارت و سرکشی».

## 2. Verification — what `scripts/ship.sh` runs

| Command (as run by `scripts/ship.sh`) | Protects |
|---|---|
| the ignored-source check inside `scripts/ship.sh` | Source files hidden by `.gitignore` (would be missing on Render). |
| `pytest` (`cd backend && python -m pytest -q`) | API behaviour, the login wall, inspection guards, Drive pipeline. |
| `npm ci` (`cd frontend && npm ci`, only when `node_modules` is missing) | Lockfile in sync. |
| `npm run build` (`cd frontend && npm run build`) | TypeScript types + the Next.js production build Render deploys. |
| `scripts/docs_gate.py` (`python3 scripts/docs_gate.py`) | Entry files, this command list, docs-map paths, signed newest WORKLOG entry, lessons frontmatter. |

## 3. Owner's standing directives
- **Ship automatically after every finished task:** `scripts/ship.sh "type(scope): summary"` — checks, commit,
  push the working branch, merge into `main`, push `main` (= deploy). Do not ask the owner to commit/push/merge;
  no PR unless asked. A `Stop` hook (`.claude/settings.json`) blocks sessions that end with unshipped work.
- **Log everything:** a new section at the bottom of `docs/WORKLOG.md` after every task (FINDING / DECISION /
  CHANGE / VERIFY / REVERT / CORRECTION / OWNER / TODO / BLOCKED), ending with the signature line (§4).
  Never delete or rewrite an earlier entry.
- Reply to the owner **in Persian**, plainly and briefly. UI text is Persian with `dir="rtl"`.
- `prompt/` belongs to the owner's external tooling — do not touch.

## 4. Signature protocol
1. **WORKLOG:** the last line of every entry: `> **امضا:** \`<agent-id>\` · YYYY-MM-DD · <how it was verified>`
   (`<agent-id>` = the model/tool you actually are, or `human (owner)`). Sign only what you wrote.
2. **git commits:** a `Co-Authored-By:` trailer naming the agent.

## 5. Conflict rule
If `CLAUDE.md` and `AGENTS.md` disagree, `AGENTS.md` wins and the drift is fixed in the same commit.
