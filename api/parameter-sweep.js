const { predictBody, proxy } = require('../lib/proxy.js')

module.exports = async (req, res) => {
  const params = req.query || {}
  const { status, data } = await proxy('/api/parameter-sweep', predictBody(params))
  res.status(status).json(data)
}
