import { C } from '../theme'

function zoneColor(intrusionM) {
  if (intrusionM < 0.08) return C.ok
  if (intrusionM < 0.16) return C.warn
  if (intrusionM < 0.26) return C.amber
  return C.danger
}

export default function IntrusionDiagram({ intrusion, profile }) {
  const prof = profile && profile.length ? profile : Array(40).fill(0)
  const maxAmp = Math.max(...prof.map(Math.abs), 1e-6)
  const scale = 34 / maxAmp

  const pts = prof
    .map((v, i) => [100 + v * scale, 34 + (i / (prof.length - 1)) * 150])
  const poly = pts.map(([x, y]) => `${x},${y}`).join(' ')

  const segColor = (i) => {
    const r = Math.abs(prof[i]) / maxAmp
    return zoneColor(intrusion * r * 0.9 + 0.03)
  }

  return (
    <div data-testid="intrusion-diagram" className="intrusion-scene">
      <svg viewBox="0 0 340 200" style={{ width: '100%', display: 'block' }}>
        <defs>
          <linearGradient id="pillarGlass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="oklch(0.925 0.008 60 / 0.10)" />
            <stop offset="1" stopColor="oklch(0.925 0.008 60 / 0.02)" />
          </linearGradient>
          <linearGradient id="intrusionSheen" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="oklch(1 1 0 / 0)" />
            <stop offset="0.5" stopColor="oklch(1 1 0 / 0.08)" />
            <stop offset="1" stopColor="oklch(1 1 0 / 0)" />
          </linearGradient>
        </defs>

        <text x="16" y="20" fill={C.text} fontSize="12" fontWeight="600">Pillar buckling / compartment intrusion</text>

        <rect x="90" y="28" width="170" height="162" fill="url(#intrusionSheen)" className="intrusion-sheen" />

        <line x1="100" y1="34" x2="100" y2="184" stroke={C.border} strokeWidth="3" />
        <text x="92" y="196" fill={C.muted} fontSize="10">undeformed</text>

        <polyline points={poly} fill="url(#pillarGlass)" stroke={C.muted} strokeWidth="1" strokeDasharray="3 3" />
        {pts.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="2.6" fill={segColor(i)} />
        ))}
        <text x="150" y="30" fill={C.text2} fontSize="11">intrusion {intrusion.toFixed(3)} m</text>

        {[['< 0.08 m', C.ok], ['0.08-0.16', C.warn], ['0.16-0.26', C.amber], ['> 0.26 m', C.danger]]
          .map(([label, color], i) => (
            <g key={label} transform={`translate(210, ${40 + i * 18})`}>
              <rect x="0" y="-8" width="12" height="12" rx="2" fill={color} />
              <text x="18" y="1" fill={C.text2} fontSize="10">{label}</text>
            </g>
          ))}
      </svg>

      <style>{`
        .intrusion-sheen { transform-origin: center; animation: intrusionSheenSweep 5s cubic-bezier(.45,0,.25,1) infinite; }
        @keyframes intrusionSheenSweep {
          0%, 70% { transform: translateX(-80px); opacity: 0; }
          78% { opacity: 1; }
          100% { transform: translateX(90px); opacity: 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .intrusion-sheen { animation: none !important; }
        }
      `}</style>
    </div>
  )
}
