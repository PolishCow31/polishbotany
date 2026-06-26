#!/usr/bin/env python3
"""Generate the pixel-art fox: an 8-frame WALK cycle + a SIT pose.

History: nano-banana can't draw gait (frozen "paw dance"); a later attempt drew
code legs onto the photoreal nano-banana body and it looked horrifying in motion
(smooth photo body + drawn legs = flailing sticks). Christian's call (Jun 26): make
it an actual PIXEL-ART sprite. This is hand-authored chunky pixel art — one cohesive
sprite, so animated legs read as a game sprite, not sticks.

Side profile, facing RIGHT. Native art ~38x27 (chunky); the app displays it with
image-rendering:pixelated so it stays crisp. Frames are bottom-anchored + uniform so
they drop into the existing distance-locked controller. Walk follows the lateral-
sequence gait (docs/fox-walk-gait-spec.md): contacts spaced ~25% apart, feet plant +
push back through stance then lift/swing; gentle 2-beat body bob.

Reproducible: `python3 scripts/build_fox_walk.py` -> img/fox-walk-1..8.png + img/fox-sit.png.
"""
import os, math
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG  = os.path.join(ROOT, 'img')
ART_W, ART_H = 38, 27

TRANSP=(0,0,0,0)
OR =(226,118,42,255)    # fox orange
ORD=(193,86,28,255)     # darker orange (far legs / shade)
CR =(245,233,214,255)   # cream
DK =(58,38,26,255)      # dark brown (lower legs)
DK2=(44,28,20,255)      # far-leg dark
BK =(20,14,10,255)      # near-black (nose, eye, ear tips)

def rrect(d,x0,y0,x1,y1,c): d.rectangle([x0,y0,x1,y1],fill=c)

def head_and_tail(d,by):
    # tail (left), bushy, cream tip
    d.polygon([(12,11+by),(7,7+by),(2,8+by),(0,12+by),(2,17+by),(7,18+by),(12,16+by)],fill=OR)
    d.polygon([(0,12+by),(2,8+by),(4,10+by),(4,16+by),(1,16+by)],fill=CR)

def head(d,by):
    d.ellipse([28,5+by,37,15+by],fill=OR)
    d.polygon([(34,9+by),(38,11+by),(38,13+by),(34,14+by)],fill=OR)   # snout
    d.polygon([(28,6+by),(30,0+by),(33,6+by)],fill=OR)                # ears
    d.polygon([(32,6+by),(34,0+by),(36,6+by)],fill=OR)
    d.polygon([(29,3+by),(30,0+by),(31,3+by)],fill=BK)
    d.polygon([(33,3+by),(34,0+by),(35,3+by)],fill=BK)
    d.polygon([(34,12+by),(38,12+by),(38,14+by),(33,14+by)],fill=CR)  # cheek/muzzle
    d.point((38,12+by),fill=BK); d.point((37,12+by),fill=BK)          # nose
    rrect(d,33,8+by,34,9+by,BK)                                       # eye

def draw_walk(frame):
    im=Image.new('RGBA',(ART_W,ART_H),TRANSP); d=ImageDraw.Draw(im)
    by=[0,0,-1,-1,0,0,-1,-1][frame%8]
    GROUND=25; bodybot=18+by
    legs=[('FH',14,False,4),('FF',23,False,6),('NH',16,True,0),('NF',25,True,2)]
    def legdraw(hx,near,contact):
        p=((frame-contact)%8)/8.0
        if p<0.625: t=p/0.625; fx=hx+2-int(round(4*t)); lift=0
        else: t=(p-0.625)/0.375; fx=hx-2+int(round(4*t)); lift=int(round(3*math.sin(math.pi*t)))
        legc=OR if near else ORD; sockc=DK if near else DK2
        foot=GROUND-lift; midy=bodybot+2; w=3 if near else 2
        d.line([(hx,bodybot-3),(hx,midy)],fill=legc,width=w)
        d.line([(hx,midy),(fx,foot)],fill=sockc,width=2)
        rrect(d,fx-1,foot,fx+1,foot+1,sockc)
    for _,hx,near,ct in legs:
        if not near: legdraw(hx,near,ct)
    for _,hx,near,ct in legs:
        if near: legdraw(hx,near,ct)
    head_and_tail(d,by)
    rrect(d,11,9+by,27,17+by,OR)                 # body
    d.ellipse([8,9+by,15,17+by],fill=OR)
    d.ellipse([23,8+by,31,17+by],fill=OR)
    rrect(d,14,16+by,25,17+by,CR)                # belly
    d.polygon([(27,11+by),(31,12+by),(30,16+by),(26,16+by)],fill=CR)  # chest/throat
    head(d,by)
    return im

def draw_sit():
    # An IDLE/standing pose (used during random pauses) — same sprite, all 4 legs planted
    # neutral. Cohesive + clean; a proper curled-sit pose can be added later.
    im=Image.new('RGBA',(ART_W,ART_H),TRANSP); d=ImageDraw.Draw(im)
    GROUND=25; bodybot=18
    def leg(hx,near):
        legc=OR if near else ORD; sockc=DK if near else DK2; w=3 if near else 2
        d.line([(hx,bodybot-3),(hx,bodybot+2)],fill=legc,width=w)
        d.line([(hx,bodybot+2),(hx,GROUND)],fill=sockc,width=2)
        rrect(d,hx-1,GROUND,hx+1,GROUND+1,sockc)
    leg(14,False); leg(23,False)                 # far legs first
    head_and_tail(d,0)
    rrect(d,11,9,27,17,OR)
    d.ellipse([8,9,15,17],fill=OR); d.ellipse([23,8,31,17],fill=OR)
    rrect(d,14,16,25,17,CR)
    d.polygon([(27,11),(31,12),(30,16),(26,16)],fill=CR)
    leg(16,True); leg(25,True)                   # near legs over body
    head(d,0)
    return im

frames=[draw_walk(f) for f in range(8)]
for i,fr in enumerate(frames,1):
    fr.save(os.path.join(IMG,f'fox-walk-{i}.png'))
draw_sit().save(os.path.join(IMG,'fox-sit.png'))

# review strip (scaled NEAREST so the chunky pixels are visible)
S=6; GR=(90,96,90,255)
strip=Image.new('RGBA',(ART_W*S*8, ART_H*S+18),GR); sd=ImageDraw.Draw(strip)
for i,fr in enumerate(frames):
    strip.alpha_composite(fr.resize((ART_W*S,ART_H*S),Image.NEAREST),(i*ART_W*S,18))
    sd.text((i*ART_W*S+4,4),str(i+1),fill=(255,255,255,255))
strip.convert('RGB').save(os.path.join(ROOT,'docs','fox-walk-frames.png'))
print('wrote 8 walk frames + fox-sit.png (pixel art) to', IMG)
