import { useState, useEffect, useRef, useCallback } from 'react'
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'
import {
  Activity, Cpu, AlertTriangle, CheckCircle2, XCircle,
  Wifi, WifiOff, TrendingDown, Zap, Gauge, Clock,
  BarChart2, ArrowLeft, Download, RefreshCw, Layers
} from 'lucide-react'
import SplashScreen from './SplashScreen.jsx'
import './index.css'

// ── Constants ──────────────────────────────────────────────────────
const BEARINGS = {
  B1: { id: 'B1', name: 'Bearing 1',  location: 'Line A · Drive End', desc: 'Primary drive-end bearing, Rexnord ZA-2115' },
  B2: { id: 'B2', name: 'Bearing 2',  location: 'Line A · Fan End',   desc: 'Fan-end bearing, showing degradation trend' },
  B3: { id: 'B3', name: 'Bearing 3',  location: 'Line B · Drive End', desc: 'Secondary drive-end bearing, near end-of-life' },
  B4: { id: 'B4', name: 'Bearing 4',  location: 'Line B · Fan End',   desc: 'New fan-end bearing, recently replaced' },
}
const BID_LIST   = ['B1','B2','B3','B4']
const MAX_HIST   = 120
const SENSOR_NAMES = ['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10','S11','S12','S13','S14']

