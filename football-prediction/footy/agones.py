"""Read the day's OPAP "Pame Stoixima" coupon from agones.gr (personal use only).

Each row gives: the coupon CODE (the number you write on the betting slip), the
competition, the kickoff time, the two teams in Greek, and OPAP's 1 / X / 2 odds.

Like the Flashscore reader, this is for your own private use: one page per run,
nothing shared, and never used to train or test models.
"""
from __future__ import annotations

import difflib
import html as htmllib
import re
import unicodedata
import urllib.request
from datetime import date

import pandas as pd

URL = "https://agones.gr/?date={day}"

# agones.gr competition id ("ii__tour-NN") -> our division code. Checked on the coupon of 22/11/2026.
TOUR_TO_DIVISION = {8: "E0", 9: "E1", 38: "SP1", 71: "SP2", 14: "D1", 77: "D2", 15: "I1", 37: "I2",
                    13: "F1", 17: "N1", 101: "P1", 2: "B1", 30: "T1", 66: "G1"}
# Fallback by competition title, for ids we have not seen (accents and Greek/Latin letters ignored).
TITLE_TO_DIVISION = {
    "ΑΓΓΛΙΑ: ΠΡΕΜΙΕΡ ΛΙΓΚ": "E0", "ΑΓΓΛΙΑ: ΤΣΑΜΠΙΟΝΣΙΠ": "E1", "ΙΣΠΑΝΙΑ: ΛΑ ΛΙΓΚΑ": "SP1",
    "ΙΣΠΑΝΙΑ: ΣΕΓΟΥΝΤΑ ΝΤΙΒΙΖΙΟΝ": "SP2", "ΓΕΡΜΑΝΙΑ: ΜΠΟΥΝΤΕΣΛΙΓΚΑ": "D1",
    "ΓΕΡΜΑΝΙΑ: 2. ΜΠΟΥΝΤΕΣΛΙΓΚΑ": "D2", "ΙΤΑΛΙΑ: ΣΕΡΙΕ Α": "I1", "ΙΤΑΛΙΑ: ΣΕΡΙΕ Β": "I2",
    "ΓΑΛΛΙΑ: ΛΙΓΚ 1": "F1", "ΓΑΛΛΙΑ: ΛΙΓΚ 2": "F2", "ΟΛΛΑΝΔΙΑ: ΕΡΕΝΤΙΒΙΖΙΕ": "N1",
    "ΠΟΡΤΟΓΑΛΙΑ: ΛΙΓΚΑ ΠΡΟ": "P1", "ΒΕΛΓΙΟ: ΓΙΟΥΠΙΛΕΡ ΛΙΓΚ": "B1", "ΤΟΥΡΚΙΑ: ΣΟΥΠΕΡ ΛΙΓΚ": "T1",
    "ΕΛΛΑΔΑ: ΣΟΥΠΕΡ ΛΙΓΚ 1": "G1", "ΣΚΩΤΙΑ: ΠΡΕΜΙΕΡΣΙΠ": "SC0", "ΣΚΩΤΙΑ: ΤΣΑΜΠΙΟΝΣΙΠ": "SC1",
}

# Greek name -> dataset name, where the automatic matching is not enough. Add your own in
# team_aliases.csv (columns: site_name,dataset).
GREEK_ALIASES = {
    "Μάντσεστερ Γιουνάιτεντ": "Man United", "Μάντσεστερ Σίτι": "Man City", "Νότιγχαμ Φόρεστ": "Nott'm Forest",
    "Ατλέτικο Μαδρίτης": "Ath Madrid", "Αθλέτικ Μπιλμπάο": "Ath Bilbao", "Ρεάλ Σοσιεδάδ": "Sociedad",
    "Ράγιο Βαγιεκάνο": "Vallecano", "Σπόρτινγκ Λισαβόνας": "Sp Lisbon", "Μπράγκα": "Sp Braga",
    "Άιντραχτ Φρανκφούρτης": "Ein Frankfurt", "Γκλάντμπαχ": "M'gladbach", "Μπορούσια Μένχενγκλαντμπαχ": "M'gladbach",
    "Παρί Σεν Ζερμέν": "Paris SG", "Ολυμπιακός": "Olympiakos", "ΑΕΚ": "AEK", "ΠΑΟΚ": "PAOK", "ΟΦΗ": "OFI Crete",
    "Βόλος": "Volos NFC", "Ηρακλής": "Iraklis",
}

