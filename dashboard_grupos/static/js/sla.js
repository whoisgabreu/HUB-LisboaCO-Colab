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

function bar(labels, datasets) {
  return {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { tooltip: TOOLTIP },
      scales: { x: { ticks: { autoSkip: false, maxRotation: 45 } } }
    }
  };
}

const COR_FAIXA = { green: '#16A36A', amber: '#D99000', red: '#D61616' };

function histConfig(h) {
  const dados = typeof h !== 'undefined' ? h : [];
  return {
    type: 'bar',
    data: {
      labels: dados.map(function (x) { return x.label; }),
      datasets: [{
        label: 'Respostas',
        data: dados.map(function (x) { return x.n; }),
        backgroundColor: dados.map(function (x) { return COR_FAIXA[x.cor] || '#94A7C4'; }),
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { ticks: { autoSkip: false, maxRotation: 30 } } },
      plugins: {
        tooltip: Object.assign({}, TOOLTIP, {
          callbacks: {
            label: function (ctx) {
              const item = dados[ctx.dataIndex];
              return ' ' + item.n + ' resposta(s) (' + item.pct + '%)';
            }
          }
        })
      }
    }
  };
}

novoGrafico('chartHistEquipe', histConfig(histEquipe));
novoGrafico('chartHistCliente', histConfig(histCliente));

novoGrafico('chartSlaHora', bar(slaHora.map(x => x[0] + 'h'), [
  { label: 'SLA útil médio (min)', data: slaHora.map(x => x[1]), backgroundColor: '#2563EB', borderRadius: 8 }
]));

novoGrafico('chartSlaDia', bar(slaDia.map(x => x[0]), [
  { label: 'SLA útil médio (min)', data: slaDia.map(x => x[1]), backgroundColor: '#16A36A', borderRadius: 8 }
]));

const MODAL_TITULOS = {
  semRespEquipe: 'Mensagens de cliente sem resposta da equipe',
  semRespCliente: 'Mensagens de equipe sem resposta do cliente'
};
const MODAL_DADOS = {
  semRespEquipe: typeof semRespEquipe !== 'undefined' ? semRespEquipe : [],
  semRespCliente: typeof semRespCliente !== 'undefined' ? semRespCliente : []
};

function trunca(t, n) {
  return t.length > n ? t.slice(0, n) + '…' : t;
}

function escapeHtml(t) {
  return String(t).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

function abreSemResposta(chave) {
  const titulo = document.getElementById('semRespostaTitulo');
  const corpo = document.getElementById('semRespostaCorpo');
  const dados = MODAL_DADOS[chave] || [];
  titulo.textContent = MODAL_TITULOS[chave] + ' (' + dados.length + ')';
  if (!dados.length) {
    corpo.innerHTML = '<p class="text-muted mb-0">Nenhuma mensagem sem resposta no período.</p>';
    return;
  }
  const linhas = dados.map(function (m) {
    return '<tr>' +
      '<td class="text-nowrap">' + m.ts + '</td>' +
      '<td>' + m.grupo + '</td>' +
      '<td>' + m.nome + ' <span class="badge text-bg-secondary">' + m.tipo + '</span></td>' +
      '<td class="text-truncate" style="max-width:28rem" title="' + escapeHtml(m.texto) + '">' + escapeHtml(trunca(m.texto, 150)) + '</td>' +
      '</tr>';
  }).join('');
  corpo.innerHTML = '<div class="table-responsive">' +
    '<table class="table table-sm table-hover align-middle">' +
    '<thead><tr><th>Quando</th><th>Grupo</th><th>Autor</th><th>Mensagem</th></tr></thead>' +
    '<tbody>' + linhas + '</tbody></table></div>';
}

document.querySelectorAll('[data-dg-modal]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    abreSemResposta(btn.getAttribute('data-dg-modal'));
    new bootstrap.Modal(document.getElementById('semRespostaModal')).show();
  });
});

const primeiras = typeof primeirasRespostas !== 'undefined' ? primeirasRespostas : [];

