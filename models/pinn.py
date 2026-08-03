"""Physics-Informed Neural Network for crashworthiness prediction.

Architecture:  fully connected MLP (tanh hidden layers) with five outputs,
each squashed through a sigmoid and re-scaled by the stored min-max target
normalization.  Inputs are z-scored physical features plus one-hot vehicle
class and test type.

The loss combines:
  - data loss:  MSE against NHTSA-style ground truth (HIC, chest g,
                intrusion, fatality probability, crush depth)
  - physics loss: energy conservation (KE vs absorbed energy), pulse
                consistency (HIC and chest g from the implied crush depth),
                computed by a differentiable physics decoder in torch.
"""

from __future__ import annotations

import json
import os
import numpy as np
import torch
import torch.nn as nn

from simulation.physics import STEEL_E, G

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Physical constants used by the differentiable decoder (SI units)
LOAD_PATHS = {"sedan": 6.0, "suv": 6.5, "truck": 7.0, "ev": 7.5}
HEAD_TRANSFER = {"frontal": 1.50, "side": 1.70, "rollover": 1.60}
EFFICIENCY = 0.85
HIC_INDEX = 0
CHEST_INDEX = 1
INTRUSION_INDEX = 2
FATALITY_INDEX = 3
CRUSH_INDEX = 4


class CrashPinn(nn.Module):
    """Fully connected physics-informed neural network."""

    def __init__(self, n_in: int, hidden: list[int] | None = None):
        super().__init__()
        hidden = hidden or [64, 64, 64]
        layers = []
        dims = [n_in] + hidden
        for i in range(len(dims) - 1):
            layers.append(nn.Linear(dims[i], dims[i + 1]))
            layers.append(nn.Tanh())
        layers.append(nn.Linear(dims[-1], 5))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.net(x))


class PinnScaler:
    """Min-max target scaler mirroring data/preprocess.py."""

    def __init__(self, tmin: np.ndarray, tmax: np.ndarray):
        self.tmin = np.asarray(tmin, dtype=np.float32)
        self.tmax = np.asarray(tmax, dtype=np.float32)
        self.span = np.maximum(self.tmax - self.tmin, 1e-6)

    def denormalize(self, y_norm: torch.Tensor) -> torch.Tensor:
        return y_norm * torch.tensor(self.span) + torch.tensor(self.tmin)

    def denormalize_np(self, y_norm: np.ndarray) -> np.ndarray:
        return y_norm * self.span + self.tmin


def physics_residuals(pred_phys: torch.Tensor, x_phys: torch.Tensor) -> dict:
    """Differentiable physics residuals.

    x_phys columns: mass_kg, v_ms, thickness_m, crumple_L, yield_pa,
                    width_m, load_paths, head_transfer, efficiency.
    pred_phys columns: hic, chest_g, intrusion_m, fatality, crush_m
    """
    m = x_phys[:, 0]
    v = x_phys[:, 1]
    t = x_phys[:, 2]
    L = x_phys[:, 3]
    sy = x_phys[:, 4]
    w = x_phys[:, 5]
    paths = x_phys[:, 6]
    transfer = x_phys[:, 7]
    eta = x_phys[:, 8]

    d = torch.clamp(pred_phys[:, CRUSH_INDEX], 1e-4, None)
    hic_pred = pred_phys[:, HIC_INDEX]
    chest_pred = pred_phys[:, CHEST_INDEX]

    # Kinetic energy and structural force capacity
    KE = 0.5 * m * v * v
    F0 = sy * w * t * paths
    k_e = STEEL_E * (t * w) * 6.0 / torch.clamp(L, 1e-3, None)
    x_y = F0 / torch.clamp(k_e, 1e-3, None)
    k_p = F0 / (2.0 * torch.clamp(L, 1e-3, None))

    # Absorbed energy by crush depth d (bilinear plastic spring)
    e_el = 0.5 * k_e * x_y * x_y
    past_yield = torch.clamp(d - x_y, 0.0, None)
    e_abs = e_el + F0 * past_yield + 0.5 * k_p * past_yield * past_yield
    res_energy = (eta * KE - e_abs) / torch.clamp(KE, 1e-3, None)

    # Pulse consistency: HIC and chest g implied by crush depth d
    T = 2.0 * d / torch.clamp(v, 1e-3, None)
    hic_phys = ((v / T) * transfer / G) ** 2.5 * T
    chest_phys = (2.0 * v / T) / G * (0.52 + 0.10 * (m / 1500.0))
    res_hic = (hic_pred - hic_phys) / 1000.0
    res_chest = (chest_pred - chest_phys) / 50.0

    return {
        "energy": res_energy,
        "hic": res_hic,
        "chest": res_chest,
    }


def physics_loss(pred_phys: torch.Tensor, x_phys: torch.Tensor,
                 weight: float = 1.0) -> torch.Tensor:
    res = physics_residuals(pred_phys, x_phys)
    loss = sum(torch.mean(r * r) for r in res.values())
    return weight * loss


def build_physics_features(raw: np.ndarray, feature_cols: list[str],
                           eta: float = EFFICIENCY) -> np.ndarray:
    """Build the x_phys matrix (SI units) from the raw feature matrix."""
    idx = {c: i for i, c in enumerate(feature_cols)}
    n = len(raw)
    mass = raw[:, idx["mass_kg"]]
    v = raw[:, idx["velocity_kmh"]] / 3.6
    t = raw[:, idx["a_pillar_thickness_mm"]] / 1000.0
    L = raw[:, idx["crumple_zone_length_m"]]
    sy = raw[:, idx["yield_strength_mpa"]] * 1.0e6
    w = raw[:, idx["section_width_mm"]] / 1000.0

    paths = np.zeros(n, dtype=np.float32)
    transfer = np.zeros(n, dtype=np.float32)
    for cls, val in LOAD_PATHS.items():
        col = f"vehicle_class_{cls}"
        if col in idx:
            paths += raw[:, idx[col]] * val
    for test, val in HEAD_TRANSFER.items():
        col = f"test_type_{test}"
        if col in idx:
            transfer += raw[:, idx[col]] * val
    paths[paths == 0] = 6.0
    transfer[transfer == 0] = 1.5

    return np.stack([mass, v, t, L, sy, w, paths, transfer,
                     np.full(n, eta, dtype=np.float32)], axis=1).astype(np.float32)


def save_checkpoint(model: nn.Module, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(model.state_dict(), path)


def load_checkpoint(path: str, n_in: int) -> CrashPinn:
    model = CrashPinn(n_in)
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    return model
