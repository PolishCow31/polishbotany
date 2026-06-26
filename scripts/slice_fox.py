#!/usr/bin/env python3
"""Slice Elthen's 2D Pixel Art Fox sprite sheet into the frames Botany's hero fox uses.

Source: scripts/fox-sheet-elthen.png (Elthen's Pixel Art Shop, elthen.itch.io/2d-pixel-art-fox-sprites).
448x224 RGBA, 32x32 slices, 14 cols x 7 rows. Row order (Elthen standard, visually confirmed):
  0 Idle(5)  1 idle2(14)  2 movement/WALK(8)  3 catch(11)  4 damage(5)  5 sleep(6)  6 death(7)

We use three: WALK (row 2), IDLE-standing (row 0), SLEEP-curled (row 5).
Full 32x32 cells are kept (no trim) so the ground line stays consistent frame-to-frame
for the controller's bottom-anchor. Re-run anytime to regenerate.
"""
from PIL import Image
import os

SRC = os.path.join(os.path.dirname(__file__), 'fox-sheet-elthen.png')
IMG = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'img'))
S = 32

sheet = Image.open(SRC).convert('RGBA')

def cell(col, row):
    return sheet.crop((col*S, row*S, (col+1)*S, (row+1)*S))

# (row, frame_count, out_prefix)
JOBS = [
    (2, 8, 'fox-walk'),    # movement -> walk cycle
    (0, 5, 'fox-idle'),    # Idle -> standing idle
    (5, 6, 'fox-sleep'),   # sleep -> curled nap
]

for row, n, prefix in JOBS:
    for i in range(n):
        out = os.path.join(IMG, f'{prefix}-{i+1}.png')
        cell(i, row).save(out)
    print(f'{prefix}: wrote {n} frames')

# retire the old single sit pose (replaced by idle + sleep)
old = os.path.join(IMG, 'fox-sit.png')
if os.path.exists(old):
    os.remove(old); print('removed old fox-sit.png')
print('done')
