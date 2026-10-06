const PALETA = ["#D61616", "#2563EB", "#16A36A", "#D99000", "#7c3aed", "#0891b2", "#64748B", "#94A7C4", "#DB2777", "#059669", "#9333ea", "#e11d48"];

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

function baseBar(labels, dados, titulo) {
  return {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: titulo,
        data: dados,
        backgroundColor: PALETA,
        borderRadius: 8,
        maxBarThickness: 42
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: TOOLTIP }
    }
  };
}

function mediaMovel(dados, janela) {
  const out = [];
  for (let i = 0; i < dados.length; i++) {
    const ini = Math.max(0, i - janela + 1);
    const fatia = dados.slice(ini, i + 1);
    out.push(Math.round((fatia.reduce((a, b) => a + b, 0) / fatia.length) * 10) / 10);
  }
  return out;
}

function linha(labels, dados) {
  return {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Mensagens',
          data: dados,
          borderColor: '#D61616',
          backgroundColor: 'rgba(214,22,22,0.10)',
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: '#D61616',
          borderWidth: 2
        },
        {
          label: 'Média móvel 7d',
          data: mediaMovel(dados, 7),
          borderColor: '#2563EB',
          borderDash: [5, 4],
          fill: false,
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'top', labels: { boxWidth: 12, usePointStyle: true } },
        tooltip: TOOLTIP
      }
    }
  };
}

if (typeof serieDia !== 'undefined') {
  novoGrafico('chartDia', linha(serieDia.map(x => x[0]), serieDia.map(x => x[1])));
  novoGrafico('chartHora', baseBar(Array.from({ length: 24 }, (_, i) => i + 'h'), horas, 'Mensagens'));
  const series = comparacao.series || [];
  novoGrafico('chartComparacao', {
    type: 'bar',
    data: {
      labels: series.map(x => x[0]),
      datasets: [
        { label: '1ª metade', data: series.map(x => x[1]), backgroundColor: '#94A7C4', borderRadius: 8 },
        { label: '2ª metade', data: series.map(x => x[2]), backgroundColor: '#D61616', borderRadius: 8 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { tooltip: TOOLTIP } }
  });
  novoGrafico('chartGrupos', baseBar(grupos.map(x => x[0]), grupos.map(x => x[1]), 'Mensagens'));
  novoGrafico('chartRemetentes', baseBar(remetentes.map(x => x[0]), remetentes.map(x => x[1]), 'Mensagens'));
}