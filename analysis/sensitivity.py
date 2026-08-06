"""Sensitivity analysis: which input features most affect HIC.

Primary method is SHAP (PermutationExplainer) against the trained PINN. When
the shap library is unavailable or fails, a permutation-importance fallback
(re-shuffle each feature on the test set and measure the RMSE increase) is
used so the dashboard always has a sensitivity chart.
"""

from __future__ import annotations

import json
import os
import numpy as np
import pandas as pd
import torch

from models.pinn import CrashPinn, PinnScaler
from analysis.metrics import rmse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "processed")
WEIGHTS_DIR = os.path.join(ROOT, "models", "weights")


def _load_model_and_data():
    with open(os.path.join(WEIGHTS_DIR, "state.json"), encoding="utf-8") as f:
        state = json.load(f)
    with open(os.path.join(DATA_DIR, "split.json"), encoding="utf-8") as f:
        split = json.load(f)
    df = pd.read_csv(os.path.join(DATA_DIR, "crash_data_validated.csv"))
    from data.preprocess import build_features, TARGETS
    X_raw, feature_cols = build_features(df)
    y_raw = df[TARGETS].to_numpy(dtype=np.float32)
    fmean = np.array(state["feature_mean"], dtype=np.float32)
    fstd = np.array(state["feature_std"], dtype=np.float32)
    X_norm = (X_raw - fmean) / fstd
    scaler = PinnScaler(np.array(state["target_min"], dtype=np.float32),
                        np.array(state["target_max"], dtype=np.float32))
    model = CrashPinn(state["n_in"])
    model.load_state_dict(torch.load(
        os.path.join(WEIGHTS_DIR, "pinn.pt"), map_location="cpu"))
    model.eval()
    te = np.array(split["test_idx"])
    return model, scaler, X_raw[te], X_norm[te], y_raw[te, 0], feature_cols


def _predict_np(model, scaler, X_norm):
    with torch.no_grad():
        return scaler.denormalize(model(
            torch.tensor(np.asarray(X_norm, dtype=np.float32)))).numpy()[:, 0]


def permutation_importance(model, scaler, X_norm, y_actual, feature_cols,
                           n_repeats=10, seed=3):
    rng = np.random.default_rng(seed)
    base = rmse(_predict_np(model, scaler, X_norm), y_actual)
    imp = {}
    X = X_norm.copy()
    for j, name in enumerate(feature_cols):
        scores = []
        for _ in range(n_repeats):
            X_pert = X.copy()
            X_pert[:, j] = rng.permutation(X_pert[:, j])
            scores.append(rmse(_predict_np(model, scaler, X_pert), y_actual))
        imp[name] = float(max(np.mean(scores) - base, 0.0))
    total = max(sum(imp.values()), 1e-9)
    return {k: v / total for k, v in imp.items()}


def shap_importance(model, scaler, X_norm, feature_cols, sample=60):
    """SHAP PermutationExplainer mean |SHAP| normalized to a fraction."""
    try:
        import shap
    except Exception:
        return None
    try:
        x_sample = X_norm[:sample]
        explainer = shap.PermutationExplainer(
            lambda x: _predict_np(model, scaler, x), x_sample, seed=11)
        sv = explainer(x_sample, max_evals=2000)
        mean_abs = np.abs(sv.values).mean(axis=0)
        total = max(mean_abs.sum(), 1e-9)
        return {name: float(v / total)
                for name, v in zip(feature_cols, mean_abs)}
    except Exception:
        return None


def feature_labels(feature_cols: list[str]) -> list[str]:
    return ["Mass", "Velocity", "Angle", "A-pillar thickness",
            "Crumple zone length", "Yield strength", "Section height",
            "Section width", "Model year", "SUV", "Sedan", "Truck", "EV",
            "Test: frontal", "Test: rollover", "Test: side"]


def run_sensitivity() -> dict:
    model, scaler, X_raw, X_norm, y_actual, feature_cols = _load_model_and_data()
    result = shap_importance(model, scaler, X_norm, feature_cols)
    method = "shap"
    if result is None:
        result = permutation_importance(model, scaler, X_norm, y_actual,
                                        feature_cols)
        method = "permutation"
    labels = feature_labels(feature_cols)
    ordered = sorted(result.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "method": method,
        "features": [{"feature": name, "label": labels[feature_cols.index(name)],
                      "importance": value} for name, value in ordered],
    }


if __name__ == "__main__":
    print(json.dumps(run_sensitivity(), indent=2))
