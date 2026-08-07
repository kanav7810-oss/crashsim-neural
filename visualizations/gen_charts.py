"""Generate all 8 statistical visualizations.

Each chart is emitted twice:
  - Plotly JSON (visualizations/json/) for the interactive dashboard
  - Matplotlib PNG (visualizations/figures/) for the PDF research report

Usage:  python -m visualizations.gen_charts
"""

from __future__ import annotations

import json
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats

from simulation.physics import VehicleGeometry, solve_crush, energy_absorbed
from analysis.sensitivity import run_sensitivity
from analysis.calibration import run_calibration

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "processed")
JSON_DIR = os.path.join(ROOT, "visualizations", "json")
PNG_DIR = os.path.join(ROOT, "visualizations", "figures")

# Dashboard theme (matches app/src/theme.js and DESIGN.md)
ACCENT = "#c79a55"
ACCENT_H = "#ddb56e"
SECONDARY = "#56c09a"
OK = "#53be70"
WARN = "#f5ae39"
DANGER = "#f14d4f"
TEXT = "#e7e3dc"
TEXT2 = "#a6a29b"
MUTED = "#7a756e"
GRID = "#1c1b18"
BRONZE_SCALE = [
    [0.0, "#0f0d0a"], [0.25, "#4a3a1e"], [0.5, "#967033"],
    [0.75, "#c79a55"], [1.0, "#e7d9bd"]]

FIXED_GEOM = dict(mass_kg=1500.0, angle_deg=0.0, yield_strength_mpa=400.0,
                  section_height_mm=150.0, section_width_mm=100.0,
                  test_type="frontal", vehicle_class="sedan", year=2020)

_LOADED_MODEL = {}


def _get_model():
    if not _LOADED_MODEL:
        import torch
        from models.pinn import CrashPinn, PinnScaler
        with open(os.path.join(ROOT, "models", "weights", "state.json"),
                  encoding="utf-8") as f:
            state = json.load(f)
        model = CrashPinn(state["n_in"])
        model.load_state_dict(torch.load(
            os.path.join(ROOT, "models", "weights", "pinn.pt"),
            map_location="cpu"))
        model.eval()
        scaler = PinnScaler(np.array(state["target_min"], dtype=np.float32),
                            np.array(state["target_max"], dtype=np.float32))
        _LOADED_MODEL.update(model=model, scaler=scaler,
                             mean=np.array(state["feature_mean"], dtype=np.float32),
                             std=np.array(state["feature_std"], dtype=np.float32),
                             cols=state["feature_columns"])
    return _LOADED_MODEL


def _pinn_hic(features: list[dict]) -> np.ndarray:
    """features: list of dicts with physical feature values (plus
    vehicle_class / test_type) matching preprocess feature order."""
    import torch
    ctx = _get_model()
    idx = {c: i for i, c in enumerate(ctx["cols"])}
    X = np.zeros((len(features), len(ctx["cols"])), dtype=np.float32)
    for i, row in enumerate(features):
        for name, val in row.items():
            if name == "vehicle_class":
                col = f"vehicle_class_{val}"
                if col in idx:
                    X[i, idx[col]] = 1.0
            elif name == "test_type":
                col = f"test_type_{val}"
                if col in idx:
                    X[i, idx[col]] = 1.0
            elif name in idx:
                X[i, idx[name]] = val
    X_norm = (X - ctx["mean"]) / ctx["std"]
    with torch.no_grad():
        pred = ctx["scaler"].denormalize(
            ctx["model"](torch.tensor(X_norm))).numpy()
    return pred[:, 0]


def load_df():
    return pd.read_csv(os.path.join(DATA_DIR, "crash_data_validated.csv"))


