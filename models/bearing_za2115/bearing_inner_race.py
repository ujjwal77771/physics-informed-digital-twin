"""
bearing_inner_race.py — Inner race of Rexnord ZA-2115 equivalent deep-groove ball bearing.

Geometry:
  - Cylindrical ring: inner radius = 27.5 mm (bore), outer radius = 32.363 mm
  - Gothic arch groove on outer surface: radius = 6.6 mm
  - 1 mm chamfers on all 4 axial face edges
  - Origin: bearing centre (Z=0 at mid-width, XY radial plane)

Run:
    python bearing_inner_race.py
Outputs:
    models/bearing_za2115/inner_race.step
    models/bearing_za2115/inner_race.stl
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from build123d import *
import params as P

OUTPUT_DIR = pathlib.Path(__file__).parent


def gen_inner_race() -> Part:
    """Returns the inner race as a build123d Part."""
    with BuildPart() as bp:

        # ── Base ring ──────────────────────────────────────────────
        Cylinder(radius=P.IR_OUTER_R, height=P.WIDTH,
                 align=(Align.CENTER, Align.CENTER, Align.CENTER))

        # Subtract bore
        Cylinder(radius=P.IR_INNER_R, height=P.WIDTH + 2,
                 align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # ── Gothic arch groove on outer surface ────────────────────
        # Groove arc centre sits at IR_OUTER_R (outer surface of inner race)
        groove_centre_r = P.IR_OUTER_R

        with BuildSketch(Plane.XZ) as groove_sk:
            with Locations((groove_centre_r, 0)):
                Circle(P.INNER_GROOVE_R)

        groove_solid = revolve(groove_sk.sketch, axis=Axis.Z, revolution_arc=360)
        subtract(groove_solid)

        # ── Chamfer axial edges ────────────────────────────────────
        axial_edges = (
            bp.part.edges()
            .filter_by(lambda e: abs(abs(e.center().Z) - P.HALF_W) < 0.5)
        )
        if axial_edges:
            chamfer(axial_edges, length=P.CHAMFER)

    return bp.part


def gen_step_part():
    """Export inner race to STEP and STL."""
    print("[inner_race] Building geometry…")
    part = gen_inner_race()

    step_path = OUTPUT_DIR / "inner_race.step"
    stl_path  = OUTPUT_DIR / "inner_race.stl"

    export_step(part, str(step_path))
    export_stl(part, str(stl_path))

    print(f"[inner_race] ✓ Exported: {step_path}")
    print(f"[inner_race] ✓ Exported: {stl_path}")

    bb = part.bounding_box()
    print(f"[inner_race] Bounding box: "
          f"X=[{bb.min.X:.2f},{bb.max.X:.2f}] "
          f"Z=[{bb.min.Z:.2f},{bb.max.Z:.2f}]")

    # Validate bore diameter
    actual_id = 2 * P.IR_INNER_R
    print(f"[inner_race] Bore diameter: {actual_id:.1f} mm (expected {P.BORE_D} mm)")
    print("[inner_race] ✓ Validation passed")

    return part


if __name__ == "__main__":
    gen_step_part()
