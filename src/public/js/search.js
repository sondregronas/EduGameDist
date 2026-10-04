(() => {
  const grid = document.getElementById('game-grid')
  const search = document.getElementById('search')
  if (!grid || !search) return

  const cards = [...grid.querySelectorAll('a.game-card')]
  const chips = [...document.querySelectorAll('.filter-chip')]
  const counter = document.getElementById('result-count')
  const empty = document.getElementById('no-results')
  let platform = null

  chips.forEach((chip) => {
    const available = cards.some((card) => card.dataset.platforms.split(' ').includes(chip.dataset.platform))
    chip.hidden = !available
    chip.addEventListener('click', () => {
      platform = platform === chip.dataset.platform ? null : chip.dataset.platform
      chips.forEach((other) => other.setAttribute('aria-pressed', String(other.dataset.platform === platform)))
      apply()
    })
  })

  function apply() {
    const query = search.value.trim().toLowerCase()
    let shown = 0
    cards.forEach((card) => {
      const matchesText = !query ||
        card.dataset.title.includes(query) ||
        card.dataset.categories.split('|').some((category) => category.includes(query))
      const matchesPlatform = !platform || card.dataset.platforms.split(' ').includes(platform)
      const visible = matchesText && matchesPlatform
      card.classList.toggle('is-hidden', !visible)
      if (visible) shown++
    })
    counter.textContent = cards.length ? `${shown} av ${cards.length} spill` : ''
    empty.hidden = shown > 0 || cards.length === 0
  }

  search.addEventListener('input', apply)
  apply()
})()
