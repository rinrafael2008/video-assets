"""All the knobs in one place, so a beginner can see and change them easily."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = Path(os.environ.get("FOOTY_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
MATCHES_CSV = DATA_DIR / "Matches.csv"

# Dataset: "Club Football Match Data" by xgabora (MIT licence). See DATA_LICENSE.md.
DATA_URL = "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data/main/data/Matches.csv"

# Which leagues to use. E0 = English Premier League, E1 = English Championship.
# Using both lets Elo ratings follow teams through promotion and relegation.
DIVISIONS = ["E0", "E1"]

# Chronological split by *season start year* (2018 means the 2018/19 season).
BURN_IN_SEASONS = 1          # first season(s): Elo ratings are still settling, so not used for training
TRAIN_LAST_SEASON = 2017     # train:      2001/02 .. 2017/18
VALID_LAST_SEASON = 2021     # validation: 2018/19 .. 2021/22
#                              test:       2022/23 .. latest

# Elo settings
ELO_START = 1500.0
ELO_K = 20.0
ELO_HOME_ADVANTAGE = 60.0
ELO_SEASON_REGRESSION = 0.2  # pull ratings 20% back towards the average at the start of every season

# Betting simulation (hypothetical, flat stake, no real money)
STAKE = 1.0
EDGE_THRESHOLDS = [0.00, 0.02, 0.05, 0.10, 0.15, 0.20]
MIN_BETS_FOR_STRATEGY = 100  # on validation; fewer bets than this = too noisy to trust -> no-bet
MIN_ODDS, MAX_ODDS = 1.01, 10.0
BOOTSTRAP_SAMPLES = 2000
RANDOM_SEED = 42
