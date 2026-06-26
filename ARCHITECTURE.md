# AI Tracker — Architecture

A phone-first, self-updating tracker of AI models, benchmarks, and forecasts —
for Christian & his dad. Lives on GitHub Pages; refreshes itself 8×/day.

Working name: **AI Tracker** (rename anytime). Project command: `/ai`.

---

## What it is

1. **History** — every landmark public AI model since GPT-3 (June 2020), with
   GPT-1/2/BERT as pre-history. Dates, params, context, benchmarks, why it mattered.
2. **Trends** — the trajectory of each key benchmark over time (MMLU, GPQA,
   SWE-bench, HumanEval, AA Intelligence Index, context window, $/token), so you
   can *see* the curve of progress.
3. **Now** — the current frontier (the AIModels2026 data, folded in).
4. **Predictions** — for announced-but-untested models, a forecast point **plus an
   uncertainty band**. Measured = solid line/dot; predicted = hollow dot + shaded
   interval that widens further into the future.
5. **Self-updating** — a job runs deep-research **8×/day** (every 3h, 12AM–9PM ET), merges new findings
   into the data files, and pushes to GitHub so the live app refreshes.

## The shape (why it's data-driven)

The app is a **static shell** (`index.html` + PWA assets) that reads JSON data files.
Nothing about a new model release requires editing the app — only the data files
change. That's what lets a headless job update it without touching code.

```
/AI
  index.html            the app (phone-first PWA, renders from data/)
  manifest.json         PWA manifest (installable to home screen)
  sw.js                 service worker (versioned cache — see PWA note below)
  data/
    models.json         master list: every model, all eras (history + now)
    trends.json         benchmark trajectories over time
    predictions.json    forecasts w/ uncertainty bands
    meta.json           lastUpdated, counts, sweep stats, data version
  scripts/
    update.sh           the updater — launchd target, 8×/day
    research-prompt.md   the prompt handed to `claude -p`
    com.christian.ai-tracker.plist   launchd schedule (every 3h, 8×/day ET)
  icons/                home-screen icons
  ARCHITECTURE.md  HANDOFF.md  README.md
```

## Data schema (the contract)

**models.json** — `{ "models": [ Model ], "version": n }`
```
Model = {
  name, lab, released (YYYY-MM-DD | YYYY-MM), params, context, modality,
  open (bool), benchmarks { MMLU, GPQA, "SWE-bench", "AA-Index", ... },
  milestone (bool), status (live|pulled|preview|open), notable, sources []
}
```

**trends.json** — `{ "trends": [ Trend ] }`
```
Trend = {
  benchmark, unit, higherBetter (bool),
  points: [ { date, model, lab, value } ],      // measured, oldest→newest
  predicted: [ { date, model, lab, value, low, high } ],  // forecast band
  notes
}
```

**predictions.json** — `{ "methodology": str, "predictions": [ Prediction ] }`
```
Prediction = { model, lab, expectedDate, benchmark, predicted, low, high, basis, confidence }
```

**meta.json** — `{ lastUpdated (ISO), models (n), labs (n), sweeps (n), dataVersion, note }`

## The update loop (8×/day)

`launchd` (not GitHub Actions — Actions needs a paid API key; Christian's Max
subscription covers `claude -p` for free) fires `scripts/update.sh` every 3 hours
(00:00 / 03:00 / 06:00 / 09:00 / 12:00 / 15:00 / 18:00 / 21:00 ET). More frequent than strictly
needed on purpose: the job only runs while the Mac is awake, so 8 slots/day make it far likelier
one lands during an open-laptop window (launchd also fires a single catch-up run at wake).

`update.sh` does:
1. `cd /Users/christian/Sites/AI`
2. `claude -p "$(cat scripts/research-prompt.md)"` → runs a scoped deep-research
   pass on "newest AI models + any benchmark updates since `meta.lastUpdated`",
   and **writes/merges** the results into `data/*.json` (additive: never drops
   history; updates predicted→measured when a forecast model gets benchmarked).
3. Bump `meta.json` (lastUpdated, counts).
4. `git add data && git commit -m "auto-update <date>" && git push` → Pages redeploys.

Crash-safe & idempotent: a merge step keys on model name, so re-running is safe.
Runs only when the Mac is awake — acceptable for a personal app; revisit with a
tiny always-on host (Cloudflare cron + the D1-flag/local-daemon pattern from
[[reference_web_local_gotchas]]) if 24/7 freshness is ever needed.

## Prediction methodology (v1)

For a model with no measured score on benchmark B:
- Fit the recent **frontier trajectory** of B (last ~6-8 SOTA points) — roughly
  log/linear vs time, respecting saturation ceilings (e.g. MMLU/HumanEval are
  capped near 100, so the curve flattens).
- The **point estimate** = trajectory value at the model's expected date, nudged by
  the lab's recent over/under-performance vs frontier.
- The **uncertainty band** widens with (a) time-to-release and (b) how noisy the
  benchmark is. Near-saturated benchmarks get tight bands near the ceiling; open
  ones (SWE-bench Pro, AA Index) get wider.
- Always render the band, never a bare point. Label confidence low/med/high.
- The forecaster is advisory; measured data always overrides on next sweep.

## PWA notes (from hard-won lessons)

- **Versioned cache.** Service worker cache name carries `meta.dataVersion`; bump
  it every data update so the home-screen app never serves a stale bundle (the
  iOS PWA stale-cache bug — see [[reference_web_local_gotchas]] §3). Data files
  fetched **network-first**; app shell cache-first.
- Installable: `manifest.json` with `display: standalone`, icons, theme color.
- Keep it readable on a phone: bottom tab bar, single column, big touch targets.

## Build phases

- **P0 (now):** scaffold, schema, app shell, updater + launchd, PWA, seed data.
- **P1:** fold in the `ai-history-foundation` workflow output → real models.json +
  trends.json + predictions.json; build the trend charts w/ prediction bands.
- **P2:** ship to GitHub Pages (new repo under polishcow31), install the launchd job.
- **P3:** polish — search, model detail pages, share, dad-friendly onboarding.

## Open decisions for Christian

- Repo name / public-or-unlisted (unlisted = robots.txt + noindex, like Mom's).
- Update times (every 3h, 8×/day ET).
- How aggressive predictions should be (calibrated vs bold).