# ---------------------------------------------------------------------------
# Chart 1: PINN vs FEA RMSE across training epochs
# ---------------------------------------------------------------------------
def chart_accuracy_curves() -> dict:
    with open(os.path.join(ROOT, "models", "training_history.json"),
              encoding="utf-8") as f:
        hist = json.load(f)
    fig = go.Figure()
    fig.add_scatter(x=hist["epoch"], y=hist["train_rmse"], name="PINN train",
                    mode="lines", line=dict(color=ACCENT, width=2))
    fig.add_scatter(x=hist["epoch"], y=hist["val_rmse"], name="PINN validation",
                    mode="lines", line=dict(color=SECONDARY, width=2))
    fig.add_hline(y=hist["fea_val_rmse"], line_dash="dash",
                  line_color=MUTED, annotation_text="FEA baseline RMSE",
                  annotation_position="right")
    fig.update_layout(title="PINN vs FEA: HIC RMSE across training epochs",
                      xaxis_title="Epoch", yaxis_title="HIC RMSE",
                      legend=dict(orientation="h", y=1.08))
    return _as_json(fig)


# ---------------------------------------------------------------------------
# Chart 2: 3D injury risk surface (velocity x thickness x HIC)
# ---------------------------------------------------------------------------
def chart_injury_surface() -> dict:
    vels = np.linspace(25, 75, 28)
    thks = np.linspace(0.8, 2.0, 28)
    Z = np.zeros((len(thks), len(vels)))
    for i, t in enumerate(thks):
        for j, v in enumerate(vels):
            row = dict(FIXED_GEOM)
            row.update(velocity_kmh=v, a_pillar_thickness_mm=t)
            Z[i, j] = _pinn_hic([row])[0]
    fig = go.Figure(data=[go.Surface(
        x=vels, y=thks, z=Z, colorscale=BRONZE_SCALE,
        colorbar=dict(title="Predicted HIC"))])
    fig.update_layout(title="Injury risk surface: velocity vs A-pillar thickness",
                      scene=dict(xaxis_title="Velocity (km/h)",
                                 yaxis_title="A-pillar thickness (mm)",
                                 zaxis_title="HIC"))
    return _as_json(fig)


# ---------------------------------------------------------------------------
# Chart 3: Vehicle class comparison with 95% CI
# ---------------------------------------------------------------------------
def chart_class_comparison() -> dict:
    df = load_df()
    rows = []
    for cls, sub in df.groupby("vehicle_class"):
        mu = sub["hic"].mean()
        se = sub["hic"].std(ddof=1) / np.sqrt(len(sub))
        z = stats.t.ppf(0.975, df=len(sub) - 1)
        rows.append(dict(cls=cls, mean=mu, ci_low=mu - z * se,
                         ci_high=mu + z * se, n=len(sub)))
    rows.sort(key=lambda r: r["mean"])
    fig = go.Figure()
    for i, r in enumerate(rows):
        fig.add_trace(go.Bar(name=r["cls"], x=[r["cls"]], y=[r["mean"]],
                             marker_color=ACCENT,
                             marker_opacity=0.95 - 0.18 * i,
                             error_y=dict(type="data", symmetric=False,
                                          color=MUTED, thickness=1,
                                          array=[r["ci_high"] - r["mean"]],
                                          arrayminus=[r["mean"] - r["ci_low"]])))
    fig.update_layout(title="Mean HIC by vehicle class (95% CI)",
                      yaxis_title="HIC", barmode="group")
    return _as_json(fig)


