import { useEffect, useRef, useState } from 'react'
import { C } from '../theme'
import AnimatedNumber from './AnimatedNumber'
import Tilt from './Tilt'

function severityColor(ratio) {
  if (ratio < 0.25) return C.ok
  if (ratio < 0.45) return C.warn
  return C.danger
}

export default function CrumpleAnimation({ crush, peakG, hic, runKey }) {
  const [progress, setProgress] = useState(0)
  const raf = useRef(null)

  useEffect(() => {
    setProgress(0)
    const start = performance.now()
    const DURATION = 1800
    const step = (now) => {
      const t = Math.min((now - start) / DURATION, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setProgress(eased)
      if (t < 1) raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [runKey, crush])

  const maxCrushPx = 95
  const crushPx = Math.min(crush, 0.55) / 0.55 * maxCrushPx * progress
  const bumperX = 545 - crushPx
  const ratio = Math.min(crush / 0.55, 1.2)
  const color = severityColor(ratio)
  const barW = Math.min((peakG || 0) / 90, 1) * 100

  return (
    <div data-testid="crumple-animation" className="crumple-scene">
      <div style={{ perspective: 1100 }}>
        <Tilt max={4} className="crumple-tilt">
          <div key={runKey} className="crumple-dolly">
            <svg viewBox="0 0 620 210" style={{ width: '100%', display: 'block' }}>
              <defs>
                <linearGradient id="bodyGlass" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="oklch(0.63 0.11 62 / 0.30)" />
                  <stop offset="0.55" stopColor="oklch(0.63 0.11 62 / 0.06)" />
                  <stop offset="1" stopColor="oklch(0 0 0 / 0.35)" />
                </linearGradient>
                <linearGradient id="cabinGlass" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="oklch(0.925 0.008 60 / 0.12)" />
                  <stop offset="1" stopColor="oklch(0.925 0.008 60 / 0.02)" />
                </linearGradient>
                <linearGradient id="sheenGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0" stopColor="oklch(1 1 0 / 0)" />
                  <stop offset="0.5" stopColor="oklch(1 1 0 / 0.10)" />
                  <stop offset="1" stopColor="oklch(1 1 0 / 0)" />
                </linearGradient>
                <clipPath id="carClip">
                  <rect x="250" y="44" width="330" height="145" />
                </clipPath>
              </defs>

              <line x1="0" y1="182" x2="620" y2="182" stroke={C.border} strokeWidth="2" />
              <rect x="250" y="186" width="270" height="6" fill="url(#sheenGrad)" opacity="0.5" />

              <rect x="560" y="40" width="30" height="142" fill={C.surface2} stroke={C.border} rx="3" />
              <text x="568" y="32" fill={C.muted} fontSize="11" textAnchor="middle">BARRIER</text>

              <g className="crumple-car">
                <ellipse cx={bumperX + 40} cy="128" rx="86" ry="52" fill={color}
                  opacity={0.10 + 0.16 * ratio} className="crumple-glow" />

                <rect x="250" y="88" width="185" height="70" rx="6" fill="url(#bodyGlass)" stroke={C.accent} strokeWidth="1.5" />
                <path d="M250 88 L285 52 L345 52 L435 88 Z" fill="url(#cabinGlass)" stroke={C.accent} strokeWidth="1.5" />
                <rect x="300" y="62" width="48" height="26" fill={C.secondary} opacity="0.75" rx="2" className="cabin-window" />

                <polygon points={`${435},88 ${435},158 ${bumperX},158 ${bumperX + 12},120 ${bumperX + 26},88`}
                  fill={color} fillOpacity="0.45" stroke={color} strokeWidth="1.5" />
                <path d={`M ${435} 104 L ${bumperX + 20} 104 M ${435} 122 L ${bumperX + 12} 122 M ${435} 140 L ${bumperX + 18} 140`}
                  stroke={color} strokeWidth="1.5" strokeDasharray="5 4" />

                <circle cx="300" cy="176" r="17" fill={C.bg} stroke={C.muted} strokeWidth="3" />
                <circle cx="300" cy="176" r="6" fill={C.text2} />
                <circle cx="455" cy="176" r="17" fill={C.bg} stroke={C.muted} strokeWidth="3" />
                <circle cx="455" cy="176" r="6" fill={C.text2} />

                <circle cx="330" cy="122" r="11" fill={C.warn} stroke={C.warn} strokeWidth="1.5" />
                <text x="438" y="70" fill={C.text} fontSize="12" fontWeight="600">Crush {crush.toFixed(2)} m</text>

                <rect x="0" y="30" width="620" height="165" fill="url(#sheenGrad)" clipPath="url(#carClip)" className="sheen" />
              </g>
            </svg>
          </div>
        </Tilt>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 12 }}>
        <div>
          <div className="micro">Peak head deceleration</div>
          <div style={{ height: 8, background: C.surface2, borderRadius: 4, margin: '6px 0 4px' }}>
            <div style={{ width: `${barW}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 0.4s cubic-bezier(.16,1,.3,1)' }} />
          </div>
          <div className="mono" style={{ fontSize: 12, color: 'var(--text-2)' }}>
            <AnimatedNumber value={peakG || 0} format={v => v.toFixed(1)} /> g
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="micro">HIC<sub>36</sub></div>
          <div className="num" style={{ fontSize: 18, fontWeight: 600, color, marginTop: 4 }}>
            <AnimatedNumber value={hic || 0} format={v => v.toFixed(0)} />
          </div>
        </div>
      </div>

      <style>{`
        .crumple-tilt { transform-style: preserve-3d; }
        .crumple-dolly { animation: crumpleDolly 900ms cubic-bezier(.16,1,.3,1) both; }
        @keyframes crumpleDolly { from { transform: scale(1.045); } to { transform: scale(1); } }
        .crumple-glow { transition: opacity 400ms cubic-bezier(.16,1,.3,1); }
        .sheen { transform-origin: center; animation: sheenSweep 3.6s cubic-bezier(.45,0,.25,1) infinite; }
        @keyframes sheenSweep {
          0%, 55% { transform: translateX(-360px); opacity: 0; }
          62% { opacity: 1; }
          100% { transform: translateX(420px); opacity: 0; }
        }
        .cabin-window { animation: windowGlint 4s ease-in-out infinite; }
        @keyframes windowGlint {
          0%, 60% { filter: none; }
          65% { filter: brightness(1.7); }
          75% { filter: none; }
        }
        @media (prefers-reduced-motion: reduce) {
          .sheen, .crumple-dolly, .cabin-window { animation: none !important; }
        }
      `}</style>
    </div>
  )
}
