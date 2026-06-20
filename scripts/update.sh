#!/usr/bin/env bash
# Twice-daily auto-update for the AI Tracker. launchd target.
# AI proposes (claude -p -> data/_delta.json); merge.py applies; git publishes.
set -uo pipefail
cd /Users/christian/Sites/AI || exit 1

CLAUDE=/Users/christian/.npm-global/bin/claude
LOG=scripts/update.log
ts() { date "+%Y-%m-%d %H:%M:%S"; }

echo "=== $(ts) update start ===" >> "$LOG"

# 1. research pass -> proposes data/_delta.json (uses Max subscription, no API key)
#    --dangerously-skip-permissions is required: headless `claude -p` otherwise
#    queues tool calls pending an interactive approval that never comes, so the
#    delta is never written. Safe here — the AI only PROPOSES data/_delta.json;
#    merge.py is the deterministic authority that decides what actually lands.
rm -f data/_delta.json
"$CLAUDE" -p --dangerously-skip-permissions "$(cat scripts/research-prompt.md)" >> "$LOG" 2>&1 \
  || { echo "$(ts) claude -p failed" >> "$LOG"; exit 1; }

# 2. deterministic, authoritative merge
if [ -f data/_delta.json ]; then
  python3 scripts/merge.py >> "$LOG" 2>&1 || { echo "$(ts) merge failed" >> "$LOG"; exit 1; }
  rm -f data/_delta.json
else
  echo "$(ts) no delta written" >> "$LOG"
fi

# 3. publish only if the dataset actually changed
if ! git diff --quiet data/ 2>/dev/null; then
  git add data/
  git commit -q -m "auto-update $(date +%F)"
  if git push -q 2>>"$LOG"; then
    echo "$(ts) pushed" >> "$LOG"
  else
    echo "$(ts) push failed (committed locally)" >> "$LOG"
  fi
else
  echo "$(ts) no data changes" >> "$LOG"
fi
echo "=== $(ts) done ===" >> "$LOG"
