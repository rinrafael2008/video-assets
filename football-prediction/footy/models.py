"""Step 4: the models.

* EloBaseline   - uses ONE number (the Elo difference) and learns how it maps to
                  home / draw / away probabilities with a multinomial logistic regression.
* candidate_outcome_models - scikit-learn models that use all the features.
* GoalsModel    - two Poisson regressions: expected home goals and expected away goals.
                  From those we get a full scoreline distribution and P(over 2.5 goals).

Every model is a scikit-learn Pipeline, so the imputer and scaler are fitted on the
training data only (fitting them on all data would leak test information).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import poisson
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from footy.features import FEATURE_COLUMNS

OUTCOMES = ["H", "D", "A"]   # column order of every probability array in this project


def outcome_index(results) -> np.ndarray:
    return np.array([OUTCOMES.index(r) for r in results])


def _predict_hda(model, X) -> np.ndarray:
    """predict_proba with columns guaranteed in H, D, A order."""
    proba = model.predict_proba(X)
    order = [list(model.classes_).index(o) for o in OUTCOMES]
    return proba[:, order]


class EloBaseline:
    name = "Elo baseline"
    features = ["elo_diff"]

    def __init__(self):
        self.model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))

    def fit(self, df):
        self.model.fit(df[self.features], df["FTResult"])
        return self

    def predict_proba(self, df) -> np.ndarray:
        return _predict_hda(self.model, df[self.features])


class SklearnOutcomeModel:
    features = FEATURE_COLUMNS

    def __init__(self, name, estimator, scale=True):
        self.name = name
        steps = [SimpleImputer(strategy="median")]
        if scale:
            steps.append(StandardScaler())
        self.model = make_pipeline(*steps, estimator)

    def fit(self, df):
        self.model.fit(df[self.features], df["FTResult"])
        return self

    def predict_proba(self, df) -> np.ndarray:
        return _predict_hda(self.model, df[self.features])


def candidate_outcome_models():
    """A few reasonable settings. The validation set decides which one wins."""
    return [
        SklearnOutcomeModel("Logistic regression (C=0.1)", LogisticRegression(C=0.1, max_iter=2000)),
        SklearnOutcomeModel("Logistic regression (C=1.0)", LogisticRegression(C=1.0, max_iter=2000)),
        SklearnOutcomeModel("Gradient boosting (shallow)", HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.03, max_iter=200, l2_regularization=1.0,
            early_stopping=False, random_state=0), scale=False),
    ]


class GoalsModel:
    name = "Poisson goals model"
    features = FEATURE_COLUMNS
    MAX_GOALS = 10

    def __init__(self, alpha=1.0):
        def pipe():
            return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                 PoissonRegressor(alpha=alpha, max_iter=1000))
        self.home, self.away = pipe(), pipe()

    def fit(self, df):
        self.home.fit(df[self.features], df["FTHome"])
        self.away.fit(df[self.features], df["FTAway"])
        return self

    def expected_goals(self, df):
        return self.home.predict(df[self.features]), self.away.predict(df[self.features])

    def score_matrix(self, lam_h, lam_a) -> np.ndarray:
        """P(home scores i, away scores j), assuming the two are independent."""
        g = np.arange(self.MAX_GOALS + 1)
        ph = poisson.pmf(g[None, :], np.asarray(lam_h)[:, None])
        pa = poisson.pmf(g[None, :], np.asarray(lam_a)[:, None])
        m = ph[:, :, None] * pa[:, None, :]
        return m / m.sum(axis=(1, 2), keepdims=True)   # put the tiny ">10 goals" tail back

    def predict(self, df) -> dict:
        lam_h, lam_a = self.expected_goals(df)
        m = self.score_matrix(lam_h, lam_a)
        i, j = np.meshgrid(np.arange(m.shape[1]), np.arange(m.shape[2]), indexing="ij")
        return {
            "exp_home_goals": lam_h,
            "exp_away_goals": lam_a,
            "p_over25": (m * (i + j > 2)).sum(axis=(1, 2)),
            "p_home_poisson": (m * (i > j)).sum(axis=(1, 2)),
            "p_draw_poisson": (m * (i == j)).sum(axis=(1, 2)),
            "p_away_poisson": (m * (i < j)).sum(axis=(1, 2)),
        }
