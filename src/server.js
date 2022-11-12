// Variabler
const port = process.env.PORT || 80
const db_file = './db/gamedb.db'

// Dependencies
const util = require('./util')
const express = require('express')
const app = express()

app.use(express.static('public'))
app.set('view engine', 'pug')
const pugData = {}  // Leave this empty

// Database
util.serializeDB(db_file)

// Environment Variables
if (process.env.DOCKER) { util.copyFolderSync('/app.defaults', '/app')}
if (process.env.NODE_ENV === 'dev') { util.devMode(app) }

app.get('/*', async (req, res) => {
  let url = req.url.replace(/^\/+/, '')

  if (pugData.gameList[url]) { pugData.gameData = pugData.gameList[url]; url = 'game'}
  else if (url === '') { url = 'index' }

  res.render(url, pugData, (err, html) => {
    if (err) { res.redirect(`/`) }
    else { res.send(html) }
  })

  // Reload db entries
  pugData.gameList = util.getGameList(db_file, pugData)
})

// Start app
app.listen(port, () => {
  pugData.gameList = util.getGameList(db_file, pugData)
  console.log(`Listening on port ${port}`)
})
