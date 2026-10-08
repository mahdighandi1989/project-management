#!/usr/bin/env bash
# Stop hook: do not let a session finish with work that is not on main
# (owner's standing rule: every finished task is committed, pushed and deployed).
input="$(cat)"
case "$input" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac
cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0
dirty="$(git status --porcelain 2>/dev/null | head -5)"
ahead="$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
if [ -n "$dirty" ] || [ "${ahead:-0}" != "0" ]; then
  reason="Owner rule (CLAUDE.md): finished work must be shipped. "
  [ -n "$dirty" ] && reason+="Uncommitted changes exist. "
  [ "${ahead:-0}" != "0" ] && reason+="HEAD has ${ahead} commit(s) not on origin/main. "
  reason+="Add a signed section to docs/WORKLOG.md, then run scripts/ship.sh \"type(scope): summary\". If the work is intentionally unfinished, say so explicitly to the owner instead."
  printf '{"decision":"block","reason":%s}\n' "$(printf '%s' "$reason" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"
fi
exit 0
