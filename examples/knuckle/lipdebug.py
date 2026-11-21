import sys, skia, json
sys.path.insert(0,'/home/claude/work/engine')
import eng, scenes
from PIL import Image, ImageDraw
eng.load_assets('/home/claude/work/engine/narration.wav','/home/claude/work/engine/mouth.npz')
t0=float(sys.argv[2]); t1=float(sys.argv[3]); step=float(sys.argv[4])
words=scenes.WORDS
ts=[]; t=t0
while t<t1: ts.append(round(t,3)); t+=step
crops=[]
for T in ts:
    surf=skia.Surface(eng.W,eng.H); c=surf.getCanvas(); c.clear(skia.ColorSetARGB(255,255,209,102))
    scenes.narr(c,540,1000,2.0,T,fists=False,shadow=False)
    a=surf.makeImageSnapshot().toarray()[...,[2,1,0]]
    # head center approx: feet 1000 - 2*(215+165+22+86)=1000-976=24 -> head y~24..; crop
    im=Image.fromarray(a[0:340,380:700]).resize((200,212))
    w=[x[0] for x in words if x[1]<=T<x[2]+0.02]
    d=ImageDraw.Draw(im); d.text((6,4),f"{T:.2f} {w[0] if w else '-'}",fill=(0,0,0))
    crops.append(im)
cols=6; rows=(len(crops)+cols-1)//cols
sh=Image.new('RGB',(200*cols,212*rows),'white')
for i,im in enumerate(crops): sh.paste(im,((i%cols)*200,(i//cols)*212))
sh.save(sys.argv[1]); print(len(crops))