# Expanded spellings of the dataset's short names, so they sound like the Greek ones.
DATASET_LONG_NAMES = {
    "Man United": "manchester united", "Man City": "manchester city", "Nott'm Forest": "nottingham forest",
    "Ath Madrid": "atletico madrid", "Ath Bilbao": "athletic bilbao", "Sp Lisbon": "sporting lisbon",
    "Sp Braga": "braga", "Ein Frankfurt": "eintracht frankfurt", "M'gladbach": "monchengladbach",
    "Sociedad": "real sociedad", "Vallecano": "rayo vallecano", "Espanol": "espanyol",
    "Paris SG": "paris saint germain", "Sheffield Weds": "sheffield wednesday", "QPR": "queens park rangers",
    "West Brom": "west bromwich", "Wolves": "wolverhampton",
}

_DIGRAPHS_START = [("μπ", "b"), ("ντ", "d"), ("γκ", "g")]
_DIGRAPHS = [("μπ", "mb"), ("ντ", "nd"), ("γκ", "ng"), ("γγ", "ng"), ("ου", "u"), ("αι", "e"), ("ει", "i"),
             ("οι", "i"), ("αυ", "av"), ("ευ", "ev"), ("τσ", "ts"), ("τζ", "tz")]
_LETTERS = dict(zip("αβγδεζηθικλμνξοπρσςτυφχψω",
                    ["a", "v", "g", "d", "e", "z", "i", "th", "i", "k", "l", "m", "n", "x", "o", "p", "r",
                     "s", "s", "t", "i", "f", "h", "ps", "o"]))


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def greek_to_latin(name: str) -> str:
    """Rough phonetic Greek -> Latin, e.g. 'Λίβερπουλ' -> 'liverpul'."""
    out = []
    name = name.lower()
    # An accent on the first vowel (ά-ι) or a diaeresis (α-ϊ) means two separate sounds, not a digraph.
    name = re.sub(r"([άέόή])([ιυ])", r"\1|\2", name)
    name = re.sub(r"([αεοη])([ϊϋΐΰ])", r"\1|\2", name)
    for word in _strip_accents(name).split():
        for g, l in _DIGRAPHS_START:
            if word.startswith(g):
                word = l + word[2:]
        for g, l in _DIGRAPHS:
            word = word.replace(g, l)
        out.append("".join(_LETTERS.get(c, c) for c in word).replace("|", ""))
    return " ".join(out)


def sound_key(latin: str) -> str:
    """Reduce a Latin spelling to how it sounds, so 'liverpool' and 'liverpul' agree."""
    s = _strip_accents(latin.lower())
    s = re.sub(r"[^a-z ]", "", s)
    for a, b in [("ch", "ts"), ("sch", "s"), ("ph", "f"), ("th", "t"), ("ck", "k"), ("c", "k"), ("q", "k"),
                 ("w", "u"), ("y", "i"), ("j", "z"), ("v", "b"), ("oo", "u"), ("ou", "u"), ("h", "")]:
        s = s.replace(a, b)
    s = re.sub(r"[aeiou]", "", s)                 # vowels vary most between languages
    return re.sub(r"(.)\1+", r"\1", s).strip()


def name_similarity(greek: str, latin_names: list[str]) -> float:
    """How alike a Greek team name sounds to any of the given Latin spellings (0..1)."""
    g = greek_to_latin(greek)
    best = 0.0
    for name in latin_names:
        if not name:
            continue
        for a, b in [(sound_key(g), sound_key(name)), (g, name.lower())]:
            best = max(best, difflib.SequenceMatcher(None, a, b).ratio())
    return best


