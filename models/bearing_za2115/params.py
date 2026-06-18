"""
params.py — Shared parametric constants for Rexnord ZA-2115 equivalent bearing.
All dimensions in mm.  Coordinate system: Z = axial, XY = radial, origin = bore centre mid-width.
"""

import math

# ── Nominal geometry ──────────────────────────────────────────────
BORE_D      = 55.0          # bore (inner) diameter
OUTER_D     = 100.0         # outer diameter
WIDTH       = 21.0          # axial width
BALL_D      = 12.7          # ball diameter
N_BALLS     = 14            # number of rolling elements
PITCH_D     = 77.5          # pitch circle diameter

# Derived
BORE_R      = BORE_D   / 2  # 27.5
OUTER_R     = OUTER_D  / 2  # 50.0
BALL_R      = BALL_D   / 2  # 6.35
PITCH_R     = PITCH_D  / 2  # 38.75
HALF_W      = WIDTH    / 2  # 10.5

# ── Race geometry ─────────────────────────────────────────────────
CLEARANCE   = 0.025         # ISO C3 radial clearance (mm)
INNER_GROOVE_R = 6.6        # inner race groove radius
OUTER_GROOVE_R = 6.8        # outer race groove radius

# Inner race: bore = BORE_R, outer surface ≈ PITCH_R - BALL_R - CLEARANCE/2
IR_INNER_R  = BORE_R                       # 27.5 mm
IR_OUTER_R  = PITCH_R - BALL_R - 0.012    # 32.363 mm

# Outer race: inner surface ≈ PITCH_R + BALL_R + CLEARANCE/2, outer = OUTER_R
OR_INNER_R  = PITCH_R + BALL_R + 0.013    # 45.113 mm
OR_OUTER_R  = OUTER_R                      # 50.0 mm

CHAMFER     = 1.0           # edge chamfer size (mm)

# ── Cage geometry ─────────────────────────────────────────────────
CAGE_R      = PITCH_R       # cage sits on pitch circle
CAGE_T      = 1.5           # cage thickness (mm)
CAGE_W      = 8.0           # cage axial width (mm)
CAGE_CUTOUT_R = BALL_R + 0.5  # pocket radius (ball + clearance)

# ── Ball positions ────────────────────────────────────────────────
BALL_ANGLES = [2 * math.pi * i / N_BALLS for i in range(N_BALLS)]
BALL_CENTRES = [
    (PITCH_R * math.cos(a), PITCH_R * math.sin(a), 0.0)
    for a in BALL_ANGLES
]

# ── BPFO formula ──────────────────────────────────────────────────
def bpfo_hz(rpm: float, contact_angle_deg: float = 0.0) -> float:
    """Ball Pass Frequency Outer race [Hz] at given RPM."""
    alpha = math.radians(contact_angle_deg)
    return (N_BALLS / 2) * (rpm / 60) * (1 - (BALL_D / PITCH_D) * math.cos(alpha))

# ── Degradation spall parameters ──────────────────────────────────
# Incipient spall (Health Index ≈ 0.65)
SPALL_INCIPIENT = dict(
    length=2.0, width=1.0, depth=0.3,
    angle_deg=270.0,   # 6 o'clock on outer race
    health_index=0.65,
    label="Early Stage – Health Index ≈ 0.65",
)

# Advanced spall (Health Index ≈ 0.25)
SPALL_DEGRADED = dict(
    length=8.0, width=2.0, depth=0.6,
    angle_deg=270.0,
    health_index=0.25,
    label="Advanced Stage – Health Index ≈ 0.25",
)

# ── Output paths ──────────────────────────────────────────────────
import pathlib
MODEL_DIR  = pathlib.Path(__file__).parent
ASSETS_DIR = MODEL_DIR.parent.parent / "assets" / "bearing_renders"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
