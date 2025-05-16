document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll('.md .math')
    .forEach((/** @type {HTMLSpanElement} */ el) => {
      katex.render(el.innerText, el)
    })
})
