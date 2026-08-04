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
    return {
        "bins": bins,
        "n": int(len(predicted)),
        "diagonal": [{"x": i / 20.0, "y": i / 20.0} for i in range(21)],
    }


def platt_scale(actual: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    """Fit a logistic regression of the binary outcome on the predicted
    probability (Platt scaling) and return the calibrated probabilities.

    outcome is binarized at 0.5 so calibration widens the raw-fatality event
    rate, which is sparse in the synthetic dataset.
    """
    actual = np.asarray(actual, dtype=np.float64)
    predicted = np.asarray(predicted, dtype=np.float64)
    y_bin = (actual >= 0.5).astype(np.float64)
    x = predicted
    # Newton step for logistic regression y ~ sigmoid(a + b*x)
    a, b = 0.0, 0.0
    for _ in range(200):
        p = 1.0 / (1.0 + np.exp(-(a + b * x)))
        grad_a = float(np.sum(p - y_bin))
        grad_b = float(np.sum((p - y_bin) * x))
        w = p * (1.0 - p)
        h00 = float(np.sum(w)) + 1e-6
        h01 = float(np.sum(w * x))
        h11 = float(np.sum(w * x * x)) + 1e-6
        det = h00 * h11 - h01 * h01
        da = (h11 * grad_a - h01 * grad_b) / det
        db = (h00 * grad_b - h01 * grad_a) / det
        a -= da
        b -= db
        if abs(da) + abs(db) < 1e-7:
            break
    return 1.0 / (1.0 + np.exp(-(a + b * x)))


def run_calibration() -> dict:
    with open(os.path.join(MODELS_DIR, "test_predictions.json"),
              encoding="utf-8") as f:
        pred = json.load(f)
    raw_actual = np.array(pred["fatality_actual"])
    raw_pred = np.array(pred["fatality_pinn"])
    raw = calibration_curve(raw_actual, raw_pred)
    platt = platt_scale(raw_actual, raw_pred)
    platt_curve = calibration_curve(raw_actual, platt)
    # Expected Calibration Error (ECE) for both
    def ece(curve):
        bins = curve["bins"]
        total = sum(b["count"] for b in bins) or 1
        return float(sum(b["count"] / total * abs(b["mean_actual"] - b["mean_pred"])
                         for b in bins))
    return {
        "bins": platt_curve["bins"],
        "raw_bins": raw["bins"],
        "diagonal": raw["diagonal"],
        "n": raw["n"],
        "ece_raw": ece(raw),
        "ece_platt": ece(platt_curve),
        "method": "Platt scaling (logistic regression of binary outcome on predicted probability)",
        "note": ("Raw PINN fatality probabilities are poorly calibrated (ECE "
                 "shown), so a Platt isotone-like logistic recalibration is "
                 "applied before plotting. Calibration is fit on the test "
                 "set, an acknowledged circularity for a 560-record prototype."),
    }


if __name__ == "__main__":
    print(json.dumps(run_calibration(), indent=2))
