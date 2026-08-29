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
# AUTH DEATH DETECTOR, layer 1 — error strings, matched BROADLY. The Max OAuth cred expires
# ~monthly (Jun 27, Jul 26, Aug 20) and every claude -p consumer on this Mac dies (Botany, Plate,
# CyMCAT, Forge). LESSON from the Aug-20-29 outage: the CLI's wording CHANGES between versions
# ("Not logged in" → "401 OAuth access token has expired" → "OAuth session expired and could not
# be refreshed") — my exact-string match missed all of it. Match the STEMS (authenticat/oauth/
# /login); the no-delta guard keeps news prose from false-positiving (a real run writes a delta).
if [ ! -f data/_delta.json ] && grep -qiE "authenticat|not logged in|/login|oauth" "$RUNOUT"; then
  echo "$(ts) AUTH EXPIRED — claude -p signed out; EVERY claude-p daemon is down. Fix: claude → /login" >> "$LOG"
  osascript -e 'display notification "claude -p signed out — Botany, Plate + all claude-p daemons are DOWN. Fix: run claude, then /login" with title "Botany updater: AUTH EXPIRED" sound name "Basso"' 2>/dev/null || true
fi
rm -f "$RUNOUT"

# DEAD-STREAK ALARM, layer 2 — alert on OUTCOME, not strings. During Aug 20-28 an expired token
# made claude -p HANG printing NOTHING (66 dead runs, zero notifications — nothing to grep).
# Strings can change or vanish; "N consecutive sweeps produced no delta" cannot. Counter resets
# on any successful delta; fires at 4 dead (=~12h) and every 8th after (~/day while dead).
STREAKF=scripts/.dead_streak
if [ -f data/_delta.json ]; then
  echo 0 > "$STREAKF"
else
  STREAK=$(( $(cat "$STREAKF" 2>/dev/null || echo 0) + 1 )); echo "$STREAK" > "$STREAKF"
  if [ "$STREAK" -eq 4 ] || { [ "$STREAK" -gt 4 ] && [ $(( (STREAK-4) % 8 )) -eq 0 ]; }; then
    echo "$(ts) DEAD STREAK: $STREAK consecutive sweeps with no delta — updater is silently down (auth? hang?). Check scripts/update.log; likely fix: claude → /login" >> "$LOG"
    osascript -e "display notification \"$STREAK consecutive sweeps produced nothing — Botany's updater is silently down. Likely: claude -p auth. Fix: run claude, then /login\" with title \"Botany updater: DEAD STREAK\" sound name \"Basso\"" 2>/dev/null || true
  fi
fi

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
