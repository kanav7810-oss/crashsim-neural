import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'
import { C } from '../theme'

const THEME = {
  font: { family: 'Inter, system-ui, sans-serif', color: C.text2, size: 11 },
  hoverlabel: { bgcolor: C.surface2, bordercolor: C.border, font: { color: C.text, size: 11, family: 'Inter, sans-serif' } },
  colorway: [C.accent, C.secondary, C.ok, C.warn, C.accentH]
}

function themedLayout(layout) {
  const l = { ...layout }
  delete l.template
  delete l.title
  const axis = (a) => ({
    gridcolor: C.border,
    zerolinecolor: C.border,
    linecolor: C.border,
    tickfont: { color: C.muted, size: 11, family: 'Inter, sans-serif' },
    titlefont: { color: C.muted, size: 11 },
    ...a
  })
  for (const k of ['xaxis', 'yaxis', 'xaxis2', 'yaxis2', 'zaxis']) {
    if (l[k]) l[k] = axis(l[k])
  }
  if (l.scene) {
    for (const k of ['xaxis', 'yaxis', 'zaxis']) {
      if (l.scene[k]) l.scene[k] = axis(l.scene[k])
    }
  }
  if (l.legend) {
    l.legend = { ...l.legend, font: { color: C.text2, size: 11, family: 'Inter, sans-serif' }, bgcolor: 'rgba(0,0,0,0)' }
  }
  if (l.colorbar || (l.data && l.data.some(t => t.colorbar))) {
    const cb = { ...(l.colorbar || {}), titlefont: { color: C.muted, size: 11 }, tickfont: { color: C.muted, size: 11 } }
    if (l.colorbar) l.colorbar = cb
    l.data = l.data?.map(t => t.colorbar ? { ...t, colorbar: cb } : t)
  }
  return l
}

export default function PlotlyChart({ data, layout, height = 360, title }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!ref.current || !data || data.length === 0) return
    const merged = {
      ...themedLayout(layout || {}),
      autosize: true,
      margin: { t: 8, l: 52, r: 18, b: 40 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: THEME.font,
      hoverlabel: THEME.hoverlabel,
      colorway: THEME.colorway
    }
    Plotly.react(ref.current, data, merged, {
      responsive: true, displayModeBar: false
    })
  }, [data, layout, title])

  return (
    <div style={{ width: '100%', height }}>
      <div ref={ref} style={{ width: '100%', height: '100%' }} data-testid="plotly-chart" />
    </div>
  )
}
