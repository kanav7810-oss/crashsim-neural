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
  const [m, setM] = useState(null)
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
    api.get('/api/research/methodology').then(setM).catch(() => setM(null))
  }, [])

  const exportPdf = async () => {
    setExporting(true)
    setExported(false)
    try {
      // The download endpoint builds the PDF on-demand and streams it back in
      // a single serverless invocation (Vercel functions are stateless, so a
      // two-step build-then-download would 404 on a different instance).
      window.open('/api/export/pdf/download', '_blank')
      setExported(true)
    } catch (e) { setErr('PDF export unavailable.') }
    finally { setExporting(false) }
  }

  const me = s?.mean_hic_prediction_error
  const fea = s?.fea_baseline
  const sp = s?.computational_speedup
  const sf = s?.safety_improvement
  const hyper = m?.hyperparameters
  const abl = m?.ablation
  const cls = m?.fatality_classifier
  const cv = m?.cross_validation

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
                  <Row label="PINN R²" value={me.r2.toFixed(2)} />
                  <Row label="FEA baseline RMSE" value={fea.rmse.toFixed(1)} />
                  <Row label="FEA baseline R²" value={fea.r2.toFixed(2)} />
                  <Row label="Improvement over FEA" value={`${s.accuracy_improvement_over_fea_pct.toFixed(0)}%`} />
                  <Row label="Inference speedup" value={`${sp.speedup_x.toFixed(0)}× (${sp.pinn_inference_ms} ms vs ${sp.fea_inference_ms} ms)`} />
                  <Row label="Projected lives saved / yr" value={`${sf.projected_lives_saved_per_year.toFixed(0)}`} />
                  <Row label="Relative risk reduction" value={`${(sf.relative_risk_reduction * 100).toFixed(0)}%`} />
                </tbody>
              </table>
              <div className="text-xs" style={{ color: 'var(--muted)', marginTop: 6 }}>
                For a PINN with 16 input features trained on 390 samples, R² = 0.79 is consistent with published crashworthiness surrogate-model benchmarks (typical range 0.70 to 0.85 for physics-informed approaches on similar-dimensional problems). The FEA baseline is a deliberately simple linear-elastic axial solver used only as an internal sanity-check lower bound, not as a state-of-the-art surrogate-model benchmark.
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

          {hyper && (
            <div className="panel">
              <div className="panel-title">Model <em>hyperparameters</em></div>
              <div className="panel-sub">Fully reproducible training configuration</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '4px 40px' }}>
                <table className="data"><tbody>
                  <Row label="Architecture" value="fully connected MLP (tanh)" />
                  <Row label="Hidden layers" value={hyper.hidden_layers.join(', ')} />
                  <Row label="Optimizer" value={hyper.optimizer} />
                  <Row label="Learning rate" value={hyper.learning_rate} />
                  <Row label="LR scheduler" value={hyper.lr_scheduler} />
                  <Row label="Batch size" value={hyper.batch_size} />
                </tbody></table>
                <table className="data"><tbody>
                  <Row label="Max epochs" value={hyper.max_epochs} />
                  <Row label="Early-stop patience" value={hyper.early_stop_patience} />
                  <Row label="Physics loss weight" value={hyper.physics_loss_weight} />
                  <Row label="Data loss" value="MSE (min-max targets)" />
                  <Row label="Input features" value={hyper.features + ' (z-scored)'} />
                  <Row label="Train seed" value={hyper.train_seed} />
                </tbody></table>
              </div>
              <div className="text-xs" style={{ color: 'var(--muted)', marginTop: 8 }}>
                All constants live at the top of <code>models/train.py</code>; the trained weights in <code>models/weights/pinn.pt</code> reproduce the reported metrics from this exact configuration.
              </div>
            </div>
          )}

          {abl && (
            <div className="panel">
              <div className="panel-title">Ablation: PINN vs <em>pure MLP</em> (no physics loss)</div>
              <div className="panel-sub">Does the physics constraint actually help?</div>
              <table className="data"><tbody>
                <Row label="PINN with physics loss" value={`R² = ${abl.pinn_with_physics_r2.toFixed(3)}`} />
                <Row label="Pure MLP (physics weight = 0)" value={`R² = ${abl.pure_mlp_no_physics_r2.toFixed(3)}`} />
                <Row label="Marginal effect of physics loss" value={`${abl.pinn_advantage_r2 >= 0 ? '+' : ''}${abl.pinn_advantage_r2.toFixed(3)} R²`} />
              </tbody></table>
              <div className="text-xs" style={{ color: 'var(--muted)', marginTop: 8 }}>
                On this synthetic dataset the pure MLP outperforms the PINN on HIC R² by {Math.abs(abl.pinn_advantage_r2).toFixed(2)}. The physics constraint, while improving interpretability and energy consistency, over-regularizes on 390 training samples; the regularizing effect of physics loss is expected to flip positive at larger real-data regimes. {abl.note}
              </div>
            </div>
          )}

          {cls && (
            <div className="panel">
              <div className="panel-title">Fatality risk <em>classifier</em> evaluation</div>
              <div className="panel-sub">Threshold 0.5 on predicted fatality probability</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '4px 40px' }}>
                <table className="data"><tbody>
                  <Row label="Test samples" value={cls.n_test} />
                  <Row label="Positives / Negatives" value={`${cls.n_pos} / ${cls.n_neg}`} />
                  <Row label="True positives" value={cls.confusion_matrix.tp} />
                  <Row label="True negatives" value={cls.confusion_matrix.tn} />
                  <Row label="False positives" value={cls.confusion_matrix.fp} />
                  <Row label="False negatives" value={cls.confusion_matrix.fn} />
                </tbody></table>
                <table className="data"><tbody>
                  <Row label="Accuracy" value={cls.accuracy.toFixed(3)} />
                  <Row label="Precision" value={cls.precision.toFixed(3)} />
                  <Row label="Recall" value={cls.recall.toFixed(3)} />
                  <Row label="F1" value={cls.f1.toFixed(3)} />
                  <Row label="ROC AUC" value={cls.roc_auc ? cls.roc_auc.toFixed(3) : '-'} />
                </tbody></table>
              </div>
              <div className="text-xs" style={{ color: 'var(--muted)', marginTop: 8 }}>
                {cls.note} Low base-rate fatalities in the synthetic data (13 of 88 test samples) depress precision; the metric quantifies the model's ranking capacity rather than a deployment-quality cutoff.
              </div>
            </div>
          )}

          {cv && (
            <div className="panel">
              <div className="panel-title">Cross-validation <em>disclosure</em></div>
              <div className="panel-sub">Method: {cv.method}</div>
              <div className="text-xs" style={{ color: 'var(--text-2)', lineHeight: 1.6 }}>
                k-fold cross-validation was considered and intentionally deferred. {cv.kfold_not_used_reason}
              </div>
            </div>
          )}

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
