import { useEffect, useState, useRef } from 'react'
import './SplashScreen.css'

export default function SplashScreen({ onComplete }) {
  const [phase, setPhase] = useState('enter')   // enter → run → exit
  const [counter, setCounter] = useState(0)
  const [typeText, setTypeText] = useState('')
  const fullText = 'DIGITAL TWIN'
  const raf = useRef(null)

  /* ── Typewriter ── */
  useEffect(() => {
    let i = 0
    const id = setInterval(() => {
      setTypeText(fullText.slice(0, i + 1))
      i++
      if (i >= fullText.length) clearInterval(id)
    }, 60)
    return () => clearInterval(id)
  }, [])

  /* ── Progress counter ── */
  useEffect(() => {
    let v = 0
    const tick = () => {
      v += v < 70 ? 1.4 : v < 90 ? 0.6 : 0.35
      setCounter(Math.min(100, Math.round(v)))
      if (v < 100) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [])

  /* ── Phase transitions ── */
  useEffect(() => {
    const t1 = setTimeout(() => setPhase('run'),  100)
    const t2 = setTimeout(() => setPhase('exit'), 2400)
    const t3 = setTimeout(() => onComplete(),     2900)
    return () => [t1, t2, t3].forEach(clearTimeout)
  }, [onComplete])

  return (
    <div className={`splash ${phase}`}>
      {/* ── Ambient background orbs ── */}
      <div className="splash-orb orb-1" />
      <div className="splash-orb orb-2" />
      <div className="splash-orb orb-3" />

      {/* ── Grid lines ── */}
      <div className="splash-grid" />

      {/* ── Central icon ── */}
      <div className="splash-center">
        <div className="icon-wrap">

          {/* Outer rotating ring */}
          <svg className="ring ring-outer" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="88"
              fill="none" stroke="rgba(56,189,248,0.12)" strokeWidth="1" />
            <circle cx="100" cy="100" r="88"
              fill="none"
              stroke="url(#cyan-grad)"
              strokeWidth="2"
              strokeDasharray="80 472"
              strokeLinecap="round" />
            <defs>
              <linearGradient id="cyan-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0" />
                <stop offset="50%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
              </linearGradient>
            </defs>
          </svg>

          {/* Mid counter-rotating ring */}
          <svg className="ring ring-mid" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="68"
              fill="none" stroke="rgba(99,102,241,0.1)" strokeWidth="1" />
            <circle cx="100" cy="100" r="68"
              fill="none"
              stroke="url(#indigo-grad)"
              strokeWidth="1.5"
              strokeDasharray="40 387"
              strokeLinecap="round" />
            <defs>
              <linearGradient id="indigo-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#818cf8" stopOpacity="0" />
                <stop offset="50%" stopColor="#818cf8" />
                <stop offset="100%" stopColor="#818cf8" stopOpacity="0" />
              </linearGradient>
            </defs>
          </svg>

          {/* Bearing geometry */}
          <svg className="bearing" viewBox="0 0 200 200">
            {/* Outer race */}
            <circle cx="100" cy="100" r="52"
              fill="none" stroke="rgba(56,189,248,0.3)" strokeWidth="6" />
            {/* Inner race */}
            <circle cx="100" cy="100" r="28"
              fill="none" stroke="rgba(99,102,241,0.4)" strokeWidth="5" />
            {/* Rolling elements × 8 */}
            {[...Array(8)].map((_, i) => {
              const a  = (i / 8) * Math.PI * 2
              const cx = 100 + 40 * Math.cos(a)
              const cy = 100 + 40 * Math.sin(a)
              return (
                <circle key={i} cx={cx} cy={cy} r="5.5"
                  fill="rgba(56,189,248,0.15)"
                  stroke="rgba(56,189,248,0.6)"
                  strokeWidth="1.5" />
              )
            })}
            {/* Centre dot */}
            <circle cx="100" cy="100" r="4"
              fill="#38bdf8"
              style={{ filter: 'drop-shadow(0 0 6px #38bdf8)' }} />
          </svg>

          {/* Pulse rings */}
          <div className="pulse-ring pulse-1" />
          <div className="pulse-ring pulse-2" />
          <div className="pulse-ring pulse-3" />

          {/* ECG / heartbeat line */}
          <svg className="ecg-line" viewBox="0 0 260 40" preserveAspectRatio="none">
            <polyline
              points="0,20 40,20 55,4 65,36 75,14 85,26 100,20 260,20"
              fill="none"
              stroke="#22d3a5"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round" />
          </svg>

          {/* Data particles */}
          {[...Array(12)].map((_, i) => (
            <div key={i} className="particle" style={{
              '--i': i,
              '--r': `${72 + (i % 3) * 16}px`,
              '--delay': `${(i * 0.18).toFixed(2)}s`
            }} />
          ))}
        </div>

        {/* ── Text block ── */}
        <div className="splash-text">
          <div className="splash-label">PHYSICS-INFORMED</div>
          <div className="splash-title">
            {typeText}
            <span className="cursor">|</span>
          </div>
          <div className="splash-sub">Bearing Health · Fault Diagnosis · RUL Prediction</div>
        </div>

        {/* ── Progress bar ── */}
        <div className="splash-progress-wrap">
          <div className="splash-progress-track">
            <div className="splash-progress-fill"
              style={{ width: `${counter}%` }} />
          </div>
          <div className="splash-progress-pct">{counter}%</div>
        </div>

        {/* ── Footer tags ── */}
        <div className="splash-tags">
          {['PyTorch', 'Physics-Informed ML', 'FastAPI', 'React'].map(t => (
            <span key={t} className="splash-tag">{t}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
