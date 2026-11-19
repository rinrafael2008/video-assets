"""Step 2a: a simple Elo rating system.

Every team has a number (rating). Before a match we compare the two numbers to get
an *expected score* for the home team (1 = win, 0.5 = draw, 0 = loss). After the
match, ratings move towards what actually happened:

    new_rating = old_rating + K * (actual_score - expected_score)

The winner gains exactly what the loser loses, so points are conserved.
"""
from __future__ import annotations

import numpy as np

from footy import config


def expected_home_score(home_rating: float, away_rating: float,
                        home_advantage: float = config.ELO_HOME_ADVANTAGE) -> float:
    diff = home_rating + home_advantage - away_rating
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def actual_home_score(home_goals: int, away_goals: int) -> float:
    if home_goals > away_goals:
        return 1.0
    if home_goals == away_goals:
        return 0.5
    return 0.0


class Elo:
    def __init__(self, k=config.ELO_K, home_advantage=config.ELO_HOME_ADVANTAGE,
                 start=config.ELO_START, season_regression=config.ELO_SEASON_REGRESSION):
        self.k = k
        self.home_advantage = home_advantage
        self.start = start
        self.season_regression = season_regression
        self.ratings: dict[str, float] = {}

    def rating(self, team: str) -> float:
        if team not in self.ratings:
            # Newcomers (e.g. promoted from a league we don't load) are usually weaker
            # than established teams, so start them at the 20th percentile.
            self.ratings[team] = (float(np.percentile(list(self.ratings.values()), 20))
                                  if len(self.ratings) >= 10 else self.start)
        return self.ratings[team]

    def new_season(self) -> None:
        """Pull everyone a little towards the average (squads change in summer)."""
        if not self.ratings:
            return
        mean = float(np.mean(list(self.ratings.values())))
        r = self.season_regression
        self.ratings = {t: (1 - r) * v + r * mean for t, v in self.ratings.items()}

    def update(self, home: str, away: str, home_goals: int, away_goals: int) -> None:
        h, a = self.rating(home), self.rating(away)
        change = self.k * (actual_home_score(home_goals, away_goals)
                           - expected_home_score(h, a, self.home_advantage))
        self.ratings[home] = h + change
        self.ratings[away] = a - change
