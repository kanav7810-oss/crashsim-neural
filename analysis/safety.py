"""Safety impact projection: lives saved if all vehicles met optimal
crumple geometry.

Methodology: for every crash configuration in the database, re-run the
physics engine with optimal structural geometry (90th percentile pillar
thickness and crumple zone length, 85th percentile yield strength within the
vehicle class). The relative reduction in occupant fatality probability is
then applied to the annual US crash fatality count attributable to frontal,
side and rollover events (NHTSA estimates), giving a projected lives-saved
figure. All numbers are model projections on the synthetic dataset, not NHTSA claims.
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd

from simulation.physics import VehicleGeometry, run_crash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "processed")

ANNUAL_FATALITIES = 38000.0
ATTRIBUTABLE_FRACTION = 0.72   # share of US crash fatalities in modeled modes


def _optimal_geometry(r, class_opt):
    o = class_opt[r["vehicle_class"]]
    return VehicleGeometry(
        mass_kg=r["mass_kg"], velocity_kmh=r["velocity_kmh"],
        angle_deg=r["angle_deg"],
        a_pillar_thickness_mm=o["thickness"],
        crumple_zone_length_m=o["crumple"],
        yield_strength_mpa=o["yield"],
        section_height_mm=r["section_height_mm"],
        section_width_mm=r["section_width_mm"],
        test_type=r["test_type"], vehicle_class=r["vehicle_class"],
        year=int(r["year"]))


def run_safety_projection() -> dict:
    df = pd.read_csv(os.path.join(DATA_DIR, "crash_data_validated.csv"))
    opt = {}
    for cls, sub in df.groupby("vehicle_class"):
        opt[cls] = {
            "thickness": float(sub["a_pillar_thickness_mm"].quantile(0.90)),
            "crumple": float(sub["crumple_zone_length_m"].quantile(0.90)),
            "yield": float(sub["yield_strength_mpa"].quantile(0.85)),
        }

    current = df["fatality_prob"].to_numpy()
    optimal = np.zeros(len(df))
    for i, r in df.iterrows():
        geom = _optimal_geometry(r, opt)
        optimal[i] = run_crash(geom, seed=1)["fatality_prob"]

    current_rate = float(current.mean())
    optimal_rate = float(optimal.mean())
    relative_reduction = 1.0 - optimal_rate / max(current_rate, 1e-9)
    attributable_fatalities = ANNUAL_FATALITIES * ATTRIBUTABLE_FRACTION
    lives_saved = relative_reduction * attributable_fatalities

    return {
        "current_mean_fatality": current_rate,
        "optimal_mean_fatality": optimal_rate,
        "relative_risk_reduction": float(relative_reduction),
        "annual_us_fatalities_modeled": float(attributable_fatalities),
        "projected_lives_saved_per_year": float(lives_saved),
        "methodology": ("Physics re-run with class 90th percentile pillar "
                        "thickness and crumple length, 85th percentile yield."),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_safety_projection(), indent=2))
