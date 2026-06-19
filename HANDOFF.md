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
app renamed **AI Tracker → Robots**.

**CURRENT app = 4 tabs (Home / Now / Charts / More)** after a long iteration session:
- **Home** (default): overview hero, AA-Index leaderboard, "best model for…" use-case
  picks, explore links.
- **Now** = the full catalog (History was MERGED in): all 96 models as rich cards
  newest-first; lab-filter chips + "★ Landmarks only" + the Frontier/Open switch.
- **Charts** = Charts+Predict MERGED: per-company **trajectory** charts (AA + SWE — each
  lab's leading model over time, tap a dot for the model, dashed line + faded dot =
  predicted next), a **release-cadence LINE graph** (historical-avg releases/qtr),
  a **head-to-head** comparison table, a **Prediction-markets** section, and **On the
  horizon**. DROPPED: trends-over-time, weights/sparsity.
- **More**: leaderboard, didn't-make-the-cut (+re-sweep correction), sources, how-it-works.
- **All open-source toggles → real Frontier↔Open segmented switches** (Home/Charts 2-state
  default Frontier; Now 3-state All/Frontier/Open). NOT "All vs Open".
- `sw.js` = **network-first for everything** (no SHELL_V bumping). Editorial sets (prices,
  leaderboard, killed, sources, weights, head-to-head, UPCOMING) are still **static in
  index.html** — data-ify later. The data files (`models/trends/predictions/meta`) drive
  Home/Now/Charts trajectories + cadence.

### ▶▶ QUEUED FOR NEXT SESSION (do this first — session was out of context)
**Integrate the prediction-markets + historics research.** The completed workflow's
output is saved durably (and committed) at **`scripts/markets-historics-raw.json`**
(53 markets, 53 historic AA/SWE points, 16 per-lab forecasts; shape = `{result:{markets,
historics,predictions,methodology}}`). Three jobs:
1. **Fill the Prediction-markets section.** Load the `markets` into the `MARKETS=[]`
   array in `index.html` (map to `{question,platform,forecast,resolveDate}`; `marketRow()`
   already renders them). Highlights: Polymarket "best model end-2026" Anthropic 64% /
   Google 15% / OpenAI 10%; GPT-6 by Dec 82%; GPT-5.6 by Jul 97%; Metaculus GPQA '26 ~99%,
   SWE-Verified resolved 83% (90% crossed Apr 7). Best to put MARKETS in a `data/markets.json`
   so the updater can maintain it (currently static seam).
2. **Re-anchor the dashed trajectory forecasts to the markets** (the `predictions` array
   has per-lab AA/SWE next-model forecasts anchored to those markets). `leadingTrajectory()`
   in index.html currently extrapolates per-lab — swap its `pred` to use these market-based
   values when available; cite source in the dot's click detail.
3. **Extend the AA/SWE trajectory lines back** with the `historics` points (pre-2026,
   `estimate:true` — render estimates visually distinct, e.g. hollow/dashed). Add them to
   `data/models.json` benchmarks or a side trajectory dataset.
Also worth: `git rm` the raw file or keep it as the source-of-record once integrated.

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

## Decided (Jun 19)
- Name **Robots**; repo `robots` → **polishcow31.github.io/robots, unlisted**; updates
  **6am/6pm ET**; forecasts **calibrated** + **market-based** (Polymarket/Metaculus/Epoch).
- **Deploy (P2) is pending HIS GO** — he chose "look it over first." Don't deploy until
  he says "deploy Robots."

## Gotchas
- Mobile screenshot verify: the `.view` fade animation gets caught dim by
  preview_screenshot — disable animation or use preview_inspect ([[reference_web_local_gotchas]] §3).
- Updater runs only when the Mac is awake (fine for personal; cloud-cron is the fallback).
- This evolved from `~/Sites/AIModels2026` (the original one-off page) — that still
  exists at `localhost:8094` as the 2026-only deep-dive; AI Tracker is the superset.
