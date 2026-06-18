"""
bearing_incipient.py — Bearing with incipient outer-race spall defect.
Health Index H(t) ≈ 0.65  |  Early-stage fault

Defect geometry:
  - Single elliptical spall pit on outer race groove
  - Location: 6 o'clock position (270° = negative Y direction)
  - Dimensions: 2.0 mm (circumferential) × 1.0 mm (axial) × 0.3 mm deep
  - Sits within the groove surface at pitch-circle depth

Physics link:
  - This defect generates an impulse every time a ball rolls over it
  - Impulse rate = BPFO (Ball Pass Frequency Outer Race)
  - At 2000 RPM → BPFO ≈ 195 Hz impulses per second
  - Kurtosis of vibration signal rises sharply from this stage

Run:
    python bearing_incipient.py
Outputs:
    models/bearing_za2115/bearing_incipient.step
    models/bearing_za2115/bearing_incipient.stl
"""

import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from build123d import *
import params as P
from bearing_outer_race import gen_outer_race
from bearing_inner_race  import gen_inner_race
from bearing_balls       import gen_balls

OUTPUT_DIR = pathlib.Path(__file__).parent
SP = P.SPALL_INCIPIENT


def gen_spalled_outer_race_incipient() -> Part:
    """
    Outer race with a single small elliptical spall pit at 6 o'clock.
    Spall: 2mm long (circumferential) × 1mm wide (axial) × 0.3mm deep.
    """
    with BuildPart() as bp:
        # Start from nominal outer race
        add(gen_outer_race())

        # ── Spall pit: elliptical pocket cut from groove surface ───
        # 6 o'clock = 270° = negative Y direction
        # Groove surface is at OR_INNER_R from axis
        # Pit centre: at (0, -OR_INNER_R, 0)
        spall_angle = math.radians(SP["angle_deg"])  # 270° = -Y
        pit_cx = P.OR_INNER_R * math.cos(spall_angle)   # ≈ 0
        pit_cy = P.OR_INNER_R * math.sin(spall_angle)   # ≈ -45.1

        # Elliptical cylinder for the pit
        # Height >> depth so we can use Boolean intersect with groove
        # Length along circumference (tangent direction) = SP["length"]
        # Width along axial direction = SP["width"]
        # We model as a Box and cut into the race
        with BuildSketch(Plane.XY.offset(-P.HALF_W - 1)) as pit_sk:
            with Locations(Location((pit_cx, pit_cy, 0))):
                # Ellipse: circumferential=length, axial=width
                Ellipse(SP["length"] / 2, SP["width"] / 2)

        pit = extrude(pit_sk.sketch, amount=P.WIDTH + 2)

        # Only remove material to depth SP["depth"] from groove surface
        # Intersect pit with a shallow shell just inside OR_INNER_R
        shallow_shell = Cylinder(
            radius=P.OR_INNER_R + 0.01,
            height=P.WIDTH + 2,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        with BuildPart() as depth_limiter:
            add(shallow_shell)
            Cylinder(
                radius=P.OR_INNER_R - SP["depth"],
                height=P.WIDTH + 2,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

        pit_limited = pit & depth_limiter.part
        subtract(pit_limited)

    return bp.part


def gen_step_part():
    print(f"[incipient] Building bearing with incipient spall — H(t) ≈ {SP['health_index']}")
    print(f"[incipient] Spall: {SP['length']}×{SP['width']}×{SP['depth']} mm at {SP['angle_deg']}°")

    with BuildPart() as assembly:
        add(gen_spalled_outer_race_incipient())
        add(gen_inner_race())
        add(gen_balls())

    part = assembly.part

    step_path = OUTPUT_DIR / "bearing_incipient.step"
    stl_path  = OUTPUT_DIR / "bearing_incipient.stl"

    export_step(part, str(step_path))
    export_stl(part, str(stl_path))

    print(f"[incipient] ✓ Exported: {step_path}")
    print(f"[incipient] ✓ {SP['label']}")

    return part


if __name__ == "__main__":
    gen_step_part()
