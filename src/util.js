const fs = require('fs')
const path = require('path')
const sqlite3 = require("sqlite3");

// This function copies all files from a folder to another recursively, which is used for the docker image
function copyFolderSync(from, to) {
    try {
        fs.mkdirSync(to, {
            recursive: true
        })
    } catch {}
    fs.readdirSync(from).forEach(element => {
        if (fs.lstatSync(path.join(from, element)).isFile()) {
            if (fs.existsSync(path.join(to, element))) {
                return
            }
            if (element === 'Games go here.txt') {
                return
            }
            fs.copyFileSync(path.join(from, element), path.join(to, element));
        } else {
            copyFolderSync(path.join(from, element), path.join(to, element));
        }
    });
}

// Spin up a development server, which reloads on file changes
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
    if (!fs.existsSync(db_folder)) {
        fs.mkdirSync(db_folder, {
            recursive: true
        })
    }

    // Connect and load table 'games', then serialize
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
            "Store1 TEXT," +
            "Store2 TEXT," +
            "Store3 TEXT," +
            "Store4 TEXT," +
            "Store5 TEXT)")
    });
    db.close()
}

// Parse cover image from database and return it as "img/<file_path>" or data:image/png;base64,<base64>
function getCover(row) {
    let cover = row ? row : null
    // If cover is from NocoDB, find the filename based on the URL
    try {
        // Nocodb stores urls as "https://<domain>/download/<project>/<table>/Cover/<file_path>"
        // We only need the file_path, which is the last part of the URL.
        // Within the docker-compose.yml file, we can map the nocodb upload folder to the /img folder,
        // which we want to use for the cover images instead of the database.
        // TODO: Temporary hack, we need to replace nocodb with a better solution eventually
        //       if key path is in the JSON, use it instead of the URL
        if (JSON.parse(row)[0].path) {return 'img/' + JSON.parse(row)[0].path.match(/download\/.+\/.+\/.+\/Cover\/(.*)/)[1]}
        return 'img/' + JSON.parse(row)[0].url.match(/\/download\/.+\/.+\/.+\/Cover\/(.*)/)[1]
    } catch {}
    // If cover is an object, convert it to a file
    if (typeof cover === 'object' && cover !== null) {
        if (!cover.toString().startsWith('data:image')) {
            return 'data:image/jpeg;base64,' + cover.toString('base64')
        }
    }
    return cover
}


// Fetch game list from database, and return it as an object
function getGameList(db_file) {
    let o = {}

    // Connect and load table 'games'
    let db = new sqlite3.Database(db_file)
    db.all("SELECT * FROM games ORDER BY (CASE WHEN title LIKE 'The %' THEN substring(title, 5, 1000) ELSE title END)", function(err, rows) {
        if (err) {
            console.log('No games found');
            return;
        }
        rows.forEach(function(row) {
            let key = row.Title.replaceAll(' ', '-')
            key = key.replaceAll(':', '')

            o[key] = {
                title: row.Title,
                description: row.Description,
                note: row.Note || '',
                cover: getCover(row.Cover),
                ttb: row.Time,
                players: row.Players,
                category: [
                    row.Category1 ? row.Category1 : '',
                    row.Category2 ? row.Category2 : '',
                    row.Category3 ? row.Category3 : ''
                ].filter(Boolean),
                developer: row.Developer,
                developer_link: row.Developer_link,
                url: row.Url,
                win_dl: row.Win_dl ? (row.Win_dl.includes('://') ? row.Win_dl : `/games/Windows/${row.Win_dl}`) : '',
                mac_dl: row.Mac_dl ? (row.Mac_dl.includes('://') ? row.Mac_dl : `/games/Mac/${row.Mac_dl}`) : '',
                linux_dl: row.Linux_dl ? (row.Linux_dl.includes('://') ? row.Linux_dl : `/games/Linux/${row.Linux_dl}`) : '',
                android_dl: row.Android_dl ? (row.Android_dl.includes('://') ? row.Android_dl : `/games/Android/${row.Android_dl}`) : '',
                links: [
                    row.Store1 ? row.Store1 : '',
                    row.Store2 ? row.Store2 : '',
                    row.Store3 ? row.Store3 : '',
                    row.Store4 ? row.Store4 : '',
                    row.Store5 ? row.Store5 : ''
                ].filter(Boolean)
            }
        });
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