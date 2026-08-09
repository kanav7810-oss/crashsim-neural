import { useEffect, useState } from 'react'
import api from '../api'
import PlotlyChart from '../components/PlotlyChart'
import AnimatedNumber from '../components/AnimatedNumber'
import Tilt from '../components/Tilt'

function Metric({ label, value, sub, format }) {
  const numeric = typeof value === 'number' && isFinite(value)
  return (
    <div>
      <div className="micro">{label}</div>
      <div className="num" style={{ fontSize: 24, fontWeight: 600, color: 'var(--text)', margin: '6px 0 2px', lineHeight: 1.1 }}>
        {numeric
          ? <AnimatedNumber value={value} format={format || (v => String(Math.round(v)))} />
          : (value ?? '-')}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--muted)' }}>{sub}</div>}
    </div>
  )
}

export default function Overview() {
  const [summary, setSummary] = useState(null)
  const [charts, setCharts] = useState({})
  const [err, setErr] = useState('')

  useEffect(() => {
    let alive = true
    Promise.all([
      api.get('/api/research/summary'),
      api.get('/api/charts/historical_trend'),
      api.get('/api/charts/class_comparison'),
      api.get('/api/charts/calibration'),
      api.get('/api/dataset/summary')
    ]).then(([s, h, c, cal, ds]) => {
      if (!alive) return
      setSummary(s)
      setCharts({ historical: h, classes: c, calibration: cal })
      setSummary(s => ({ ...s, dataset: ds }))
    }).catch(e => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const s = summary || {}
  const me = s.mean_hic_prediction_error || {}
  const sp = s.computational_speedup || {}
  const sf = (s.safety_improvement || {})

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {err && <div style={{ color: 'var(--danger)' }}>Failed to load: {err}</div>}

      {summary && (
        <Tilt max={2.5} className="panel" style={{ padding: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '28px 24px' }}>
            <Metric label="Dataset records"
              value={s.dataset ? s.dataset.total : s.total_records}
              sub={`${s.sample_sizes.train} train / ${s.sample_sizes.val} val / ${s.sample_sizes.test} test · synthetic, acknowledged limitation`} />
            <Metric label="PINN HIC MAE"
              value={me.mae}
              format={v => v.toFixed(1)}
              sub={`RMSE ${me.rmse ? me.rmse.toFixed(1) : '-'} | R² ${me.r2 ? me.r2.toFixed(2) : '-'} (within PINN benchmark range 0.70-0.85)`} />
            <Metric label="FEA baseline MAE"
              value={s.fea_baseline ? s.fea_baseline.mae : null}
              format={v => v.toFixed(1)}
              sub="linear elastic solver" />
            <Metric label="Improvement vs FEA"
              value={s.accuracy_improvement_over_fea_pct}
              format={v => v.toFixed(0) + '%'}
              sub="HIC RMSE reduction" />
            <Metric label="Inference speedup"
              value={sp.speedup_x}
              format={v => v.toFixed(0) + '×'}
              sub={`PINN ${sp.pinn_inference_ms ? sp.pinn_inference_ms : '-'} ms vs FEA ${sp.fea_inference_ms ? sp.fea_inference_ms : '-'} ms`} />
            <Metric label="Projected lives saved / yr"
              value={sf.projected_lives_saved_per_year}
              format={v => Math.round(v).toLocaleString()}
              sub={`risk reduction ${(sf.relative_risk_reduction * 100).toFixed(0)}% · model estimate, not NHTSA`} />
          </div>
        </Tilt>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20, alignItems: 'start' }}>
        {charts.historical && (
          <div className="panel">
            <div className="panel-title">Synthetic HIC <em>safety</em> trend</div>
            <div className="panel-sub">Median HIC by model year, 2000-2024 (NHTSA-schema data)</div>
            <PlotlyChart data={charts.historical.data} layout={charts.historical.layout} height={300} />
          </div>
        )}
        {charts.classes && (
          <div className="panel">
            <div className="panel-title">Mean HIC by vehicle <em>class</em></div>
            <div className="panel-sub">95% CI</div>
            <PlotlyChart data={charts.classes.data} layout={charts.classes.layout} height={300} />
          </div>
        )}
        {charts.calibration && (
          <div className="panel">
            <div className="panel-title">Model <em>calibration</em></div>
            <div className="panel-sub">Predicted vs observed fatality probability</div>
            <PlotlyChart data={charts.calibration.data} layout={charts.calibration.layout} height={300} />
          </div>
        )}
      </div>
    </div>
  )
}
