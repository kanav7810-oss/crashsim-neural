import { useState } from 'react'
import api from '../api'
import GeometryForm from '../components/GeometryForm'
import CrumpleAnimation from '../components/CrumpleAnimation'
import IntrusionDiagram from '../components/IntrusionDiagram'
import SpecularCTA from '../components/SpecularCTA'
import AnimatedNumber from '../components/AnimatedNumber'
import { DEFAULT_GEOMETRY } from '../geometry'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { Play } from 'lucide-react'
import { C, hicColor, TOOLTIP } from '../theme'

function Metric({ label, value, unit, color, dp = 2 }) {
  const numeric = typeof value === 'number' && isFinite(value)
  return (
    <div style={{ padding: '12px 14px', border: '1px solid var(--border)', borderRadius: 'var(--radius-s)', background: 'oklch(0.17 0.01 60 / 0.5)' }}>
      <div className="micro">{label}</div>
      <div className="num" style={{ fontSize: 20, fontWeight: 600, color: color || 'var(--text)', marginTop: 5, lineHeight: 1.15 }}>
        {numeric ? <AnimatedNumber value={value} format={v => v.toFixed(dp)} /> : (value ?? '-')}{unit}
      </div>
    </div>
  )
}

export default function ScenarioBuilder() {
  const [geom, setGeom] = useState(DEFAULT_GEOMETRY)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    setErr('')
    try {
      const r = await api.post('/api/predict', geom)
      setResult(r)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  const pinn = result?.pinn
  const fea = result?.fea
  const physics = result?.physics

  const compareData = pinn ? [
    { name: 'HIC', PINN: Math.round(pinn.hic), FEA: Math.round(fea.hic) },
    { name: 'Chest g', PINN: +pinn.chest_g.toFixed(1), FEA: +fea.chest_g.toFixed(1) }
  ] : []

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20, alignItems: 'start' }}>
      <div className="panel">
        <div className="panel-title">Vehicle &amp; <em>crash</em> configuration</div>
        <div className="panel-sub">Set geometry and run a full injury prediction</div>
        <GeometryForm value={geom} onChange={setGeom} />
        <div style={{ marginTop: 16 }}>
          <SpecularCTA data-testid="btn-run-predict" onClick={run} disabled={loading}>
            <Play size={15} /> {loading ? 'Running…' : 'Run full injury prediction'}
          </SpecularCTA>
        </div>
        {err && <div data-testid="predict-error" style={{ color: 'var(--danger)', marginTop: 12 }}>{err}</div>}
      </div>

      {result && (
        <>
          <div className="panel">
            <div className="panel-title"><em>Prediction</em> report</div>
            <div className="panel-sub">PINN outputs vs FEA baseline</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10, marginBottom: 16 }}>
              <Metric label={<>HIC<sub>36</sub> (PINN)</>} value={pinn.hic} dp={0} color={hicColor(pinn.hic)} />
              <Metric label="Chest decel" value={pinn.chest_g} unit=" g" dp={1} />
              <Metric label="Intrusion" value={pinn.intrusion_m} unit=" m" />
              <Metric label="Fatality risk" value={pinn.fatality_prob * 100} unit="%" color={pinn.fatality_prob < 0.1 ? C.ok : C.danger} />
            </div>
            <div className="hint" style={{ marginBottom: 12 }}>
              FMVSS 208 HIC threshold: 1000. HIC below 700 is considered low risk.
            </div>
            <div style={{ height: 190 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={compareData} data-testid="pinn-fea-chart" layout="vertical" margin={{ left: 10, right: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
                  <XAxis type="number" stroke={C.muted} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" stroke={C.text2} width={70} tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={TOOLTIP} cursor={{ fill: 'rgba(199,154,85,0.08)' }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="PINN" fill={C.accent} radius={[0, 4, 4, 0]} />
                  <Bar dataKey="FEA" fill={C.muted} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="hint" style={{ marginTop: 10 }}>
              Physics crush: {physics.crush_m.toFixed(2)} m. Energy absorbed: {(physics.energy_absorbed_j / 1000).toFixed(0)} kJ of {((physics.kinetic_energy_j || 0) / 1000).toFixed(0)} kJ.
            </div>
          </div>
          <div className="panel">
            <div className="panel-title">Crumple zone <em>deformation</em></div>
            <div className="panel-sub">Frontal crush at {geom.velocity_kmh} km/h</div>
            <CrumpleAnimation crush={physics.crush_m} peakG={physics && Math.max(...(result.animation.accel_head_g || [0]))}
              hic={pinn.hic} runKey={JSON.stringify(geom)} />
          </div>
          <div className="panel">
            <div className="panel-title">Structural <em>intrusion</em></div>
            <div className="panel-sub">Pillar buckling profile</div>
            <IntrusionDiagram intrusion={pinn.intrusion_m} profile={result.animation.intrusion_profile} />
          </div>
        </>
      )}
    </div>
  )
}
