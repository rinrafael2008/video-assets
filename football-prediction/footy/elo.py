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
                 start=config.ELO_START, season_regression=config.ELO_SEASON_REGRESSION,
                 promotion_shift=config.ELO_PROMOTION_SHIFT):
        self.k = k
        # Rating points added when a team goes UP a division (usually negative: the champion of
        # the 2nd division is weaker than its rating, earned against weaker teams, suggests).
        # A relegated team gets the opposite.
        self.promotion_shift = promotion_shift
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

    def change_division(self, team: str, promoted: bool) -> None:
        self.ratings[team] = self.rating(team) + (self.promotion_shift if promoted else -self.promotion_shift)

    def new_season(self) -> None:
        """Pull everyone a little towards the average (squads change in summer)."""
        if not self.ratings:
            return
        mean = float(np.mean(list(self.ratings.values())))
        r = self.season_regression
        self.ratings = {t: (1 - r) * v + r * mean for t, v in self.ratings.items()}

    def home_edge(self, neutral: bool = False) -> float:
        """Home advantage in rating points (0 when the match is at a neutral venue)."""
        return 0.0 if neutral else self.home_advantage

    def update(self, home: str, away: str, home_goals: int, away_goals: int,
               k: float | None = None, neutral: bool = False) -> None:
        """`k` can be raised for important matches (e.g. a World Cup final)."""
        h, a = self.rating(home), self.rating(away)
        change = (self.k if k is None else k) * (actual_home_score(home_goals, away_goals)
                                                 - expected_home_score(h, a, self.home_edge(neutral)))
        self.ratings[home] = h + change
        self.ratings[away] = a - change
