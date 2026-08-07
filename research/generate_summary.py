"""Generate research/stats_summary.json for the paper.

Compiles: mean HIC prediction error, PINN vs FEA accuracy improvement,
train/val/test split sizes, measured PINN vs FEA computational speedup, and
the projected lives-saved safety figure.

Usage:  python -m research.generate_summary
"""

from __future__ import annotations

import json
import os
import time
import numpy as np

from analysis.metrics import comparison_report
from analysis.safety import run_safety_projection

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT, "models")
OUT = os.path.join(ROOT, "research", "stats_summary.json")


def _time_pinn_inference(n=1000) -> float:
    import torch
    from models.pinn import CrashPinn
    state = json.load(open(os.path.join(ROOT, "models", "weights", "state.json"),
                           encoding="utf-8"))
    model = CrashPinn(state["n_in"])
    model.load_state_dict(torch.load(
        os.path.join(ROOT, "models", "weights", "pinn.pt"), map_location="cpu"))
    model.eval()
    x = torch.rand(n, state["n_in"])
    with torch.no_grad():
        start = time.perf_counter()
        for _ in range(3):
            model(x)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
    elapsed = (time.perf_counter() - start) / 3.0
    return elapsed / n * 1000.0   # ms per prediction


def _time_fea_inference(n=50) -> float:
    from simulation.fea import fea_predict
    from simulation.physics import VehicleGeometry
    geom = VehicleGeometry()
    start = time.perf_counter()
    for _ in range(n):
        fea_predict(geom)
    elapsed = time.perf_counter() - start
    return elapsed / n * 1000.0   # ms per prediction


def main():
    report = comparison_report()
    with open(os.path.join(MODELS_DIR, "metrics.json"), encoding="utf-8") as f:
        metrics = json.load(f)

    pinn_ms = _time_pinn_inference()
    fea_ms = _time_fea_inference()

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mean_hic_prediction_error": {
            "mae": report["pinn"]["mae"],
            "rmse": report["pinn"]["rmse"],
            "r2": report["pinn"]["r2"],
            "mae_ci_95": report["pinn"]["hic_ci"],
        },
        "fea_baseline": {
            "mae": report["fea_baseline"]["mae"],
            "rmse": report["fea_baseline"]["rmse"],
            "r2": report["fea_baseline"]["r2"],
        },
        "accuracy_improvement_over_fea_pct": report["improvement_pct"],
        "sample_sizes": {
            "train": metrics["splits"]["train_idx"],
            "val": metrics["splits"]["val_idx"],
            "test": metrics["splits"]["test_idx"],
        },
        "total_records": sum(metrics["splits"].values()),
        "computational_speedup": {
            "pinn_inference_ms": round(pinn_ms, 4),
            "fea_inference_ms": round(fea_ms, 4),
            "speedup_x": round(fea_ms / max(pinn_ms, 1e-9), 2),
        },
        "safety_improvement": run_safety_projection(),
        "training": {
            "epochs_trained": metrics["epochs_trained"],
            "best_val_hic_rmse": metrics["best_val_hic_rmse"],
            "fea_val_hic_rmse": metrics["fea_val_hic_rmse"],
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {OUT}")
    print(f"PINN HIC MAE {summary['mean_hic_prediction_error']['mae']:.1f} "
          f"vs FEA {summary['fea_baseline']['mae']:.1f} "
          f"({summary['accuracy_improvement_over_fea_pct']:.1f}% better)")
    print(f"Speedup: PINN {pinn_ms:.4f} ms vs FEA {fea_ms:.4f} ms "
          f"({summary['computational_speedup']['speedup_x']}x)")
    print(f"Lives saved / year: "
          f"{summary['safety_improvement']['projected_lives_saved_per_year']:.0f}")


if __name__ == "__main__":
    main()
