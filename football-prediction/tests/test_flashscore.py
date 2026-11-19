"""Flashscore reader tests. No internet: we use small hand-written HTML with the same
structure as Flashscore's pages, so these tests break only if OUR code breaks."""
from datetime import date

import pandas as pd
import pytest

from footy import flashscore as fs

TODAY = date(2026, 11, 19)


def test_odds_url():
    url = "https://www.flashscore.com/match/football/aek-ANpZncAM/kalamata-4vN7O8j0/?mid=Khzsze2n"
    assert fs.odds_url(url) == ("https://www.flashscore.com/match/football/aek-ANpZncAM/kalamata-4vN7O8j0/"
                                "odds/1x2-odds/full-time/?mid=Khzsze2n")


def test_dates_without_year():
    assert fs.parse_list_date("21.11. 19:30", TODAY, past=False) == pd.Timestamp("2026-11-21")
    assert fs.parse_list_date("03.01. 15:00", TODAY, past=False) == pd.Timestamp("2027-01-03")
    assert fs.parse_list_date("08.11. 14:00", TODAY, past=True) == pd.Timestamp("2026-11-08")
    assert fs.parse_list_date("20.12. 14:00", TODAY, past=True) == pd.Timestamp("2025-12-20")
    assert fs.parse_start_time("21.11.2026 19:30") == pd.Timestamp("2026-11-21")
    assert fs.parse_list_date("Postponed", TODAY, past=False) is None


def test_choose_bookmaker():
    rows = [{"bookmaker": "bet365", "odds": ["8.00", "4.75", "1.33"]},
            {"bookmaker": "Novibet", "odds": ["-", "4.90", "1.38"]},
            {"bookmaker": "Stoiximan.gr", "odds": ["8.25", "5.00", "1.37"]}]
    assert fs.choose_bookmaker(rows, "stoiximan") == ("Stoiximan.gr", [8.25, 5.0, 1.37])
    assert fs.choose_bookmaker(rows, "Novibet") == ("bet365", [8.0, 4.75, 1.33])   # incomplete -> fallback
    assert fs.choose_bookmaker([], "x") is None


@pytest.mark.parametrize("flashscore,expected", [
    ("Olympiacos Piraeus", "Olympiakos"), ("AEK Athens", "AEK"), ("PAOK", "PAOK"),
    ("Levadiakos", "Levadeiakos"), ("Volos", "Volos NFC"), ("OFI Crete", "OFI Crete"),
    ("Manchester Utd", "Man United"), ("Nottingham", "Nott'm Forest"), ("Bayern Munich", "Bayern Munich"),
    ("B. Monchengladbach", "MGladbach"),     # alias target spelled differently in the dataset
])
def test_team_matching(flashscore, expected):
    known = ["AEK", "Olympiakos", "Olympiakos Volou", "PAOK", "Levadeiakos", "Volos NFC", "Niki Volos",
             "OFI", "OFI Crete", "Man United", "Man City", "Nott'm Forest", "Bayern Munich", "MGladbach"]
    assert fs.match_team(flashscore, known, fs.load_aliases()) == expected


def test_unknown_team_is_not_guessed():
    assert fs.match_team("Totally Different FC", ["AEK", "PAOK"], {}) is None


def test_rows_to_fixture_table_skips_old_results_and_reports_unknowns():
    history = pd.DataFrame({"HomeTeam": ["AEK", "PAOK"], "AwayTeam": ["PAOK", "AEK"],
                            "MatchDate": pd.to_datetime(["2026-08-30", "2026-09-03"]), "Season": [2026, 2026]})
    results = [{"time": "08.11. 14:00", "home": "AEK Athens", "away": "PAOK", "home_score": "2", "away_score": "1"},
               {"time": "01.09. 14:00", "home": "AEK Athens", "away": "PAOK", "home_score": "0", "away_score": "0"},
               {"time": "09.11. 14:00", "home": "AEK Athens", "away": "PAOK", "home_score": "-", "away_score": "-"}]
    upcoming = [{"time": "22.11. 19:30", "home": "PAOK", "away": "AEK Athens", "start": None, "url": "u",
                 "bookmaker": "Stoiximan.gr", "odds": [2.1, 3.2, 3.5]},
                {"time": "22.11. 19:30", "home": "Mystery FC", "away": "PAOK", "start": None, "url": "u"}]
    t, unknown = fs.rows_to_fixture_table("G1", results, upcoming, history, fs.load_aliases(), TODAY)
    assert unknown == ["Mystery FC"]
    assert len(t) == 2                                       # 1 new result + 1 matched fixture
    assert t.iloc[0][["HomeTeam", "FTHome", "FTAway"]].tolist() == ["AEK", 2, 1]
    assert t.iloc[1][["HomeTeam", "AwayTeam", "OddHome", "Bookmaker"]].tolist() == ["PAOK", "AEK", 2.1, "Stoiximan.gr"]


