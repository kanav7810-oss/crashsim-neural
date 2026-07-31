"""NHTSA-style crashworthiness dataset generator.

Produces a physics-consistent dataset of 560 crash configurations across
model years 2000-2024 covering frontal, side and rollover tests and four
vehicle classes (sedan, SUV, truck, EV).

Every record is produced by running the physics engine, then adding
measurement noise and a documented year-over-year safety improvement trend.
The schema matches the NHTSA NCAP crashworthiness data so that real NHTSA
CSV exports can be dropped into data/raw and used interchangeably.

Usage:  python -m data.generate_dataset
"""

from __future__ import annotations

import csv
import os
import random
import numpy as np
from dataclasses import dataclass

from simulation.physics import VehicleGeometry, run_crash, fatality_probability
from simulation.physics import p_ais

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "data", "processed", "crash_data.csv")
N_RECORDS = 560

MAKES = {
    "sedan": [("Honda", "Accord"), ("Toyota", "Camry"), ("Ford", "Fusion"),
              ("Chevrolet", "Malibu"), ("Hyundai", "Sonata"), ("Nissan", "Altima")],
    "suv": [("Ford", "Explorer"), ("Honda", "CR-V"), ("Toyota", "RAV4"),
            ("Jeep", "Grand Cherokee"), ("Chevrolet", "Equinox"), ("Hyundai", "Tucson")],
    "truck": [("Ford", "F-150"), ("Chevrolet", "Silverado"), ("Ram", "1500"),
              ("Toyota", "Tundra"), ("GMC", "Sierra")],
    "ev": [("Tesla", "Model 3"), ("Tesla", "Model Y"), ("Chevrolet", "Bolt"),
           ("Ford", "Mustang Mach-E"), ("Hyundai", "Ioniq 5"), ("Rivian", "R1T")],
}

CLASS_RANGES = {
    "sedan": dict(mass=(1250, 1750), thickness=(0.90, 1.50), yield_=(300, 500),
                  crumple=(0.70, 1.00), height=(140, 170), width=(95, 115)),
    "suv": dict(mass=(1750, 2350), thickness=(1.00, 1.60), yield_=(340, 520),
                crumple=(0.75, 1.05), height=(145, 180), width=(105, 125)),
    "truck": dict(mass=(2000, 2800), thickness=(1.10, 1.80), yield_=(360, 560),
                  crumple=(0.70, 1.00), height=(150, 190), width=(110, 130)),
    "ev": dict(mass=(1800, 2500), thickness=(1.10, 1.70), yield_=(350, 540),
               crumple=(0.85, 1.10), height=(150, 180), width=(110, 130)),
}

TEST_TYPES = {
    "frontal": (45.0, 65.0, (0, 15)),
    "side": (35.0, 60.0, (85, 95)),
    "rollover": (30.0, 55.0, (20, 45)),
}

SAFETY_TREND = 0.006   # approx 0.6% per year improvement in HIC / chest


def sample_geometry(rng: np.random.Generator, cls: str,
                    test_type: str, year: int) -> VehicleGeometry:
    rng_cls = CLASS_RANGES[cls]
    mass = rng.uniform(*rng_cls["mass"])
    thickness = rng.uniform(*rng_cls["thickness"])
    yield_ = rng.uniform(*rng_cls["yield_"])
    crumple = rng.uniform(*rng_cls["crumple"])
    height = rng.uniform(*rng_cls["height"])
    width = rng.uniform(*rng_cls["width"])
    v_lo, v_hi, ang = TEST_TYPES[test_type]
    velocity = rng.uniform(v_lo, v_hi)
    angle = rng.uniform(*ang)
    return VehicleGeometry(
        mass_kg=round(mass, 1),
        velocity_kmh=round(velocity, 1),
        angle_deg=round(angle, 1),
        a_pillar_thickness_mm=round(thickness, 2),
        crumple_zone_length_m=round(crumple, 3),
        yield_strength_mpa=round(yield_, 1),
        section_height_mm=round(height, 1),
        section_width_mm=round(width, 1),
        test_type=test_type,
        vehicle_class=cls,
        year=year,
    )


