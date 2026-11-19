# Football prediction research system (beginner edition)

A small Python project that teaches you how to:

1. predict the probabilities of **home win / draw / away win** and the **number of goals** for football
   matches, in **11 main European leagues** (including Greece) and for **national teams**,
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
7. [Results](#7-results)
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

# 5b. Recommended: bring it up to date AND extend it back to 1993/94 from Football-Data.co.uk
#     (first time about 10 minutes; afterwards seconds). Re-run it any time.
python -m footy.update

# 6. Run the whole research pipeline (takes about 10 seconds; results go to outputs\)
python -m footy.pipeline

# 7. Open the dashboard in your browser (press Ctrl+C in PowerShell to stop it)
streamlit run dashboard.py

# 8. Run the automated tests
python -m pytest
```

**Optional extras** (sections 7b–7d explain each one):

```powershell
python -m footy.study                          # every main league + one pooled model (~1 minute)
python -m footy.international --download       # national teams (downloads ~4 MB the first time)
copy fixtures_template.csv my_fixtures.csv     # then type in odds you see, e.g. on Stoiximan
python -m footy.upcoming my_fixtures.csv       # predictions for upcoming matches vs your odds

# OR let it read fixtures, Stoiximan odds and recent results from Flashscore (personal use, section 7e)
python -m playwright install chromium          # once: downloads the browser it uses (~150 MB)
python -m footy.flashscore --leagues G1 --bookmaker Stoiximan
python -m footy.upcoming outputs\flashscore_fixtures.csv

# "What should I play today?" - reads the OPAP coupon on agones.gr (personal use, section 7f)
python -m footy.today
```

In the dashboard, use the **"Results to show"** menu on the left to switch between leagues and national teams.

If you use **Command Prompt** (cmd.exe) instead of PowerShell, step 3 is `.venv\Scripts\activate.bat`.
On macOS or Linux, use `python3 -m venv .venv` and `source .venv/bin/activate`.

To run a single league: `python -m footy.pipeline --divisions G1` (Greece). Codes: `E0`/`E1` England,
`SP1`/`SP2` Spain, `D1`/`D2` Germany, `I1`/`I2` Italy, `F1`/`F2` France, `N1` Netherlands, `P1` Portugal,
`B1` Belgium, `T1` Turkey, `G1` Greece, `SC0`/`SC1` Scotland. Where a second division exists, load it
too, so that Elo ratings can follow promoted and relegated teams. The dataset also has `ARG`, `BRA`,
`USA`, `JAP` and more for 2012–2024, but those are not studied here (see Limitations).

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
│   ├── pipeline.py        runs everything in order, writes outputs/
│   ├── study.py           runs the pipeline for every main league + a pooled model
│   ├── international.py   national-team version (neutral venues, match importance)
│   ├── upcoming.py        predictions for upcoming matches vs odds you type in
│   ├── flashscore.py      personal-use reader: Flashscore fixtures, odds and recent results
│   ├── agones.py          personal-use reader: OPAP coupon (codes + odds) from agones.gr
│   ├── today.py           "what should I play today?" - verdict per coupon code
│   ├── update.py          keeps the data current + adds 1993-2000 from Football-Data.co.uk
│   └── tune_elo.py        searches the best Elo settings on the validation seasons
├── dashboard.py           local Streamlit dashboard (only reads outputs/)
├── tests/                 automated tests (use small fake data, no download needed)
├── fixtures_template.csv  example file for upcoming matches and your own odds
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

**Keeping it up to date, with a bigger range.** The xgabora dataset is only updated every few months.
At the time of writing it ends on 3 September 2026. `python -m footy.update` fills the gap from
**Football-Data.co.uk**, the site the dataset itself was built from, which is updated twice a week:
- the first run downloads **every season since 1993/94** for all 17 divisions and saves them in
  `data/football-data/`. Later runs only re-download the current season;
- team names that the two sources spell differently are translated automatically. The program learns
  the translation from matches that appear in both (same league, date and score);
- only matches the main dataset doesn't have are added (newer ones, and the 1990s), to
  `data/Matches_update.csv`. Every command loads it automatically;
- `python -m footy.today` refreshes the current season by itself, and then fills the last few days
  (after Football-Data's latest update) from Flashscore.

So the data covers **1993/94 to last weekend** (results; odds from about 2000 on). After the first update,
re-run `python -m footy.study`: the models train on more seasons, and the numbers in section 7 will
change a little.
`python -m footy.study` uses 11 countries: about 150,000 matches.

**National teams** use a second dataset: *International football results from 1872* by Mart Jürisoo.
It is **CC0 (public domain)**, so you can use it for anything. It has about 50,000 matches, but **no odds**.

**Flashscore and Stoiximan.** Neither gives a licence to reuse its data, and Flashscore's terms forbid
scraping. Because of that, they are **never used to train or test the models**. You chose to use
Flashscore for your own private use, so there is an **optional** reader (section 7e). It reads upcoming
fixtures, the odds Flashscore shows (in Greece this includes Stoiximan.gr), and recent results, slowly
and a few pages at a time. Everything it collects stays on your computer. Don't share or publish it.
You can also type odds in by hand instead (section 7d).

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

## 7. Results

English Premier League + Championship. Test = 3,794 matches (2022/23 to September 2026), all with Bet365 odds.

**Home / draw / away (test seasons):**

| Model | Log loss | Brier | Accuracy | Calibration error |
|---|---|---|---|---|
| Elo baseline | 1.0251 | 0.6150 | 48.8% | 0.017 |
| Logistic regression + shots (best on validation) | 1.0178 | 0.6103 | 49.1% | 0.011 |
| Poisson goals model (H/D/A) | 1.0188 | 0.6107 | 49.3% | 0.016 |
| **Bookmaker, Bet365, margin removed** | **1.0080** | **0.6038** | **49.8%** | **0.006** |

**Goals:** the Poisson model's average error is 0.95 home goals and 0.83 away goals. Simply guessing
the league average gives 1.01 and 0.85. For over/under 2.5 goals, the model's Brier score is 0.247
against the bookmaker's 0.243, so the bookmaker is better here too.

**Hypothetical backtest:** every threshold lost money on the **validation** seasons (−6% to −11% ROI),
so the system chose **"No bet"**. For information only, the same thresholds on the test seasons also
lost money: −2% to −7% ROI over 550–2,990 bets, with drawdowns of 100–195 units. Every 95% interval
includes zero, with low ends between −10% and −21% and high ends between +1% and +8%. At the best market
price (unrealistic for one bettor), validation chose NO BET as well.

**Plain-English conclusion:** the models learn real patterns. They clearly beat the "know nothing"
guess (1.0986). But the bookmaker's prices already contain everything our simple features know, and
more (injuries, line-ups, team news). The model's "value bets" are mostly cases where it is wrong.
The Bet365 margin of about 5.5% guarantees a loss unless you have a real edge. This is the normal,
expected result for a first model, and it is exactly why the no-bet option exists.

(Your numbers may differ slightly if the dataset has been updated since this run.)

### 7b. All main leagues (`python -m footy.study`)

Same rules for every league: train up to 2017/18, choose on 2018/19–2021/22, test from 2022/23.
"Bookmaker" = Bet365 with the margin removed. The last column is for information only.

| League | Test matches | Elo log loss | Model log loss | Bookmaker log loss | Bookmaker margin | Chosen on validation | Test ROI at EV ≥ 5% (95% interval) |
|---|---|---|---|---|---|---|---|
| England | 3,794 | 1.0251 | 1.0178 | **1.0080** | 5.5% | NO BET | −4.8% (−11.4% to 2.3%) |
| Spain | 3,432 | 1.0162 | 1.0118 | **1.0007** | 6.1% | NO BET | −3.8% (−9.7% to 2.0%) |
| Germany | 2,484 | 1.0190 | 1.0178 | **1.0025** | 5.5% | EV ≥ 20% (see below) | −6.1% (−13.5% to 2.2%) |
| Italy | 3,079 | 1.0278 | 1.0253 | **1.0086** | 5.9% | NO BET | −12.3% (−18.4% to −6.1%) |
| France | 2,721 | 1.0376 | 1.0276 | **1.0148** | 6.4% | NO BET | −12.8% (−20.7% to −5.3%) |
| Netherlands | 1,257 | 0.9511 | 0.9489 | **0.9395** | 5.7% | NO BET | −5.9% (−16.7% to 5.6%) |
| Portugal | 1,257 | 0.9189 | 0.9204 | **0.9083** | 6.4% | NO BET | −11.5% (−21.8% to −1.1%) |
| Belgium | 1,277 | 1.0012 | 1.0039 | **0.9893** | 6.8% | NO BET | −14.7% (−25.6% to −4.2%) |
| Turkey | 1,340 | 0.9811 | 0.9844 | **0.9552** | 6.7% | NO BET | −24.8% (−33.8% to −15.1%) |
| Greece | 405 | 0.9605 | 0.9612 | **0.9406** | 7.6% | NO BET | −11.6% (−28.9% to 6.8%) |
| Scotland | 1,628 | 1.0021 | 1.0062 | **0.9854** | 7.6% | NO BET | −13.3% (−23.8% to −3.2%) |
| All pooled | 22,674 | 1.0082 | 1.0018 | **0.9909** | 6.1% | NO BET | −9.3% (−12.1% to −6.6%) |

What this shows:
- The **bookmaker is better in every league**. Smaller, less-watched leagues (Greece, Turkey, Scotland)
  are *not* easier. They have higher margins (6.7–7.6%), and our model is just as far behind.
- **Germany is a warning example.** On validation, a high-threshold rule (EV ≥ 15–20%) made a small
  profit, with a 95% interval far into negative territory: that could easily be luck. The system chose it
  anyway, because the rule only asks for a profit over at least 100 bets. On the test seasons it lost
  (−2.9% after improvement 1, −15.6% over 406 bets after improvement 3). Earlier, Scotland did the same:
  +0.05% on validation, then −21% on test. We did **not**
  change the rule after seeing this, because that would be cheating with the test data. Instead,
  `footy.today` only says PLAY when a rule *also* made money on the unseen test seasons.
- **Greece:** the dataset is missing the 2011/12, 2022/23 and 2023/24 seasons, which is why its test set
  is small (405 matches).

### Improvement 1: shot features (what changed and what it bought)

Shots and shots on target describe how well a team really plays better than goals, which are partly
luck. The model now also gets each team's average shots for and against, and shots on target for and
against, over its **previous 8 matches**. A match's own shots are never used: a test checks this.

Not every league has shot data from the start (Greece, Netherlands, Portugal, Belgium and Turkey only from
2017). So every model competes in two versions, with and without shots, and **the validation seasons
decide per league**. Gap to the bookmaker's log loss on the test seasons:

| League | Before | After | Gap closed |
|---|---|---|---|
| England | 0.0204 | 0.0142 | 30% |
| Spain | 0.0191 | 0.0153 | 20% |
| Germany | 0.0205 | 0.0161 | 21% |
| Italy | 0.0227 | 0.0174 | 23% |
| France | 0.0260 | 0.0176 | 32% |
| All pooled | 0.0201 | 0.0143 | 29% |
| NL, PT, BE, TR, GR, SCO | | | ≈0% (validation chose *no shots*: too little history) |

A real improvement, but not enough: the model is still behind the bookmaker in every league, and no
betting rule survived the unseen seasons. Once `python -m footy.update` adds more seasons with shots,
re-running `python -m footy.study` may let the smaller leagues use them too.

### Improvement 2: the best price (what it bought)

The price you bet at matters as much as the prediction. OPAP's coupon takes 6–11% per match; the best
price per outcome across several bookmakers usually takes only 2–4%.

**In `footy.today`:** for every coupon match, the program now opens the match's Flashscore odds page and
takes the **best price per outcome** among OPAP's coupon and the bookmakers listed in `MY_BOOKMAKERS` in
`footy/config.py`: Stoiximan, Novibet, bet365, Bwin, Interwetten, PameStoixima, Winmasters, Betsson,
Elabet and Fonbet by default. **Edit that list to the bookmakers where you actually have an account.**
Expected values and verdicts use those best prices. Example (21/11/2026, real odds):

```
[574] 19:30  Καλαμάτα - ΑΕΚ   (ΕΛΛΑΔΑ: Σούπερ Λιγκ 1)
      OPAP odds   1 8.00  X 5.00  2 1.35   (margin 6.6%)
      best price  1 8.25 (Stoiximan)  X 5.25 (PameStoixima)  2 1.38 (Novibet)   (margin 3.6%)
```

This adds one odds page per match (a few minutes for a full Saturday). `--opap-only` skips it.

**In the backtests:** the dataset has the best price across ~17 bookmakers for each match. That's an
*optimistic* upper bound: one person can't hold accounts everywhere or always catch the top price. Even
then, with the betting threshold chosen on validation as always:

| League | Bet365 margin | Best-price margin | Chosen on validation (best price) | Result on unseen test seasons |
|---|---|---|---|---|
| England, Spain, Italy, NL, PT, BE, GR, pooled | 5.5–7.6% | 1.5–3.4% | NO BET | – |
| Germany | 5.5% | 1.7% | EV ≥ 20% | +2.0% (729 bets, 95% interval −11% to +16%) |
| France | 6.4% | 1.8% | EV ≥ 20% | −12.1% (803 bets) |
| Turkey | 6.7% | 1.8% | EV ≥ 20% | −21.7% (436 bets) |
| Scotland | 7.6% | 2.9% | EV ≥ 15% | −14.3% (746 bets) |

**Conclusion:** the best price cuts the bookmaker's cut by about two-thirds, which makes any bet much
cheaper. But it doesn't create an edge by itself: even at the optimistic best prices, nothing is reliably
profitable on unseen seasons. Germany's +2.0% is well within luck. So the verdict rules stay the same, and
are still based on Bet365 prices, which one person really could get.

### Improvement 3: tuned Elo settings and promoted teams

**Promoted / relegated teams.** At a team's first match of a season the program compares its division
with last season's. The model gets four new inputs: home/away team *just promoted* and *just relegated*.
They are known before the season starts. A rating penalty for promoted teams was tried too, but tuning
found it doesn't help once the other settings are right, so it is set to 0.

**Tuned Elo settings.** `python -m footy.tune_elo` tries 64–144 combinations of K, home advantage, summer
pull-to-average and promotion shift, scoring each **only on the validation seasons** of all 11 leagues.
Result: K 20 → **15** (ratings react a bit more slowly), summer pull 20% → **5%**, home advantage 80
(anything from 70 to 110 scored the same). Validation log loss of the Elo baseline: 1.0224 → 1.0179.

Effect on the **unseen test seasons** (gap between the model's and the bookmaker's log loss):

| League | After improvement 1 | After improvement 3 |
|---|---|---|
| England | 0.0142 | **0.0098** |
| France | 0.0176 | **0.0127** |
| Spain | 0.0153 | **0.0111** |
| Greece | 0.0272 | **0.0206** |
| Scotland | 0.0266 | **0.0208** |
| Portugal | 0.0153 | **0.0121** |
| All pooled | 0.0143 | **0.0109** |
| Germany, Italy | 0.016–0.017 | 0.015–0.017 (small gain) |
| NL, BE, TR | | unchanged |

On the 21/11/2026 coupon this fixed the two promoted-team cases that looked wrong: Tottenham–Ipswich
(model 40% → 58% for Tottenham, OPAP 63%) and Coventry–Palace (model 55% → 39% for Coventry, OPAP 39%).
Not everything got better: for Newcastle–Arsenal the model now gives Arsenal 42% (OPAP 61%). Slower
ratings take longer to catch a team in strong current form.

Across improvements 1 and 3, the gap to the bookmaker shrank by about **half** in England (0.0204 →
0.0098), France and Spain. The model is still behind everywhere, and no betting rule survives the
unseen seasons, so the verdict is still NO BET.

### Improvement 4: match importance and team news

**Match importance (in the model, where validation wants it).** From the league table *before* each
match: table position, points behind the leader, points above the relegation zone (both divided by
the points still available, so "6 behind with 2 games left" ≠ "6 behind with 30 left"), how far the
season is, and a "nothing to play for" flag (late season, can't reach the top, can't go down). The league
format (teams, matches per team, e.g. Scotland's 38 games with 12 teams, Belgium's play-offs) is taken
from the *previous* season, so nothing from the future leaks in; the leakage test caught a first version
that did. Every model now competes in four versions (basic / + shots / + table / + both) and validation
picks per league.

Result on the unseen test seasons: **no reliable gain.** Scotland improved a little (gap 0.0208 → 0.0194),
and so did the pooled model (0.0109 → 0.0106). Spain, Germany and Portugal got slightly worse where
validation chose the table version. Bookmakers already price relegation battles and dead rubbers.

**Team news (shown, not used by the model).** `footy.today` now opens each match's Flashscore line-ups
page and shows who is **out** (injured, suspended, ill) and **doubtful**, whether the line-ups are
*predicted* or *official* (official ones appear about 1 hour before kickoff), and the average player rating
of each XI. Example (21/11/2026):

```
[574] 19:30  Καλαμάτα - ΑΕΚ
      model       1 10%  X 21%  2 70%
      team news   Καλαμάτα: OUT Vargas K. (Muscle Injury)
      team news   ΑΕΚ: OUT Joao Mario (Illness), Marin R. (Red Card), Zubkov O. (Broken Leg) | doubtful Alexiou C. (Injury)
      line-ups    predicted, average player rating 6.6 vs 7.2
      !! many absences: the model does NOT know about these. Trust its numbers less here.
```

Why the model doesn't use team news: to learn how much a missing player matters, it needs thousands of
past matches *with* their absences, and no dataset we have includes that. Any adjustment invented without
that history would be a guess dressed up as a calculation. So the information is shown for **you** to
weigh, with a warning when a team misses 3 or more players. New signings and transfers aren't covered;
the Elo summer adjustment only partly reflects squad changes. `--no-team-news` skips these pages.

### 7c. National teams (`python -m footy.international`)

Train 1990–2013, validation 2014–2018, test 2019 to November 2026 (7,874 matches). Earlier matches back
to 1872 are used only to warm up the Elo ratings. Differences from clubs:
- no home advantage at **neutral venues**;
- World Cup matches move ratings more than friendlies (bigger **K**);
- big wins move ratings more (a **goal-difference multiplier**).

| Model | Log loss | Brier | Accuracy |
|---|---|---|---|
| Elo baseline | 0.8613 | 0.5058 | 60.9% |
| Logistic regression | **0.8565** | **0.5028** | **60.9%** |
| Poisson goals model (H/D/A) | 0.8763 | 0.5143 | 59.8% |
| Naive (historical rates) | 1.0490 | 0.6324 | 48.0% |

National-team matches are more predictable than club matches, because the gaps in strength are bigger
(think Germany vs San Marino). On **major tournament finals** only (803 matches), log loss is 0.906.
There are **no odds** in this dataset, so we can't say whether the model would beat the bookmaker here,
and there's no backtest.

### 7d. Upcoming matches with your own odds (e.g. Stoiximan)

1. Copy `fixtures_template.csv` to `my_fixtures.csv` and open it in Excel or Notepad.
2. One row per match: league code, date, teams, and the three odds you see (home, draw, away).
   The `Bookmaker` column is just a note for yourself.
3. **Team names must match the dataset** (e.g. `Olympiakos`, `PAOK`, `AEK`, `Panathinaikos`). If a name
   is wrong, the program suggests the closest ones. Capital letters are fixed automatically.
4. The dataset ends in early September 2026. To catch the ratings up, add recent **results** as rows with
   `FTHome` and `FTAway` filled in. The program warns you when your data is more than 3 weeks behind.
5. Run `python -m footy.upcoming my_fixtures.csv`. The results go to `outputs/upcoming_predictions.csv`
   and the dashboard's **Upcoming** tab.

For each match you get: the model's probabilities and "fair odds" (1 ÷ probability), the bookmaker's
probabilities with the margin removed, the bookmaker's margin, the expected value of each outcome, the
expected goals, and P(over 2.5). When the model rates an outcome higher than the bookmaker, the file says
so, but **this is not a bet signal**: in every league above, the bookmaker was right more often than the model.

### 7e. Flashscore reader (personal use)

`python -m footy.flashscore --leagues G1 E0 --bookmaker Stoiximan` opens Flashscore in an invisible
Chrome browser and, for each league:
1. reads the **results** page and keeps every result played *after* the dataset ends (early September
   2026). This catches the Elo ratings and form up to today;
2. reads the **fixtures** page, and for each match in the next 10 days (at most 20 per league) opens its
   **odds** page and takes the 1X2 odds of your chosen bookmaker. If that bookmaker isn't listed, it uses
   the first one shown;
3. translates Flashscore's team names into the dataset's names ("Olympiacos Piraeus" → "Olympiakos",
   "AEK Athens" → "AEK"). Names it can't match are listed; add them to a file called
   `team_aliases.csv`, with the columns `flashscore,dataset`;
4. saves everything to `outputs/flashscore_fixtures.csv`, in the same format as `my_fixtures.csv`.

Then run `python -m footy.upcoming outputs\flashscore_fixtures.csv`, and look at the dashboard's
**Upcoming** tab.

Good to know:
- **The bookmakers shown depend on your location.** From Greece, Flashscore shows Stoiximan.gr,
  PameStoixima, Novibet, bet365, Bwin.gr and Interwetten. From another country you'll see other ones.
- **It is deliberately slow**: it waits 2–4 seconds between pages. One league takes about 1–2 minutes.
- Add `--show-browser` to watch it work. Use `--days-ahead` and `--max-matches` to read fewer pages.
- **It will break if Flashscore changes its website.** When it does, the message says nothing was
  collected; typing odds in by hand (7d) still works.
- Only the 1X2 odds, kickoff dates and results are read. Team news, line-ups and injuries are not.

### 7f. "What should I play today?" (`python -m footy.today`)

One command does the whole check:
1. reads today's **OPAP Pame Stoixima coupon on agones.gr**: the **match codes** (κωδικοί), teams and
   OPAP's 1 / X / 2 odds;
2. keeps only matches from the 11 studied leagues. Other leagues are skipped, because the model was never
   tested on them;
3. reads **Flashscore** for those leagues, to bring ratings up to date and to translate the Greek team
   names. Each coupon match is paired with that day's fixture in the same league. If the pairing isn't
   clear, the match is **skipped, never guessed**;
4. prints, for every code: OPAP's odds and margin, OPAP's chances (margin removed), the model's chances,
   the expected goals, and a **verdict**.

How the verdict is decided: a league counts as **playable** only if its betting rule made money on the
validation seasons **and** on the unseen test seasons, with at least 95% of bootstrap resamples positive.
If it is, a match gets **PLAY 1/X/2 (single, 1 unit)** when its expected value reaches that league's
threshold. Otherwise it gets **NO BET**. **Right now no league passes**, so the answer is always NO BET.
That's not a bug. It's what the evidence says, and the program will start saying PLAY only if a future,
better model earns it.

Example from the 22/11/2026 coupon (Greek Super League):

```
[668] 16:00  Λεβαδειακός - Ατρόμητος   (ΕΛΛΑΔΑ: Σούπερ Λιγκ 1)
      OPAP odds   1 2.40  X 3.00  2 3.00   (margin 8.3%)
      OPAP chance 1 38%  X 31%  2 31%
      model       1 51%  X 29%  2 19%   expected goals 1.4-0.9
      -> NO BET   (no betting rule passed validation)
```

The model likes the home side much more than OPAP does here. In the backtests, disagreements like
this lost money more often than they won.

Why "single, 1 unit" and never doubles or trebles: each selection carries OPAP's margin (usually 6–10%,
more than Bet365's 5.5% used in the backtests). In a treble the margins multiply, to roughly 20–25%.
Options: `--date 2026-11-22` (another day), `--leagues G1 E0` (only some leagues).

---

## 8. Limitations (please read)

- **Data licence**: the compilation is MIT-licensed, but the original source (Football-Data.co.uk)
  has no formal open licence. See [DATA_LICENSE.md](DATA_LICENSE.md).
- **When were the odds taken?** Football-Data.co.uk's notes say its Bet365 odds are collected on **Friday
  afternoons** for weekend games, and Tuesday afternoons for midweek games. They are *pre-closing* prices,
  so a bettor really could have got them. Prices move afterwards (team news), and we can't simulate that.
- **Best market price is optimistic**: it takes the best price from about 17 bookmakers after the fact.
  Getting it would need accounts everywhere, perfect timing, and no betting limits.
- **The backtest is simplified**: no betting limits, no stake restrictions or banned accounts, no
  odds moving after you bet, no taxes or fees, and every bet is assumed to be accepted at the listed price.
- **What the model still doesn't use**: injuries, suspensions and line-ups (shown next to each match in
  `footy.today`, but not learned from; there's no history of them), expected goals (xG), transfers and weather. Cup and European matches are not in the data, so "rest days" is not exact.
- **Elo settings** were tuned once, on the validation seasons, as one shared setting for all leagues
  (`python -m footy.tune_elo`). Re-run it after `footy.update` adds more seasons; per-league tuning might
  help a little more, but would risk fitting noise in small leagues.
- **The Poisson goals model** assumes the home and away goals are independent. In reality, it
  under-predicts draws a little (the Dixon–Coles adjustment fixes this).
- **The test period includes part of the 2026/27 season** (up to 2 September 2026).
- **Statistics**: one test period is one sample. A bootstrap interval treats bets as independent,
  but bets on the same weekend are related. The true uncertainty is probably wider.
- **Choosing the threshold** on validation is itself a small search. With only 6 options, the risk of
  overfitting is small, but it isn't zero.
- **Leagues not studied**: the extra leagues in the dataset (Argentina, Brazil, USA, Japan and others)
  run on a calendar-year season, but the code assumes seasons start in July. They also stop in 2024.
- **National teams have no odds**, so their results only measure prediction quality, not betting value.
  Team names in that dataset change over time (e.g. "Czechoslovakia"); they are treated as separate teams.
- **Upcoming predictions** are only as good as the ratings. If you don't add recent results, the ratings
  are frozen at early September 2026. Each country gets its own model, the one that won validation for that
  league in `python -m footy.study` (with or without shots). Run the study first; otherwise a plain logistic
  regression without shots is used.
- **The Football-Data.co.uk updater** was written from the site's published column guide, and tested on
  made-up files in that format. This test computer can't reach the site, so it hasn't run against the real
  files yet. Check the "Saved ... extra matches" message after your first run. Team-name translation needs
  at least 2 shared matches per club, so a club that appears only in brand-new data keeps Football-Data's
  spelling.
- **agones.gr reader**: personal use only, one page per run. It depends on the site's current layout.
  It was tested on saved copies of the real pages (this test computer can't reach the site). The matching
  of competitions to our leagues uses agones.gr's competition numbers, checked on one weekend's coupon.
  OPAP's rules on the minimum number of selections per slip are not checked.
- **Odds you type in** are only checked loosely, so mistakes in typing go straight into the comparison.
- **The Flashscore reader** goes against Flashscore's terms, which forbid scraping. It's included only
  because you asked for it for private use. It depends on the site's current layout, and it was tested on
  saved copies of real Flashscore pages, not live from Greece (this test computer can't reach Flashscore).
  Results it adds are trusted as they are, and newly promoted clubs are matched to the dataset's older
  club of the same name (e.g. "Iraklis 1908" → "Iraklis").

---

## 9. Running the tests

```powershell
python -m pytest            # all 74 tests, about 20 seconds, no internet needed
python -m pytest -v         # list each test by name
```

The tests use small, **made-up** leagues, so they don't need the real data. They check:
- **Elo**: points are conserved, home advantage works, and the end-of-season pull towards the average works.
- **No leakage**: changing a result never changes earlier features, deleting future matches never
  changes past features, a match's own shots never reach its features, and the split never overlaps.
- **Odds**: margin removal makes the probabilities add up to 1, keeps the favourite first, and shrinks
  long shots more with the power method.
- **Metrics**: perfect and "know nothing" predictions get the right scores, and a forecaster that is
  calibrated by construction gets a low calibration error.
- **Backtest**: profit, drawdown, the value rule, missing odds, and the no-bet choice when the model
  has no edge.
- **National teams**: neutral venues get no home advantage, more important matches move ratings more,
  and there is no leakage.
- **Upcoming matches**: margin maths, typed-in results updating the ratings, team-name suggestions, and
  the out-of-date warning.
- **Flashscore reader**: dates without a year, odds-page addresses, choosing the bookmaker, team-name
  matching, skipping results already in the dataset, and the page-reading code (on hand-written sample pages).
- **"What to play today"**: reading coupon rows and codes, Greek→Latin names (incl. ά-ι / ϊ), pairing
  lookalike names correctly (Brighton vs Everton), no pairing across leagues or days, and the verdict rules.
- **Match importance and team news**: table position / gaps / "nothing to play for", reading
  injured / suspended / doubtful players and line-up ratings, and the many-absences warning.
- **Promoted teams**: detected from the division change, flagged for the whole season, rating shift
  applied once (when switched on).
- **Data updater**: reading old and new Football-Data CSV layouts, learning team-name translations from
  shared matches, and never adding a match twice.
- **End to end**: the whole pipeline and the dashboard (every results folder) run on fake data.

---

## 10. Ideas for next steps
1. Tune the Elo settings (K, home advantage) on the validation seasons.
2. Add the Dixon–Coles correction to the goals model.
3. Add more leagues, or pool several leagues together.
4. Add features such as xG, if you can find an openly licensed source.
5. Use a **licensed** live-data API (with your own key) for fixtures, line-ups and odds, instead of typing them in.
6. Track **closing line value**: whether your bets beat the final odds. This is a faster and less noisy
   test of skill than profit.

Responsible gambling: if you or someone you know is struggling with gambling, help is available, for
example at <https://www.begambleaware.org> (UK) or from your local support service.
