// Mørkt eller lyst tema. Uten eget valg følger siden systemets innstilling, og er mørk hvis den er ukjent.
// Lastes i <head>, slik at riktig tema brukes før siden tegnes.
(() => {
  const root = document.documentElement
  const system = matchMedia('(prefers-color-scheme: light)')
  let chosen = null
  try { chosen = localStorage.getItem('theme') } catch { /* lagring er blokkert */ }

  const current = () => (chosen || (system.matches ? 'light' : 'dark')) === 'light' ? 'light' : 'dark'
  const inputs = () => document.querySelectorAll('.theme-switch input')
  function apply() {
    root.dataset.theme = current()
    inputs().forEach((input) => { input.checked = input.value === root.dataset.theme })
  }
  apply()
  system.addEventListener('change', apply)

  document.addEventListener('DOMContentLoaded', () => {
    apply()
    inputs().forEach((input) => input.addEventListener('change', () => {
      chosen = input.value
      try { localStorage.setItem('theme', chosen) } catch { /* lagring er blokkert */ }
      apply()
    }))
  })
})()