def build_rows() -> list[dict]:
    rng = np.random.default_rng(20240611)
    rows = []
    years = [year for year in range(2000, 2025) for _ in range(24)]
    rng.shuffle(years)
    for i in range(N_RECORDS):
        year = years[i % len(years)]
        cls = rng.choice(list(CLASS_RANGES.keys()))
        test_type = rng.choice(list(TEST_TYPES.keys()))
        geom = sample_geometry(rng, cls, test_type, year)
        result = run_crash(geom, seed=int(rng.integers(0, 2 ** 31)))
        trend = 1.0 - SAFETY_TREND * (year - 2000)
        hic = result["hic"] * trend
        chest = result["chest_g"] * trend
        intrusion = result["intrusion_m"]
        p_fatal = float(np.clip(fatality_probability(hic, chest, intrusion), 0.0, 1.0))
        # AIS severity bucket: highest severity whose probability exceeds 0.3
        severities = [2, 3, 4, 5]
        ais = 1
        for s in severities:
            if p_ais(hic, chest, intrusion, s) >= 0.30:
                ais = s
        make, model = MAKES[cls][int(rng.integers(0, len(MAKES[cls])))]
        rows.append({
            "crash_id": f"NHTSA-{year}-{test_type[:2].upper()}-{i + 1:04d}",
            "year": year,
            "make": make,
            "model": model,
            "vehicle_class": cls,
            "test_type": test_type,
            "mass_kg": geom.mass_kg,
            "velocity_kmh": geom.velocity_kmh,
            "angle_deg": geom.angle_deg,
            "a_pillar_thickness_mm": geom.a_pillar_thickness_mm,
            "crumple_zone_length_m": geom.crumple_zone_length_m,
            "yield_strength_mpa": geom.yield_strength_mpa,
            "section_height_mm": geom.section_height_mm,
            "section_width_mm": geom.section_width_mm,
            "hic": round(hic, 2),
            "chest_g": round(chest, 2),
            "intrusion_m": round(intrusion, 4),
            "fatality_prob": round(p_fatal, 4),
            "ais_severity": ais,
            "crush_m": round(result["crush_m"], 4),
            "energy_absorbed_j": round(result["energy_absorbed_j"], 1),
            "kinetic_energy_j": round(result["kinetic_energy_j"], 1),
            "p_critical_n": round(result["p_critical_n"], 1),
        })
    return rows


def validate_rows(rows: list[dict]) -> None:
    assert len(rows) >= 500, "Training set must contain at least 500 records"
    classes = {r["vehicle_class"] for r in rows}
    tests = {r["test_type"] for r in rows}
    assert classes == {"sedan", "suv", "truck", "ev"}, classes
    assert tests == {"frontal", "side", "rollover"}, tests
    years = {r["year"] for r in rows}
    assert min(years) <= 2001 and max(years) >= 2023, (min(years), max(years))
    for r in rows:
        assert r["hic"] > 0, r
        assert 0 <= r["intrusion_m"] <= 0.6, r
        assert 0 <= r["fatality_prob"] <= 1, r
        assert 10 < r["chest_g"] < 120, r


def main() -> None:
    rows = build_rows()
    validate_rows(rows)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    hic = np.array([r["hic"] for r in rows])
    print(f"Wrote {len(rows)} records to {OUT_PATH}")
    print(f"HIC range: {hic.min():.0f} - {hic.max():.0f}, median {np.median(hic):.0f}")
    print(f"Classes: {classes_count(rows)}")
    print(f"Tests: {test_count(rows)}")


def classes_count(rows: list[dict]) -> dict:
    out = {}
    for r in rows:
        out[r["vehicle_class"]] = out.get(r["vehicle_class"], 0) + 1
    return out


def test_count(rows: list[dict]) -> dict:
    out = {}
    for r in rows:
        out[r["test_type"]] = out.get(r["test_type"], 0) + 1
    return out


if __name__ == "__main__":
    main()
