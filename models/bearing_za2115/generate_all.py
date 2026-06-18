"""
generate_all.py — Master runner for all ZA-2115 bearing CAD models.

Generates in order:
  1. outer_race.step / .stl
  2. inner_race.step / .stl
  3. balls.step / .stl
  4. bearing_assembly.step / .stl + topology_summary.txt
  5. bearing_incipient.step / .stl  (H(t) ≈ 0.65)
  6. bearing_degraded.step / .stl   (H(t) ≈ 0.25)

Usage:
    python models/bearing_za2115/generate_all.py

Requirements:
    pip install build123d
"""

import sys, pathlib, time

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).parent))

print("=" * 60)
print("  Rexnord ZA-2115 Bearing — CAD Generation Suite")
print("  Physics-Informed Digital Twin Project")
print("=" * 60)

results = {}

def run(name, fn):
    print(f"\n{'─'*50}")
    print(f"  [{name}]")
    print(f"{'─'*50}")
    t0 = time.time()
    try:
        fn()
        dt = time.time() - t0
        results[name] = f"✓ {dt:.1f}s"
        print(f"  [{name}] Done in {dt:.1f}s")
    except Exception as e:
        results[name] = f"✗ ERROR: {e}"
        print(f"  [{name}] ERROR: {e}")
        import traceback; traceback.print_exc()


from bearing_outer_race import gen_step_part as outer_race
from bearing_inner_race  import gen_step_part as inner_race
from bearing_balls       import gen_step_part as balls
from bearing_assembly    import gen_step_assembly as assembly
from bearing_incipient   import gen_step_part as incipient
from bearing_degraded    import gen_step_part as degraded

run("outer_race",  outer_race)
run("inner_race",  inner_race)
run("balls",       balls)
run("assembly",    assembly)
run("incipient",   incipient)
run("degraded",    degraded)

print("\n" + "=" * 60)
print("  GENERATION SUMMARY")
print("=" * 60)
for name, result in results.items():
    print(f"  {name:<20} {result}")

output_dir = pathlib.Path(__file__).parent
files = list(output_dir.glob("*.step")) + list(output_dir.glob("*.stl"))
total_mb = sum(f.stat().st_size for f in files) / 1e6
print(f"\n  Output directory : {output_dir}")
print(f"  Files generated  : {len(files)}")
print(f"  Total size       : {total_mb:.1f} MB")
print("=" * 60)
