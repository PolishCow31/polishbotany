# AI Tracker — Handoff

Phone-first, self-updating AI history + trends + forecasts app for Christian & dad.
Resume command: `/ai`. Local: `localhost:8095`. Full design: [ARCHITECTURE.md](ARCHITECTURE.md).

## State — Jun 19 2026

### ✓ DONE (Jun 19, session 20) — NBP forest background · border wildflowers · 5-frame fox walk
(1) **Forest background (nano-banana PRO).** Generated a moody misty-pine forest (`img/forest-bg.jpg`, 860px, NBP
Pro 2K 9:16, downscaled). New fixed `#forest` layer (z-2) = the image (`center top/cover fixed`) under a dark
vertical scrim gradient (`.88` top → `.42` mid → `.72` bottom) so the bright misty sky doesn't wash out the header
and the UI stays legible. Body bg → transparent (forest shows through margins/gaps/header); column borders bumped to
`--line2`; pollen opacity .7→.55. Grounds the app; cards stay opaque/readable over it.
(2) **Wildflowers framing the borders** (his ask: on the borders, NOT covering data). 2 nano-banana wildflower
sprigs (`flower-a/b.png`, white-cream + pink-lavender, magenta-keyed). New fixed `#flowers` overlay matching the
column (max-width 560 centered) with 6 sprigs anchored in the **edge gutter / corners** (`.fl-tl/-tr/-ml/-mr/-bl/-br`,
small ~33-44px, negative offsets so they sit at/just outside the column frame). On desktop they hug the column edge
in the margin; on mobile in the ~14px card-padding gutter — clear of card text (verified: no real text coverage).
(3) **Fox walk = 5 frames now.** Added 3 nano-banana frames; dropped the first "leap" reroll (body too low/stretched)
and regenerated it body-height-locked. WALK cycle = `[a,e,b,d,c]` with a per-frame `BOB` bounce array, cadence
165→**115ms**. (`fox-walk-c/d/e.png` added; all magenta-keyed, nearest-resized.) Walk reads much smoother (foreground
tab; rAF still pauses when hidden). Verified: forest+flowers+fox load, data intact (96 models, Pulse), zero console
errors. **Redeploy = `git push`.** NOTE: preview-panel shows "0 models" only because that sandbox can't fetch
`data/` — the real localhost server + live site load data fine.

### ✓ DONE (Jun 19, session 19) — removed all foliage; gave the fox a real walk cycle
(1) **Removed ALL vines/branches** per his call — deleted the `decorate()` foliage IIFE + `.vine-deco` CSS + the
3 vine PNGs (`git rm` vine-corner/vine-hang/sprig). Verified 0 `.vine-deco`, no 404s, no console errors.
(2) **Fox walk now actually animates.** The old `fox-walk-b` was ~identical to `-a` (the model barely moved the
legs) so the 2-frame swap showed no motion. Regenerated `fox-walk-b` via nano-banana as a distinct **passing pose**
(legs gathered under the body, lifted) using `-a` as the style reference — confirmed visibly distinct (stride vs
gathered). Controller tuned: frame cadence 190→**165ms**, gait bob -1.5→**-2.5px** (body lifts on the passing
frame → bouncy trot). Walk reads animated on a foreground tab (rAF still pauses when hidden). **Redeployed via
`git push`** (site is live at polishcow31.github.io/polishbotany).

