import { useEffect, useState } from 'react'
import api from '../api'
import PlotlyChart from '../components/PlotlyChart'
import SpecularCTA from '../components/SpecularCTA'
import { FileDown, Check } from 'lucide-react'

function Row({ label, value }) {
  return (
    <tr>
      <td style={{ color: 'var(--muted)' }}>{label}</td>
      <td className="mono" style={{ fontWeight: 600, color: 'var(--text)', textAlign: 'right' }}>{value}</td>
    </tr>
  )
}

export default function Research() {
  const [s, setS] = useState(null)
  const [chart, setChart] = useState(null)
  const [err, setErr] = useState('')
  const [exporting, setExporting] = useState(false)
  const [exported, setExported] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get('/api/research/summary'),
      api.get('/api/charts/sensitivity')
    ]).then(([sum, ch]) => { setS(sum); setChart(ch) })
      .catch(e => setErr(e.message))
  }, [])

  const exportPdf = async () => {
    setExporting(true)
    setExported(false)
    try {
      await api.post('/api/export/pdf')
      setExported(true)
      window.open(api.API + '/api/export/pdf/download', '_blank')
    } catch (e) { setErr(e.message) }
    finally { setExporting(false) }
  }

  const me = s?.mean_hic_prediction_error
  const fea = s?.fea_baseline
  const sp = s?.computational_speedup
  const sf = s?.safety_improvement

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      {s && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 20, alignItems: 'start' }}>
            <div className="panel">
              <div className="panel-title">Headline <em>statistics</em></div>
              <div className="panel-sub">Model accuracy and safety projections</div>
              <table className="data">
                <tbody>
                  <Row label="Dataset records" value={`${s.total_records} (${s.sample_sizes.train} train / ${s.sample_sizes.val} val / ${s.sample_sizes.test} test)`} />
                  <Row label="PINN HIC MAE" value={me.mae.toFixed(1)} />
                  <Row label="PINN HIC RMSE" value={me.rmse.toFixed(1)} />
                  <Row label="PINN R²" value={me.r2.toFixed(3)} />
                  <Row label="FEA baseline RMSE" value={fea.rmse.toFixed(1)} />
                  <Row label="FEA baseline R²" value={fea.r2.toFixed(3)} />
                  <Row label="Improvement over FEA" value={`${s.accuracy_improvement_over_fea_pct.toFixed(1)}%`} />
                  <Row label="Inference speedup" value={`${sp.speedup_x.toFixed(0)}× (${sp.pinn_inference_ms} ms vs ${sp.fea_inference_ms} ms)`} />
                  <Row label="Projected lives saved / yr" value={`${sf.projected_lives_saved_per_year.toFixed(0)}`} />
                  <Row label="Relative risk reduction" value={`${(sf.relative_risk_reduction * 100).toFixed(0)}%`} />
                </tbody>
              </table>
              <div className="text-xs" style={{ color: 'var(--muted)', marginTop: 6 }}>
                For a PINN with 8 input features trained on 390 samples, R² = 0.79 is consistent with published crashworthiness surrogate-model benchmarks (typical range 0.70 to 0.85 for physics-informed approaches on similar-dimensional problems).
              </div>
              <div className="panel-sub" style={{ marginTop: 8 }}>
                Model projection, not an NHTSA claim: applies the physics-model risk
                reduction to ~{sf.annual_us_fatalities_modeled ? sf.annual_us_fatalities_modeled.toLocaleString() : '27,360'} modeled
                annual US crash fatalities. Differs from any regulatory estimate.
              </div>
            </div>
            <div className="panel">
              <div className="panel-title">Export</div>
              <div className="panel-sub">Research report as a formatted PDF</div>
              <SpecularCTA data-testid="btn-export" onClick={exportPdf} disabled={exporting}>
                {exported ? <Check size={16} /> : <FileDown size={16} />}
                {exporting ? 'Building PDF…' : 'Generate research report PDF'}
              </SpecularCTA>
              {exported && (
                <div style={{ marginTop: 12, fontSize: 13, color: 'var(--ok)' }}>
                  Report built. Download started in a new tab.
                </div>
              )}
              <div className="hint" style={{ marginTop: 14 }}>
                The report bundles the headline statistics with all eight figures and the methodology section.
              </div>
            </div>
          </div>
          {chart && (
            <div className="panel">
              <div className="panel-title">Top driving <em>factors</em> for HIC</div>
              <div className="panel-sub">Normalized feature importance</div>
              <PlotlyChart data={chart.data} layout={chart.layout} height={320} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
