let tcBtn = document.getElementById('tc-link')
let tcModal = document.getElementById('tc-modal')
let closeBtn = document.getElementsByClassName('close-modal')[0]

// bind tcBtn on click
tcBtn.addEventListener('click', () => {
    tcModal.classList.toggle('hidden')
    window.scrollTo(0, 0)
});

// bind closeBtn on click
closeBtn.addEventListener('click', () => {
    tcModal.classList.toggle('hidden')
});

// bind window on click
window.addEventListener('click', (e) => {
    if (e.target === tcModal) {
        tcModal.classList.toggle('hidden')
    }
});

// bind window on keydown (esc)
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !tcModal.classList.contains('hidden')) {
        tcModal.classList.toggle('hidden')
    }
});