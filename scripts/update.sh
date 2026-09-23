#!/usr/bin/env bash
# Twice-daily auto-update for the AI Tracker. launchd target.
# AI proposes (claude -p -> data/_delta.json); merge.py applies; git publishes.
set -uo pipefail
cd /Users/christian/Sites/AI || exit 1

CLAUDE=/Users/christian/.npm-global/bin/claude
MODEL=claude-opus-5-5   # pinned Sep 23 2026: with no --model this inherited the interactive Fable default and died on its weekly cap
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
  "$CLAUDE" -p --model "$MODEL" --dangerously-skip-permissions "$(cat scripts/research-prompt.md)" > "$RUNOUT" 2>&1 \
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
# LIMIT DETECTOR, layer 1b — a usage cap is NOT an auth death, and the fix is different. Sep 21-22
# 2026: the Fable weekly cap was hit; claude -p died in ~3s with "You've reached your Fable 5 limit"
# for 11+ straight runs while layer 2 told him to /login. Capture the cause so layer 2 names it.
FAILCAUSE=""
if [ ! -f data/_delta.json ]; then
  CAP=$(grep -oiE "reached your [^.]*limit" "$RUNOUT" | head -1 | tr -d '"')
  if [ -n "$CAP" ]; then FAILCAUSE="usage cap ($CAP)"
  elif grep -qiE "authenticat|not logged in|/login|oauth" "$RUNOUT"; then FAILCAUSE="auth expired"; fi
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
    if [ -n "$FAILCAUSE" ]; then WHY="cause: $FAILCAUSE"; else WHY="no error text (auth? hang?)"; fi
    case "$FAILCAUSE" in
      usage*) FIX="wait for the cap to reset, or point claude -p at a model with headroom" ;;
      *)      FIX="run claude, then /login" ;;
    esac
    echo "$(ts) DEAD STREAK: $STREAK consecutive sweeps with no delta — $WHY. Check scripts/update.log; likely fix: $FIX" >> "$LOG"
    osascript -e "display notification \"$STREAK sweeps produced nothing — $WHY. Fix: $FIX\" with title \"Botany updater: DEAD STREAK\" sound name \"Basso\"" 2>/dev/null || true
  fi
fi

# 2. deterministic, authoritative merge
if [ -f data/_delta.json ]; then
  python3 scripts/merge.py >> "$LOG" 2>&1 || { echo "$(ts) merge failed" >> "$LOG"; exit 1; }
  rm -f data/_delta.json
else
  echo "$(ts) no delta written" >> "$LOG"
fi

# 2b. AA-Index column = a straight copy of Artificial Analysis's live index (scripts/aa_sync.py): fills new models,
#     mirrors re-scores. When AA re-versions its index the sync refuses (exit 2) and this alarms once a day instead,
#     because a re-version needs the manual `python3 scripts/aa_sync.py --rebase`. (Sep 23 2026: a hand-pinned v4.1
#     scale froze the leaderboard for weeks after AA moved to v4.3 — Fable 5.1 shown at 66 vs AA's 53.)
python3 scripts/aa_sync.py --sync >> "$LOG" 2>&1
if [ $? -eq 2 ] && [ "$(cat scripts/.aa_rescale_alarm 2>/dev/null)" != "$(date +%F)" ]; then
  date +%F > scripts/.aa_rescale_alarm
  osascript -e 'display notification "Artificial Analysis re-versioned its index; AA numbers are frozen until you run: python3 scripts/aa_sync.py --rebase" with title "Botany: AA index re-versioned" sound name "Basso"' 2>/dev/null || true
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
