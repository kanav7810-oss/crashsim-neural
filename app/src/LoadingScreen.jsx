import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import api from './api'

const PHASE_DURATION = 5000
const MIN_VISIBLE = 8000

const steps = [
  { label: 'Loading dataset schema', target: 12 },
  { label: 'Fetching model metrics', target: 28 },
  { label: 'Preparing visualizations', target: 45 },
  { label: 'Calibrating charts', target: 62 },
  { label: 'Initializing research data', target: 78 },
  { label: 'Syncing physics parameters', target: 90 },
  { label: 'Finalizing interface', target: 95 },
]

export default function LoadingScreen({ onComplete }) {
  const [progress, setProgress] = useState(0)
  const [stepIdx, setStepIdx] = useState(0)
  const [ready, setReady] = useState(false)
  const [fade, setFade] = useState(false)

  useEffect(() => {
    const start = Date.now()
    let raf

    const tick = () => {
      const elapsed = Date.now() - start
      const t = Math.min(elapsed / PHASE_DURATION, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      const base = eased * 95

      const currentStep = steps.reduce((acc, s, i) => (base >= s.target ? i : acc), 0)
      setStepIdx(currentStep)
      setProgress(Math.min(base, 95))

      if (t < 1) {
        raf = requestAnimationFrame(tick)
      }
    }
    raf = requestAnimationFrame(tick)

    const criticalEndpoints = [
      api.get('/api/research/summary'),
      api.get('/api/charts/historical_trend'),
      api.get('/api/charts/class_comparison'),
      api.get('/api/dataset/summary'),
    ]

    Promise.allSettled(criticalEndpoints).then(() => {
      const remaining = MIN_VISIBLE - (Date.now() - start)
      setTimeout(() => setReady(true), Math.max(0, remaining))
    }).catch(() => {
      setTimeout(() => setReady(true), MIN_VISIBLE - (Date.now() - start))
    })

    return () => cancelAnimationFrame(raf)
  }, [])

  useEffect(() => {
    if (ready && progress >= 90) {
      setProgress(100)
      const t = setTimeout(() => setFade(true), 400)
      const t2 = setTimeout(() => onComplete(), 900)
      return () => { clearTimeout(t); clearTimeout(t2) }
    }
  }, [ready, progress, onComplete])

  const stepLabel = steps[stepIdx]?.label || 'Finalizing interface'

  return (
    <AnimatePresence>
      {!fade && (
        <motion.div
          className="loading-screen"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            background: 'var(--bg)',
          }}
        >
          <div className="orbs" aria-hidden="true">
            <div className="orb orb-1" />
            <div className="orb orb-2" />
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            style={{ position: 'relative', zIndex: 1, textAlign: 'center' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginBottom: 6 }}>
              <img
                src="/favicon.svg" alt=""
                style={{ width: 32, height: 32, borderRadius: 8,
                  background: 'linear-gradient(135deg, var(--accent-fill), var(--accent))',
                  boxShadow: '0 0 24px -4px var(--accent)',
                }}
              />
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '0.04em' }}>CRASHSIM</div>
                <div style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '0.22em', fontFamily: 'var(--mono)' }}>NEURAL</div>
              </div>
            </div>

            <motion.div
              style={{
                fontFamily: 'var(--display)',
                fontSize: 36,
                fontWeight: 600,
                letterSpacing: '-0.02em',
                marginTop: 24,
                color: 'var(--text)',
              }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              Crash <em style={{ fontStyle: 'italic', color: 'var(--accent)' }}>premium</em>
            </motion.div>

            <motion.div
              style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6, letterSpacing: '-0.005em' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.7 }}
            >
              Physics-informed crashworthiness intelligence
            </motion.div>
          </motion.div>

          <motion.div
            style={{ position: 'relative', zIndex: 1, width: 280, marginTop: 48 }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.9 }}
          >
            <div style={{
              height: 3, borderRadius: 2,
              background: 'var(--border-s)',
              overflow: 'hidden',
            }}>
              <motion.div
                style={{
                  height: '100%', borderRadius: 2,
                  background: 'linear-gradient(90deg, var(--accent-fill), var(--accent))',
                  boxShadow: '0 0 12px -2px var(--accent)',
                }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
              />
            </div>

            <div style={{
              display: 'flex', justifyContent: 'space-between',
              marginTop: 10, fontSize: 10, fontFamily: 'var(--mono)',
              color: 'var(--muted)', letterSpacing: '0.04em',
            }}>
              <span>{stepLabel}</span>
              <span>{Math.round(progress)}%</span>
            </div>
          </motion.div>

          <style>{`
            .loading-screen .orbs { position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }
            .loading-screen .orb { position: absolute; border-radius: 50%; filter: blur(90px); will-change: transform; }
            .loading-screen .orb-1 { width: 500px; height: 500px; top: -160px; right: -100px; opacity: 0.15;
              background: radial-gradient(circle, oklch(0.62 0.12 60 / 0.5), transparent 70%);
              animation: loadOrbA 20s ease-in-out infinite alternate; }
            .loading-screen .orb-2 { width: 420px; height: 420px; bottom: -180px; left: -120px; opacity: 0.10;
              background: radial-gradient(circle, oklch(0.58 0.12 45 / 0.5), transparent 70%);
              animation: loadOrbB 26s ease-in-out infinite alternate; }
            @keyframes loadOrbA { from { transform: translate3d(0, 0, 0) scale(1); } to { transform: translate3d(-50px, 40px, 0) scale(1.1); } }
            @keyframes loadOrbB { from { transform: translate3d(0, 0, 0) scale(1); } to { transform: translate3d(60px, -40px, 0) scale(1.06); } }
          `}</style>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
