const { RENDER } = require('../lib/proxy.js')

module.exports = async (req, res) => {
  try {
    const r = await fetch(RENDER + '/api/export/pdf/download')
    const buf = Buffer.from(await r.arrayBuffer())
    res.setHeader('Content-Type', 'application/pdf')
    res.setHeader('Content-Disposition', 'attachment; filename="crashsim_neural_research_report.pdf"')
    res.status(r.status).send(buf)
  } catch (e) {
    res.status(502).json({ detail: 'PDF download unavailable' })
  }
}