# ---------------------------------------------------------------------------
# Chart 4: Crumple zone efficiency heatmap (energy absorbed per kg)
# ---------------------------------------------------------------------------
def chart_crumple_efficiency() -> dict:
    lengths = np.linspace(0.5, 1.2, 30)
    thks = np.linspace(0.8, 2.0, 30)
    Z = np.zeros((len(thks), len(lengths)))
    for i, t in enumerate(thks):
        for j, L in enumerate(lengths):
            geom = VehicleGeometry(mass_kg=1500, velocity_kmh=56,
                                   a_pillar_thickness_mm=t,
                                   crumple_zone_length_m=L,
                                   yield_strength_mpa=400,
                                   section_height_mm=150,
                                   section_width_mm=100,
                                   test_type="frontal", vehicle_class="sedan")
            d = solve_crush(geom, 0.85)
            Z[i, j] = energy_absorbed(d, geom) / geom.mass_kg
    fig = go.Figure(data=[go.Heatmap(
        x=np.round(lengths, 2), y=np.round(thks, 2), z=Z,
        colorscale=BRONZE_SCALE,
        colorbar=dict(title="kJ absorbed per kg"))])
    fig.update_layout(title="Crumple zone efficiency: absorbed energy per kg",
                      xaxis_title="Crumple zone length (m)",
                      yaxis_title="A-pillar thickness (mm)")
    return _as_json(fig)


# ---------------------------------------------------------------------------
# Chart 5: Sensitivity analysis (SHAP / permutation)
# ---------------------------------------------------------------------------
def chart_sensitivity() -> dict:
    sens = run_sensitivity()
    names = [s["label"] for s in sens["features"]][:12]
    values = [s["importance"] for s in sens["features"]][:12]
    fig = go.Figure(go.Bar(x=values, y=names, orientation="h",
                           marker_color=ACCENT))
    fig.update_layout(title=f"Sensitivity of HIC to input features "
                            f"({sens['method']})",
                      xaxis_title="Normalized importance", yaxis_title="")
    return _as_json(fig)


# ---------------------------------------------------------------------------
# Chart 6: Historical NHTSA HIC trend 2000-2024
# ---------------------------------------------------------------------------
def chart_historical_trend() -> dict:
    df = load_df()
    yearly = df.groupby("year")["hic"].median().reset_index()
    x = yearly["year"].to_numpy()
    y = yearly["hic"].to_numpy()
    slope, intercept, _, _, _ = stats.linregress(x, y)
    fig = go.Figure()
    fig.add_scatter(x=x, y=y, name="Median HIC by year", mode="markers+lines",
                    marker=dict(size=6, color=ACCENT),
                    line=dict(color=ACCENT, width=1.5))
    fig.add_scatter(x=x, y=slope * x + intercept, name="Linear trend",
                    mode="lines", line=dict(color=MUTED, dash="dash"))
    fig.update_layout(title="NHTSA HIC safety trend 2000-2024",
                      xaxis_title="Model year", yaxis_title="Median HIC",
                      annotations=[dict(x=0.98, y=0.05, xref="paper",
                                        yref="paper", showarrow=False,
                                        text=f"slope {slope:.1f} HIC/year")])
    return _as_json(fig)


# ---------------------------------------------------------------------------
# Chart 7: Fatality probability by crash type
# ---------------------------------------------------------------------------
def chart_fatality_by_crash_type() -> dict:
    df = load_df()
    fig = go.Figure()
    order = ["frontal", "side", "rollover"]
    for tt in order:
        sub = df[df["test_type"] == tt]["fatality_prob"]
        fig.add_trace(go.Violin(y=sub, x=[tt] * len(sub), name=tt,
                                box_visible=True, meanline_visible=True,
                                line_color=ACCENT,
                                fillcolor="rgba(199,154,85,0.18)"))
    fig.update_layout(title="Occupant fatality probability by crash type",
                      yaxis_title="Fatality probability")
    return _as_json(fig)


# ---------------------------------------------------------------------------
# Chart 8: Model calibration plot
# ---------------------------------------------------------------------------
def chart_calibration() -> dict:
    cal = run_calibration()
    bins = cal["bins"]
    fig = go.Figure()
    fig.add_scatter(x=[d["x"] for d in cal["diagonal"]],
                    y=[d["y"] for d in cal["diagonal"]], name="Perfect",
                    mode="lines", line=dict(dash="dash", color=MUTED))
    fig.add_scatter(x=[b["mean_pred"] for b in bins],
                    y=[b["mean_actual"] for b in bins],
                    name="PINN calibration",
                    mode="markers+lines", marker=dict(size=11, color=ACCENT),
                    line=dict(color=ACCENT, width=2))
    fig.update_layout(title="Model calibration: predicted vs actual fatality",
                      xaxis_title="Predicted probability",
                      yaxis_title="Actual probability")
    return _as_json(fig)


