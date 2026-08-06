"""FastAPI backend for the CRASHSIM-NEURAL dashboard.

Serves the trained PINN, physics simulator, FEA baseline, dataset explorer,
charts, training monitor (SSE), parameter sweeps, comparison tool, research
summary and PDF export.

Run with:  uvicorn api.main:app --port 8000
"""

from __future__ import annotations

import io
import json
import os
import time
from typing import Literal, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from simulation.physics import VehicleGeometry, run_crash
from simulation.fea import fea_predict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "processed")
WEIGHTS_DIR = os.path.join(ROOT, "models", "weights")
CHARTS_DIR = os.path.join(ROOT, "visualizations", "json")
FIGURES_DIR = os.path.join(ROOT, "visualizations", "figures")
RESEARCH_DIR = os.path.join(ROOT, "research")
REPORTS_DIR = os.path.join(ROOT, "data", "reports")
# Vercel functions have a read-only filesystem except /tmp; fall back to
# /tmp when the project tree isn't writable (Vercel) or VERCEL env is set.
if os.environ.get("VERCEL") or not os.access(os.path.dirname(REPORTS_DIR), os.W_OK):
    REPORTS_DIR = os.path.join("/tmp", "crashsim_reports")

app = FastAPI(title="CRASHSIM-NEURAL", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"])

_VALID_CLASSES = {"sedan", "suv", "truck", "ev"}
_VALID_TESTS = {"frontal", "side", "rollover"}

# ---------------------------------------------------------------------------
# Model context — loaded eagerly at import for fast cold starts
# ---------------------------------------------------------------------------
_CTX = {}
_MODEL_LOAD_ERROR = None


def _load_model_context():
    """Load PINN model and scaler. Runs once at import."""
    global _CTX, _MODEL_LOAD_ERROR
    if _CTX:
        return _CTX
    try:
        import torch
        from models.pinn import CrashPinn, PinnScaler
        state_path = os.path.join(WEIGHTS_DIR, "state.json")
        weights_path = os.path.join(WEIGHTS_DIR, "pinn.pt")
        if not os.path.exists(state_path):
            raise FileNotFoundError(f"Missing {state_path}")
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"Missing {weights_path}")
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
        model = CrashPinn(state["n_in"])
        model.load_state_dict(torch.load(weights_path, map_location="cpu"))
        model.eval()
        _CTX = {
            "model": model,
            "scaler": PinnScaler(
                np.array(state["target_min"], dtype=np.float32),
                np.array(state["target_max"], dtype=np.float32)),
            "mean": np.array(state["feature_mean"], dtype=np.float32),
            "std": np.array(state["feature_std"], dtype=np.float32),
            "cols": state["feature_columns"],
            "targets": state["targets"],
        }
        return _CTX
    except Exception as e:
        _MODEL_LOAD_ERROR = e
        raise


def get_ctx():
    if _MODEL_LOAD_ERROR:
        raise _MODEL_LOAD_ERROR
    return _load_model_context()


def load_dataset() -> pd.DataFrame:
    if "df" not in _CTX:
        _CTX["df"] = pd.read_csv(os.path.join(DATA_DIR,
                                              "crash_data_validated.csv"))
    return _CTX["df"]


def geometry_to_features(g: dict) -> np.ndarray:
    ctx = get_ctx()
    idx = {c: i for i, c in enumerate(ctx["cols"])}
    X = np.zeros(len(ctx["cols"]), dtype=np.float32)
    for col in ctx["cols"]:
        if col.startswith("vehicle_class_") or col.startswith("test_type_"):
            continue
        if col in g:
            X[idx[col]] = g[col]
    vc = f"vehicle_class_{g.get('vehicle_class', 'sedan')}"
    tt = f"test_type_{g.get('test_type', 'frontal')}"
    if vc in idx:
        X[idx[vc]] = 1.0
    if tt in idx:
        X[idx[tt]] = 1.0
    return X


