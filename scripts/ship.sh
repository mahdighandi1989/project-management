#!/usr/bin/env bash
# Ship the current work: verify ⇒ commit ⇒ push the working branch ⇒ merge into
# main ⇒ push main. Render auto-deploys `main` (backend AND frontend), so a
# successful run = deployed. Modelled on Detective-1's scripts/ship.sh.
#
#   scripts/ship.sh "type(scope): summary"
#
# Refuses to ship if backend tests, the frontend build or the docs gate fail.
# Never force-pushes.
set -euo pipefail

MSG="${1:-}"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
retry() { # network ops: 4 retries with exponential backoff
  local n=0 delay=2
  until "$@"; do
    n=$((n + 1)); [ "$n" -ge 5 ] && return 1
    echo "retrying in ${delay}s…"; sleep "$delay"; delay=$((delay * 2))
  done
}

# --- 1. checks -------------------------------------------------------------
say "Source files hidden by .gitignore"
hidden="$(git ls-files --others --ignored --exclude-standard -- frontend/src backend/app backend/tests docs scripts experiences \
  | grep -v -E '(__pycache__|\.pyc$|\.pytest_cache|^docs/supervisor/inspection/(QUEUE|URGENT)\.md|^docs/supervisor/inspection/(shots|files)/|^docs/supervisor/last_surface_scan\.json)' || true)"
if [ -n "$hidden" ]; then
  echo "$hidden"
  echo "❌ these source files exist locally but are ignored by .gitignore — they would be missing on Render. Fix .gitignore."
  exit 1
fi

say "Backend tests"
PY="${PYTHON:-python3}"
(cd backend && "$PY" -c "import fastapi, pytest, sqlalchemy" 2>/dev/null) || (cd backend && "$PY" -m pip install -q -r requirements.txt)
run_tests() { (cd backend && INSPECTION_SYNC_DISABLED=1 "$PY" -m pytest -q -p no:cacheprovider); }
run_tests || { echo "❌ backend tests failed — not shipping"; exit 1; }

say "Frontend build"
(cd frontend && { [ -d node_modules ] || npm ci --no-audit --no-fund; } && NEXT_TELEMETRY_DISABLED=1 npm run build >/tmp/ship-frontend-build.log 2>&1) \
  || { tail -40 /tmp/ship-frontend-build.log; echo "❌ frontend build failed — not shipping"; exit 1; }

say "Docs gate"
"$PY" scripts/docs_gate.py || { echo "❌ docs gate failed — not shipping"; exit 1; }

# --- 2. commit ---------------------------------------------------------------
BRANCH="$(git branch --show-current)"
if [ -n "$(git status --porcelain)" ]; then
  [ -n "$MSG" ] || { echo "❌ uncommitted changes: pass a commit message"; exit 1; }
  say "Commit"
  git add -A
  git commit -q -m "$MSG"
fi

# --- 3. push working branch --------------------------------------------------
if [ "$BRANCH" != "main" ]; then
  say "Push $BRANCH"
  retry git push -q -u origin "$BRANCH"
fi

# --- 4. merge into main and push (deploy) ------------------------------------
say "Merge into main"
retry git fetch -q origin main
if ! git merge-base --is-ancestor origin/main HEAD; then
  echo "main has moved — merging origin/main into $BRANCH first"
  git merge -q --no-edit origin/main
  run_tests || { echo "❌ tests failed after merging main"; exit 1; }
  [ "$BRANCH" != "main" ] && retry git push -q origin "$BRANCH"
fi
retry git push -q origin HEAD:main
say "Shipped $(git rev-parse --short HEAD) to main — Render will deploy it automatically"
