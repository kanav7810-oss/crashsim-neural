import { useState, useCallback } from 'react'
import { AnimatePresence } from 'framer-motion'
import LoadingScreen from './LoadingScreen'
import Overview from './tabs/Overview'
import ScenarioBuilder from './tabs/ScenarioBuilder'
import GeometryOptimizer from './tabs/GeometryOptimizer'
import TrainingMonitor from './tabs/TrainingMonitor'
import DatasetExplorer from './tabs/DatasetExplorer'
import Comparison from './tabs/Comparison'
import ChartsGallery from './tabs/ChartsGallery'
import Research from './tabs/Research'
import { Gauge, FlaskConical, Sliders, Activity, Database, GitCompare, BarChart3, FileText } from 'lucide-react'

const TABS = [
  { id: 'overview', label: 'Overview', icon: Gauge },
  { id: 'builder', label: 'Scenario Builder', title: <>Scenario <em>Builder</em></>, icon: FlaskConical },
  { id: 'geometry', label: 'Geometry Optimizer', title: <>Geometry <em>Optimizer</em></>, icon: Sliders },
  { id: 'training', label: 'Training Monitor', title: <>Training <em>Monitor</em></>, icon: Activity },
  { id: 'dataset', label: 'Dataset Explorer', title: <>Dataset <em>Explorer</em></>, icon: Database },
  { id: 'compare', label: 'Comparison', icon: GitCompare },
  { id: 'charts', label: 'Statistical Charts', title: <>Statistical <em>Charts</em></>, icon: BarChart3 },
  { id: 'research', label: 'Research & Export', title: <>Research &amp; <em>Export</em></>, icon: FileText }
]