def link_to_fixtures(coupon: pd.DataFrame, fixtures: pd.DataFrame, aliases: dict | None = None) -> dict:
    """Pair each coupon match with one known fixture of the SAME league and (about) the same day.

    Matching home+away together among the few games of one league on one day is far safer
    than guessing single names. `fixtures` needs Division, MatchDate, HomeTeam, AwayTeam
    (dataset names) and may have FlashscoreHome/FlashscoreAway. Returns {coupon index: fixture index}.
    Matches with no clear partner are left out rather than guessed.
    """
    aliases = {**GREEK_ALIASES, **(aliases or {})}
    links = {}
    for i, c in coupon.iterrows():
        pool = fixtures[(fixtures.Division == c.division) &
                        ((pd.to_datetime(fixtures.MatchDate) - pd.Timestamp(c.day)).abs() <= pd.Timedelta(days=1))]
        scores = []
        for j, f in pool.iterrows():
            def side(greek, team, fs_name):
                if aliases.get(greek.strip()) == team:
                    return 1.0
                return name_similarity(greek, [team, DATASET_LONG_NAMES.get(team, ""), fs_name or ""])
            scores.append((side(c.home_gr, f.HomeTeam, f.get("FlashscoreHome")) +
                           side(c.away_gr, f.AwayTeam, f.get("FlashscoreAway")), j))
        scores.sort(reverse=True)
        if scores and scores[0][0] >= 1.0 and (len(scores) == 1 or scores[0][0] - scores[1][0] >= 0.25):
            links[i] = scores[0][1]
    return links


def _division(tour_id: int, title: str) -> str | None:
    if tour_id in TOUR_TO_DIVISION:
        return TOUR_TO_DIVISION[tour_id]
    t = _strip_accents(title).upper().replace("A", "Α").replace("B", "Β")
    return TITLE_TO_DIVISION.get(" ".join(t.split()))


def _float(text):
    try:
        v = float(text.strip())
        return v if v > 1 else None
    except ValueError:
        return None


ROW_RE = re.compile(r'<tr class="([^"]*\bii__match_row\b[^"]*)"(.*?)</tr>', re.S)


def parse_coupon(page_html: str) -> pd.DataFrame:
    """One row per match on the page."""
    rows = []
    for cls, body in ROW_RE.findall(page_html):
        tour = re.search(r"ii__tour-(\d+)", cls)
        state = re.search(r"ii__match_state_(\d+)", cls)
        title = re.search(r'title="([^"]+)" class="flag', body)
        time_ = re.search(r'ii__localtime">\s*([^<]*)<', body)
        code = re.search(r'href="https://agones\.gr/livescore/[^"]+">\s*([^<]*?)\s*</a>', body)
        teams = re.findall(r'table--matches__team_row">.*?<span>([^<]+)</span>', body, re.S)
        odds = {v: _float(t) for v, t in re.findall(r'data-vote="([1X2])"[^>]*>\s*([^<]*?)\s*</button>', body)}
        if len(teams) != 2:
            continue
        rows.append({
            "code": code.group(1) if code and code.group(1).isdigit() else None,
            "competition": htmllib.unescape(title.group(1)) if title else "",
            "tour_id": int(tour.group(1)) if tour else None,
            "time": time_.group(1).strip() if time_ else "",
            "home_gr": htmllib.unescape(teams[0]).strip(), "away_gr": htmllib.unescape(teams[1]).strip(),
            "odd_1": odds.get("1"), "odd_X": odds.get("X"), "odd_2": odds.get("2"),
            "state": int(state.group(1)) if state else None,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["division"] = [_division(t, c) for t, c in zip(df.tour_id, df.competition)]
    return df


def fetch(day: date) -> str:
    """Download the coupon page; falls back to a real browser if the plain download has no rows."""
    req = urllib.request.Request(URL.format(day=day.isoformat()),
                                 headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "el,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", errors="replace")
    if ROW_RE.search(page):
        return page
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return page
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(locale="el-GR")
        pg.goto(URL.format(day=day.isoformat()), wait_until="domcontentloaded", timeout=45000)
        pg.wait_for_selector("tr.ii__match_row", timeout=20000)
        page = pg.content()
        browser.close()
    return page
