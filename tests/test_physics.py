"""Unit tests for the physics engine.

Run with:  python -m pytest tests -q
"""

import numpy as np
import pytest

from simulation.physics import (
    G, STEEL_E, VehicleGeometry, solve_crush, energy_absorbed,
    hic36, occupant_response, beam_buckling, structural_intrusion,
    run_crash, fatality_probability, p_ais, _triangular_pulse,
)


def test_triangular_pulse_area_equals_velocity():
    v0 = 15.6
    d = 0.7
    t, a = _triangular_pulse(v0, d)
    area = np.trapezoid(a, t)
    assert abs(area - v0) / v0 < 0.01


def test_hic36_matches_analytic_triangular_pulse():
    # For a triangular pulse, HIC over the full pulse equals
    # (avg_accel_g)^2.5 * T with avg = a_peak/2 = v0/T.
    v0, d = 15.6, 0.7
    transfer = 1.5
    t, a = _triangular_pulse(v0, d)
    a_g = a * transfer / G
    T = 2.0 * d / v0
    hic = hic36(a_g, t, window=T)
    analytic = ((v0 / T) * transfer / G) ** 2.5 * T
    assert hic == pytest.approx(analytic, rel=0.05)


def test_energy_conservation_balance():
    geom = VehicleGeometry(mass_kg=1500, velocity_kmh=56,
                           a_pillar_thickness_mm=1.2,
                           crumple_zone_length_m=0.8,
                           yield_strength_mpa=400)
    d = solve_crush(geom, efficiency=0.85)
    e_abs = energy_absorbed(d, geom)
    ke = geom.kinetic_energy
    assert abs(e_abs - 0.85 * ke) / (0.85 * ke) < 0.02


def test_crush_increases_with_velocity():
    g_lo = VehicleGeometry(mass_kg=1500, velocity_kmh=40,
                           a_pillar_thickness_mm=1.2,
                           crumple_zone_length_m=0.8)
    g_hi = VehicleGeometry(mass_kg=1500, velocity_kmh=70,
                           a_pillar_thickness_mm=1.2,
                           crumple_zone_length_m=0.8)
    assert solve_crush(g_hi) > solve_crush(g_lo)


def test_buckling_critical_load_matches_euler():
    geom = VehicleGeometry(a_pillar_thickness_mm=1.2,
                           section_height_mm=150,
                           section_width_mm=100)
    L = 0.8
    # Euler pinned-pinned: P_cr = pi^2 E I / L^2
    t = 0.0012
    w = 0.1
    h = 0.15
    I = (w * h ** 3 - (w - 2 * t) * (h - 2 * t) ** 3) / 12.0
    expected = np.pi ** 2 * STEEL_E * I / L ** 2
    p_cr, _, _ = beam_buckling(geom, axial_load=10000.0, length_m=L)
    assert p_cr == pytest.approx(expected, rel=0.05)


def test_buckling_deflection_blows_up_near_critical():
    geom = VehicleGeometry(a_pillar_thickness_mm=1.2,
                           section_height_mm=150,
                           section_width_mm=100)
    L = 0.8
    _, w_low, _ = beam_buckling(geom, axial_load=0.1e6, length_m=L)
    # Just below P_cr the deflection should be much larger than the low load
    _, w_high, _ = beam_buckling(geom, axial_load=0.9e6, length_m=L)
    assert w_high > 5 * w_low


def test_intrusion_ranges_and_ordering():
    frontal = VehicleGeometry(mass_kg=1500, velocity_kmh=56,
                              test_type="frontal", vehicle_class="sedan")
    side = VehicleGeometry(mass_kg=1500, velocity_kmh=56,
                           test_type="side", vehicle_class="sedan")
    f = structural_intrusion(frontal, 0.5)
    s = structural_intrusion(side, 0.2)
    assert 0 <= f["intrusion_m"] <= 0.6
    assert 0 <= s["intrusion_m"] <= 0.6
    assert s["intrusion_m"] > f["intrusion_m"]


def test_higher_velocity_raises_hic_and_fatality():
    lo = VehicleGeometry(mass_kg=1500, velocity_kmh=35,
                         a_pillar_thickness_mm=1.2,
                         crumple_zone_length_m=0.8)
    hi = VehicleGeometry(mass_kg=1500, velocity_kmh=65,
                         a_pillar_thickness_mm=1.2,
                         crumple_zone_length_m=0.8)
    r_lo = run_crash(lo)
    r_hi = run_crash(hi)
    assert r_hi["hic"] > r_lo["hic"]
    assert r_hi["fatality_prob"] >= r_lo["fatality_prob"]


def test_probabilities_are_valid_and_monotonic():
    assert 0.0 <= fatality_probability(100, 30, 0.05) <= 1.0
    assert 0.0 <= fatality_probability(2000, 90, 0.4) <= 1.0
    assert p_ais(400, 30, 0.05, 3) < p_ais(1600, 30, 0.05, 3)
    assert p_ais(400, 30, 0.05, 2) > p_ais(400, 30, 0.05, 5)


def test_run_crash_output_schema():
    geom = VehicleGeometry()
    r = run_crash(geom, seed=7)
    for key in ["crush_m", "hic", "chest_g", "intrusion_m", "fatality_prob",
                "energy_absorbed_j", "kinetic_energy_j"]:
        assert key in r
    assert 0 < r["crush_m"] < 2.0
    assert r["hic"] > 0
    assert 0 <= r["fatality_prob"] <= 1
