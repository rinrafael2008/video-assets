import sys, subprocess
from PIL import Image
mp4=sys.argv[1]; out=sys.argv[2]; times=[float(x) for x in sys.argv[3:]]
ims=[]
for i,t in enumerate(times):
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',mp4,'-frames:v','1',f'/tmp/_f{i}.png'],check=True)
    ims.append(Image.open(f'/tmp/_f{i}.png').convert('RGB').resize((360,640),Image.LANCZOS))
cols=3; rows=(len(ims)+cols-1)//cols
sh=Image.new('RGB',(360*cols,640*rows),'white')
for i,im in enumerate(ims): sh.paste(im,((i%cols)*360,(i//cols)*640))
sh.save(out); print('ok')
