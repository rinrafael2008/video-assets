"""agones.gr coupon reading, Greek-name linking and the "what to play today" verdicts.
No internet: hand-written HTML in agones.gr's row format and synthetic leagues."""
import json
from datetime import date

import pandas as pd

from footy import agones as ag
from footy import today

ROW = """<tr class="ii__match_state_1 ii__match_row ii__tour-{tour} ii__match_row_1{code} ii__has_odds table-new__item" data-mid="1{code}">
<td class="ii__fav_star"></td><td><a href="#"><img src="x" title="{title}" class="flag radius2"></a></td>
<td class="ii__localtime">19:30</td><td><a href="https://agones.gr/livescore/1-2/a-b">{code}</a></td>
<td><a href="https://agones.gr/livescore/1-2/a-b" class="table--matches__teams">
<div class="table--matches__team_row"><img alt="x"><span>{home}</span></div>
<div class="table--matches__team_row"><img alt="x"><span>{away}</span></div></a></td>
<td><button data-vote="1" class="btn"> {o1} </button></td><td><button data-vote="X" class="btn"> {ox} </button></td>
<td><button data-vote="2" class="btn"> {o2} </button></td></tr>"""


def test_parse_coupon():
    page = (ROW.format(tour=66, code=714, title="ΕΛΛΑΔΑ: Σούπερ Λιγκ 1", home="ΠΑΟΚ", away="Κηφισιά",
                       o1="1.38", ox="4.75", o2="7.50") +
            ROW.format(tour=999, code=623, title="ΙΑΠΩΝΙΑ: J. Λιγκ 2", home="Α", away="Β", o1="2.60", ox="3.10", o2="2.52") +
            ROW.format(tour=998, code=701, title="ΓΑΛΛΙΑ: Λιγκ 2", home="Γ", away="Δ", o1="2", ox="3", o2="4"))
    c = ag.parse_coupon(page)
    assert c.code.tolist() == ["714", "623", "701"]
    assert c.division.tolist()[0] == "G1" and pd.isna(c.division.tolist()[1])
    assert c.division.tolist()[2] == "F2"                       # found by title when the id is unknown
    assert c.iloc[0][["home_gr", "away_gr", "odd_1", "odd_X", "odd_2"]].tolist() == ["ΠΑΟΚ", "Κηφισιά", 1.38, 4.75, 7.5]


def test_greek_transliteration():
    assert ag.greek_to_latin("Λίβερπουλ") == "liverpul"
    assert ag.greek_to_latin("Μπράιτον") == "braiton"
    assert ag.sound_key(ag.greek_to_latin("Λίβερπουλ")) == ag.sound_key("Liverpool")


def test_linking_uses_the_days_fixtures_and_avoids_lookalikes():
    # "Brighton" and "Everton" sound alike on their own; pairing with the opponent decides.
    fixtures = pd.DataFrame({"Division": "E0", "MatchDate": date(2026, 11, 22),
                             "HomeTeam": ["Hull", "Everton", "Liverpool", "Man City"],
                             "AwayTeam": ["Brighton", "Fulham", "Man United", "Chelsea"]})
    coupon = pd.DataFrame({"division": "E0", "day": date(2026, 11, 22),
                           "home_gr": ["Χαλ", "Λίβερπουλ", "Έβερτον", "Γουέστ Χαμ"],
                           "away_gr": ["Μπράιτον", "Μάντσεστερ Γιουνάιτεντ", "Φούλαμ", "Άρσεναλ"]})
    links = ag.link_to_fixtures(coupon, fixtures)
    assert links == {0: 0, 1: 2, 2: 1}                          # West Ham-Arsenal isn't a fixture: skipped


def test_no_link_across_leagues_or_days():
    fixtures = pd.DataFrame({"Division": ["G1", "E0"], "MatchDate": [date(2026, 11, 29), date(2026, 11, 22)],
                             "HomeTeam": ["PAOK", "PAOK"], "AwayTeam": ["Kifisia", "Kifisia"]})
    coupon = pd.DataFrame({"division": ["G1"], "day": [date(2026, 11, 22)], "home_gr": ["ΠΑΟΚ"], "away_gr": ["Κηφισιά"]})
    assert ag.link_to_fixtures(coupon, fixtures) == {}


