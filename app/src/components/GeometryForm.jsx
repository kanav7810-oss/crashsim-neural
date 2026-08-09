import { FIELD_DEFS, CLASSES, TEST_TYPES, YEARS } from '../geometry'

const stepPrecision = s => {
  const t = String(s).split('.')
  return t.length === 1 ? 0 : t[1].length
}

export default function GeometryForm({ value, onChange, compact = false }) {
  const set = (key, v) => onChange({ ...value, [key]: v })

  return (
    <div className="geom-form" data-testid="geometry-form">
      <div style={{
        display: 'grid',
        gridTemplateColumns: compact ? '1fr' : '1fr 1fr',
        gap: '12px 16px'
      }}>
        {FIELD_DEFS.map(f => (
          <label key={f.key} style={{ fontSize: 13, color: 'var(--text-2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 2 }}>
              <span>{f.label}</span>
              <span className="mono" style={{ fontSize: 12, color: 'var(--text)' }}>{value[f.key]}{f.unit}</span>
            </div>
            <input type="range" data-testid={`range-${f.key}`} min={f.min} max={f.max} step={f.step}
              value={value[f.key]}
              onChange={e => set(f.key, parseFloat(parseFloat(e.target.value).toFixed(stepPrecision(f.step))))}
              style={{ width: '100%' }} />
          </label>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : '1fr 1fr', gap: 10, marginTop: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-2)' }}>
          <div style={{ marginBottom: 4 }}>Vehicle class</div>
          <select value={value.vehicle_class} data-testid="select-class"
            onChange={e => set('vehicle_class', e.target.value)} style={{ width: '100%' }}>
            {CLASSES.map(c => <option key={c} value={c}>{c.toUpperCase()}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 13, color: 'var(--text-2)' }}>
          <div style={{ marginBottom: 4 }}>Test type</div>
          <select value={value.test_type} data-testid="select-test"
            onChange={e => set('test_type', e.target.value)} style={{ width: '100%' }}>
            {TEST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 13, color: 'var(--text-2)' }}>
          <div style={{ marginBottom: 4 }}>Model year</div>
          <select value={value.year} data-testid="select-year"
            onChange={e => set('year', parseInt(e.target.value))} style={{ width: '100%' }}>
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>
      </div>
    </div>
  )
}
