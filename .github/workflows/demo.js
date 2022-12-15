const fs = require('fs')
const pug = require('pug')
const util = require('./util')
const pugData = {
    title: 'EduGameDist Demo',
    base_url: 'https://sondregronas.github.io/EduGameDist',
    gameList: {},
    gameData: {}
}


const basegame = {
  title: 'Title',
  description: 'Description',
  note: '',
  cover: 'cover.png',

  ttb: '10 min',
  players: '1',
  category: [
    'Cat 1',
    'Cat 2',
    'Cat 3'
  ],

  developer: 'Sondre Grønås',
  developer_link: 'https://github.com/sondregronas',

  url: '',
  win_dl: '',
  mac_dl: '',
  linux_dl: '',
  android_dl: '',

  links: [
    'https://steampowered.com',
    'https://itch.io',
    'https://gog.com',
    'https://humblebundle.com',
    '#'
  ]
}

fakegame = Object.assign({}, basegame, {
    title: 'Fake: Game',
    description: 'Explore the world of Fake: Game, a game about nothing.',
    note: 'You can add personalized notes, with <a href="#">links</a> and other <b>HTML</b> tags.',
    cover: 'fakegame.png',
    win_dl: '#',
    mac_dl: '#'
})

nonexistant = Object.assign({}, basegame, {
    title: 'Non-Existant',
    description: 'This game does not exist, nor do the associated links.',
    cover: 'nonexistant.png',
    players: '1',
    ttb: '5 min',
    developer_link: undefined,
    category: [
        'Existance',
        'Game'
    ],
    links: [],
    url: '#',
    linux_dl: '#'
})

sample2 = Object.assign({}, basegame, {
    title: 'Sample 2',
    description: 'This is a sample game.',
    cover: 'sample2.png',
    players: '1+',
    ttb: '3 hours',
    category: [
        'Sample',
        'Game'
    ],
    win_dl: '#',
    mac_dl: '#',
    linux_dl: '#',
    android_dl: '#',
    url: '#'
})

spacefiller3 = Object.assign({}, basegame, {
    title: 'Space Filler 3',
    description: 'Meet the Space Filler 3, a game filling the space of an otherwise empty game list.',
    cover: 'spacefiller3.png',
    players: '2-8',
    ttb: '30 min',
    category: [
        'Space',
        'Filling'
    ],
    url: '#'
})

oslo2084 = Object.assign({}, basegame, {
    title: 'Oslo 2084',
    description: `I Oslo 2084 styrer spilleren Embla, en ung jente som bruker tiden sin på hobbyhacking og programmering av sin egen robotvenn, støvsugeren Moppy. I Oslo 2084 er byen i stadig større grad styrt av kunstig intelligens og ny teknologi. Embla og Moppy må løse ulike utfordringer og demokratiske dilemma for å bevege seg gjennom de ulike nivåene i spillet og kjempe mot anti-demokratiske krefter.`,
    note: `Fra Demokrativerksted hos Utøya (Europeiske Wergeland Centre).<br><a href="https://theewc.org/content/uploads/sites/7/2021/10/Hefte-Oslo-2084-1-1.pdf">Trykk her for Ressurshefte.pdf</a>`,
    cover: 'oslo2084.png',
    ttb: '45 min',
    players: '1',
    category: [
        'Demokrati',
        'Norsk'
    ],
    developer: 'Anansi',
    developer_link: 'https://demokrativerksted.no/spill',
    url: 'https://anansigames.itch.io/oslo2084',
    links: [
        'https://anansigames.itch.io/oslo2084'
    ]
})

pugData.gameList = {
    'Fake-Game': fakegame,
    'Non-Existant': nonexistant,
    'Oslo-2084': oslo2084,
    'Sample-2': sample2,
    'Space-Filler-3': spacefiller3
}

pugData.gameList = Object.fromEntries(
    Object.entries(pugData.gameList).sort()
)

function main() {
    fs.mkdirSync('demo', { recursive: true })
    util.copyFolderSync('public', 'demo')

    let nocodb_placeholder = `href="/" onmouseover="javascript:event.target.port=8080"`
    let nocodb_replacement = `href="https://sondregronas.github.io/EduGameDist/docs/Gallery/Nocodb" target="_blank"`
    let games = `href="/"`
    let games_replacement = `href="/EduGameDist"`

    let html = pug.renderFile('views/index.pug', pugData)
    html = html.replace(nocodb_placeholder, nocodb_replacement)
    html = html.replace(games, games_replacement)
    fs.writeFile('demo/index.html', html, function (err) {if (err) throw err})

    Object.values(pugData.gameList).forEach(function (game) {
        pugData.gameData = game
        // TODO: Replace "Nocodb" link with an actual demo for nocodb
        let fname = game.title.replace(/ /g, '-').replace(/:/g, '')

        let html = pug.renderFile('views/game.pug', pugData)
        html = html.replace(nocodb_placeholder, nocodb_replacement)
        html = html.replace(games, games_replacement)
        fs.writeFile(`demo/${fname}.html`, html, function (err) {if (err) throw err})
    })
}

main()