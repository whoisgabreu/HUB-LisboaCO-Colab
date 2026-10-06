/* Persistência da aba selecionada na tela Grupos & Remetentes. */
(function () {
  const KEY = 'dg_grupos_tab';
  const tabEls = document.querySelectorAll('#gruposTabs .nav-link');
  if (!tabEls.length) return;
  const saved = localStorage.getItem(KEY);
  if (saved) {
    const alvo = document.querySelector('#gruposTabs .nav-link[data-bs-target="' + saved + '"]');
    if (alvo) bootstrap.Tab.getOrCreateInstance(alvo).show();
  }
  tabEls.forEach(function (el) {
    el.addEventListener('shown.bs.tab', function (e) {
      localStorage.setItem(KEY, e.target.getAttribute('data-bs-target'));
    });
  });
})();
