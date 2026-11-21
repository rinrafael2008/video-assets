import sys, subprocess, multiprocessing as mp
sys.path.insert(0, '/home/claude/work/engine')
import eng, scenes
def work(a):
    i, f0, f1 = a
    eng.ENV = eng.Env('/home/claude/work/engine/narration.wav')
    eng.render_range(scenes.frame, f0, f1, f'/tmp/seg{i}.mp4', nsub=5, shutter=0.6, crf=18)
if __name__ == '__main__':
    n = int(round(scenes.TOTAL * eng.FPS)); mid = n // 2
    with mp.Pool(2) as p: p.map(work, [(0, 0, mid), (1, mid, n)])
    open('/tmp/list.txt', 'w').write("file '/tmp/seg0.mp4'\nfile '/tmp/seg1.mp4'\n")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', '/tmp/list.txt', '-c', 'copy', '/tmp/silent.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', '/tmp/silent.mp4', '-i', '/home/claude/work/engine/knuckle-mix-v1.mp3',
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart',
                    '/home/claude/work/engine/knuckle-v1.mp4'], check=True)
    print('done frames', n)
