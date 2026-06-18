"""
bearing_outer_race.py — Outer race of Rexnord ZA-2115 equivalent deep-groove ball bearing.

Geometry:
  - Cylindrical ring: outer radius = 50 mm, inner radius = 45.113 mm, axial width = 21 mm
  - Gothic arch groove on bore surface: radius = 6.8 mm, centred at pitch radius from axis
  - 1 mm chamfers on all 4 axial face edges
  - Origin: bearing centre (Z=0 at mid-width, XY radial plane)

Run:
    python bearing_outer_race.py
Outputs:
    models/bearing_za2115/outer_race.step
    models/bearing_za2115/outer_race.stl
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from build123d import (
    BuildPart, BuildSketch, BuildLine,
    Cylinder, Circle, Rectangle, Sphere,
    revolve, extrude, chamfer, fillet,
    Axis, Plane, Location,
    export_step, export_stl,
    add, subtract, Part,
    RadiusOf, Edge, Face,
    Mode, Align,
)
from build123d import *
import params as P

OUTPUT_DIR = pathlib.Path(__file__).parent


def gen_outer_race() -> Part:
    """
    Returns the outer race as a build123d Part.
    Coordinate origin: bearing centre (mid-width, bore axis).
    """
    with BuildPart() as bp:

        # ── Base ring ──────────────────────────────────────────────
        # Full outer cylinder
        Cylinder(radius=P.OR_OUTER_R, height=P.WIDTH, align=(Align.CENTER, Align.CENTER, Align.CENTER))

        # Subtract bore cylinder (leaves the ring wall)
        Cylinder(radius=P.OR_INNER_R, height=P.WIDTH + 2,
                 align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # ── Gothic arch groove on inner bore surface ───────────────
        # The groove is a torus-like feature: a circle of radius OUTER_GROOVE_R
        # revolved around the Z-axis at radius = groove centre from axis.
        # Groove centre radius from Z-axis = OR_INNER_R (sits on bore surface)
        groove_centre_r = P.OR_INNER_R  # groove arc centre at bore surface

        with BuildSketch(Plane.XZ) as groove_sk:
            with Locations((groove_centre_r, 0)):
                Circle(P.OUTER_GROOVE_R)

        groove_solid = revolve(groove_sk.sketch, axis=Axis.Z, revolution_arc=360)
        subtract(groove_solid)

        # ── Chamfer axial edges ────────────────────────────────────
        # Chamfer the 4 circular edges on +Z and -Z faces
        outer_edges = (
            bp.part.edges()
            .filter_by(lambda e: abs(abs(e.center().Z) - P.HALF_W) < 0.5)
        )
        if outer_edges:
            chamfer(outer_edges, length=P.CHAMFER)

    return bp.part


def gen_step_part():
    """Export outer race to STEP and STL."""
    print("[outer_race] Building geometry…")
    part = gen_outer_race()

    step_path = OUTPUT_DIR / "outer_race.step"
    stl_path  = OUTPUT_DIR / "outer_race.stl"

    export_step(part, str(step_path))
    export_stl(part, str(stl_path))

    print(f"[outer_race] ✓ Exported: {step_path}")
    print(f"[outer_race] ✓ Exported: {stl_path}")

    # Validation
    bb = part.bounding_box()
    print(f"[outer_race] Bounding box: "
          f"X=[{bb.min.X:.2f},{bb.max.X:.2f}] "
          f"Y=[{bb.min.Y:.2f},{bb.max.Y:.2f}] "
          f"Z=[{bb.min.Z:.2f},{bb.max.Z:.2f}]")
    expected_od = 2 * P.OR_OUTER_R
    actual_od   = bb.max.X - bb.min.X
    assert abs(actual_od - expected_od) < 0.1, f"OD mismatch: expected {expected_od}, got {actual_od:.2f}"
    assert abs((bb.max.Z - bb.min.Z) - P.WIDTH) < 0.1, "Width mismatch"
    print("[outer_race] ✓ Validation passed")

    return part


if __name__ == "__main__":
    gen_step_part()
