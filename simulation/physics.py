"""Core physics engine for crashworthiness simulation.

Implements:
  - Crumple zone plastic deformation (bilinear force-displacement model)
  - Energy absorption via integration of F(x) over crush distance
  - Numeric HIC (Head Injury Criterion) from an acceleration pulse
  - AIS injury probability curves (published sigmoid parameters)
  - Occupant fatality probability (combined head/chest/intrusion model)
  - Structural intrusion via finite-difference beam buckling (Euler-Bernoulli)

All physical quantities use SI units unless noted otherwise. Acceleration for
HIC is expressed in units of g (standard gravitational acceleration), which is
the convention used by NHTSA and the biomechanics literature.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, asdict, field

G = 9.80665          # m/s^2, standard gravity
STEEL_E = 210.0e9    # Pa, Young modulus of automotive steel
STEEL_DENSITY = 7850.0  # kg/m^3

# Published-style AIS sigmoid parameters: P(AIS>=s) = 1/(1+exp(a - b*X))
# Head (X = HIC): Prasad and Mertz style risk curves
AIS_HEAD = {
    2: (4.60, 0.0047),
    3: (6.00, 0.0042),
    4: (8.00, 0.0044),
    5: (10.20, 0.0045),
}
# Chest (X = chest g-force)
AIS_CHEST = {
    3: (6.50, 0.120),
    4: (8.50, 0.125),
    5: (10.80, 0.128),
}
# Intrusion (X = intrusion depth in centimeters)
AIS_INTRUSION = {
    4: (6.50, 0.35),
    5: (9.00, 0.38),
}


@dataclass
class VehicleGeometry:
    """Physical specification of a crash scenario."""

    mass_kg: float = 1500.0
    velocity_kmh: float = 56.0
    angle_deg: float = 0.0
    a_pillar_thickness_mm: float = 1.2
    crumple_zone_length_m: float = 0.80
    yield_strength_mpa: float = 400.0
    section_height_mm: float = 150.0
    section_width_mm: float = 100.0
    test_type: str = "frontal"   # frontal | side | rollover
    vehicle_class: str = "sedan"  # sedan | suv | truck | ev
    year: int = 2020

    @property
    def velocity_ms(self) -> float:
        return self.velocity_kmh / 3.6

    @property
    def kinetic_energy(self) -> float:
        return 0.5 * self.mass_kg * self.velocity_ms ** 2

    def to_dict(self) -> dict:
        return asdict(self)


def _sigmoid(a: float, b: float, x: float) -> float:
    z = a - b * x
    z = max(min(z, 50.0), -50.0)
    return 1.0 / (1.0 + np.exp(z))


def p_ais(head_h_ic: float, chest_g: float, intrusion_m: float,
          severity: int) -> float:
    """Combined AIS probability for head, chest and intrusion mechanisms."""
    p_head = _sigmoid(*AIS_HEAD[severity], head_h_ic)
    if severity in AIS_CHEST:
        p_chest = _sigmoid(*AIS_CHEST[severity], chest_g)
    else:
        p_chest = 0.0
    if severity in AIS_INTRUSION:
        p_intr = _sigmoid(*AIS_INTRUSION[severity], intrusion_m * 100.0)
    else:
        p_intr = 0.0
    return 1.0 - (1.0 - p_head) * (1.0 - p_chest) * (1.0 - p_intr)


def fatality_probability(head_h_ic: float, chest_g: float,
                         intrusion_m: float) -> float:
    """Fatality probability from AIS 5+ head, chest and intrusion risk."""
    p_head = p_ais(head_h_ic, chest_g, intrusion_m, 5)
    p_chest = _sigmoid(*AIS_CHEST[5], chest_g)
    p_intr = _sigmoid(*AIS_INTRUSION[5], intrusion_m * 100.0)
    return 1.0 - (1.0 - p_head) * (1.0 - p_chest) * (1.0 - p_intr)


def structural_force_capacity(geom: VehicleGeometry) -> float:
    """Peak force the front/side structure can carry (N).

    The effective load path is the A-pillar / rocker section plus the main
    longitudinal rails. We model it as an effective section whose area scales
    with pillar thickness and section width.
    """
    thickness = geom.a_pillar_thickness_mm / 1000.0
    width = geom.section_width_mm / 1000.0
    area = thickness * width
    yield_pa = geom.yield_strength_mpa * 1.0e6
    base = yield_pa * area
    # Number of parallel load paths (two rails + rocker) and geometry effect
    load_paths = 6.0
    if geom.vehicle_class == "suv":
        load_paths = 6.5
    elif geom.vehicle_class == "truck":
        load_paths = 7.0
    elif geom.vehicle_class == "ev":
        load_paths = 7.5
    return base * load_paths


def energy_absorbed(d: float, geom: VehicleGeometry) -> float:
    """Energy absorbed (J) by crushing the structure to depth d (m).

    Bilinear plastic spring: elastic up to the yield displacement, then a
    gently hardening plastic plateau.
    """
    F0 = structural_force_capacity(geom)
    L = geom.crumple_zone_length_m
    k_e = STEEL_E * (geom.a_pillar_thickness_mm / 1000.0
                     * geom.section_width_mm / 1000.0) / L * 6.0
    x_y = F0 / max(k_e, 1.0)
    if d <= x_y:
        return 0.5 * k_e * d * d
    k_p = F0 / max(2.0 * L, 1e-6)   # small plastic hardening slope
    e_el = 0.5 * k_e * x_y * x_y
    return e_el + F0 * (d - x_y) + 0.5 * k_p * (d - x_y) * (d - x_y)


def solve_crush(geom: VehicleGeometry, efficiency: float = 0.85) -> float:
    """Solve energy balance KE*eff = E_absorbed(d) for the crush depth d (m)."""
    KE = geom.kinetic_energy * efficiency
    F0 = structural_force_capacity(geom)
    L = geom.crumple_zone_length_m
    k_e = STEEL_E * (geom.a_pillar_thickness_mm / 1000.0
                     * geom.section_width_mm / 1000.0) / L * 6.0
    x_y = F0 / max(k_e, 1.0)
    e_el = 0.5 * k_e * x_y * x_y
    if KE <= e_el:
        return np.sqrt(2.0 * KE / k_e)
    k_p = F0 / (2.0 * L)
    A = 0.5 * k_p
    B = F0
    C = e_el - F0 * x_y - KE
    disc = B * B - 4.0 * A * C
    disc = max(disc, 0.0)
    return min(((-B + np.sqrt(disc)) / (2.0 * A)) + x_y, 1.6 * L)


def _triangular_pulse(v0: float, d: float, dt: float = 0.0005,
                      pad: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Triangular acceleration pulse for a structure crushing distance d.

    Returns (time, acceleration in m/s^2). Area under the pulse equals v0 so
    the structure brings the occupant compartment to rest.
    """
    if d <= 1e-6 or v0 <= 0:
        return np.array([0.0]), np.array([0.0])
    T = 2.0 * d / v0
    n_pts = max(int(T / dt), 8)
    t = np.linspace(0.0, T, n_pts)
    a_peak = 2.0 * v0 / T
    tri = np.minimum(t, T - t)
    a = (2.0 * a_peak / T) * tri
    if pad > 0:
        tail = np.arange(T, T + pad, dt)
        t = np.concatenate([t, tail])
        a = np.concatenate([a, np.zeros_like(tail)])
    return t, a


