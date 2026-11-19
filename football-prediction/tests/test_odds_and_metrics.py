import numpy as np
import pytest

from footy import evaluate as ev
from footy.odds import overround, remove_margin_power, remove_margin_proportional


def test_margin_removal_sums_to_one():
    odds = np.array([[2.0, 3.4, 3.8], [1.3, 5.5, 10.0]])
    for f in (remove_margin_proportional, remove_margin_power):
        p = f(odds)
        assert np.allclose(p.sum(axis=1), 1)
        assert (np.argsort(p, axis=1) == np.argsort(1 / odds, axis=1)).all()  # order kept


def test_fair_odds_unchanged():
    fair = np.array([[2.0, 4.0, 4.0]])
    assert np.allclose(remove_margin_proportional(fair), [[0.5, 0.25, 0.25]])
    assert np.allclose(remove_margin_power(fair), [[0.5, 0.25, 0.25]], atol=1e-6)
    assert overround(fair)[0] == pytest.approx(1.0)


def test_power_method_takes_more_from_longshots():
    odds = np.array([[1.3, 5.5, 10.0]])
    assert remove_margin_power(odds)[0, 2] < remove_margin_proportional(odds)[0, 2]


def test_metric_reference_values():
    y = np.array([0, 1, 2])
    perfect = np.eye(3)
    uniform = np.full((3, 3), 1 / 3)
    assert ev.log_loss(perfect, y) == pytest.approx(0, abs=1e-12)
    assert ev.brier(perfect, y) == 0
    assert ev.accuracy(perfect, y) == 1
    assert ev.log_loss(uniform, y) == pytest.approx(np.log(3))
    assert ev.brier(uniform, y) == pytest.approx(2 / 3)


def test_calibration_of_a_calibrated_forecaster_is_small():
    rng = np.random.default_rng(0)
    p = rng.dirichlet([3, 2, 2], size=20000)
    y = np.array([rng.choice(3, p=row) for row in p])
    assert ev.expected_calibration_error(p, y) < 0.02
    t = ev.calibration_table(p, y)
    assert set(t.outcome) == {"H", "D", "A"} and t.n.sum() == 3 * len(p)