def build_geom(g: dict) -> VehicleGeometry:
    return VehicleGeometry(
        mass_kg=float(g["mass_kg"]),
        velocity_kmh=float(g["velocity_kmh"]),
        angle_deg=float(g["angle_deg"]),
        a_pillar_thickness_mm=float(g["a_pillar_thickness_mm"]),
        crumple_zone_length_m=float(g["crumple_zone_length_m"]),
        yield_strength_mpa=float(g["yield_strength_mpa"]),
        section_height_mm=float(g["section_height_mm"]),
        section_width_mm=float(g["section_width_mm"]),
        test_type=g["test_type"], vehicle_class=g["vehicle_class"],
        year=int(g["year"]))


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class GeometryInput(BaseModel):
    mass_kg: float = Field(500, ge=500, le=5000)
    velocity_kmh: float = Field(56, ge=5, le=200)
    angle_deg: float = Field(0, ge=0, le=90)
    a_pillar_thickness_mm: float = Field(1.2, ge=0.4, le=4.0)
    crumple_zone_length_m: float = Field(0.8, ge=0.3, le=2.0)
    yield_strength_mpa: float = Field(400, ge=100, le=1200)
    section_height_mm: float = Field(150, ge=50, le=300)
    section_width_mm: float = Field(100, ge=50, le=300)
    vehicle_class: str = Field("sedan")
    test_type: str = Field("frontal")
    year: int = Field(2020, ge=2000, le=2024)

    def validate_enums(self):
        if self.vehicle_class not in _VALID_CLASSES:
            raise ValueError("vehicle_class must be one of sedan, suv, truck, ev")
        if self.test_type not in _VALID_TESTS:
            raise ValueError("test_type must be one of frontal, side, rollover")


class CompareRequest(BaseModel):
    vehicle_a: GeometryInput
    vehicle_b: GeometryInput


class SweepRequest(BaseModel):
    param: str
    low: float
    high: float
    steps: int = Field(30, ge=2, le=80)
    geometry: GeometryInput


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------
def predict_full(g: dict) -> dict:
    ctx = get_ctx()
    import torch
    X = geometry_to_features(g)
    X_norm = (X - ctx["mean"]) / ctx["std"]
    with torch.no_grad():
        pred_norm = ctx["model"](torch.tensor(X_norm[None], dtype=torch.float32))
    pred = ctx["scaler"].denormalize(pred_norm).numpy()[0]
    geom = build_geom(g)
    physics = run_crash(geom, seed=0)
    fea = fea_predict(geom)
    return {
        "pinn": {
            "hic": float(pred[0]), "chest_g": float(pred[1]),
            "intrusion_m": float(pred[2]), "fatality_prob": float(pred[3]),
            "crush_m": float(pred[4]),
        },
        "fea": fea,
        "physics": {k: v for k, v in physics.items()
                    if k not in ("time", "accel_head_g", "accel_struct_ms2",
                                 "intrusion_profile")},
        "animation": {
            "time": physics["time"],
            "accel_head_g": physics["accel_head_g"],
            "accel_struct_ms2": physics["accel_struct_ms2"],
            "intrusion_profile": physics["intrusion_profile"],
            "crush_m": physics["crush_m"],
        },
        "input": g,
    }


@app.get("/api/health")
def health():
    model_ok = False
    model_error = None
    try:
        ctx = get_ctx()
        model_ok = ctx["model"] is not None
    except Exception as e:
        model_error = str(e)
    return {
        "status": "ok" if model_ok else "degraded",
        "service": "crashsim-neural",
        "model_loaded": model_ok,
        "model_error": model_error,
    }


@app.get("/api/warmup")
def warmup():
    """Force model load to warm up cold starts."""
    try:
        import torch
        ctx = get_ctx()
        # Do a dummy prediction to ensure everything works
        dummy = ctx["model"](torch.zeros(1, len(ctx["cols"]), dtype=torch.float32))
        return {"status": "warmed", "model_loaded": True, "input_dim": len(ctx["cols"])}
    except Exception as e:
        raise HTTPException(500, f"Warmup failed: {e}")


@app.get("/api/dataset/summary")
def dataset_summary():
    df = load_dataset()
    return {
        "total": int(len(df)),
        "classes": df["vehicle_class"].value_counts().to_dict(),
        "test_types": df["test_type"].value_counts().to_dict(),
        "year_range": [int(df["year"].min()), int(df["year"].max())],
        "hic_range": [float(df["hic"].min()), float(df["hic"].max())],
    }


