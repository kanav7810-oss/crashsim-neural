const RENDER = 'https://crashsim-neural-api.onrender.com'

export function parseQuery(event) {
  const { searchParams } = new URL(event.url || `http://x${event.rawQuery || ''}`)
  const out = {}
  for (const [k, v] of searchParams.entries()) out[k] = v
  return out
}

function groupParams(params, prefix) {
  const out = {}
  for (const [k, v] of Object.entries(params)) {
    if (k.startsWith(prefix)) {
      out[k.slice(prefix.length)] = v
    }
  }
  return out
}

export function compareBody(params) {
  return {
    vehicle_a: normalize(groupParams(params, 'a_')),
    vehicle_b: normalize(groupParams(params, 'b_'))
  }
}

export function predictBody(params) {
  return normalize(params)
}

function normalize(o) {
  const numKeys = ['mass_kg','velocity_kmh','angle_deg','a_pillar_thickness_mm','crumple_zone_length_m','yield_strength_mpa','section_height_mm','section_width_mm','year']
  const out = { ...o }
  for (const k of numKeys) if (out[k] != null && out[k] !== '') out[k] = Number(out[k])
  return out
}

export async function proxy(path, body, method = 'POST') {
  const r = await fetch(RENDER + path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  })
  const text = await r.text()
  let data
  try { data = JSON.parse(text) } catch { data = { detail: text } }
  return { status: r.status, data }
}
