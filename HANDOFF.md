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

**P1 — NEXT (data fold-in):** the `ai-history-foundation` workflow (run id
`wf_0dd4029e-ae5`, task `w7ozy0g5h`) is researching the full GPT-3→2026 history +
benchmark trajectories + forecasts. When it lands: assemble real `models.json` (~100
models, all eras), `trends.json` (MMLU/GPQA/SWE-bench/HumanEval/AA-Index/MATH/context/
price trajectories), `predictions.json` (forecaster output + bands), `narrative`/
landmarks; set `dataVersion:1`. The app then comes fully alive — no code changes needed,
only data.

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
