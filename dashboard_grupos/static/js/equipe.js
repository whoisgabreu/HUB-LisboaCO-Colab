/* Filtro instantâneo por nome ou LID na tela Equipe & Clientes.
   Ignora acentos e maiúsculas. Filtra as tabelas de autores (equipe e clientes)
   pelo nome e a de não mapeados por nome ou LID. */
(function () {
  function normaliza(s) {
    return (s || '').toString().normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  const input = document.getElementById('equipeBusca');
  if (input) {
    const tabelas = [
      { id: 'tblEquipe', match: [0] },
      { id: 'tblClientes', match: [0] },
      { id: 'tblNaoMapeados', match: [0, 1] }
    ];

    const aplicar = function () {
      const q = normaliza(input.value);
      tabelas.forEach(function (cfg) {
        const tabela = document.getElementById(cfg.id);
        if (!tabela) return;
        const tbody = tabela.tBodies[0];
        const rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'))
          .filter(function (tr) {
            return !tr.classList.contains('dg-empty') && !tr.classList.contains('dg-filter-empty');
          });

        let visiveis = 0;
        rows.forEach(function (tr) {
          const casa = !q || cfg.match.some(function (i) {
            const td = tr.cells[i];
            return td && normaliza(td.textContent).indexOf(q) !== -1;
          });
          tr.classList.toggle('d-none', !casa);
          if (casa) visiveis++;
        });

        const vazio = tbody.querySelector('.dg-filter-empty');
        if (vazio) vazio.classList.toggle('d-none', !(q && rows.length > 0 && visiveis === 0));
      });
    };

    input.addEventListener('input', aplicar);
  }

  (function () {
    const KEY = 'dg_equipe_tab';
    const tabEls = document.querySelectorAll('#equipeTabs .nav-link');
    if (!tabEls.length) return;
    const saved = localStorage.getItem(KEY);
    if (saved) {
      const alvo = document.querySelector('#equipeTabs .nav-link[data-bs-target="' + saved + '"]');
      if (alvo) bootstrap.Tab.getOrCreateInstance(alvo).show();
    }
    tabEls.forEach(function (el) {
      el.addEventListener('shown.bs.tab', function (e) {
        localStorage.setItem(KEY, e.target.getAttribute('data-bs-target'));
      });
    });
  })();
})();
