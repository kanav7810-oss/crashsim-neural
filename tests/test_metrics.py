"""Unit tests for metrics and the safety projection engine.

Run with:  python -m pytest tests -q
"""

import os

import numpy as np
import pytest

from analysis.metrics import rmse, mae, r2, bootstrap_ci
from analysis.safety import run_safety_projection

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _perfect(a):
    return np.asarray(a, dtype=np.float64)


def test_rmse_zero_when_perfect():
    a = np.array([1.0, 2.0, 3.0])
    assert rmse(a, a) == 0.0


def test_mae_matches_mean_abs_distance():
    a = np.array([1.0, 5.0, 9.0])
    b = np.array([2.0, 4.0, 7.0])
    assert mae(a, b) == pytest.approx(4.0 / 3.0)


def test_r2_is_one_for_perfect_and_positive_correlated():
    a = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    assert r2(a, a) == pytest.approx(1.0)
    b = a + np.array([0.1, -0.1, 0.1, -0.1, 0.1])
    assert 0.9 < r2(a, b) < 1.0


def test_bootstrap_ci_brackets_point_estimate():
    # Regression: CI must contain the point estimate (was inflated ~3x by an
    # independent-resample bug that destroyed (pred, actual) pairing).
    rng = np.random.default_rng(0)
    actual = rng.normal(loc=400.0, scale=120.0, size=200)
    pred = actual + rng.normal(scale=60.0, size=200)
    ci = bootstrap_ci(actual, pred, metric=mae, n_boot=500)
    assert ci["ci_low"] <= ci["point"] <= ci["ci_high"]
    # CI width should be modest relative to the point, not ~3x inflated.
    assert (ci["ci_high"] - ci["ci_low"]) < ci["point"]


def test_bootstrap_ci_requires_correlation_respected():
    # Random pairing inflates error; correct pairing stays near metric(a,a)=0.
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    ci = bootstrap_ci(a, a, metric=mae, n_boot=300)
    assert ci["point"] == pytest.approx(0.0, abs=1e-9)
    assert ci["ci_low"] <= ci["point"] <= ci["ci_high"]


def test_safety_projection_outputs_are_valid_ranges():
    out = run_safety_projection()
    assert 0.0 <= out["current_mean_fatality"] <= 1.0
    assert 0.0 <= out["optimal_mean_fatality"] <= 1.0
    assert 0.0 <= out["relative_risk_reduction"] <= 1.0
    assert out["projected_lives_saved_per_year"] >= 0
    assert "methodology" in out