def _as_json(fig):
    return json.loads(fig.to_json())


CHART_BUILDERS = {
    "accuracy_curves": chart_accuracy_curves,
    "injury_surface": chart_injury_surface,
    "class_comparison": chart_class_comparison,
    "crumple_efficiency": chart_crumple_efficiency,
    "sensitivity": chart_sensitivity,
    "historical_trend": chart_historical_trend,
    "fatality_by_crash_type": chart_fatality_by_crash_type,
    "calibration": chart_calibration,
}


def _save_pngs():
    """Matplotlib PNG versions for the PDF research report."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def fig_wrap(ax, title, xlab, ylab):
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(xlab, fontsize=9)
        ax.set_ylabel(ylab, fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig

    df = load_df()

    # 1 accuracy curves
    with open(os.path.join(ROOT, "models", "training_history.json"),
              encoding="utf-8") as f:
        hist = json.load(f)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(hist["epoch"], hist["train_rmse"], label="PINN train")
    ax.plot(hist["epoch"], hist["val_rmse"], label="PINN validation")
    ax.axhline(hist["fea_val_rmse"], ls="--", color="r", label="FEA baseline")
    ax.legend(fontsize=8)
    fig_wrap(ax, "PINN vs FEA: HIC RMSE across epochs", "Epoch", "HIC RMSE")
    fig.savefig(os.path.join(PNG_DIR, "1_accuracy_curves.png"), dpi=130)
    plt.close(fig)

    # 2 injury surface
    vels = np.linspace(25, 75, 28)
    thks = np.linspace(0.8, 2.0, 28)
    Z = np.zeros((len(thks), len(vels)))
    for i, t in enumerate(thks):
        for j, v in enumerate(vels):
            row = dict(FIXED_GEOM)
            row.update(velocity_kmh=v, a_pillar_thickness_mm=t)
            Z[i, j] = _pinn_hic([row])[0]
    fig, ax = plt.subplots(figsize=(7, 5), subplot_kw=dict(projection="3d"))
    VV, TT = np.meshgrid(vels, thks)
    ax.plot_surface(VV, TT, Z, cmap="viridis", alpha=0.95)
    ax.set_xlabel("Velocity (km/h)", fontsize=8)
    ax.set_ylabel("Thickness (mm)", fontsize=8)
    ax.set_zlabel("HIC", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG_DIR, "2_injury_surface.png"), dpi=130)
    plt.close(fig)

    # 3 class comparison with CI
    fig, ax = plt.subplots(figsize=(7, 4))
    rows = []
    for cls, sub in df.groupby("vehicle_class"):
        mu = sub["hic"].mean()
        se = sub["hic"].std(ddof=1) / np.sqrt(len(sub))
        z = stats.t.ppf(0.975, df=len(sub) - 1)
        rows.append((cls, mu, z * se))
    rows.sort(key=lambda r: r[1])
    names = [r[0] for r in rows]
    means = [r[1] for r in rows]
    errs = [r[2] for r in rows]
    ax.bar(names, means, yerr=errs, capsize=5, color=ACCENT, alpha=0.85)
    fig_wrap(ax, "Mean HIC by vehicle class (95% CI)", "Class", "HIC")
    fig.savefig(os.path.join(PNG_DIR, "3_class_comparison.png"), dpi=130)
    plt.close(fig)

    # 4 crumple efficiency heatmap
    lengths = np.linspace(0.5, 1.2, 30)
    thks2 = np.linspace(0.8, 2.0, 30)
    H = np.zeros((len(thks2), len(lengths)))
    for i, t in enumerate(thks2):
        for j, L in enumerate(lengths):
            geom = VehicleGeometry(mass_kg=1500, velocity_kmh=56,
                                   a_pillar_thickness_mm=t,
                                   crumple_zone_length_m=L,
                                   yield_strength_mpa=400,
                                   section_height_mm=150, section_width_mm=100)
            H[i, j] = energy_absorbed(solve_crush(geom, 0.85), geom) / 1500.0
    fig, ax = plt.subplots(figsize=(7, 4.5))
    im = ax.imshow(H, aspect="auto", origin="lower", cmap="plasma",
                   extent=[lengths.min(), lengths.max(), thks2.min(), thks2.max()])
    ax.set_xlabel("Crumple zone length (m)", fontsize=9)
    ax.set_ylabel("A-pillar thickness (mm)", fontsize=9)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("kJ/kg", fontsize=8)
    ax.set_title("Crumple zone efficiency: absorbed energy per kg", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG_DIR, "4_crumple_efficiency.png"), dpi=130)
    plt.close(fig)

    # 5 sensitivity
    sens = run_sensitivity()
    names5 = [s["label"] for s in sens["features"]][:12]
    vals5 = [s["importance"] for s in sens["features"]][:12]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(names5[::-1], vals5[::-1], color="#967033", alpha=0.85)
    ax.set_title(f"Sensitivity of HIC ({sens['method']})", fontsize=11)
    ax.set_xlabel("Normalized importance", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG_DIR, "5_sensitivity.png"), dpi=130)
    plt.close(fig)

    # 6 historical trend
    yearly = df.groupby("year")["hic"].median().reset_index()
    x6 = yearly["year"].to_numpy()
    y6 = yearly["hic"].to_numpy()
    slope, intercept, *_ = stats.linregress(x6, y6)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(x6, y6, "o-", color=SECONDARY, ms=4)
    ax.plot(x6, slope * x6 + intercept, "--", color="#dc2626")
    ax.set_title(f"NHTSA HIC safety trend 2000-2024 (slope {slope:.1f}/yr)",
                 fontsize=11)
    ax.set_xlabel("Model year", fontsize=9)
    ax.set_ylabel("Median HIC", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG_DIR, "6_historical_trend.png"), dpi=130)
    plt.close(fig)

    # 7 fatality by crash type
    fig, ax = plt.subplots(figsize=(7, 4))
    data7 = [df[df["test_type"] == tt]["fatality_prob"]
             for tt in ["frontal", "side", "rollover"]]
    ax.violinplot(data7, showmeans=True, showmedians=True)
    ax.set_xticks([1, 2, 3], ["frontal", "side", "rollover"])
    ax.set_ylabel("Fatality probability", fontsize=9)
    ax.set_title("Occupant fatality probability by crash type", fontsize=11)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG_DIR, "7_fatality_by_crash_type.png"), dpi=130)
    plt.close(fig)

    # 8 calibration
    cal = run_calibration()
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "--", color="#9ca3af", label="Perfect")
    ax.plot([b["mean_pred"] for b in cal["bins"]],
            [b["mean_actual"] for b in cal["bins"]], "o-", color=ACCENT)
    ax.set_title("Model calibration: predicted vs actual fatality", fontsize=11)
    ax.set_xlabel("Predicted probability", fontsize=9)
    ax.set_ylabel("Actual probability", fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG_DIR, "8_calibration.png"), dpi=130)
    plt.close(fig)


def main():
    os.makedirs(JSON_DIR, exist_ok=True)
    os.makedirs(PNG_DIR, exist_ok=True)
    manifest = []
    for name, builder in CHART_BUILDERS.items():
        chart = builder()
        with open(os.path.join(JSON_DIR, f"{name}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(chart, f)
        manifest.append(name)
        print(f"chart {name} OK")
    with open(os.path.join(JSON_DIR, "manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(manifest, f)
    _save_pngs()
    print("PNG figures saved to visualizations/figures/")
    print("All 8 charts generated.")


if __name__ == "__main__":
    main()
