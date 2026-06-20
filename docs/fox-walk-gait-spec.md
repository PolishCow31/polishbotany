# Fox walk-cycle gait spec (for the future rebuild)

Distilled from a deep-research pass (Jun 20 2026) — verified against peer-reviewed
biomechanics (Cartmill et al. 2002; Usherwood eLife 2017) + animation craft
(Williams' *Animator's Survival Kit*, Game Developer / AnimSchool / Slynyrd) +
Muybridge. Use this to build the walk **when Fable 5 returns** (current nano-banana /
NB2 CANNOT draw distinct gait phases — see HANDOFF "fox walk parked").

## The gait (a fox = canid = lateral-sequence symmetrical walk)

- **Footfall order:** LH → LF → RH → RF (left-hind, left-fore, right-hind, right-fore).
  Each hind foot is immediately followed by the **same-side** fore. Starting limb is
  arbitrary; the invariant is *hind-then-ipsilateral-fore*.
- **Timing:** the four footfalls are evenly spaced **~25% of the cycle apart**. On an
  8-frame loop: contacts land at **frames 1, 3, 5, 7**.
  - near-hind contact = frame 1 (phase 0%)
  - near-fore contact = frame 3 (phase 25%) ← **the near-hind LEADS the near-fore by ~2 frames**
  - far-hind contact = frame 5 (phase 50%)
  - far-fore contact = frame 7 (phase 75%)
- **Duty factor > 0.5** (walk, by definition; canids ≈0.6–0.69): each leg is planted
  **~5 of 8 frames**, and at least two feet are ALWAYS on the ground (no airborne phase).
- **Left/right offset = exactly 50%:** far-side legs = near-side legs shifted **+4 frames**.
- **Per-leg keyframes (Williams' 4 keys):** CONTACT → DOWN (recoil) → PASSING → UP (lift).
  Key all four per leg, not just contact+passing (2 keys = stiff "sweep").

## What makes it read as walking (vs the "paw dance" / "marching in place")

THE failure mode we hit: legs move in **unison / symmetrically**, no contact→passing
distinction, feet don't push back. Fixes:
1. **Offset the near-fore vs near-hind by ~2 frames** — they must NEVER be in the same
   position at the same time. (The "front & hind in simple anti-phase / half-step opposite"
   idea is WRONG — refuted 0-3. It's a 25% lateral offset, not 50% opposite.)
2. **Feet plant and push BACK:** a planted foot must translate *backward* relative to the
   body across its stance frames, then lift and swing forward. If feet slide, it skates.
3. Step through a real reference frame-by-frame; mark contact/passing/lift explicitly.

## Reference

- Muybridge *Animal Locomotion* (1887), evenly-sampled lateral plates (6/8/12 phases).
  Usable walking-carnivore GIF: Wikimedia "Tigress walking 1884~1886.gif" (12 frames,
  lateral) — same lateral-sequence gait; saved approach = restyle its phases to the fox.
- Full cited report: deep-research run wf_3c7afcf8-1fd (Jun 20 2026).

## Build notes (when Fable 5 is back)

- Generate as a **single sprite sheet** (one generation → consistent body, no head-pop)
  — that part nano-banana already does well. The blocker was leg-phase fidelity.
- Then: magenta-key (`scripts/chroma_key.py` logic) + **largest-connected-component
  denoise** (drops stray specks — the green-blob bug) + register bottom-center on a shared
  canvas + order per the frames-1..8 grid above.
- Controller already does **distance-locked stepping** (advance a leg frame per ~4.5px
  MOVED) so feet plant at any speed — keep that; just feed it correct frames.
