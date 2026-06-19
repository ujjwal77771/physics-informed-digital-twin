/**
 * BearingViewer3D.jsx
 * Interactive 3D bearing viewer using Three.js (procedural geometry).
 * Shows the Rexnord ZA-2115 bearing with realistic inner/outer race,
 * rolling elements, cage, degradation zone, ground shadow, and cursor-following.
 */

import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

// ── ZA-2115 parameters (mm → scene units, 1 unit = 1 mm) ─────────
const P = {
  BORE_R:      27.5,
  IR_INNER_R:  27.5,
  IR_OUTER_R:  32.4,
  OR_INNER_R:  45.1,
  OR_OUTER_R:  50.0,
  WIDTH:       21.0,
  BALL_R:      6.35,
  PITCH_R:     38.75,
  N_BALLS:     14,
  GROOVE_R:    6.6,   // raceway groove radius (slightly > ball radius)
}

function healthColor(hi) {
  if (hi > 0.6) return new THREE.Color(0x22d3a5)   // teal — normal
  if (hi > 0.25) return new THREE.Color(0xf59e0b)  // amber — warning
  return new THREE.Color(0xef4444)                  // red   — critical
}

function buildScene(canvas, healthIndex, mouseRef) {
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
  scene.fog = new THREE.Fog(0x0d1520, 250, 700)

  // ── Camera ──────────────────────────────────────────────────────
  const camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 1000)
  camera.position.set(85, 55, 85)
  camera.lookAt(0, 0, 0)

  // ── Controls ────────────────────────────────────────────────────
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.minDistance = 60
  controls.maxDistance = 300
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.6

  // ── Lights ──────────────────────────────────────────────────────
  scene.add(new THREE.AmbientLight(0x334466, 0.7))

  const sun = new THREE.DirectionalLight(0xffffff, 2.8)
  sun.position.set(80, 140, 60)
  sun.castShadow = true
  sun.shadow.mapSize.set(2048, 2048)
  sun.shadow.camera.near = 10
  sun.shadow.camera.far = 400
  sun.shadow.camera.left = -80
  sun.shadow.camera.right = 80
  sun.shadow.camera.top = 80
  sun.shadow.camera.bottom = -80
  sun.shadow.bias = -0.001
  scene.add(sun)

  const fill = new THREE.DirectionalLight(0x4499ff, 0.5)
  fill.position.set(-80, -40, -60)
  scene.add(fill)

  const rim = new THREE.PointLight(0x22d3a5, 1.0, 250)
  rim.position.set(0, 90, 0)
  scene.add(rim)

  // ── Materials ────────────────────────────────────────────────────
  const steelMat = new THREE.MeshStandardMaterial({
    color: 0xb8c0d0,
    metalness: 0.96,
    roughness: 0.12,
    envMapIntensity: 0.9,
  })

  const hColor = healthColor(healthIndex)
  const raceMat = new THREE.MeshStandardMaterial({
    color: healthIndex > 0.6 ? 0xb0b8c8 : healthIndex > 0.25 ? 0xc8a060 : 0xc85050,
    metalness: 0.93,
    roughness: healthIndex > 0.6 ? 0.10 : healthIndex > 0.25 ? 0.28 : 0.50,
    envMapIntensity: 0.8,
  })

  const cageMat = new THREE.MeshStandardMaterial({
    color: 0xd4a017,
    metalness: 0.82,
    roughness: 0.25,
    envMapIntensity: 0.6,
  })

  const spallMat = new THREE.MeshStandardMaterial({
    color: 0x2a0e04,
    metalness: 0.2,
    roughness: 0.95,
    emissive: healthIndex < 0.3 ? 0x3a0000 : 0x000000,
    emissiveIntensity: 0.4,
  })

  const ballMat = new THREE.MeshStandardMaterial({
    color: 0xd0d6e0,
    metalness: 0.98,
    roughness: 0.05,
    envMapIntensity: 1.0,
  })

  // ── Parent group for cursor-following ───────────────────────────
  const bearingGroup = new THREE.Group()
  scene.add(bearingGroup)

  const SEGS = 128

  // ═══ OUTER RACE ════════════════════════════════════════════════
  // Outer shell
  const outerShellGeo = new THREE.CylinderGeometry(P.OR_OUTER_R, P.OR_OUTER_R, P.WIDTH, SEGS, 1, false)
  const outerShellMesh = new THREE.Mesh(outerShellGeo, raceMat)
  outerShellMesh.rotation.x = Math.PI / 2
  outerShellMesh.castShadow = true
  outerShellMesh.receiveShadow = true
  bearingGroup.add(outerShellMesh)

  // Outer race inner bore surface (visible gap between outer race and balls)
  const outerBoreGeo = new THREE.CylinderGeometry(P.OR_INNER_R, P.OR_INNER_R, P.WIDTH + 0.5, SEGS, 1, true)
  const outerBoreMesh = new THREE.Mesh(outerBoreGeo, raceMat.clone())
  outerBoreMesh.material.side = THREE.BackSide
  outerBoreMesh.rotation.x = Math.PI / 2
  bearingGroup.add(outerBoreMesh)

  // Outer race raceway groove (torus ring where balls sit)
  const outerGrooveGeo = new THREE.TorusGeometry(P.OR_INNER_R, P.GROOVE_R, 24, SEGS)
  const outerGrooveMat = raceMat.clone()
  outerGrooveMat.color.set(0x9098a8)
  outerGrooveMat.roughness = 0.08
  const outerGrooveMesh = new THREE.Mesh(outerGrooveGeo, outerGrooveMat)
  bearingGroup.add(outerGrooveMesh)

  // Outer race chamfer rings (top and bottom edge bevels)
  const chamferGeo = new THREE.TorusGeometry(P.OR_OUTER_R - 0.5, 0.8, 8, SEGS)
  const chamferMat = new THREE.MeshStandardMaterial({ color: 0x8890a0, metalness: 0.9, roughness: 0.2 })
  const chamferTop = new THREE.Mesh(chamferGeo, chamferMat)
  chamferTop.position.z = P.WIDTH / 2
  bearingGroup.add(chamferTop)
  const chamferBot = chamferTop.clone()
  chamferBot.position.z = -P.WIDTH / 2
  bearingGroup.add(chamferBot)

  // ═══ INNER RACE ════════════════════════════════════════════════
  // Inner race outer surface
  const innerOuterGeo = new THREE.CylinderGeometry(P.IR_OUTER_R, P.IR_OUTER_R, P.WIDTH, SEGS, 1, false)
  const innerOuterMesh = new THREE.Mesh(innerOuterGeo, raceMat)
  innerOuterMesh.rotation.x = Math.PI / 2
  innerOuterMesh.castShadow = true
  bearingGroup.add(innerOuterMesh)

  // Inner race bore
  const innerBoreGeo = new THREE.CylinderGeometry(P.IR_INNER_R, P.IR_INNER_R, P.WIDTH + 0.5, SEGS, 1, true)
  const innerBoreMesh = new THREE.Mesh(innerBoreGeo, steelMat)
  innerBoreMesh.material.side = THREE.BackSide
  innerBoreMesh.rotation.x = Math.PI / 2
  bearingGroup.add(innerBoreMesh)

  // Inner race raceway groove
  const innerGrooveGeo = new THREE.TorusGeometry(P.IR_OUTER_R, P.GROOVE_R, 24, SEGS)
  const innerGrooveMat = raceMat.clone()
  innerGrooveMat.color.set(0x9098a8)
  innerGrooveMat.roughness = 0.08
  const innerGrooveMesh = new THREE.Mesh(innerGrooveGeo, innerGrooveMat)
  bearingGroup.add(innerGrooveMesh)

  // Inner race chamfers
  const innerChamferGeo = new THREE.TorusGeometry(P.IR_OUTER_R - 0.3, 0.6, 8, SEGS)
  const innerChamferTop = new THREE.Mesh(innerChamferGeo, chamferMat)
  innerChamferTop.position.z = P.WIDTH / 2
  bearingGroup.add(innerChamferTop)
  const innerChamferBot = innerChamferTop.clone()
  innerChamferBot.position.z = -P.WIDTH / 2
  bearingGroup.add(innerChamferBot)

  // Shaft bore visualization (center hole)
  const shaftGeo = new THREE.CylinderGeometry(P.BORE_R - 2, P.BORE_R - 2, P.WIDTH * 1.2, SEGS, 1, true)
  const shaftMat = new THREE.MeshStandardMaterial({ color: 0x556677, metalness: 0.7, roughness: 0.3, side: THREE.BackSide })
  const shaftMesh = new THREE.Mesh(shaftGeo, shaftMat)
  shaftMesh.rotation.x = Math.PI / 2
  bearingGroup.add(shaftMesh)

  // ═══ ROLLING ELEMENTS (14 Chrome Steel Balls) ══════════════════
  const ballGeo = new THREE.SphereGeometry(P.BALL_R, 48, 48)
  const balls = []
  for (let i = 0; i < P.N_BALLS; i++) {
    const angle = (2 * Math.PI * i) / P.N_BALLS
    const bx = P.PITCH_R * Math.cos(angle)
    const by = P.PITCH_R * Math.sin(angle)
    const ball = new THREE.Mesh(ballGeo, ballMat)
    ball.position.set(bx, by, 0)
    ball.castShadow = true
    ball.receiveShadow = true
    balls.push(ball)
    bearingGroup.add(ball)
  }

  // ═══ CAGE (Brass Retainer with Pockets) ═════════════════════════
  // Main cage ring
  const cageRingGeo = new THREE.TorusGeometry(P.PITCH_R, 2.0, 8, SEGS)
  const cageRing1 = new THREE.Mesh(cageRingGeo, cageMat)
  cageRing1.position.z = P.BALL_R * 0.7
  bearingGroup.add(cageRing1)
  const cageRing2 = cageRing1.clone()
  cageRing2.position.z = -P.BALL_R * 0.7
  bearingGroup.add(cageRing2)

  // Cage pocket bridges between balls
  const bridgeGeo = new THREE.CylinderGeometry(1.2, 1.2, P.BALL_R * 1.4, 8)
  for (let i = 0; i < P.N_BALLS; i++) {
    const a1 = (2 * Math.PI * i) / P.N_BALLS
    const a2 = (2 * Math.PI * (i + 0.5)) / P.N_BALLS
    const mx = P.PITCH_R * Math.cos(a2)
    const my = P.PITCH_R * Math.sin(a2)
    const bridge = new THREE.Mesh(bridgeGeo, cageMat)
    bridge.position.set(mx, my, 0)
    bridge.rotation.x = Math.PI / 2
    bearingGroup.add(bridge)
  }

  // ═══ SPALL / DEGRADATION ZONE ══════════════════════════════════
  let spallGroup = null
  if (healthIndex < 0.9) {
    spallGroup = new THREE.Group()

    const severity = healthIndex < 0.25 ? 1.0 : healthIndex < 0.5 ? 0.6 : 0.3
    const spallLen = 4 + severity * 12        // 4mm → 16mm
    const spallWid = 1.5 + severity * 3       // 1.5mm → 4.5mm
    const spallDep = 0.3 + severity * 1.2     // shallow → deep pit

    // Spall pit — dark rough patch on outer race inner surface
    const spallGeo = new THREE.BoxGeometry(spallLen, spallWid, spallDep + 1)
    const spallMesh = new THREE.Mesh(spallGeo, spallMat)
    spallMesh.position.set(0, -(P.OR_INNER_R - 0.3), 0)
    spallGroup.add(spallMesh)

    // Micro-cracks radiating from spall (lines)
    if (healthIndex < 0.6) {
      const crackMat = new THREE.LineBasicMaterial({ color: 0xff4444, linewidth: 1, transparent: true, opacity: 0.7 })
      for (let c = 0; c < 3 + Math.floor(severity * 5); c++) {
        const pts = []
        const cx = (Math.random() - 0.5) * spallLen * 0.8
        const baseY = -(P.OR_INNER_R - 0.2)
        pts.push(new THREE.Vector3(cx, baseY, (Math.random() - 0.5) * 2))
        for (let s = 0; s < 3; s++) {
          const prev = pts[pts.length - 1]
          pts.push(new THREE.Vector3(
            prev.x + (Math.random() - 0.5) * 3,
            prev.y - Math.random() * 2,
            prev.z + (Math.random() - 0.5) * 2
          ))
        }
        const crackGeo = new THREE.BufferGeometry().setFromPoints(pts)
        spallGroup.add(new THREE.Line(crackGeo, crackMat))
      }
    }

    // BPFO indicator arrow
    if (healthIndex < 0.7) {
      const arrowDir = new THREE.Vector3(0, 1, 0).normalize()
      const arrowOrigin = new THREE.Vector3(0, -(P.OR_OUTER_R + 14), 0)
      const arrowHelper = new THREE.ArrowHelper(
        arrowDir, arrowOrigin, 10,
        healthIndex < 0.3 ? 0xef4444 : 0xf59e0b,
        3.5, 2.5
      )
      spallGroup.add(arrowHelper)
    }

    // Floating label for degradation zone
    const labelCanvas = document.createElement('canvas')
    labelCanvas.width = 512
    labelCanvas.height = 128
    const ctx = labelCanvas.getContext('2d')
    ctx.fillStyle = 'rgba(0,0,0,0)'
    ctx.clearRect(0, 0, 512, 128)

    // Background pill
    ctx.fillStyle = healthIndex < 0.3 ? 'rgba(239,68,68,0.85)' : 'rgba(245,158,11,0.85)'
    const rx = 8, rw = 480, rh = 100, ry2 = 14
    ctx.beginPath()
    ctx.roundRect(16, ry2, rw, rh, rx)
    ctx.fill()

    // Text
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 36px Inter, Arial, sans-serif'
    ctx.textAlign = 'center'
    const labelText = healthIndex < 0.3 ? '⚠ ADVANCED SPALL' : healthIndex < 0.6 ? '⚠ INCIPIENT SPALL' : 'MICRO-PIT ZONE'
    ctx.fillText(labelText, 256, 55)
    ctx.font = '24px Inter, Arial, sans-serif'
    ctx.fillStyle = 'rgba(255,255,255,0.8)'
    const detailText = healthIndex < 0.3 ? `Depth: ${(spallDep).toFixed(1)}mm · Length: ${spallLen.toFixed(0)}mm` : `Outer Race Defect · BPFO Active`
    ctx.fillText(detailText, 256, 90)

    const labelTexture = new THREE.CanvasTexture(labelCanvas)
    const labelSpriteMat = new THREE.SpriteMaterial({ map: labelTexture, transparent: true, depthTest: false })
    const labelSprite = new THREE.Sprite(labelSpriteMat)
    labelSprite.position.set(0, -(P.OR_OUTER_R + 28), 0)
    labelSprite.scale.set(40, 10, 1)
    spallGroup.add(labelSprite)

    // Connecting line from label to spall
    const linePts = [
      new THREE.Vector3(0, -(P.OR_OUTER_R + 23), 0),
      new THREE.Vector3(0, -(P.OR_INNER_R + 2), 0),
    ]
    const lineGeo = new THREE.BufferGeometry().setFromPoints(linePts)
    const lineMat = new THREE.LineDashedMaterial({ color: healthIndex < 0.3 ? 0xef4444 : 0xf59e0b, dashSize: 2, gapSize: 1.5 })
    const labelLine = new THREE.Line(lineGeo, lineMat)
    labelLine.computeLineDistances()
    spallGroup.add(labelLine)

    bearingGroup.add(spallGroup)
  }

  // ═══ GROUND SHADOW ═════════════════════════════════════════════
  // Circular shadow plane beneath the bearing
  const shadowGeo = new THREE.CircleGeometry(65, 64)
  const shadowMat = new THREE.MeshBasicMaterial({
    color: 0x000000,
    transparent: true,
    opacity: 0.35,
    depthWrite: false,
  })
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat)
  shadowMesh.rotation.x = -Math.PI / 2
  shadowMesh.position.y = -38
  scene.add(shadowMesh)

  // Grid floor
  const grid = new THREE.GridHelper(300, 30, 0x1a2a3a, 0x1a2a3a)
  grid.position.y = -40
  scene.add(grid)

  // ── Health glow ring ─────────────────────────────────────────────
  const glowGeo = new THREE.TorusGeometry(P.OR_OUTER_R + 4, 0.6, 8, SEGS)
  const glowMat = new THREE.MeshBasicMaterial({ color: hColor, transparent: true, opacity: 0.5 })
  const glowMesh = new THREE.Mesh(glowGeo, glowMat)
  bearingGroup.add(glowMesh)

  // ── Animation loop ───────────────────────────────────────────────
  let animId
  const clock = new THREE.Clock()

  // Cursor-follow smoothing
  const targetTiltX = { value: 0 }
  const targetTiltY = { value: 0 }
  const currentTiltX = { value: 0 }
  const currentTiltY = { value: 0 }

  function animate() {
    animId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()
    const dt = clock.getDelta()

    // Inner race rotation (simulate bearing operation)
    const omega = 0.4
    innerOuterMesh.rotation.y = omega * t
    innerGrooveMesh.rotation.z = omega * t
    innerBoreMesh.rotation.y = omega * t
    shaftMesh.rotation.y = omega * t * 1.2

    // Ball revolution around pitch circle
    for (let i = 0; i < P.N_BALLS; i++) {
      const cageSpeed = omega * 0.4 // cage speed ≈ 0.4× shaft
      const angle = (2 * Math.PI * i) / P.N_BALLS + cageSpeed * t
      balls[i].position.x = P.PITCH_R * Math.cos(angle)
      balls[i].position.y = P.PITCH_R * Math.sin(angle)
      // Ball self-spin
      balls[i].rotation.x = t * 3
      balls[i].rotation.z = t * 2
    }

    // Cage rotation
    const cageOmega = omega * 0.4
    cageRing1.rotation.z = cageOmega * t
    cageRing2.rotation.z = cageOmega * t

    // Glow pulse
    glowMat.opacity = 0.3 + 0.2 * Math.sin(t * 2)

    // Cursor-following tilt
    if (mouseRef.current) {
      targetTiltX.value = mouseRef.current.y * 0.15  // ±0.15 rad max
      targetTiltY.value = mouseRef.current.x * 0.15
    }
    currentTiltX.value += (targetTiltX.value - currentTiltX.value) * 0.04
    currentTiltY.value += (targetTiltY.value - currentTiltY.value) * 0.04
    bearingGroup.rotation.x = currentTiltX.value
    bearingGroup.rotation.y = currentTiltY.value

    // Shadow scale pulse (subtle)
    const shadowPulse = 1.0 + 0.02 * Math.sin(t * 1.5)
    shadowMesh.scale.set(shadowPulse, shadowPulse, 1)

    controls.update()
    renderer.render(scene, camera)
  }
  animate()

  // ── Resize handler ────────────────────────────────────────────────
  function onResize() {
    const W2 = canvas.clientWidth, H2 = canvas.clientHeight
    if (W2 === 0 || H2 === 0) return
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
  const mouseRef = useRef({ x: 0, y: 0 })

  // Track mouse position relative to canvas center (-1 to 1)
  const handleMouseMove = (e) => {
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    mouseRef.current = {
      x: ((e.clientX - rect.left) / rect.width - 0.5) * 2,
      y: ((e.clientY - rect.top) / rect.height - 0.5) * 2,
    }
  }

  const handleMouseLeave = () => {
    mouseRef.current = { x: 0, y: 0 }
  }

  useEffect(() => {
    if (!canvasRef.current) return
    if (cleanupRef.current) cleanupRef.current()
    cleanupRef.current = buildScene(canvasRef.current, healthIndex, mouseRef)
    return () => cleanupRef.current?.()
  }, [healthIndex])

  const label = healthIndex > 0.65
    ? 'Nominal — No Defects  (H ≈ 1.0)'
    : healthIndex > 0.3
    ? 'Incipient Spall — Early Stage  (H ≈ 0.65)'
    : 'Advanced Spall — Critical  (H ≈ 0.25)'

  return (
    <div
      style={{ position: 'relative', width: '100%', height: '100%', minHeight: 360, borderRadius: 12, overflow: 'hidden' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }}/>

      {/* Top-left label */}
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

      {/* Bottom-right specs */}
      <div style={{
        position: 'absolute', bottom: 12, right: 12,
        background: 'rgba(8,13,20,0.75)',
        borderRadius: 6, padding: '5px 10px',
        fontSize: 10, color: '#4a5568', fontFamily: 'JetBrains Mono,monospace',
      }}>
        OD 100mm · Bore 55mm · 14 balls · Drag to orbit
      </div>

      {/* Bottom-left engineering details */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12,
        background: 'rgba(8,13,20,0.75)',
        borderRadius: 6, padding: '5px 10px',
        fontSize: 9, color: '#3a4a5c', fontFamily: 'JetBrains Mono,monospace',
        lineHeight: 1.6,
      }}>
        Model checkpoint: v2.3.1 · ONNX RT 1.17<br/>
        Last calibrated: 14 Jun 2026 09:32 UTC
      </div>

      {/* Critical alert badge */}
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
