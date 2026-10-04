// Tema: mørkt, blått (standard) eller lyst. Lastes i <head>, slik at valget gjelder før siden tegnes.
(() => {
  const root = document.documentElement
  let theme = 'blue'
  try { theme = localStorage.getItem('theme') || theme } catch { /* lagring er blokkert */ }
  root.dataset.theme = ['dark', 'blue', 'light'].includes(theme) ? theme : 'blue'

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.theme-switch input').forEach((input) => {
      input.checked = input.value === root.dataset.theme
      input.addEventListener('change', () => {
        root.dataset.theme = input.value
        try { localStorage.setItem('theme', input.value) } catch { /* lagring er blokkert */ }
      })
    })
  })
})()
