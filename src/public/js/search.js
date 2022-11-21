let games = document.querySelectorAll('[id=game-grid-card]')

// Search bar, search by title or category
document.getElementById('search').addEventListener('input', (e) => {
    let search = e.target.value.toLowerCase()
    Array.from(games).forEach((game) => {
        let title = game.getElementsByClassName('game-title')[0].innerHTML.toLowerCase()
        let categories = []
        // Add all categories to array
        game.querySelectorAll('[class=game-card-category]').forEach(category => {
            categories.push(category.innerHTML.toLowerCase())
        })
        if (title.includes(search) || categories.some(category => category.startsWith(search))) {
            game.classList.remove('hidden-search')
        } else {
            game.classList.add('hidden-search')
        }
    })
    checkAllHidden()
})

// Filter by platform
document.querySelectorAll('.filterBtn').forEach((btn) => {
    btn.addEventListener('change', (e) => {
        let platform = btn.className.split(' ')[2]
        Array.from(games).forEach((game) => {
            game.classList.remove('hidden-platform')
        })
        // Hide games for other platforms
        if (btn.checked) {
            Array.from(games).forEach((game) => {
                if (!game.getElementsByClassName(platform).length) {
                    game.classList.add('hidden-platform')
                }
            })
        }
        // Add radio behaviour to filter buttons
        document.querySelectorAll('.filterBtn').forEach((btn2) => {
            if (btn2 !== btn) {
                btn2.checked = false
            }
        })
        checkAllHidden()
    })
})

// Only display platform buttons if there are games for that platform
document.querySelectorAll('.filterBtn').forEach((btn) => {
    let platform = btn.className.split(' ')[2]
    Array.from(games).forEach((game) => {
        if (game.getElementsByClassName(platform).length > 0) {
            btn.style.display = 'inline-block'
        }
    })
})

// If all games are hidden, display a message
function checkAllHidden(){
    let hidden = []
    Array.from(games).forEach((game) => {
        if (game.classList.contains('hidden-platform')) {
            hidden.push(game)
        }
        else if (game.classList.contains('hidden-search')) {
            hidden.push(game)
        }
    })
    if (hidden.length === games.length) {
        document.getElementById('no-results').style.display = 'block'
    } else {
        document.getElementById('no-results').style.display = 'none'
    }
}
