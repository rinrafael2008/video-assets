# Football prediction research system (beginner edition)

A small Python project that teaches you how to:

1. predict the probabilities of **home win / draw / away win** and the **number of goals** for football matches,
2. check honestly whether those predictions are any good,
3. compare them with the bookmaker's view, and
4. run a **pretend** betting simulation to see whether the model could have made money.

> **This is a research and learning tool. It never places real bets and has no way to place them.**
> Nothing here is betting advice. The main finding (see [Results](#7-results-from-the-first-run)) is that
> the bookmaker predicts better than our models, so the honest recommendation is **not to bet**.

---

## Contents
1. [Quick start on Windows](#1-quick-start-on-windows)
2. [What's in the project](#2-whats-in-the-project)
3. [The data, and why we can use it](#3-the-data-and-why-we-can-use-it)
4. [Step by step: how the system works](#4-step-by-step-how-the-system-works)
5. [How we avoid cheating (data leakage)](#5-how-we-avoid-cheating-data-leakage)
6. [Reading the results](#6-reading-the-results)
7. [Results from the first run](#7-results-from-the-first-run)
8. [Limitations](#8-limitations-please-read)
9. [Running the tests](#9-running-the-tests)
10. [Ideas for next steps](#10-ideas-for-next-steps)

---

## 1. Quick start on Windows

You need **Python 3.11, 3.12 or 3.13**. If you don't have Python yet, download it from
<https://www.python.org/downloads/windows/>. In the installer, tick **"Add python.exe to PATH"**.

Open **PowerShell**: press the Windows key, type `powershell`, then press Enter. Then run these
commands one at a time:

```powershell
# 1. Go to the project folder (change the path to wherever you saved it)
cd C:\path\to\football-prediction

# 2. Create a "virtual environment": a private box for this project's libraries
py -m venv .venv

# 3. Switch it on. Your prompt should now start with (.venv)
.venv\Scripts\Activate.ps1
#    If you get "running scripts is disabled on this system", run this once and try again:
#    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 4. Install the libraries
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Download the data (about 45 MB, saved to data\Matches.csv)
python -m footy.data

# 6. Run the whole research pipeline (takes about 10 seconds; results go to outputs\)
python -m footy.pipeline

# 7. Open the dashboard in your browser (press Ctrl+C in PowerShell to stop it)
streamlit run dashboard.py

# 8. Run the automated tests
python -m pytest
```

If you use **Command Prompt** (cmd.exe) instead of PowerShell, step 3 is `.venv\Scripts\activate.bat`.
On macOS or Linux, use `python3 -m venv .venv` and `source .venv/bin/activate`.

To try other leagues: `python -m footy.pipeline --divisions SP1 SP2` (Spain). Other codes are `D1`
(Germany), `I1` (Italy), `F1` (France), each followed by its second division (`D2`, `I2`, `F2`).
Use top **and** second divisions together, so that Elo ratings can follow promoted and relegated teams.

---

## 2. What's in the project

```
football-prediction/
├── footy/                 the Python package
│   ├── config.py          all the settings (leagues, seasons, Elo K-factor, betting thresholds)
│   ├── data.py            download + clean the CSV
│   ├── elo.py             Elo rating system
│   ├── features.py        pre-match features (Elo, recent form, rest days)
│   ├── split.py           chronological train / validation / test split
│   ├── models.py          Elo baseline, scikit-learn models, Poisson goals model
│   ├── odds.py            odds -> probabilities, removing the bookmaker margin
│   ├── evaluate.py        log loss, Brier score, accuracy, calibration
│   ├── backtest.py        hypothetical flat-stake value-betting simulation
│   └── pipeline.py        runs everything in order, writes outputs/
├── dashboard.py           local Streamlit dashboard (only reads outputs/)
├── tests/                 automated tests (use small fake data, no download needed)
├── requirements.txt
├── DATA_LICENSE.md        dataset licence details
└── README.md              this file
```

`data/` and `outputs/` are created when you run the project. They are not stored in git.

---

## 3. The data, and why we can use it

We use **Club Football Match Data** by `xgabora` on GitHub. It is released under the **MIT licence**,
which allows use for any purpose, including machine-learning training, as long as you keep the
copyright notice. It contains about 239,000 matches from 2000 to 2026, with the final score and the
pre-match odds from **Bet365** (one real bookmaker), plus the **best price across about 17 bookmakers**.

One caveat: the dataset author collected the numbers from Football-Data.co.uk, which offers its files
for free but has no formal open licence. Research and learning, like this project, is the intended use.
Check with them before any commercial use. [DATA_LICENSE.md](DATA_LICENSE.md) has the full details and
some alternatives.

By default we use the **English Premier League (E0)** and the **Championship (E1)**: about 23,000 matches.

---

## 4. Step by step: how the system works

### Step 1: Load and clean (`footy/data.py`)
- We keep only the columns we need: date, teams, final score and odds.
- Some odds are broken, for example `0.00`. Any odds of 1.00 or less are treated as missing.
- We check that the three implied probabilities of each match add up to a believable total
  (about 1.00 to 1.30). Odds that fail this check are thrown away.
- We sort the matches by date. **Order matters**, because everything after this step walks through
  time.

### Step 2: Elo ratings (`footy/elo.py`)
Elo is a simple rating system, first invented for chess. Every team has a number, starting at 1500.
- Before a match, we turn the rating difference (plus about 60 points for home advantage) into an
  *expected score* for the home team, between 0 and 1.
- After the match, the winner takes points from the loser:
  `change = K × (actual − expected)`, with K = 20. A surprise result moves the ratings a lot;
  an expected result moves them only a little.
- At the start of every season, ratings are pulled 20% back towards the average, because squads change
  over the summer.
- A team we've never seen before (for example, one promoted from League One) starts at a low-ish rating,
  the 20th percentile of current ratings, because newcomers are usually weaker.

### Step 3: Features (`footy/features.py`)
"Features" are the inputs the model sees. For each match, using **only earlier matches**, we record:
- both teams' Elo ratings and the difference between them,
- points, goals scored and goals conceded per game over each team's last 5 matches,
- days since each team's last match (capped at 30),
- how many matches of history we have for each team.

We **ignore** the dataset's shots, cards, corners and half-time score columns, because they happen
*during* the match. We also ignore its ready-made Elo and form columns, because we can't be 100% sure
how they were timed. Instead, we build our own and test them.

### Step 4: Chronological split (`footy/split.py`)
| Part | Seasons | What it's for |
|---|---|---|
| (burn-in) | 2000/01 | Elo ratings are still settling, so not used |
| **Train** | 2001/02 – 2017/18 | the models learn from these |
| **Validation** | 2018/19 – 2021/22 | we pick the best model and the betting rule here |
| **Test** | 2022/23 – Sept 2026 | final, one-time exam. Never used to make any choice |

We **never shuffle** the matches. A random split would let the model learn from 2024 to predict 2019,
which is impossible in real life.

### Step 5: Models (`footy/models.py`)
1. **Elo baseline**: uses only the Elo difference. A small logistic regression learns how a rating gap
   turns into home, draw and away probabilities.
2. **scikit-learn models**: two logistic regressions (different strengths of regularisation) and a
   shallow gradient-boosting model, all using every feature. Whichever has the lowest **validation**
   log loss wins.
3. **Poisson goals model**: two Poisson regressions predict *expected home goals* and *expected away
   goals*. From those we build a table of every possible scoreline, which gives P(over 2.5 goals) and a
   third set of home/draw/away probabilities.

The models are **not** given the odds as inputs. This keeps the comparison with the bookmaker fair:
the model and the market are two independent opinions.

After the choice is made on validation, the winning model is **re-trained on train + validation**,
and then predicts the test seasons **once**.

### Step 6: Bookmaker comparison (`footy/odds.py`)
Odds of 2.50 imply a probability of 1 / 2.50 = 40%. For a single match, the home, draw and away
implied probabilities add up to about **105%**. The extra 5% is the bookmaker's margin (their profit).
We remove it in two ways:
- **Proportional**: divide each by the total, so they add up to 100%.
- **Power method**: takes a bit more margin away from long shots, which is where bookmakers usually
  hide more of it.

Then we score the bookmaker's probabilities exactly like our own models.

### Step 7: Hypothetical backtest (`footy/backtest.py`)
- **Expected value (EV)** of staking 1 unit = `our probability × odds − 1`. For example, 0.45 × 2.50 − 1 = +0.125.
- For each match, take the outcome with the highest EV. If that EV is at least the **threshold**,
  pretend to stake **1 unit**. Otherwise, skip the match.
- The threshold (0%, 2%, 5%, 10%, 15% or 20%) is chosen on the **validation** seasons. A threshold
  only counts if it was profitable over at least 100 bets. If none qualifies, the system chooses
  **"No bet"**, which is always a valid option: 0 bets, 0 profit, 0 risk.
- Prices are **Bet365 odds**: one real bookmaker you could actually have bet with. The "best market
  price" is shown only as an *optimistic* extra row.
- Reported numbers: number of bets, ROI (profit ÷ total staked), hit rate, average odds,
  **maximum drawdown** (the worst fall from a previous high, in units), and a **95% bootstrap interval**
  for the ROI (how much the ROI could vary just by luck).

---

## 5. How we avoid cheating (data leakage)

"Leakage" means the model secretly sees information it couldn't have had before kickoff. It makes
results look great on paper, and then they fail in real life. Our safeguards:

| Risk | Safeguard | Checked by test |
|---|---|---|
| A match's own result used in its features | features are read **before** each match updates the ratings | `test_changing_a_result_does_not_change_its_own_or_earlier_features` |
| Future matches affecting past features | features depend only on earlier rows | `test_deleting_the_future_does_not_change_the_past` |
| In-match stats (shots, cards…) used as inputs | not in the feature list | `test_features_do_not_use_match_statistics` |
| Random shuffling mixes past and future | chronological split, with an overlap check | `test_split_is_chronological_and_disjoint` |
| Imputer or scaler learning from test data | scikit-learn `Pipeline`, fitted on training rows only | (by design) |
| Choosing the model or bet rule after seeing test results | all choices made on validation; test used once | `test_no_bet_chosen_when_model_has_no_edge` |

---

## 6. Reading the results

| Metric | Meaning | "Know nothing" value | Better is |
|---|---|---|---|
| **Log loss** | punishes confident wrong predictions very hard | 1.0986 (always ⅓, ⅓, ⅓) | lower |
| **Brier score** | average squared error of the 3 probabilities (range 0–2) | 0.667 | lower |
| **Accuracy** | how often the most likely outcome happened | ~44% (always pick home) | higher |
| **Calibration error** | average gap between "we said 40%" and "it happened 38%" | – | lower |

Accuracy is the easiest to understand, but it's the **least useful** here. Draws are almost never the
favourite, so accuracy hides how good the probabilities are. Focus on log loss and Brier score.

Football is very random. Even the bookmaker only reaches a log loss of about 1.00. Differences of
**0.005** are meaningful.

---

## 7. Results from the first run

English Premier League + Championship. Test = 3,794 matches (2022/23 to September 2026), all with Bet365 odds.

**Home / draw / away (test seasons):**

| Model | Log loss | Brier | Accuracy | Calibration error |
|---|---|---|---|---|
| Elo baseline | 1.0306 | 0.6188 | 48.7% | 0.016 |
| Logistic regression (best on validation) | 1.0290 | 0.6178 | 48.2% | 0.015 |
| Poisson goals model (H/D/A) | 1.0324 | 0.6201 | 48.2% | 0.017 |
| **Bookmaker, Bet365, margin removed** | **1.0080** | **0.6038** | **49.8%** | **0.006** |

**Goals:** the Poisson model's average error is 0.96 home goals and 0.83 away goals. Simply guessing
the league average gives 1.01 and 0.85. For over/under 2.5 goals, the model's Brier score is 0.248
against the bookmaker's 0.243, so the bookmaker is better here too.

**Hypothetical backtest:** every threshold lost money on the **validation** seasons (−6% to −11% ROI),
so the system chose **"No bet"**. For information only, the same thresholds on the test seasons also
lost money: −3% to −8% ROI over 1,100–3,250 bets, with drawdowns of 140–210 units. Every 95% interval
includes zero, with low ends between −9% and −19% and high ends between +1% and +5%. Even at the best market price (which is unrealistic for one bettor), ROI was
+1.1%, with an interval of −5.8% to +7.2%: indistinguishable from zero.

**Plain-English conclusion:** the models learn real patterns. They clearly beat the "know nothing"
guess (1.0986). But the bookmaker's prices already contain everything our simple features know, and
more (injuries, line-ups, team news). The model's "value bets" are mostly cases where it is wrong.
The Bet365 margin of about 5.5% guarantees a loss unless you have a real edge. This is the normal,
expected result for a first model, and it is exactly why the no-bet option exists.

(Your numbers may differ slightly if the dataset has been updated since this run.)

---

## 8. Limitations (please read)

- **Data licence**: the compilation is MIT-licensed, but the original source (Football-Data.co.uk)
  has no formal open licence. See [DATA_LICENSE.md](DATA_LICENSE.md).
- **When were the odds taken?** The dataset's Bet365 odds were probably collected a day or two before
  kickoff, and in some seasons they may be closing odds. If they are closing odds, they are *sharper*
  than the prices you would usually bet at, which makes the bookmaker look harder to beat. We can't
  tell exactly which from the dataset.
- **Best market price is optimistic**: it takes the best price from about 17 bookmakers after the fact.
  Getting it would need accounts everywhere, perfect timing, and no betting limits.
- **The backtest is simplified**: no betting limits, no stake restrictions or banned accounts, no
  odds moving after you bet, no taxes or fees, and every bet is assumed to be accepted at the listed price.
- **Simple features**: no team news, injuries, line-ups, expected goals (xG), transfers, weather or
  motivation. Cup and European matches are not in the data, so "rest days" is not exact.
- **Elo settings are fixed** (K = 20, home advantage = 60, season regression = 20%). They were chosen by
  hand and not tuned.
- **The Poisson goals model** assumes the home and away goals are independent. In reality, it
  under-predicts draws a little (the Dixon–Coles adjustment fixes this).
- **The test period includes part of the 2026/27 season** (up to 2 September 2026).
- **Statistics**: one test period is one sample. A bootstrap interval treats bets as independent,
  but bets on the same weekend are related. The true uncertainty is probably wider.
- **Choosing the threshold** on validation is itself a small search. With only 6 options, the risk of
  overfitting is small, but it isn't zero.
- **Only tested on English leagues**. Other leagues will need their own run.

---

## 9. Running the tests

```powershell
python -m pytest            # all 24 tests, about 5 seconds, no internet needed
python -m pytest -v         # list each test by name
```

The tests use small, **made-up** leagues, so they don't need the real data. They check:
- **Elo**: points are conserved, home advantage works, and the end-of-season pull towards the average works.
- **No leakage**: changing a result never changes earlier features, deleting future matches never
  changes past features, and the split never overlaps.
- **Odds**: margin removal makes the probabilities add up to 1, keeps the favourite first, and shrinks
  long shots more with the power method.
- **Metrics**: perfect and "know nothing" predictions get the right scores, and a forecaster that is
  calibrated by construction gets a low calibration error.
- **Backtest**: profit, drawdown, the value rule, missing odds, and the no-bet choice when the model
  has no edge.
- **End to end**: the whole pipeline and the dashboard both run on fake data.

---

## 10. Ideas for next steps
1. Tune the Elo settings (K, home advantage) on the validation seasons.
2. Add the Dixon–Coles correction to the goals model.
3. Add more leagues, or pool several leagues together.
4. Add features such as xG, if you can find an openly licensed source.
5. Track **closing line value**: whether your bets beat the final odds. This is a faster and less noisy
   test of skill than profit.

Responsible gambling: if you or someone you know is struggling with gambling, help is available, for
example at <https://www.begambleaware.org> (UK) or from your local support service.