@app.get("/api/dataset")
def dataset(
    vehicle_class: Optional[str] = None,
    test_type: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_hic: Optional[float] = None,
    max_hic: Optional[float] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "year",
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
):
    df = load_dataset()
    if vehicle_class:
        df = df[df["vehicle_class"] == vehicle_class]
    if test_type:
        df = df[df["test_type"] == test_type]
    if min_year:
        df = df[df["year"] >= min_year]
    if max_year:
        df = df[df["year"] <= max_year]
    if min_hic:
        df = df[df["hic"] >= min_hic]
    if max_hic:
        df = df[df["hic"] <= max_hic]
    if search:
        s = search.lower()
        mask = df["make"].str.lower().str.contains(s) | \
               df["model"].str.lower().str.contains(s)
        df = df[mask]
    total = int(len(df))
    if sort in df.columns:
        df = df.sort_values(sort, ascending=(order == "asc"))
    start = (page - 1) * per_page
    rows = df.iloc[start:start + per_page].to_dict(orient="records")
    return {"total": total, "page": page, "per_page": per_page, "rows": rows}


@app.get("/api/dataset/download")
def dataset_download():
    """Stream the full 560-record synthetic dataset as CSV for research export."""
    path = os.path.join(DATA_DIR, "crash_data_validated.csv")
    if not os.path.exists(path):
        raise HTTPException(404, "dataset not found")
    headers = {"Content-Disposition": "attachment; filename=crashsim_dataset.csv"}
    return FileResponse(path, media_type="text/csv", headers=headers)


# ---------------------------------------------------------------------------
# Prediction, comparison, sweep
# ---------------------------------------------------------------------------
@app.get("/api/predict")
def predict_get(
    mass_kg: float = 1500,
    velocity_kmh: float = 56,
    angle_deg: float = 0,
    a_pillar_thickness_mm: float = 1.2,
    crumple_zone_length_m: float = 0.8,
    yield_strength_mpa: float = 400,
    section_height_mm: float = 150,
    section_width_mm: float = 100,
    vehicle_class: str = "sedan",
    test_type: str = "frontal",
    year: int = 2020,
):
    g = {
        "mass_kg": mass_kg, "velocity_kmh": velocity_kmh,
        "angle_deg": angle_deg, "a_pillar_thickness_mm": a_pillar_thickness_mm,
        "crumple_zone_length_m": crumple_zone_length_m,
        "yield_strength_mpa": yield_strength_mpa,
        "section_height_mm": section_height_mm,
        "section_width_mm": section_width_mm,
        "vehicle_class": vehicle_class, "test_type": test_type, "year": year,
    }
    return predict_full(g)


@app.post("/api/predict")
def predict(geom: GeometryInput):
    try:
        geom.validate_enums()
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return predict_full(geom.model_dump())


@app.get("/api/compare")
def compare_get(
    a_mass_kg: float = 1500, a_velocity_kmh: float = 56, a_angle_deg: float = 0,
    a_a_pillar_thickness_mm: float = 1.2, a_crumple_zone_length_m: float = 0.8,
    a_yield_strength_mpa: float = 400, a_section_height_mm: float = 150,
    a_section_width_mm: float = 100, a_vehicle_class: str = "sedan",
    a_test_type: str = "frontal", a_year: int = 2020,
    b_mass_kg: float = 2100, b_velocity_kmh: float = 72, b_angle_deg: float = 0,
    b_a_pillar_thickness_mm: float = 1.2, b_crumple_zone_length_m: float = 0.8,
    b_yield_strength_mpa: float = 400, b_section_height_mm: float = 150,
    b_section_width_mm: float = 100, b_vehicle_class: str = "suv",
    b_test_type: str = "frontal", b_year: int = 2020,
):
    ga = {
        "mass_kg": a_mass_kg, "velocity_kmh": a_velocity_kmh,
        "angle_deg": a_angle_deg, "a_pillar_thickness_mm": a_a_pillar_thickness_mm,
        "crumple_zone_length_m": a_crumple_zone_length_m,
        "yield_strength_mpa": a_yield_strength_mpa,
        "section_height_mm": a_section_height_mm,
        "section_width_mm": a_section_width_mm,
        "vehicle_class": a_vehicle_class, "test_type": a_test_type, "year": a_year,
    }
    gb = {
        "mass_kg": b_mass_kg, "velocity_kmh": b_velocity_kmh,
        "angle_deg": b_angle_deg, "a_pillar_thickness_mm": b_a_pillar_thickness_mm,
        "crumple_zone_length_m": b_crumple_zone_length_m,
        "yield_strength_mpa": b_yield_strength_mpa,
        "section_height_mm": b_section_height_mm,
        "section_width_mm": b_section_width_mm,
        "vehicle_class": b_vehicle_class, "test_type": b_test_type, "year": b_year,
    }
    return {"vehicle_a": predict_full(ga), "vehicle_b": predict_full(gb)}


