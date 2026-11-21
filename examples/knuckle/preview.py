import sys, skia, json
sys.path.insert(0, '/home/claude/work/engine')
import eng, scenes
from PIL import Image
eng.load_assets('/home/claude/work/engine/narration.wav', '/home/claude/work/engine/mouth.npz')
times = [float(x) for x in sys.argv[2:]]
out = sys.argv[1]
ims = []
for t in times:
    surf = skia.Surface(eng.W, eng.H); cv = surf.getCanvas(); scenes.frame(cv, t)
    a = surf.makeImageSnapshot().toarray()
    ims.append(Image.fromarray(a[..., [2, 1, 0]]).resize((360, 640), Image.LANCZOS))
cols = 3; rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (360 * cols, 640 * rows), 'white')
for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
sheet.save(out)
print('ok', out)
