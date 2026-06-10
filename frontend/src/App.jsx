import { useState, useEffect, useRef, useCallback } from 'react'
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'
import {
  Activity, Cpu, AlertTriangle, CheckCircle2, XCircle,
  Wifi, WifiOff, TrendingDown, Zap, Gauge, Clock, BarChart2
} from 'lucide-react'
import './index.css'

const WS_URL = 'ws://localhost:8000/ws/telemetry'
const MAX_HISTORY = 60
const SENSOR_NAMES = ['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10','S11','S12','S13','S14']

// ── Health Arc SVG ──────────────────────────────────────────────
function HealthArc({ index }) {
  const R = 70, cx = 90, cy = 90
  const startAngle = Math.PI * 0.8
  const endAngle   = Math.PI * 0.2
  const totalArc   = (2 * Math.PI) - (startAngle - endAngle)
  const clamp = Math.max(0, Math.min(1, index))
  const filled = clamp * totalArc

  const arcPath = (start, sweep) => {
    const s = { x: cx + R * Math.cos(start), y: cy + R * Math.sin(start) }
    const e = { x: cx + R * Math.cos(start + sweep), y: cy + R * Math.sin(start + sweep) }
    const large = sweep > Math.PI ? 1 : 0
    return `M ${s.x} ${s.y} A ${R} ${R} 0 ${large} 1 ${e.x} ${e.y}`
  }

  const color = clamp > 0.6 ? '#22d3a5' : clamp > 0.25 ? '#f59e0b' : '#ef4444'
  const pct   = Math.round(clamp * 100)

  return (
    <div className="health-arc-container">
      <svg className="arc-svg" width={180} height={115} viewBox="0 0 180 115">
        {/* Track */}
        <path d={arcPath(startAngle, totalArc)} fill="none"
          stroke="rgba(255,255,255,0.06)" strokeWidth={10} strokeLinecap="round" />
        {/* Filled */}
        <path d={arcPath(startAngle, filled)} fill="none"
          stroke={color} strokeWidth={10} strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 8px ${color})`, transition: 'all 0.6s ease' }} />
        {/* Labels */}
        <text x={cx} y={cy - 4} className="arc-label" fill={color}>{pct}%</text>
        <text x={cx} y={cy + 18} className="arc-sublabel">Health Index</text>
      </svg>
    </div>
  )
}

// ── Status Badge ────────────────────────────────────────────────
function StatusBadge({ status }) {
  const icons = { NORMAL: <CheckCircle2 size={11}/>, WARNING: <AlertTriangle size={11}/>, CRITICAL: <XCircle size={11}/> }
  return (
    <span className={`status-badge ${status}`}>
      {icons[status] || null}
      {status}
    </span>
  )
}

// ── Custom Tooltip ──────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'rgba(8,13,20,0.95)', border: '1px solid rgba(56,189,248,0.2)',
      borderRadius: 8, padding: '8px 14px', fontSize: 12
    }}>
      <div style={{ color: '#8b9cb5', marginBottom: 4 }}>Step {label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontWeight: 600 }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </div>
      ))}
    </div>
  )
}

// ── Main App ────────────────────────────────────────────────────
export default function App() {
  const [wsState, setWsState]       = useState('disconnected')  // connecting | connected | disconnected
  const [latest, setLatest]         = useState(null)
  const [history, setHistory]       = useState([])
  const [events, setEvents]         = useState([])
  const [prevStatus, setPrevStatus] = useState(null)
  const wsRef = useRef(null)

  const connect = useCallback(() => {
    if (wsRef.current) wsRef.current.close()
    setWsState('connecting')
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen  = () => setWsState('connected')
    ws.onclose = () => { setWsState('disconnected'); wsRef.current = null }
    ws.onerror = () => { setWsState('disconnected'); ws.close() }

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setLatest(data)
      setHistory(h => {
        const next = [...h, { ...data, t: data.step }]
        return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next
      })
      // Log status changes
      setPrevStatus(prev => {
        if (prev !== null && prev !== data.status) {
          const time = new Date().toLocaleTimeString()
          setEvents(ev => [{
            time, status: data.status, rul: data.predicted_rul, step: data.step
          }, ...ev].slice(0, 30))
        }
        return data.status
      })
    }
  }, [])

  useEffect(() => { connect(); return () => wsRef.current?.close() }, [connect])

  // Reconnect on disconnect after 3s
  useEffect(() => {
    if (wsState === 'disconnected') {
      const t = setTimeout(connect, 3000)
      return () => clearTimeout(t)
    }
  }, [wsState, connect])

  const hi      = latest?.health_index ?? 0
  const rul     = latest?.predicted_rul ?? '--'
  const tRul    = latest?.true_rul ?? '--'
  const status  = latest?.status ?? 'NORMAL'
  const sensors = latest?.sensors ?? Array(14).fill(0)
  const step    = latest?.step ?? 0

  const rulColor = status === 'CRITICAL' ? '#ef4444' : status === 'WARNING' ? '#f59e0b' : '#38bdf8'

  const gradId = `grad-${status}`

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-brand">
          <div className="brand-icon">⚙️</div>
          <div>
            <div className="brand-title">Physics-Informed Digital Twin</div>
            <div className="brand-sub">Industrial Bearing Health Monitor · RUL Prediction</div>
          </div>
        </div>
        <div className="header-status">
          <span className="step-counter">Step: {step}</span>
          <StatusBadge status={status} />
          <div className={`connection-badge ${wsState}`}>
            {wsState === 'connected'
              ? <><Wifi size={13}/><span className="dot pulse"/></>
              : wsState === 'connecting'
              ? <><Activity size={13}/></>
              : <><WifiOff size={13}/></>}
            {wsState.charAt(0).toUpperCase() + wsState.slice(1)}
          </div>
        </div>
      </header>

      <main className="main">
        {/* ── Alert Banner ── */}
        {status === 'CRITICAL' && (
          <div className="alert-banner CRITICAL">
            <XCircle size={16}/>
            <strong>CRITICAL:</strong> Severe bearing degradation detected. Immediate maintenance required — predicted RUL: {typeof rul === 'number' ? rul.toFixed(1) : rul} cycles.
          </div>
        )}
        {status === 'WARNING' && (
          <div className="alert-banner WARNING">
            <AlertTriangle size={16}/>
            <strong>WARNING:</strong> Degradation trend detected. Schedule inspection. Predicted RUL: {typeof rul === 'number' ? rul.toFixed(1) : rul} cycles.
          </div>
        )}

        {/* ── Top Metric Cards ── */}
        <div className="grid-top">
          {/* RUL */}
          <div className="card metric-card">
            <div className="metric-icon"><TrendingDown /></div>
            <div className="card-title"><Clock size={13}/> Predicted RUL</div>
            <div className="metric-value" style={{ color: rulColor }}>
              {typeof rul === 'number' ? rul.toFixed(0) : '--'}
            </div>
            <div className="metric-label">Remaining Useful Life (cycles)</div>
          </div>

          {/* True RUL */}
          <div className="card metric-card">
            <div className="metric-icon"><BarChart2 /></div>
            <div className="card-title"><Gauge size={13}/> Actual RUL</div>
            <div className="metric-value" style={{ color: '#6366f1' }}>
              {typeof tRul === 'number' ? tRul.toFixed(0) : '--'}
            </div>
            <div className="metric-label">Ground Truth Cycles Remaining</div>
          </div>

          {/* Error */}
          <div className="card metric-card">
            <div className="metric-icon"><Activity /></div>
            <div className="card-title"><Zap size={13}/> Prediction Error</div>
            <div className="metric-value" style={{ color: '#f59e0b' }}>
              {(typeof rul === 'number' && typeof tRul === 'number')
                ? Math.abs(rul - tRul).toFixed(1)
                : '--'}
            </div>
            <div className="metric-label">|Predicted − True| cycles</div>
          </div>

          {/* Step */}
          <div className="card metric-card">
            <div className="metric-icon"><Cpu /></div>
            <div className="card-title"><Activity size={13}/> Run Time</div>
            <div className="metric-value" style={{ color: '#22d3a5' }}>{step}</div>
            <div className="metric-label">Elapsed measurement steps</div>
          </div>
        </div>

        {/* ── Middle: Health Arc + RUL Chart ── */}
        <div className="grid-mid">
          {/* Health Arc */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><Gauge size={13}/> Machine Health Index</span>
              <StatusBadge status={status} />
            </div>
            <HealthArc index={hi} />
            <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-secondary)', textAlign: 'center', lineHeight: 1.6 }}>
              {status === 'NORMAL'   && '✅ Operating within safe parameters. No immediate action required.'}
              {status === 'WARNING'  && '⚠️ Degradation trend detected. Increase monitoring frequency.'}
              {status === 'CRITICAL' && '🚨 Immediate shutdown recommended to prevent catastrophic failure.'}
            </div>
          </div>

          {/* RUL Time Series */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><TrendingDown size={13}/> RUL History</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradTrue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="gradPred" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={rulColor} stopOpacity={0.25}/>
                    <stop offset="95%" stopColor={rulColor} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="t" tick={{ fontSize:10, fill:'#4a5568' }} />
                <YAxis tick={{ fontSize:10, fill:'#4a5568' }} domain={[0,130]} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={20} stroke="rgba(239,68,68,0.4)" strokeDasharray="4 2" label={{ value:'CRITICAL', fill:'#ef4444', fontSize:9 }} />
                <Area type="monotone" dataKey="true_rul"      name="True RUL"      stroke="#6366f1" fill="url(#gradTrue)" strokeWidth={1.5} dot={false} />
                <Area type="monotone" dataKey="predicted_rul" name="Predicted RUL" stroke={rulColor} fill="url(#gradPred)" strokeWidth={2}   dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ── Bottom: Sensor Array + Event Log ── */}
        <div className="grid-bottom">
          {/* Sensor Values */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><Activity size={13}/> Live Sensor Readings</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>14 channels · 20 kHz</span>
            </div>
            <div className="sensor-grid">
              {SENSOR_NAMES.map((name, i) => (
                <div key={name} className="sensor-cell">
                  <div className="sensor-name">{name}</div>
                  <div className="sensor-val">{typeof sensors[i] === 'number' ? sensors[i].toFixed(2) : '--'}</div>
                </div>
              ))}
            </div>

            {/* Health Index Line Chart */}
            <div style={{ marginTop: 16 }}>
              <div className="card-title" style={{ marginBottom: 8 }}><BarChart2 size={13}/> Health Index Over Time</div>
              <ResponsiveContainer width="100%" height={130}>
                <LineChart data={history} margin={{ top: 2, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="t" tick={{ fontSize:9, fill:'#4a5568' }} />
                  <YAxis tick={{ fontSize:9, fill:'#4a5568' }} domain={[0,1]} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="health_index" name="Health" stroke="#22d3a5" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Event Log */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><AlertTriangle size={13}/> Status Events</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{events.length} events</span>
            </div>
            {events.length === 0
              ? <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '16px 0', textAlign: 'center' }}>
                  Monitoring… status changes will appear here.
                </div>
              : <div className="event-log">
                  {events.map((ev, i) => (
                    <div key={i} className={`event-item ${ev.status}`}>
                      <div className="event-time">{ev.time}</div>
                      <div style={{ fontSize: 12, flex: 1 }}>
                        Status changed to <strong>{ev.status}</strong> — RUL: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>{ev.rul.toFixed(1)}</span>
                      </div>
                    </div>
                  ))}
                </div>
            }
          </div>
        </div>
      </main>

      <footer className="footer">
        Physics-Informed Digital Twin · BIT Mesra · Ujjwal Deep · {new Date().getFullYear()}
      </footer>
    </div>
  )
}
