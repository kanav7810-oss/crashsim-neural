export const C = {
  accent: '#c79a55',
  accentH: '#ddb56e',
  secondary: '#56c09a',
  ok: '#53be70',
  warn: '#f5ae39',
  amber: '#e8862e',
  danger: '#f14d4f',
  text: '#e7e3dc',
  text2: '#a6a29b',
  muted: '#7a756e',
  border: '#1c1b18',
  borderS: '#26241f',
  surface2: '#131210',
  grid: '#1c1b18'
}

export const TOOLTIP = {
  background: 'rgba(18, 18, 22, 0.92)',
  border: `1px solid ${C.borderS}`,
  borderRadius: 6,
  fontSize: 12,
  color: C.text,
  boxShadow: '0 8px 28px -12px rgba(0,0,0,0.8)',
  backdropFilter: 'blur(8px)',
  padding: '6px 10px'
}

export const hicColor = (hic) => (hic < 700 ? C.ok : hic < 1000 ? C.warn : C.danger)
