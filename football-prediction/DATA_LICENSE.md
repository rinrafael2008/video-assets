# Dataset and licence notes

**Dataset used:** *Club Football Match Data (2000–2026)* by Adam Gábor (GitHub user `xgabora`)
- Repository: https://github.com/xgabora/Club-Football-Match-Data
- File: `data/Matches.csv` (about 239,000 matches, 38 leagues, July 2000 to September 2026)
- Licence of the repository: **MIT**. The MIT licence lets anyone use, copy, modify and redistribute
  the files, commercially or not, as long as the copyright notice is kept. That includes training
  machine-learning models. We do **not** redistribute the CSV in this project; `python -m footy.data`
  downloads it from the original repository.

**Where the numbers come from (please read):**
- The dataset README says match results, statistics and odds were collected from
  **Football-Data.co.uk**, and Elo ratings from **ClubElo**.
- Football-Data.co.uk offers its CSV files for free download "for football betting system
  development", but it does **not** publish a formal open-data licence. Its disclaimer covers
  liability only and does not mention reuse. The MIT licence covers the dataset author's own
  compilation; it cannot give you more rights than the original sources gave.
- **What this means for you:** personal, educational and research use (what this project does)
  is the normal, intended use of these files. If you plan to **sell** a product built on this data,
  or **republish** the data, check with Football-Data.co.uk first.
- Facts such as "Arsenal 2–1 Chelsea on a given date" are generally not protected by copyright.
  Odds compilations and database rights (for example the EU/UK database right) are less clear.
  This note is not legal advice.

**Alternatives with explicit open licences, but no betting odds:**
- openfootball / football.csv: public domain (CC0), results only
- Fjelstul English Football Database: CC BY-SA 4.0, results only

None of the clearly open-licensed datasets we found include bookmaker odds. This project needs odds
for the market comparison and the backtest, which is why we chose this dataset.

Attribution: "Club Football Match Data" © 2025 xgabora, MIT licence. Source data: Football-Data.co.uk, ClubElo.

---

# National teams dataset

**International football results from 1872 to 2026** by Mart Jürisoo
- Repository: https://github.com/martj42/international_results (file `results.csv`)
- Licence: **CC0 1.0 (public domain dedication)**, so it can be used for any purpose, including ML training,
  with no conditions. Downloaded by `python -m footy.international --download`, not redistributed here.
- Contains results only (no odds).

# Stoiximan, Flashscore and other betting/score sites

These sites give no licence to reuse their data, and Flashscore's terms (personal use only) forbid
scraping. **They are never used to train or evaluate the models.**

At the user's explicit request, for private personal use only, `footy/flashscore.py` can read
upcoming fixtures, the odds Flashscore displays (including Stoiximan.gr when viewed from Greece) and
recent results. It reads a few pages slowly and saves them only to the git-ignored `outputs/` folder.
Using it is your own decision and responsibility. Do not publish, share or sell anything it collects.
