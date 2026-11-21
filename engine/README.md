# Code-rendered stickman video engine (Skia + ffmpeg)

- `eng.py` easing, camera, IK stickman, fists, particles, captions, motion-blur render loop
- `scenes.py` the knuckle-cracking video (8 scenes, wipes, camera moves)
- `tts_knuckle.py` Kokoro narration (voice am_adam), `make_mix2.py` music + SFX mix
- `render_full.py` renders 2 halves in parallel, concatenates, muxes audio (~70 s for 32 s of 1080x1920 @30 fps, 5 sub-frames of blur)
- `preview.py` / `sheet_mp4.py` contact sheets for reviewing frames
- Needs: `pip install skia-python kokoro-onnx soundfile numpy pillow`, ffmpeg, Poppins-Bold.ttf, Kokoro model files.
- skia returns BGRA, so ffmpeg input is `-pix_fmt bgra`.
