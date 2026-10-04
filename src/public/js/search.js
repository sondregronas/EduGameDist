(() => {
  const grid = document.getElementById('game-grid')
  const search = document.getElementById('search')
  if (!grid || !search) return

  const cards = [...grid.querySelectorAll('.game-card[data-title]')]
  const category = document.getElementById('category-filter')
  const platform = document.getElementById('platform-filter')
  const counter = document.getElementById('result-count')
  const empty = document.getElementById('no-results')

  // Filtrene kan settes i adressen, f.eks. /?category=puzzle&platform=windows.
  const params = new URLSearchParams(location.search)
  search.value = params.get('q') || ''
  for (const [select, key] of [[category, 'category'], [platform, 'platform']]) {
    const wanted = (params.get(key) || '').toLowerCase()
    if (select && [...select.options].some((option) => option.value === wanted)) select.value = wanted
  }

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
  category?.addEventListener('change', apply)
  platform?.addEventListener('change', apply)
  apply()
})()
