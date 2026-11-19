"""Read upcoming fixtures, bookmaker odds and recent results from Flashscore.

PERSONAL USE ONLY. Flashscore's terms of use allow personal use and do not allow
scraping. You asked for this for your own private research, so:
  * it reads only a few pages, slowly (a pause of a few seconds between pages);
  * nothing it collects is saved in git or shared (data/ and outputs/ are git-ignored);
  * its data is used ONLY for upcoming-match predictions, never to train or test models
    (training uses the openly licensed datasets, see DATA_LICENSE.md).
If Flashscore changes its website, this module will stop working until it is updated.

Setup, once:    python -m playwright install chromium
Run:            python -m footy.flashscore --leagues G1 E0 --bookmaker Stoiximan
Then:           python -m footy.upcoming outputs/flashscore_fixtures.csv

Which bookmakers appear depends on the country you are in. In Greece, Flashscore
lists Stoiximan.gr, Novibet, bet365 and others; elsewhere you will see local ones.
"""
from __future__ import annotations

import argparse
import difflib
import random
import re
import sys
import time
import unicodedata
from datetime import date, datetime
from urllib.parse import urlsplit

import pandas as pd

from footy import config, data

BASE = "https://www.flashscore.com/football/"
LEAGUE_PATHS = {
    "E0": "england/premier-league", "E1": "england/championship",
    "SP1": "spain/laliga", "SP2": "spain/laliga2",
    "D1": "germany/bundesliga", "D2": "germany/2-bundesliga",
    "I1": "italy/serie-a", "I2": "italy/serie-b",
    "F1": "france/ligue-1", "F2": "france/ligue-2",
    "N1": "netherlands/eredivisie", "P1": "portugal/liga-portugal",
    "B1": "belgium/jupiler-pro-league", "T1": "turkey/super-lig",
    "G1": "greece/super-league",
    "SC0": "scotland/premiership", "SC1": "scotland/championship",
}

# Flashscore name -> dataset name, for names too different for the automatic matcher.
# You can add your own in team_aliases.csv (columns: flashscore,dataset).
BUILT_IN_ALIASES = {
    "Olympiacos Piraeus": "Olympiakos", "Levadiakos": "Levadeiakos", "Volos": "Volos NFC",
    "Larissa": "Larisa", "Iraklis 1908": "Iraklis",
    "Manchester City": "Man City", "Manchester Utd": "Man United", "Nottingham": "Nott'm Forest",
    "Sheffield Utd": "Sheffield United", "Sheffield Wed": "Sheffield Weds",
    "Atl. Madrid": "Ath Madrid", "Ath Bilbao": "Ath Bilbao", "Athletic Bilbao": "Ath Bilbao",
    "Espanyol": "Espanol", "Real Sociedad": "Sociedad", "Rayo Vallecano": "Vallecano",
    "Celta Vigo": "Celta", "Eintracht Frankfurt": "Ein Frankfurt", "B. Monchengladbach": "M'gladbach",
    "Bayer Leverkusen": "Leverkusen", "Hamburger SV": "Hamburg", "AC Milan": "Milan", "AS Roma": "Roma",
    "Hellas Verona": "Verona", "PSG": "Paris SG", "Sporting CP": "Sp Lisbon", "Sporting Lisbon": "Sp Lisbon",
    "FC Porto": "Porto", "Braga": "Sp Braga", "SC Braga": "Sp Braga", "PSV": "PSV Eindhoven",
}
ALIAS_FILE = config.PROJECT_ROOT / "team_aliases.csv"
NOISE_WORDS = {"fc", "cf", "ac", "as", "sc", "afc", "sv", "fk", "ssc", "cd", "ud", "rc", "club", "de"}