def write_league(folder, threshold, test_roi, p_pos):
    folder.mkdir(parents=True)
    (folder / "summary.json").write_text(json.dumps({"chosen_threshold": threshold}))
    pd.DataFrame({"strategy": ["No bet", f"Chosen on validation: EV >= {threshold}"],
                  "roi": [0, test_roi], "p_roi_positive": [None, p_pos]}).to_csv(folder / "test_backtest.csv", index=False)


def test_league_evidence(tmp_path):
    write_league(tmp_path / "Greece", None, 0, 0)
    write_league(tmp_path / "Scotland", 0.15, -0.23, 0.0)
    write_league(tmp_path / "England", 0.05, 0.08, 0.99)
    assert today.league_evidence("G1", tmp_path)[0] is False
    ok, _, why = today.league_evidence("SC0", tmp_path)
    assert ok is False and "failed on unseen seasons" in why
    assert today.league_evidence("E0", tmp_path)[:2] == (True, 0.05)
    assert "not studied" in today.league_evidence("I1", tmp_path / "missing")[2]


def coupon_for(day, code="701"):
    return pd.DataFrame([{"code": code, "competition": "ΑΓΓΛΙΑ: Πρέμιερ Λιγκ", "tour_id": 8, "time": "17:00",
                          "home_gr": "Ομάδα Ένα", "away_gr": "Ομάδα Δύο", "odd_1": 3.0, "odd_X": 3.4, "odd_2": 2.4,
                          "state": 1, "division": "E0"}])


def fake_flashscore(divisions, day):
    return pd.DataFrame([{"Division": "E0", "MatchDate": day, "HomeTeam": "Team1", "AwayTeam": "Team2",
                          "FTHome": None, "FTAway": None}]), []


def test_run_says_no_bet_when_no_league_is_proven(tmp_path, monkeypatch, matches):
    monkeypatch.setattr("footy.config.OUTPUT_DIR", tmp_path)
    write_league(tmp_path / "leagues" / "England", None, 0, 0)
    out = today.run(date(2009, 8, 1), fetch_coupon=coupon_for, get_flashscore=fake_flashscore, history_raw=matches,
                    leagues_dir=tmp_path / "leagues", aliases={"Ομάδα Ένα": "Team1", "Ομάδα Δύο": "Team2"},
                    verbose=False)
    assert out.code.tolist() == ["701"] and out.verdict.tolist() == ["NO BET"]
    assert abs(out.model_pH.iloc[0] + out.model_pD.iloc[0] + out.model_pA.iloc[0] - 1) < 1e-9
    assert (tmp_path / "today_2009-08-01.csv").exists()


def test_run_marks_play_only_for_proven_league_with_enough_value(tmp_path, monkeypatch, matches):
    monkeypatch.setattr("footy.config.OUTPUT_DIR", tmp_path)
    write_league(tmp_path / "leagues" / "England", -1.0, 0.08, 0.99)    # accept any EV: forces a PLAY
    out = today.run(date(2009, 8, 1), fetch_coupon=coupon_for, get_flashscore=fake_flashscore, history_raw=matches,
                    leagues_dir=tmp_path / "leagues", aliases={"Ομάδα Ένα": "Team1", "Ομάδα Δύο": "Team2"},
                    verbose=False)
    assert out.verdict.iloc[0].startswith("PLAY ") and "single" in out.verdict.iloc[0]


def test_run_with_no_studied_leagues_is_no_bet(capsys):
    c = coupon_for(date(2026, 11, 19)).assign(division=None)
    out = today.run(date(2026, 11, 19), fetch_coupon=lambda d: c, get_flashscore=fake_flashscore)
    assert out.empty and "NO BET" in capsys.readouterr().out