LIST_HTML = """
<div class="event__match event__match--scheduled" id="g_1_abc">
  <a class="eventRowLink" href="https://www.flashscore.com/match/football/a-1/b-2/?mid=abc"></a>
  <span class="event__stageTime">21.11. 19:30</span>
  <div class="event__homeParticipant"><span>Kalamata</span></div>
  <div class="event__awayParticipant"><span>AEK Athens</span></div>
  <span class="event__score event__score--home">-</span><span class="event__score event__score--away">-</span>
</div>
<div class="event__match" id="g_1_def">
  <a class="eventRowLink" href="https://www.flashscore.com/match/football/c-3/d-4/?mid=def"></a>
  <span class="event__stageTime">08.11. 14:00</span>
  <div class="event__homeParticipant"><span>Olympiacos Piraeus</span></div>
  <div class="event__awayParticipant"><span>PAOK</span></div>
  <span class="event__score event__score--home">1</span><span class="event__score event__score--away">1</span>
</div>"""
ODDS_HTML = """
<div class="duelParticipant__startTime"><div>21.11.2026 19:30</div></div>
<div class="ui-table__row"><div class="oddsCell__bookmakerPart"><a title="bet365"><img alt="bet365"></a></div>
  <a class="oddsCell__odd"><span>8.00</span></a><a class="oddsCell__odd"><span>4.75</span></a>
  <a class="oddsCell__odd"><span>1.33</span></a></div>
<div class="ui-table__row"><div class="oddsCell__bookmakerPart"><a title="Stoiximan.gr"><img alt="Stoiximan"></a></div>
  <a class="oddsCell__odd"><span>8.25</span></a><a class="oddsCell__odd"><span>5.00</span></a>
  <a class="oddsCell__odd"><span>1.37</span></a></div>"""


@pytest.fixture(scope="module")
def page():
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch()
    except Exception as e:  # browser not installed
        pytest.skip(f"Chromium for Playwright not available: {e}")
    yield browser.new_page()
    browser.close()
    pw.stop()


def test_page_extraction_javascript(page):
    page.set_content(LIST_HTML)
    rows = page.evaluate(fs.FIXTURES_JS)
    assert [r["scheduled"] for r in rows] == [True, False]
    assert rows[0]["home"].strip() == "Kalamata" and rows[0]["away"].strip() == "AEK Athens"
    assert rows[0]["time"] == "21.11. 19:30" and rows[0]["url"].endswith("?mid=abc")
    assert (rows[1]["home_score"], rows[1]["away_score"]) == ("1", "1")
    page.set_content(ODDS_HTML)
    odds = page.evaluate(fs.ODDS_JS)
    assert odds["start"].strip() == "21.11.2026 19:30"
    assert fs.choose_bookmaker(odds["rows"], "Stoiximan") == ("Stoiximan.gr", [8.25, 5.0, 1.37])


def test_team_news_summary():
    page = {"groups": [{"group": "Predicted lineups", "home": [{"name": "X", "note": ""}], "away": []},
                       {"group": "Will not play", "home": [{"name": "Vargas K.", "note": "Muscle Injury"}],
                        "away": [{"name": "Marin R.", "note": "Red Card"}, {"name": "Zubkov O.", "note": "Broken Leg"}]},
                       {"group": "Questionable", "home": [], "away": [{"name": "Alexiou C.", "note": "Injury"}]}],
            "ratings": ["6.6", "7.2"]}
    n = fs.team_news(page)
    assert n["lineup_status"] == "predicted"
    assert n["home_out"] == [("Vargas K.", "Muscle Injury")] and len(n["away_out"]) == 2
    assert n["away_doubtful"] == [("Alexiou C.", "Injury")]
    assert (n["home_xi_rating"], n["away_xi_rating"]) == (6.6, 7.2)
    assert fs.team_news({"groups": [], "ratings": []})["lineup_status"] == "none"
    assert fs.lineups_url("https://x/match/football/a/b/?mid=1") == "https://x/match/football/a/b/summary/lineups/?mid=1"
