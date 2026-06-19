# AI Tracker — Handoff

Phone-first, self-updating AI history + trends + forecasts app for Christian & dad.
Resume command: `/ai`. Local: `localhost:8095`. Full design: [ARCHITECTURE.md](ARCHITECTURE.md).

## State — Jun 19 2026

**P0 DONE & verified (this session):**
- `index.html` — phone-first PWA shell, bottom-nav (Now / History / Trends / Predict /
  About), renders from `data/*.json`. Verified at 375px: cards, milestone timeline,
  time-series charts, and the **prediction uncertainty cone** all render.
- `data/{models,trends,predictions,meta}.json` — SEED data (10 landmark models +
  2 trends + 3 forecasts). `dataVersion:0` flags seed → UI shows a "being researched"
  banner. **Replaced in P1.**
- Auto-updater: `scripts/update.sh` + `scripts/merge.py` (AI proposes a `_delta.json`,
  deterministic Python merge applies it — additive, idempotent by name) +
  `scripts/research-prompt.md` + `scripts/com.christian.ai-tracker.plist` (6am+6pm ET).
  **Merge pipeline functionally tested & proven** (added model, promoted a prediction,
  bumped version, reverted clean). Not yet installed.
- PWA: `manifest.json`, `sw.js` (data network-first = always fresh; shell cache-first).
- Committed as the initial git commit.

**P1 DONE (Jun 19):** the `ai-history-foundation` workflow (`wf_0dd4029e-ae5`) returned
the full history; `scripts/build_data.py` transformed it into the live data files —
**96 models GPT-1→2026, 48 landmarks, 8 trend curves** (MMLU/GPQA/SWE-bench/HumanEval/
AA-Index/MATH/context/price) with **16 forecasts attached to the curves**. `dataVersion:1`,
seed banner gone. Verified at 375px: Now (23 cards), History (48-node timeline from
GPT-1 2018), Trends (8 charts incl. prediction cones), Predict (16 gauges). Re-run
`python3 scripts/build_data.py <workflow-output.json>` to rebuild from a fresh run.
NOTES: app renamed **AI Tracker → Robots**. Views: **Now** (lab-filter chips + rich
cards: price/modality/all-benchmarks, tap-to-expand), **History** (16 landmarks +
show-all), **Charts** (accordions: trends-over-time / cadence-2026 / weights-sparsity /
head-to-head), **Predict** (forecast gauges + Upcoming/horizon list), **More**
(accordions: leaderboard / didn't-make-the-cut / sources / how-it-works). `sw.js` is now
**network-first for everything** (cache = offline fallback only) — no more SHELL_V
bumping, dev changes and twice-daily data both always show fresh. A few editorial sets
(WEIGHTS, leaderboard, killed, sources, prices) are embedded static in index.html for now
— data-ify them later so the updater maintains them.

**P2 — deploy + automate (needs Christian's go):**
- Create GitHub repo under polishcow31 (Chrome — token can't create repos). Free Pages
  repos are PUBLIC source; if he wants it unlisted add `robots.txt`+noindex (already
  has the meta noindex). **Public repo under his name = ask-first per CLAUDE.md.**
- `git push` → enable Pages (Chrome). Install launchd: copy plist to
  `~/Library/LaunchAgents/`, `launchctl load`. Confirm `claude -p` writes `_delta.json`
  headlessly (the one untested link).

**P3 — polish:** home-screen icons (`icons/icon-{192,512}.png` — referenced, not made
yet; nano-banana or SVG→PNG via headless Chrome per [[reference_web_local_gotchas]]),
search, model-detail pages, dad onboarding, share.

## Decisions made (overridable)
- Phone-first PWA on GitHub Pages; updates via **launchd + `claude -p`** (free on Max,
  not paid GitHub Actions). History anchored at **GPT-3 (Jun 2020)**. Predictions always
  shown as point + **uncertainty band** (widening with horizon).

## Open for Christian
- Repo name + public-or-unlisted. Update times (default 6am/6pm ET). Prediction
  aggressiveness (calibrated vs bold). App name ("AI Tracker" is a placeholder).

## Gotchas
- Mobile screenshot verify: the `.view` fade animation gets caught dim by
  preview_screenshot — disable animation or use preview_inspect ([[reference_web_local_gotchas]] §3).
- Updater runs only when the Mac is awake (fine for personal; cloud-cron is the fallback).
- This evolved from `~/Sites/AIModels2026` (the original one-off page) — that still
  exists at `localhost:8094` as the 2026-only deep-dive; AI Tracker is the superset.
