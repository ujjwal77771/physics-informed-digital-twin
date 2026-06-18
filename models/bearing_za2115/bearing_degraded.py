"""
bearing_degraded.py — Bearing with advanced outer-race spall propagation.
Health Index H(t) ≈ 0.25  |  Advanced degradation stage

Defect geometry:
  - Extended merged spall cavity on outer race groove at 6 o'clock
  - Dimensions: 8.0 mm (circumferential) × 2.0 mm (axial) × 0.6 mm deep
  - Simulates multiple pits merged into a single elongated cavity
  - Surface offset on groove walls simulates roughness (shell offset technique)

Physics link:
  - At this stage, kurtosis is very high and RMS vibration has elevated significantly
  - BPFO impulses are broad-band and irregular due to spall edge impacts
  - VibFormer model predicts H(t) < 0.3 → CRITICAL status
  - Remaining useful life < 20 cycles in simulation

Run:
    python bearing_degraded.py
Outputs:
    models/bearing_za2115/bearing_degraded.step
    models/bearing_za2115/bearing_degraded.stl
"""

import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from build123d import *
import params as P
from bearing_outer_race import gen_outer_race
from bearing_inner_race  import gen_inner_race
from bearing_balls       import gen_balls

OUTPUT_DIR = pathlib.Path(__file__).parent
SP = P.SPALL_DEGRADED


def gen_spalled_outer_race_degraded() -> Part:
    """
    Outer race with large merged spall cavity + simulated surface roughness.
    Cavity: 8mm × 2mm × 0.6mm at 270° (6 o'clock).
    Secondary pits: 3 smaller satellite pits adjacent to main cavity.
    """
    with BuildPart() as bp:
        add(gen_outer_race())

        spall_angle = math.radians(SP["angle_deg"])
        pit_cx = P.OR_INNER_R * math.cos(spall_angle)
        pit_cy = P.OR_INNER_R * math.sin(spall_angle)

        # ── Primary elongated cavity ───────────────────────────────
        with BuildSketch(Plane.XY.offset(-P.HALF_W - 1)) as main_sk:
            with Locations(Location((pit_cx, pit_cy, 0))):
                Ellipse(SP["length"] / 2, SP["width"] / 2)
        main_pit = extrude(main_sk.sketch, amount=P.WIDTH + 2)

        shell = Cylinder(radius=P.OR_INNER_R + 0.01, height=P.WIDTH + 2,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER))
        with BuildPart() as shell_bp:
            add(shell)
            Cylinder(radius=P.OR_INNER_R - SP["depth"], height=P.WIDTH + 2,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER),
                     mode=Mode.SUBTRACT)
        main_limited = main_pit & shell_bp.part
        subtract(main_limited)

        # ── Satellite pit 1 — upstream of main (at ~260°) ─────────
        a1 = math.radians(260)
        c1x = P.OR_INNER_R * math.cos(a1)
        c1y = P.OR_INNER_R * math.sin(a1)
        with BuildSketch(Plane.XY.offset(-P.HALF_W - 1)) as s1_sk:
            with Locations(Location((c1x, c1y, 0))):
                Ellipse(1.5, 0.8)
        s1_pit = extrude(s1_sk.sketch, amount=P.WIDTH + 2)
        with BuildPart() as s1_shell:
            add(shell)
            Cylinder(radius=P.OR_INNER_R - 0.35, height=P.WIDTH + 2,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER),
                     mode=Mode.SUBTRACT)
        subtract(s1_pit & s1_shell.part)

        # ── Satellite pit 2 — downstream (at ~280°) ───────────────
        a2 = math.radians(280)
        c2x = P.OR_INNER_R * math.cos(a2)
        c2y = P.OR_INNER_R * math.sin(a2)
        with BuildSketch(Plane.XY.offset(-P.HALF_W - 1)) as s2_sk:
            with Locations(Location((c2x, c2y, 0))):
                Ellipse(1.2, 0.6)
        s2_pit = extrude(s2_sk.sketch, amount=P.WIDTH + 2)
        with BuildPart() as s2_shell:
            add(shell)
            Cylinder(radius=P.OR_INNER_R - 0.25, height=P.WIDTH + 2,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER),
                     mode=Mode.SUBTRACT)
        subtract(s2_pit & s2_shell.part)

    return bp.part


def gen_step_part():
    print(f"[degraded] Building bearing with advanced spall — H(t) ≈ {SP['health_index']}")
    print(f"[degraded] Main cavity: {SP['length']}×{SP['width']}×{SP['depth']} mm at {SP['angle_deg']}°")
    print(f"[degraded] + 2 satellite pits at 260° and 280°")

    with BuildPart() as assembly:
        add(gen_spalled_outer_race_degraded())
        add(gen_inner_race())
        add(gen_balls())

    part = assembly.part

    step_path = OUTPUT_DIR / "bearing_degraded.step"
    stl_path  = OUTPUT_DIR / "bearing_degraded.stl"

    export_step(part, str(step_path))
    export_stl(part, str(stl_path))

    print(f"[degraded] ✓ Exported: {step_path}")
    print(f"[degraded] ✓ {SP['label']}")

    return part


if __name__ == "__main__":
    gen_step_part()
