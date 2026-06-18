"""
bearing_balls.py — 14 rolling elements (spheres) for Rexnord ZA-2115 equivalent bearing.

Geometry:
  - 14 spheres, diameter = 12.7 mm each
  - Uniformly distributed on pitch circle of radius 38.75 mm
  - All centres at Z = 0 (mid-width plane)
  - Ball 0 at angle 0° (positive X axis), subsequent balls at 360°/14 ≈ 25.71° intervals

Validation:
  - All ball centres at exactly PITCH_R from Z axis
  - No ball-to-ball intersection (angular spacing > ball diameter / pitch circle arc)

Run:
    python bearing_balls.py
Outputs:
    models/bearing_za2115/balls.step
    models/bearing_za2115/balls.stl
"""

import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from build123d import *
import params as P

OUTPUT_DIR = pathlib.Path(__file__).parent


def gen_balls() -> Part:
    """Returns all 14 balls as a single compound Part."""
    with BuildPart() as bp:
        for cx, cy, cz in P.BALL_CENTRES:
            with Locations(Location((cx, cy, cz))):
                Sphere(radius=P.BALL_R)

    return bp.part


def gen_step_part():
    """Export balls to STEP and STL with validation."""
    print(f"[balls] Building {P.N_BALLS} rolling elements…")
    part = gen_balls()

    step_path = OUTPUT_DIR / "balls.step"
    stl_path  = OUTPUT_DIR / "balls.stl"

    export_step(part, str(step_path))
    export_stl(part, str(stl_path))

    print(f"[balls] ✓ Exported: {step_path}")
    print(f"[balls] ✓ Exported: {stl_path}")

    # ── Validation ─────────────────────────────────────────────────
    # Check angular spacing > ball diameter / pitch circumference * 360
    min_arc_deg = 360 / P.N_BALLS
    min_arc_mm  = P.PITCH_R * math.radians(min_arc_deg)
    assert min_arc_mm > P.BALL_D, (
        f"Balls would intersect! Arc spacing {min_arc_mm:.2f} mm < ball diameter {P.BALL_D} mm"
    )

    # Verify pitch radius for each ball centre
    for i, (cx, cy, cz) in enumerate(P.BALL_CENTRES):
        r = math.hypot(cx, cy)
        assert abs(r - P.PITCH_R) < 1e-6, f"Ball {i} pitch radius error: {r:.6f} ≠ {P.PITCH_R}"

    print(f"[balls] ✓ All {P.N_BALLS} ball centres on pitch circle (R = {P.PITCH_R} mm)")
    print(f"[balls] ✓ Angular spacing: {min_arc_deg:.2f}° = {min_arc_mm:.2f} mm arc > {P.BALL_D} mm (no intersection)")

    return part


if __name__ == "__main__":
    gen_step_part()
