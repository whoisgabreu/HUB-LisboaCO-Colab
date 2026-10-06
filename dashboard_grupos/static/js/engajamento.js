const PALETA = ["#D61616", "#2563EB", "#16A36A", "#D99000", "#7c3aed", "#0891b2", "#64748B", "#94A7C4", "#DB2777", "#059669", "#9333ea", "#e11d48", "#475569", "#94a3b8", "#cbd5e1"];

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

novoGrafico('chartPapel', {
  type: 'bar',
  data: {
    labels: papel.map(x => x[0]),
    datasets: [{ label: 'Mensagens', data: papel.map(x => x[1]), backgroundColor: PALETA, borderRadius: 8 }]
  },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: TOOLTIP } }
});

novoGrafico('chartParticipacao', {
  type: 'doughnut',
  data: {
    labels: participacaoLabels,
    datasets: [{
      data: participacao,
      backgroundColor: PALETA,
      borderWidth: 2,
      borderColor: 'transparent'
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '62%',
    plugins: {
      legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } },
      tooltip: Object.assign({}, TOOLTIP, {
        callbacks: {
          label: function (ctx) { return ' ' + ctx.label + ': ' + ctx.parsed + '%'; }
        }
      })
    }
  }
});

novoGrafico('chartTopClientes', {
  type: 'bar',
  data: {
    labels: topClientes.map(x => x.nome),
    datasets: [{ label: 'Mensagens', data: topClientes.map(x => x.msgs), backgroundColor: PALETA, borderRadius: 8 }]
  },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: TOOLTIP } }
});

(function () {
  const KEY = 'dg_engajamento_tab';
  const tabEls = document.querySelectorAll('#engajamentoTabs .nav-link');
  if (!tabEls.length) return;
  const saved = localStorage.getItem(KEY);
  if (saved) {
    const alvo = document.querySelector('#engajamentoTabs .nav-link[data-bs-target="' + saved + '"]');
    if (alvo) bootstrap.Tab.getOrCreateInstance(alvo).show();
  }
  tabEls.forEach(function (el) {
    el.addEventListener('shown.bs.tab', function (e) {
      localStorage.setItem(KEY, e.target.getAttribute('data-bs-target'));
    });
  });
})();

/* Card "Clientes inativos" → modal com a lista */
document.querySelectorAll('[data-status-modal="inativos"]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    const tabela = document.getElementById('tblEngInativos');
    const titulo = document.getElementById('clientesInativosTitulo');
    const corpo = document.getElementById('clientesInativosCorpo');
    if (!tabela || !titulo || !corpo) return;

    const rows = Array.prototype.slice.call(tabela.querySelectorAll('tbody tr'))
      .filter(function (tr) { return !tr.classList.contains('dg-empty'); });
    titulo.textContent = 'Clientes inativos (' + rows.length + ')';

    if (!rows.length) {
      corpo.innerHTML = '<p class="text-muted mb-0">Nenhum cliente inativo detectado.</p>';
    } else {
      const ths = Array.prototype.slice.call(tabela.querySelectorAll('thead th'))
        .map(function (th) { return '<th>' + th.innerHTML + '</th>'; }).join('');
      const trs = rows.map(function (tr) { return '<tr>' + tr.innerHTML + '</tr>'; }).join('');
      corpo.innerHTML = '<div class="table-responsive">' +
        '<table class="table table-sm table-hover align-middle">' +
        '<thead><tr>' + ths + '</tr></thead>' +
        '<tbody>' + trs + '</tbody></table></div>';
      corpo.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el, { trigger: 'hover focus' });
      });
    }

    new bootstrap.Modal(document.getElementById('clientesInativosModal')).show();
  });
});

/* Card "Clientes em risco" → modal com a lista (a partir do JSON) */
(function () {
  const btn = document.querySelector('[data-status-modal="risco"]');
  const dados = typeof clientesRisco !== 'undefined' ? clientesRisco : [];
  if (!btn) return;

  function esc(t) {
    return String(t == null ? '' : t).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  btn.addEventListener('click', function () {
    const titulo = document.getElementById('clientesRiscoTitulo');
    const corpo = document.getElementById('clientesRiscoCorpo');
    if (!titulo || !corpo) return;
    titulo.textContent = 'Clientes em risco (' + dados.length + ')';
    if (!dados.length) {
      corpo.innerHTML = '<p class="text-muted mb-0">Nenhum cliente em risco no período.</p>';
    } else {
      const trs = dados.map(function (d) {
        const dias = (d.dias_sem_contato == null) ? '—' : d.dias_sem_contato;
        const situacao = d.nunca_respondeu
          ? '<span class="badge text-bg-danger">Nunca respondeu</span>'
          : '<span class="badge text-bg-warning">Sem contato</span>';
        return '<tr>' +
          '<td>' + esc(d.nome) + '</td>' +
          '<td>' + esc(d.papel) + '</td>' +
          '<td class="text-end">' + d.grupos + '</td>' +
          '<td class="text-end">' + d.msgs + '</td>' +
          '<td class="text-end">' + dias + '</td>' +
          '<td class="text-end">' + d.taxa_resposta + '%</td>' +
          '<td>' + situacao + '</td>' +
          '</tr>';
      }).join('');
      corpo.innerHTML = '<div class="table-responsive"><table class="table table-sm table-hover align-middle">' +
        '<thead><tr><th>Cliente</th><th>Papel</th><th class="text-end">Grupos</th><th class="text-end">Msgs</th>' +
        '<th class="text-end">Dias sem contato</th><th class="text-end">Taxa resposta</th><th>Situação</th></tr></thead>' +
        '<tbody>' + trs + '</tbody></table></div>';
    }
    new bootstrap.Modal(document.getElementById('clientesRiscoModal')).show();
  });
})();