export default function App() {
  const [loaded, setLoaded] = useState(false)
  const [tab, setTab] = useState('overview')
  const onLoadComplete = useCallback(() => setLoaded(true), [])
  const render = () => {
    switch (tab) {
      case 'overview': return <Overview />
      case 'builder': return <ScenarioBuilder />
      case 'geometry': return <GeometryOptimizer />
      case 'training': return <TrainingMonitor />
      case 'dataset': return <DatasetExplorer />
      case 'compare': return <Comparison />
      case 'charts': return <ChartsGallery />
      case 'research': return <Research />
      default: return null
    }
  }

  const current = TABS.find(t => t.id === tab)

  return (
    <>
      <AnimatePresence>
        {!loaded && <LoadingScreen onComplete={onLoadComplete} />}
      </AnimatePresence>
      <div className="app-frame">
      <div className="orbs" aria-hidden="true">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
        <div className="orb orb-4" />
      </div>

      <aside className="sidebar">
        <div className="brand">
          <img src="/favicon.svg" alt="" className="brand-mark" style={{ width: 28, height: 28, borderRadius: 7 }} />
          <div>
            <div className="brand-name">CRASHSIM</div>
            <div className="brand-sub">NEURAL</div>
          </div>
        </div>
        <nav className="nav" data-testid="side-nav">
          {TABS.map(t => {
            const Icon = t.icon
            const active = tab === t.id
            return (
              <button key={t.id} data-testid={`tab-${t.id}`} onClick={() => setTab(t.id)}
                className={`nav-item ${active ? 'active' : ''}`}>
                <Icon size={16} strokeWidth={active ? 2 : 1.75} />
                <span>{t.label}</span>
              </button>
            )
          })}
        </nav>
        <div className="sidebar-foot mono">research instrument</div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div>
            <div className="page-title">{current.title || current.label}</div>
          </div>
          <div className="topbar-status mono">
            <span className="status-dot" />
            research instrument
          </div>
        </header>
        <main key={tab} className="content tab-enter">
          {render()}
        </main>
        <footer className="app-footer">
          <div className="app-footer-main">
            Physics-informed neural network trained on synthetic NHTSA-schema crashworthiness records, benchmarked against a linear FEA baseline.
            Research use only, not a substitute for regulatory testing.
          </div>
          <div className="app-footer-legal mono">
            <span>© 2026 CRASHSIM-NEURAL</span>
            <span className="sep">·</span>
            <span>All rights reserved</span>
            <span className="sep">·</span>
            <span>Terms of Service</span>
            <span className="sep">·</span>
            <span>Privacy Policy</span>
            <span className="sep">·</span>
            <span>Predictions do not constitute engineering certification or legal advice</span>
          </div>
        </footer>
      </div>

      <style>{`
        .app-frame { display: flex; min-height: 100vh; position: relative; z-index: 1; }

        .orbs { position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }
        .orb { position: absolute; border-radius: 50%; filter: blur(90px); will-change: transform; }
        .orb-1 { width: 560px; height: 560px; top: -180px; right: -120px; opacity: 0.20;
          background: radial-gradient(circle, oklch(0.62 0.12 60 / 0.5), transparent 70%);
          animation: orbDriftA 26s ease-in-out infinite alternate; }
        .orb-2 { width: 480px; height: 480px; bottom: -200px; left: -140px; opacity: 0.14;
          background: radial-gradient(circle, oklch(0.58 0.12 45 / 0.5), transparent 70%);
          animation: orbDriftB 32s ease-in-out infinite alternate; }
        .orb-3 { width: 380px; height: 380px; top: 42%; left: 42%; opacity: 0.10;
          background: radial-gradient(circle, oklch(0.68 0.09 145 / 0.5), transparent 70%);
          animation: orbDriftC 38s ease-in-out infinite alternate; }
        .orb-4 { width: 300px; height: 300px; top: 16%; left: 12%; opacity: 0.08;
          background: radial-gradient(circle, oklch(0.78 0.09 80 / 0.5), transparent 70%);
          animation: orbDriftA 44s ease-in-out infinite alternate-reverse; }
        @keyframes orbDriftA { from { transform: translate3d(0, 0, 0) scale(1); } to { transform: translate3d(-70px, 60px, 0) scale(1.12); } }
        @keyframes orbDriftB { from { transform: translate3d(0, 0, 0) scale(1); } to { transform: translate3d(90px, -50px, 0) scale(1.08); } }
        @keyframes orbDriftC { from { transform: translate3d(0, 0, 0) scale(1); } to { transform: translate3d(-40px, -70px, 0) scale(1.15); } }

        .sidebar {
          width: 220px; flex-shrink: 0; border-right: 1px solid var(--border);
          display: flex; flex-direction: column; padding: 16px 10px;
          background: oklch(0.12 0.006 60 / 0.55);
          backdrop-filter: blur(24px) saturate(1.35);
          -webkit-backdrop-filter: blur(24px) saturate(1.35);
          position: sticky; top: 0; height: 100vh; z-index: 2;
        }
        .brand { display: flex; align-items: center; gap: 10px; padding: 2px 8px 18px; }
        .brand-mark {
          background: linear-gradient(135deg, var(--accent-fill), var(--accent));
          box-shadow: 0 0 18px -4px var(--accent);
        }
        .brand-name { font-size: 12px; font-weight: 700; letter-spacing: 0.04em; }
        .brand-sub { font-size: 10px; color: var(--muted); letter-spacing: 0.22em; font-family: var(--mono); }

        .nav { display: flex; flex-direction: column; gap: 1px; flex: 1; }
        .nav-item {
          position: relative; display: flex; align-items: center; gap: 9px; cursor: pointer;
          background: transparent; border: none; text-align: left;
          color: var(--text-2); font-size: 13px; font-weight: 500;
          padding: 7px 10px; border-radius: var(--radius-s);
          transition: background-color 160ms cubic-bezier(.16,1,.3,1), color 160ms cubic-bezier(.16,1,.3,1), transform 160ms cubic-bezier(.16,1,.3,1);
        }
        .nav-item:hover { background: oklch(0.17 0.01 60 / 0.7); color: var(--text); }
        .nav-item:active { transform: scale(0.98); }
        .nav-item.active { background: var(--accent-bg); color: var(--accent); font-weight: 600; }
        .nav-item.active::before {
          content: ''; position: absolute; left: 0; top: 7px; bottom: 7px; width: 2px;
          border-radius: 1px; background: var(--accent);
          animation: navSlide 260ms cubic-bezier(.16,1,.3,1) both;
        }
        @keyframes navSlide { from { transform: scaleY(0); opacity: 0; } to { transform: scaleY(1); opacity: 1; } }
        .sidebar-foot { padding: 12px 10px 2px; border-top: 1px solid var(--border); font-size: 10px; color: var(--muted); }

        .app-main { flex: 1; min-width: 0; display: flex; flex-direction: column; position: relative; z-index: 1; }

        .topbar {
          display: flex; align-items: center; justify-content: space-between;
          padding: 18px 32px 16px; border-bottom: 1px solid var(--border);
          background: oklch(0.12 0.006 60 / 0.45);
          backdrop-filter: blur(20px) saturate(1.3);
          -webkit-backdrop-filter: blur(20px) saturate(1.3);
          position: sticky; top: 0; z-index: 3;
        }
        .page-title { font-family: var(--display); font-size: 22px; font-weight: 600; letter-spacing: -0.01em; }
        .page-title em, .panel-title em { font-style: italic; }
        .topbar-status { display: flex; align-items: center; gap: 7px; font-size: 11px; color: var(--muted); }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 0 0 oklch(0.72 0.16 152 / 0.6); animation: pulse 2.8s ease-out infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 oklch(0.72 0.16 152 / 0.55); } 70% { box-shadow: 0 0 0 7px oklch(0.72 0.16 152 / 0); } 100% { box-shadow: 0 0 0 0 oklch(0.72 0.16 152 / 0); } }

        .content { flex: 1; padding: 28px 32px 40px; width: 100%; max-width: 1120px; position: relative; z-index: 1; }
        .tab-enter { animation: tabIn 300ms cubic-bezier(.16,1,.3,1) both; }
        @keyframes tabIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }

        .content > * { animation: rise 360ms cubic-bezier(.16,1,.3,1) both; }
        .content > *:nth-child(2) { animation-delay: 45ms; }
        .content > *:nth-child(3) { animation-delay: 90ms; }
        .content > *:nth-child(4) { animation-delay: 135ms; }
        .content > *:nth-child(5) { animation-delay: 180ms; }
        .content > *:nth-child(6) { animation-delay: 225ms; }
        @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

        .app-footer {
          border-top: 1px solid var(--border); padding: 14px 32px;
          font-size: 11px; color: var(--muted); letter-spacing: -0.005em;
          position: relative; z-index: 1;
          display: flex; flex-direction: column; gap: 7px;
        }
        .app-footer-main { line-height: 1.5; }
        .app-footer-legal {
          display: flex; flex-wrap: wrap; gap: 4px 10px;
          font-size: 10px; color: var(--muted); letter-spacing: 0.01em;
        }
        .app-footer-legal .sep { opacity: 0.45; }

        .panel {
          position: relative; overflow: hidden;
          background:
            linear-gradient(180deg, oklch(0.925 0.008 60 / 0.035), oklch(0.925 0.008 60 / 0.015)),
            oklch(0.155 0.009 60 / 0.62);
          backdrop-filter: blur(22px) saturate(1.4);
          -webkit-backdrop-filter: blur(22px) saturate(1.4);
          border: 1px solid var(--border);
          border-radius: var(--radius); padding: 20px;
          box-shadow: inset 0 1px 0 oklch(1 0 0 / 0.05), 0 14px 40px -18px oklch(0 0 0 / 0.7);
          transition: border-color 200ms cubic-bezier(.16,1,.3,1), box-shadow 200ms cubic-bezier(.16,1,.3,1);
        }
        .panel:hover { border-color: var(--border-s); box-shadow: inset 0 1px 0 oklch(1 0 0 / 0.06), 0 16px 48px -18px oklch(0 0 0 / 0.75), 0 0 0 1px oklch(0.63 0.11 62 / 0.06); }
        .panel::after {
          content: ''; position: absolute; inset: 0 0 auto 0; height: 1px;
          background: linear-gradient(90deg, transparent, oklch(1 1 0 / 0.05) 30%, oklch(1 1 0 / 0.05) 70%, transparent);
          pointer-events: none;
        }
        .panel-title { font-family: var(--display); font-size: 16px; font-weight: 600; letter-spacing: -0.01em; margin-bottom: 4px; }
        .panel-sub { font-size: 12px; color: var(--muted); margin-bottom: 14px; letter-spacing: -0.005em; }
        .hint { font-size: 12px; color: var(--muted); line-height: 1.5; letter-spacing: -0.005em; }

        .num { font-family: var(--display); font-weight: 600; font-variant-numeric: normal; letter-spacing: -0.01em; }

        .tilt { transform-style: preserve-3d; }

        .btn {
          cursor: pointer; border-radius: var(--radius-s); height: 32px;
          padding: 0 14px; font-size: 13px; font-weight: 500; letter-spacing: -0.005em;
          display: inline-flex; align-items: center; gap: 8px;
          transition: background-color 180ms cubic-bezier(.16,1,.3,1), color 180ms cubic-bezier(.16,1,.3,1), border-color 180ms cubic-bezier(.16,1,.3,1), transform 120ms cubic-bezier(.16,1,.3,1), box-shadow 180ms cubic-bezier(.16,1,.3,1);
        }
        .btn:active { transform: scale(0.97) translateY(1px); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-primary {
          background: linear-gradient(180deg, var(--accent), var(--accent-fill));
          color: oklch(0.97 0.004 60); border: 1px solid var(--accent);
          box-shadow: inset 0 1px 0 oklch(1 1 0 / 0.18), 0 4px 16px -6px oklch(0.5 0.1 58 / 0.7);
        }
        .btn-primary:hover:not(:disabled) { background: linear-gradient(180deg, var(--accent-h), var(--accent)); box-shadow: inset 0 1px 0 oklch(1 1 0 / 0.22), 0 6px 22px -6px oklch(0.5 0.1 58 / 0.85); }
        .btn-ghost { background: oklch(0.925 0.008 60 / 0.03); color: var(--text-2); border: 1px solid var(--border-s); }
        .btn-ghost:hover:not(:disabled) { background: oklch(0.925 0.008 60 / 0.06); color: var(--text); border-color: var(--border-s); }

        input[type=range] {
          appearance: none; width: 100%; height: 4px; border-radius: 2px;
          background: var(--border-s); cursor: pointer; margin: 8px 0;
          transition: height 160ms ease-out;
        }
        input[type=range]::-webkit-slider-thumb {
          appearance: none; width: 13px; height: 13px; border-radius: 50%;
          background: radial-gradient(circle at 35% 30%, var(--accent-h), var(--accent-fill));
          border: 2px solid var(--bg);
          box-shadow: 0 0 0 1px var(--accent), 0 0 12px -2px var(--accent);
          transition: transform 120ms cubic-bezier(.16,1,.3,1), box-shadow 120ms ease-out;
        }
        input[type=range]::-webkit-slider-thumb:hover { transform: scale(1.22); box-shadow: 0 0 0 3px var(--accent-bg), 0 0 0 1px var(--accent), 0 0 16px -2px var(--accent); }
        input[type=range]::-webkit-slider-thumb:active { transform: scale(1.3); }
        input[type=range]::-moz-range-thumb {
          width: 13px; height: 13px; border-radius: 50%;
          background: var(--accent); border: 2px solid var(--bg);
          box-shadow: 0 0 0 1px var(--accent), 0 0 12px -2px var(--accent);
        }

        select, input[type=number], input[type=text] {
          background: oklch(0.17 0.01 60 / 0.8); color: var(--text);
          border: 1px solid var(--border-s); border-radius: var(--radius-s);
          padding: 0 10px; height: 32px; font-size: 13px;
          transition: border-color 160ms ease-out, box-shadow 160ms ease-out;
        }
        select:hover, input:hover { border-color: oklch(0.33 0.016 60 / 1); }
        select:focus, input:focus { border-color: var(--accent); outline: none; box-shadow: 0 0 0 3px var(--accent-bg); }
        select { padding-right: 28px; }

        .tag {
          display: inline-block; background: oklch(0.17 0.01 60 / 0.8); color: var(--text-2);
          border: 1px solid var(--border); border-radius: var(--radius-s);
          padding: 1px 8px; font-size: 11px; font-family: var(--mono); letter-spacing: 0.01em;
        }
        .micro { font-size: 11px; color: var(--muted); letter-spacing: 0.06em; text-transform: uppercase; font-weight: 500; }

        table.data { width: 100%; border-collapse: collapse; font-size: 13px; }
        table.data th {
          text-align: left; color: var(--muted); font-weight: 600; font-size: 12px;
          padding: 8px 10px; border-bottom: 1px solid var(--border);
        }
        table.data td { padding: 8px 10px; border-bottom: 1px solid var(--border); color: var(--text-2); }
        table.data tr { transition: background-color 140ms ease-out; }
        table.data tr:hover td { background: oklch(0.925 0.008 60 / 0.03); }

        .mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }

        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
          .orb { animation: none !important; }
        }
      `}</style>
    </div>
    </>
  )
}
