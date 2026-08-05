"""Statistical metrics and comparison engine.

Provides RMSE, MAE, R2, bootstrap confidence intervals, and the PINN vs FEA
baseline comparison report used across the dashboard, visualizations and the
research paper statistics.
"""

from __future__ import annotations

import json
import os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT, "models")


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def r2(a, b):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    ss_res = np.sum((a - b) ** 2)
    ss_tot = np.sum((b - b.mean()) ** 2)
    return float(1 - ss_res / max(ss_tot, 1e-9))


def bootstrap_ci(a, b, metric=mae, n_boot=2000, ci=0.95, seed=1):
    """Bootstrap confidence interval for a metric between predicted/actual."""
    rng = np.random.default_rng(seed)
    a = np.asarray(a)
    b = np.asarray(b)
    n = len(a)
    if n == 0:
        return None
    idx = rng.integers(0, n, size=(n_boot, n))
    stats = np.array([metric(a[sample], b[sample]) for sample in idx])
    lo = np.percentile(stats, (1 - ci) / 2 * 100)
    hi = np.percentile(stats, (1 + ci) / 2 * 100)
    return {"point": metric(a, b), "ci_low": float(lo), "ci_high": float(hi)}


def load_test_predictions():
    path = os.path.join(MODELS_DIR, "test_predictions.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def comparison_report() -> dict:
    """PINN vs FEA report on the held-out test set (HIC target)."""
    pred = load_test_predictions()
    actual = np.array(pred["hic_actual"])
    pinn = np.array(pred["hic_pinn"])
    fea = np.array(pred["hic_fea"])

    pinn_rmse = rmse(pinn, actual)
    fea_rmse = rmse(fea, actual)
    return {
        "n_test": int(len(actual)),
        "pinn": {
            "rmse": pinn_rmse,
            "mae": mae(pinn, actual),
            "r2": r2(pinn, actual),
            "hic_ci": bootstrap_ci(pinn, actual, mae),
        },
        "fea_baseline": {
            "rmse": fea_rmse,
            "mae": mae(fea, actual),
            "r2": r2(fea, actual),
            "hic_ci": bootstrap_ci(fea, actual, mae),
        },
        "improvement_pct": float((1 - pinn_rmse / max(fea_rmse, 1e-9)) * 100),
    }
