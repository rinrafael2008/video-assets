"""Football-Data.co.uk updater: CSV parsing, automatic team-name translation, and adding
only the matches the main dataset doesn't have. No internet: fake CSV files."""
from datetime import date

import pandas as pd

from footy import data, update


def fd_csv(rows, old_style=False):
    """Build a Football-Data style CSV (dd/mm/yy dates). old_style = 1990s-like columns."""
    if old_style:
        head = "Div,Date,HomeTeam,AwayTeam,HG,AG,Res"
        lines = [f"E0,{d:%d/%m/%y},{h},{a},{hg},{ag},X" for d, h, a, hg, ag in rows]
    else:
        head = "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A,BbMxH,BbMxD,BbMxA,B365>2.5,B365<2.5"
        lines = [f"E0,{d:%d/%m/%Y},15:00,{h},{a},{hg},{ag},X,2.1,3.3,3.6,2.2,3.4,3.8,1.9,1.9" for d, h, a, hg, ag in rows]
    return "\n".join([head] + lines) + "\n"


def test_parse_football_data_csv():
    df = update.to_dataset_format(fd_csv([(date(2026, 9, 12), "Arsenal", "Chelsea", 2, 1)]), "E0")
    r = df.iloc[0]
    assert (r.MatchDate, r.HomeTeam, r.FTHome, r.FTAway, r.FTResult) == (pd.Timestamp("2026-09-12"), "Arsenal", 2, 1, "H")
    assert (r.OddHome, r.MaxHome, r.Over25) == (2.1, 2.2, 1.9)
    old = update.to_dataset_format(fd_csv([(date(1995, 8, 19), "Arsenal", "Chelsea", 0, 0)], old_style=True), "E0")
    assert old.iloc[0].MatchDate == pd.Timestamp("1995-08-19") and old.iloc[0].FTResult == "D"
    assert pd.isna(old.iloc[0].OddHome)                         # no odds in the 1990s files: fine


def test_season_codes():
    assert update.season_code(2026) == "2627" and update.season_code(1999) == "9900"
    assert update.current_season(date(2026, 11, 19)) == 2026 and update.current_season(date(2027, 3, 1)) == 2026


def main_dataset():
    return pd.DataFrame({
        "Division": "E0", "MatchDate": ["2026-08-16", "2026-08-23", "2026-08-30"],
        "HomeTeam": ["Man United", "Nott'm Forest", "Man United"], "AwayTeam": ["Nott'm Forest", "Man United", "Arsenal"],
        "FTHome": [1, 2, 0], "FTAway": [0, 2, 1]})


def fake_fetch(div, season, refresh=False):
    if season == 1995:
        return fd_csv([(date(1995, 8, 19), "Man Utd", "Nottingham F", 3, 1)], old_style=True)
    if season == 2026:   # overlaps the main dataset (names spelled differently) + newer matches
        return fd_csv([(date(2026, 8, 16), "Man Utd", "Nottingham F", 1, 0),
                       (date(2026, 8, 23), "Nottingham F", "Man Utd", 2, 2),
                       (date(2026, 8, 30), "Man Utd", "Arsenal", 0, 1),
                       (date(2026, 11, 8), "Arsenal", "Man Utd", 3, 0)])
    return None


def test_update_translates_names_and_adds_only_missing_matches():
    add = update.update(["E0"], main=main_dataset(), fetch=fake_fetch, today=date(2026, 11, 19),
                        verbose=False, first_season=1995)
    assert sorted(add.MatchDate) == ["1995-08-19", "2026-11-08"]           # overlap not duplicated
    assert set(add.HomeTeam) | set(add.AwayTeam) == {"Man United", "Nott'm Forest", "Arsenal"}
    assert (add.Source == "football-data.co.uk").all()


def test_load_raw_includes_update_file(tmp_path):
    main = tmp_path / "Matches.csv"
    main_dataset().assign(FTResult="H").to_csv(main, index=False)
    extra = tmp_path / "Matches_update.csv"
    pd.DataFrame({"Division": ["E0"], "MatchDate": ["2026-11-08"], "HomeTeam": ["Arsenal"], "AwayTeam": ["Man United"],
                  "FTHome": [3], "FTAway": [0], "Source": ["football-data.co.uk"]}).to_csv(extra, index=False)
    raw = data.load_raw(main, extra)
    assert len(raw) == 4 and "Source" not in raw.columns
    assert len(data.load_raw(main, tmp_path / "missing.csv")) == 3
