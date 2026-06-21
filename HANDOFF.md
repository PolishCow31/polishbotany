# AI Tracker — Handoff

Phone-first, self-updating AI history + trends + forecasts app for Christian & dad.
Resume command: `/ai`. Local: `localhost:8095`. Full design: [ARCHITECTURE.md](ARCHITECTURE.md).

## State — Jun 20 2026

### ✓ DONE (Jun 20, session 28) — open-source chart back-fill (verified) + Charts cleanups + glossary/header fixes (LIVE-file, theme NOT deployed)
All on the live working `index.html` (forest theme, lighter palette + Fraunces/Spline fonts from session 27's post-revert tweaks). **Theme still NOT git-pushed; data back-fill WILL auto-push next cron (`git add data/`).**
- **OPEN-SOURCE trajectory back-fill — the big one.** The Charts "Open source" AA + SWE lines were 1-2 lonely dots; now
  **5 climbing lines each** (DeepSeek, Alibaba, Zhipu, Moonshot, NVIDIA), hollow back-estimates → solid live endpoints, just
  like the Frontier chart. Done as a **verified Workflow** (`wf_25d0bc1a-a9a`, 15 agents: 7 lab researchers → 7 adversarial
  verifiers → 1 cross-lab reconcile). **CRUX (don't forget): the app's AA-Index is a COMPRESSED/re-baselined scale, NOT real
  Artificial Analysis** — 2025 top open models sit ~10-22 here vs ~45-65 real; the workflow calibrated every AA value to the
  app's anchors (frontier ceiling-over-time + existing open historics + live endpoints), NOT real-world numbers. SWE used ~real
  SWE-bench Verified. Integrated deterministically (`forecasts.json.bak-pre-openbackfill` + `models.json.bak-…` backups):
  **+30 historics** (now 78; `estimate:true`, each with a `basis`), **bumped the flagged-incoherent existing Qwen3-235B AA
  13→17**, and **filled 6 missing LIVE endpoint benchmarks** (DeepSeek-V4-Pro SWE=80; Kimi K2.7 AA=49/SWE=79; GLM-5.2
  AA=51/SWE=79; Nemotron 3 Ultra SWE=73) so each lab's line reaches "now" (a lab's historics only render if it has a LIVE point
  in that benchmark+view — that's why the fills were needed). Deterministic guard passed: every AA ≤56 & under the
  contemporaneous frontier ceiling, every SWE ≤90; `historicsUsable('aa'/'swe')` both still TRUE. `merge.py` never touches
  `historics`, so the cron can't clobber the back-fill. Verified both charts @375px render 5 climbing lines.
- **Charts cleanups:** removed the **"Tap any dot to see the model."** `.tdhint` banner under every chart (dots still tappable)
  + the **"…live in the Predict tab"** note at the bottom of the Charts tab.
- **More-glossary readability fix:** the search results render BARE on the light sage bg, so the light ink washed out →
  scoped deep-forest text on `#glossres` (`.gt-term/.gt-def/.gt-cat/.accsub`). Same bare-on-sage class of bug the eyebrows/
  captions were already patched for.
- **Header tagline:** masthead now = leaf + "Botany" + *"The continuous growth and roots of AI"*. Fixing it surfaced a latent
  bug — `<header class="bar">` was inheriting the bar-CHART `.bar` grid (`grid-template-columns:96px 1fr 40px`, line ~234) →
  contents crammed to 96px; pinned `header.bar{display:block}`.
- **gitignore:** added `data/*.bak-*` + `index.mk*.html` so the cron's `git add data/` doesn't push the local backups.
- **Release-radar staleness fix (`scripts/research-prompt.md`, local-only — not deployed, cron reads it locally):** he
  noticed "radar Jun 19" on Jun 20 and asked why predictions weren't updating. Root cause: the markets sub-tab DOES refresh
  every sweep (by URL), but the **release-radar** prompt said "if the picture changed, output the list" → the agent could
  skip re-verifying it, so `releases.json` (+ its `updated` date) froze. Per his call (he doesn't care about the date, only
  that the INFO refreshes), changed the radar instruction to **re-verify EVERY sweep** — reuse the live market odds it's
  already pulling to re-check each item's window/prob, promote shipped models out, add new ones, and ALWAYS re-emit the full
  list (carry-forward all still-pending, drop only shipped/cancelled). Takes effect next 6am sweep; radar data pushes via `data/`.

### ↩ (Jun 20, session 27) — "GLASSHOUSE, LIGHTS ON" UI overhaul (Mk.1.1) — built + verified, then REVERTED to Mk.1 at his call
Christian asked for a full UI overhaul via the **frontend-design plugin**, with backups: current = **Mk.1**, new = **Mk.1.1**.
- **Backups (both on disk, untracked):** `index.mk1.html` (the forest/sage-dusk "before", 1169 lines) + `index.mk1.1.html`
  (the glasshouse "after" = live `index.html`, 1256 lines). Revert to Mk.1 = `cp index.mk1.html index.html`.
- **How the direction was chosen:** a Workflow **design panel** (6 designers → 6 critics, 12 agents) drafted distinct
  directions; surfaced 3 (two dark, one light herbarium) to him via AskUserQuestion. He picked **"Glasshouse at night."**
  The light-herbarium variants were honestly flagged for a **dad-legibility risk** (serif body on low-contrast linen at 375px).
- **Theme = a Victorian conservatory after midnight** (resolves the old dark-cards-floating-on-light-sage tension by going
  FULLY dark). Done as a **safe reskin: `:root` tokens + a web-font `<link>` + an appended "GLASSHOUSE" override block at the
  END of `<style>` + a few small surgical JS edits. ZERO data-wiring touched** (the method that's survived every prior reskin).
  - **Type system (the biggest win):** added Google Fonts **Fraunces** (display/plaque moments — H1, hero specimen name,
    modal title), **Newsreader** (reading prose + specimen names), **Spline Sans Mono** (ALL data/labels/scores — replaces SF
    Mono). System sans kept only for tiny functional UI chrome (nav/chips/seg/file-tabs). `--display`/`--body`/`--mono` vars.
  - **Palette:** green-black `#0A1410` base, grow-light lime `#7FE3A1` (accent, used as LIGHT not fill), aged-brass `#C9A56A`
    (framing/eyebrows/#1-rank), orchid `#C58BD6` (Predict/forecast "exotic-specimen wing" — EXPECTED/PREVIEW pills),
    condensation-ink text. Lab colors UNCHANGED (charts need them distinguishable).
  - **Panes:** every card is a backlit misted-glass sheet (brass hairline top-rail via inset box-shadow; lime inner-glow only
    on live/featured: `.lbrow.gold`, `.phero`, `.hero.pulse`). Brass eyebrows are color+tracking only — **NO hairline rules**
    (deliberately honored his same-day "lines blocking the page" ask; overrode the panel's rule suggestion).
  - **Hero-as-thesis:** small `renderHome` edit adds an "in bloom" specimen plaque above the Pulse — current leader's name in
    Fraunces + lab in a brass tag + AA score glowing lime (reads the already-computed `top`; guarded). Fox stays the keeper on
    the rail (its `.fox-shadow` recolored black→warm grow-light pool). Pollen retired to a few faint lime/brass nocturnal motes.
  - **SIGNATURE = the misted glass is REAL:** nano-banana asset `img/glass-night.jpeg` (dark frosted greenhouse glass +
    condensation + glazing-bars, 9:16) is the fixed `#forest` bg under a dark scrim — the whole app reads as lit through
    conservatory glass (the spec's anti-"flat-void" move; [[feedback_realistic_visuals]] real-asset not CSS-fake). **DROPPED**
    the panel's "fox wipes the fog" motion — the critic proved it's built on a false premise about the fox engine (fox is
    `position:absolute` on the hero's top edge at z-16, not behind glass) → it'd be a new JS feature fighting the engine.
  - Leaf logo recolored (lime leaf, brass midrib, brass frame) + favicon + theme-color `#0A1410`.
- **VERIFIED at 375px (Chrome preview @ :8095):** all 6 tabs render clean (Home hero+leaderboard, Current rows w/ orchid
  PREVIEW, Charts w/ Spline-mono axes, Predict orchid wing, News editorial headlines, More glass breathes), **zero console
  errors**, data intact (98 models). Fox overlap on non-Home views in screenshots = the known headless rAF-pause gotcha, not a
  bug (it's Home-only on a real device).
- **REVERTED — he reviewed Mk.1.1 in the preview and chose Mk.1.** `cp index.mk1.html index.html` done → the live working
  file AND the live site are both back to **Mk.1 / forest-sage** (1169 lines, byte-identical). Never deployed. Mk.1.1 is fully
  **PARKED** at `index.mk1.1.html` + its asset `img/glass-night.jpeg` if he revisits or wants to graft pieces. **The strongest
  standalone piece worth re-offering on the forest theme = the real type system** (Fraunces display / Newsreader reading /
  Spline Sans Mono data) — it was the biggest genuine upgrade and is theme-independent. Untracked scratch: `index.mk1.html`,
  `index.mk1.1.html`, `img/glass-night.jpeg` (+ a stray `img/bgtex-c.jpeg` from before). None committed.
- **Plugins:** earlier this session, scoped 3 plugins for Botany via `/plug` — `typescript-lsp` + `commit-commands` (project),
  `context7` (user/everywhere); installed the `typescript-language-server` binary. `aitracker` launch.json switched to the
  real `http.server` on 8095 + `autoPort:false` so `preview_start` owns the port (foreign detached server collides otherwise).
- **POST-REVERT live tweaks to the FOREST theme (his asks, on the live working file):** (a) added a **header tagline** — masthead is
  now leaf + "Botany" + *"The continuous growth and roots of AI"* (one line). Fixing it surfaced a real latent bug: `<header class="bar">`
  was silently inheriting the **bar-chart `.bar` grid** (line ~234, `grid-template-columns:96px 1fr 40px`) → contents crammed into 96px;
  pinned `header.bar{display:block}`. (b) **Lightened the harsh near-black greens** project-wide (`:root`): panel `#0f1d17`→`#213a2c`,
  bg→`#16261d`, lines lifted, ink slightly brighter — softer mid-forest cards on the sage bg. (c) **Brought the glasshouse type system
  to the forest theme** (the salvageable gem): Google Fonts **Fraunces** (wordmark + model/specimen names + section/card titles via an
  appended block), **Spline Sans** (`--sans`, body/UI), **Spline Sans Mono** (`--mono`, all data) — replaces system-sans + SF-Mono. Nav
  glass lightened to match. Verified Home+Current @375px, zero console errors. Still the forest theme (NOT glasshouse), NOT committed/deployed.

### ✓ LIVE-RUN STATUS (Jun 20) — both daily sweeps fired; PM was slow → watchdog added
The launchd updater is running in production. **6am sweep: clean, ~4 min** (commit `6bc9f19`, dataVersion 6).
**6pm sweep: SUCCEEDED but took ~89 min** (fired 18:12 on wake since the Mac slept through 18:00; pushed 19:41,
commit `1006d43`, dataVersion 7; added +2 models, +3 news, +2 terms, 2 briefs, refreshed markets). The 89-min
crawl = `claude -p` burned only 17s CPU across it, i.e. blocked on slow/Cloudflare-gated market fetches; root cause
was the over-heavy "research ~25-45 markets across 4 platforms EVERY run" ask. **Fixed (commit pushed):** (1)
`update.sh` now wraps `claude -p` in a **25-min perl-alarm watchdog** (macOS has no GNU `timeout`) so a hang can
never block future fires (launchd won't start a 2nd instance); a kill/non-zero exit no longer aborts — it still
merges any delta written. (2) `research-prompt.md` markets section dialed back to the **~10-15 highest-signal open
markets + any new ones, skip-slow-pages** (the set persists + refreshes by URL, so it stays thorough over time).
Next AM run should be back to a few minutes. Watch `scripts/update.log` if a run ever looks stuck again.

**Also Jun 20 (post-6pm-run):** (a) **Pulse AA-scale regression caught + fixed** — the 6pm sweep wrote the Pulse on
the OLD **v4.0** scale ("61.4 on the live v4.0 scale, ~4 points clear of Gemini 3.1 Pro") contradicting the
leaderboard right below it (app is **v4.1**, Opus 4.8=**56**, runner-up GPT-5.5=55). Corrected the live Pulse +
**hardened `research-prompt.md` to PIN v4.1** (use the models.json value, never re-research a v4.0 number). LESSON:
`merge.py` validates STRUCTURE (real URLs, valid dates) but NOT factual consistency, so a wrong-scale Pulse sailed
through — if it recurs, add a merge.py guard rejecting a v4.0-range AA number in the Pulse. (b) **UI: removed the
header bottom-border + the `.hsec::after` section-header hairlines** (all tabs) per his "lines blocking the page" ask
— part of the night's minimal/clean direction (see [[feedback_minimal_clean_ui]]).



### ✅ DONE (Jun 20, session 26c) — prediction markets folded into the twice-daily loop (gap closed)
The Predict tab's **prediction markets + narrative were NOT auto-updating** — `forecasts.json` was built
only by the manual `build_forecasts.py`; the cron never touched it, so the markets froze. Now in the loop:
- **`research-prompt.md`** gained a thorough **PREDICTION MARKETS** section (HIGH PRIORITY): research live
  odds across Polymarket/Metaculus/Kalshi/Manifold (+Epoch/METR) across the 4 categories
  `ranking|release|benchmark|capability`; `forecast` must LEAD with the headline `%` (the bar reads
  `firstPct`); real-URL-only + open-only; plus rewrite `marketsStory` (4 `{h,t}` paras) and optionally
  `trajForecasts` (chart cones). Schema gained `markets`/`marketsStory`/`trajForecasts`.
- **`merge.py`** section 6f writes `forecasts.json`: markets **refresh BY URL** (re-read = fresh odds), new
  ones append, **resolved/past pruned**; **integrity guard `mkt_ok`** rejects any url whose domain ≠ platform
  (`MKT_DOMAINS`, mirrors the news guard); bad categories coerced to `capability`; `marketsStory`(3–6 paras)
  + `trajForecasts`(≥4) replace-if-provided. **`historics` + `methodology` are NEVER touched** (those are the
  manual AA-rebaseline territory — see below).
- **VERIFIED both halves:** synthetic delta (add / refresh-by-url-no-dup / reject-bad-domain / prune-past /
  coerce-category, historics+methodology preserved) AND a real headless research test (**25 markets found,
  ALL 25 pass the guard**, all 4 categories; the agent even self-caught a Kalshi URL it had pattern-guessed).
  First LIVE markets refresh lands on the next scheduled run (6am/6pm) — wiring proven per-link, not yet run live.
- Runtime logs (`scripts/*.log`) now gitignored.
- **AA-rebaseline stays MANUAL by design** (the one remaining non-auto piece): when Artificial Analysis
  re-versions its Index scale (v4.1→v4.2…), every model's score shifts non-linearly and must be RE-FETCHED
  from AA (not computable from old values), the trigger isn't machine-announced, and it's a DESTRUCTIVE whole-
  dataset rewrite (opposite of the additive/idempotent merge) that would corrupt every chart+leaderboard at
  once if wrong. So it's human-launched (matches [[feedback_ai_auditor_architecture]]). To redo it: a research
  pass re-fetching live AA values + the `historicsUsable` guard, like the Jun 19 v4.0→v4.1 rebaseline.

### ◷ PARKED (Jun 20, session 26b) — fox WALK animation: waiting for Fable 5
The fox got a UI fix + a deep-dive that ended in a deliberate park:
- **Pinch-zoom fix (DONE, live):** fox was `position:fixed` → detached from the hero under
  pinch-zoom (drifted vertically). First "fixed" it by hiding it on zoom — Christian rejected
  ("don't make him vanish"). REAL FIX: `position:absolute` in body coord space (it's content,
  zooms WITH the hero); tracking math = body-relative doc coords (`r.left-b.left`, `r.top-b.top`).
- **Walk cycle (PARKED):** replaced the choppy 5 jiggly frames with an **8-frame cycle** (single
  sprite-sheet gen → consistent body, registered bottom-center, distance-locked stepping so feet
  plant). BUT the gait reads as a "paw dance," not walking. Ran `/deep-research` on quadruped gait
  (verified spec → `docs/fox-walk-gait-spec.md`) and proved the blocker is **nano-banana: it
  freezes the legs in ~ONE pose** (measured foot-spread identical ~87% across all 12 frames),
  ignores even a real Muybridge tiger-walk reference. So a correct gait needs a procedural leg-rig,
  a real artist sprite, or a stronger model. **Christian's call: wait for Fable 5** to come back
  (export-pulled) and let it draw the frames, rather than hand-rig now. See [[reference_nanobanana_no_gait]].
- **Cleaned up (DONE, live):** the new 8 frames had floating stray-pixel specks ("green blobs"
  on the sage bg) → fixed with a **largest-connected-component denoise** (fox intact). Current live
  fox = consistent-body, blob-free, ambling stiffly (gait parked). Controller's distance-stepping
  + the absolute-positioning zoom fix stay. **When Fable 5 returns:** regenerate the sheet, run it
  through key→denoise→register→order-per-spec (`docs/fox-walk-gait-spec.md`), feed the existing
  controller. Old 5 frames (`fox-walk-a..e`) were git-removed; new frames = `fox-walk-1..8.png`.

### ✅ DONE (Jun 20, session 26) — P2 COMPLETE: the twice-daily updater is INSTALLED + VALIDATED end-to-end · icons · nits
**THE BIG ONE — the auto-updater works and is live.** This was "the last step before done" for ~a dozen sessions.
Done autonomously while Christian was away ("take the reins, be appropriate"), pushing each change as applied.
- **Found + fixed the latent showstopper:** headless `claude -p` was silently QUEUING its Write/WebSearch tool calls
  pending an interactive permission that never comes in a launchd context → every sweep would have written nothing
  ("no delta written") and been a silent no-op. **Fix:** `update.sh` now calls
  `claude -p --dangerously-skip-permissions "$(cat scripts/research-prompt.md)"`. Safe by design — the AI only
  PROPOSES `data/_delta.json`; deterministic `merge.py` is the authority (the propose/dispose architecture).
- **launchd job installed + loaded:** `cp scripts/com.christian.ai-tracker.plist ~/Library/LaunchAgents/` +
  `launchctl load`. Fires **6am & 6pm ET** (RunAtLoad:false). Verified registered (`launchctl list` → com.christian.ai-tracker).
- **AUTH GOTCHA (recorded):** `claude`'s credentials live in the **login keychain** (`security` service
  `"Claude Code-credentials"`, acct `christian`), NOT a file. So `env -i` (synthetic minimal env) reports
  "Not logged in" — but a real **LaunchAgent runs in the GUI login session and DOES reach the keychain.** Don't be
  fooled by an `env -i` test; the real `launchctl kickstart` is the valid check.
- **VALIDATED END-TO-END THE REAL WAY:** `launchctl kickstart -k gui/$(id -u)/com.christian.ai-tracker` → job ran in
  its true launchd context, **authenticated**, did the research pass headless, merged, and **auto-pushed**
  (commit `9ff575e`), exit 0, empty `launchd.err.log`. So the cron genuinely works, not just "installed."
- **Two real research sweeps ran tonight** (one I supervised + pushed `data/` manually after verifying; one the cron
  fired). BOTH were appropriately conservative: 0 new models, and the agent **correctly rejected** false "new model"
  claims (MiniMax M2.7, Qwen3 Coder Next) AND old-v4.0-scale "61.4" aggregator-slop numbers as untrustworthy rather
  than fabricating. The one factual addition (Google/SpaceX/xAI **$920M/mo** compute deal) I independently
  corroborated (DCD/Engadget/CNBC/Techzine) before letting it land. Pulse rewritten each sweep; **dataVersion now 5**,
  3 sweeps logged. All pushed live.
- **NOTE — the cron auto-pushes with NO human review** (by design). Tonight's runs were clean + the agent's skepticism
  is good, but if Christian ever wants a review gate, change `update.sh` step 3 to open a PR / write to a branch
  instead of `git push` to main. Risk is bounded by merge.py's guards + it's his unlisted personal tracker (revertible).
- **✓ Home-screen icons** — `icons/icon-192.png` + `icon-512.png` (were referenced by manifest+apple-touch but the
  folder was EMPTY → broken default icon on Add-to-Home-Screen). Rendered the in-app SVG leaf logo to PNG via
  **headless Chrome** (`/Applications/Google Chrome.app/.../Google Chrome --headless --screenshot --window-size=NxN`),
  then PIL-downscaled the 512 to 192 (the direct 192 render came out blank — Chrome min-window quirk; downscale fixed
  it). Maskable, dark `#0b140f` bg, good safe-zone margin. Pushed.
- **✓ Nits** — Opus 4.8 `notable` prose 61.4→56 / 60.2→55 (matches the AA-v4.1 leaderboard); `git rm img/forest-bg.jpg`
  (dead since the sage-bg swap; recoverable from history). Pushed.
- **CLEANUP CANDIDATES (left untouched, noted):** (1) `editorial.leaderboard` + `editorial.upcoming` hold STALE
  old-scale data (Opus 4.8 at 61.3, a phantom "Claude Mythos Preview" 65.2) — but they're **UNRENDERED** (removed from
  the UI in session 7), so nothing leaks; worth a future scrub. (2) `merge.py` re-serializes `editorial.json`
  pretty-printed, so a 1-field pulse change shows as a ~197-line diff (formatting churn, harmless but noisy).
- Commits this session: `f01c98f` (Pulse Read-more) `5f91b3a` (sage bg) `6896c9d` (mobile fixes) `56c20c6`(toggle
  spacing) `…`(nits) `…`(icons) `…`(update.sh fix) + the two auto-update commits. All on `origin/main`.
**STATE: P0+P1+P2 all DONE. Botany is built, deployed, and self-updating.** Remaining = P3 polish only (in-app
search, model-detail pages, dad onboarding/share) + the two cleanup candidates above. Christian was reviewing UI
tweaks ("keep tweaking UI" was open-ended) — pick that back up on his return.

### ✓ DONE (Jun 19, session 25) — Home Pulse "Read more" clamp · forest bg → light-sage texture
Two asks, both built + verified at 375px (Chrome preview @ :8095), zero console errors, committed.
**(1) Pulse "Read more" clamp.** The Home Pulse paragraph now collapses to **~4 lines** (`max-height:calc(1.64em*4)`,
`overflow:hidden`) with the 4th line **fading into the card** (a `.pulse-txt.clamp::after` bottom gradient to
`var(--panel)`); a centered green **"Read more ▼"** disclosure (`.pulse-more`) expands it → "Read less" + caret
rotates 180° (`[aria-expanded]`). Delegated handler `[data-pulse-toggle]` (in the doc click block) toggles `.clamp`
so it survives `renderHome()` re-draws; resets collapsed each Home visit. **Overflow guard** in renderHome: if the
Pulse doesn't exceed 4 lines (`scrollHeight<=clientHeight+2`) the button is `hidden` and clamp removed — no dangling
"Read more" on a short Pulse. Commit `f01c98f`.
**(2) Background: forest photo → soft light-sage WATERCOLOR texture.** Per his ask ("lightly textured lighter green").
Generated via **nano-banana Flash, 1K, 9:16** → `img/bgtex-a.jpeg` (soft sage watercolor wash, even/airy, no focal
subject). `#forest` layer rewritten: dropped the dark scrim + `forest-bg.jpg`, now `url(img/bgtex-a.jpeg) center
top/cover fixed, #cfe3c2`. Cards/header/nav stay DARK (he only asked for the bg) → dark cards float on light sage,
reads clean. **Dependent legibility fixes (the bg flip would've washed these out):** recolored every bare-on-bg text
to deep forest-green via overrides appended at END of `<style>` (source-order win) — `.vh #27492f`, `.hsec #375a43`,
`.vsub #3c5a43`, `.gloss-hint/.empty #456a4d`; **darkened the pollen mote palette** (`COLORS` → muted sage/olive
`rgba(74,110,66)/(96,130,80)/(150,128,70)`) so the drifting motes read on a light bg; gave the **#1 gold leaderboard
row an opaque base** (`…,var(--bg2)` second layer) so no sage bleeds through its tint gradient. **Also removed the
green body side-borders** (`border-left/right:var(--line2)` — his "lime-green phone-size borders = visual noise").
Verified Home/Charts/More all legible. Commit `5f91b3a`. **Alternates kept on disk (untracked):** `img/bgtex-c.jpeg`
(a muted LINEN-weave texture — one-line swap if he prefers it) and `img/forest-bg.jpg` (instant revert to forest).
NOTE: neither alternate is committed; if he settles on sage, `git rm img/forest-bg.jpg` to clean up.
**(cont., commit `6896c9d`) — 4 mobile fixes:** (a) **file-tab strip drag** — `.ftabs` got `touch-action:pan-x` +
`overscroll-behavior-x:contain` (+ `user-select:none` on `.ftab`) so the horizontal tab scroller only pans
sideways instead of dragging vertically/all-over on touch (it still scrolls horizontally by design — News has 8
topic tabs). (b) **fox falls out of place on pinch-zoom** — FIRST tried hiding it on zoom (Christian rejected: "I'd
rather he doesn't glitch out vertically" — vanishing is a cop-out). REAL FIX (session 26): the fox was `position:fixed`
(pinned to the layout viewport) so under pinch it detached from the hero while content zoomed. Changed to
**`position:absolute`** in body's coord space → it's ordinary CONTENT, so it magnifies/pans in lockstep with the hero;
tracking math switched to body-relative document coords (`r.left-b.left`, `r.top-b.top`; these are layout coords =
zoom-invariant). Removed the visualViewport hide-guard. VERIFY GOTCHA: headless preview pages are "hidden" so the
fox's `requestAnimationFrame` is PAUSED → `fox.style` reads empty in `preview_eval` and the fox looks unpositioned;
`preview_screenshot` REPLAYS a frame and shows it placed correctly (don't panic — confirmed glued to the hero rim).
Couldn't physically pinch-zoom headless, so the final feel-confirm is a pinch on Christian's phone. (c) **Sources always fully open** — removed the default `open` on the nested week/day/sweep `<details>` in
`renderSources()` (lines ~1026/1028/1030) so opening Sources shows a condensed collapsed tree you drill into. (d)
**Home header** now reads **"Overview · updated Xh ago"** — `renderHome` computes `updAgo=timeAgo(meta.lastUpdated)`,
renders a muted `.vh-upd` span (this is the lightweight return of the freshness blurb removed in session 24, but
inline on the OVERVIEW header instead of a separate element). All verified at 375px, zero console errors.
NOTE on verifying the fox: `preview_screenshot` REPLAYS the `#fox` opacity transition, so the fox can look ~93%
visible on a non-Home view in a screenshot even though `fox-off`/opacity:0 is correctly applied — trust
preview_inspect/eval (`foxClasses`), not the shot ([[reference_web_local_gotchas]] §3).

### ✓ DONE (Jun 19, session 24) — removed Home meta blurbs
He didn't want two meta "inserts" on Home: (a) the header `.upd` blurb ("● updated Xh ago / N models · M sweeps")
— removed the `#upd` element (header now = logo + "Botany" only) and guarded `renderUpd()` (`const u=$('#upd'); if(u)…`);
(b) the **Pulse meta footer line** ("The Pulse · latest sweep · updated · auto-refreshes 6am & 6pm ET") — dropped the
`.pulse-meta` div from `heroHTML` (the Pulse paragraph itself stays). `.bar .upd`/`.pulse-meta` CSS + `pulseWhen`/
`pulseRoutine` vars now unused but harmless. Verified: both gone, data intact, zero console errors. Redeploy=`git push`.

### ✓ DONE (Jun 19, session 23) — +25% font (dad's eyes) · pinch-to-zoom
(1) **All fonts ×1.25** (his dad found it hard to read on phone). Done via a targeted regex pass over index.html
(`scripts`-free, inline python): multiplied every `font-size:Npx` and `font:[weight ]Npx` shorthand value by 1.25
(129 declarations, CSS + JS template strings). SVG chart text (`font-size="N"` attributes, no px) deliberately left
alone. Backup: `index.html.bak-prefont`. **Verified at 375px mobile: no horizontal overflow anywhere**, leaderboard
+ 2-col best-grid + nav (6 tabs) + Details/tie modals all still fit; only effect is the `.ftabs` sub-tab strips now
scroll horizontally (they're overflow-x scrollers by design — fine). Zero console errors.
(2) **Pinch-to-zoom enabled**: viewport meta dropped `maximum-scale=1.0, user-scalable=no` →
`width=device-width, initial-scale=1.0, viewport-fit=cover`. Redeploy = `git push`. If a future bump is wanted,
re-run the same ×factor regex (or revert from the .bak).

### ✓ DONE (Jun 19, session 22) — removed flowers · brighter forest · fox smoothness fix
(1) **Removed ALL flowers** (CSS `#flowers`/`.fl-*` + the 6-img element + `git rm flower-a/b.png`). He'll re-add
later as **overhead-view flower BUDS** (top-down), a different style — NOT the side-view sprigs. Don't re-add yet.
(2) **Background swapped — brighter, less gloomy.** New nano-banana **Pro** sunlit forest (golden light, fresh
greens, mossy path) replaces the gloomy misty one (`img/forest-bg.jpg` overwritten). Scrim lightened
(`.88/.42/.72` → `.74/.5/.44/.66`) so the sunlight shows but UI stays legible (header has its own dark bg; cards are
opaque). Verified readable.
(3) **Fox smoothness fix** (he said glitchy). Root cause: the 5 frames had **different canvas sizes** (220×146/156/
…) so each swap resized + shifted the fox; AND the JS `BOB` lifted the WHOLE sprite (feet off the ground = hopping).
Fixes: **normalized all 5 walk frames to a uniform 194×140 canvas** (crop→scale to common width→pad bottom-center so
feet align), set `bob=0` (gait is baked into the bottom-anchored frames, feet stay planted), `image-rendering:auto`
(frames are LANCZOS-scaled now), cadence 115→135ms, fox height 46→48. Verified: all 5 frames 194×140, no console
errors, data intact (96 models). Redeploy = `git push`.

### ✓ DONE (Jun 19, session 21) — tie card → popup; preview panel onto :8095
(1) **"Best model for…" tie card now opens the bottom-sheet POPUP** (like the model Details) instead of expanding
inline. `bestCard()` writes each tie to a `TIEMAP` (keyed by use-case label, reset each `renderHome`) + renders
`data-tie="<label>"`; new `tieInfo()`/`openTieModal()` show the label, "N-way tie · value", and all tied models as
`.tierow`s (lab dot + name + lab). Handler `[data-tieexpand]`→`[data-tie]`. Verified: 10-way "Longest context" tie
opens a clean popup listing all 10. (Old `.tielist/.tiechip/.tiecard.exp` CSS now unused, left harmless.)
(2) **Preview panel now shows the real :8095 app with data.** The panel had been showing the bare index.html file
(no server context → couldn't fetch `data/` → "0 models"). Killed the detached persistent http.server on 8095 and
ran `preview_start aitracker` so the PREVIEW tooling owns 8095 (serverId per session) and serves the directory →
data loads (96 models verified in-panel). TRADEOFF: the preview server is NOT detached, so it dies on session
switch (the old persistent-server guidance) — but the app is published live now, so his phone can use
polishcow31.github.io/polishbotany; the panel is for in-session preview. To restore a detached server later:
`nohup python3 -m http.server 8095 --directory /Users/christian/Sites/AI >/dev/null 2>&1 &` (but that re-conflicts
with preview_start). **Redeploy = `git push`.**

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
