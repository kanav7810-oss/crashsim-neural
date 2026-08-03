"""PINN training loop with physics-informed loss and FEA baseline comparison.

Trains CrashPinn on the processed dataset, tracks per-epoch validation HIC
RMSE against the linear FEA baseline, and writes:

  models/weights/pinn.pt             trained weights
  models/weights/state.json          scalers + metadata
  models/training_history.json       per-epoch loss + RMSE for the dashboard
  models/test_predictions.json       PINN vs FEA vs actual on the test set
  models/metrics.json                RMSE/MAE/R2 for both approaches

Usage:  python -m models.train
"""

from __future__ import annotations

import json
import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from simulation.physics import VehicleGeometry
from simulation.fea import fea_predict
from models.pinn import (CrashPinn, PinnScaler, physics_loss,
                         build_physics_features, save_checkpoint)
from data.preprocess import build_features, TARGETS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "processed")
MODEL_DIR = os.path.join(ROOT, "models")
WEIGHTS_DIR = os.path.join(MODEL_DIR, "weights")

EPOCHS = 1200
BATCH_SIZE = 64
LR = 1e-3
PHYSICS_WEIGHT = 0.6
PATIENCE = 150
SEED = 7

PHYS_COLS = {c: i for i, c in enumerate(
    ["mass_kg", "velocity_kmh", "angle_deg", "a_pillar_thickness_mm",
     "crumple_zone_length_m", "yield_strength_mpa", "section_height_mm",
     "section_width_mm", "year"])}


def load_processed():
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA_DIR, "crash_data_validated.csv"))
    with open(os.path.join(DATA_DIR, "split.json"), encoding="utf-8") as f:
        meta = json.load(f)
    X_raw, feature_cols = build_features(df)
    y_raw = df[TARGETS].to_numpy(dtype=np.float32)
    fmean = np.array(meta["feature_mean"], dtype=np.float32)
    fstd = np.array(meta["feature_std"], dtype=np.float32)
    tmin = np.array(meta["target_min"], dtype=np.float32)
    tmax = np.array(meta["target_max"], dtype=np.float32)
    X_norm = (X_raw - fmean) / fstd
    y_norm = (y_raw - tmin) / np.maximum(tmax - tmin, 1e-6)
    idx = {k: np.array(meta[k]) for k in ("train_idx", "val_idx", "test_idx")}
    return df, X_raw, X_norm, y_raw, y_norm, feature_cols, tmin, tmax, idx