@app.post("/api/compare")
def compare(req: CompareRequest):
    try:
        req.vehicle_a.validate_enums()
        req.vehicle_b.validate_enums()
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"vehicle_a": predict_full(req.vehicle_a.model_dump()),
            "vehicle_b": predict_full(req.vehicle_b.model_dump())}


@app.get("/api/parameter-sweep")
def parameter_sweep_get(
    param: str = "velocity_kmh",
    low: float = 10,
    high: float = 120,
    steps: int = 28,
    mass_kg: float = 1500,
    velocity_kmh: float = 56,
    angle_deg: float = 0,
    a_pillar_thickness_mm: float = 1.2,
    crumple_zone_length_m: float = 0.8,
    yield_strength_mpa: float = 400,
    section_height_mm: float = 150,
    section_width_mm: float = 100,
    vehicle_class: str = "sedan",
    test_type: str = "frontal",
    year: int = 2020,
):
    base = {
        "mass_kg": mass_kg, "velocity_kmh": velocity_kmh,
        "angle_deg": angle_deg, "a_pillar_thickness_mm": a_pillar_thickness_mm,
        "crumple_zone_length_m": crumple_zone_length_m,
        "yield_strength_mpa": yield_strength_mpa,
        "section_height_mm": section_height_mm,
        "section_width_mm": section_width_mm,
        "vehicle_class": vehicle_class, "test_type": test_type, "year": year,
    }
    values = np.linspace(low, high, steps)
    points = []
    for v in values:
        g = dict(base)
        g[param] = float(v)
        try:
            r = predict_full(g)
        except Exception:
            continue
        points.append({"x": float(v), "hic_pinn": r["pinn"]["hic"],
                       "hic_fea": r["fea"]["hic"],
                       "fatality": r["pinn"]["fatality_prob"]})
    return {"param": param, "points": points}


@app.post("/api/parameter-sweep")
def parameter_sweep(req: SweepRequest):
    if req.param not in ("velocity_kmh", "a_pillar_thickness_mm",
                         "crumple_zone_length_m", "yield_strength_mpa",
                         "mass_kg"):
        raise HTTPException(422, "param must be a supported feature")
    base = req.geometry.model_dump()
    values = np.linspace(req.low, req.high, req.steps)
    points = []
    for v in values:
        g = dict(base)
        g[req.param] = float(v)
        try:
            r = predict_full(g)
        except Exception:
            continue
        points.append({"x": float(v), "hic_pinn": r["pinn"]["hic"],
                       "hic_fea": r["fea"]["hic"],
                       "fatality": r["pinn"]["fatality_prob"]})
    return {"param": req.param, "points": points}


# ---------------------------------------------------------------------------
# Charts, training monitor, research
# ---------------------------------------------------------------------------
@app.get("/api/charts/{name}")
def chart(name: str):
    path = os.path.join(CHARTS_DIR, f"{name}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "chart not found")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/training/history")