# JavaScript run inside the page: pick the data out of the rendered HTML.
FIXTURES_JS = """() => Array.from(document.querySelectorAll('.event__match')).map(r => ({
    id: r.id,
    scheduled: r.classList.contains('event__match--scheduled'),
    time: (r.querySelector('.event__stageTime, .event__time') || {}).innerText || '',
    home: (r.querySelector('.event__homeParticipant') || {}).innerText || '',
    away: (r.querySelector('.event__awayParticipant') || {}).innerText || '',
    home_score: (r.querySelector('.event__score--home') || {}).innerText || '',
    away_score: (r.querySelector('.event__score--away') || {}).innerText || '',
    url: (r.querySelector('a.eventRowLink') || r.querySelector('a[href*="/match/"]') || {}).href || ''
}))"""
ODDS_JS = """() => ({
    start: (document.querySelector('.duelParticipant__startTime') || {}).innerText || '',
    rows: Array.from(document.querySelectorAll('.ui-table__row')).map(r => {
        const part = r.querySelector('.oddsCell__bookmakerPart');
        const link = part && part.querySelector('a[title]');
        const img = part && part.querySelector('img[alt]');
        return {bookmaker: (link && link.title) || (img && img.alt) || '',
                odds: Array.from(r.querySelectorAll('.oddsCell__odd')).map(c => c.innerText.trim())};
    })
})"""


# ---------------------------------------------------------------------------------
# Pure helpers (no browser needed; covered by tests/test_flashscore.py)
# ---------------------------------------------------------------------------------
def odds_url(match_url: str) -> str:
    """.../match/football/a-x/b-y/?mid=ID  ->  .../match/football/a-x/b-y/odds/1x2-odds/full-time/?mid=ID"""
    parts = urlsplit(match_url)
    path = parts.path if parts.path.endswith("/") else parts.path + "/"
    return f"{parts.scheme}://{parts.netloc}{path}odds/1x2-odds/full-time/" + (f"?{parts.query}" if parts.query else "")


def parse_list_date(text: str, today: date, past: bool) -> pd.Timestamp | None:
    """'21.11. 12:30' has no year. Upcoming matches are on/after today, results on/before it."""
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(?:(\d{4}))?", text or "")
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
    if y:
        return pd.Timestamp(int(y), mo, d)
    for year in (today.year - 1, today.year, today.year + 1):
        when = date(year, mo, d)
        if (past and 0 <= (today - when).days < 366) or (not past and 0 <= (when - today).days < 366):
            return pd.Timestamp(when)
    return None


def parse_start_time(text: str) -> pd.Timestamp | None:
    """Match page shows the full date: '21.11.2026 19:30'."""
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text or "")
    return pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def to_float(text):
    try:
        v = float(str(text).strip())
        return v if v > 1.0 else None
    except ValueError:
        return None


def choose_bookmaker(rows: list[dict], preferred: str | None) -> tuple[str, list[float]] | None:
    """Prefer the bookmaker whose name contains `preferred` (case-insensitive), else the first complete row."""
    complete = []
    for r in rows:
        odds = [to_float(o) for o in r.get("odds", [])[:3]]
        if len(odds) == 3 and all(odds):
            complete.append((r.get("bookmaker", "").strip(), odds))
    if not complete:
        return None
    if preferred:
        for name, odds in complete:
            if preferred.lower() in name.lower():
                return name, odds
    return complete[0]


def _norm(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    words = re.sub(r"[^a-z0-9 ]", " ", name).split()
    return " ".join(w for w in words if w not in NOISE_WORDS and not w.isdigit())


def load_aliases(path=ALIAS_FILE) -> dict:
    aliases = dict(BUILT_IN_ALIASES)
    if path.exists():
        user = pd.read_csv(path)
        aliases.update(dict(zip(user.flashscore.str.strip(), user.dataset.str.strip())))
    return aliases


def match_team(name: str, known: list[str], aliases: dict, preferred: list[str] | None = None) -> str | None:
    """Find the dataset's name for a Flashscore team name, or None if unsure.
    `preferred` = teams seen recently in this league (checked first, to avoid old namesakes)."""
    name = name.strip()
    for pool in ([preferred] if preferred else []) + [known]:
        if name in pool:
            return name
        if aliases.get(name) in pool:
            return aliases[name]
        target = _norm(name)
        normed = {k: _norm(k) for k in pool}
        exact = [k for k, v in normed.items() if v == target]
        if len(exact) == 1:
            return exact[0]
        t_words = set(target.split())
        contains = [k for k, v in normed.items() if v and (set(v.split()) <= t_words or t_words <= set(v.split()))]
        if len(contains) == 1:
            return contains[0]
        scored = sorted(((difflib.SequenceMatcher(None, target, v).ratio(), k) for k, v in normed.items()), reverse=True)
        if scored and scored[0][0] >= 0.8 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.05):
            return scored[0][1]
    return None


