/* Combobox de busca para filtros (busca por nome, sem acentos). */
(function () {
  function normaliza(s) {
    return (s || '').toString().normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function initCombo(root) {
    const input = root.querySelector('.dg-combo-input');
    const hidden = root.querySelector('input[type="hidden"]');
    const list = root.querySelector('.dg-combo-list');
    if (!input || !hidden || !list) return;

    const itens = Array.prototype.slice.call(list.querySelectorAll('li'));
    let ativo = -1;
    let visiveis = [];

    function abrir() {
      list.classList.add('dg-combo-open');
      input.setAttribute('aria-expanded', 'true');
    }

    function fechar() {
      list.classList.remove('dg-combo-open');
      input.setAttribute('aria-expanded', 'false');
      ativo = -1;
    }

    function destaca() {
      visiveis.forEach(function (li, i) {
        li.classList.toggle('dg-combo-active', i === ativo);
      });
      if (ativo >= 0 && visiveis[ativo]) {
        visiveis[ativo].scrollIntoView({ block: 'nearest' });
      }
    }

    function filtra() {
      const q = normaliza(input.value);
      visiveis = [];
      itens.forEach(function (li) {
        const casa = !q || normaliza(li.dataset.value).indexOf(q) !== -1;
        li.classList.toggle('d-none', !casa);
        if (casa) visiveis.push(li);
      });
      ativo = visiveis.length ? 0 : -1;
      destaca();
    }

    function selecionar(li) {
      if (!li) return;
      input.value = li.dataset.value;
      hidden.value = li.dataset.value;
      fechar();
    }

    input.addEventListener('focus', function () {
      filtra();
      abrir();
    });

    input.addEventListener('input', function () {
      hidden.value = '';
      filtra();
      abrir();
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (!list.classList.contains('dg-combo-open')) { filtra(); abrir(); }
        if (visiveis.length) { ativo = (ativo + 1) % visiveis.length; destaca(); }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (visiveis.length) { ativo = (ativo - 1 + visiveis.length) % visiveis.length; destaca(); }
      } else if (e.key === 'Enter') {
        if (list.classList.contains('dg-combo-open') && ativo >= 0) {
          e.preventDefault();
          selecionar(visiveis[ativo]);
        }
      } else if (e.key === 'Escape') {
        fechar();
      }
    });

    list.addEventListener('mousedown', function (e) {
      e.preventDefault();
    });

    list.addEventListener('click', function (e) {
      const li = e.target.closest('li');
      if (li) selecionar(li);
    });

    input.addEventListener('blur', function () {
      setTimeout(function () {
        if (hidden.value === '') {
          const q = normaliza(input.value);
          const casam = q ? itens.filter(function (li) {
            return normaliza(li.dataset.value).indexOf(q) !== -1;
          }) : [];
          const exato = casam.find(function (li) { return normaliza(li.dataset.value) === q; });
          if (exato) {
            input.value = exato.dataset.value;
            hidden.value = exato.dataset.value;
          } else if (casam.length === 1) {
            input.value = casam[0].dataset.value;
            hidden.value = casam[0].dataset.value;
          } else {
            input.value = '';
          }
        }
        fechar();
      }, 120);
    });
  }

  document.querySelectorAll('[data-combo]').forEach(initCombo);
})();
