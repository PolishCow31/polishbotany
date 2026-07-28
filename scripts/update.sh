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
#    WATCHDOG: a 25-min cap (perl alarm — macOS has no GNU `timeout`) so a hung/too-slow run can
#    NEVER block future launchd fires (launchd won't start a 2nd instance while one is running).
#    Non-zero exit (incl. the watchdog kill) does NOT abort — step 2 still merges whatever delta
#    was written before the cutoff, and logs if none was.
rm -f data/_delta.json
RUNOUT=$(mktemp -t ai-tracker-run)
perl -e 'alarm shift @ARGV; exec @ARGV' 1500 \
  "$CLAUDE" -p --dangerously-skip-permissions "$(cat scripts/research-prompt.md)" > "$RUNOUT" 2>&1 \
  || echo "$(ts) claude -p exited non-zero / hit the 25-min watchdog — merging any delta it wrote" >> "$LOG"
cat "$RUNOUT" >> "$LOG"
# AUTH DEATH DETECTOR: the Max OAuth cred expires ~monthly (Jun 27, Jul 26) and every claude -p
# consumer on this Mac dies SILENTLY (Botany, Plate relay, CyMCAT engine). Match only the CLI's
# exact error strings (news prose won't contain these verbatim + a real run always writes a delta).
if [ ! -f data/_delta.json ] && grep -qiE "not logged in|please run /login|invalid authentication credentials" "$RUNOUT"; then
  echo "$(ts) AUTH EXPIRED — claude -p signed out; EVERY claude-p daemon is down. Fix: claude → /login" >> "$LOG"
  osascript -e 'display notification "claude -p signed out — Botany, Plate + all claude-p daemons are DOWN. Fix: run claude, then /login" with title "Botany updater: AUTH EXPIRED" sound name "Basso"' 2>/dev/null || true
fi
rm -f "$RUNOUT"

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