def hic36(a_g: np.ndarray, t: np.ndarray, window: float = 0.036) -> float:
    """Compute HIC over sliding time windows (HIC36).

    HIC = max over (t1, t2) of [ (1/(t2-t1)) * integral(a dt) ]^2.5 * (t2-t1)

    a_g is head acceleration in units of g. t in seconds.
    """
    if len(a_g) < 2:
        return 0.0
    dt = t[1] - t[0]
    if dt <= 0:
        return 0.0
    n = max(int(window / dt), 1)
    n = min(n, len(t) - 1)
    best = 0.0
    for i in range(0, len(t) - n + 1):
        seg_t = t[i:i + n]
        seg_a = a_g[i:i + n]
        dt_win = seg_t[-1] - seg_t[0]
        if dt_win <= 0:
            continue
        avg = float(np.trapezoid(seg_a, seg_t) / dt_win)
        hic = (avg ** 2.5) * dt_win
        if hic > best:
            best = hic
    return best


def occupant_response(geom: VehicleGeometry, crush: float) -> dict:
    """Compute occupant-level responses from geometry and crush depth.

    Returns head acceleration history (for animation), HIC, chest g-force.
    """
    v0 = geom.velocity_ms
    t, a_struct = _triangular_pulse(v0, crush)
    head_transfer = 1.50
    if geom.test_type == "side":
        head_transfer = 1.70
    elif geom.test_type == "rollover":
        head_transfer = 1.60
    a_head = a_struct * head_transfer / G   # in g
    h_ic = hic36(a_head, t)
    chest_g = (max(a_struct) / G) * (0.52 + 0.10 * (geom.mass_kg / 1500.0))
    return {"time": t, "accel_struct": a_struct, "accel_head_g": a_head,
            "hic": float(h_ic), "chest_g": float(chest_g)}


