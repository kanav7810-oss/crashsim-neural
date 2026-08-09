const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function handle(r) {
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try {
      const j = await r.json()
      msg = j.detail || msg
    } catch (_) { /* ignore */ }
    throw new Error(msg)
  }
  return r.json()
}

export function get(path, params) {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null)).toString()
    : ''
  return fetch(API + path + qs).then(handle)
}

export function post(path, body) {
  return fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(handle)
}

export function trainingStream(onEvent) {
  const es = new EventSource(API + '/api/training/stream')
  es.onmessage = (ev) => onEvent(JSON.parse(ev.data))
  es.onerror = () => es.close()
  return () => es.close()
}

export default { get, post, trainingStream, API }
