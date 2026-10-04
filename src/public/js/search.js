(() => {
  const grid = document.getElementById('game-grid')
  const search = document.getElementById('search')
  if (!grid || !search) return

  const cards = [...grid.querySelectorAll('.game-card[data-title]')]
  const counter = document.getElementById('result-count')
  const empty = document.getElementById('no-results')

  // Nedtrekksmeny (listbox) som kan brukes med mus og tastatur.
  function dropdown(root, onChange) {
    const button = root.querySelector('.dropdown-button')
    const menu = root.querySelector('.menu')
    const shown = root.querySelector('.dropdown-value')
    const options = [...menu.querySelectorAll('[role="option"]')]
    let active = 0
    options.forEach((option, index) => { option.id = `${root.id}-${index}` })

    function highlight(index) {
      active = index
      options.forEach((option, i) => option.classList.toggle('active', i === index))
      menu.setAttribute('aria-activedescendant', options[index].id)
      options[index].scrollIntoView({ block: 'nearest' })
    }
    function open() {
      menu.hidden = false
      button.setAttribute('aria-expanded', 'true')
      highlight(Math.max(0, options.findIndex((option) => option.getAttribute('aria-selected') === 'true')))
      menu.focus()
    }
    function close(refocus = true) {
      if (menu.hidden) return
      menu.hidden = true
      button.setAttribute('aria-expanded', 'false')
      if (refocus) button.focus()
    }
    function choose(index, notify = true) {
      const option = options[index]
      options.forEach((other) => other.setAttribute('aria-selected', String(other === option)))
      shown.replaceChildren(...[...option.children].filter((part) => !part.matches('.menu-count, .menu-check')).map((part) => part.cloneNode(true)))
      root.dataset.value = option.dataset.value
      root.classList.toggle('is-set', Boolean(option.dataset.value))
      if (notify) onChange()
    }

    button.addEventListener('click', () => (menu.hidden ? open() : close()))
    button.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); open() }
    })
    menu.addEventListener('mousemove', (event) => {
      const option = event.target.closest('[role="option"]')
      if (option) highlight(options.indexOf(option))
    })
    menu.addEventListener('click', (event) => {
      const option = event.target.closest('[role="option"]')
      if (option) { choose(options.indexOf(option)); close() }
    })
    menu.addEventListener('keydown', (event) => {
      const last = options.length - 1
      const moves = { ArrowDown: Math.min(active + 1, last), ArrowUp: Math.max(active - 1, 0), Home: 0, End: last }
      if (event.key in moves) { event.preventDefault(); highlight(moves[event.key]) }
      else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(active); close() }
      else if (event.key === 'Escape') { event.preventDefault(); close() }
      else if (event.key === 'Tab') close(false)
    })
    document.addEventListener('click', (event) => { if (!root.contains(event.target)) close(false) })

    return {
      get value() { return root.dataset.value || '' },
      set(wanted) {
        const index = options.findIndex((option) => option.dataset.value === wanted)
        if (index >= 0) choose(index, false)
      },
    }
  }

  const filter = (id) => {
    const root = document.getElementById(id)
    return root ? dropdown(root, apply) : null
  }
  const category = filter('category-filter')
  const platform = filter('platform-filter')

  // Filtrene kan settes i adressen, f.eks. /?category=puzzle&platform=windows.
  const params = new URLSearchParams(location.search)
  search.value = params.get('q') || ''
  category?.set((params.get('category') || '').toLowerCase())
  platform?.set((params.get('platform') || '').toLowerCase())

  function apply() {
    const query = search.value.trim().toLowerCase()
    const wantedCategory = category ? category.value : ''
    const wantedPlatform = platform ? platform.value : ''
    let shown = 0
    cards.forEach((card) => {
      const visible = (!query || card.dataset.title.includes(query)) &&
        (!wantedCategory || card.dataset.categories.split('|').includes(wantedCategory)) &&
        (!wantedPlatform || card.dataset.platforms.split(' ').includes(wantedPlatform))
      card.classList.toggle('is-hidden', !visible)
      if (visible) shown++
    })
    counter.textContent = cards.length ? `${shown} av ${cards.length} spill` : ''
    empty.hidden = shown > 0 || cards.length === 0

    const next = new URLSearchParams()
    if (query) next.set('q', search.value.trim())
    if (wantedCategory) next.set('category', wantedCategory)
    if (wantedPlatform) next.set('platform', wantedPlatform)
    const queryString = next.toString()
    history.replaceState(null, '', queryString ? `?${queryString}` : location.pathname)
  }

  search.addEventListener('input', apply)
  apply()
})()
