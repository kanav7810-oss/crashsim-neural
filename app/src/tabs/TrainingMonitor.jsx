import { useEffect, useRef, useState } from 'react'
import { trainingStream } from '../api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { Play, Square } from 'lucide-react'
import SpecularCTA from '../components/SpecularCTA'
import { C, TOOLTIP } from '../theme'

export default function TrainingMonitor() {
  const [data, setData] = useState([])
  const [running, setRunning] = useState(false)
  const closeRef = useRef(null)
  const [done, setDone] = useState(false)
  const [feaLine, setFeaLine] = useState(null)

  const start = () => {
    setData([])
    setDone(false)
    setFeaLine(null)
    setRunning(true)
    closeRef.current = trainingStream((ev) => {
      if (ev.done) {
        setDone(true)
        setRunning(false)
        return
      }
      setData(d => {
        const next = [...d, {
          epoch: ev.epoch, trainLoss: +ev.train_loss.toFixed(4), valLoss: +ev.val_loss.toFixed(4),
          trainRMSE: +ev.train_rmse.toFixed(1), valRMSE: +ev.val_rmse.toFixed(1)
        }]
        if (!feaLine && ev.fea_val_rmse) setFeaLine(ev.fea_val_rmse)
        return next
      })
    })
  }

  const stop = () => {
    if (closeRef.current) closeRef.current()
    closeRef.current = null
    setRunning(false)
  }

  useEffect(() => () => { if (closeRef.current) closeRef.current() }, [])

  const lossData = data.map(d => ({ epoch: d.epoch, 'Training loss': d.trainLoss, 'Validation loss': d.valLoss }))
  const rmseData = data.map(d => ({
    epoch: d.epoch, 'PINN train RMSE': d.trainRMSE, 'PINN val RMSE': d.valRMSE,
    'FEA baseline': feaLine
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        {!running ? (
          <SpecularCTA data-testid="btn-start-training" onClick={start}>
            <Play size={15} /> {done ? 'Replay training run' : 'Start training run'}
          </SpecularCTA>
        ) : (
          <button className="btn btn-ghost" data-testid="btn-stop-training" onClick={stop}>
            <Square size={15} /> Stop
          </button>
        )}
        {done && <span className="tag">training completed</span>}
        {running && <span className="tag" style={{ color: 'var(--accent)' }}>streaming epochs…</span>}
      </div>

      <div className="panel">
        <div className="panel-title">Loss curves (data + <em>physics</em>)</div>
        <div className="panel-sub">Training vs validation loss per epoch</div>
        <div style={{ height: 280 }} data-testid="loss-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={lossData}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
              <XAxis dataKey="epoch" stroke={C.muted} label={{ value: 'epoch', position: 'insideBottomRight', fill: C.muted, fontSize: 11 }} tick={{ fontSize: 11 }} />
              <YAxis stroke={C.muted} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={TOOLTIP} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="Training loss" stroke={C.accent} dot={false} strokeWidth={2} />
              <Line dataKey="Validation loss" stroke={C.secondary} dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">HIC RMSE: <em>PINN</em> vs FEA baseline</div>
        <div className="panel-sub">Root mean squared error on HIC<sub>36</sub> across epochs</div>
        <div style={{ height: 280 }} data-testid="rmse-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rmseData}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
              <XAxis dataKey="epoch" stroke={C.muted} tick={{ fontSize: 11 }} />
              <YAxis stroke={C.muted} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={TOOLTIP} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="PINN train RMSE" stroke={C.secondary} dot={false} strokeWidth={2} />
              <Line dataKey="PINN val RMSE" stroke={C.accent} dot={false} strokeWidth={2} />
              <Line dataKey="FEA baseline" stroke={C.muted} strokeDasharray="6 4" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
