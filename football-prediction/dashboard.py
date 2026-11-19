"""Local dashboard.  Start it with:   streamlit run dashboard.py
It only READS the files in outputs/ (made by: python -m footy.pipeline).
Research and education only - it cannot place bets."""
import json

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from footy import backtest as bt
from footy.config import OUTPUT_DIR
from footy.models import outcome_index

st.set_page_config(page_title="Football prediction research", layout="wide")
st.title("Football prediction research dashboard")
st.warning("Research and education only. This tool never places real bets, and nothing here is "
           "betting advice. Past results do not guarantee future results.")

if not (OUTPUT_DIR / "summary.json").exists():
    st.error("No results yet. In a terminal run:  python -m footy.data  then  python -m footy.pipeline")
    st.stop()

summary = json.loads((OUTPUT_DIR / "summary.json").read_text())
test_metrics = pd.read_csv(OUTPUT_DIR / "test_metrics.csv")
valid_metrics = pd.read_csv(OUTPUT_DIR / "validation_metrics.csv")
calib = pd.read_csv(OUTPUT_DIR / "calibration.csv")
preds = pd.read_csv(OUTPUT_DIR / "test_predictions.csv", parse_dates=["MatchDate"])
test_bt = pd.read_csv(OUTPUT_DIR / "test_backtest.csv")
valid_bt = pd.read_csv(OUTPUT_DIR / "validation_backtest.csv")

c = st.columns(4)
c[0].metric("Leagues", ", ".join(summary["divisions"]))
c[1].metric("Test matches", f"{summary['n_test']:,}")
c[2].metric("Test matches with odds", f"{summary['n_test_with_odds']:,}")
c[3].metric("Strategy chosen on validation", "NO BET" if summary["chosen_threshold"] is None
            else f"EV >= {summary['chosen_threshold']:.0%}")
st.caption(f"Best scikit-learn model (chosen on validation): **{summary['best_ml_model']}**. Train seasons {summary['train_seasons']}, validation {summary['valid_seasons']}, "
           f"test {summary['test_seasons']} (season 2022 = 2022/23).")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Accuracy", "Calibration", "Goals", "Backtest", "Matches"])

with tab1:
    st.subheader("Test-set scores (lower log loss / Brier = better)")
    st.dataframe(test_metrics.round(4), hide_index=True, width="stretch")
    st.markdown("- **Log loss** of a coin-flip-style 1/3 guess is 1.0986; **Brier** of that guess is 0.667.\n"
                "- The **bookmaker** row uses Bet365 odds with the margin removed. Beating it is very hard.")
    st.subheader("Validation scores (used to pick the model)")
    st.dataframe(valid_metrics.round(4), hide_index=True, width="stretch")

with tab2:
    st.subheader("Calibration: when a model says X%, does it happen X% of the time?")
    outcome = st.radio("Outcome", ["H", "D", "A"], horizontal=True,
                       format_func={"H": "Home win", "D": "Draw", "A": "Away win"}.get)
    d = calib[(calib.outcome == outcome) & (calib.n >= 20)]
    diag = alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(strokeDash=[4, 4], color="gray") \
        .encode(x="x", y="y")
    pts = alt.Chart(d).mark_line(point=True).encode(
        x=alt.X("mean_predicted", title="Predicted probability", scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("observed_frequency", title="Observed frequency", scale=alt.Scale(domain=[0, 1])),
        color="model", tooltip=["model", "n", alt.Tooltip("mean_predicted", format=".3f"),
                                alt.Tooltip("observed_frequency", format=".3f")])
    st.altair_chart(diag + pts, width="stretch")
    st.caption("Points on the dashed line = perfectly calibrated. Bins with fewer than 20 matches are hidden.")

with tab3:
    g = summary["goals"]
    st.subheader("Goals model (Poisson regression)")
    st.table(pd.DataFrame({
        "Model": [g["mae_home_goals_model"], g["mae_away_goals_model"], g["over25_brier_model"], g["over25_logloss_model"]],
        "Benchmark": [g["mae_home_goals_naive"], g["mae_away_goals_naive"], g["over25_brier_bookmaker"],
                      g["over25_logloss_bookmaker"]]},
        index=["Home goals MAE (vs average)", "Away goals MAE (vs average)",
               "Over 2.5 Brier (vs bookmaker)", "Over 2.5 log loss (vs bookmaker)"]).round(4))
    st.caption("MAE = average absolute miss in goals. Benchmarks: league-average goals and the bookmaker's "
               "margin-free over/under 2.5 probability.")

with tab4:
    st.subheader("Hypothetical flat-stake backtest on TEST seasons (1 unit per bet)")
    st.dataframe(test_bt.round(3), hide_index=True, width="stretch")
    st.markdown("- `roi_ci_low` / `roi_ci_high`: 95% bootstrap interval - if it includes 0, the result could "
                "easily be luck.\n- Rows marked **[info]** were NOT used for any decision; picking the best of them "
                "after seeing test results would be cheating.\n- **[optimistic]** uses the best price across ~17 "
                "bookmakers, which a single bettor usually can't get.")
    with st.expander("Validation backtest (this is what chose the strategy)"):
        st.dataframe(valid_bt.round(3), hide_index=True, width="stretch")

    st.subheader("Explore a threshold yourself (for learning only)")
    t = st.slider("Minimum expected value to place a pretend bet", 0.0, 0.5, 0.05, 0.01)
    probs = preds[["ml_pH", "ml_pD", "ml_pA"]].to_numpy()
    odds = preds[["OddHome", "OddDraw", "OddAway"]].to_numpy(float)
    bets = bt.run_backtest(probs, odds, outcome_index(preds.FTResult), t)
    s = bt.summarise(bets, "explore")
    k = st.columns(4)
    k[0].metric("Bets", s["bets"])
    k[1].metric("ROI", f"{s['roi']:.1%}")
    k[2].metric("Max drawdown", f"{s['max_drawdown']:.1f} units")
    k[3].metric("Hit rate", "-" if not s["bets"] else f"{s['hit_rate']:.1%}")
    st.write(f"95% bootstrap interval for ROI: **{s['roi_ci_low']:.1%} to {s['roi_ci_high']:.1%}**. "
             "Warning: tuning this slider on the test seasons is exactly the overfitting the pipeline avoids.")
    if s["bets"]:
        curve = bets.assign(bet_number=np.arange(1, len(bets) + 1))
        st.line_chart(curve, x="bet_number", y="cumulative_profit")

with tab5:
    st.subheader("Test-set predictions")
    team = st.selectbox("Filter by team", ["(all)"] + sorted(set(preds.HomeTeam) | set(preds.AwayTeam)))
    view = preds if team == "(all)" else preds[(preds.HomeTeam == team) | (preds.AwayTeam == team)]
    cols = ["MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "ml_pH", "ml_pD", "ml_pA",
            "mkt_pH", "mkt_pD", "mkt_pA", "exp_home_goals", "exp_away_goals", "p_over25"]
    st.dataframe(view[cols].round({c: 3 for c in cols[5:]}), hide_index=True, width="stretch")
    st.caption("ml_* = scikit-learn model, mkt_* = bookmaker (margin removed). All predictions were made "
               "with information available before kickoff.")
