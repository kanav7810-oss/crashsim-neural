import { useState } from 'react'
import api from '../api'
import GeometryForm from '../components/GeometryForm'
import SpecularCTA from '../components/SpecularCTA'
import { DEFAULT_GEOMETRY } from '../geometry'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { GitCompare } from 'lucide-react'
import { C, hicColor, TOOLTIP } from '../theme'

function Side({ title, geom, onChange, result }) {
  const p = result?.pinn
  const f = result?.fea
  return (
    <div className="panel">
      <div className="panel-title">{title}</div>
      <div className="panel-sub">Geometry configuration</div>
      <GeometryForm value={geom} onChange={onChange} compact />
      {p && (
        <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
          <div className="micro" style={{ marginBottom: 8 }}>Prediction</div>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            <div>
              <span className="num" style={{ fontSize: 22, fontWeight: 600, color: hicColor(p.hic) }}>{p.hic.toFixed(0)}</span>
              <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 6 }}>HIC</span>
            </div>
            <div>
              <span className="num" style={{ fontSize: 22, fontWeight: 600 }}>{p.chest_g.toFixed(1)}</span>
              <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 6 }}>g</span>
            </div>
            <div>
              <span className="num" style={{ fontSize: 22, fontWeight: 600 }}>{p.fatality_prob.toFixed(3)}</span>
              <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 6 }}>p<sub>fat</sub></span>
            </div>
          </div>
          <div className="hint" style={{ marginTop: 8 }}>
            FEA baseline: HIC {f.hic.toFixed(0)} | crush {f.crush_m.toFixed(2)} m
          </div>
        </div>
      )}
    </div>
  )
}

export default function Comparison() {
  const [a, setA] = useState(DEFAULT_GEOMETRY)
  const [b, setB] = useState({ ...DEFAULT_GEOMETRY, mass_kg: 2100, vehicle_class: 'suv', velocity_kmh: 72 })
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')

  const run = async () => {
    setErr('')
    try {
      const r = await api.post('/api/compare', { vehicle_a: a, vehicle_b: b })
      setResult(r)
    } catch (e) { setErr(e.message) }
  }

  const chartData = result ? [
    { name: 'HIC', 'Vehicle A': Math.round(result.vehicle_a.pinn.hic), 'Vehicle B': Math.round(result.vehicle_b.pinn.hic) },
    { name: 'Chest g', 'Vehicle A': +result.vehicle_a.pinn.chest_g.toFixed(1), 'Vehicle B': +result.vehicle_b.pinn.chest_g.toFixed(1) },
    { name: 'Intrusion cm', 'Vehicle A': +(result.vehicle_a.pinn.intrusion_m * 100).toFixed(1), 'Vehicle B': +(result.vehicle_b.pinn.intrusion_m * 100).toFixed(1) },
    { name: 'Fatality %', 'Vehicle A': +(result.vehicle_a.pinn.fatality_prob * 100).toFixed(2), 'Vehicle B': +(result.vehicle_b.pinn.fatality_prob * 100).toFixed(2) }
  ] : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20 }}>
        <Side title="Vehicle A" geom={a} onChange={setA} result={result?.vehicle_a} />
        <Side title="Vehicle B" geom={b} onChange={setB} result={result?.vehicle_b} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <SpecularCTA data-testid="btn-compare" onClick={run}>
          <GitCompare size={16} /> Compare vehicles
        </SpecularCTA>
        {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      </div>
      {result && (
        <div className="panel">
          <div className="panel-title">Side-by-side <em>injury</em> metrics</div>
          <div className="panel-sub">PINN predictions for both configurations</div>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
                <XAxis dataKey="name" stroke={C.text2} tick={{ fontSize: 12 }} />
                <YAxis stroke={C.muted} tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={TOOLTIP} cursor={{ fill: 'rgba(199,154,85,0.08)' }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Vehicle A" fill={C.accent} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Vehicle B" fill={C.secondary} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
