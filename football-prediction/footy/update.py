"""Keep the match data up to date (and extend it back to 1993) from Football-Data.co.uk.

    python -m footy.update              first run: every season since 1993/94 (~10 minutes)
                                        later runs: only the current season (seconds)
    python -m footy.update --refresh    download everything again

Why: the main dataset (xgabora, see DATA_LICENSE.md) is updated only every few months.
Football-Data.co.uk is where its numbers come from, and it is updated twice a week with
results and odds. The extra matches are saved to data/Matches_update.csv, in the same
format as data/Matches.csv. Every part of the project loads both automatically.

How the two sources are combined:
1. Team names: the two sources sometimes spell clubs differently. We learn the
   translation automatically from matches that appear in BOTH files (same league, date
   and score) and apply it, so a club never becomes two different "teams".
2. Only matches that the main dataset does NOT have are added: newer than its last
   match in that league, or older than its first one (the 1990s).
3. The last few days (after Football-Data's latest update) still come from Flashscore,
   inside `python -m footy.today`.

Licence: same source as the main dataset; free to download for personal research, no
formal open licence (see DATA_LICENSE.md). The files stay on your computer.
"""
from __future__ import annotations

import argparse
import io
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date

import pandas as pd

from footy import config, data

URL = "https://www.football-data.co.uk/mmz4281/{code}/{div}.csv"
CACHE_DIR = config.DATA_DIR / "football-data"
UPDATE_CSV = config.DATA_DIR / "Matches_update.csv"
FIRST_SEASON = 1993
DIVISIONS = sorted({d for divs in config.LEAGUE_GROUPS.values() for d in divs})


