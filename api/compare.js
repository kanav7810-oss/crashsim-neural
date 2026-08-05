const { compareBody, proxy } = require('../lib/proxy.js')

module.exports = async (req, res) => {
  const params = req.query || {}
  const { status, data } = await proxy('/api/compare', compareBody(params))
  res.status(status).json(data)
}
