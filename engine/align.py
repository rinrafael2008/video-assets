"""Offline word timings (forced alignment with pocketsphinx) - replaces the upload + Picsart-transcribe round trip.
usage: python3 -I align.py <project_dir>   reads script.json + narration.wav + narration_meta.json, writes words.json
Accuracy vs ASR transcript on the knuckle video: mean 60 ms, p90 ~90 ms (ok for captions, cues and lip-sync).
Words missing from the CMU dictionary need "pron": {"word": "ARPABET PHONES"} in script.json (e.g. "ig": "IH G").
If this fails, fall back to picsart_media_transcribe on a raw.githubusercontent.com URL (WITHOUT the text param).
"""
import sys, json, re, os, subprocess
import numpy as np
import soundfile as sf


def align(proj):
    from pocketsphinx import Decoder, get_model_path
    mp = get_model_path()
    sc = json.load(open(os.path.join(proj, "script.json"))); pron = sc.get("pron", {})
    meta = json.load(open(os.path.join(proj, "narration_meta.json")))
    wav = os.path.join(proj, "narration.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ar", "16000", "-ac", "1", "-f", "s16le", "/tmp/_n16.raw"], check=True)
    pcm = np.fromfile("/tmp/_n16.raw", dtype=np.int16)
    y = pcm.astype(np.float32) / 32768.0
    hop = 160                                                     # 10 ms energy frames
    rms = np.sqrt(np.convolve(y ** 2, np.ones(hop) / hop, mode="same"))[::hop]
    res = []
    for ln in meta["lines"]:
        a, b = int(max(ln["start"] - 0.05, 0) * 16000), int((ln["end"] + 0.05) * 16000)
        words = ln["text"].split()
        clean = [re.sub(r"[^a-z']", "", w.lower()) for w in words]
        d = Decoder(hmm=f"{mp}/en-us/en-us", dict=f"{mp}/en-us/cmudict-en-us.dict", loglevel="FATAL")
        for c_ in clean:
            if c_ in pron and d.lookup_word(c_) is None: d.add_word(c_, pron[c_], True)
            elif d.lookup_word(c_) is None: raise SystemExit(f"'{c_}' not in dictionary: add \"pron\": {{\"{c_}\": \"PHONES\"}} to script.json")
        d.set_align_text(" ".join(clean))
        d.start_utt(); d.process_raw(pcm[a:b].tobytes(), False, True); d.end_utt()
        al = [(x.start_frame / 100.0, (x.end_frame + 1) / 100.0) for x in d.seg() if not x.word.startswith(("<", "[", "+"))]
        if len(al) != len(words): raise SystemExit(f"alignment mismatch on: {ln['text']}")
        seg = rms[int(ln["start"] * 100):int(ln["end"] * 100) + 1]; thr = max(seg.max() * 0.08, 1e-3) if len(seg) else 1e-3
        t0 = a / 16000
        for w, (s, e) in zip(words, al):
            s += t0; e += t0
            for t in np.arange(s, s + 0.15, 0.01):               # snap start to the audible onset
                if rms[min(int(t * 100), len(rms) - 1)] > thr: s = float(t); break
            res.append([w, round(s, 3), round(e, 3)])
    for i in range(len(res) - 1):                                  # continuous speech: end = next start
        if 0 <= res[i + 1][1] - res[i][2] < 0.15: res[i][2] = res[i + 1][1]
        res[i][2] = max(res[i][2], res[i][1] + 0.05)
    json.dump(res, open(os.path.join(proj, "words_spoken.json"), "w"))          # as spoken (for lip-sync)
    disp = merge_show(res, sc.get("show", {}))
    json.dump(disp, open(os.path.join(proj, "words.json"), "w"))                 # as displayed (captions, cues)
    return disp


def merge_show(words, show):
    """show: {"twenty fifteen": "2015", "m r i": "MRI"} merges consecutive spoken words into one caption word"""
    norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    rules = sorted(((k.split(), v) for k, v in show.items()), key=lambda r: -len(r[0]))
    out, i = [], 0
    while i < len(words):
        for ph, rep in rules:
            n = len(ph)
            if i + n <= len(words) and [norm(w[0]) for w in words[i:i + n]] == ph:
                tail = re.search(r"[^\w']+$", words[i + n - 1][0]); out.append([rep + (tail.group(0) if tail else ""), words[i][1], words[i + n - 1][2]]); i += n; break
        else: out.append(list(words[i])); i += 1
    return out


if __name__ == "__main__":
    print(len(align(sys.argv[1])), "words")
