const { proxy } = require('../lib/proxy.js')

module.exports = async (req, res) => {
  const { status, data } = await proxy('/api/export/pdf', {})
  res.status(status).json(data)
}
