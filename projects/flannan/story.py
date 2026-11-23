"""Flannan Isles short: storyboard anchored to the spoken words (shared by audio.py and build_scene.py)."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, "words.json")))
TOTAL = 53.9          # narration ends 53.06; hold + fade

_n = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def at(word, n=0, end=False, off=0.0):
    hits = 0
    for w in WORDS:
        if _n(w[0]) == _n(word) or _n(w[0].split()[0]) == _n(word):
            if hits == n:
                return (w[2] if end else w[1]) + off
            hits += 1
    raise KeyError(word)


PX = "https://videos.pexels.com/video-files/"
CLIPS = {   # key: (url, duration, credit)
    "LH":     (PX + "19936883/19936883-uhd_1440_2560_60fps.mp4", 10.68, "kemal can acartürk"),
    "CLIFF":  (PX + "30810366/13177802_2560_1440_32fps.mp4", 11.02, "Eren Ataselim"),
    "SURF":   (PX + "31310225/13367416_2560_1440_30fps.mp4", 27.29, "Gylfi Gylfason"),
    "PIER":   (PX + "26885382/12025994_2560_1440_25fps.mp4", 7.88, "Aswin R S"),
    "HALL":   (PX + "19205536/19205536-uhd_2560_1440_30fps.mp4", 10.01, "Nino Souza"),
    "CANDLE": (PX + "3138263/3138263-hd_1920_1080_30fps.mp4", 47.07, "Pabitra Sarkar"),
    "BOOK":   (PX + "11384843/11384843-hd_1080_1920_25fps.mp4", 15.02, "Sahil Sharma"),
    "BOOK2":  (PX + "11530072/11530072-uhd_2560_1440_25fps.mp4", 11.56, "Attila Pergel"),
    "SLOW":   (PX + "2053565/2053565-hd_1920_1080_24fps.mp4", 12.48, "Elia Clerici"),
    "BOAT":   (PX + "19280144/19280144-uhd_1440_2730_30fps.mp4", 20.07, "Atahan Demir"),
}

# (start time, clip, in-point seconds, grade)  grade: 'dark' | 'cold' | 'warm'
SHOTS = [
    (0.00,                    "LH",     0.0, "cold"),
    (at("Three", off=-0.10),  "CLIFF",  1.0, "cold"),
    (at("Scottish", off=-0.10), "SURF", 2.0, "cold"),
    (at("story", off=-0.10),  "LH",     5.0, "dark"),
    (at("Fake.", off=-0.12),  "SURF",  14.0, "dark"),
    (at("11", off=-0.10),     "BOAT",   0.5, "cold"),
    (at("Nobody's", off=-0.10), "PIER", 0.5, "cold"),
    (at("door", off=-0.12),   "HALL",   0.0, "dark"),
    (at("beds", off=-0.10),   "CANDLE", 3.0, "warm"),
    (at("Two", off=-0.10),    "BOAT",   8.0, "dark"),
    (at("One", off=-0.10),    "HALL",   6.0, "dark"),
    (at("No", 0, off=-0.10),  "CANDLE", 20.0, "warm"),
    (at("No", 1, off=-0.10),  "HALL",   2.0, "dark"),
    (at("Those", off=-0.10),  "BOOK2",  1.0, "warm"),
    (at("12", off=-0.10),     "BOOK",   2.0, "warm"),
    (at("famous", off=-0.12), "BOOK2",  6.0, "warm"),
    (at("praying,", off=-0.10), "CANDLE", 35.0, "warm"),
    (at("First", off=-0.10),  "BOOK",   9.0, "warm"),
    (at("Fiction.", off=-0.10), "SURF", 20.0, "dark"),
    (at("But", off=-0.10),    "SURF",   5.0, "cold"),
    (at("A", 3, off=-0.10),   "SLOW",   1.5, "cold"),
    (at("Damage", off=-0.10), "CLIFF",  3.0, "cold"),
    (at("Best", off=-0.10),   "SURF",  15.0, "cold"),
    (at("freak", off=-0.12),  "SURF",  18.0, "dark"),
    (at("Their", off=-0.12),  "BOAT",  12.0, "dark"),
    (at("legend", off=-0.10), "LH",     5.5, "dark"),
]
CUTS = [s[0] for s in SHOTS[1:]]
