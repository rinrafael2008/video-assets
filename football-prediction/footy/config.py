"""All the knobs in one place, so a beginner can see and change them easily."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = Path(os.environ.get("FOOTY_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
MATCHES_CSV = DATA_DIR / "Matches.csv"

# Dataset: "Club Football Match Data" by xgabora (MIT licence). See DATA_LICENSE.md.
DATA_URL = "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data/main/data/Matches.csv"

# "Main leagues" studied by `python -m footy.study`: country -> divisions loaded together.
# Second divisions are included where available so Elo can follow promoted/relegated teams.
LEAGUE_GROUPS = {
    "England": ["E0", "E1"],
    "Spain": ["SP1", "SP2"],
    "Germany": ["D1", "D2"],
    "Italy": ["I1", "I2"],
    "France": ["F1", "F2"],
    "Netherlands": ["N1"],
    "Portugal": ["P1"],
    "Belgium": ["B1"],
    "Turkey": ["T1"],
    "Greece": ["G1"],
    "Scotland": ["SC0", "SC1"],
}
TOP_DIVISIONS = {"E0", "SP1", "D1", "I1", "F1", "N1", "P1", "B1", "T1", "G1", "SC0"}

# Which leagues the single-run pipeline uses by default. E0 = English Premier League, E1 = English Championship.
# Using both lets Elo ratings follow teams through promotion and relegation.
DIVISIONS = ["E0", "E1"]

# Chronological split by *season start year* (2018 means the 2018/19 season).
BURN_IN_SEASONS = 1          # first season(s): Elo ratings are still settling, so not used for training
TRAIN_LAST_SEASON = 2017     # train:      2001/02 .. 2017/18
VALID_LAST_SEASON = 2021     # validation: 2018/19 .. 2021/22
#                              test:       2022/23 .. latest

# Elo settings, tuned on the VALIDATION seasons with `python -m footy.tune_elo` (results in
# outputs/elo_tuning.csv). Validation log loss of the Elo baseline: 1.0224 with the old
# hand-picked settings (K 20, home 60, pull 0.2) -> 1.0179 with these.
ELO_START = 1500.0
ELO_K = 15.0                 # how fast ratings react to a result
ELO_HOME_ADVANTAGE = 80.0    # anything from 70 to 110 scored the same; the model re-learns it anyway
ELO_SEASON_REGRESSION = 0.05 # pull ratings 5% back towards the average at the start of every season
ELO_PROMOTION_SHIFT = 0.0    # rating change for a promoted team: tuning found 0 best (the model
                             # gets "promoted"/"relegated" flags instead)

# Betting simulation (hypothetical, flat stake, no real money)
STAKE = 1.0
EDGE_THRESHOLDS = [0.00, 0.02, 0.05, 0.10, 0.15, 0.20]
MIN_BETS_FOR_STRATEGY = 100  # on validation; fewer bets than this = too noisy to trust -> no-bet
MIN_ODDS, MAX_ODDS = 1.01, 10.0
BOOTSTRAP_SAMPLES = 2000
RANDOM_SEED = 42

# ---- Bookmakers you can bet with (used by footy.today to find the best price) ----------
# Names as Flashscore shows them (matched by "contains", capitals ignored). Keep only the ones
# where YOU have an account: a better price elsewhere is no use if you can't bet there.
# OPAP's coupon price (from agones.gr) is always included.
MY_BOOKMAKERS = ["Stoiximan", "Novibet", "bet365", "Bwin", "Interwetten", "PameStoixima",
                 "Winmasters", "Betsson", "Elabet", "Fonbet"]

# ---- National teams (python -m footy.international) --------------------------------
# Dataset: "International football results from 1872" by Mart Jürisoo, CC0 (public domain).
INTL_DATA_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
INTL_CSV = DATA_DIR / "international_results.csv"
INTL_TRAIN_START = "1990-01-01"   # older matches only warm up the Elo ratings
INTL_TRAIN_END = "2013-12-31"     # train:      1990 .. 2013
INTL_VALID_END = "2018-12-31"     # validation: 2014 .. 2018   test: 2019 .. latest
INTL_HOME_ADVANTAGE = 100.0
