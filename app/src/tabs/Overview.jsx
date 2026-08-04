import { useEffect, useState } from 'react'
import api from '../api'
import PlotlyChart from '../components/PlotlyChart'
import AnimatedNumber from '../components/AnimatedNumber'
import Tilt from '../components/Tilt'
import { ChevronDown } from 'lucide-react'

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
  const [showLives, setShowLives] = useState(false)

  useEffect(() => {
    let alive = true
    Promise.all([
      api.get('/api/research/summary'),
      api.get('/api/charts/historical_trend'),
      api.get('/api/charts/class_comparison'),
      api.get('/api/dataset/summary')
    ]).then(([s, h, c, ds]) => {
      if (!alive) return
      setSummary(s)
      setCharts({ historical: h, classes: c })
      setSummary(s => ({ ...s, dataset: ds }))
    }).catch(e => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const s = summary || {}
  const me = s.mean_hic_prediction_error || {}
  const ci = me.mae_ci_95 || null
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
              sub={ci ? `95% bootstrap CI: ${ci.ci_low.toFixed(1)}–${ci.ci_high.toFixed(1)} · R² ${me.r2 ? me.r2.toFixed(2) : '-'} (within PINN benchmark range 0.70–0.85)` : `RMSE ${me.rmse ? me.rmse.toFixed(1) : '-'} · R² ${me.r2 ? me.r2.toFixed(2) : '-'}`} />
            <Metric label="FEA baseline MAE"
              value={s.fea_baseline ? s.fea_baseline.mae : null}
              format={v => v.toFixed(1)}
              sub="linear elastic axial solver (deliberately simple lower bound for internal comparison)" />
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

      {summary && (
        <div className="panel" style={{ padding: 18 }}>
          <button className="btn btn-ghost" data-testid="btn-lives-toggle"
            onClick={() => setShowLives(v => !v)}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ChevronDown size={14} style={{ transform: showLives ? 'rotate(180deg)' : 'none', transition: 'transform 160ms' }} />
            How is the lives-saved projection calculated?
          </button>
          {showLives && (
            <div style={{ marginTop: 14, fontSize: 13, lineHeight: 1.6, color: 'var(--text-2)' }}>
              <p style={{ marginTop: 0 }}>
                For every crash configuration in the synthetic dataset, the physics engine is re-run with an
                <em> optimal structural geometry</em> (90th percentile A-pillar thickness and crumple-zone length,
                85th percentile yield strength within the vehicle class). The relative reduction in mean fatality
                probability is then applied to the share of US crash fatalities attributable to frontal, side and
                rollover events.
              </p>
              <pre className="mono" style={{ background: 'oklch(0.17 0.01 60 / 0.7)', padding: 12, borderRadius: 6, overflowX: 'auto', fontSize: 12 }}>
reduction           = 1 - mean_fatality_optimal / mean_fatality_current
                    = 1 - {sf.optimal_mean_fatality ? sf.optimal_mean_fatality.toFixed(4) : '-'} / {sf.current_mean_fatality ? sf.current_mean_fatality.toFixed(4) : '-'}
                    = {(sf.relative_risk_reduction * 100).toFixed(1)}%
modeled_fatalities  = 38,000 US/yr × 0.72 (frontal+side+rollover share)
                    = {sf.annual_us_fatalities_modeled ? Math.round(sf.annual_us_fatalities_modeled).toLocaleString() : '27,360'}
lives_saved         = reduction × modeled_fatalities
                    = {(sf.relative_risk_reduction * 100).toFixed(0)}% × {sf.annual_us_fatalities_modeled ? Math.round(sf.annual_us_fatalities_modeled).toLocaleString() : '27,360'}
                    ≈ {Math.round(sf.projected_lives_saved_per_year).toLocaleString()}
              </pre>
              <p style={{ marginBottom: 0, color: 'var(--muted)' }}>
                The 38,000 annual US crash fatalities and the 0.72 modeled-mode share come from public NHTSA-style
                reporting; they are scalar inputs in <code>analysis/safety.py</code>, not learned from the synthetic dataset.
                The reduction percentage <em>is</em> derived from the synthetic physics-engine re-run, so the
                projected lives-saved figure is a methodology illustration, not a regulatory estimate.
              </p>
            </div>
          )}
        </div>
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
            <div className="panel-sub">95% CI · overlapping CIs indicate the model distinguishes weakly between classes on HIC alone, an acknowledged limitation (see Research tab)</div>
            <PlotlyChart data={charts.classes.data} layout={charts.classes.layout} height={300} />
          </div>
        )}
      </div>
    </div>
  )
}
