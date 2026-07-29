"""Linear-elastic finite element baseline solver.

The baseline predicts crush and occupant response using a strictly linear
elastic 1D axial finite element model. It assembles element stiffness
matrices, applies a ramped crash load, and solves the global system
K u = F. Because it ignores plastic energy dissipation, its predictions
degrade at high speed, which is exactly the shortcoming the PINN is trained
to overcome.
"""

from __future__ import annotations

import numpy as np
from .physics import VehicleGeometry, G, STEEL_E, hic36, _triangular_pulse


def _assemble_stiffness(n_elements: int, ea: float, length: float) -> np.ndarray:
    """Assemble the global axial stiffness matrix for n uniform bar elements."""
    K = np.zeros((n_elements + 1, n_elements + 1))
    k = ea / length
    for i in range(n_elements):
        K[i, i] += k
        K[i, i + 1] -= k
        K[i + 1, i] -= k
        K[i + 1, i + 1] += k
    return K


def _fea_linear_response(geom: VehicleGeometry,
                         n_elements: int = 32) -> dict:
    """Solve the linear elastic FE problem and extract a crush estimate."""
    L = geom.crumple_zone_length_m
    width = geom.section_width_mm / 1000.0
    thickness = geom.a_pillar_thickness_mm / 1000.0
    area = width * thickness * 6.0   # effective parallel load paths
    ea = STEEL_E * area
    K = _assemble_stiffness(n_elements, ea, L / n_elements)

    # Rampe crash load up to the force implied by momentum transfer.
    v0 = geom.velocity_ms
    KE = 0.5 * geom.mass_kg * v0 * v0
    f_peak = min(2.0 * KE / L, 1.5e6)
    F = np.zeros(n_elements + 1)
    F[-1] = f_peak

    # Fixed base: constrain node 0.
    K_r = K[1:, 1:]
    F_r = F[1:]
    try:
        u = np.linalg.solve(K_r, F_r)
    except np.linalg.LinAlgError:
        u = np.zeros_like(F_r)
    u = np.concatenate([[0.0], u])
    crush = float(u[-1])
    if not np.isfinite(crush) or crush < 0:
        crush = 0.0
    # Linear-spring energy: E = 0.5 * k * u^2 (no plastic dissipation)
    k_eff = f_peak / max(crush, 1e-6)
    e_lin = 0.5 * k_eff * crush * crush
    # Time and HIC from the linear crush depth.
    t, a_struct = _triangular_pulse(v0, crush)
    head_transfer = 1.50
    if geom.test_type == "side":
        head_transfer = 1.70
    elif geom.test_type == "rollover":
        head_transfer = 1.60
    a_head = a_struct * head_transfer / G
    h_ic = hic36(a_head, t)
    chest = (max(a_struct) / G) * (0.52 + 0.10 * (geom.mass_kg / 1500.0))
    return {
        "crush_m": crush,
        "energy_absorbed_j": float(e_lin),
        "hic": float(h_ic),
        "chest_g": float(chest),
        "max_displacement_m": float(np.max(np.abs(u))),
        "fea_stiffness_Nm": float(k_eff),
    }


def fea_predict(geom: VehicleGeometry) -> dict:
    """Public FEA baseline prediction for a vehicle geometry."""
    return _fea_linear_response(geom)
