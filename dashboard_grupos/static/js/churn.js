/* Busca instantânea por nome do cliente na tela de Churn.
   Ignora acentos e maiúsculas e integra com a paginação (table._dgPag). */
(function () {
  function normaliza(s) {
    return (s || '').toString().normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  const input = document.getElementById('churnBusca');
  const table = document.getElementById('tblChurn');
  if (!input || !table) return;

  const pag = table._dgPag;

  function aplicar() {
    const q = normaliza(input.value);
    if (pag) {
      pag.setFilter(q ? function (tr) {
        return normaliza(tr.cells[0].textContent).indexOf(q) !== -1;
      } : null);
      pag.reset();
      pag.refresh();
    }
  }

  input.addEventListener('input', aplicar);
})();
