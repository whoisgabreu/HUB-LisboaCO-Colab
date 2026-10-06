const TOOLTIP = {
  backgroundColor: '#08172D',
  padding: 10,
  cornerRadius: 8,
  titleFont: { weight: '600' }
};

function novoGrafico(id, config) {
  const el = document.getElementById(id);
  if (el && window[id + '_chart']) window[id + '_chart'].destroy();
  if (el) window[id + '_chart'] = new Chart(el, config);
}

const dados = (typeof statusData !== 'undefined' ? statusData : [])
  .filter(function (x) { return x.dias_ambos !== null && x.dias_ambos !== undefined; });

const corPorStatus = {
  inativo: '#D61616',
  semi_cliente: '#D99000',
  semi_equipe: '#D99000',
  ativo: '#16A36A',
  nunca: '#94A7C4'
};

novoGrafico('chartInativos', {
  type: 'bar',
  data: {
    labels: dados.map(function (x) { return x.nome; }),
    datasets: [{
      label: 'Dias sem interação',
      data: dados.map(function (x) { return x.dias_ambos; }),
      backgroundColor: dados.map(function (x) { return corPorStatus[x.status] || '#94A7C4'; }),
      borderRadius: 8
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: { tooltip: TOOLTIP },
    scales: { x: { min: 0 } }
  }
});

/* Cards de status → modal com a lista de grupos da categoria */
const STATUS_LABEL = {
  nunca: 'Nunca ativos',
  inativo: 'Inativos',
  semi_cliente: 'Semi · sem cliente',
  semi_equipe: 'Semi · sem equipe'
};

document.querySelectorAll('[data-status-modal]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    const alvo = btn.getAttribute('data-status-modal');
    const tabela = document.getElementById('tblStatus');
    const titulo = document.getElementById('statusGruposTitulo');
    const corpo = document.getElementById('statusGruposCorpo');
    if (!tabela || !titulo || !corpo) return;

    const rows = tabela.querySelectorAll('tbody tr[data-status="' + alvo + '"]');
    titulo.textContent = (STATUS_LABEL[alvo] || alvo) + ' (' + rows.length + ')';

    if (!rows.length) {
      corpo.innerHTML = '<p class="text-muted mb-0">Nenhum grupo nesta categoria.</p>';
    } else {
      const ths = Array.prototype.slice.call(tabela.querySelectorAll('thead th'))
        .map(function (th) { return '<th>' + th.innerHTML + '</th>'; }).join('');
      const trs = Array.prototype.map.call(rows, function (tr) {
        return '<tr>' + tr.innerHTML + '</tr>';
      }).join('');
      corpo.innerHTML = '<div class="table-responsive">' +
        '<table class="table table-sm table-hover align-middle">' +
        '<thead><tr>' + ths + '</tr></thead>' +
        '<tbody>' + trs + '</tbody></table></div>';
      corpo.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el, { trigger: 'hover focus' });
      });
    }

    new bootstrap.Modal(document.getElementById('statusGruposModal')).show();
  });
});