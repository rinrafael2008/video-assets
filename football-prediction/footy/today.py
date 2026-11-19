""""What should I play today?"  -  python -m footy.today

1. Reads today's OPAP coupon from agones.gr (codes, teams, OPAP 1/X/2 odds).
2. Keeps the matches from the 11 leagues this project studied (others are skipped:
   the model was never tested on them, so it has no business predicting them).
3. Reads Flashscore for those leagues: recent results (to bring ratings up to date)
   and the fixture list (to translate the Greek team names safely).
4. Predicts every match and compares with OPAP's odds (margin removed).
5. Gives a verdict per coupon CODE, using the evidence from the backtests:
   a league is only "playable" if its betting rule made money on BOTH the validation
   seasons AND the unseen test seasons, with at least 95% of bootstrap resamples positive.
   So far, no league passes. The usual verdict is therefore NO BET, and that is the honest answer.

Personal use only (agones.gr and Flashscore). Research only: this never places a bet.
Before all that it refreshes the current season from Football-Data.co.uk (footy.update),
so only the last few days need Flashscore.
Options:  --date 2026-11-22   --leagues G1 E0   --no-flashscore   --no-update
"""
from __future__ import annotations

import argparse
import json
from datetime import date

import numpy as np
import pandas as pd

from footy import agones, config, data
from footy.upcoming import predict

COUNTRY_OF = {d: c for c, divs in config.LEAGUE_GROUPS.items() for d in divs}
OUTCOME_NAME = {"H": "1", "D": "X", "A": "2"}


def league_evidence(division: str, leagues_dir=None) -> tuple[bool, float | None, str]:
    """(playable?, EV threshold, explanation) from the saved study results."""
    leagues_dir = leagues_dir or (config.OUTPUT_DIR / "leagues")
    folder = leagues_dir / COUNTRY_OF.get(division, "?")
    if not (folder / "summary.json").exists():
        return False, None, "league not studied yet (run: python -m footy.study)"
    summary = json.loads((folder / "summary.json").read_text())
    t = summary.get("chosen_threshold")
    if t is None:
        return False, None, "no betting rule passed validation"
    bt = pd.read_csv(folder / "test_backtest.csv")
    chosen = bt[bt.strategy.str.startswith("Chosen on validation")]
    if chosen.empty or chosen.roi.iloc[0] <= 0 or chosen.p_roi_positive.iloc[0] < 0.95:
        roi = chosen.roi.iloc[0] if len(chosen) else float("nan")
        return False, t, f"rule passed validation but failed on unseen seasons (ROI {roi:+.1%})"
    return True, t, f"rule EV >= {t:.0%} profitable on validation and test"


def decide(pred: pd.DataFrame, leagues_dir=None) -> pd.DataFrame:
    """Add verdict columns to upcoming.predict output."""
    out = pred.copy()
    ev = out[["ev_H", "ev_D", "ev_A"]].to_numpy(float)
    best = np.nanargmax(np.where(np.isnan(ev), -np.inf, ev), axis=1)
    out["best_pick"] = [OUTCOME_NAME["HDA"[b]] for b in best]
    out["best_ev"] = ev[np.arange(len(ev)), best]
    verdicts, reasons = [], []
    for r in out.itertuples():
        playable, t, why = league_evidence(r.Division, leagues_dir)
        if not playable:
            verdicts.append("NO BET")
        elif r.best_ev >= t:
            verdicts.append(f"PLAY {r.best_pick} (single, 1 unit)")
        else:
            verdicts.append("NO BET")
            why = f"no edge today (best EV {r.best_ev:+.1%} < {t:.0%})"
        reasons.append(why)
    out["verdict"], out["reason"] = verdicts, reasons
    return out


