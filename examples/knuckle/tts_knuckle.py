import json
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

LINES = [
    ("That crack isn't your bones.", 0.45),
    ("Pull a knuckle, and the joint separates so fast that a tiny gap opens in the fluid. That's the pop.", 0.35),
    ("It took until twenty fifteen for an M R I to film it.", 0.45),
    ("So does it give you arthritis?", 0.45),
    ("One doctor tested it on himself. For over sixty years, he cracked only his left hand, twice a day.", 0.30),
    ("His right hand was the control.", 0.45),
    ("Neither hand got arthritis, and he won an Ig Nobel prize.", 0.40),
    ("A later study of two hundred fifteen people found no link either.", 0.50),
    ("So no, it isn't your bones. Sorry, mom.", 0.0),
]
k = Kokoro("/home/claude/work/kokoro-v1.0.onnx", "/home/claude/work/voices-v1.0.bin")
chunks, meta, t, sr_out = [], [], 0.0, None
for text, pause in LINES:
    s, sr = k.create(text, voice="am_adam", speed=1.05, lang="en-us")
    sr_out = sr
    dur = len(s) / sr
    meta.append({"text": text, "start": round(t, 3), "end": round(t + dur, 3)})
    chunks.append(s)
    t += dur
    if pause:
        chunks.append(np.zeros(int(sr * pause), dtype=np.float32))
        t += pause
a = np.concatenate(chunks)
a = a / max(1e-6, np.max(np.abs(a))) * 0.92
sf.write("narration.wav", a, sr_out)
json.dump({"total": round(t, 3), "lines": meta}, open("narration_meta.json", "w"), indent=1)
print(round(t, 2))
for m in meta: print(m["start"], m["end"], m["text"][:50])