def fea_hic_for_rows(df, rows_idx):
    import pandas as pd
    vals = []
    sub = df.iloc[rows_idx]
    for _, r in sub.iterrows():
        geom = VehicleGeometry(
            mass_kg=r["mass_kg"], velocity_kmh=r["velocity_kmh"],
            angle_deg=r["angle_deg"], a_pillar_thickness_mm=r["a_pillar_thickness_mm"],
            crumple_zone_length_m=r["crumple_zone_length_m"],
            yield_strength_mpa=r["yield_strength_mpa"],
            section_height_mm=r["section_height_mm"],
            section_width_mm=r["section_width_mm"],
            test_type=r["test_type"], vehicle_class=r["vehicle_class"],
            year=int(r["year"]))
        vals.append(fea_predict(geom)["hic"])
    return np.array(vals)


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    df, X_raw, X_norm, y_raw, y_norm, feature_cols, tmin, tmax, idx = load_processed()
    scaler = PinnScaler(tmin, tmax)
    x_phys_raw = build_physics_features(X_raw, feature_cols)

    tr, va, te = idx["train_idx"], idx["val_idx"], idx["test_idx"]
    X_tr = torch.tensor(X_norm[tr], dtype=torch.float32)
    y_tr = torch.tensor(y_norm[tr], dtype=torch.float32)
    xp_tr = torch.tensor(x_phys_raw[tr], dtype=torch.float32)
    X_va = torch.tensor(X_norm[va], dtype=torch.float32)
    y_va = torch.tensor(y_norm[va], dtype=torch.float32)
    xp_va = torch.tensor(x_phys_raw[va], dtype=torch.float32)
    X_te = torch.tensor(X_norm[te], dtype=torch.float32)
    xp_te = torch.tensor(x_phys_raw[te], dtype=torch.float32)

    model = CrashPinn(X_tr.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, mode="min", factor=0.5, patience=40)
    loader = DataLoader(TensorDataset(X_tr, y_tr, xp_tr),
                        batch_size=BATCH_SIZE, shuffle=True)

    fea_val_rmse = rmse(fea_hic_for_rows(df, va), y_raw[va, 0])
    print(f"FEA baseline val HIC RMSE: {fea_val_rmse:.1f}")

    history = {"epoch": [], "train_rmse": [], "val_rmse": [],
               "train_loss": [], "val_loss": [], "physics_loss": [],
               "fea_val_rmse": fea_val_rmse, "lr": []}
    best_val = float("inf")
    best_state = None
    patience_left = PATIENCE

    for epoch in range(1, EPOCHS + 1):
        model.train()
        tot_loss, tot_phys, n_batch = 0.0, 0.0, 0
        for xb, yb, xpb in loader:
            opt.zero_grad()
            pred = model(xb)
            data_loss = nn.functional.mse_loss(pred, yb)
            phys = physics_loss(scaler.denormalize(pred), xpb,
                                weight=PHYSICS_WEIGHT)
            loss = data_loss + phys
            loss.backward()
            opt.step()
            tot_loss += float(loss.detach()) * len(xb)
            tot_phys += float(phys.detach()) * len(xb)
            n_batch += len(xb)
        avg_loss = tot_loss / n_batch
        avg_phys = tot_phys / n_batch

        # Validation metrics
        model.eval()
        with torch.no_grad():
            pred_va = scaler.denormalize(model(X_va)).numpy()
            pred_tr = scaler.denormalize(model(X_tr)).numpy()
            val_phys = physics_loss(scaler.denormalize(model(X_va)), xp_va,
                                    weight=PHYSICS_WEIGHT)
            val_data = nn.functional.mse_loss(model(X_va), y_va)
        val_rmse_hic = rmse(pred_va[:, 0], y_raw[va, 0])
        train_rmse_hic = rmse(pred_tr[:, 0], y_raw[tr, 0])
        val_loss_total = float((val_data + val_phys).detach())

        sched.step(val_rmse_hic)
        cur_lr = opt.param_groups[0]["lr"]
        history["epoch"].append(epoch)
        history["train_rmse"].append(train_rmse_hic)
        history["val_rmse"].append(val_rmse_hic)
        history["train_loss"].append(avg_loss)
        history["val_loss"].append(val_loss_total)
        history["physics_loss"].append(avg_phys)
        history["lr"].append(cur_lr)

        if val_rmse_hic < best_val:
            best_val = val_rmse_hic
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_left = PATIENCE
        else:
            patience_left -= 1
        if epoch % 100 == 0 or epoch == 1:
            print(f"epoch {epoch:4d} loss={avg_loss:.4f} phys={avg_phys:.4f} "
                  f"trainRMSE={train_rmse_hic:6.1f} valRMSE={val_rmse_hic:6.1f} "
                  f"FEA={fea_val_rmse:.1f}")
        if patience_left <= 0:
            print(f"early stop at epoch {epoch}")
            break

    model.load_state_dict(best_state)
    model.eval()

    # Final metrics on all splits and targets
    with torch.no_grad():
        pred_te = scaler.denormalize(model(X_te)).numpy()
        pred_va = scaler.denormalize(model(X_va)).numpy()
        pred_tr = scaler.denormalize(model(X_tr)).numpy()

    def metrics_set(pred, y):
        out = {}
        for j, tname in enumerate(TARGETS):
            out[tname] = {
                "rmse": rmse(pred[:, j], y[:, j]),
                "mae": float(np.mean(np.abs(pred[:, j] - y[:, j]))),
                "r2": float(1 - np.sum((pred[:, j] - y[:, j]) ** 2)
                            / max(np.sum((y[:, j] - y[:, j].mean()) ** 2), 1e-9)),
            }
        return out

    fea_hic_te = fea_hic_for_rows(df, te)
    metrics = {
        "pinn": {
            "train": metrics_set(pred_tr, y_raw[tr]),
            "val": metrics_set(pred_va, y_raw[va]),
            "test": metrics_set(pred_te, y_raw[te]),
        },
        "fea_baseline": {
            "test": {
                "hic": {"rmse": rmse(fea_hic_te, y_raw[te, 0]),
                        "mae": float(np.mean(np.abs(fea_hic_te - y_raw[te, 0]))),
                        "r2": float(1 - np.sum((fea_hic_te - y_raw[te, 0]) ** 2)
                                    / max(np.sum((y_raw[te, 0] - y_raw[te, 0].mean()) ** 2), 1e-9))},
            }
        },
        "splits": {k: int(len(v)) for k, v in idx.items()},
        "epochs_trained": len(history["epoch"]),
        "best_val_hic_rmse": best_val,
        "fea_val_hic_rmse": fea_val_rmse,
        "improvement_pct": float(
            (1 - best_val / max(fea_val_rmse, 1e-9)) * 100),
    }

    save_checkpoint(model, os.path.join(WEIGHTS_DIR, "pinn.pt"))
    state = {
        "n_in": int(X_tr.shape[1]),
        "feature_columns": feature_cols,
        "targets": TARGETS,
        "target_min": tmin.tolist(),
        "target_max": tmax.tolist(),
        "feature_mean": np.mean(X_raw, axis=0).tolist(),
        "feature_std": np.std(X_raw, axis=0).tolist(),
    }
    with open(os.path.join(WEIGHTS_DIR, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    with open(os.path.join(MODEL_DIR, "training_history.json"), "w",
              encoding="utf-8") as f:
        json.dump(history, f)
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(MODEL_DIR, "test_predictions.json"), "w",
              encoding="utf-8") as f:
        json.dump({
            "hic_actual": y_raw[te, 0].tolist(),
            "hic_pinn": pred_te[:, 0].tolist(),
            "hic_fea": fea_hic_te.tolist(),
            "fatality_actual": y_raw[te, 4].tolist(),
            "fatality_pinn": pred_te[:, 3].tolist(),
        }, f, indent=2)

    print("\n=== Final test metrics ===")
    print("PINN  HIC: ", metrics["pinn"]["test"]["hic"])
    print("FEA   HIC: ", metrics["fea_baseline"]["test"]["hic"])
    print(f"Improvement over FEA baseline: {metrics['improvement_pct']:.1f}%")
    print("Saved weights, history, metrics, and test predictions.")


if __name__ == "__main__":
    main()