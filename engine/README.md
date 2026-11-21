# Code-rendered stickman shorts: fast pipeline

Free end to end (Kokoro voice, Skia drawing, numpy music/SFX, ffmpeg). One command turns a script plus a scene file into a finished 1080x1920 short.

```
python3 -I engine/build.py projects/<slug> --draft   # ~10 s once narration exists: half-res, no blur, to check cues and layout
python3 -I engine/build.py projects/<slug>           # final: motion blur, loudness-normalised audio, contact sheet (~80 s for 32 s)
```

## Setup (new workspace)
- `pip install --break-system-packages skia-python kokoro-onnx soundfile numpy pillow pocketsphinx`; ffmpeg; Poppins-Bold at `/usr/share/fonts/truetype/google-fonts/`.
- Kokoro files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) from the kokoro-onnx GitHub release `model-files-v1.0`; put them in `/home/claude/work` or set `KOKORO_DIR`.

## Making a video (target: about 15 minutes of work after the idea is picked)
1. **Topic + facts.** Curiosity question with a twist; check every claim with a search; note sources for the description.
2. **`projects/<slug>/script.json`** (copy `projects/kit-demo`): `lines` as `[spoken text, pause_after]`, 85-95 words, hook first, twist or loop last.
   - Write numbers and acronyms the way they are spoken ("twenty fifteen", "M R I"), then map them to caption text with `"show": {"twenty fifteen": "2015", "m r i": "MRI"}`.
   - A word missing from the CMU dictionary needs `"pron": {"ig": "IH G"}` (align.py tells you which).
3. **`projects/<slug>/scenes.py`**: `def build(): return [Scene(...), ...]` with layers from `kit.py`. Anchor everything with `at("word")` (absolute seconds, `n=` picks the occurrence, `off=` shifts). A KeyError means the word is not in the transcript.
   - Layers: `Narrator` (poses idle/hands_up/wide/cheer/worry/point, `walk=`, `outfit="doc"|"mom"`), `Headline`, `Tag`, `BigNumber`, `Stamp`, `Burst`, `Starburst`, `Prop` (bone, trophy, any fn), `Mark` (check/cross), `QMarks`, `Crowd`, `Arrow`, `Custom(fn)` for anything bespoke.
   - Layers add their own sound cues and camera punches; scene changes get wipes (`trans="auto"`) and a whoosh; captions are automatic. Last scene should reuse the first scene's `bg` so the video loops.
4. **Draft** (`--draft`), open `out/<slug>-draft.sheet.png` (one frame per scene), fix overlaps, run the final.
5. **Verify**: transcribe the rendered mp4 and compare with the script; check `ffprobe` shows audio. Never publish without the user's approval of the shown draft.

## What the build does
| step | file | time | note |
|---|---|---|---|
| narration | `tts.py` | ~20 s | Kokoro `am_adam`, speed 1.05, one call per line so line spans are known |
| word timings | `align.py` | ~3 s | offline forced alignment (pocketsphinx), mean error ~55 ms vs ASR; replaces upload + Picsart transcribe |
| lip-sync | `lipsync.py` | <1 s | phonemes per word -> visemes (open, width, teeth), gated by the audio envelope, 25 ms lead, head nod on word onsets |
| mix | `sfx.py` | ~5 s | pluck arpeggio bed, SFX from layer cues, music ducked under voice, compressor + two-pass loudnorm -14 LUFS + limiter |
| render | `eng.py` | draft ~10 s, final ~75 s | 2 processes; final = 5 sub-frames, shutter 0.6, crf 18 |

If `align.py` ever fails: push the narration to this repo and run `picsart_media_transcribe` on the raw.githubusercontent.com URL with `language en`, `async false` and WITHOUT the `text` parameter (with it the words are spread evenly). Save as `words.json`.

## Lessons (do not relearn)
- **Lip-sync:** driving the mouth from loudness looks like a flapping jaw. Use word timings + phonemes: closed for M/B/P, teeth for F/V/S, round for O/U/W, wide for A/E; scale by the envelope and lead the audio by ~25 ms.
- **Captions** use the frame-centre time (`eng.CAPT`), otherwise motion blur ghosts two chunks together. Keep chunks <= 17 characters.
- **Audio:** the raw synth mix is ~-25 LUFS and sounds quiet; the loudnorm chain in `sfx.mix_from_cues` is required.
- **skia** returns BGRA: ffmpeg input is `-pix_fmt bgra`; reorder `[..., [2,1,0]]` for PIL.
- **Layout:** keep text clear of the caption band (y > ~1330 on a 1920 canvas); headlines at y 175-330; check the sheet for text touching screen edges (size <= ~126 for two-word headlines).
- **Elbows** must bend outward (the IK flips per arm); a hidden raised arm looks broken, use `hands_up` instead.
- Every scene needs a gesture change, camera move or entrance; a new visual every 1.5-2 s; first frame already shows the hook.

## Legacy
`examples/knuckle/` is the first hand-timed video (custom scenes, ~430 lines). Kept as a reference for `Custom` layers and bespoke props.
