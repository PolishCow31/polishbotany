#!/usr/bin/env python3
"""Key out a flat magenta (#FF00FF) chroma background from a generated foliage asset,
despill the purple fringe, autocrop to content. Magenta is used (not green) because the
subjects are green leaves. Usage: chroma_key.py <src> <dst.png>"""
import sys
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA")
px = im.load()
w, h = im.size
for y in range(h):
    for x in range(w):
        r, g, b, a = px[x, y]
        m = min(r, b) - g                      # magenta-ness: R & B high, G low
        if m > 80:                             # clearly background
            px[x, y] = (r, g, b, 0)
        elif m > 22:                           # anti-aliased edge: feather + despill
            alpha = int(255 * (1 - (m - 22) / 58.0))
            px[x, y] = (min(r, g + 40), g, min(b, g + 40), max(0, alpha))
        else:                                  # foreground; mild despill if still purple-leaning
            if r > g and b > g:
                px[x, y] = (min(r, g + 60), g, min(b, g + 60), 255)
            else:
                px[x, y] = (r, g, b, 255)
bbox = im.getbbox()
if bbox:
    im = im.crop(bbox)
im.save(dst)
print("keyed", src, "->", dst, im.size)