function wsUrl(bid) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/ws/telemetry/${bid}`
}

// ── Small sub-components ───────────────────────────────────────────

function StatusBadge({ status }) {
  const icons = { NORMAL: <CheckCircle2 size={11}/>, WARNING: <AlertTriangle size={11}/>, CRITICAL: <XCircle size={11}/> }
  return <span className={`status-badge ${status}`}>{icons[status]}{status}</span>
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background:'rgba(8,13,20,.96)', border:'1px solid rgba(56,189,248,.2)', borderRadius:8, padding:'8px 14px', fontSize:12 }}>
      <div style={{ color:'#8b9cb5', marginBottom:4 }}>Step {label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color:p.color, fontWeight:600 }}>
          {p.name}: {typeof p.value==='number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  )
}

// ── Mini health arc for fleet cards ───────────────────────────────
function MiniArc({ index }) {
  const R=44, cx=52, cy=52
  const start = Math.PI * 0.8
  const total = 2*Math.PI - (Math.PI*0.8 - Math.PI*0.2)
  const clamp = Math.max(0, Math.min(1, index??0))
  const filled = clamp * total
  const arc = (s, sw) => {
    const sx = cx+R*Math.cos(s), sy = cy+R*Math.sin(s)
    const ex = cx+R*Math.cos(s+sw), ey = cy+R*Math.sin(s+sw)
    return `M ${sx} ${sy} A ${R} ${R} 0 ${sw>Math.PI?1:0} 1 ${ex} ${ey}`
  }
  const color = clamp>.6?'#22d3a5':clamp>.25?'#f59e0b':'#ef4444'
  return (
    <svg width={104} height={68} viewBox="0 0 104 68" style={{overflow:'visible'}}>
      <path d={arc(start,total)} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={8} strokeLinecap="round"/>
      <path d={arc(start,filled)} fill="none" stroke={color} strokeWidth={8} strokeLinecap="round"
        style={{filter:`drop-shadow(0 0 6px ${color})`, transition:'all .6s ease'}}/>
      <text x={cx} y={cy-2} textAnchor="middle" dominantBaseline="middle"
        fill={color} style={{fontSize:16, fontWeight:800, fontFamily:'Inter,sans-serif'}}>
        {Math.round(clamp*100)}%
      </text>
      <text x={cx} y={cx+14} textAnchor="middle" dominantBaseline="middle"
        fill="#4a5568" style={{fontSize:9, fontFamily:'JetBrains Mono,monospace'}}>HEALTH</text>
    </svg>
  )
}

// ── Full health arc for detail view ───────────────────────────────
function HealthArc({ index }) {
  const R=70, cx=90, cy=90
  const start=Math.PI*.8, total=2*Math.PI-(Math.PI*.8-Math.PI*.2)
  const clamp=Math.max(0,Math.min(1,index??0))
  const arc=(s,sw)=>{
    const sx=cx+R*Math.cos(s),sy=cy+R*Math.sin(s)
    const ex=cx+R*Math.cos(s+sw),ey=cy+R*Math.sin(s+sw)
    return `M ${sx} ${sy} A ${R} ${R} 0 ${sw>Math.PI?1:0} 1 ${ex} ${ey}`
  }
  const color=clamp>.6?'#22d3a5':clamp>.25?'#f59e0b':'#ef4444'
  return (
    <div className="health-arc-container">
      <svg className="arc-svg" width={180} height={115} viewBox="0 0 180 115">
        <path d={arc(start,total)} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={10} strokeLinecap="round"/>
        <path d={arc(start,clamp*total)} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round"
          style={{filter:`drop-shadow(0 0 8px ${color})`,transition:'all .6s ease'}}/>
        <text x={cx} y={cy-4} className="arc-label" fill={color}>{Math.round(clamp*100)}%</text>
        <text x={cx} y={cy+18} className="arc-sublabel">Health Index</text>
      </svg>
    </div>
  )
}

// ── Bearing Fleet Card ─────────────────────────────────────────────
function BearingCard({ bid, state, wsState, onClick }) {
  const meta = BEARINGS[bid]
  const lat  = state.latest
  const hi   = lat?.health_index ?? 0
  const rul  = lat?.predicted_rul
  const st   = lat?.status ?? 'NORMAL'
  const step = lat?.step ?? '--'
  const isCrit = st === 'CRITICAL'
  const isWarn = st === 'WARNING'

  return (
    <div
      className={`fleet-card ${isCrit?'crit':isWarn?'warn':''}`}
      onClick={() => onClick(bid)}
    >
      <div className={`fc-status-bar ${st}`}/>
      <div className="fc-body">
        <div className="fc-top">
          <div>
            <div className="fc-id">{bid}</div>
            <div className="fc-name">{meta.name}</div>
            <div className="fc-loc">{meta.location}</div>
          </div>
          <StatusBadge status={st}/>
        </div>

        <div className="fc-arc-wrap">
          <MiniArc index={hi}/>
        </div>

        <div className="fc-metrics">
          <div className="fc-metric">
            <span className="fc-mval" style={{ color: rul < 30 ? '#ef4444' : rul < 60 ? '#f59e0b' : '#38bdf8' }}>
              {typeof rul==='number' ? rul.toFixed(0) : '--'}
            </span>
            <span className="fc-mkey">RUL Cycles</span>
          </div>
          <div className="fc-metric">
            <span className="fc-mval" style={{ color:'#8b9cb5' }}>{step}</span>
            <span className="fc-mkey">Step</span>
          </div>
        </div>

        <div className="fc-footer">
          <span className="fc-updated">
            {lat ? `Updated ${new Date().toLocaleTimeString()}` : 'Connecting…'}
          </span>
          <span className="fc-cta">View detail →</span>
        </div>
      </div>
    </div>
  )
}

// ── Fleet overview stats bar ───────────────────────────────────────
function FleetStatsBar({ bearingStates }) {
  const all    = BID_LIST.map(b => bearingStates[b].latest)
  const crits  = all.filter(l => l?.status==='CRITICAL').length
  const warns  = all.filter(l => l?.status==='WARNING').length
  const norms  = all.filter(l => l?.status==='NORMAL').length
  const avgHi  = all.filter(Boolean).reduce((s,l)=>s+(l.health_index??0),0)/(all.filter(Boolean).length||1)

  return (
    <div className="fleet-stats-bar">
      <div className="fstat">
        <span className="fstat-icon">🏭</span>
        <div>
          <div className="fstat-val">{BID_LIST.length}</div>
          <div className="fstat-key">Total Assets</div>
        </div>
      </div>
      <div className="fstat">
        <span className="fstat-icon">✅</span>
        <div>
          <div className="fstat-val" style={{color:'#22d3a5'}}>{norms}</div>
          <div className="fstat-key">Normal</div>
        </div>
      </div>
      <div className="fstat">
        <span className="fstat-icon">⚠️</span>
        <div>
          <div className="fstat-val" style={{color:'#f59e0b'}}>{warns}</div>
          <div className="fstat-key">Warning</div>
        </div>
      </div>
      <div className="fstat">
        <span className="fstat-icon">🚨</span>
        <div>
          <div className="fstat-val" style={{color:crits>0?'#ef4444':'#8b9cb5'}}>{crits}</div>
          <div className="fstat-key">Critical</div>
        </div>
      </div>
    </div>
  )
}

// ── Alert Feed (cross-fleet) ───────────────────────────────────────
function AlertFeed({ alerts }) {
  if (!alerts.length) return (
    <div className="alert-feed">
      <div className="alert-feed-header">
        <span className="card-title"><AlertTriangle size={13}/> Fleet Alert History</span>
        <span style={{fontSize:11,color:'var(--text-muted)'}}>No alerts yet</span>
      </div>
      <div className="af-empty">All bearings operating normally — alerts appear here automatically.</div>
    </div>
  )

  return (
    <div className="alert-feed">
      <div className="alert-feed-header">
        <span className="card-title"><AlertTriangle size={13}/> Fleet Alert History</span>
        <span style={{fontSize:11,color:'var(--text-muted)',fontFamily:'var(--font-mono)'}}>{alerts.length} events</span>
      </div>
      <div className="alert-feed-list">
        {alerts.map((ev, i) => (
          <div key={i} className={`af-item ${ev.status||ev.to_status}`}>
            <span className="af-bearing">{ev.bearing_id||ev.bid}</span>
            <span className="af-text">
              Status changed to <strong>{ev.status||ev.to_status}</strong>
              {ev.predicted_rul!=null && <> — RUL: <span style={{fontFamily:'var(--font-mono)',color:'var(--accent-cyan)'}}>{Number(ev.predicted_rul).toFixed(1)}</span> cycles</>}
            </span>
            <span className="af-time">{ev.time || (ev.ts ? new Date(ev.ts).toLocaleTimeString() : '')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Detail view ────────────────────────────────────────────────────
function DetailView({ bid, state, wsConnected, onBack }) {
  const meta  = BEARINGS[bid]
  const lat   = state.latest
  const hist  = state.history
  const evts  = state.events

  const hi   = lat?.health_index ?? 0
  const rul  = lat?.predicted_rul
  const trul = lat?.true_rul
  const st   = lat?.status ?? 'NORMAL'
  const step = lat?.step ?? 0
  const sens = lat?.sensors ?? Array(14).fill(0)
  const rc   = st==='CRITICAL'?'#ef4444':st==='WARNING'?'#f59e0b':'#38bdf8'

  const exportUrl = `/export/${bid}`

  return (
    <>
      {/* Breadcrumb + back */}
      <div className="detail-breadcrumb">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={14}/> Fleet Overview
        </button>
        <span style={{color:'var(--text-muted)',fontSize:13}}>/</span>
        <span style={{fontSize:13,color:'var(--text-secondary)'}}>{meta.name}</span>
      </div>

      {/* Hero */}
      <div className="detail-hero">
        <div className="dh-left">
          <div className="dh-icon">⚙️</div>
          <div>
            <div className="dh-id">{bid} · {meta.location}</div>
            <div className="dh-name">{meta.name}</div>
            <div className="dh-loc">{meta.desc}</div>
          </div>
        </div>
        <div className="dh-right">
          <StatusBadge status={st}/>
          <div className={`connection-badge ${wsConnected?'connected':'disconnected'}`}>
            {wsConnected ? <><Wifi size={13}/><span className="dot pulse"/></> : <WifiOff size={13}/>}
            {wsConnected ? 'Live' : 'Offline'}
          </div>
          <a className="export-btn" href={exportUrl} download>
            <Download size={13}/> Export CSV
          </a>
        </div>
      </div>

      {/* Alert banners */}
      {st==='CRITICAL' && (
        <div className="alert-banner CRITICAL">
          <XCircle size={16}/>
          <strong>CRITICAL:</strong> Severe bearing degradation. Immediate maintenance required — RUL: {typeof rul==='number'?rul.toFixed(1):rul} cycles.
        </div>
      )}
      {st==='WARNING' && (
        <div className="alert-banner WARNING">
          <AlertTriangle size={16}/>
          <strong>WARNING:</strong> Degradation detected. Schedule inspection — RUL: {typeof rul==='number'?rul.toFixed(1):rul} cycles.
        </div>
      )}

      {/* Metric cards */}
      <div className="grid-top">
        <div className="card metric-card">
          <div className="metric-icon"><TrendingDown/></div>
          <div className="card-title"><Clock size={13}/> Predicted RUL</div>
          <div className="metric-value" style={{color:rc}}>{typeof rul==='number'?rul.toFixed(0):'--'}</div>
          <div className="metric-label">Remaining Useful Life (cycles)</div>
        </div>
        <div className="card metric-card">
          <div className="metric-icon"><BarChart2/></div>
          <div className="card-title"><Gauge size={13}/> True RUL</div>
          <div className="metric-value" style={{color:'#6366f1'}}>{typeof trul==='number'?trul.toFixed(0):'--'}</div>
          <div className="metric-label">Ground Truth Cycles Remaining</div>
        </div>
        <div className="card metric-card">
          <div className="metric-icon"><Activity/></div>
          <div className="card-title"><Zap size={13}/> Prediction Error</div>
          <div className="metric-value" style={{color:'#f59e0b'}}>
            {(typeof rul==='number'&&typeof trul==='number') ? Math.abs(rul-trul).toFixed(1) : '--'}
          </div>
          <div className="metric-label">|Predicted − True| cycles</div>
        </div>
        <div className="card metric-card">
          <div className="metric-icon"><Cpu/></div>
          <div className="card-title"><Activity size={13}/> Run Step</div>
          <div className="metric-value" style={{color:'#22d3a5'}}>{step}</div>
          <div className="metric-label">Elapsed measurement steps</div>
        </div>
      </div>

      {/* Health arc + RUL chart */}
      <div className="grid-mid">
        <div className="card">
          <div className="card-header">
            <span className="card-title"><Gauge size={13}/> Health Index</span>
            <StatusBadge status={st}/>
          </div>
          <HealthArc index={hi}/>
          <div style={{marginTop:12,fontSize:12,color:'var(--text-secondary)',textAlign:'center',lineHeight:1.6}}>
            {st==='NORMAL'   && '✅ Operating within safe parameters.'}
            {st==='WARNING'  && '⚠️ Degradation detected. Increase monitoring.'}
            {st==='CRITICAL' && '🚨 Immediate shutdown recommended.'}
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title"><TrendingDown size={13}/> RUL Trend</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={hist} margin={{top:4,right:8,left:-20,bottom:0}}>
              <defs>
                <linearGradient id={`gT_${bid}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id={`gP_${bid}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={rc} stopOpacity={0.25}/>
                  <stop offset="95%" stopColor={rc} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)"/>
              <XAxis dataKey="step" tick={{fontSize:10,fill:'#4a5568'}}/>
              <YAxis tick={{fontSize:10,fill:'#4a5568'}} domain={[0,130]}/>
              <Tooltip content={<CustomTooltip/>}/>
              <ReferenceLine y={20} stroke="rgba(239,68,68,.4)" strokeDasharray="4 2"
                label={{value:'CRITICAL',fill:'#ef4444',fontSize:9}}/>
              <Area type="monotone" dataKey="true_rul"      name="True RUL"      stroke="#6366f1" fill={`url(#gT_${bid})`} strokeWidth={1.5} dot={false}/>
              <Area type="monotone" dataKey="predicted_rul" name="Predicted RUL" stroke={rc}      fill={`url(#gP_${bid})`} strokeWidth={2}   dot={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Sensors + events */}
      <div className="grid-bottom">
        <div className="card">
          <div className="card-header">
            <span className="card-title"><Activity size={13}/> Live Sensor Readings</span>
            <span style={{fontSize:11,color:'var(--text-muted)',fontFamily:'var(--font-mono)'}}>14 ch · 20 kHz</span>
          </div>
          <div className="sensor-grid">
            {SENSOR_NAMES.map((name,i)=>(
              <div key={name} className="sensor-cell">
                <div className="sensor-name">{name}</div>
                <div className="sensor-val">{typeof sens[i]==='number'?sens[i].toFixed(2):'--'}</div>
              </div>
            ))}
          </div>
          <div style={{marginTop:16}}>
            <div className="card-title" style={{marginBottom:8}}><BarChart2 size={13}/> Health Index Trend</div>
            <ResponsiveContainer width="100%" height={130}>
              <LineChart data={hist} margin={{top:2,right:8,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)"/>
                <XAxis dataKey="step" tick={{fontSize:9,fill:'#4a5568'}}/>
                <YAxis tick={{fontSize:9,fill:'#4a5568'}} domain={[0,1]}/>
                <Tooltip content={<CustomTooltip/>}/>
                <Line type="monotone" dataKey="health_index" name="H(t)" stroke="#22d3a5" strokeWidth={2} dot={false}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <span className="card-title"><AlertTriangle size={13}/> Alert History</span>
            <span style={{fontSize:11,color:'var(--text-muted)'}}>{evts.length} events</span>
          </div>
          {evts.length===0
            ? <div className="empty-state">Monitoring… status changes appear here.</div>
            : <div className="event-log">
                {evts.map((ev,i)=>(
                  <div key={i} className={`event-item ${ev.status}`}>
                    <div className="event-time">{ev.time}</div>
                    <div style={{fontSize:12,flex:1}}>
                      → <strong>{ev.status}</strong> — RUL: <span style={{fontFamily:'var(--font-mono)',color:'var(--accent-cyan)'}}>{Number(ev.rul).toFixed(1)}</span>
                    </div>
                  </div>
                ))}
              </div>
          }
        </div>
      </div>
    </>
  )
}

// ══════════════════════════════════════════════════════════════════
// MAIN APP
// ══════════════════════════════════════════════════════════════════
export default function App() {
  const [showSplash, setShowSplash] = useState(true)
  const [view, setView]             = useState('fleet')   // 'fleet' | 'detail'
  const [selected, setSelected]     = useState(null)      // bearing bid

  // Per-bearing state
  const initState = () => Object.fromEntries(BID_LIST.map(b => [b, { latest:null, history:[], events:[] }]))
  const [bearingStates, setBearingStates] = useState(initState)
  const [wsStates, setWsStates]           = useState(Object.fromEntries(BID_LIST.map(b=>[b,'disconnected'])))

  // Cross-fleet alert feed (merged from all bearings)
  const [globalAlerts, setGlobalAlerts] = useState([])

  const wsRefs      = useRef(Object.fromEntries(BID_LIST.map(b=>[b,null])))
  const prevStatus  = useRef(Object.fromEntries(BID_LIST.map(b=>[b,null])))

  // ── Connect one bearing's WebSocket ──────────────────────────────
  const connectBearing = useCallback((bid) => {
    if (wsRefs.current[bid]) wsRefs.current[bid].close()
    setWsStates(ws => ({...ws, [bid]:'connecting'}))
    const ws = new WebSocket(wsUrl(bid))
    wsRefs.current[bid] = ws

    ws.onopen  = () => setWsStates(ws => ({...ws, [bid]:'connected'}))
    ws.onclose = () => { setWsStates(ws => ({...ws, [bid]:'disconnected'})); wsRefs.current[bid]=null }
    ws.onerror = () => { ws.close() }

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)

      // Ping keepalive — ignore
      if (msg.type === 'ping') return

      // History backfill on connect
      if (msg.type === 'history' && Array.isArray(msg.data)) {
        setBearingStates(prev => ({
          ...prev,
          [bid]: { ...prev[bid], history: msg.data.slice(-MAX_HIST) }
        }))
        return
      }

      // Live telemetry tick
      const data = msg
      setBearingStates(prev => {
        const old = prev[bid]
        const nextHist = [...old.history, { ...data, step: data.step }]
        const trimmed  = nextHist.length > MAX_HIST ? nextHist.slice(-MAX_HIST) : nextHist

        // Detect status transition
        let nextEvents = old.events
        if (prevStatus.current[bid] && prevStatus.current[bid] !== data.status) {
          const ev = { time: new Date().toLocaleTimeString(), status: data.status, rul: data.predicted_rul, step: data.step }
          nextEvents = [ev, ...old.events].slice(0, 50)
          // Push to global fleet alert feed
          setGlobalAlerts(g => [{ ...ev, bearing_id: bid, bid }, ...g].slice(0, 100))
        }
        prevStatus.current[bid] = data.status

        return { ...prev, [bid]: { latest: data, history: trimmed, events: nextEvents } }
      })
    }
  }, [])

  // ── Mount: connect all 4 bearings ────────────────────────────────
  useEffect(() => {
    BID_LIST.forEach(bid => connectBearing(bid))
    return () => BID_LIST.forEach(bid => wsRefs.current[bid]?.close())
  }, [connectBearing])

  // ── Auto-reconnect any disconnected bearings ──────────────────────
  useEffect(() => {
    const t = setInterval(() => {
      BID_LIST.forEach(bid => {
        if (wsStates[bid] === 'disconnected') connectBearing(bid)
      })
    }, 5000)
    return () => clearInterval(t)
  }, [wsStates, connectBearing])

  // ── Fleet stats ───────────────────────────────────────────────────
  const connectedCount = BID_LIST.filter(b => wsStates[b]==='connected').length

  const wsCountClass = connectedCount === 4 ? '' : connectedCount > 0 ? 'partial' : 'offline'

  return (
    <>
      {showSplash && <SplashScreen onComplete={() => setShowSplash(false)}/>}
      <div className="app" style={{opacity:showSplash?0:1, transition:'opacity .5s ease'}}>

        {/* ── Header ── */}
        <header className="header">
          <div className="header-brand">
            <div className="brand-icon">⚙️</div>
            <div>
              <div className="brand-title">Physics-Informed Digital Twin</div>
              <div className="brand-sub">Industrial Fleet Health Monitor · Real-Time RUL Prediction</div>
            </div>
          </div>

          <div style={{display:'flex',alignItems:'center',gap:6}}>
            <button className={`nav-tab ${view==='fleet'?'active':''}`}
              onClick={()=>{setView('fleet');setSelected(null)}}>
              <Layers size={13} style={{marginRight:5}}/>Fleet
            </button>
            {selected && (
              <button className={`nav-tab ${view==='detail'?'active':''}`}
                onClick={()=>setView('detail')}>
                {BEARINGS[selected]?.name}
              </button>
            )}
          </div>

          <div className="header-right">
            <span className={`ws-count ${wsCountClass}`}>
              <span className="dot pulse" style={{display:'inline-block',marginRight:5}}/>
              {connectedCount}/{BID_LIST.length} Live
            </span>
          </div>
        </header>

        {/* ── Main content ── */}
        <main className="main">
          {view === 'fleet' ? (
            <>
              {/* Fleet stats bar */}
              <FleetStatsBar bearingStates={bearingStates}/>

              {/* 4-bearing grid */}
              <div className="fleet-grid">
                {BID_LIST.map(bid => (
                  <BearingCard
                    key={bid} bid={bid}
                    state={bearingStates[bid]}
                    wsState={wsStates[bid]}
                    onClick={(b)=>{ setSelected(b); setView('detail') }}
                  />
                ))}
              </div>

              {/* Cross-fleet alert feed */}
              <AlertFeed alerts={globalAlerts}/>
            </>
          ) : (
            selected && (
              <DetailView
                bid={selected}
                state={bearingStates[selected]}
                wsConnected={wsStates[selected]==='connected'}
                onBack={()=>{ setView('fleet'); setSelected(null) }}
              />
            )
          )}
        </main>

        <footer className="footer">
          Physics-Informed Digital Twin · Fleet Monitor · BIT Mesra · Ujjwal Deep · {new Date().getFullYear()}
        </footer>
      </div>
    </>
  )
}
