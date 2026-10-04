(() => {
  const $ = (selector, root = document) => root.querySelector(selector)
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]

  const icon = (name) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    svg.setAttribute('class', 'icon')
    svg.setAttribute('aria-hidden', 'true')
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use')
    use.setAttribute('href', `/assets/img/icons.svg#${name}`)
    svg.appendChild(use)
    return svg
  }

  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag)
    Object.entries(props).forEach(([key, value]) => {
      if (key === 'class') node.className = value
      else if (key === 'dataset') Object.assign(node.dataset, value)
      else node.setAttribute(key, value)
    })
    children.forEach((child) => node.append(child))
    return node
  }

  function toast(message, type = '') {
    const box = $('#toasts')
    // Samme melding flere ganger på rad (f.eks. ved flytting med piltastene) vises bare én gang.
    $$('.toast', box).filter((item) => item.textContent === message).forEach((item) => item.remove())
    const item = el('div', { class: `toast ${type}` }, message)
    box.appendChild(item)
    setTimeout(() => item.remove(), type === 'error' ? 8000 : 4500)
  }

  function flash(message, type) {
    sessionStorage.setItem('flash', JSON.stringify({ message, type }))
  }

  // Filer (Blob) sendes som de er, alt annet som JSON.
  async function api(method, url, body) {
    const raw = body instanceof Blob
    const response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': raw ? 'application/octet-stream' : 'application/json' } : {},
      body: body ? (raw ? body : JSON.stringify(body)) : undefined,
    })
    let data = {}
    try { data = await response.json() } catch { /* tomt svar */ }
    if (response.status === 401) { location.assign(`/login?next=${encodeURIComponent(location.pathname)}`); throw new Error(data.error || 'Du må logge inn.') }
    if (!response.ok) throw new Error(data.error || `Noe gikk galt (${response.status}).`)
    return data
  }

  const CRC_TABLE = (() => {
    const table = []
    for (let n = 0; n < 256; n++) {
      let c = n
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1
      table[n] = c >>> 0
    }
    return table
  })()

  // Samme fargeberegning som serverens `hue`-filter, slik at kategorier beholder fargen sin.
  function hue(text) {
    let crc = 0xFFFFFFFF
    for (const byte of new TextEncoder().encode(text)) crc = CRC_TABLE[(crc ^ byte) & 0xFF] ^ (crc >>> 8)
    return ((crc ^ 0xFFFFFFFF) >>> 0) % 360
  }

  function formatSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let value = bytes
    let unit = 0
    while (value >= 1000 && unit < units.length - 1) { value /= 1000; unit++ }
    const text = unit === 0 || value >= 100 ? value.toFixed(0) : value.toFixed(1).replace('.', ',')
    return `${text} ${units[unit]}`
  }

  const isHttpUrl = (value) => {
    try { return ['http:', 'https:'].includes(new URL(value).protocol) } catch { return false }
  }

  const pending = sessionStorage.getItem('flash')
  if (pending) {
    sessionStorage.removeItem('flash')
    const { message, type } = JSON.parse(pending)
    toast(message, type)
  }

  // Flytt elementer i en liste ved å dra dem (mus og berøring), eller med piltastene. Elementet løftes og
  // følger pekeren, de andre glir unna, og det pulserer når det er plassert.
  const calm = matchMedia('(prefers-reduced-motion: reduce)')
  const glide = { duration: 220, easing: 'cubic-bezier(.2, .8, .2, 1)' }

  function sortable(list, { items, axis = 'y', handle = null, onChange }) {
    const members = () => [...list.children].filter((child) => child.matches(items))

    // Endre rekkefølgen og la elementene gli fra der de var til der de havner (FLIP).
    function rearrange(change, held = null) {
      const all = members()
      const before = new Map(all.map((member) => [member, member.getBoundingClientRect()]))
      change()
      // Å flytte et element i DOM-en starter inn-animasjonen (pop) på nytt; den skal ikke vises her.
      all.forEach((member) => member.getAnimations().forEach((animation) => animation.cancel()))
      if (calm.matches) return
      all.forEach((member) => {
        if (member === held) return
        const was = before.get(member)
        const now = member.getBoundingClientRect()
        if (was.left !== now.left || was.top !== now.top) {
          member.animate([{ transform: `translate(${was.left - now.left}px, ${was.top - now.top}px)` }, { transform: 'none' }], glide)
        }
      })
    }

    function pulse(item) {
      if (calm.matches) return
      const accent = getComputedStyle(item).getPropertyValue('--accent').trim()
      item.animate([{ boxShadow: `0 0 0 0 ${accent}` }, { boxShadow: '0 0 0 12px transparent' }], { duration: 700, easing: 'ease-out' })
    }

    list.addEventListener('pointerdown', (event) => {
      const grip = event.target.closest(handle || items)
      const item = grip?.closest(items)
      if (event.button !== 0 || !item || !list.contains(item) || (!handle && event.target.closest('button, input, a'))) return
      event.preventDefault()
      const box = item.getBoundingClientRect()
      const grab = { x: event.clientX - box.left, y: event.clientY - box.top }
      const origin = { x: event.clientX, y: event.clientY }
      let lifted = false
      let moved = false

      // Lyttes på dokumentet: å flytte elementet i DOM-en ville ellers sluppet pekeren.
      const move = ({ clientX, clientY }) => {
        if (!lifted) {
          if (Math.hypot(clientX - origin.x, clientY - origin.y) < 4) return
          lifted = true
          item.getAnimations().forEach((animation) => animation.cancel())
          item.classList.add('dragging')
          document.documentElement.classList.add('is-sorting')
        }
        const target = document.elementFromPoint(clientX, clientY)?.closest(items)
        if (target && target !== item && target.parentElement === item.parentElement) {
          const area = target.getBoundingClientRect()
          const forward = members().indexOf(target) > members().indexOf(item)
          const point = axis === 'x' ? clientX : clientY
          const middle = axis === 'x' ? area.left + area.width / 2 : area.top + area.height / 2
          // Bytt først når pekeren er forbi midten i retningen den flyttes, så elementene ikke hopper frem og tilbake.
          if (forward ? point > middle : point < middle) {
            rearrange(() => target[forward ? 'after' : 'before'](item), item)
            moved = true
          }
        }
        item.style.transform = ''
        const home = item.getBoundingClientRect()
        item.style.transform = `translate(${clientX - grab.x - home.left}px, ${clientY - grab.y - home.top}px)`
      }
      const end = () => {
        document.removeEventListener('pointermove', move)
        document.removeEventListener('pointerup', end)
        document.removeEventListener('pointercancel', end)
        if (!lifted) return
        document.documentElement.classList.remove('is-sorting')
        const offset = item.style.transform
        item.style.transform = ''
        item.classList.remove('dragging')
        if (offset && !calm.matches) item.animate([{ transform: offset }, { transform: 'none' }], glide)
        if (moved) {
          pulse(item)
          onChange()
        }
      }
      document.addEventListener('pointermove', move)
      document.addEventListener('pointerup', end)
      document.addEventListener('pointercancel', end)
    })

    list.addEventListener('keydown', (event) => {
      const step = (axis === 'x' ? { ArrowLeft: -1, ArrowRight: 1 } : { ArrowUp: -1, ArrowDown: 1 })[event.key]
      const item = event.target.closest(items)
      if (!step || !item || event.target !== (handle ? item.querySelector(handle) : item)) return
      event.preventDefault()
      const sibling = step < 0 ? item.previousElementSibling : item.nextElementSibling
      if (!sibling?.matches(items)) return
      rearrange(() => sibling[step < 0 ? 'before' : 'after'](item))
      event.target.focus()
      pulse(item)
      onChange()
    })

    return { rearrange }
  }

  // ---------- Kategorier: velg fra listen, eller lag en ny med «Ny kategori» ----------
  function categoryPicker(root, inventory, selectedIds, onChange) {
    const byId = (id) => inventory.find((category) => category.id === id)
    let selected = selectedIds.filter(byId)
    let options = []
    let active = -1
    const chips = el('span', { class: 'tag-chips' })
    const pick = el('button', { type: 'button', class: 'tag-add-btn' }, icon('plus'), el('span', {}, 'Legg til kategori'))
    const search = el('input', {
      class: 'tag-input', placeholder: 'Søk i kategoriene …', autocomplete: 'off', role: 'combobox',
      'aria-expanded': 'false', 'aria-label': 'Søk i kategoriene', hidden: '',
    })
    const menu = el('div', { class: 'menu', role: 'listbox', hidden: '' })
    const create = el('button', { type: 'button', class: 'btn btn-small btn-ghost' }, icon('tag'), 'Ny kategori')
    const name = el('input', { class: 'tag-input', placeholder: 'Navn på ny kategori', maxlength: '100', 'aria-label': 'Navn på ny kategori', hidden: '' })
    root.replaceChildren(el('div', { class: 'tag-list' }, chips, el('span', { class: 'tag-add' }, pick, search, menu), el('span', { class: 'tag-add' }, create, name)))

    function renderChips() {
      chips.replaceChildren(...selected.map((id) => {
        const category = byId(id)
        return el('span', { class: 'tag tag-editable', style: `--h: ${hue(category.name)}`, dataset: { id }, tabindex: '0', title: 'Dra for å endre rekkefølgen, eller bruk piltastene' },
          el('span', {}, category.name),
          el('button', { type: 'button', class: 'tag-remove', 'aria-label': `Fjern ${category.name}` }, icon('minus')))
      }))
    }
    function choose(id) {
      if (selected.includes(id)) return
      selected.push(id)
      renderChips()
      onChange()
    }
    sortable(chips, {
      items: '.tag-editable',
      axis: 'x',
      onChange: () => {
        selected = $$('.tag-editable', chips).map((chip) => Number(chip.dataset.id))
        onChange()
      },
    })
    chips.addEventListener('click', (event) => {
      const remove = event.target.closest('.tag-remove')
      if (!remove) return
      const id = Number(remove.closest('.tag-editable').dataset.id)
      selected = selected.filter((other) => other !== id)
      renderChips()
      onChange()
    })

    // Søk og velg blant kategoriene som finnes
    function highlight(index) {
      active = index
      $$('.menu-option', menu).forEach((node, i) => node.classList.toggle('active', i === index))
      $$('.menu-option', menu)[index]?.scrollIntoView({ block: 'nearest' })
    }
    function renderMenu() {
      const query = search.value.trim().toLowerCase()
      options = inventory.filter((category) => !selected.includes(category.id) && category.name.toLowerCase().includes(query))
      menu.replaceChildren(...options.map((category, index) => {
        const node = el('button', { type: 'button', role: 'option', class: 'menu-option', tabindex: '-1' },
          el('span', { class: 'menu-dot', style: `--h: ${hue(category.name)}` }), el('span', { class: 'menu-text' }, category.name))
        node.addEventListener('mouseenter', () => highlight(index))
        node.addEventListener('click', () => { choose(category.id); search.value = ''; renderMenu() })
        return node
      }))
      if (!options.length) {
        const message = query ? 'Ingen treff. Bruk «Ny kategori» for å lage den.'
          : inventory.length ? 'Alle kategoriene er valgt.' : 'Ingen kategorier ennå. Bruk «Ny kategori».'
        menu.append(el('div', { class: 'menu-label' }, message))
      }
      menu.hidden = false
      search.setAttribute('aria-expanded', 'true')
      highlight(options.length ? 0 : -1)
    }
    function closeSearch() {
      search.value = ''
      search.hidden = true
      pick.hidden = false
      menu.hidden = true
      search.setAttribute('aria-expanded', 'false')
    }
    pick.addEventListener('click', () => { pick.hidden = true; search.hidden = false; search.focus(); renderMenu() })
    search.addEventListener('input', renderMenu)
    search.addEventListener('blur', closeSearch)
    search.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' && options.length) { event.preventDefault(); highlight((active + 1) % options.length) }
      else if (event.key === 'ArrowUp' && options.length) { event.preventDefault(); highlight((active - 1 + options.length) % options.length) }
      else if (event.key === 'Enter') {
        event.preventDefault()
        if (options[active]) { choose(options[active].id); search.value = ''; renderMenu() }
      } else if (event.key === 'Escape') { event.preventDefault(); closeSearch(); pick.focus() }
    })
    menu.addEventListener('mousedown', (event) => event.preventDefault())

    // Ny kategori legges i listen og velges med en gang
    const closeName = () => { name.value = ''; name.hidden = true; create.hidden = false }
    create.addEventListener('click', () => { create.hidden = true; name.hidden = false; name.focus() })
    name.addEventListener('blur', () => { if (!name.value.trim()) closeName() })
    name.addEventListener('keydown', async (event) => {
      if (event.key === 'Escape') { event.preventDefault(); closeName(); create.focus(); return }
      if (event.key !== 'Enter') return
      event.preventDefault()
      if (!name.value.trim()) return
      try {
        const category = await api('POST', '/api/categories', { name: name.value })
        if (!byId(category.id)) inventory.push({ id: category.id, name: category.name })
        choose(category.id)
        toast(category.existing ? `«${category.name}» fantes allerede og er lagt til.` : `Kategorien «${category.name}» er opprettet.`, 'success')
        closeName()
        create.focus()
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })

    renderChips()
    return { get ids() { return [...selected] } }
  }

  // ---------- Kategorilisten: legg til, gi nytt navn, slett og endre rekkefølge (lagres med en gang) ----------
  function categoryManager(root, categories, onChange = () => {}) {
    const gamesText = (count) => `${count} spill`
    const list = el('ul', { class: 'category-list' })
    const nameInput = el('input', { class: 'ghost', maxlength: '100', placeholder: 'Navn på ny kategori', 'aria-label': 'Navn på ny kategori' })
    const form = el('form', { class: 'inline-form' }, nameInput, el('button', { type: 'submit', class: 'btn btn-small' }, icon('plus'), 'Legg til'))
    const sort = el('button', { type: 'button', class: 'btn btn-small btn-ghost' }, 'Sorter alfabetisk')
    root.replaceChildren(list, form, el('div', { class: 'category-tools' }, sort))

    function row(category) {
      const handle = el('button', { type: 'button', class: 'icon-btn drag-handle', title: 'Dra for å flytte, eller bruk piltastene', 'aria-label': `Flytt ${category.name}` }, icon('grip'))
      const dot = el('span', { class: 'menu-dot', style: `--h: ${hue(category.name)}` })
      const input = el('input', { type: 'text', maxlength: '100', 'aria-label': 'Navn på kategorien' })
      input.value = category.name
      const remove = el('button', { type: 'button', class: 'icon-btn danger', title: 'Slett kategorien', 'aria-label': `Slett ${category.name}` }, icon('trash'))
      const item = el('li', { class: 'category-row', dataset: { id: category.id } }, handle, dot, input, el('span', { class: 'category-count' }, gamesText(category.games)), remove)
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); input.blur() }
        if (event.key === 'Escape') { event.preventDefault(); input.value = category.name; input.blur() }
      })
      input.addEventListener('change', async () => {
        if (!input.value.trim() || input.value.trim() === category.name) { input.value = category.name; return }
        try {
          const result = await api('PUT', `/api/categories/${category.id}`, { name: input.value })
          category.name = result.name
          input.value = result.name
          dot.style.setProperty('--h', hue(result.name))
          handle.setAttribute('aria-label', `Flytt ${result.name}`)
          toast(`Kategorien heter nå «${result.name}»${category.games ? ` på ${gamesText(category.games)}` : ''}.`, 'success')
          onChange()
        } catch (problem) {
          input.value = category.name
          toast(problem.message, 'error')
        }
      })
      remove.addEventListener('click', async () => {
        const used = category.games ? ` Den fjernes fra ${gamesText(category.games)}.` : ''
        if (!confirm(`Slette kategorien «${category.name}»?${used}`)) return
        try {
          await api('DELETE', `/api/categories/${category.id}`)
          item.remove()
          toast(`«${category.name}» er slettet.`, 'success')
          onChange()
        } catch (problem) {
          toast(problem.message, 'error')
        }
      })
      return item
    }

    // Lagringene går etter hverandre, så den siste rekkefølgen alltid vinner.
    let saving = Promise.resolve()
    function saveOrder() {
      const ids = $$('.category-row', list).map((item) => Number(item.dataset.id))
      saving = saving.then(async () => {
        try {
          await api('PUT', '/api/categories/order', { ids })
          toast('Rekkefølgen er lagret.', 'success')
          onChange()
        } catch (problem) {
          toast(problem.message, 'error')
        }
      })
    }

    list.replaceChildren(...categories.map(row))
    const order = sortable(list, { items: '.category-row', handle: '.drag-handle', onChange: saveOrder })
    sort.addEventListener('click', () => {
      const byName = (a, b) => $('input', a).value.localeCompare($('input', b).value, 'nb', { sensitivity: 'base' })
      order.rearrange(() => list.append(...$$('.category-row', list).sort(byName)))
      saveOrder()
    })
    form.addEventListener('submit', async (event) => {
      event.preventDefault()
      if (!nameInput.value.trim()) { nameInput.focus(); return }
      try {
        const result = await api('POST', '/api/categories', { name: nameInput.value })
        if (result.existing) { toast(`«${result.name}» finnes allerede.`, 'error'); return }
        list.append(row({ id: result.id, name: result.name, games: 0 }))
        nameInput.value = ''
        toast(`Kategorien «${result.name}» er lagt til.`, 'success')
        onChange()
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })
  }

  // ---------- Forsiden: legg til spill ----------
  const addDialog = $('#add-dialog')
  if (addDialog) initAddDialog()

  function initAddDialog() {
    let steamId = ''
    let coverUrl = ''
    let links = []
    const categories = categoryPicker($('#add-categories'), JSON.parse($('#category-data').textContent), [], () => {})
    const title = $('#add-title')
    const error = $('#add-error')
    const submit = $('#add-submit')

    $('#add-game').addEventListener('click', () => addDialog.showModal())
    $$('[data-close]', addDialog).forEach((button) => button.addEventListener('click', () => addDialog.close()))

    function renderLinks() {
      const box = $('#add-links')
      box.replaceChildren(...links.map((link) =>
        el('span', { class: `link-pill store-${link.key}` }, icon(link.key), el('span', {}, link.label))))
    }

    $('#add-steam-fetch').addEventListener('click', async (event) => {
      const button = event.currentTarget
      error.hidden = true
      button.disabled = true
      try {
        const data = await api('POST', '/api/steam', { steam: $('#add-steam').value })
        title.value = data.title
        $('#add-description').value = data.description
        $('#add-developer').value = data.developer
        $('#add-developer-link').value = data.developer_link || ''
        steamId = data.steam_app_id
        coverUrl = data.cover_url
        links = data.store_links
        if (coverUrl) {
          $('#add-preview img').src = coverUrl
          $('#add-preview').hidden = false
        }
        renderLinks()
        const found = await api('POST', '/api/stores', { title: data.title, developer: data.developer })
        links = [...links, ...found.links.filter((link) => !links.some((known) => known.url === link.url))]
        renderLinks()
      } catch (problem) {
        error.textContent = problem.message
        error.hidden = false
      } finally {
        button.disabled = false
      }
    })

    $('#add-form').addEventListener('submit', async (event) => {
      event.preventDefault()
      error.hidden = true
      submit.disabled = true
      try {
        const result = await api('POST', '/api/games', {
          title: title.value,
          description: $('#add-description').value,
          developer: $('#add-developer').value,
          developer_link: $('#add-developer-link').value.trim(),
          steam_app_id: steamId,
          cover_url: coverUrl,
          store_links: links.map((link) => link.url),
          categories: categories.ids,
        })
        if (result.warning) flash(result.warning, 'error')
        location.href = `/${result.slug}?edit=1`
      } catch (problem) {
        error.textContent = problem.message
        error.hidden = false
        submit.disabled = false
      }
    })
  }

  const categoriesDialog = $('#categories-dialog')
  if (categoriesDialog) {
    let changed = false
    categoryManager($('#category-manager', categoriesDialog), JSON.parse($('#category-data').textContent), () => { changed = true })
    $('#edit-categories').addEventListener('click', () => categoriesDialog.showModal())
    $$('[data-close]', categoriesDialog).forEach((button) => button.addEventListener('click', () => categoriesDialog.close()))
    // Filteret og kortene viser kategoriene, så siden lastes på nytt når listen er endret.
    categoriesDialog.addEventListener('close', () => { if (changed) location.reload() })
  }

  const localize = $('#localize-covers')
  if (localize) {
    localize.addEventListener('click', async () => {
      localize.disabled = true
      toast('Laster ned omslagsbilder …')
      try {
        const result = await api('POST', '/api/covers/localize')
        flash(`${result.downloaded} omslagsbilde(r) lastet ned${result.failed ? `, ${result.failed} feilet` : ''}.${result.reason ? ` ${result.reason}` : ''}`, result.failed ? 'error' : 'success')
        location.reload()
      } catch (problem) {
        toast(problem.message, 'error')
        localize.disabled = false
      }
    })
  }

  // ---------- Skjul spill for besøkende ----------
  const visibilityText = (hidden) => (hidden ? 'Spillet er skjult for besøkende.' : 'Spillet er synlig for besøkende igjen.')

  $$('.card-eye').forEach((button) => {
    button.addEventListener('click', async () => {
      const card = button.closest('.game-card')
      const hidden = button.getAttribute('aria-pressed') !== 'true'
      button.disabled = true
      try {
        await api('PUT', `/api/games/${card.dataset.gameId}`, { hidden })
        card.classList.toggle('is-concealed', hidden)
        button.setAttribute('aria-pressed', String(hidden))
        button.title = hidden ? 'Skjult for besøkende. Klikk for å vise spillet.' : 'Synlig for besøkende. Klikk for å skjule spillet.'
        button.setAttribute('aria-label', `${hidden ? 'Vis' : 'Skjul'} ${$('.card-title', card).textContent}`)
        button.replaceChildren(icon(hidden ? 'eye-off' : 'eye'))
        toast(visibilityText(hidden), 'success')
      } catch (problem) {
        toast(problem.message, 'error')
      } finally {
        button.disabled = false
      }
    })
  })

  const visibility = $('#visibility-toggle')
  if (visibility) {
    visibility.addEventListener('click', async () => {
      const hidden = visibility.getAttribute('aria-pressed') !== 'true'
      visibility.disabled = true
      try {
        await api('PUT', `/api/games/${$('#game').dataset.gameId}`, { hidden })
        visibility.setAttribute('aria-pressed', String(hidden))
        visibility.replaceChildren(icon(hidden ? 'eye-off' : 'eye'), hidden ? 'Skjult' : 'Synlig')
        $('#hidden-notice').hidden = !hidden
        toast(visibilityText(hidden), 'success')
      } catch (problem) {
        toast(problem.message, 'error')
      } finally {
        visibility.disabled = false
      }
    })
  }

  // ---------- Innstillinger ----------
  if ($('#settings')) initSettings()

  function initSettings() {
    const data = JSON.parse($('#settings-data').textContent)
    const form = $('#settings-form')
    const navList = $('#nav-editor')
    let dirty = false
    const markDirty = () => { dirty = true }

    $('#site-title').value = data.site_title
    $('#hero-title').value = data.hero_title
    $('#hero-text').value = data.hero_text
    form.addEventListener('input', markDirty)
    window.addEventListener('beforeunload', (event) => { if (dirty) event.preventDefault() })

    // Logo
    const logoRemove = $('#logo-remove')
    function showLogo(url) {
      $('#logo-preview').replaceChildren(url ? el('img', { src: url, alt: '' }) : icon('gamepad'))
      $('.brand').firstElementChild.replaceWith(url ? el('img', { class: 'brand-logo', src: url, alt: '' }) : icon('gamepad'))
      $('link[rel="icon"]').href = url || '/assets/img/favicon.ico'
      logoRemove.hidden = !url
    }
    $('#logo-file').addEventListener('change', async (event) => {
      const [file] = event.target.files
      event.target.value = ''
      if (!file) return
      try {
        const result = await api('POST', '/api/settings/logo', file)
        showLogo(result.logo_url)
        toast('Logoen er oppdatert.', 'success')
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })
    logoRemove.addEventListener('click', async () => {
      try {
        await api('DELETE', '/api/settings/logo')
        showLogo('')
        toast('Standardikonet brukes igjen.', 'success')
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })

    // Meny: innebygde sider og egne lenker i valgfri rekkefølge
    function navRow(item) {
      const builtin = item.key !== 'link'
      const info = builtin ? data.builtins[item.key] : null
      const row = el('li', { class: 'nav-row', dataset: { key: item.key } })
      const label = el('input', {
        type: 'text', class: 'nav-label', maxlength: '40', 'aria-label': 'Navn i menyen', placeholder: builtin ? info.label : 'Navn',
      })
      label.value = item.label || ''
      let target
      let symbol
      const options = el('div', { class: 'nav-options' })
      if (builtin) {
        symbol = el('span', { class: 'nav-icon' }, icon(info.icon))
        target = el('span', { class: 'nav-target', title: info.href }, info.href)
        const visible = el('input', { type: 'checkbox', class: 'nav-visible' })
        visible.checked = !item.hidden
        row.classList.toggle('is-off', !visible.checked)
        visible.addEventListener('change', () => row.classList.toggle('is-off', !visible.checked))
        options.append(el('label', { class: 'nav-check', title: 'Vis siden i menyen' }, visible, 'Vis'))
      } else {
        // Egne lenker får et ikon man kan bla gjennom ved å klikke på det.
        row.dataset.icon = data.nav_icons.includes(item.icon) ? item.icon : data.nav_icons[0]
        symbol = el('button', { type: 'button', class: 'nav-icon nav-icon-pick', title: 'Klikk for å bytte ikon', 'aria-label': 'Bytt ikon' }, icon(row.dataset.icon))
        symbol.addEventListener('click', () => {
          const icons = data.nav_icons
          row.dataset.icon = icons[(icons.indexOf(row.dataset.icon) + 1) % icons.length]
          symbol.replaceChildren(icon(row.dataset.icon))
          markDirty()
        })
        // Ikke type=url: nettleseren avviser da lokale lenker som /side.
        target = el('input', { type: 'text', inputmode: 'url', class: 'nav-url', maxlength: '2000', placeholder: 'https://… eller /side', 'aria-label': 'Lenke' })
        target.value = item.url || ''
        const newTab = el('input', { type: 'checkbox', class: 'nav-new-tab' })
        newTab.checked = Boolean(item.new_tab)
        options.append(
          el('label', { class: 'nav-check', title: 'Åpne lenken i en ny fane' }, newTab, 'Ny fane'),
          el('button', { type: 'button', class: 'icon-btn danger nav-remove', 'aria-label': 'Fjern lenken', title: 'Fjern lenken' }, icon('trash')),
        )
      }
      const move = el('div', { class: 'nav-move' },
        el('button', { type: 'button', class: 'icon-btn nav-up', 'aria-label': 'Flytt opp', title: 'Flytt opp' }, icon('chevron-up')),
        el('button', { type: 'button', class: 'icon-btn nav-down', 'aria-label': 'Flytt ned', title: 'Flytt ned' }, icon('chevron-down')))
      row.append(symbol, label, target, options, move)
      return row
    }
    function refreshMoves() {
      const rows = $$('.nav-row', navList)
      rows.forEach((row, index) => {
        $('.nav-up', row).disabled = index === 0
        $('.nav-down', row).disabled = index === rows.length - 1
      })
    }
    navList.replaceChildren(...data.nav.map(navRow))
    refreshMoves()
    navList.addEventListener('click', (event) => {
      const button = event.target.closest('button')
      const row = button?.closest('.nav-row')
      if (!row) return
      if (button.classList.contains('nav-up') && row.previousElementSibling) row.previousElementSibling.before(row)
      else if (button.classList.contains('nav-down') && row.nextElementSibling) row.nextElementSibling.after(row)
      else if (button.classList.contains('nav-remove')) row.remove()
      else return
      markDirty()
      refreshMoves()
      if (row.isConnected && !button.disabled) button.focus()
    })
    $('#nav-add').addEventListener('click', () => {
      const row = navRow({ key: 'link', label: '', url: '', new_tab: false })
      navList.append(row)
      refreshMoves()
      markDirty()
      $('.nav-label', row).focus()
    })

    // Sider
    $$('.page-editor').forEach((box) => {
      const page = data.pages[box.dataset.page]
      const area = $('textarea', box)
      area.value = page.content
      $('[data-default]', box).addEventListener('click', () => {
        const current = area.value.trim()
        if (current && current !== page.default.trim() && !confirm('Erstatte teksten i feltet med standardteksten?')) return
        area.value = page.default
        markDirty()
      })
    })

    form.addEventListener('submit', async (event) => {
      event.preventDefault()
      const button = $('#settings-save')
      const body = {
        site_title: $('#site-title').value,
        hero_title: $('#hero-title').value,
        hero_text: $('#hero-text').value,
        nav: $$('.nav-row', navList).map((row) => (row.dataset.key === 'link'
          ? { key: 'link', label: $('.nav-label', row).value, url: $('.nav-url', row).value.trim(), new_tab: $('.nav-new-tab', row).checked, icon: row.dataset.icon }
          : { key: row.dataset.key, label: $('.nav-label', row).value, hidden: !$('.nav-visible', row).checked })),
      }
      $$('.page-editor').forEach((box) => { body[`${box.dataset.page}_content`] = $('textarea', box).value })
      button.disabled = true
      try {
        await api('PUT', '/api/settings', body)
        dirty = false
        flash('Innstillingene er lagret.', 'success')
        location.reload()
      } catch (problem) {
        toast(problem.message, 'error')
        button.disabled = false
      }
    })

    // Kategorier: endringer lagres med en gang
    categoryManager($('#category-manager'), data.categories)

    // Passord
    const passwordForm = $('#password-form')
    passwordForm.addEventListener('submit', async (event) => {
      event.preventDefault()
      const password = $('#password-new').value
      if (password !== $('#password-repeat').value) { toast('De nye passordene er ikke like.', 'error'); return }
      try {
        await api('POST', '/api/settings/password', { current: $('#password-current')?.value || '', password })
        flash('Passordet er lagret. Alle andre er logget ut.', 'success')
        location.reload()
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })
    $('#password-remove')?.addEventListener('click', async () => {
      const current = $('#password-current')
      if (!current.value) { toast('Skriv inn nåværende passord først.', 'error'); current.focus(); return }
      const question = passwordForm.dataset.env === 'true'
        ? 'Fjerne det lagrede passordet og bruke ADMIN_PASSWORD igjen?'
        : 'Fjerne det lagrede passordet? ADMIN_PASSWORD er ikke satt, så innloggingen blir slått av.'
      if (!confirm(question)) return
      try {
        await api('DELETE', '/api/settings/password', { current: current.value })
        flash('Det lagrede passordet er fjernet.', 'success')
        location.reload()
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })
  }

  // ---------- Spillsiden: rediger direkte på siden ----------
  const root = $('#game[data-game-id]')
  if (root) initEditor(root)

  function initEditor(page) {
    const data = JSON.parse($('#editor-data').textContent)
    const gameId = page.dataset.gameId
    const stores = data.stores
    const fields = $$('[data-field]', page)
    let steamAppId = data.game.steam_app_id
    let coverUrl = data.game.cover_url
    let coverChanged = false
    let dirty = false
    let uploading = 0
    // I redigeringsmodus lagres kategoriene sammen med resten; ellers lagres de med en gang.
    let categorySaves = Promise.resolve()
    const categories = categoryPicker($('#category-picker'), data.categories, data.game.categories.map((category) => category.id), () => {
      if (document.body.classList.contains('editing')) { markDirty(); return }
      const ids = categories.ids
      categorySaves = categorySaves.then(async () => {
        try {
          await api('PUT', `/api/games/${gameId}`, { categories: ids })
          toast('Kategoriene er lagret.', 'success')
        } catch (problem) {
          toast(problem.message, 'error')
        }
      })
    })

    const markDirty = () => { dirty = true }
    const storeInfo = (url) => {
      let host = ''
      try { host = new URL(url).hostname.toLowerCase().replace(/^www\./, '') } catch { /* ugyldig */ }
      const match = stores.find((store) => host === store.domain || host.endsWith(`.${store.domain}`))
      return match ? { key: match.key, label: match.label } : { key: 'link', label: host || url }
    }

    const autosize = (area) => { area.style.height = 'auto'; area.style.height = `${area.scrollHeight + 2}px` }
    const textareas = fields.filter((field) => field.tagName === 'TEXTAREA')
    textareas.forEach((area) => area.addEventListener('input', () => autosize(area)))
    fields.forEach((field) => field.addEventListener('input', markDirty))

    function setEditing(on) {
      document.body.classList.toggle('editing', on)
      $('#edit-toggle').hidden = on
      if (on) textareas.forEach(autosize)
    }

    $('#edit-toggle').addEventListener('click', () => setEditing(true))
    $('#cancel-edit').addEventListener('click', () => {
      if (uploading && !confirm('Opplastinger pågår og avbrytes hvis du forlater redigeringen. Fortsette?')) return
      if (dirty && !confirm('Du har ulagrede endringer. Forkaste dem?')) return
      dirty = false
      location.reload()
    })
    window.addEventListener('beforeunload', (event) => {
      if ((dirty || uploading) && document.body.classList.contains('editing')) event.preventDefault()
    })
    if (new URLSearchParams(location.search).has('edit')) setEditing(true)

    // Lagre
    $('#save-edit').addEventListener('click', async (event) => {
      const button = event.currentTarget
      const body = {}
      fields.forEach((field) => { body[field.dataset.field] = field.value })
      body.categories = categories.ids
      body.store_links = $$('#link-list .link-pill').map((pill) => pill.dataset.url)
      body.steam_app_id = steamAppId
      if (coverChanged) body.cover_url = coverUrl
      if (!body.title.trim()) { toast('Spillet må ha en tittel.', 'error'); return }
      if (uploading && !confirm('Opplastinger pågår. Lagre likevel?')) return
      button.disabled = true
      try {
        const result = await api('PUT', `/api/games/${gameId}`, body)
        dirty = false
        flash(result.warning || 'Endringene er lagret.', result.warning ? 'error' : 'success')
        location.href = `/${result.slug}`
      } catch (problem) {
        toast(problem.message, 'error')
        button.disabled = false
      }
    })

    $('#delete-game').addEventListener('click', async () => {
      const name = $('[data-field="title"]').value
      if (!confirm(`Slette «${name}» og alle tilhørende filer? Dette kan ikke angres.`)) return
      try {
        await api('DELETE', `/api/games/${gameId}`)
        dirty = false
        flash('Spillet er slettet.', 'success')
        location.href = '/'
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })

    // Omslagsbilde
    const coverImg = $('#cover-img')
    const coverPlaceholder = $('#cover-placeholder')
    function showCover(url) {
      if (url) coverImg.src = url
      coverImg.hidden = !url
      coverPlaceholder.hidden = Boolean(url)
    }
    $('#cover-url').addEventListener('change', (event) => {
      const value = event.target.value.trim()
      if (value && !isHttpUrl(value)) { toast('Bildelenken må starte med http:// eller https://.', 'error'); return }
      coverUrl = value
      coverChanged = true
      markDirty()
      showCover(value)
    })
    $('#cover-remove').addEventListener('click', () => {
      coverUrl = ''
      coverChanged = true
      $('#cover-url').value = ''
      markDirty()
      showCover('')
    })
    $('#cover-file').addEventListener('change', async (event) => {
      const [file] = event.target.files
      event.target.value = ''
      if (!file) return
      try {
        toast('Laster opp omslagsbilde …')
        const result = await uploadFile(file, 'cover', () => {})
        coverUrl = result.href
        coverChanged = false
        showCover(`${result.href}?v=${Date.now()}`)
        toast('Omslagsbildet er oppdatert.', 'success')
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })

    // Butikklenker (plus/minus)
    $('#link-list').addEventListener('click', (event) => {
      const remove = event.target.closest('.tag-remove')
      if (remove) { remove.closest('.link-pill').remove(); markDirty() }
    })

    function addLink(url) {
      const value = url.trim()
      if (!isHttpUrl(value)) { toast('Lenken må starte med http:// eller https://.', 'error'); return false }
      if ($$('#link-list .link-pill').some((pill) => pill.dataset.url === value)) return false
      const info = storeInfo(value)
      const remove = el('button', { type: 'button', class: 'tag-remove', 'aria-label': `Fjern ${info.label}` }, icon('minus'))
      const pill = el('span', { class: `link-pill store-${info.key}`, dataset: { url: value } }, icon(info.key), el('span', {}, info.label), remove)
      $('#link-list .tag-add').before(pill)
      markDirty()
      return true
    }

    const linkButton = $('#link-add-btn')
    const linkInput = $('#link-input')
    const closeLinkInput = () => { linkInput.value = ''; linkInput.hidden = true; linkButton.hidden = false }
    linkButton.addEventListener('click', () => { linkButton.hidden = true; linkInput.hidden = false; linkInput.focus() })
    linkInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault()
        if (addLink(linkInput.value)) linkInput.value = ''
      } else if (event.key === 'Escape') {
        closeLinkInput()
      }
    })
    linkInput.addEventListener('blur', () => {
      if (linkInput.value.trim()) addLink(linkInput.value)
      closeLinkInput()
    })

    async function findStores(title, developer) {
      const found = await api('POST', '/api/stores', { title, developer })
      return found.links.filter((link) => addLink(link.url))
    }

    $('#stores-find').addEventListener('click', async (event) => {
      const button = event.currentTarget
      const title = $('[data-field="title"]').value.trim()
      if (!title) { toast('Skriv inn en tittel først.', 'error'); return }
      button.disabled = true
      toast('Leter etter spillet hos GOG, itch.io og Humble Bundle …')
      try {
        const added = await findStores(title, $('[data-field="developer"]').value)
        toast(added.length ? `La til ${added.map((link) => link.label).join(', ')}.` : 'Fant ingen nye butikklenker.', added.length ? 'success' : '')
      } catch (problem) {
        toast(problem.message, 'error')
      } finally {
        button.disabled = false
      }
    })

    // Steam
    const steamPop = $('#steam-pop')
    $('#steam-open').addEventListener('click', () => {
      steamPop.hidden = !steamPop.hidden
      if (!steamPop.hidden) $('#steam-input').focus()
    })
    $('#steam-input').addEventListener('keydown', (event) => {
      if (event.key === 'Enter') $('#steam-fetch').click()
    })
    $('#steam-fetch').addEventListener('click', async (event) => {
      const button = event.currentTarget
      button.disabled = true
      try {
        const steam = await api('POST', '/api/steam', { steam: $('#steam-input').value })
        const targets = { title: steam.title, description: steam.description, developer: steam.developer, developer_link: steam.developer_link }
        const overwrites = Object.entries(targets).some(([key, value]) => {
          const current = $(`[data-field="${key}"]`).value.trim()
          return current && value && current !== value
        })
        if (overwrites && !confirm('Overskrive tittel, beskrivelse, utvikler og nettsted med informasjonen fra Steam?')) return
        Object.entries(targets).forEach(([key, value]) => {
          const field = $(`[data-field="${key}"]`)
          if (value) field.value = value
          if (field.tagName === 'TEXTAREA') autosize(field)
        })
        if (steam.cover_url) {
          coverUrl = steam.cover_url
          coverChanged = true
          $('#cover-url').value = steam.cover_url
          showCover(steam.cover_url)
        }
        steamAppId = steam.steam_app_id
        steam.store_links.forEach((link) => addLink(link.url))
        markDirty()
        steamPop.hidden = true
        toast('Hentet informasjon fra Steam. Husk å lagre.', 'success')
        try {
          const added = await findStores(steam.title, steam.developer)
          if (added.length) toast(`La også til ${added.map((link) => link.label).join(', ')}.`, 'success')
        } catch { /* butikksøk er valgfritt */ }
      } catch (problem) {
        toast(problem.message, 'error')
      } finally {
        button.disabled = false
      }
    })

    // Filer
    function uploadFile(file, platform, onProgress) {
      return new Promise((resolve, reject) => {
        const request = new XMLHttpRequest()
        request.open('POST', `/api/games/${gameId}/files`)
        request.setRequestHeader('Content-Type', 'application/octet-stream')
        request.setRequestHeader('X-Platform', platform)
        request.setRequestHeader('X-File-Name', encodeURIComponent(file.name))
        request.upload.onprogress = (event) => { if (event.lengthComputable) onProgress(event.loaded, event.total) }
        request.onload = () => {
          let body = {}
          try { body = JSON.parse(request.responseText) } catch { /* ikke JSON */ }
          if (request.status === 401) location.assign(`/login?next=${encodeURIComponent(location.pathname)}`)
          if (request.status >= 200 && request.status < 300) resolve(body)
          else reject(new Error(body.error || `Opplastingen feilet (${request.status}).`))
        }
        request.onerror = () => reject(new Error('Nettverksfeil under opplasting. Sjekk at proxyen tillater store filer.'))
        request.send(file)
      })
    }

    function fileItem(file) {
      const external = file.url ? { target: '_blank', rel: 'noopener noreferrer' } : {}
      const link = el('a', { class: 'download-btn', href: file.href, ...external }, icon(file.url ? 'external' : 'download'), el('span', { class: 'file-name', title: file.name }, file.name))
      if (file.size_text) link.append(el('span', { class: 'file-size' }, file.size_text))
      const remove = el('button', { type: 'button', class: 'icon-btn danger edit-only file-delete', 'aria-label': `Slett ${file.name}` }, icon('trash'))
      return el('li', { dataset: { fileId: file.id } }, link, remove)
    }

    $$('.dropzone', page).forEach((zone) => {
      const block = zone.closest('.platform-block')
      const input = $('input', zone)
      const queue = []
      let running = false

      async function drain() {
        if (running) return
        running = true
        while (queue.length) {
          const file = queue.shift()
          const bar = el('span')
          const label = el('span', {}, `${file.name} · venter …`)
          const row = el('div', { class: 'upload-item' }, label, el('div', { class: 'upload-bar' }, bar))
          $('.uploads', block).appendChild(row)
          uploading++
          try {
            const result = await uploadFile(file, zone.dataset.platform, (loaded, total) => {
              bar.style.width = `${(loaded / total) * 100}%`
              label.textContent = `${file.name} · ${formatSize(loaded)} av ${formatSize(total)}`
            })
            row.remove()
            block.classList.remove('is-empty')
            $('.file-list', block).appendChild(fileItem(result))
          } catch (problem) {
            row.classList.add('failed')
            label.textContent = `${file.name} · ${problem.message}`
            bar.style.width = '0'
            setTimeout(() => row.remove(), 12000)
          } finally {
            uploading--
          }
        }
        running = false
      }

      const enqueue = (files) => { queue.push(...files); drain() }
      input.addEventListener('change', () => { enqueue([...input.files]); input.value = '' })
      zone.addEventListener('dragover', (event) => { event.preventDefault(); zone.classList.add('drag') })
      zone.addEventListener('dragleave', () => zone.classList.remove('drag'))
      zone.addEventListener('drop', (event) => {
        event.preventDefault()
        zone.classList.remove('drag')
        enqueue([...event.dataTransfer.files])
      })
    })

    // Lenke til en fil som ligger et annet sted, i stedet for å laste den opp
    $$('.file-link', page).forEach((form) => {
      const block = form.closest('.platform-block')
      const input = $('input', form)
      const button = $('button', form)
      form.addEventListener('submit', async (event) => {
        event.preventDefault()
        if (!input.value.trim()) { input.focus(); return }
        button.disabled = true
        try {
          const result = await api('POST', `/api/games/${gameId}/file-links`, { platform: form.dataset.platform, url: input.value })
          input.value = ''
          block.classList.remove('is-empty')
          $('.file-list', block).appendChild(fileItem(result))
          toast('Lenken er lagt til.', 'success')
        } catch (problem) {
          toast(problem.message, 'error')
        } finally {
          button.disabled = false
        }
      })
    })

    page.addEventListener('click', async (event) => {
      const remove = event.target.closest('.file-delete')
      if (!remove) return
      const item = remove.closest('li')
      const name = $('.file-name', item).textContent
      if (!confirm(`Slette filen «${name}»?`)) return
      try {
        await api('DELETE', `/api/files/${item.dataset.fileId}`)
        item.remove()
        toast('Filen er slettet.', 'success')
      } catch (problem) {
        toast(problem.message, 'error')
      }
    })
  }
})()
