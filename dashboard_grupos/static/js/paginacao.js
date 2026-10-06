/* Paginação client-side reutilizável.
   Auto-inicializa toda <table data-paginate>.
   Tamanho de página global (20/50/100) persistido em localStorage.
   Expõe table._dgPag = { reset, refresh, setSize } para integração (ex.: ordenação). */
(function () {
  const SIZE_KEY = 'dg_page_size';
  const SIZES = [20, 50, 100];
  let tamanho = parseInt(localStorage.getItem(SIZE_KEY), 10);
  if (SIZES.indexOf(tamanho) === -1) tamanho = 20;

  const instancias = [];

  function numerosPagina(total, atual) {
    const out = [];
    if (total <= 7) {
      for (let i = 1; i <= total; i++) out.push(i);
      return out;
    }
    out.push(1);
    if (atual > 4) out.push('...');
    for (let i = Math.max(2, atual - 1); i <= Math.min(total - 1, atual + 1); i++) out.push(i);
    if (atual < total - 3) out.push('...');
    out.push(total);
    return out;
  }

  function initPaginacao(table) {
    const tbody = table.tBodies[0];
    if (!tbody) return;
    const wrap = table.closest('.table-responsive') || table.parentElement;

    const header = document.createElement('div');
    header.className = 'd-flex justify-content-end align-items-center mb-2';
    header.innerHTML =
      '<label class="text-muted small mb-0 me-2">Mostrar</label>' +
      '<select class="form-select form-select-sm dg-page-size" style="width:auto"></select>' +
      '<span class="text-muted small ms-2">por página</span>';
    const select = header.querySelector('select');
    SIZES.forEach(function (s) {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      select.appendChild(opt);
    });
    select.value = String(tamanho);
    wrap.parentNode.insertBefore(header, wrap);

    const footer = document.createElement('div');
    footer.className = 'd-flex justify-content-between align-items-center flex-wrap gap-2 mt-2';
    footer.innerHTML =
      '<span class="text-muted small dg-page-info"></span>' +
      '<nav><ul class="pagination pagination-sm mb-0"></ul></nav>';
    const info = footer.querySelector('.dg-page-info');
    const ul = footer.querySelector('.pagination');
    wrap.parentNode.insertBefore(footer, wrap.nextSibling);

    let page = 1;
    let filtro = null;

    const inst = {
      select: select,
      setSize: function (s) { select.value = String(s); },
      reset: function () { page = 1; },
      setFilter: function (fn) { filtro = fn || null; },
      refresh: function () { render(); }
    };
    table._dgPag = inst;
    instancias.push(inst);

    function linhas() {
      return Array.prototype.slice.call(tbody.querySelectorAll('tr'))
        .filter(function (tr) {
          return !tr.classList.contains('dg-empty') && (!filtro || filtro(tr));
        });
    }

    function render() {
      const rows = linhas();
      const total = rows.length;
      const size = parseInt(select.value, 10) || tamanho;
      const pages = Math.max(1, Math.ceil(total / size));
      if (page > pages) page = pages;
      if (page < 1) page = 1;

      rows.forEach(function (tr, i) {
        tr.classList.toggle('d-none', i < (page - 1) * size || i >= page * size);
      });

      info.textContent = total === 0
        ? 'Nenhum resultado.'
        : 'Mostrando ' + ((page - 1) * size + 1) + '–' + Math.min(page * size, total) + ' de ' + total;

      ul.innerHTML = '';
      if (pages <= 1) return;

      function item(label, target, opts) {
        opts = opts || {};
        const li = document.createElement('li');
        li.className = 'page-item' + (opts.disabled ? ' disabled' : '') + (opts.active ? ' active' : '');
        const el = document.createElement(opts.disabled ? 'span' : 'a');
        el.className = 'page-link';
        el.textContent = label;
        if (!opts.disabled) {
          el.href = '#';
          el.addEventListener('click', function (e) {
            e.preventDefault();
            page = target;
            render();
          });
        }
        li.appendChild(el);
        ul.appendChild(li);
      }

      item('Anterior', page - 1, { disabled: page <= 1 });
      numerosPagina(pages, page).forEach(function (n) {
        if (n === '...') item('…', 0, { disabled: true });
        else item(String(n), n, { active: n === page });
      });
      item('Próxima', page + 1, { disabled: page >= pages });
    }

    select.addEventListener('change', function () {
      tamanho = parseInt(select.value, 10) || 20;
      localStorage.setItem(SIZE_KEY, String(tamanho));
      instancias.forEach(function (o) {
        o.setSize(tamanho);
        o.reset();
        o.refresh();
      });
    });

    render();
  }

  document.querySelectorAll('table[data-paginate]').forEach(initPaginacao);
})();
