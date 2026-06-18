/**
 * BearingViewer3D.jsx
 * Interactive 3D bearing viewer using Three.js (procedural geometry).
 * Shows the ZA-2115 bearing with health-state visualization — no external GLB needed.
 * Health index H(t) maps to visual damage on outer race.
 */

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

// ── ZA-2115 parameters (mm → scene units, 1 unit = 1 mm) ─────────
const P = {
  BORE_R:    27.5,
  OR_INNER_R: 45.1,
  OR_OUTER_R: 50.0,
  IR_OUTER_R: 32.4,
  WIDTH:      21.0,
  BALL_R:     6.35,
  PITCH_R:    38.75,
  N_BALLS:    14,
  CHAMFER:    1.0,
}

function healthColor(hi) {
  if (hi > 0.6) return new THREE.Color(0x22d3a5)   // teal — normal
  if (hi > 0.25) return new THREE.Color(0xf59e0b)  // amber — warning
  return new THREE.Color(0xef4444)                  // red   — critical
}

function buildScene(canvas, healthIndex) {
  const W = canvas.clientWidth, H = canvas.clientHeight

  // ── Renderer ────────────────────────────────────────────────────
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(W, H, false)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.outputColorSpace = THREE.SRGBColorSpace

  // ── Scene ───────────────────────────────────────────────────────
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0d1520)
  scene.fog = new THREE.Fog(0x0d1520, 200, 600)

  // ── Camera ──────────────────────────────────────────────────────
  const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 1000)
  camera.position.set(90, 60, 90)
  camera.lookAt(0, 0, 0)

  // ── Controls ────────────────────────────────────────────────────
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.minDistance = 60
  controls.maxDistance = 300
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.8

  // ── Lights ──────────────────────────────────────────────────────
  scene.add(new THREE.AmbientLight(0x334466, 0.8))

  const sun = new THREE.DirectionalLight(0xffffff, 2.5)
  sun.position.set(80, 120, 60)
  sun.castShadow = true
  sun.shadow.mapSize.set(2048, 2048)
  scene.add(sun)

  const fill = new THREE.DirectionalLight(0x4499ff, 0.6)
  fill.position.set(-80, -40, -60)
  scene.add(fill)

  const rim = new THREE.PointLight(0x22d3a5, 1.2, 200)
  rim.position.set(0, 80, 0)
  scene.add(rim)

  // ── Materials ────────────────────────────────────────────────────
  const steelMat = new THREE.MeshStandardMaterial({
    color: 0xb0b8c8,
    metalness: 0.95,
    roughness: 0.15,
    envMapIntensity: 0.8,
  })

  const hColor   = healthColor(healthIndex)
  const raceMat  = new THREE.MeshStandardMaterial({
    color: healthIndex > 0.6 ? 0xb0b8c8 : healthIndex > 0.25 ? 0xc8a060 : 0xc85050,
    metalness: 0.92,
    roughness: healthIndex > 0.6 ? 0.12 : healthIndex > 0.25 ? 0.30 : 0.55,
    envMapIntensity: 0.7,
  })

  const cageMat = new THREE.MeshStandardMaterial({
    color: 0xd4a017,
    metalness: 0.8,
    roughness: 0.3,
  })

  const spallMat = new THREE.MeshStandardMaterial({
    color: 0x3a1a0a,
    metalness: 0.3,
    roughness: 0.95,
  })

  // ── Geometry helpers ────────────────────────────────────────────
  const SEGS = 128

  // Outer race — torus + cylinder approach
  const outerRingGeo = new THREE.CylinderGeometry(
    P.OR_OUTER_R, P.OR_OUTER_R, P.WIDTH, SEGS, 1, false
  )
  // Bore of outer race
  const outerBoreGeo = new THREE.CylinderGeometry(
    P.OR_INNER_R, P.OR_INNER_R, P.WIDTH + 2, SEGS, 1, true
  )
  const outerRaceMesh = new THREE.Mesh(outerRingGeo, raceMat)
  outerRaceMesh.rotation.x = Math.PI / 2  // Z = axial
  outerRaceMesh.castShadow = true
  outerRaceMesh.receiveShadow = true
  scene.add(outerRaceMesh)

  // Groove torus on outer race bore surface
  const outerGrooveTorus = new THREE.TorusGeometry(P.OR_INNER_R, 3.4, 32, SEGS)
  const outerGrooveMesh  = new THREE.Mesh(outerGrooveTorus, raceMat)
  scene.add(outerGrooveMesh)

  // Inner race
  const innerRingGeo = new THREE.CylinderGeometry(
    P.IR_OUTER_R, P.IR_OUTER_R, P.WIDTH, SEGS, 1, false
  )
  const innerRaceMesh = new THREE.Mesh(innerRingGeo, raceMat)
  innerRaceMesh.rotation.x = Math.PI / 2
  innerRaceMesh.castShadow = true
  scene.add(innerRaceMesh)

  // Bore cap (thin bore surface)
  const boreSurfGeo  = new THREE.CylinderGeometry(P.BORE_R, P.BORE_R, P.WIDTH, SEGS, 1, true)
  const boreSurfMesh = new THREE.Mesh(boreSurfGeo, steelMat)
  boreSurfMesh.rotation.x = Math.PI / 2
  scene.add(boreSurfMesh)

  // Inner groove torus
  const innerGrooveTorus = new THREE.TorusGeometry(P.IR_OUTER_R, 3.3, 32, SEGS)
  const innerGrooveMesh  = new THREE.Mesh(innerGrooveTorus, raceMat)
  scene.add(innerGrooveMesh)

  // ── Balls ────────────────────────────────────────────────────────
  const ballGeo = new THREE.SphereGeometry(P.BALL_R, 32, 32)
  for (let i = 0; i < P.N_BALLS; i++) {
    const angle = (2 * Math.PI * i) / P.N_BALLS
    const bx = P.PITCH_R * Math.cos(angle)
    const by = P.PITCH_R * Math.sin(angle)
    const ball = new THREE.Mesh(ballGeo, steelMat)
    ball.position.set(bx, by, 0)
    ball.castShadow = true
    scene.add(ball)
  }

  // ── Cage ─────────────────────────────────────────────────────────
  const cageGeo  = new THREE.TorusGeometry(P.PITCH_R, 1.5, 8, P.N_BALLS * 4)
  const cageMesh = new THREE.Mesh(cageGeo, cageMat)
  scene.add(cageMesh)

  // ── Spall pit visualisation (health-state dependent) ─────────────
  if (healthIndex < 0.9) {
    // Incipient: small dark ellipse at 6 o'clock on outer race bore
    const spallDepth = healthIndex < 0.3 ? 0.6 : 0.3
    const spallL     = healthIndex < 0.3 ? 8.0 : 2.0
    const spallW     = healthIndex < 0.3 ? 2.0 : 1.0

    // Position: 6 o'clock = -Y direction, on outer race inner surface
    const spallGeo = new THREE.BoxGeometry(spallL, spallW, spallDepth + 0.5)
    const spallMesh = new THREE.Mesh(spallGeo, spallMat)
    spallMesh.position.set(0, -(P.OR_INNER_R), 0)
    spallMesh.rotation.z = Math.PI / 2
    scene.add(spallMesh)

    // BPFO arrow indicator
    if (healthIndex < 0.7) {
      const arrowDir = new THREE.Vector3(0, -1, 0).normalize()
      const arrowOrigin = new THREE.Vector3(0, -(P.OR_OUTER_R + 12), 0)
      const arrowHelper = new THREE.ArrowHelper(
        arrowDir, arrowOrigin, 10,
        healthIndex < 0.3 ? 0xef4444 : 0xf59e0b,
        4, 3
      )
      scene.add(arrowHelper)
    }
  }

  // ── Grid floor ───────────────────────────────────────────────────
  const grid = new THREE.GridHelper(300, 30, 0x1a2a3a, 0x1a2a3a)
  grid.position.y = -70
  scene.add(grid)

  // ── Health glow ring ─────────────────────────────────────────────
  const glowGeo  = new THREE.TorusGeometry(P.OR_OUTER_R + 5, 0.5, 8, SEGS)
  const glowMat  = new THREE.MeshBasicMaterial({ color: hColor, transparent: true, opacity: 0.5 })
  const glowMesh = new THREE.Mesh(glowGeo, glowMat)
  scene.add(glowMesh)

  // ── Animation loop ───────────────────────────────────────────────
  let animId
  const clock = new THREE.Clock()

  function animate() {
    animId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()

    // Inner race and balls rotate (simulate bearing operation)
    const omega = 0.3  // rad/s
    innerRaceMesh.rotation.z = omega * t
    innerGrooveMesh.rotation.z = omega * t

    // Glow pulse
    glowMat.opacity = 0.3 + 0.2 * Math.sin(t * 2)

    controls.update()
    renderer.render(scene, camera)
  }
  animate()

  // ── Resize handler ────────────────────────────────────────────────
  function onResize() {
    const W2 = canvas.clientWidth, H2 = canvas.clientHeight
    camera.aspect = W2 / H2
    camera.updateProjectionMatrix()
    renderer.setSize(W2, H2, false)
  }
  window.addEventListener('resize', onResize)

  return () => {
    cancelAnimationFrame(animId)
    window.removeEventListener('resize', onResize)
    controls.dispose()
    renderer.dispose()
  }
}