function abrePrimeira(idx) {
  const p = primeiras[idx];
  if (!p) return;
  document.getElementById('primeiraTitulo').textContent = 'Resposta do dia — ' + p.grupo + ' (' + p.dia + ')';
  const msgs = p.cliente_msgs.map(function (m) { return Object.assign({}, m, { lado: 'cliente' }); })
    .concat(p.equipe_msgs.map(function (m) { return Object.assign({}, m, { lado: 'equipe' }); }));
  const linhas = msgs.map(function (m) {
    return '<tr>' +
      '<td class="text-nowrap">' + m.ts + '</td>' +
      '<td><span class="badge ' + (m.lado === 'equipe' ? 'text-bg-primary' : 'text-bg-secondary') + '">' + m.lado + '</span></td>' +
      '<td>' + m.nome + '</td>' +
      '<td class="text-truncate" style="max-width:26rem" title="' + escapeHtml(m.texto) + '">' + escapeHtml(trunca(m.texto, 150)) + '</td>' +
      '</tr>';
  }).join('');
  document.getElementById('primeiraCorpo').innerHTML =
    '<div class="table-responsive">' +
    '<table class="table table-sm table-hover align-middle">' +
    '<thead><tr><th>Quando</th><th>Lado</th><th>Autor</th><th>Mensagem</th></tr></thead>' +
    '<tbody>' + linhas + '</tbody></table></div>';
  new bootstrap.Modal(document.getElementById('primeiraModal')).show();
}

document.querySelectorAll('#tblPrimeiras tbody tr.row-click').forEach(function (tr) {
  tr.addEventListener('click', function () {
    abrePrimeira(parseInt(tr.getAttribute('data-idx'), 10));
  });
});

const sortBtn = document.getElementById('sortMinutos');
let sortMode = 'normal';

function atualizarSortBtn() {
  if (!sortBtn) return;
  if (sortMode === 'normal') {
    sortBtn.innerHTML = '<i class="bi bi-arrow-down-up"></i>';
    sortBtn.title = 'Ordenar por tempo de resposta (normal)';
  } else if (sortMode === 'cres') {
    sortBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
    sortBtn.title = 'Menor tempo de resposta primeiro';
  } else {
    sortBtn.innerHTML = '<i class="bi bi-arrow-down"></i>';
    sortBtn.title = 'Maior tempo de resposta primeiro';
  }
}

function aplicarOrdenacao() {
  const tbody = document.querySelector('#tblPrimeiras tbody');
  if (!tbody) return;
  const linhas = Array.prototype.slice.call(tbody.querySelectorAll('tr'))
    .filter(function (tr) { return !tr.classList.contains('dg-empty'); });
  if (sortMode === 'normal') {
    linhas.sort(function (a, b) {
      return parseInt(a.getAttribute('data-orig'), 10) - parseInt(b.getAttribute('data-orig'), 10);
    });
  } else {
    const dir = sortMode === 'cres' ? 1 : -1;
    linhas.sort(function (a, b) {
      const va = parseFloat(a.getAttribute('data-minutos'));
      const vb = parseFloat(b.getAttribute('data-minutos'));
      return (va - vb) * dir;
    });
  }
  linhas.forEach(function (tr) { tbody.appendChild(tr); });
  atualizarSortBtn();
  const pag = document.getElementById('tblPrimeiras')._dgPag;
  if (pag) { pag.reset(); pag.refresh(); }
}

if (sortBtn) {
  sortBtn.addEventListener('click', function () {
    sortMode = sortMode === 'normal' ? 'cres' : (sortMode === 'cres' ? 'decres' : 'normal');
    aplicarOrdenacao();
  });
}

(function () {
  const KEY = 'dg_sla_tab';
  const tabEls = document.querySelectorAll('#slaTabs .nav-link');
  if (!tabEls.length) return;
  const saved = localStorage.getItem(KEY);
  if (saved) {
    const alvo = document.querySelector('#slaTabs .nav-link[data-bs-target="' + saved + '"]');
    if (alvo) bootstrap.Tab.getOrCreateInstance(alvo).show();
  }
  tabEls.forEach(function (el) {
    el.addEventListener('shown.bs.tab', function (e) {
      localStorage.setItem(KEY, e.target.getAttribute('data-bs-target'));
    });
  });
})();