def rows_to_fixture_table(division, results, upcoming, history, aliases, today) -> tuple[pd.DataFrame, list[str]]:
    """Turn scraped rows into the CSV format footy.upcoming reads. Returns (table, unmatched names)."""
    known = sorted(set(history.HomeTeam) | set(history.AwayTeam))
    recent = history[history.Season >= history.Season.max() - 1]
    preferred = sorted(set(recent.HomeTeam) | set(recent.AwayTeam))
    unmatched, out = set(), []
    last_known = history.MatchDate.max()

    def team(n):
        t = match_team(n, known, aliases, preferred)
        if t is None:
            unmatched.add(n.strip())
        return t

    for r in results:
        when = parse_list_date(r["time"], today, past=True)
        hs, as_ = r.get("home_score", "").strip(), r.get("away_score", "").strip()
        if when is None or when <= last_known or not (hs.isdigit() and as_.isdigit()):
            continue                      # already in the dataset, or not a finished match
        h, a = team(r["home"]), team(r["away"])
        if h and a:
            out.append({"Division": division, "MatchDate": when.date(), "HomeTeam": h, "AwayTeam": a,
                        "FTHome": int(hs), "FTAway": int(as_), "Source": "Flashscore result"})
    for r in upcoming:
        when = r.get("start") or parse_list_date(r["time"], today, past=False)
        h, a = team(r["home"]), team(r["away"])
        if when is None or not (h and a):
            continue
        row = {"Division": division, "MatchDate": pd.Timestamp(when).date(), "HomeTeam": h, "AwayTeam": a,
               "Source": "Flashscore fixture", "FlashscoreURL": r.get("url", ""),
               "FlashscoreHome": r["home"].strip(), "FlashscoreAway": r["away"].strip()}
        if r.get("bookmaker"):
            row.update(Bookmaker=r["bookmaker"], OddHome=r["odds"][0], OddDraw=r["odds"][1], OddAway=r["odds"][2])
        out.append(row)
    return pd.DataFrame(out), sorted(unmatched)


# ---------------------------------------------------------------------------------
# Browser part (needs internet and: python -m playwright install chromium)
# ---------------------------------------------------------------------------------
class Reader:
    def __init__(self, headless=True, min_pause=2.0, max_pause=4.0):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            sys.exit("Playwright is not installed. Run:  pip install -r requirements.txt\n"
                     "and then once:  python -m playwright install chromium")
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=headless)
        self.page = self.browser.new_page(locale="en-GB")
        self.min_pause, self.max_pause = min_pause, max_pause
        self._consent_done = False

    def close(self):
        self.browser.close()
        self._pw.stop()

    def _open(self, url, wait_for, timeout=15000):
        time.sleep(random.uniform(self.min_pause, self.max_pause))   # be gentle with the website
        self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if not self._consent_done:
            try:   # cookie banner
                self.page.click("#onetrust-accept-btn-handler", timeout=4000)
            except Exception:
                pass
            self._consent_done = True
        try:
            self.page.wait_for_selector(wait_for, timeout=timeout)
            return True
        except Exception:
            return False

    def list_page(self, division, kind, show_more=0):
        """kind = 'fixtures' or 'results'. show_more = how often to click 'Show more matches'."""
        url = f"{BASE}{LEAGUE_PATHS[division]}/{kind}/"
        if not self._open(url, ".event__match"):
            return []
        for _ in range(show_more):
            try:
                self.page.get_by_text("Show more matches").first.click(timeout=3000)
                self.page.wait_for_timeout(2500)
            except Exception:
                break
        return self.page.evaluate(FIXTURES_JS)

    def odds(self, match_url):
        if not self._open(odds_url(match_url), ".ui-table__row", timeout=10000):
            return {"start": self.page.evaluate(ODDS_JS)["start"], "rows": []}
        return self.page.evaluate(ODDS_JS)


