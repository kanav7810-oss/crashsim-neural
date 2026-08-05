import { proxy } from '../lib/proxy.js'

export default async function handler(req, res) {
  const { status, data } = await proxy('/api/export/pdf', {})
  res.status(status).json(data)
}