// ── React Component ───────────────────────────────────────────────
export default function BearingViewer3D({ healthIndex = 1.0, status = 'NORMAL' }) {
  const canvasRef = useRef(null)
  const cleanupRef = useRef(null)

  useEffect(() => {
    if (!canvasRef.current) return
    if (cleanupRef.current) cleanupRef.current()
    cleanupRef.current = buildScene(canvasRef.current, healthIndex)
    return () => cleanupRef.current?.()
  }, [healthIndex])

  const hi   = Math.round(healthIndex * 100)
  const label = healthIndex > 0.65
    ? 'Nominal — No Defects  (H ≈ 1.0)'
    : healthIndex > 0.3
    ? 'Incipient Spall — Early Stage  (H ≈ 0.65)'
    : 'Advanced Spall — Critical  (H ≈ 0.25)'

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 360, borderRadius: 12, overflow: 'hidden' }}>
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }}/>

      {/* Overlay labels */}
      <div style={{
        position: 'absolute', top: 12, left: 12,
        background: 'rgba(8,13,20,0.82)', backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 8, padding: '8px 14px',
        fontFamily: 'Inter,sans-serif',
      }}>
        <div style={{ fontSize: 10, color: '#4a5568', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Rexnord ZA-2115 · Digital Twin
        </div>
        <div style={{ fontSize: 13, color: '#f0f6ff', fontWeight: 600, marginTop: 2 }}>{label}</div>
      </div>

      <div style={{
        position: 'absolute', bottom: 12, right: 12,
        background: 'rgba(8,13,20,0.75)',
        borderRadius: 6, padding: '5px 10px',
        fontSize: 10, color: '#4a5568', fontFamily: 'JetBrains Mono,monospace',
      }}>
        OD 100mm · Bore 55mm · 14 balls · Drag to orbit
      </div>

      {status === 'CRITICAL' && (
        <div style={{
          position: 'absolute', top: 12, right: 12,
          background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)',
          borderRadius: 6, padding: '5px 12px',
          fontSize: 11, color: '#fca5a5', fontWeight: 700, letterSpacing: '0.05em',
          animation: 'blink 1s ease-in-out infinite',
        }}>
          ⚠ SPALL DETECTED — BPFO ACTIVE
        </div>
      )}
    </div>
  )
}
