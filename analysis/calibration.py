"""Model calibration: predicted vs actual fatality probabilities."""

from __future__ import annotations

import json
import os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT, "models")


def calibration_curve(actual: np.ndarray, predicted: np.ndarray,
                      n_bins: int = 10) -> dict:
    """Bin predicted probabilities and average the actual outcomes per bin."""
    actual = np.asarray(actual, dtype=np.float64)
    predicted = np.asarray(predicted, dtype=np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (predicted >= lo) & (predicted < hi)
        if i == n_bins - 1:
            mask |= predicted == 1.0
        if mask.sum() == 0:
            continue
        bins.append({
            "bin": i,
            "bin_center": float((lo + hi) / 2),
            "mean_pred": float(predicted[mask].mean()),
            "mean_actual": float(actual[mask].mean()),
            "count": int(mask.sum()),
        })
    # Always include the diagonal reference for plotting
    return {
        "bins": bins,
        "n": int(len(predicted)),
        "diagonal": [{"x": i / 20.0, "y": i / 20.0} for i in range(21)],
    }


def run_calibration() -> dict:
    with open(os.path.join(MODELS_DIR, "test_predictions.json"),
              encoding="utf-8") as f:
        pred = json.load(f)
    return calibration_curve(
        np.array(pred["fatality_actual"]), np.array(pred["fatality_pinn"]))


if __name__ == "__main__":
    print(json.dumps(run_calibration(), indent=2))