def test_best_prices_only_from_your_bookmakers():
    rows = [{"bookmaker": "OPAP coupon", "odds": [2.0, 3.0, 3.5]},
            {"bookmaker": "Stoiximan.gr", "odds": ["2.20", "3.10", "3.40"]},
            {"bookmaker": "Novibet", "odds": ["2.10", "3.30", "-"]},
            {"bookmaker": "Pinnacle", "odds": ["2.50", "3.60", "4.00"]}]          # not one of "your" bookmakers
    best, who = today.best_prices(rows, ["Stoiximan", "Novibet", "OPAP coupon"])
    assert best == [2.2, 3.3, 3.5] and who == ["Stoiximan.gr", "Novibet", "OPAP coupon"]


def test_run_uses_best_price_for_value_and_keeps_opap_price(tmp_path, monkeypatch, matches):
    monkeypatch.setattr("footy.config.OUTPUT_DIR", tmp_path)
    write_league(tmp_path / "leagues" / "England", None, 0, 0)

    def flashscore_with_url(divisions, day):
        t, p = fake_flashscore(divisions, day)
        return t.assign(FlashscoreURL="https://fs/match/1"), p

    odds_pages = {"https://fs/match/1": [{"bookmaker": "Stoiximan.gr", "odds": ["3.30", "3.60", "2.50"]},
                                         {"bookmaker": "Unknown Bet", "odds": ["9.00", "9.00", "9.00"]}]}
    out = today.run(date(2009, 8, 1), fetch_coupon=coupon_for, get_flashscore=flashscore_with_url, history_raw=matches,
                    leagues_dir=tmp_path / "leagues", aliases={"Ομάδα Ένα": "Team1", "Ομάδα Δύο": "Team2"},
                    verbose=False, get_odds=lambda urls: {u: odds_pages[u] for u in urls},
                    my_bookmakers=["Stoiximan"], get_lineups=lambda urls: {u: {} for u in urls})
    r = out.iloc[0]
    assert (r.OddHome, r.OddDraw, r.OddAway) == (3.3, 3.6, 2.5)          # coupon had 3.0 / 3.4 / 2.4
    assert r.best_by_1 == "Stoiximan.gr" and float(r.opap_1) == 3.0
    assert r.bookmaker_margin < r.opap_margin
    assert abs(r.ev_H - (r.model_pH * 3.3 - 1)) < 1e-9


def test_team_news_is_shown_and_saved(tmp_path, monkeypatch, matches, capsys):
    monkeypatch.setattr("footy.config.OUTPUT_DIR", tmp_path)
    write_league(tmp_path / "leagues" / "England", None, 0, 0)

    def flashscore_with_url(divisions, day):
        t, p = fake_flashscore(divisions, day)
        return t.assign(FlashscoreURL="https://fs/match/1"), p

    news = {"lineup_status": "predicted", "home_out": [("A. Player", "Injury"), ("B. Player", "Red Card"),
                                                       ("C. Player", "Illness")],
            "away_out": [], "home_doubtful": [], "away_doubtful": [("D. Player", "Knock")],
            "home_xi_rating": 6.6, "away_xi_rating": 7.2}
    out = today.run(date(2009, 8, 1), fetch_coupon=coupon_for, get_flashscore=flashscore_with_url, history_raw=matches,
                    leagues_dir=tmp_path / "leagues", aliases={"Ομάδα Ένα": "Team1", "Ομάδα Δύο": "Team2"},
                    get_odds=lambda urls: {u: [] for u in urls}, get_lineups=lambda urls: {u: news for u in urls})
    printed = capsys.readouterr().out
    assert "OUT A. Player (Injury), B. Player (Red Card), C. Player (Illness)" in printed
    assert "doubtful D. Player (Knock)" in printed and "6.6 vs 7.2" in printed
    assert "many absences" in printed
    saved = pd.read_csv(tmp_path / "today_2009-08-01.csv")
    assert saved.n_home_out.iloc[0] == 3 and "news" not in saved.columns
