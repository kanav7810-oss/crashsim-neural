import { useEffect, useState } from 'react'
import api from '../api'
import { CLASSES, TEST_TYPES } from '../geometry'
import { Search, Database } from 'lucide-react'
import { C } from '../theme'

const COLS = [
  { key: 'year', label: 'Year' }, { key: 'make', label: 'Make' }, { key: 'model', label: 'Model' },
  { key: 'vehicle_class', label: 'Class' }, { key: 'test_type', label: 'Test' },
  { key: 'velocity_kmh', label: 'km/h' }, { key: 'mass_kg', label: 'Mass kg' },
  { key: 'hic', label: <>HIC<sub>36</sub></> }, { key: 'chest_g', label: 'Chest g' },
  { key: 'intrusion_m', label: 'Intrusion m' }
]

export default function DatasetExplorer() {
  const [filters, setFilters] = useState({ vehicle_class: '', test_type: '', search: '' })
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('year')
  const [order, setOrder] = useState('desc')
  const [perPage, setPerPage] = useState(20)
  const [data, setData] = useState({ total: 0, rows: [] })
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/api/dataset', { ...filters, sort, order, page, per_page: perPage })
      .then(setData).catch(e => setErr(e.message))
  }, [filters, sort, order, page, perPage])

  const pages = Math.max(1, Math.ceil(data.total / perPage))

  const toggleSort = (k) => {
    if (sort === k) setOrder(o => (o === 'asc' ? 'desc' : 'asc'))
    else { setSort(k); setOrder('asc') }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="hint">
        {data.total} physics-validated synthetic records following the NHTSA schema.
        Real NHTSA FARS and crash-test endpoints require institutional access; instead of overstating
        claims of real data, the generator drives the physics engine with randomized geometry and
        adds measurement noise, so the synthetic dataset respects real crash mechanics.
        The 560-record size is an acknowledged limitation: results demonstrate the methodology,
        not production-ready accuracy or generalizable safety claims.
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <a className="btn btn-ghost" data-testid="btn-download-csv" href={`${api.API}/api/dataset/download`} download="crashsim_dataset.csv" style={{ textDecoration: 'none' }}>
          <Database size={14} /> Download full dataset CSV
        </a>
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <select data-testid="explorer-class" value={filters.vehicle_class}
          onChange={e => { setFilters(f => ({ ...f, vehicle_class: e.target.value })); setPage(1) }}>
          <option value="">All classes</option>
          {CLASSES.map(c => <option key={c} value={c}>{c.toUpperCase()}</option>)}
        </select>
        <select data-testid="explorer-test" value={filters.test_type}
          onChange={e => { setFilters(f => ({ ...f, test_type: e.target.value })); setPage(1) }}>
          <option value="">All test types</option>
          {TEST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 220 }}>
          <Search size={15} style={{ color: 'var(--muted)' }} />
          <input type="text" placeholder="Search make or model" data-testid="explorer-search"
            value={filters.search} style={{ width: '100%' }}
            onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1) }} />
        </div>
        <select value={perPage} onChange={e => { setPerPage(parseInt(e.target.value)); setPage(1) }}>
          {[10, 20, 50, 100].map(n => <option key={n} value={n}>{n} rows</option>)}
        </select>
        {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      </div>

      <div className="panel" style={{ overflowX: 'auto', padding: 12 }}>
        <table className="data" data-testid="dataset-table">
          <thead>
            <tr>
              {COLS.map(c => (
                <th key={c.key} style={{ cursor: 'pointer' }} data-testid={`th-${c.key}`}
                  onClick={() => toggleSort(c.key)}>
                  {c.label}{sort === c.key ? (order === 'asc' ? ' ↑' : ' ↓') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r, i) => (
              <tr key={i}>
                <td>{r.year}</td>
                <td>{r.make}</td>
                <td>{r.model}</td>
                <td><span className="tag">{r.vehicle_class}</span></td>
                <td>{r.test_type}</td>
                <td className="mono">{r.velocity_kmh}</td>
                <td className="mono">{r.mass_kg}</td>
                <td className="mono" style={{ color: r.hic > 1000 ? C.danger : 'var(--text)' }}>{r.hic.toFixed ? r.hic.toFixed(0) : r.hic}</td>
                <td className="mono">{r.chest_g.toFixed ? r.chest_g.toFixed(1) : r.chest_g}</td>
                <td className="mono">{r.intrusion_m.toFixed ? r.intrusion_m.toFixed(3) : r.intrusion_m}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="mono" style={{ fontSize: 12, color: 'var(--muted)' }}>
          Page {data.page} of {pages}
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
          <button className="btn btn-ghost" disabled={page >= pages} onClick={() => setPage(p => p + 1)}>Next</button>
        </div>
      </div>
    </div>
  )
}
