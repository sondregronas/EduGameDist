(() => {
  const grid = document.getElementById('game-grid')
  const search = document.getElementById('search')
  if (!grid || !search) return

  const cards = [...grid.querySelectorAll('.game-card[data-title]')]
  const counter = document.getElementById('result-count')
  const empty = document.getElementById('no-results')
  const matchToggle = document.getElementById('category-match')
  const clear = document.getElementById('clear-filters')

  // Nedtrekksmeny (listbox) som kan brukes med mus og tastatur. Med data-multiple kan flere valg krysses av;
  // det første valget («Alle …») tømmer valget.
  function dropdown(root, onChange) {
    const multiple = root.hasAttribute('data-multiple')
    const button = root.querySelector('.dropdown-button')
    const menu = root.querySelector('.menu')
    const shown = root.querySelector('.dropdown-value')
    const options = [...menu.querySelectorAll('[role="option"]')]
    const [allOption] = options
    let active = 0
    options.forEach((option, index) => { option.id = `${root.id}-${index}` })

    const selected = () => options.filter((option) => option.dataset.value && option.getAttribute('aria-selected') === 'true')
    const visibleParts = (option) => [...option.children].filter((part) => !part.matches('.menu-count, .menu-check')).map((part) => part.cloneNode(true))

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
    // Knappen viser det som er valgt: «Alle …», ett valg, eller det første valget og hvor mange til.
    function render() {
      const chosen = selected()
      allOption.setAttribute('aria-selected', String(chosen.length === 0))
      if (chosen.length <= 1) {
        shown.replaceChildren(...visibleParts(chosen[0] || allOption))
      } else {
        const names = chosen.map((option) => option.querySelector('.menu-text').textContent)
        const text = Object.assign(document.createElement('span'), { className: 'menu-text', textContent: names.join(', ') })
        const more = Object.assign(document.createElement('span'), { className: 'menu-count', textContent: String(chosen.length) })
        shown.replaceChildren(...visibleParts(chosen[0]).filter((part) => !part.matches('.menu-text')), text, more)
      }
      root.classList.toggle('is-set', chosen.length > 0)
    }
    function choose(index, notify = true) {
      const option = options[index]
      if (multiple && option !== allOption) {
        option.setAttribute('aria-selected', String(option.getAttribute('aria-selected') !== 'true'))
      } else {
        options.forEach((other) => other.setAttribute('aria-selected', String(other === option)))
      }
      render()
      if (notify) onChange()
    }
    // I en flervalgsmeny blir menyen stående åpen, så man kan krysse av flere på rad.
    const pick = (index) => { choose(index); if (!multiple || index === 0) close() }

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
      if (option) pick(options.indexOf(option))
    })
    menu.addEventListener('keydown', (event) => {
      const last = options.length - 1
      const moves = { ArrowDown: Math.min(active + 1, last), ArrowUp: Math.max(active - 1, 0), Home: 0, End: last }
      if (event.key in moves) { event.preventDefault(); highlight(moves[event.key]) }
      else if (event.key === ' ' || (event.key === 'Enter' && !multiple)) { event.preventDefault(); pick(active) }
      else if (event.key === 'Enter') { event.preventDefault(); close() }
      else if (event.key === 'Escape') { event.preventDefault(); close() }
      else if (event.key === 'Tab') close(false)
    })
    document.addEventListener('click', (event) => { if (!root.contains(event.target)) close(false) })

    return {
      get values() { return selected().map((option) => option.dataset.value) },
      set(wanted) {
        const values = new Set(wanted.filter(Boolean))
        options.forEach((option) => option.setAttribute('aria-selected', String(values.has(option.dataset.value))))
        if (!multiple && selected().length > 1) selected().slice(1).forEach((option) => option.setAttribute('aria-selected', 'false'))
        render()
      },
    }
  }

  const filter = (id) => {
    const root = document.getElementById(id)
    return root ? dropdown(root, apply) : null
  }
  const category = filter('category-filter')
  const platform = filter('platform-filter')
  const matchAll = () => matchToggle?.querySelector('input[value="all"]').checked

  // Filtrene kan settes i adressen, f.eks. /?category=puzzle&category=co-op&match=all&platform=windows.
  const params = new URLSearchParams(location.search)
  search.value = params.get('q') || ''
  category?.set(params.getAll('category').map((value) => value.toLowerCase()))
  platform?.set([(params.get('platform') || '').toLowerCase()])
  if (matchToggle && params.get('match') === 'all') matchToggle.querySelector('input[value="all"]').checked = true

  function apply() {
    const query = search.value.trim().toLowerCase()
    const wantedCategories = category ? category.values : []
    const [wantedPlatform = ''] = platform ? platform.values : []
    const all = matchAll() && wantedCategories.length > 1
    let shown = 0
    cards.forEach((card) => {
      const categories = card.dataset.categories.split('|')
      const hasCategory = (value) => categories.includes(value)
      const visible = (!query || card.dataset.title.includes(query)) &&
        (!wantedCategories.length || (all ? wantedCategories.every(hasCategory) : wantedCategories.some(hasCategory))) &&
        (!wantedPlatform || card.dataset.platforms.split(' ').includes(wantedPlatform))
      card.classList.toggle('is-hidden', !visible)
      if (visible) shown++
    })
    counter.textContent = cards.length ? `${shown} av ${cards.length} spill` : ''
    empty.hidden = shown > 0 || cards.length === 0
    // «Minst én / Alle» betyr bare noe når mer enn én kategori er valgt.
    if (matchToggle) matchToggle.hidden = wantedCategories.length < 2
    if (clear) clear.hidden = !query && !wantedCategories.length && !wantedPlatform

    const next = new URLSearchParams()
    if (query) next.set('q', search.value.trim())
    wantedCategories.forEach((value) => next.append('category', value))
    if (all) next.set('match', 'all')
    if (wantedPlatform) next.set('platform', wantedPlatform)
    const queryString = next.toString()
    history.replaceState(null, '', queryString ? `?${queryString}` : location.pathname)
  }

  search.addEventListener('input', apply)
  matchToggle?.addEventListener('change', apply)
  clear?.addEventListener('click', () => {
    search.value = ''
    category?.set([])
    platform?.set([])
    apply()
    search.focus()
  })
  apply()
})()
