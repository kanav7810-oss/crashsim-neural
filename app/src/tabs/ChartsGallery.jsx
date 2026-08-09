import { useEffect, useState } from 'react'
import api from '../api'
import PlotlyChart from '../components/PlotlyChart'

const CHART_META = [
  { name: 'accuracy_curves', title: <>PINN training <em>accuracy</em> curves</>, sub: 'Training and validation HIC RMSE over epochs' },
  { name: 'injury_surface', title: <>Injury risk <em>surface</em></>, sub: 'HIC vs impact velocity and A-pillar thickness' },
  { name: 'class_comparison', title: <>Performance by vehicle <em>class</em></>, sub: 'Prediction error with 95% CI' },
  { name: 'crumple_efficiency', title: <>Crumple zone <em>efficiency</em></>, sub: 'Energy absorption across vehicle classes and test types' },
  { name: 'sensitivity', title: <>Feature <em>sensitivity</em> (SHAP)</>, sub: 'Which inputs drive HIC predictions' },
  { name: 'historical_trend', title: <>Historical <em>safety</em> trend</>, sub: 'Median HIC by model year 2000-2024' },
  { name: 'fatality_by_crash_type', title: <>Fatality probability by <em>crash</em> type</>, sub: 'AIS severity distribution' },
  { name: 'calibration', title: <>Model <em>calibration</em></>, sub: 'Predicted vs observed risk' }
]

export default function ChartsGallery() {
  const [charts, setCharts] = useState({})
  const [err, setErr] = useState('')

  useEffect(() => {
    let alive = true
    Promise.all(CHART_META.map(c => api.get(`/api/charts/${c.name}`).then(f => [c.name, f])))
      .then(entries => alive && setCharts(Object.fromEntries(entries)))
      .catch(e => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: 20, alignItems: 'start' }}>
        {CHART_META.map(c => (
          <div className="panel" key={c.name}>
            <div className="panel-title">{c.title}</div>
            <div className="panel-sub">{c.sub}</div>
            {charts[c.name] ? (
              <PlotlyChart data={charts[c.name].data} layout={charts[c.name].layout} height={320} />
            ) : (
              <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 13 }}>
                Loading…
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
