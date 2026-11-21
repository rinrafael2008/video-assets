"""Free narration with Kokoro (voice am_adam) + per-line timing meta.
usage: python3 -I tts.py <project_dir>      reads <project_dir>/script.json -> narration.wav/.mp3, narration_meta.json
script.json: {"voice":"am_adam","speed":1.05,"lines":[["Spoken text.", pause_after_seconds], ...]}
Write numbers and acronyms the way they are spoken ("twenty fifteen", "M R I"); captions come from the transcript/aligner.
"""
import sys, json, os, subprocess
import numpy as np
import soundfile as sf

def run(proj):
    from kokoro_onnx import Kokoro
    sc = json.load(open(os.path.join(proj, "script.json")))
    k = Kokoro(os.path.join(os.environ.get("KOKORO_DIR", "/home/claude/work"), "kokoro-v1.0.onnx"), os.path.join(os.environ.get("KOKORO_DIR", "/home/claude/work"), "voices-v1.0.bin"))
    chunks, meta, t, sr_out = [], [], 0.0, 24000
    for text, pause in sc["lines"]:
        s, sr = k.create(text, voice=sc.get("voice", "am_adam"), speed=sc.get("speed", 1.05), lang="en-us")
        sr_out = sr; dur = len(s) / sr
        meta.append({"text": text, "start": round(t, 3), "end": round(t + dur, 3)})
        chunks.append(s); t += dur
        if pause:
            chunks.append(np.zeros(int(sr * pause), dtype=np.float32)); t += pause
    a = np.concatenate(chunks); a = a / max(1e-6, np.max(np.abs(a))) * 0.92
    wav = os.path.join(proj, "narration.wav"); sf.write(wav, a, sr_out)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-codec:a", "libmp3lame", "-q:a", "3", os.path.join(proj, "narration.mp3")], check=True)
    json.dump({"total": round(t, 3), "lines": meta}, open(os.path.join(proj, "narration_meta.json"), "w"), indent=1)
    return t

if __name__ == "__main__":
    print("narration seconds:", round(run(sys.argv[1]), 2))