def flashscore_tables(divisions, day):
    """Recent results + fixture list from Flashscore, with dataset team names."""
    from footy import flashscore as fs
    raw = data.load_raw()
    aliases = fs.load_aliases()
    reader = fs.Reader()
    tables, problems = [], []
    try:
        for div in divisions:
            history = data.clean(raw, [div])
            gap = (pd.Timestamp(day) - history.MatchDate.max()).days
            results = reader.list_page(div, "results", show_more=min(6, max(gap, 0) // 21))
            fixtures = [dict(r, start=None) for r in reader.list_page(div, "fixtures") if r["scheduled"]]
            table, unmatched = fs.rows_to_fixture_table(div, results, fixtures, history, aliases, day)
            if unmatched:
                problems.append(f"{div}: Flashscore names not matched {unmatched} (add to team_aliases.csv)")
            tables.append(table)
    finally:
        reader.close()
    return (pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()), problems


def run(day: date, leagues=None, use_flashscore=True, fetch_coupon=None, get_flashscore=None,
        history_raw=None, leagues_dir=None, aliases=None, verbose=True):
    say = print if verbose else (lambda *a, **k: None)
    fetch_coupon = fetch_coupon or (lambda d: agones.parse_coupon(agones.fetch(d)))
    get_flashscore = get_flashscore or flashscore_tables
    coupon = fetch_coupon(day)
    if coupon.empty:
        say("No matches found on agones.gr for this day.")
        return pd.DataFrame()
    playable_rows = coupon.code.notna() & coupon[["odd_1", "odd_X", "odd_2"]].notna().all(axis=1)
    if "state" in coupon:
        playable_rows &= coupon.state.isin([1]) | coupon.state.isna()     # 1 = not started yet
    on_coupon = coupon[playable_rows]
    covered = on_coupon[on_coupon.division.notna()]
    if leagues:
        covered = covered[covered.division.isin(leagues)]
    say(f"OPAP coupon {day:%d/%m/%Y}: {len(on_coupon)} matches with odds, {len(covered)} from the studied leagues.")
    if covered.empty:
        say("\nVERDICT: NO BET. None of today's coupon matches are from leagues the model was tested on.")
        return pd.DataFrame()

    covered = covered.assign(day=day)
    divisions = sorted(covered.division.unique())
    warnings = []
    if use_flashscore:
        say(f"Reading Flashscore for {', '.join(divisions)} (results + fixtures, a few pages, slowly)...")
        fs_table, problems = get_flashscore(divisions, day)
        warnings += problems
    else:
        fs_table = pd.DataFrame(columns=["Division", "MatchDate", "HomeTeam", "AwayTeam"])
        warnings.append("Without Flashscore, team names can't be matched safely and ratings stay out of date.")
    fixtures = fs_table[fs_table.FTHome.isna()] if "FTHome" in fs_table else fs_table
    links = agones.link_to_fixtures(covered, fixtures, aliases)
    skipped = covered.loc[[i for i in covered.index if i not in links]]
    if not links:
        say("\nCould not match any coupon match to a known fixture, so no predictions. VERDICT: NO BET.")
        return pd.DataFrame()

    rows = []
    for i, j in links.items():
        c, f = covered.loc[i], fixtures.loc[j]
        rows.append({"Division": c.division, "MatchDate": pd.Timestamp(day).date(), "HomeTeam": f.HomeTeam,
                     "AwayTeam": f.AwayTeam, "OddHome": c.odd_1, "OddDraw": c.odd_X, "OddAway": c.odd_2,
                     "Bookmaker": f"OPAP code {c.code}"})
    results = fs_table[fs_table.FTHome.notna()] if "FTHome" in fs_table else pd.DataFrame()
    pred, w = predict(history_raw if history_raw is not None else data.load_raw(),
                      pd.concat([results, pd.DataFrame(rows)], ignore_index=True))
    warnings += w
    pred = decide(pred, leagues_dir)
    pred["code"] = pred.Bookmaker.str.replace("OPAP code ", "", regex=False)
    meta = covered.set_index(covered.code.astype(str))[["time", "competition", "home_gr", "away_gr"]]
    pred = pred.join(meta, on="code")
    pred = pred.sort_values(["time", "code"]).reset_index(drop=True)

    for w in warnings:
        say("WARNING:", w)
    say("")
    for r in pred.itertuples():
        say(f"[{r.code}] {r.time}  {r.home_gr} - {r.away_gr}   ({r.competition})")
        say(f"      OPAP odds   1 {r.OddHome:.2f}  X {r.OddDraw:.2f}  2 {r.OddAway:.2f}   (margin {r.bookmaker_margin:.1%})")
        say(f"      OPAP chance 1 {r.book_pH:.0%}  X {r.book_pD:.0%}  2 {r.book_pA:.0%}")
        say(f"      model       1 {r.model_pH:.0%}  X {r.model_pD:.0%}  2 {r.model_pA:.0%}   "
            f"expected goals {r.exp_home_goals:.1f}-{r.exp_away_goals:.1f}")
        say(f"      -> {r.verdict}   ({r.reason})")
    if len(skipped):
        say(f"\nSkipped (team names not matched safely): " +
            ", ".join(f"[{c.code}] {c.home_gr}-{c.away_gr}" for c in skipped.itertuples()))
    n_play = int(pred.verdict.str.startswith("PLAY").sum())
    say("\n" + ("VERDICT: NO BET today. The model has no proven edge over OPAP in these leagues."
                if n_play == 0 else f"VERDICT: {n_play} single(s) marked PLAY above. Flat 1 unit each, no doubles/trebles."))
    out = config.OUTPUT_DIR / f"today_{day.isoformat()}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pred.to_csv(out, index=False)
    say(f"Saved {out}.  Research only - this program never places bets.")
    return pred


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD (default: today)")
    parser.add_argument("--leagues", nargs="+", help="only these league codes, e.g. G1 E0")
    parser.add_argument("--no-flashscore", action="store_true", help="skip Flashscore (not recommended)")
    parser.add_argument("--no-update", action="store_true", help="skip the Football-Data.co.uk refresh")
    args = parser.parse_args()
    if not args.no_update:
        from footy import update
        try:
            print("Refreshing results and odds from Football-Data.co.uk...")
            quick = not update.CACHE_DIR.exists()     # first time: just the last 2 seasons, not 1993-now
            add = update.update(verbose=False, first_season=update.current_season() - 1 if quick else update.FIRST_SEASON)
            if len(add):
                add.to_csv(update.UPDATE_CSV, index=False)
        except Exception as e:      # no internet, site down, ...: carry on with what we have
            print(f"WARNING: Football-Data.co.uk update failed ({e}); continuing with saved data.")
    run(date.fromisoformat(args.date), args.leagues, use_flashscore=not args.no_flashscore)


if __name__ == "__main__":
    main()
