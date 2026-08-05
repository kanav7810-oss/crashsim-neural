import { useEffect, useState } from 'react'
import api from '../api'
import GeometryForm from '../components/GeometryForm'
import PlotlyChart from '../components/PlotlyChart'
import AnimatedNumber from '../components/AnimatedNumber'
import Tilt from '../components/Tilt'
import { DEFAULT_GEOMETRY } from '../geometry'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { C, hicColor, TOOLTIP } from '../theme'

function Readout({ label, value, format, color }) {
  const numeric = typeof value === 'number' && isFinite(value)
  return (
    <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 14, transform: 'translateZ(30px)' }}>
      <div className="micro">{label}</div>
      <div className="num" style={{ fontSize: 28, fontWeight: 600, color: color || 'var(--text)', marginTop: 4, lineHeight: 1.1 }}>
        {numeric
          ? <AnimatedNumber value={value} format={format || (v => String(Math.round(v)))} />
          : (value ?? '-')}
      </div>
    </div>
  )
}

export default function GeometryOptimizer() {
  const [geom, setGeom] = useState(DEFAULT_GEOMETRY)
  const [pred, setPred] = useState(null)
  const [surface, setSurface] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [sweep, setSweep] = useState([])
  const [sweepSpeed, setSweepSpeed] = useState(56)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/api/charts/injury_surface').then(setSurface).catch(() => {})
    api.get('/api/charts/crumple_efficiency').then(setHeatmap).catch(() => {})
  }, [])

  // Debounced auto-prediction: instant feedback as sliders move.
  useEffect(() => {
    const t = setTimeout(() => {
      api.post('/api/predict', geom).then(r => {
        setPred(r)
        setErr('')
      }).catch(() => setPred(null))
    }, 250)
    return () => clearTimeout(t)
  }, [geom])

  // Parameter sweep for the velocity slider.
  useEffect(() => {
    const t = setTimeout(() => {
      api.post('/api/parameter-sweep', {
        param: 'velocity_kmh', low: 10, high: 120, steps: 28, geometry: geom
      }).then(r => setSweep(r.points)).catch(() => {})
    }, 200)
    return () => clearTimeout(t)
  }, [geom])

  const pinn = pred?.pinn
  const speedHic = sweep.length ? sweep[Math.round((sweepSpeed - 10) / 110 * (sweep.length - 1))] : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}

      <div className="panel">
        <div className="panel-title">Live <em>readout</em></div>
        <div className="panel-sub">Auto-predicts as geometry changes</div>
        <Tilt max={3} style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
          <Readout label="Predicted HIC" value={pinn?.hic} format={v => v.toFixed(0)} color={pinn ? hicColor(pinn.hic) : undefined} />
          <Readout label="Fatality probability" value={pinn?.fatality_prob} format={v => (v * 100).toFixed(2) + '%'} />
          <Readout label="Chest g-force" value={pinn?.chest_g} format={v => v.toFixed(1)} />
        </Tilt>
        <div style={{ marginTop: 20 }}>
          <GeometryForm value={geom} onChange={setGeom} compact />
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">Parameter sweep: <em>impact</em> velocity</div>
        <div className="panel-sub">Drag the slider; the HIC curve updates in real time</div>
        <input type="range" min={10} max={120} step={1} value={sweepSpeed} data-testid="sweep-slider"
          onChange={e => setSweepSpeed(parseInt(e.target.value))} style={{ width: '100%' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
          <span>10 km/h</span>
          <span className="mono" data-testid="sweep-value">
            {sweepSpeed} km/h {speedHic ? `| HIC ${speedHic.hic_pinn.toFixed(0)}` : ''}
          </span>
          <span>120 km/h</span>
        </div>
        <div style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sweep} margin={{ left: 0, right: 10, top: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
              <XAxis dataKey="x" stroke={C.muted} label={{ value: 'km/h', position: 'insideBottomRight', fill: C.muted, fontSize: 11 }} tick={{ fontSize: 11 }} tickFormatter={v => Math.round(v)} interval={Math.floor(sweep.length / 8)} />
              <YAxis stroke={C.muted} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={TOOLTIP} labelFormatter={v => `${Math.round(v)} km/h`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="hic_pinn" name="PINN HIC" stroke={C.accent} strokeWidth={2} dot={false} />
              <Line dataKey="hic_fea" name="FEA HIC" stroke={C.muted} strokeWidth={2} strokeDasharray="5 4" dot={false} />
              <ReferenceLine x={sweepSpeed} stroke={C.text2} strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20, alignItems: 'start' }}>
        {surface && (
          <div className="panel">
            <div className="panel-title">Injury <em>risk</em> surface</div>
            <div className="panel-sub">HIC vs impact velocity and A-pillar thickness</div>
            <PlotlyChart data={surface.data} layout={surface.layout} height={340} />
          </div>
        )}
        {heatmap && (
          <div className="panel">
            <div className="panel-title">Crumple zone <em>efficiency</em></div>
            <div className="panel-sub">Absorbed energy per kg across geometry</div>
            <PlotlyChart data={heatmap.data} layout={heatmap.layout} height={340} />
          </div>
        )}
      </div>
    </div>
  )
}
