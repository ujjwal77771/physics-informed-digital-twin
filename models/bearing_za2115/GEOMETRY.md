# GEOMETRY CONTRACT — Rexnord ZA-2115 Deep-Groove Ball Bearing
# models/bearing_za2115/GEOMETRY.md

## Coordinate System

- **Z axis** = axial direction (bearing axis of rotation)
- **X–Y plane** = radial plane (perpendicular to rotation axis)
- **Origin** = centre of bore, mid-width axially (Z = 0 at bearing centreline)
- All dimensions in **millimetres (mm)**

## Nominal Parameters — ZA-2115 Equivalent

| Parameter | Symbol | Value (mm) |
|:----------|:------:|:----------:|
| Bore (inner diameter) | d | 55.0 |
| Outer diameter | D | 100.0 |
| Width (axial) | B | 21.0 |
| Ball diameter | Bd | 12.7 |
| Number of balls | n | 14 |
| Pitch circle diameter | Pd | 77.5 |
| Pitch circle radius | Rp | 38.75 |
| Inner race outer radius | Ri_outer | 31.75 |
| Outer race inner radius | Ro_inner | 44.75 |
| Inner groove radius | r_inner | 6.6 |
| Outer groove radius | r_outer | 6.8 |
| Chamfer size | ch | 1.0 |
| Contact angle | α | 0° (radial) |
| Radial clearance | Cr | 0.025 mm (C3 class) |

## Derived Dimensions

| Quantity | Formula | Value |
|:---------|:--------|:-----:|
| Inner race inner radius | d/2 | 27.5 mm |
| Inner race outer radius | Rp - Bd/2 | 32.4 mm |
| Outer race inner radius | Rp + Bd/2 | 45.1 mm |
| Outer race outer radius | D/2 | 50.0 mm |
| Half-width | B/2 | 10.5 mm |
| Ball centre Z | 0 (mid-plane) | 0 mm |

## BPFO — Ball Pass Frequency Outer Race

```
BPFO = (n/2) × RPM/60 × (1 − (Bd/Pd) × cos(α))
     = (14/2) × (RPM/60) × (1 − (12.7/77.5) × cos(0°))
     = 7 × (RPM/60) × 0.8361
     = 5.853 × RPM/60  [Hz]

At 2000 RPM → BPFO = 195.1 Hz
At 1200 RPM → BPFO = 117.1 Hz
```

## Face / Edge Naming Convention

| Handle | Description |
|:-------|:------------|
| `outer_race.bore_face` | Inner cylindrical surface of outer race (groove location) |
| `outer_race.od_face` | Outer cylindrical surface |
| `outer_race.face_plus` | Axial face at +Z (front) |
| `outer_race.face_minus` | Axial face at −Z (back) |
| `inner_race.od_face` | Outer cylindrical surface (groove location) |
| `inner_race.bore_face` | Inner bore surface (shaft fit) |
| `ball_i.centre` | Centre point of ball i (i = 0..13) |
| `cage.ring_face` | Cylindrical mid-surface of cage ring |
| `spall.pit_face` | Floor surface of spall pit (degraded variants) |

## Clearance Fits

- **Radial clearance** between ball and race grooves: 0.025 mm (ISO C3)
- **Axial float**: unconstrained in CAD (no preload modelled)
- **Cage to ball**: 0.1 mm radial gap (loose fit)

## Degradation State Mapping

| File | Health Index H(t) | Geometry Change |
|:-----|:-----------------:|:----------------|
| `bearing_healthy.py` | 1.00 | Nominal — no defects |
| `bearing_incipient.py` | 0.65 | 2×1×0.3 mm spall pit on outer race |
| `bearing_degraded.py` | 0.25 | 8×2×0.6 mm merged spall cavity |

## Output Paths

```
models/bearing_za2115/
  ├── GEOMETRY.md           ← this file
  ├── params.py             ← shared parameter constants
  ├── bearing_outer_race.py
  ├── bearing_inner_race.py
  ├── bearing_balls.py
  ├── bearing_cage.py
  ├── bearing_assembly.py
  ├── bearing_healthy.py
  ├── bearing_incipient.py
  ├── bearing_degraded.py
  └── generate_all.py       ← master runner

assets/bearing_renders/
  ├── healthy_iso.png
  ├── healthy_section.png
  ├── incipient_iso.png
  ├── degraded_iso.png
  └── assembly_exploded.png
```
