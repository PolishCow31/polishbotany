#!/usr/bin/env python3
"""Generate the fox WALK cycle — 8 frames, real legs that actually move.

The blocker for months: no image model (nano-banana, NB2) can draw distinct gait
phases — every "frame" had near-identical legs => the "paw dance". The fix here:
stop asking a model to draw the gait. Keep the gorgeous nano-banana fox BODY and
draw the 4 legs procedurally per the verified gait spec (docs/fox-walk-gait-spec.md)
with real 2-bone IK (law of cosines) so knees bend, feet plant + push backward
through stance, then lift in a sin-arc swing.

Gait (canid lateral-sequence walk): contacts at frames 1,3,5,7; near-hind LEADS
near-fore by 2 frames (25% offset); far side = near side + 4 frames (50%); duty
factor >0.5 so >=2 feet always down. Far legs drawn behind the body, near in front.

Reproducible + idempotent: reads a PRISTINE source (img/fox-source.png) and writes
img/fox-walk-1..8.png in CYCLE ORDER. Re-run anytime: `python3 scripts/build_fox_walk.py`.
Originated from the Jun 26 2026 "fox-walk-approaches" workflow (drawnlegs won the bake-off).
"""
import os
from PIL import Image, ImageDraw
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG  = os.path.join(ROOT, 'img')
SRC  = os.path.join(IMG, 'fox-source.png')   # pristine full fox (legs get erased + redrawn from this)

im = Image.open(SRC).convert('RGBA')
W, H = im.size  # 220x146
a = np.array(im)

# ---- 1. Body without legs: erase below a curved belly cutoff (tail x<58 fully kept) ----
anchors = [(0,146),(58,146),(60,108),(70,106),(100,104),(115,106),
           (130,104),(150,108),(168,111),(179,114),(200,114),(220,114)]
def cutoff(x):
    for i in range(len(anchors)-1):
        x0,y0=anchors[i]; x1,y1=anchors[i+1]
        if x0<=x<=x1:
            t=(x-x0)/(x1-x0) if x1>x0 else 0
            return y0+(y1-y0)*t
    return 114
body = a.copy()
for x in range(W):
    cy=cutoff(x)
    for y in range(H):
        if y>cy and x>=58:
            body[y,x]=[0,0,0,0]
body_img = Image.fromarray(body)

# ---- 2. Legs: 4 limbs, lateral-sequence phasing (contacts at frames 0,2,4,6 = 1,3,5,7) ----
LEGS = {
  'NH': dict(hx=112, hy=107, near=True,  contact=0),  # near hind  (leads near-fore by 2)
  'NF': dict(hx=180, hy=112, near=True,  contact=2),  # near fore
  'FH': dict(hx=72,  hy=104, near=False, contact=4),  # far hind   (= near hind + 4)
  'FF': dict(hx=146, hy=108, near=False, contact=6),  # far fore   (= near fore + 4)
}
SHAFT=(40,23,21,255); SHAFT_FAR=(29,17,16,255)
PAW=(12,8,8,255);     PAW_FAR=(7,5,5,255)
THIGH=(199,88,30,255);THIGH_FAR=(152,67,23,255)
GROUND=141; UPPER=16; LOWER=16; THICK=8; THICK_FAR=7
REACH=9; PUSH=11; LIFT=12; NFRAMES=8

def foot_pos(hx, hy, p):
    stance_end=5/8
    if p < stance_end:                       # stance: foot planted, translating BACKWARD
        t=p/stance_end
        return hx+REACH-(REACH+PUSH)*t, GROUND, True
    t=(p-stance_end)/(1-stance_end)          # swing: lift in a sin arc, reach forward
    return hx-PUSH+(REACH+PUSH)*t, GROUND-LIFT*np.sin(np.pi*t), False

def draw_leg(draw, hx, hy, p, near):
    fx,fy,_=foot_pos(hx,hy,p)
    col=SHAFT if near else SHAFT_FAR
    paw=PAW if near else PAW_FAR
    thigh=THIGH if near else THIGH_FAR
    th=THICK if near else THICK_FAR
    thl=max(th-2,3)
    L1,L2=UPPER,LOWER
    dx,dy=fx-hx,fy-hy
    d=np.hypot(dx,dy); d=min(d,L1+L2-0.5); d=max(d,abs(L1-L2)+0.5)
    base=np.arctan2(dy,dx)
    ca=max(-1,min(1,(L1*L1+d*d-L2*L2)/(2*L1*d)))
    ang=np.arccos(ca)
    sign=1 if hx<130 else -1                  # canid Z-bend: hind stifle vs fore elbow
    ka=base-sign*ang
    kx,ky=hx+L1*np.cos(ka), hy+L1*np.sin(ka)
    tr=th/2+2
    draw.ellipse([hx-tr,hy-tr-1,hx+tr,hy+tr],fill=thigh)   # orange blob masks the hip seam
    draw.line([(hx,hy),(kx,ky)],fill=col,width=th)
    draw.line([(kx,ky),(fx,fy)],fill=col,width=thl)
    rr=th/2
    draw.ellipse([hx-rr+1,hy-rr+1,hx+rr-1,hy+rr-1],fill=col)
    draw.ellipse([kx-rr,ky-rr,kx+rr,ky+rr],fill=col)
    rl=thl/2
    draw.ellipse([fx-rl,fy-rl,fx+rl,fy+rl],fill=col)
    pw=thl+2
    draw.ellipse([fx-pw/2,fy-2.5,fx+pw/2+2,fy+2],fill=paw)

frames=[]
for f in range(NFRAMES):
    canvas=Image.new('RGBA',(W,H),(0,0,0,0))
    dd=ImageDraw.Draw(canvas)
    for name in ('FH','FF'):                  # far legs behind body
        lg=LEGS[name]; draw_leg(dd,lg['hx'],lg['hy'],((f-lg['contact'])%NFRAMES)/NFRAMES,lg['near'])
    canvas.alpha_composite(body_img)
    dd=ImageDraw.Draw(canvas)
    for name in ('NH','NF'):                  # near legs in front
        lg=LEGS[name]; draw_leg(dd,lg['hx'],lg['hy'],((f-lg['contact'])%NFRAMES)/NFRAMES,lg['near'])
    frames.append(canvas)

# ---- 3. write the 8 frames into the app (cycle order) ----
for i,fr in enumerate(frames,1):
    fr.save(os.path.join(IMG,f'fox-walk-{i}.png'))

# ---- 4. reference strip for docs ----
GRAY=(90,96,90,255)
strip=Image.new('RGBA',(W*NFRAMES, H+18),GRAY)
sd=ImageDraw.Draw(strip)
for i,fr in enumerate(frames):
    strip.alpha_composite(fr,(i*W,18)); sd.text((i*W+4,4),str(i+1),fill=(255,255,255,255))
strip.convert('RGB').save(os.path.join(ROOT,'docs','fox-walk-frames.png'))
print(f'wrote {NFRAMES} frames to {IMG}/fox-walk-1..8.png + docs/fox-walk-frames.png')