# ---------------------------------------------------------------------------
# Finite-difference beam buckling model for structural intrusion
# ---------------------------------------------------------------------------

def _d2_d4_matrices(n: int, dx: float) -> tuple[np.ndarray, np.ndarray]:
    """Build central-difference D2 and D4 operators for a simply supported
    beam with n interior unknowns (w1..w(n-2) plus two boundary points).

    Simply supported boundary conditions: w(0)=0, w(L)=0, w''(0)=0, w''(L)=0.
    Returns (D4, D2) acting on full n-point vector [w0, w1, ..., w(n-1)].
    """
    D2 = np.zeros((n, n))
    D4 = np.zeros((n, n))
    for i in range(n):
        # second derivative stencil
        for j, c in ((-2, 1.0), (-1, -2.0), (0, 1.0)):
            idx = i + j
            if 0 <= idx < n:
                D2[i, idx] += c / (dx * dx)
        # fourth derivative stencil
        for j, c in ((-2, 1.0), (-1, -4.0), (0, 6.0), (1, -4.0), (2, 1.0)):
            idx = i + j
            if 0 <= idx < n:
                D4[i, idx] += c / (dx ** 4)
    # Apply simply supported boundary rows
    D2[0, :] = 0; D2[0, 0] = 1.0; D4[0, :] = 0; D4[0, 0] = 1.0
    D2[-1, :] = 0; D2[-1, -1] = 1.0; D4[-1, :] = 0; D4[-1, -1] = 1.0
    return D4, D2


def _d2_d4_interior(n: int, dx: float) -> tuple[np.ndarray, np.ndarray]:
    """D2 and D4 on interior unknowns only, with simply supported boundary
    conditions folded in via fictitious points (w_-1 = -w_1, w_n = -w_(n-2)).

    Returns matrices of shape (n-2, n-2) acting on [w1 .. w(n-2)].
    """
    m = n - 2
    D2 = np.zeros((m, m))
    D4 = np.zeros((m, m))
    for i in range(m):
        # global node index
        g = i + 1
        # D2: w(g-1) - 2w(g) + w(g+1)
        for j, c in ((-1, 1.0), (0, -2.0), (1, 1.0)):
            col = (g + j) - 1
            if 0 <= col < m:
                D2[i, col] += c / (dx * dx)
        # D4 stencil
        for j, c in ((-2, 1.0), (-1, -4.0), (0, 6.0), (1, -4.0), (2, 1.0)):
            col = (g + j) - 1
            if 0 <= col < m:
                D4[i, col] += c / (dx ** 4)
        # boundary corrections for i == 0 (global node 1) and i == m-1.
        # w_0 = w_(n-1) = 0 (fixed), so D2 needs no correction. The w''=0
        # conditions give fictitious points w_-1 = -w_1 and w_n = -w_(n-2),
        # which subtract 1.0/dx^4 from the self-term of D4.
        if i == 0:
            D4[i, 0] -= 1.0 / (dx ** 4)
        if i == m - 1:
            D4[i, -1] -= 1.0 / (dx ** 4)
    return D4, D2