def training_history():
    with open(os.path.join(ROOT, "models", "training_history.json"),
              encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/training/stream")
def training_stream():
    with open(os.path.join(ROOT, "models", "training_history.json"),
              encoding="utf-8") as f:
        hist = json.load(f)

    def gen():
        epochs = hist["epoch"]
        for i, ep in enumerate(epochs):
            payload = {
                "epoch": ep,
                "train_loss": hist["train_loss"][i],
                "val_loss": hist["val_loss"][i],
                "train_rmse": hist["train_rmse"][i],
                "val_rmse": hist["val_rmse"][i],
                "fea_val_rmse": hist["fea_val_rmse"],
            }
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(0.012)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/metrics")
def metrics():
    with open(os.path.join(ROOT, "models", "metrics.json"),
              encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/research/summary")
def research_summary():
    path = os.path.join(RESEARCH_DIR, "stats_summary.json")
    if not os.path.exists(path):
        raise HTTPException(404, "research summary not generated")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/research/methodology")
def research_methodology():
    path = os.path.join(RESEARCH_DIR, "methodology.json")
    if not os.path.exists(path):
        return {
            "hyperparameters": None,
            "ablation": None,
            "fatality_classifier": None,
            "cross_validation": None,
        }
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------
def _build_pdf() -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Image, Table, TableStyle, PageBreak)
    from reportlab.lib import colors

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(REPORTS_DIR, "crashsim_neural_research_report.pdf")
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    h1 = styles["Title"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, leading=11)

    summary = json.load(open(os.path.join(RESEARCH_DIR, "stats_summary.json"),
                             encoding="utf-8"))
    safety = summary["safety_improvement"]

    story = [Paragraph("CRASHSIM-NEURAL", h1),
             Paragraph("Physics-Informed Neural Network for Vehicle "
                       "Crashworthiness Prediction", h2),
              Paragraph("Predictions from a physics-informed neural network "
                        "trained on a physics-consistent synthetic dataset "
                        "following the NHTSA schema, compared against a linear "
                        "finite element baseline.", body),
             Spacer(1, 10), Paragraph("Key statistics", h2)]

    rows = [
        ["Metric", "Value"],
        ["Records in dataset",
         f"{summary['total_records']} (train {summary['sample_sizes']['train']}, "
         f"val {summary['sample_sizes']['val']}, test {summary['sample_sizes']['test']})"],
        ["PINN HIC MAE (test set)",
         f"{summary['mean_hic_prediction_error']['mae']:.1f}"],
        ["PINN HIC RMSE / R2",
         f"{summary['mean_hic_prediction_error']['rmse']:.1f} / "
         f"{summary['mean_hic_prediction_error']['r2']:.2f}"],
        ["FEA baseline HIC RMSE / R2",
         f"{summary['fea_baseline']['rmse']:.1f} / {summary['fea_baseline']['r2']:.2f}"],
        ["PINN accuracy improvement over FEA",
         f"{summary['accuracy_improvement_over_fea_pct']:.1f}%"],
        ["Computational speedup (PINN vs FEA)",
         f"{summary['computational_speedup']['speedup_x']:.0f}x"],
        ["Projected lives saved per year",
         f"{safety['projected_lives_saved_per_year']:.0f} "
         f"(relative risk reduction {safety['relative_risk_reduction'] * 100:.0f}%)"],
    ]
    t = Table(rows, colWidths=[2.8 * inch, 3.4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#eef2ff")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    for i, name in enumerate(["1_accuracy_curves", "2_injury_surface",
                              "3_class_comparison", "4_crumple_efficiency",
                              "5_sensitivity", "6_historical_trend",
                              "7_fatality_by_crash_type", "8_calibration"]):
        img_path = os.path.join(FIGURES_DIR, f"{name}.png")
        if os.path.exists(img_path):
            story.append(Paragraph(f"Figure {i + 1}: {name.replace('_', ' ')}",
                                   h2))
            story.append(Image(img_path, width=6.0 * inch, height=3.8 * inch))
            story.append(Spacer(1, 6))

    story.append(Paragraph("Methodology", h2))
    story.append(Paragraph(
        "The dataset is generated by the physics engine (plastic crumple zone "
        "energy absorption, HIC36 sliding-window calculation, AIS injury "
        "probability curves, finite-difference beam buckling intrusion model) "
        "with measurement noise, and is validated against documented NHTSA "
        "value ranges. The PINN is trained with a combined data and "
        "physics-consistency loss. The FEA baseline is a linear elastic axial "
        "finite element solver. Sensitivity uses SHAP PermutationExplainer. "
        "Safety projections apply the modeled relative risk reduction to "
        "annual US crash fatality counts and are model estimates, not NHTSA "
        "claims.", small))
    doc.build(story)
    return out_path


@app.get("/api/export/pdf")
def export_pdf_get():
    path = _build_pdf()
    return {"status": "ok", "url": "/api/export/pdf/download",
            "filename": os.path.basename(path)}


@app.post("/api/export/pdf")
def export_pdf():
    path = _build_pdf()
    return {"status": "ok", "url": "/api/export/pdf/download",
            "filename": os.path.basename(path)}


@app.get("/api/export/pdf/download")
def download_pdf():
    path = _build_pdf()
    return FileResponse(path, media_type="application/pdf",
                        filename="crashsim_neural_research_report.pdf")


@app.get("/")
def root():
    return {"service": "crashsim-neural", "docs": "/docs",
            "endpoints": [r.path for r in app.routes
                          if r.path.startswith("/api")]}
