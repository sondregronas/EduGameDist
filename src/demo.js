const fs = require('fs')
const pug = require('pug')
const util = require('./util')
const demoImg = require('./demo-img')
const pugData = {title: 'EduGameDist Demo', gameList: {}, gameData: {}}


const basegame = {
  title: 'Title',
  description: 'Description',
  note: '',
  cover: demoImg.img1,

  ttb: '10 min',
  players: '1',
  category: [
    'Cat 1',
    'Cat 2',
    'Cat 3'
  ],

  developer: 'Sondre Grønås',
  developer_link: 'https://github.com/sondregronas',

  url: '#',
  win_dl: '#',
  mac_dl: '#',
  linux_dl: '#',
  android_dl: '#',

  links: [
    'https://steampowered.com',
    'https://itch.io',
    'https://gog.com',
    'https://humblebundle.com',
    '#'
  ]
}

game1 = Object.assign({}, basegame, {
    title: 'Fake: Game',
    description: 'Explore the world of Fake: Game, a game about nothing.',
    note: 'You can add personalized notes, with <a href="#">links</a> and other <b>HTML</b> tags.',
    cover: demoImg.fakegame,
    url: '',
    linux_dl: '',
    android_dl: ''
})

game2 = Object.assign({}, basegame, {
    title: 'Non-Existant',
    description: 'This game does not exist, nor do the associated links.',
    cover: demoImg.nonexistant,
    players: '1',
    ttb: '5 min',
    developer_link: undefined,
    category: [
        'Existance',
        'Game'
    ],
    links: [],
    win_dl: '',
    mac_dl: '',
    android_dl: ''
})

game3 = Object.assign({}, basegame, {
    title: 'Sample 2',
    description: 'This is a sample game.',
    cover: demoImg.sample2,
    players: '1+',
    ttb: '3 hours',
    category: [
        'Sample',
        'Game'
    ],
})

game4 = Object.assign({}, basegame, {
    title: 'Space Filler 3',
    description: 'Meet the Space Filler 3, a game filling the space of an otherwise empty game list.',
    cover: demoImg.spacefiller3,
    players: '2-8',
    ttb: '30 min',
    category: [
        'Space',
        'Filling'
    ],
    win_dl: '',
    mac_dl: '',
    linux_dl: '',
    android_dl: ''
})


pugData.gameList[game1.title.replace(/ /g, '-').replace(/:/g, '')] = game1
pugData.gameList[game2.title.replace(/ /g, '-').replace(/:/g, '')] = game2
pugData.gameList[game3.title.replace(/ /g, '-').replace(/:/g, '')] = game3
pugData.gameList[game4.title.replace(/ /g, '-').replace(/:/g, '')] = game4

function main() {
    const html = pug.renderFile('views/index.pug', pugData)

    fs.mkdirSync('demo', { recursive: true })
    util.copyFolderSync('public', 'demo')

    fs.writeFile('demo/index.html', html, function (err) {if (err) throw err})

    Object.values(pugData.gameList).forEach(function (game) {
        pugData.gameData = game
        // TODO: Replace "Nocodb" link with a demo link to nocodb
        let html = pug.renderFile('views/game.pug', pugData)
        let fname = game.title.replace(/ /g, '-').replace(/:/g, '')
        fs.writeFile(`demo/${fname}.html`, html, function (err) {if (err) throw err})
    })
}

main()