def collect(divisions, bookmaker=None, max_matches=20, days_ahead=10, headless=True, today=None):
    today = today or date.today()
    raw = data.load_raw()
    aliases = load_aliases()
    reader = Reader(headless=headless)
    tables, problems = [], []
    try:
        for div in divisions:
            if div not in LEAGUE_PATHS:
                problems.append(f"{div}: no Flashscore page configured (see LEAGUE_PATHS)")
                continue
            print(f"[{div}] reading results and fixtures...")
            history = data.clean(raw, [div])
            gap_days = (pd.Timestamp(today) - history.MatchDate.max()).days
            results = reader.list_page(div, "results", show_more=min(6, gap_days // 21))
            fixtures = [r for r in reader.list_page(div, "fixtures") if r["scheduled"]]
            upcoming = []
            for r in fixtures:
                when = parse_list_date(r["time"], today, past=False)
                if when is None or (when.date() - today).days > days_ahead or len(upcoming) >= max_matches:
                    continue
                print(f"    odds: {r['home'].strip()} - {r['away'].strip()}")
                o = reader.odds(r["url"])
                pick = choose_bookmaker(o["rows"], bookmaker)
                r = dict(r, start=parse_start_time(o["start"]))
                if pick:
                    r.update(bookmaker=pick[0], odds=pick[1])
                upcoming.append(r)
            table, unmatched = rows_to_fixture_table(div, results, upcoming, history, aliases, today)
            if unmatched:
                problems.append(f"{div}: could not match {unmatched} - add them to team_aliases.csv")
            print(f"    {int(table.get('FTHome', pd.Series(dtype=float)).notna().sum())} new results, "
                  f"{int(table.get('FTHome', pd.Series(dtype=float)).isna().sum()) if len(table) else 0} upcoming")
            tables.append(table)
    finally:
        reader.close()
    out = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    return out, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--leagues", nargs="+", default=["G1"], help="league codes, e.g. G1 E0 (default: G1)")
    parser.add_argument("--bookmaker", default="Stoiximan", help="preferred bookmaker name (default: Stoiximan)")
    parser.add_argument("--max-matches", type=int, default=20, help="max upcoming matches per league (default 20)")
    parser.add_argument("--days-ahead", type=int, default=10, help="only matches in the next N days (default 10)")
    parser.add_argument("--show-browser", action="store_true", help="watch the browser work")
    parser.add_argument("--out", default=str(config.OUTPUT_DIR / "flashscore_fixtures.csv"))
    args = parser.parse_args()

    print("Personal use only: reading Flashscore slowly, a few pages at a time.")
    table, problems = collect(args.leagues, args.bookmaker, args.max_matches, args.days_ahead,
                              headless=not args.show_browser)
    for p in problems:
        print("WARNING:", p)
    if table.empty:
        sys.exit("Nothing collected. Flashscore may have changed its layout, or no matches were found.")
    other = table.Bookmaker.dropna().unique() if "Bookmaker" in table else []
    if args.bookmaker and len(other) and not any(args.bookmaker.lower() in b.lower() for b in other):
        print(f"NOTE: '{args.bookmaker}' was not listed on Flashscore from your location; "
              f"used {', '.join(other)} instead.")
    from pathlib import Path
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)
    print(f"Saved {args.out} at {datetime.now():%H:%M}.  Next:  python -m footy.upcoming {args.out}")


if __name__ == "__main__":
    main()
