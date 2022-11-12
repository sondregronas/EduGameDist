const fs = require('fs')
const path = require('path')
const sqlite3 = require("sqlite3");

function copyFolderSync(from, to) {
    try {fs.mkdirSync(to, { recursive: true })} catch {}
    fs.readdirSync(from).forEach(element => {
        if (fs.lstatSync(path.join(from, element)).isFile()) {
          if (fs.existsSync(path.join(to, element))) { return }
          if (element === 'Games go here.txt') { return }
          fs.copyFileSync(path.join(from, element), path.join(to, element));
        } else {
          copyFolderSync(path.join(from, element), path.join(to, element));
        }
    });
}

function devMode(app) {
  console.log('WARNING: Dev mode initialized.')
  const path = require('path')
  const watchFolders = ['views', 'views/templates', 'public', 'public/css']
  let paths = []
  watchFolders.forEach(folder => {
    paths = paths.concat([path.join(__dirname, folder)])
  })
  app.use(require('easy-livereload')({
    watchDirs: paths,
    checkFunc: (file) => {
      return /.(pug|css|js|jpg|png|gif|svg)$/.test(file)
    }
  }))
}

function serializeDB(db_file) {
    // if folder to db_file does not exist, create it
    let db_folder = path.dirname(db_file)
    if (!fs.existsSync(db_folder)) { fs.mkdirSync(db_folder, { recursive: true }) }
    const db = new sqlite3.Database(db_file)
    db.serialize(() => {
      db.run("CREATE TABLE IF NOT EXISTS games (" +
          "id INTEGER NOT NULL PRIMARY KEY," +
          "Title TEXT NOT NULL," +
          "Description TEXT," +
          "Note TEXT," +
          "Cover BLOB," +
          "Time TEXT," +
          "Players TEXT," +
          "Category1 TEXT," +
          "Category2 TEXT," +
          "Category3 TEXT," +
          "Developer TEXT," +
          "Developer_link TEXT," +
          "Url TEXT," +
          "Win_dl TEXT," +
          "Mac_dl TEXT," +
          "Linux_dl TEXT," +
          "Android_dl TEXT," +
          "Steam TEXT," +
          "Humblebundle TEXT," +
          "Gog TEXT," +
          "Itchio TEXT)")
    });
    db.close()
}

// Hent data fra database
function getGameList(db_file) {
  let o = {}

  // Connect and load table 'games'
  let db = new sqlite3.Database(db_file)
  db.all("SELECT * FROM games ORDER BY (CASE WHEN title LIKE 'The %' THEN substring(title, 5, 1000) ELSE title END)", function(err, rows) {
    if (err) { console.log('No games found'); return; }
    rows.forEach(function (row) {
      let key = row.Title.replaceAll(' ', '-')
      key = key.replaceAll(':', '')

      // Essential data
      o[key] = {title: row.Title}
      if (row.Description)    {o[key]["description"]    = row.Description}
      if (row.Note)           {o[key]["note"]           = row.Note}
      if (row.Cover)          {o[key]["cover"]          = 'img/' + JSON.parse(row.Cover)[0].url.split('/download/noco/Games/Games/Cover/')[1]}
      if (row.Time)           {o[key]["ttb"]            = row.Time}
      if (row.Players)        {o[key]["players"]        = row.Players}
      if (row.Developer)      {o[key]["developer"]      = row.Developer}
      if (row.Developer_link) {o[key]["developer_link"] = row.Developer_link}

      // Download buttons / URLs
      if (row.Url)        {o[key]["url"]        = row.Url}
      if (row.Win_dl)     {o[key]["win_dl"]     = `/games/Windows/${row.Win_dl}`}
      if (row.Mac_dl)     {o[key]["mac_dl"]     = `/games/Mac/${row.Mac_dl}`}
      if (row.Linux_dl)   {o[key]["linux_dl"]   = `/games/Linux/${row.Linux_dl}`}
      if (row.Android_dl) {o[key]["android_dl"] = `/games/Android/${row.Android_dl}`}

      // Categories
      o[key]["category"] = []
      if (row.Category1) {o[key]["category"].push(row.Category1)}
      if (row.Category2) {o[key]["category"].push(row.Category2)}
      if (row.Category3) {o[key]["category"].push(row.Category3)}

      // Links
      o[key]["links"] = []
      if (row.Steam) {o[key]["links"].push(row.Steam)}
      if (row.Gog) {o[key]["links"].push(row.Gog)}
      if (row.Itchio) {o[key]["links"].push(row.Itchio)}
      if (row.Humblebundle) {o[key]["links"].push(row.Humblebundle)}
      })
    });
  db.close()
  return o
}

module.exports = {
    copyFolderSync,
    devMode,
    serializeDB,
    getGameList
}
