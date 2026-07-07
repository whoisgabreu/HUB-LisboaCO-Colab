/* ==============================
   PADRONIZADORES - Tab Switching
   ================================ */

function switchPadTab(ev, tabId) {
    document.querySelectorAll('.tab-btn').forEach(function (btn) {
        btn.classList.remove('active');
    });
    ev.currentTarget.classList.add('active');

    document.querySelectorAll('.slide-content').forEach(function (slide) {
        slide.classList.remove('active');
    });
    document.getElementById('slide-' + tabId).classList.add('active');
}

/* ==============================
   UTM
   ================================ */

function gerarUTM() {
    var url = document.getElementById('utm-url').value.trim();
    var source = document.getElementById('utm-source').value.trim();
    var medium = document.getElementById('utm-medium').value.trim();
    var campaign = document.getElementById('utm-campaign').value.trim();
    var term = document.getElementById('utm-term').value.trim();
    var content = document.getElementById('utm-content').value.trim();
    var output = document.getElementById('utm-output');

    if (!url || !source || !medium) {
        output.textContent = 'Preencha os campos obrigatórios (*)';
        return;
    }

    var params = [];
    params.push('utm_source=' + source.toLowerCase());
    params.push('utm_medium=' + medium.toLowerCase());
    if (campaign) params.push('utm_campaign=' + campaign.toLowerCase());
    if (term) params.push('utm_term=' + term);
    if (content) params.push('utm_content=' + content);

    var separator = url.indexOf('?') === -1 ? '?' : '&';
    output.textContent = url + separator + params.join('&');
}

/* ==============================
   Campanha Facebook
   ================================ */

function gerarCampanhaFB() {
    var numero = document.getElementById('campfb-numero').value || '1';
    var v4 = document.getElementById('campfb-v4').checked;
    var tipo = document.getElementById('campfb-tipo').value;
    var nome = document.getElementById('campfb-nome').value.trim();
    var output = document.getElementById('campfb-output');

    var parts = [numero, '-'];
    if (v4) parts.push('[V4]');
    parts.push(tipo);
    parts.push('-');
    if (nome) parts.push(nome);

    output.textContent = parts.join(' ');
}

/* ==============================
   Conjunto Facebook
   ================================ */

function switchConjuntoMode() {
    var mode = document.getElementById('conjfb-mode').value;
    document.querySelectorAll('.conjunto-fields').forEach(function (el) {
        el.classList.remove('active');
    });
    document.getElementById('conjfb-mode-' + mode).classList.add('active');
    gerarConjuntoFB();
}

function gerarConjuntoFB() {
    var mode = document.getElementById('conjfb-mode').value;
    var output = document.getElementById('conjfb-output');

    if (mode === 'publico') {
        var fator = document.getElementById('conjfb-fator').value.trim() || '00';
        var publico = document.getElementById('conjfb-publico').value;
        var geo = document.getElementById('conjfb-geo').value.trim() || '';
        var tipoPublico = document.getElementById('conjfb-tipo-publico').value;
        var sexo = document.getElementById('conjfb-sexo').value;
        var idade = document.getElementById('conjfb-idade').value.trim() || '';
        var nome = document.getElementById('conjfb-nome').value.trim();

        var parts = [fator, '-', '[' + publico + ']', '[' + geo + ']', '[' + tipoPublico + ']', '[' + sexo + ']', '[' + idade + ']', '-'];
        if (nome) parts.push(nome);
        output.textContent = parts.join(' ');
    } else {
        var fator = document.getElementById('conjfb-pos-fator').value.trim() || '00';
        var publico = document.getElementById('conjfb-pos-publico').value;
        var plataforma = document.getElementById('conjfb-plataforma').value;
        var posicionamento = document.getElementById('conjfb-posicionamento').value;
        var sexo = document.getElementById('conjfb-pos-sexo').value;
        var idade = document.getElementById('conjfb-pos-idade').value.trim() || '';

        var parts = [fator, '-', '[' + publico + ']', '[' + plataforma + ']', '[' + posicionamento + ']', '[' + sexo + ']', '[' + idade + ']'];
        output.textContent = parts.join(' ');
    }
}