def beam_buckling(geom: VehicleGeometry, axial_load: float,
                  length_m: float | None = None,
                  n: int = 40) -> tuple[float, float, np.ndarray]:
    """Finite-difference beam buckling under axial load.

    Solves (EI w'''' + P w'') w = q(x) on a simply supported beam where q is
    the lateral load induced by an initial geometric imperfection. Returns
    (critical_load P_cr, max lateral deflection / intrusion depth, deflection
    profile w(x)).
    """
    L = length_m if length_m is not None else max(geom.crumple_zone_length_m, 0.3)
    thickness = geom.a_pillar_thickness_mm / 1000.0
    width = geom.section_width_mm / 1000.0
    h = geom.section_height_mm / 1000.0
    # Rectangular hollow-section bending inertia (effective)
    I = (width * h ** 3 - (width - 2 * thickness) * (h - 2 * thickness) ** 3) / 12.0
    I = max(I, 1e-10)
    E = STEEL_E
    dx = L / (n - 1)
    D4_int, D2_int = _d2_d4_interior(n, dx)
    B = -D2_int
    try:
        from scipy.linalg import eigh
        w_vals = eigh(D4_int, B, eigvals_only=True, subset_by_index=[0, 4])
    except Exception:
        w_vals = np.linalg.eigvals(np.linalg.solve(B, D4_int))
        w_vals = np.sort(np.real(w_vals))
    positive = w_vals[w_vals > 1e-6]
    if len(positive) == 0:
        p_cr = float("inf")
    else:
        p_cr = float(positive[0] * E * I)

    # Imperfection: initial camber w0(x) = d0 * sin(pi x / L)
    x = np.linspace(0.0, L, n)
    d0 = 0.003
    q = axial_load * (np.pi / L) ** 2 * d0 * np.sin(np.pi * x / L)
    # Solve (EI D4 + P D2) w = q using the full BVP operators
    D4, D2 = _d2_d4_matrices(n, dx)
    M = E * I * D4 + axial_load * D2
    M[0, :] = 0; M[0, 0] = 1.0
    M[-1, :] = 0; M[-1, -1] = 1.0
    q[0] = 0.0; q[-1] = 0.0
    try:
        w = np.linalg.solve(M, q)
    except np.linalg.LinAlgError:
        w = np.zeros_like(q)
    w = np.where(np.isfinite(w), w, 0.0)
    return p_cr, float(np.max(np.abs(w))), w


def _plastic_crush_resistance(geom: VehicleGeometry) -> float:
    """Plastic collapse resistance of a thin-walled pillar section.

    Uses the Wierzbicki-Abramowicz progressive folding formula
    P_m ~= 9.56 * sigma0 * t^(5/3) * b^(1/3) applied per wall and summed over
    the load-bearing pillars of the occupant compartment.
    """
    t = geom.a_pillar_thickness_mm / 1000.0
    b = geom.section_width_mm / 1000.0
    sigma0 = geom.yield_strength_mpa * 1.0e6
    p_per_wall = 9.56 * sigma0 * t ** (5.0 / 3.0) * b ** (1.0 / 3.0)
    n_walls = 4.0
    n_pillars = 3.0 if geom.vehicle_class in ("truck", "suv", "ev") else 2.0
    return p_per_wall * n_walls * n_pillars