### ✓ DONE (Jun 19, session 18) — RENAMED to Botany · PUBLISHED · walking fox
**(1) Renamed Robots → Botany.** `<title>`/apple-title/`<h1>`/manifest name+short_name = "Botany"; logo+favicon
swapped from the chart-line to a green leaf glyph; manifest theme/bg → `#0b140f`.
**(2) PUBLISHED (he gave the go).** New PUBLIC repo **github.com/PolishCow31/polishbotany** (created via Chrome —
token still can't, 403). Committed all pending work to `main`, `git push` via the osxkeychain cred (worked), enabled
Pages via Chrome (Settings▸Pages → Deploy from branch `main` `/ (root)` → Save). **Live (unlisted): https://polishcow31.github.io/polishbotany/**
(robots.txt `Disallow:/` + noindex meta both present). Added `.gitignore` for the local backups (`index.html.bak-*`,
`*.matrix-shelved`, `_delta.json`, `*-raw.jpeg`). First Pages build takes ~1-2 min. **Re-deploy now = `git push`.**
**(3) Fox rebuilt** to walk + sit. Three nano-banana pixel sprites (`img/fox-walk-a/b.png`, `fox-sit.png` — finer
pixels, "more real"; keyed via the magenta PIL workflow, nearest-resized to preserve pixels). New element = an
`<img id="fox-img">` (not the SVG rects). Controller (rAF in the effects script): the fox **ambles** left↔right along
the **top edge of the overview** (feet on `.hero`'s top border, tracked each frame via `getBoundingClientRect`),
**flips** to face its direction, alternates the 2 walk frames + a gait bob, and **randomly sits** (swaps to the sit
sprite, pauses 3-8s) then resumes. Added `#v-home .hero{margin-top:54px}` to open a walking band ABOVE the card so
the fox is on-top-not-inside and **never overlaps the "OVERVIEW" words** (it sits in the band below the vh). rAF
pauses when the tab's hidden (so it looked frozen in the headless verify tab — it's correct; runs on a foreground
tab). Verified: rename live, fox positions on the rim clear of OVERVIEW (geometry + screenshot), data intact, zero
console errors. Backup before this: `index.html.bak-prevines` (pre-fox-sprites work is in git history).
**NEXT per his plan: keep perfecting UI, then perfect the routines (install the 6am/6pm launchd updater — still not installed), then done.**

### ✓ DONE (Jun 19, session 17) — realistic foliage on random card borders (replaced the bad SVG branches)
He called the bottom SVG branches "done poorly" (a cheap stroke-path fake — exactly what [[feedback_realistic_visuals]]
warns against) and asked for "mostly realistic branches/vines/leaves on random borders." **Removed the `#roots`
undergrowth entirely.** Generated **3 real botanical assets via nano-banana** (`img/vine-corner.png`, `vine-hang.png`,
`sprig.png`) — semi-realistic ivy/pothos illustrations with veins + shading. TOOLING NOTE: his machine has **no
ffmpeg/imagemagick and no brew**, so the nano-banana `-t` transparent flag can't run; instead generated on a flat
**MAGENTA** chroma background (NOT green — the leaves are green) and keyed it out with a reusable PIL script
`scripts/chroma_key.py` (magenta-key + despill + autocrop). Downscaled to ~140KB each. **Placement engine** (IIFE in
the effects script): `decorate()` scatters assets onto ~26% of cards (`.mcard,.chartcard,.pcard,.newsrow,.mktrow,
.ftab-panel,.phero,.bestcard,.note` — excludes tight rows + the rapidly-rerendering `.gterm`), **deterministic by a
content hash** so it's stable across re-renders (no flicker). Corners limited to **BR/BL + a right-edge drape** to
clear titles (top-left) and dates (top-right); `.vine-deco` is `position:absolute; pointer-events:none; z-index:6;
opacity:.93` with a drop-shadow; the card gets `overflow:visible; z-index:1` to let it overhang. A debounced
`MutationObserver` on `main` (disconnect-during-decorate) re-applies after every view render. Verified: vines render
(~37 across views), titles/dates legible, Details modal still clickable through them, data intact, zero console
errors. Backup before this: `index.html.bak-prevines`. Assets in `img/`, keyer in `scripts/`.

### ✓ DONE (Jun 19, session 16) — More = live glossary search; drop Home Explore (verified)
- **More**: definitions search is now **live + persistent at the top, no accordion** (the first thing you see). The
  149 terms are NOT listed up front — `glossResults('')` returns a hint ("Type a word or acronym to search 149 AI
  terms…"); typing surfaces matches live via the existing `#glossq` `input` listener (works because the input is
  always in the DOM now). vh renamed "More"→"Definitions & acronyms". **Sources kept as an accordion below**,
  unchanged. CSS `.gloss-hint` added.
- **Home**: removed the **Explore** section (the hsec + `.explore` data-goto buttons) — redundant with the bottom
  nav. Leaderboard + "Best model for…" kept. (The `[data-goto]` click handler stays — still used by the Charts→
  Predict pointer.)
Verified: Home Explore gone (leaderboard/best intact), More search at top with 0 terms upfront + working live
search ("rlhf"→4 matches, clear→hint), Sources accordion below, zero console errors, data intact.

### ✓ DONE (Jun 19, session 15) — Home "Pulse": one dense living paragraph the two routines rewrite (verified)
Replaced the Home overview hero's stat-sentence with **The Pulse** — one dense 4–6 sentence situation-brief of the
AI frontier (leader & race, biggest news, imminent releases + market odds, a watch-item), `**bold**` on key facts.
It's **data-driven and maintained by the twice-daily routines**: new `editorial.pulse {text,updated,routine}`;
`boot()` loads `PULSE=ed.pulse`; `renderHome()` shows `fmtPulse()` (escapes, then `**x**`→`<b>`) + a meta line
"● The Pulse · {6am/6pm/latest} sweep · updated Xm ago · auto-refreshes 6am & 6pm ET" (pulsing dot). Falls back to
the old computed sentence if pulse missing. **Updater plumbing:** `merge.py` editorial block now applies
`editorial.pulse` (string or `{text}`), stamping `updated`=now + `routine`=AM/PM by ET hour — **tested end-to-end**
(sample delta → routine PM, timestamp, text replaced; restored). `research-prompt.md` gained an "ALWAYS rewrite
pulse" instruction (one dense paragraph, grounded only in that run's data, ~4–6 bolds, plain voice) + schema
`editorial.pulse`. **I wrote the current Pulse** (the "manual" one, in editorial.json): Opus 4.8 leads 56 / tight
race / export-control pull of Fable5+Mythos5 / G7 / GPT-5.6 + Gemini 3.5 Pro ~97% for July / Sanders 50% tax
watch-item. Verified: renders (895 chars, 7 bolds), meta line correct, zero console errors, data intact (dataVersion
still 3). The fox still clears it (hero padding-right:60). CSS `.pulse-txt/.pulse-meta/.pulse-dot` in the forest block.

### ✓ DONE (Jun 19, session 14) — file-cabinet sub-tabs for Current/Charts/Predict/News (verified)
Per his request, replaced the accordion/seg/chip systems in 4 views with a **file-folder tab** system: a tab strip
at the top of the view whose **active tab is stitched to the content panel** (same bg, border-bottom removed via
`margin-bottom:-1px` over the panel's `--line2` top border → "attached to the page, no bottom border"); inactive
tabs sit recessed/darker (`--bg2`, muted text). New reusable `fileTabs(view,active,tabs)` helper + `.ftabs/.ftab/
.ftab-panel` CSS + a single `.ftab` delegated click handler. Per-view state: **Current** `nowCat` → tabs All/
Frontier/Open (with counts) + panel of 96 cards; **Charts** new `chartsTab` → Frontier-by-company / Release cadence
/ Head-to-head (was 3 accordions); **Predict** new `predictTab` → Release radar / Prediction markets (was 2
accordions); **News** `newsTopic` → All + 7 topic tabs (was filter chips), strip is horizontally scrollable.
Content-generating fns (modelCard, trajWrap, cadenceLine, headToHead, relRow, marketsBody, newsRow) all REUSED —
**zero data-wiring change**. Inner `.seg` controls (traj AA/SWE, hh metric) still live inside the Charts panel and
still re-render via the existing seg handler (#traj-aa-wrap/#traj-swe-wrap/#hh-wrap kept). `.ftab-panel .chartcard`
chrome stripped so charts sit clean in the panel. VERIFIED (Chrome MCP @ :8095): all 4 views render tabs+panel,
switching swaps content correctly (now 96 cards · charts 3 · predict radar 12 ↔ markets 51 · news 8 tabs/15 rows),
all data intact, zero console errors, zero overflow. The old `.fchip`/`.seg('now')` handlers are now dead but
harmless (left in place).

### ✓ DONE (Jun 19, session 13) — forest critters: living pixel fox + bark undergrowth (verified)
Two requested decorative features on the forest theme, both self-contained (no data-wiring touched):
1. **Living pixel-art fox** perched top-right of the Home overview hero. Hand-built pixel fox (~48 `<rect>` in a
   32×34 viewBox, `shape-rendering:crispEdges`, `image-rendering:pixelated`) — orange head/ears, cream face+chest,
   dark eyes/nose/paws, curled tail. "Living" via 3 idle CSS animations: `foxBreathe` (gentle bob), `foxBlink`
   (eyes `.foxEye` scaleY), `foxTail` (`#foxTail` rotate flick); `prefers-reduced-motion` disables all. Element
   `#fox` is a body child (absolute, top:80 right:12, z-16, pointer-events:none) so it survives renderHome()
   re-renders; a small JS IIFE toggles `.fox-off` on nav/`[data-goto]` clicks so it shows ONLY on Home. Added
   `#v-home .hero{padding-right:60px}` so the hero text clears the fox.
2. **Bark branch/root undergrowth** — `#roots` SVG (13 stroke paths + 5 green leaf-bud circles, bark `--bark
   #6b4a2f`/`--bark2 #8a5e3a`), a delicate fringe rising from just above the bottom nav (fixed, z-24 FOREGROUND,
   pointer-events:none, opacity .68, height 50). NOTE: tried it as a z-1 BACKGROUND first — invisible, dense
   content covered it; foreground fringe above the nav ("forest floor") is what reads. Tuned height/opacity down
   so it doesn't cross the card data values.
Verified: fox animations all running, fox toggles Home-only, 96 models/96 briefs/149 glossary/53 markets/13
releases/15 news intact, all tabs render, zero overflow, zero console errors. Backup before this: `index.html.bak-prefox`.

### ✓ DONE (Jun 19, session 12) — FOREST / WOODLAND @ DUSK reskin (Pass 1, verified) — CURRENT LIVE THEME
After reverting the Matrix overhaul (session 11) as too much, Christian asked for a **nature theme**, dialed back.
Design locked via a 2nd 10-question questionnaire → memory `project_robots_forest_ui.md`. Choices: **forest/woodland ·
dusk twilight gradient (dark) · earth+green two-tone (green `#62c177` primary, bark/amber `#d99a4e` secondary) ·
lab colors RE-TINTED to natural hues (max hue-spread: OpenAI pine, Anthropic terracotta, Google muted-sky, xAI
driftwood, Meta indigo, NVIDIA moss, etc.) · ONE faint ambient effect = slow drifting pollen/firefly particles
(canvas `#pollen`, FPS-capped 24, ≤64 dots, paused-when-hidden, reduced-motion static) · minimal motion otherwise
(kept the original soft fade) · CLEAN SANS kept (recolor only) · soft & rounded warm cards (16px radius, gentle
shadow) · TOPOGRAPHIC chart backdrop (faint repeating-radial contour rings behind `.chartcard`) · themed but
restrained, legibility wins.** Same safe-reskin method as before: rewrote `:root` (chrome + lab vars), appended a
"FOREST / WOODLAND @ DUSK" override block at end of `<style>`, added the `#pollen` canvas + a self-contained
particle `<script>`, dusk-gradient body bg (fixed-attachment). **VERIFIED (Chrome MCP @ :8095):** all data migrated
(96 models / 96 briefs / 149 glossary / 53 markets / 13 releases / 15 news), leaderboard order intact, 96 Current
cards, 4 chart SVGs, all 6 tabs render, **zero console errors, zero overflow**. Topo contour reads as a map without
fighting the data; natural lab tones stay distinguishable. Backup of pre-nature original: `index.html.bak-prenature`.
Matrix attempt still parked at `index.html.matrix-shelved`. **LOOP RUNNING** (self-paced ~60s perfection passes).
Pass-1 screenshotted: Home + Charts.
**Pass 2 (verified):** eyeballed News + More on forest (both read well). Two real fixes: (a) **retinted `NEWS_SRC_COLOR`**
(JS source-pill map) from the old vivid/neon palette to forest-muted tones — killed the literal old-accent-blue IEEE
`#5b8cff` and the neon-mint Bloomberg/Nature `#34d399`, kept all distinguishable. (b) **Separated the 3 close blue lab
tones** — Google `#5b86c4→#5b9ccb` (cyan-sky), Meta `#5560ac→#4f5aa8` (deeper royal), DeepSeek `#8071c9→#9072cc`
(violet); RGB distance Google↔Meta 76, Meta↔DeepSeek 78 (both up from mid-50s). Zero console errors, data intact.
**Pass 3 (verified) — CONVERGED, loop STOPPED:** eyeballed Predict on forest. Fixes: (a) **status pills `.h-soon`**
(EXPECTED/CONFIRMED) off old-blue → forest green `rgba(98,193,119,.14)/#9fd9ad`; (b) **`platColor()`** market-platform
colors retinted off old neon/blue → forest-muted (Polymarket sky, Metaculus moss-teal, Manifold honey, Kalshi
seafoam, Epoch plum, METR copper, AI-Index lavender) keeping them distinguishable; (c) **`.sq.secondary`** source
badge → forest; (d) **pollen density** bumped (divisor 26000→15000, cap 64→90) so it actually reads on a phone
viewport (~12 dots → ~22). **FINAL VERIFICATION (Chrome MCP @ :8095):** all data present (96 models/96 briefs/149
glossary/53 markets/48 historics/13 releases/15 news/14 prices/dataVersion 3), all 6 tabs render (96 Current cards,
4 chart SVGs, 12+47 Predict, 15 News, 149+18 More), leaderboard order intact, **zero overflow, zero console errors.**
Deliberately SKIPPED topographic axis lines on the charts (would risk legibility — "legibility wins" per his brief).
**The forest theme is done and ready for Christian's review.** No further passes (would be cosmetic bikeshedding).
Backups: pre-nature original `index.html.bak-prenature`; shelved Matrix `index.html.matrix-shelved`.

### ↩ REVERTED (Jun 19, session 11) — Matrix/retro UI overhaul built + verified, then rolled back at his call
**OUTCOME: reverted. The live app is the ORIGINAL blue theme.** Christian: "revert to the original, we went too
hard and ambitious here" (mid-Pass-2). Original restored from `index.html.bak-prematrix` (now removed; original IS
`index.html`); the full Matrix build is parked at **`index.html.matrix-shelved`** for reference if he ever wants a
*lighter* take. Verified post-revert: accent `#5b8cff`, system sans, no rain canvas, 96 models/96 cards, leaderboard
Opus 4.8 56, zero console errors. Lesson for a future restyle: he wanted the theme *dialed back*, not maxed — the
all-mono + full-canvas-rain + glow + glitch + scramble combo was too much at once. Next attempt: subtler, fewer
effects, keep legibility-first. The details below are what the shelved version contains (NOT live):
Christian ordered a full restyle to **Techy + Black + Matrix + Retro**, design locked via a 10-question
AskUserQuestion questionnaire. Locked choices (also in memory `project_robots_matrix_ui.md`): faint ambient
**canvas digital-rain** (real, not CSS) · green chrome `#00ff41` on `#03070b` but **per-lab data colors kept
exactly** · **all monospace** · **phosphor glow only** (no scanlines/flicker) · fast glitch-in (<0.6s, no boot
screen) · **terminal-window cards** (squared 4px corners, glowing borders, `›`/`▌`/`>` prompt prefixes) ·
**wireframe-glow charts** (drop-shadow traces, labels/dots/lab-colors kept) · restyled bottom 6-tab nav (green
glow + top rail + blinking `_`) · **scramble-decode on key numbers** · strong-but-legible (data wins).
**Implementation = safe CSS reskin, ZERO data-wiring edits:** (a) rewrote `:root` chrome vars (kept all lab
hexes), (b) appended one "MATRIX / RETRO-TERMINAL OVERHAUL" override block at end of `<style>` (later rules
win; base rules untouched), (c) added `<canvas id="rain">` + a self-contained effects `<script>` after the main
script (rain = FPS-capped 20, opacity .55, paused when hidden, `prefers-reduced-motion`-aware; scramble only
touches a leaf text node so it never destroys child DOM). **VERIFIED (Chrome MCP @ :8095):** all data migrated
— 96 models / 96 briefs / 149 glossary / 53 markets / 48 historics / 15 news / 13 releases / 14 prices,
dataVersion 3, leaderboard order intact (Opus 4.8 56→GPT-5.5 55→4.7 54→GPT-5.4 51→Gemini 3.1 Pro 46); 96 Current
cards, 4 chart SVGs, all 6 tabs render; **zero console errors, zero mobile overflow**. Pre-overhaul backup:
`index.html.bak-prematrix`. **LOOP RUNNING** (self-paced ~60s perfection passes, NOT a blind cron — a 60s cron
would fire mid-edit and clobber index.html). Pass-1 screenshotted: Home, Charts, model Details modal. Remaining
loop passes: visually verify Predict/News/More tabs, contrast/legibility audit, card-chrome refinement,
adversarial data-placement audit.

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

### ✓ DONE (Jun 19, this session) — prediction-markets + historics integrated, verified at 375px
New data file **`data/forecasts.json`** (built by **`scripts/build_forecasts.py`** from
`scripts/markets-historics-raw.json` — re-run after any fresh research pass) bundles
`markets` (53), `historics` (53), `trajForecasts` (16), `methodology`. `index.html` loads it
in `boot()` via a **guarded** fetch into globals `MARKETS / HISTORICS / TRAJFC / FCMETHOD`
(a missing file can't break the 4 core data files). dataVersion bumped **1→2**.
1. **Prediction-markets section filled** — `marketsBody()` renders all 53, grouped into 4
   collapsible sub-accordions by category (ranking→"Who leads the field", release→"What ships,
   and when", benchmark→"Benchmark milestones", capability→"Big-picture & AGI") + a "How these
   forecasts are built" methodology footnote. Rows are **clickable** (open the market `url` via
   a `.mktrow.lnk[data-href]` handler), platform-color-coded (`platColor`/`shortPlat`), forecast
   full-width below the question. GOTCHA baked in: forecasts contain raw `<1%`/`≥` → ALL market
   text runs through the new **`he()` HTML-escaper** (line ~279). Don't remove it or `<1%`
   silently eats the row.
2. **Forecasts re-anchored** — `leadingTrajectory()` now overrides its extrapolated `pred` with
   the matching `TRAJFC` `{lab,benchmark}` market forecast (point + low/high band + expectedDate;
   `canonLab` matches lab names). `multiLineChart()` draws the **uncertainty cone** (shaded
   triangle widening from the last real point out to the low/high band) + a whisker line; the
   pred-dot click detail now shows the band, expected date, basis, and source.
3. **Lines extended back** — historics merged into each shown lab's series, BUT gated by
   **`historicsUsable(cat)`**. REBASE CAVEAT: the **AA Index was re-versioned in 2026** (pre-rebase
   frontier ~70 in 2025 → post-rebase high-50s/low-60s in 2026; a uniform down-step across every
   lab at the 2025→2026 seam). So AA historics sit ABOVE live values and are **auto-dropped** (the
   guard keeps historics only if max-historic ≤ live-frontier×1.03), with an on-chart amber rebase
   note. **Only SWE-bench (stable scale) extends back to ~2024.** Estimate dots render hollow.
   Self-correcting: if a future sweep puts AA historics on the live scale, they pass automatically.
   Deliberately did NOT hand-patch AA scores (per the don't-hand-patch-scores memory).
The raw file `scripts/markets-historics-raw.json` is kept as the source-of-record / regen seed.

### ✓ DONE (Jun 19, session 2) — data-ify editorial + rename + News section
1. **Editorial sets data-ified** → new **`data/editorial.json`** (`prices`, `leaderboard{source,rows}`,
   `upcoming`, `killed`, `sources`), loaded in `boot()` into `let PRICES/LB/LBMETA/UPCOMING/KILLED/SOURCES`
   (were `const` arrays in index.html). The updater can now maintain these. Leaderboard source label is
   driven by `LBMETA.source`. **Removed dead code**: `WEIGHTS` array + `weightsChart()` + `HH_AA`/`HH_SWE`
   (the dropped weights chart + old head-to-head — defined, never called).
2. **"Now" tab renamed → "Current"** (nav label + Home explore link only; internal ids stay `now`/`v-now`/
   `nowFilter`/`renderNow` to avoid churn).
3. **News section** = new 5th tab (Home/Current/Charts/**News**/More) → **`data/news.json`** (`{updated,note,items[]}`,
   each `{title,source,url,date,topic,blurb}`). `renderNews()` + `newsRow()`; topic-filter chips (reuses
   `.fchip`, handled via `data-news-topic`); rows clickable (the market link handler was generalized to
   `.lnk[data-href]`); source pills color-coded via `NEWS_SRC_COLOR`. 15 curated items, **all links verified**
   (6 CNBC opened + confirmed, 2 AP wire, MIT Tech Review/IEEE agent-fetched, Nature resolves, Bloomberg
   fact corroborated). ⚠ SOURCING CAVEAT: **WSJ/Reuters/FT/Bloomberg are hard-blocked** from BOTH the research
   agent's WebSearch AND Chrome MCP (safety restrictions) — so despite his explicit WSJ ask, no WSJ link
   exists; the verified set skews CNBC/AP/MITTR. To add WSJ he'd open it himself, or use a tool with paywall
   access. `news.json.note` records this.
- All boot fetches (forecasts/editorial/news) are **guarded** (Promise.all with per-fetch `.catch(()=>({}))`),
  so a missing aux file never breaks the core app. Zero console errors; verified at 375px.
- **The twice-daily updater now maintains `news.json` + `editorial.json` too** (done this session):
  `scripts/research-prompt.md` gained a **News** section (find 6–12 recent reputable AI reads; allowed
  sources CNBC/MIT-Tech-Review/Nature/IEEE/Axios/Verge/Ars/Science/Economist; explicitly forbidden to emit
  WSJ/Reuters/AP/Bloomberg/FT since its WebSearch can't reach them; real URLs only) + an **editorial** section
  (prices/leaderboard/upcoming). `scripts/merge.py` gained: **news** = rolling refresh (validate → dedupe by
  url → newest-first → cap `NEWS_MAX=24`), with an **integrity guard `news_ok()`** that drops any item whose
  url domain ≠ its `source` (via `NEWS_DOMAINS`) — kills the WebSearch-hallucinated-URL failure mode; and
  **editorial** = prices merge-by-key (never drop) + replace-if-provided for leaderboard/upcoming/killed/sources.
  Delta schema = `{...models..., "news":[...], "editorial":{prices,leaderboard,upcoming,killed}}`. TESTED: a
  sample delta added 1 valid news item, REJECTED a fabricated `example.com` link, deduped a repeat, merged the
  price — then restored. The updater (launchd) is still **not installed** (P2).

### ✓ DONE (Jun 19, session 3) — Predict tab rebuilt + Definitions/acronym search
Two asks, both shipped & verified at 375px. Data was generated by an **ultracode Workflow** (20 agents:
8 glossary categories fanned out → 8 skeptics refuted defs → release-radar research → 3 adversarial
date/prob refuters → JS assemble). Result: `data/glossary.json` (**149 terms**, 8 categories, 41 acronyms;
0 dropped, 22 defs corrected by skeptics) + `data/releases.json` (**13 release items**, all survived 3-lens
adversarial verify). Both loaded guarded in `boot()` into `GLOSSARY` / `RELEASES` / `RELMETA`.
1. **Definitions & acronyms search** = top accordion of **More**. `#glossq` input → live-filters `#glossres`
   (a `document` `input` listener updates ONLY the results div, so focus is preserved). `glossMatch()` searches
   term + acronym + def + `aka[]` (so "rlhf" finds "Reinforcement Learning from Human Feedback"). Term cards =
   name + acronym badge + category tag + def. Post-merge dedup collapsed 2 same-acronym dupes (HLE, RLHF).
2. **Predict** = NEW 6th tab (Home/Current/Charts/**Predict**/News/More — nav font tightened to 8.8px to fit 6).
   Markets + On-the-horizon MOVED out of Charts into Predict (Charts now = trajectories/cadence/head-to-head
   only; its caption + a pointer line updated). Predict has: **(a) Frontier release radar** — a "next frontier
   drop" hero (soonest frontier item, prob≥25), an **SVG timeline strip** (now-marker + quarter gridlines +
   lab-colored dots, frontier dots larger/ringed, tap → `#reldetail`), and a date-sorted list (lab dot, FRONTIER
   tag, status pill, expected window, **probability bar**, basis). **(b) Prediction markets** — now sorted by
   resolveDate within each category group + a `firstPct()`-parsed **probability bar** per row. **(c) On the horizon**.
   Helpers: `firstPct`, `probBar`, `radarStrip`, `relRow`, `nextFrontier`, `renderPredict` (+ `RELSORTED` global,
   `circle[data-rel]`/`.relrow` click handler). CSS for `.phero* .relrow .pbar .mkt-bar .gsearch .gterm` etc.
- **Updater maintains both new datasets**: `merge.py` += `releases` (replace snapshot) + `glossary` (additive
  by term, dedupe, never drop); `research-prompt.md` += a release-radar section (real markets only, drop shipped
  models) + a glossary-extension section (add a few missing terms/run). Delta schema += `releases`/`glossary`.
  TESTED (replaced releases, added a term, skipped an MMLU dupe, restored).
- Radar data quality note: probs are window-matched for GPT-5.6 (97%), Gemini 3.5 Pro (97%), GPT-6 (82% by Dec);
  the rumored ones are `prob:-1` (no market) and a couple (Grok 5 1%, Gemini 4.0 2%) carry a near-date "won't
  ship by Jun 30" reading that the per-item `basis` line explains. Hero = Gemini 3.5 Pro.

### ✓ DONE (Jun 19, session 10) — AA re-baselined onto Artificial Analysis's live (v4.1) scale
The back-fill exposed that the app's 2026 AA values were ~10% higher than AA-live (app Opus 4.8 = 61.4; AA-live
≈ 56), so we put EVERYTHING on one scale. Three research passes: back-fill of 22 pre-2026 flagships (`wr4b72r3p`
→ `scripts/aa-backfill-raw.json`, field `aa_v41`), re-fetch of 11/14 live models (`w82uet82a`), and a gap-fill
agent for the 3 it missed (Gemini 3.1 Pro=46, Grok 4.3=44, Muse Spark=43). Integration (a Python pass with
/tmp backups): **(a)** replaced the 14 live models' AA in `models.json` with AA-live values (Opus 4.8 61.4→56,
GPT-5.4 57→51, GPT-5.5 57→55, Gemini 3.1 Pro 57→46, Grok 4.3 53→44, …); **(b)** replaced `forecasts.json`
`historics` aa with the 22 back-fill points (AA-live, estimate:true, real labs, date YYYY-MM) — kept the 26 swe;
**(c)** bumped `meta.dataVersion`→3. The AA rebase note auto-hides now (`historicsUsable('aa')===true`, since
back-fill max 51 ≤ live 56). **Verified app-wide:** leaderboard re-ordered (Opus 4.8 56 → GPT-5.5 55 → Opus 4.7
54 → GPT-5.4 51 → Gemini 3.1 Pro 46), hero "leader at 56", best-model Top-overall 56, head-to-head AA re-ranked,
and the AA chart now spans Q1'25→Q2'26 (22 dots, hollow estimates for the back-fill). Zero console errors.
**Also fixed a real caching bug:** boot's `fetch` was serving STALE data from the browser HTTP cache (the
re-baseline didn't show until bypassed). boot now uses `fetch(url,{cache:'no-store'})` via a `J()` helper for ALL
data files — guarantees fresh data on every load/update (the SW still provides offline fallback). This would have
bitten the twice-daily updates on the live site too.

### ✓ DONE (Jun 19, session 10b) — tie card: expandable
He asked for a small expand button on the simplified tie card. `bestCard()` ties now render as a compact grid box
("10-way tie ›") that, on tap (`[data-tieexpand]` → toggles `.exp`), expands to **full-width** revealing all tied
models as `.tiechip`s; tap again to collapse. Re-added `.tiecard`/`.tiechev`/`.tielist`/`.tiechip` CSS.

### ✓ DONE (Jun 19, session 10) — "Best model for…" tie card simplified to grid size
He asked to simplify the 10-way-context-tie card to match the other boxes. `bestCard()` now renders a tie as a
normal grid box showing the count as the name ("10-way tie") + the value ("1M ctx") — no more full-width span or
chip list. Removed the unused `.bestcard.tie`/`.tielist`/`.tiechip` CSS. Verified at 375px.

### ✓ DONE (Jun 19, session 9) — Home refresh + tie-aware "Best model for…"
(1) **Explore links rebuilt** to match the 6-tab app — Current/Charts/**Predict**/**News**/More with accurate
descriptions (removed stale "forecasts in Charts" + "leaderboard/fact-checks in More"; added the Predict & News
cards). (2) **"Best model for…" now shows TIES**: `pickBest()` returns `{models:[…], disp}` (all models at the
top value, recent-first) instead of one winner; `bestCard()` renders a single-winner card OR, for a tie, a
**full-width card** (`grid-column:1/-1`) listing every tied model as lab-colored `.tiechip`s with "N-way tie".
Confirmed: frontier **Longest context = 10-way tie at 1M** (the user flagged this). CSS: `.bestcard.tie`,
`.tielist`, `.tiechip`. Verified at 375px, zero console errors.
⏳ STILL RUNNING (background): the **AA v4 back-fill workflow** (`wr4b72r3p`) researching pre-2026 flagships'
current-scale AA values — integrate its verified points into the AA historics when it completes.

### ✓ DONE (Jun 19, session 8b) — Frontier-by-company: show ties (GPT-5.5 was hidden)
`leadingTrajectory()`'s monotonic filter used **strictly-greater** (`> best+0.001`), which silently DROPPED any
model that TIED the running best — that's why **GPT-5.5 (AA 57) was invisible** (it tied GPT-5.4's 57). Changed to
**greater-or-equal** (`>= best-0.001`, only bump `best` on strict increase): tied flagships now show, while
lower-tier follow-ons (Sonnet/Haiku/Flash released after a higher Opus) are still dropped so the line never fakes
a regression (verified: anyDips=false; SWE Anthropic stays clean; AA dots ~doubled to 10). Caption updated.
KNOWN LIMIT he raised ("more historical data"): AA time-depth is walled by the **2026 AA rebase** (pre-2026 AA is
on an incomparable scale, dropped by `historicsUsable`), so AA only spans 2026; SWE could extend if the 18-month
`WINDOW_MONTHS` is widened. The real fix for AA depth = re-research pre-2026 flagships' AA onto the current v4
scale (a data task, not a hand-patch). Offered these as a follow-up choice.

### ✓ DONE (Jun 19, session 8) — Frontier-by-company: measured-only, last 18 months
Charts → "Frontier by company": (1) the **prediction overlay is gone** — `leadingTrajectory()` no longer
computes a `pred`; `multiLineChart()` dropped the dashed connector, faded forecast dot, uncertainty cone +
whisker, and the cone key; the `circle[data-pred]` click handler is removed. `TRAJFC` is now unused by the
charts (still loaded, harmless). (2) **Windowed to the last 18 months** — `windowCut()` (= now − 18mo,
~`2024.97`); both the live points and the SWE back-estimates are filtered to `tval >= cut`. SWE spans
~Q1'25→Q2'26 (full growth curve); AA only has current-scale (2026) data so it covers that era (rebase note
updated). X-axis switched from year ticks to **quarter ticks** (Q1 '25 … Q2 '26). Captions updated; the
metric/Frontier-Open switches still re-render in place (session-7 fix). Verified at 375px, zero console errors.
Also fixed earlier this session: the Charts AA/SWE/GPQA/AIME + Frontier/Open switches now re-render only their
own chart container (`#hh-wrap`/`#traj-aa-wrap`/`#traj-swe-wrap`) instead of the whole tab, so accordions stay
open and scroll position holds.

### ✓ DONE (Jun 19, session 7) — pruned tabs + a dated per-sweep Sources log
Per his feedback: (1) **Predict → "On the horizon" accordion removed** (its info lives in the release radar
now; `UPCOMING`/editorial.upcoming stays in data, just unrendered). (2) **More → "Leaderboard" and "Didn't
make the cut" removed** (redundant); the `LB`/`KILLED` globals stay loaded but unused. (3) **More → "How it
works" removed.** So **More now = Definitions & acronyms + Sources only.** (4) **Sources rebuilt as a dated,
per-sweep hierarchy** → new `data/sources.json` `{sweeps:[{date,routine:"AM"|"PM"|"build",sources:[{u,url,q}]}]}`,
loaded into `SWEEPS`. `renderSources()` groups newest-first **Week → Day → AM/PM sweep → clickable source links**
(nested `.subacc`; latest of each open; `.srcrow` reuses the `.lnk[data-href]` handler). Seeded with one
"6/19 build" entry from the old backbone sources (18). **The updater logs each run's sources**: `research-prompt.md`
now asks for `sweepSources` (every URL consulted), and `merge.py` appends them under today's date + AM/PM
(hour<12 ET = AM) — same routine re-run overwrites. Also trimmed the research prompt's editorial section to
prices only (leaderboard/upcoming UIs are gone). Delta schema += `sweepSources`. Tested (PM entry appended
alongside the build, restored). Verified at 375px, zero console errors.

### ✓ DONE (Jun 19, session 6) — Prediction markets → a cohesive story
Predict's Prediction-markets section no longer dumps all 53 rows. It now **leads with a 4-paragraph narrative**
(`marketsStory` in `data/forecasts.json` — themed: the race / what ships next / benchmarks saturating / the long
game, each with a bold accent lead-in, grounded in the exact open-market numbers). The raw markets moved behind a
collapsed **"Browse the N open markets"** sub-accordion (category headers, not nested accordions). **Resolved
markets are excluded everywhere** via `marketIsOpen(mk)` — drops any with `/resolved/i` in forecast/question OR a
leading `YYYY-MM-DD` resolveDate before today (6 of 53 dropped: Jan LMArena, two SWE-bench, ARC-AGI-April,
FrontierMath-Jun30, GPQA-leaderboard). New global `FCSTORY`; CSS `.mktstory`/`.mktgrp-h`. The story is static data
for now — regenerate it whenever the markets are re-researched (it's NOT in the twice-daily merge loop, since
markets live in forecasts.json built by `build_forecasts.py`, not merge.py). Verified at 375px, zero console errors.

### ✓ DONE (Jun 19, session 5) — Predict radar simplified
Per his feedback: (1) the SVG timeline strip (`radarStrip`) is REMOVED, along with `nowFrac` and the inline
`#reldetail` tap-target. (2) Each release row now has a **ⓘ Details button** → opens the shared bottom-sheet
modal via `openReleaseModal(i)` / `releaseInfo(r)` (header + prob bar + basis + source); the basis is no longer
inline on the row. (3) The list is ordered soonest-first by `expectedDate` (was already, now it's the only
ordering cue). (4) The "Next frontier drop" hero stays, and the list now EXCLUDES it (`listItems =
RELSORTED.filter(r=>r!==nextFrontier())`). Handler: `[data-rel]`/`#reldetail` replaced by `[data-rel-info]`.
Dead `.reldet*` CSS left in place (harmless). Verified at 375px, zero console errors.

### ✓ DONE (Jun 19, session 4) — head-to-head bar graph, model info popups, filter cleanup
1. **Charts → Head-to-head is a horizontal bar graph again** (was a table). `headToHead()` now renders an SVG
   horizontal-bar chart of the top-8 live models on ONE benchmark, lab-colored, value-labelled, with a
   **metric switcher** (`segCtl('hh',…)` → AA/SWE/GPQA/AIME; `hhMetric` global + `which==='hh'` seg handler).
2. **Current → each card's "more" expander replaced by an ⓘ Details button → bottom-sheet popup.** The inline
   `notable`/`.more` clip is gone; cards now end in `.infobtn[data-info=name]`. A `#modal`/`#modalcard` element
   (added after `</main>`) opens via `openModal(name)` (close: ✕, backdrop, or Esc). `modelInfo(m)` shows
   name + lab/date/badges + a specs line + a benchmark line + a **cohesive 2-paragraph plain-English brief**
   (what it is / new / strong / weak). Brief text = `BRIEFS[name]` from new **`data/briefs.json`** (a
   `{name: "para1\n\npara2"}` map for **all 96 models**), with `synthBrief(m)` as a data-built fallback.
   Briefs generated by **two ultracode passes**: a 20-agent workflow (10 slice-authors → 10 fact-check
   verifiers, 1 fix) covered 78; a gap-fill agent did the 18 the authors skipped → 96/96, names all match.
3. **Current → Lab-filter chips and "★ Landmarks only" removed.** `renderNow()` keeps only the All/Frontier/Open
   `segCtl`. Deleted `nowFilter`/`nowLandmarks` globals + their `.fchip` handler branches + the cnt/labs logic;
   the only `.fchip` left is the News topic filter. Dead `.more` click handler removed.
- **Updater maintains briefs too**: `merge.py` += `briefs` (merge by model name, add/replace); `research-prompt.md`
  asks for a `briefs` entry for each `newModels` model. Delta schema += `briefs`. Tested (replace + add, restored).
- Nav is still 6 tabs (8.8px labels). All verified at 375px, zero console errors.

**Next likely:** P2 deploy (pending his go) — push, enable Pages, install the launchd plist, confirm `claude -p`
writes a delta headlessly (one pass now covers models + news + editorial + releases + glossary + briefs).

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
