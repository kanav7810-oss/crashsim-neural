const RENDER = 'https://crashsim-neural-api.onrender.com'

const NUM_KEYS = [
  'mass_kg', 'velocity_kmh', 'angle_deg', 'a_pillar_thickness_mm',
  'crumple_zone_length_m', 'yield_strength_mpa', 'section_height_mm',
  'section_width_mm', 'year', 'low', 'high', 'steps'
]

function normalize(o) {
  const out = { ...o }
  for (const k of NUM_KEYS) {
    if (out[k] != null && out[k] !== '') out[k] = Number(out[k])
  }
  return out
}

function groupParams(params, prefix) {
  const out = {}
  for (const k of Object.keys(params)) {
    if (k.startsWith(prefix)) out[k.slice(prefix.length)] = params[k]
  }
  return out
}

function predictBody(params) {
  return normalize(params)
}

function compareBody(params) {
  return {
    vehicle_a: normalize(groupParams(params, 'a_')),
    vehicle_b: normalize(groupParams(params, 'b_'))
  }
}

async function proxy(path, body, method = 'POST') {
  try {
    const r = await fetch(RENDER + path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    })
    const text = await r.text()
    let data
    try { data = JSON.parse(text) } catch { data = { detail: text } }
    return { status: r.status, data }
  } catch (e) {
    return { status: 502, data: { detail: 'upstream unavailable: ' + (e && e.message ? e.message : 'unknown') } }
  }
}

module.exports = { predictBody, compareBody, proxy, RENDER }
