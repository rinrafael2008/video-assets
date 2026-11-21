#!/usr/bin/env python3
"""One command from script to finished video.

    python3 -I build.py projects/<slug> --draft      # ~10-15 s: half-res, no motion blur, for checking cues and layout
    python3 -I build.py projects/<slug>              # final: 1080x1920, 5-sub-frame motion blur, loudness-normalised audio

Project folder: script.json (lines, pron, show) + scenes.py. scenes.py is either
  - a kit project:   def build() -> [kit.Scene, ...]  (cues, camera, sfx, captions all derived from word times)
  - a custom project: frame(c, T), TOTAL   (+ optional CUES list)
Steps (each skipped when its output is newer than its inputs): tts -> align -> lipsync -> mix -> render (2 procs) -> mux -> contact sheet.
"""
import sys, os, json, time, subprocess, importlib.util, multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def newer(out, *ins):
    return os.path.exists(out) and all(os.path.exists(i) and os.path.getmtime(out) >= os.path.getmtime(i) for i in ins)


def step(name, t0):
    print(f"[{time.time() - t0:6.1f}s] {name}", flush=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    proj = os.path.abspath(args[0]); draft = "--draft" in sys.argv; force = "--force" in sys.argv
    slug = os.path.basename(proj.rstrip("/")); T0 = time.time()
    out_dir = os.path.join(proj, "out"); os.makedirs(out_dir, exist_ok=True)
    out = args[1] if len(args) > 1 else os.path.join(out_dir, f"{slug}-{'draft' if draft else 'final'}.mp4")
    wav, words, spoken, npz = (os.path.join(proj, f) for f in ("narration.wav", "words.json", "words_spoken.json", "mouth.npz"))
    script = os.path.join(proj, "script.json")

    if force or not newer(wav, script):
        import tts; step(f"tts ({tts.run(proj):.1f}s of narration)", T0)
    if force or not newer(words, wav, script):
        import align; align.align(proj); step("align (word timings)", T0)
    if force or not newer(npz, words, spoken):
        import lipsync; lipsync.build(json.load(open(spoken)), wav, npz); step("lipsync", T0)

    import eng, kit, soundfile as sf
    nlen = sf.info(wav).duration
    kit.load(proj, nlen)
    sp = importlib.util.spec_from_file_location("scenes", os.path.join(proj, "scenes.py")); m = importlib.util.module_from_spec(sp)
    sys.path.insert(0, proj); sp.loader.exec_module(m)
    if hasattr(m, "build"):
        tl = kit.Timeline(m.build(), kit.STATE["total"]); frame_fn, total, cues = tl.frame, tl.total, tl.cues()
    else:
        frame_fn, total, cues = m.frame, m.TOTAL, list(getattr(m, "CUES", []))
    step(f"scenes loaded ({total:.2f}s, {len(cues)} sfx cues)", T0)

    import sfx
    aac = os.path.join(out_dir, "mix.m4a")
    sfx.mix_from_cues(wav, total, cues, aac, workdir=out_dir, music_fn=getattr(m, "MUSIC", None), voice_fx=getattr(m, "VOICE_FX", None), master=getattr(m, "MASTER", None)); step("audio mix + loudnorm", T0)

    n = int(round(total * eng.FPS)); mid = n // 2
    kw = dict(nsub=1, shutter=0.0, crf=27, scale=0.5) if draft else dict(nsub=5, shutter=0.6, crf=18, scale=1.0)
    if not draft: kw.update(getattr(m, "RENDER", {}))
    global _FN, _KW, _DIR; _FN, _KW, _DIR = frame_fn, kw, out_dir
    nproc = max(2, min(int(os.environ.get("NPROC", os.cpu_count() or 2)), 6)); bounds = [round(n * k / nproc) for k in range(nproc + 1)]
    with mp.get_context("fork").Pool(nproc) as p: p.map(_work, [(i, bounds[i], bounds[i + 1]) for i in range(nproc)])
    step(f"render {n} frames ({'draft' if draft else 'final'})", T0)
    open(f"{out_dir}/list.txt", "w").write("".join(f"file '{out_dir}/seg{i}.mp4'\n" for i in range(nproc)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{out_dir}/list.txt", "-i", aac,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", out], check=True)
    step(f"muxed -> {out}", T0)
    sheet(out, total, out.replace(".mp4", ".sheet.png"), [s.start for s in tl.scenes] if hasattr(m, "build") else None)
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "csv=p=0", out], capture_output=True, text=True).stdout.split()
    step(f"verified: {pr}", T0)


_FN = _KW = _DIR = None


def _work(a):
    import eng
    i, f0, f1 = a
    eng.render_range(_FN, f0, f1, f"{_DIR}/seg{i}.mp4", **_KW)


def sheet(mp4, total, png, starts):
    from PIL import Image
    ts = [min(s + 0.9, total - 0.1) for s in starts] if starts else [total * (k + 0.5) / 9 for k in range(9)]
    ims = []
    for t in ts[:12]:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=360:-2", "/tmp/_f.png"], check=True)
        ims.append(Image.open("/tmp/_f.png").convert("RGB").copy())
    cols = 4; rows = (len(ims) + cols - 1) // cols; w, h = ims[0].size
    sh = Image.new("RGB", (w * cols, h * rows), "white")
    for i, im in enumerate(ims): sh.paste(im, ((i % cols) * w, (i // cols) * h))
    sh.save(png)


if __name__ == "__main__":
    main()
