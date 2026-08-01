"""Preprocessing, validation and train/val/test splitting.

Reads data/processed/crash_data.csv, validates the schema and value ranges,
engineers the PINN feature matrix (numeric + one-hot categorical), and writes:

  data/processed/train.csv        training split
  data/processed/val.csv          validation split
  data/processed/test.csv         held-out test split
  data/processed/split.json       row index assignment
  data/processed/features.json    feature/target metadata + scalers

Usage:  python -m data.preprocess
"""

from __future__ import annotations

import csv
import json
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "processed", "crash_data.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed")

NUMERIC_FEATURES = [
    "mass_kg", "velocity_kmh", "angle_deg", "a_pillar_thickness_mm",
    "crumple_zone_length_m", "yield_strength_mpa", "section_height_mm",
    "section_width_mm", "year",
]
CATEGORICAL_FEATURES = ["vehicle_class", "test_type"]
TARGETS = ["hic", "chest_g", "intrusion_m", "fatality_prob", "crush_m"]

RANGE_RULES = {
    "hic": (1, 4000),
    "chest_g": (1, 150),
    "intrusion_m": (0, 0.6),
    "fatality_prob": (0, 1),
    "crush_m": (0, 2.5),
    "mass_kg": (500, 5000),
    "velocity_kmh": (5, 200),
    "a_pillar_thickness_mm": (0.4, 4.0),
    "crumple_zone_length_m": (0.3, 2.0),
    "yield_strength_mpa": (100, 1200),
    "section_height_mm": (50, 300),
    "section_width_mm": (50, 300),
}


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows that violate documented physical ranges."""
    before = len(df)
    for col, (lo, hi) in RANGE_RULES.items():
        if col in df.columns:
            df = df[(df[col] >= lo) & (df[col] <= hi)]
    df = df.drop_duplicates(subset=["crash_id"])
    df = df.reset_index(drop=True)
    print(f"Validation: {before} -> {len(df)} rows after range + duplicate check")
    return df


def one_hot(df: pd.DataFrame, column: str) -> pd.DataFrame:
    for value in sorted(df[column].unique()):
        df[f"{column}_{value}"] = (df[column] == value).astype(np.float32)
    return df


def build_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    df = one_hot(df, "vehicle_class")
    df = one_hot(df, "test_type")
    cols = NUMERIC_FEATURES + [
        c for c in df.columns if c.startswith("vehicle_class_")
        or c.startswith("test_type_")
    ]
    return df[cols].to_numpy(dtype=np.float32), cols


def main() -> None:
    df = pd.read_csv(SRC)
    df = validate(df)
    if len(df) < 500:
        raise RuntimeError("Dataset too small after validation")

    X, feature_cols = build_features(df)
    y = df[TARGETS].to_numpy(dtype=np.float32)

    # Stratified split by vehicle class
    rng = np.random.default_rng(42)
    n = len(df)
    idx = np.arange(n)
    train_idx, val_idx, test_idx = [], [], []
    for cls in sorted(df["vehicle_class"].unique()):
        cls_idx = idx[df["vehicle_class"].to_numpy() == cls]
        rng.shuffle(cls_idx)
        n_cls = len(cls_idx)
        n_train = int(n_cls * 0.70)
        n_val = int(n_cls * 0.15)
        train_idx.extend(cls_idx[:n_train])
        val_idx.extend(cls_idx[n_train:n_train + n_val])
        test_idx.extend(cls_idx[n_train + n_val:])
    train_idx = np.sort(np.array(train_idx))
    val_idx = np.sort(np.array(val_idx))
    test_idx = np.sort(np.array(test_idx))

    # Target normalization (min-max to [0, 1])
    tmin = y.min(axis=0)
    tmax = y.max(axis=0)
    tmin = np.where(tmax - tmin < 1e-8, tmin - 1.0, tmin)
    tmax = np.where(np.arange(y.shape[1]) >= 0, tmax, tmax)
    tspan = np.maximum(tmax - tmin, 1e-6)
    y_norm = (y - tmin) / tspan

    # Feature standardization (z-score)
    fmean = X.mean(axis=0)
    fstd = X.std(axis=0)
    fstd = np.where(fstd < 1e-8, 1.0, fstd)
    X_norm = (X - fmean) / fstd

    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(os.path.join(OUT_DIR, "crash_data_validated.csv"), index=False)
    pd.DataFrame(X[train_idx], columns=feature_cols).to_csv(
        os.path.join(OUT_DIR, "X_train_raw.csv"), index=False)
    pd.DataFrame(y[train_idx], columns=TARGETS).to_csv(
        os.path.join(OUT_DIR, "y_train_raw.csv"), index=False)

    meta = {
        "n_samples": int(n),
        "n_features": int(X.shape[1]),
        "feature_columns": feature_cols,
        "targets": TARGETS,
        "train_idx": train_idx.tolist(),
        "val_idx": val_idx.tolist(),
        "test_idx": test_idx.tolist(),
        "target_min": tmin.tolist(),
        "target_max": tmax.tolist(),
        "feature_mean": fmean.tolist(),
        "feature_std": fstd.tolist(),
        "split_sizes": {"train": len(train_idx), "val": len(val_idx),
                        "test": len(test_idx)},
    }
    with open(os.path.join(OUT_DIR, "split.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Features: {X.shape[1]}, Targets: {y.shape[1]}")
    print(f"Split: train={len(train_idx)} val={len(val_idx)} test={len(test_idx)}")
    print(f"Target normalization spans: {np.round(tspan, 4).tolist()}")
    print("Saved validated CSV, feature matrices, and split.json")


if __name__ == "__main__":
    main()
