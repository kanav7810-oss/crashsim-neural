import { predictBody, proxy } from '../lib/proxy.js'

export default async function handler(req, res) {
  const params = Object.fromEntries(new URLSearchParams(req.query || '').entries())
  const { status, data } = await proxy('/api/parameter-sweep', predictBody(params))
  res.status(status).json(data)
}
