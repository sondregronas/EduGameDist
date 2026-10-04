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
    const item = el('div', { class: `toast ${type}` }, message)
    box.appendChild(item)
    setTimeout(() => item.remove(), type === 'error' ? 8000 : 4500)
  }

  function flash(message, type) {
    sessionStorage.setItem('flash', JSON.stringify({ message, type }))
  }

  async function api(method, url, body) {
    const response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
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

  // ---------- Forsiden: legg til spill ----------
  const addDialog = $('#add-dialog')
  if (addDialog) initAddDialog()

  function initAddDialog() {
    let steamId = ''
    let coverUrl = ''
    let links = []
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
      body.categories = $$('#tag-list .tag-editable').map((tag) => tag.dataset.value)
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

    // Kategorier og butikklenker (plus/minus)
    $('#tag-list').addEventListener('click', (event) => {
      const remove = event.target.closest('.tag-remove')
      if (remove) { remove.closest('.tag-editable').remove(); markDirty() }
    })
    $('#link-list').addEventListener('click', (event) => {
      const remove = event.target.closest('.tag-remove')
      if (remove) { remove.closest('.link-pill').remove(); markDirty() }
    })

    function addCategory(name) {
      const value = name.trim()
      if (!value) return false
      if ($$('#tag-list .tag-editable').some((tag) => tag.dataset.value.toLowerCase() === value.toLowerCase())) return false
      const remove = el('button', { type: 'button', class: 'tag-remove', 'aria-label': `Fjern ${value}` }, icon('minus'))
      const chip = el('span', { class: 'tag tag-editable', style: `--h: ${hue(value)}`, dataset: { value } }, el('span', {}, value), remove)
      $('#tag-list .tag-add').before(chip)
      markDirty()
      return true
    }

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

    function inlineAdder(buttonId, inputId, onAdd, menu) {
      const button = $(buttonId)
      const input = $(inputId)
      const open = () => { button.hidden = true; input.hidden = false; input.focus(); menu?.render() }
      const close = () => { input.value = ''; input.hidden = true; button.hidden = false; menu?.hide() }
      button.addEventListener('click', open)
      input.addEventListener('keydown', (event) => {
        if (menu?.key(event)) return
        if (event.key === 'Enter' || (event.key === ',' && input.type !== 'url')) {
          event.preventDefault()
          if (onAdd(input.value)) { input.value = ''; menu?.render() }
        } else if (event.key === 'Escape') {
          close()
        }
      })
      input.addEventListener('input', () => menu?.render())
      input.addEventListener('blur', () => {
        if (input.value.trim()) onAdd(input.value)
        close()
      })
    }

    // Egendefinert nedtrekksmeny for kategorier
    function categoryMenu(input, menuEl, known) {
      let options = []
      let active = -1
      const used = () => $$('#tag-list .tag-editable').map((tag) => tag.dataset.value.toLowerCase())
      const hide = () => { menuEl.hidden = true; input.setAttribute('aria-expanded', 'false'); active = -1 }
      function highlight(index) {
        active = index
        $$('.tag-option', menuEl).forEach((node, i) => node.classList.toggle('active', i === index))
        $$('.tag-option', menuEl)[index]?.scrollIntoView({ block: 'nearest' })
      }
      function pick(value) {
        if (addCategory(value)) input.value = ''
        render()
        input.focus()
      }
      function render() {
        const query = input.value.trim().toLowerCase()
        const taken = used()
        options = known
          .filter((name) => !taken.includes(name.toLowerCase()) && name.toLowerCase().includes(query))
          .map((name) => ({ name, create: false }))
        if (query && !known.some((name) => name.toLowerCase() === query) && !taken.includes(query)) {
          options.push({ name: input.value.trim(), create: true })
        }
        menuEl.replaceChildren()
        if (!options.length) { hide(); return }
        if (options.some((option) => !option.create)) menuEl.append(el('div', { class: 'tag-menu-label' }, 'Eksisterende kategorier'))
        options.forEach((option, index) => {
          const node = el('button', {
            type: 'button', role: 'option', class: `tag-option${option.create ? ' create' : ''}`, style: `--h: ${hue(option.name)}`,
          }, option.create ? `Opprett «${option.name}»` : option.name)
          node.addEventListener('mouseenter', () => highlight(index))
          node.addEventListener('click', () => pick(option.name))
          menuEl.append(node)
        })
        menuEl.hidden = false
        input.setAttribute('aria-expanded', 'true')
        active = -1
      }
      function key(event) {
        if (menuEl.hidden || !options.length) return false
        if (event.key === 'ArrowDown') { event.preventDefault(); highlight((active + 1) % options.length); return true }
        if (event.key === 'ArrowUp') { event.preventDefault(); highlight((active - 1 + options.length) % options.length); return true }
        if (event.key === 'Enter' && active >= 0) { event.preventDefault(); pick(options[active].name); return true }
        return false
      }
      menuEl.addEventListener('mousedown', (event) => event.preventDefault())
      return { render, hide, key }
    }
    inlineAdder('#tag-add-btn', '#tag-input', addCategory, categoryMenu($('#tag-input'), $('#tag-menu'), data.categories || []))
    inlineAdder('#link-add-btn', '#link-input', addLink)

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
      const link = el('a', { class: 'download-btn', href: file.href }, icon('download'), el('span', { class: 'file-name' }, file.name))
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