/* ==============================
   Anúncio Facebook
   ================================ */

function gerarAnuncioFB() {
    var numero = document.getElementById('anuncfb-numero').value || '1';
    var formato = document.getElementById('anuncfb-formato').value;
    var nome = document.getElementById('anuncfb-nome').value.trim();
    var output = document.getElementById('anuncfb-output');

    output.textContent = numero + ' ' + formato + ' - ' + nome;
}

/* ==============================
   Campanha Google
   ================================ */

function gerarCampanhaGGL() {
    var numero = document.getElementById('campggl-numero').value || '1';
    var v4 = document.getElementById('campggl-v4').checked;
    var tipo = document.getElementById('campggl-tipo').value;
    var objetivo = document.getElementById('campggl-objetivo').value;
    var geo = document.getElementById('campggl-geo').value.trim();
    var nome = document.getElementById('campggl-nome').value.trim();
    var output = document.getElementById('campggl-output');

    var parts = [numero, '-'];
    if (v4) parts.push('[V4]');
    parts.push(tipo);
    parts.push(objetivo);
    if (geo) parts.push('[' + geo + ']');
    parts.push('-');
    if (nome) parts.push(nome);

    output.textContent = parts.join(' ');
}

/* ==============================
   Grupo Google Search
   ================================ */

function gerarGrupoSearch() {
    var ref = document.getElementById('grpsearch-ref').value.trim() || '00';
    var corresp = document.getElementById('grpsearch-corresp').value;
    var sexo = document.getElementById('grpsearch-sexo').value;
    var nome = document.getElementById('grpsearch-nome').value.trim();
    var output = document.getElementById('grpsearch-output');

    var parts = [ref, '-', '[' + corresp + ']', '[' + sexo + ']', '-'];
    if (nome) parts.push(nome);

    output.textContent = parts.join(' ');
}

/* ==============================
   Grupo Google Demais
   ================================ */

function gerarGrupoDemais() {
    var ref = document.getElementById('grpdemais-ref').value.trim() || '00';
    var publico = document.getElementById('grpdemais-publico').value;
    var detalhes = document.getElementById('grpdemais-detalhes').value.trim();
    var sexo = document.getElementById('grpdemais-sexo').value;
    var idade = document.getElementById('grpdemais-idade').value.trim();
    var nome = document.getElementById('grpdemais-nome').value.trim();
    var output = document.getElementById('grpdemais-output');

    var parts = [ref, '-', '[' + publico + ']'];
    parts.push('[' + detalhes + ']');
    parts.push('[' + sexo + ']');
    parts.push('[' + idade + ']');
    parts.push('-');
    if (nome) parts.push(nome);

    output.textContent = parts.join(' ');
}

/* ==============================
   Copiar para clipboard
   ================================ */

function copiarTexto(elementId) {
    var el = document.getElementById(elementId);
    var text = el.textContent;

    if (!text || text === 'Preencha os campos obrigatórios (*)') return;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
            showCopiedFeedback(el);
        });
    } else {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showCopiedFeedback(el);
    }
}

function showCopiedFeedback(outputEl) {
    var container = outputEl.closest('.preview-box');
    var btn = container.querySelector('.btn-copy');
    var originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> Copiado!';
    btn.classList.add('copied');
    setTimeout(function () {
        btn.innerHTML = originalText;
        btn.classList.remove('copied');
    }, 2000);
}

/* ==============================
   Inicialização
   ================================ */

document.addEventListener('DOMContentLoaded', function () {
    gerarUTM();
    gerarCampanhaFB();
    gerarConjuntoFB();
    gerarAnuncioFB();
    gerarCampanhaGGL();
    gerarGrupoSearch();
    gerarGrupoDemais();
});