def structural_intrusion(geom: VehicleGeometry, crush: float) -> dict:
    """Estimate occupant-compartment intrusion depth (m).

    Two mechanisms combine:
      1. Elastic finite-difference beam buckling (P_cr, amplified camber).
      2. Plastic collapse when the transmitted axial force exceeds the
         compartment's plastic crush resistance (Wierzbicki-Abramowicz).
    """
    F0 = structural_force_capacity(geom)
    if geom.test_type == "side":
        # Side impacts have no crumple zone: force loads pillars directly
        axial = F0 * 2.2
        length = max(geom.crumple_zone_length_m * 0.5, 0.30)
    elif geom.test_type == "rollover":
        axial = F0 * 0.75
        length = max(geom.crumple_zone_length_m * 0.8, 0.30)
    else:
        axial = F0 * (1.0 + crush / max(geom.crumple_zone_length_m, 1e-6))
        length = max(geom.crumple_zone_length_m * 0.9, 0.30)

    # Elastic finite-difference buckling response
    p_cr, w_max, w = beam_buckling(geom, axial, length)
    if np.isfinite(p_cr) and p_cr > 0:
        ratio = axial / p_cr
    else:
        ratio = 0.0
    elastic_amp = 1.0 / max(1.0 - min(ratio, 0.99), 0.01)
    elastic_part = w_max * elastic_amp

    # Plastic collapse mechanism (side members are lighter gauge)
    r_comp = _plastic_crush_resistance(geom)
    if geom.test_type == "side":
        r_comp *= 0.65
    compartment_depth = 0.5
    plastic_factor = 0.15
    if axial <= r_comp:
        plastic_part = 0.0
    else:
        excess = (axial - r_comp) / max(r_comp, 1e-6)
        plastic_part = compartment_depth * min(excess * plastic_factor, 0.9)

    intrusion = float(np.clip(plastic_part + elastic_part, 0.0, 0.6))
    return {"p_cr": float(p_cr), "axial_load": float(axial),
            "r_plastic": float(r_comp), "intrusion_m": intrusion,
            "profile": w.tolist()}


def run_crash(geom: VehicleGeometry, seed: int | None = None) -> dict:
    """Full crash simulation: crush, energy, occupant response, intrusion."""
    rng = np.random.default_rng(seed)
    efficiency = 0.85 + rng.normal(0.0, 0.02)
    efficiency = float(np.clip(efficiency, 0.78, 0.92))
    crush = solve_crush(geom, efficiency)
    occ = occupant_response(geom, crush)
    intr = structural_intrusion(geom, crush)
    hic = occ["hic"]
    chest = occ["chest_g"]
    intrusion = intr["intrusion_m"]
    # Noise from test-to-test variability
    noise_hic = 1.0 + rng.normal(0.0, 0.06)
    noise_chest = 1.0 + rng.normal(0.0, 0.05)
    noise_intr = 1.0 + rng.normal(0.0, 0.06)
    hic = float(max(hic * noise_hic, 1.0))
    chest = float(max(chest * noise_chest, 0.1))
    intrusion = float(np.clip(intrusion * noise_intr, 0.0, 0.6))
    p_fatal = float(np.clip(fatality_probability(hic, chest, intrusion), 0.0, 1.0))
    energy = energy_absorbed(crush, geom)
    return {
        "crush_m": float(crush),
        "energy_absorbed_j": float(energy),
        "kinetic_energy_j": float(geom.kinetic_energy),
        "hic": hic,
        "chest_g": chest,
        "intrusion_m": intrusion,
        "fatality_prob": p_fatal,
        "efficiency": efficiency,
        "p_critical_n": float(intr["p_cr"]),
        "time": occ["time"].tolist(),
        "accel_head_g": occ["accel_head_g"].tolist(),
        "accel_struct_ms2": occ["accel_struct"].tolist(),
        "intrusion_profile": intr["profile"],
    }