def season_code(start_year: int) -> str:
    """2026 -> '2627' (the 2026/27 season)."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def current_season(today: date | None = None) -> int:
    today = today or date.today()
    return today.year if today.month >= 7 else today.year - 1


def download(div: str, start_year: int, refresh: bool = False, pause: float = 1.0) -> str | None:
    """CSV text for one league-season (cached in data/football-data/), or None if it doesn't exist."""
    path = CACHE_DIR / f"{season_code(start_year)}_{div}.csv"
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    time.sleep(pause)                                        # be gentle with the website
    req = urllib.request.Request(URL.format(code=season_code(start_year), div=div),
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("latin-1")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def _first(df, *cols):
    for c in cols:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce")
    return pd.Series(float("nan"), index=df.index)


def to_dataset_format(csv_text: str, div: str) -> pd.DataFrame:
    """One Football-Data CSV -> the columns of data/Matches.csv."""
    raw = pd.read_csv(io.StringIO(csv_text), on_bad_lines="skip", encoding_errors="ignore")
    raw = raw.dropna(subset=[c for c in ("HomeTeam", "AwayTeam", "Date") if c in raw.columns])
    if raw.empty or "HomeTeam" not in raw.columns:
        return pd.DataFrame()
    home_goals = _first(raw, "FTHG", "HG")
    away_goals = _first(raw, "FTAG", "AG")
    out = pd.DataFrame({
        "Division": div,
        "MatchDate": pd.to_datetime(raw["Date"], dayfirst=True, format="mixed", errors="coerce"),
        "MatchTime": raw["Time"] if "Time" in raw.columns else None,
        "HomeTeam": raw["HomeTeam"].astype(str).str.strip(),
        "AwayTeam": raw["AwayTeam"].astype(str).str.strip(),
        "FTHome": home_goals, "FTAway": away_goals,
        "OddHome": _first(raw, "B365H"), "OddDraw": _first(raw, "B365D"), "OddAway": _first(raw, "B365A"),
        "MaxHome": _first(raw, "MaxH", "BbMxH"), "MaxDraw": _first(raw, "MaxD", "BbMxD"),
        "MaxAway": _first(raw, "MaxA", "BbMxA"),
        "Over25": _first(raw, "B365>2.5"), "Under25": _first(raw, "B365<2.5"),
    })
    out = out.dropna(subset=["MatchDate", "FTHome", "FTAway"])
    out["FTResult"] = [("H" if h > a else "D" if h == a else "A") for h, a in zip(out.FTHome, out.FTAway)]
    return out


def learn_name_map(new: pd.DataFrame, main: pd.DataFrame) -> dict:
    """Football-Data name -> main-dataset name, from matches present in both
    (same league, same day, same score). Majority vote per name."""
    m = main[["Division", "MatchDate", "FTHome", "FTAway", "HomeTeam", "AwayTeam"]].copy()
    m["MatchDate"] = pd.to_datetime(m.MatchDate)
    key = ["Division", "MatchDate", "FTHome", "FTAway"]
    m = m.drop_duplicates(key, keep=False)                       # only unambiguous rows
    n = new.drop_duplicates(key, keep=False)
    both = n.merge(m, on=key, suffixes=("_new", "_main"))
    votes = {}
    for side in ("HomeTeam", "AwayTeam"):
        for a, b in zip(both[f"{side}_new"], both[f"{side}_main"]):
            votes.setdefault(a, Counter())[b] += 1
    return {a: c.most_common(1)[0][0] for a, c in votes.items() if c.most_common(1)[0][1] >= 2}


def missing_rows(new: pd.DataFrame, main: pd.DataFrame) -> pd.DataFrame:
    """Rows of `new` (already renamed) that the main dataset doesn't have."""
    main_dates = pd.to_datetime(main.MatchDate)
    keep = []
    for div, g in new.groupby("Division"):
        in_main = main_dates[main.Division == div]
        if in_main.empty:
            keep.append(g)
            continue
        keep.append(g[(g.MatchDate > in_main.max()) | (g.MatchDate < in_main.min())])
    out = pd.concat(keep) if keep else new.iloc[:0]
    known = set(zip(main_dates.dt.date, main.HomeTeam, main.AwayTeam))
    return out[[(d.date(), h, a) not in known for d, h, a in zip(out.MatchDate, out.HomeTeam, out.AwayTeam)]]


def update(divisions=DIVISIONS, refresh=False, today=None, main=None, fetch=download, verbose=True,
           first_season=FIRST_SEASON) -> pd.DataFrame:
    say = print if verbose else (lambda *a, **k: None)
    main = main if main is not None else pd.read_csv(config.MATCHES_CSV, low_memory=False)
    now = current_season(today)
    frames = []
    for div in divisions:
        got = 0
        for season in range(first_season, now + 1):
            # Old seasons never change: use the saved copy. The current season is always re-downloaded.
            text = fetch(div, season, refresh=refresh or season == now)
            if text:
                df = to_dataset_format(text, div)
                if len(df):
                    frames.append(df)
                    got += 1
        say(f"  {div}: {got} seasons")
    if not frames:
        return pd.DataFrame()
    new = pd.concat(frames, ignore_index=True)
    names = learn_name_map(new, main)
    new["HomeTeam"] = new.HomeTeam.replace(names)
    new["AwayTeam"] = new.AwayTeam.replace(names)
    add = missing_rows(new, main).sort_values("MatchDate")
    add = add.assign(MatchDate=add.MatchDate.dt.strftime("%Y-%m-%d"), Source="football-data.co.uk")
    return add


def main_cli():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="download every season again")
    parser.add_argument("--leagues", nargs="+", default=DIVISIONS, help="league codes (default: all studied)")
    args = parser.parse_args()
    first_time = not CACHE_DIR.exists()
    print("Updating from Football-Data.co.uk" + (" (first time: all seasons since 1993/94, about 10 minutes)"
                                                  if first_time or args.refresh else "") + "...")
    add = update(args.leagues, refresh=args.refresh)
    if add.empty:
        print("Nothing new.")
        return
    add.to_csv(UPDATE_CSV, index=False)
    old = add[pd.to_datetime(add.MatchDate) < "2000-07-01"]
    print(f"Saved {len(add):,} extra matches to {UPDATE_CSV}: {len(old):,} from the 1990s, "
          f"{len(add) - len(old):,} recent (latest {add.MatchDate.max()}).")
    print("Tip: re-run  python -m footy.study  to retrain and re-test every league on the bigger data.")


if __name__ == "__main__":
    main_cli()
