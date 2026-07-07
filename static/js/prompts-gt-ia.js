/* ==============================
   PROMPTS GT IA - Tab Switching
   ================================ */

function switchPromptTab(ev, tabId) {
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
   Helpers
   ================================ */

function _v(id) {
    var el = document.getElementById(id);
    return el ? el.value.trim() : '';
}

function _txt(id) {
    var el = document.getElementById(id);
    return el ? el.value : '';
}

function _checked(id) {
    var el = document.getElementById(id);
    return el ? el.checked : false;
}

function _checkedValues(containerId) {
    var values = [];
    document.querySelectorAll('#' + containerId + ' input[type="checkbox"]:checked').forEach(function (cb) {
        values.push(cb.value);
    });
    return values;
}

/* ==============================
   Repeating Items
   ================================ */

function removerItem(btn) {
    var item = btn.closest('.repeating-item');
    item.remove();
    // Trigger regeneration from whichever function
    var slide = item.closest('.slide-content');
    if (slide) {
        var id = slide.id;
        if (id === 'slide-subir-campanha') { renumberConjuntos(); gerarSubirCampanha(); }
        else if (id === 'slide-otimizacao-direta') { renumberAcoesOd(); gerarOtimizacaoDireta(); }
        else if (id === 'slide-exec-pos-analise') { renumberAcoesEpa(); gerarExecPosAnalise(); }
    }
}

function adicionarConjunto() {
    var container = document.getElementById('sc-conjuntos-container');
    var template = document.getElementById('sc-conjunto-template');
    var clone = template.content.cloneNode(true);
    container.appendChild(clone);
    renumberConjuntos();
    gerarSubirCampanha();
}

function renumberConjuntos() {
    var items = document.querySelectorAll('#sc-conjuntos-container .repeating-item');
    items.forEach(function (item, idx) {
        var num = String(idx + 1).padStart(2, '0');
        item.querySelector('.item-num').textContent = num;
    });
}

function adicionarAcaoOd() {
    var container = document.getElementById('od-acoes-container');
    var template = document.getElementById('od-acao-template');
    var clone = template.content.cloneNode(true);
    container.appendChild(clone);
    renumberAcoesOd();
    gerarOtimizacaoDireta();
}

function renumberAcoesOd() {
    var items = document.querySelectorAll('#od-acoes-container .repeating-item');
    items.forEach(function (item, idx) {
        item.querySelector('.item-num').textContent = String(idx + 1).padStart(2, '0');
    });
}

function adicionarAcaoEpa() {
    var container = document.getElementById('epa-acoes-container');
    var template = document.getElementById('epa-acao-template');
    var clone = template.content.cloneNode(true);
    container.appendChild(clone);
    renumberAcoesEpa();
    gerarExecPosAnalise();
}

function renumberAcoesEpa() {
    var items = document.querySelectorAll('#epa-acoes-container .repeating-item');
    items.forEach(function (item, idx) {
        item.querySelector('.item-num').textContent = String(idx + 1).padStart(2, '0');
    });
}

/* ==============================
   Toggle Formulário (Subir Campanha)
   ================================ */

function toggleFormulario() {
    var checked = document.getElementById('sc-tem-formulario').checked;
    var section = document.getElementById('sc-form-section');
    section.classList.toggle('active', checked);
}

/* ==============================
   Copiar
   ================================ */

function copiarTexto(elementId) {
    var el = document.getElementById(elementId);
    var text = el.value || el.textContent;
    if (!text) return;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
            showCopiedFeedback(el);
        });
    } else {
        el.select();
        document.execCommand('copy');
        showCopiedFeedback(el);
    }
}

function showCopiedFeedback(outputEl) {
    var container = outputEl.closest('.preview-box');
    if (!container) return;
    var btn = container.querySelector('.btn-copy');
    if (!btn) return;
    var originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> Copiado!';
    btn.classList.add('copied');
    setTimeout(function () {
        btn.innerHTML = originalText;
        btn.classList.remove('copied');
    }, 2000);
}

/* ==============================
   1 - SUBIR CAMPANHA
   ================================ */

function gerarSubirCampanha() {
    var cliente = _v('sc-cliente') || '[NOME DO CLIENTE]';
    var conta = _v('sc-conta') || '[NOME OU ID DA CONTA]';
    var plataforma = _txt('sc-plataforma');
    var objetivo = _txt('sc-objetivo');
    var campanha = _v('sc-campanha') || '[NOME DA CAMPANHA]';
    var verba = _v('sc-verba') || '[R$ X/dia ou orçamento total]';
    var estruturaCampanha = _v('sc-estrutura-campanha') || '[NOME]';
    var drive = _v('sc-drive') || '[LINK DO DRIVE]';
    var copy = _v('sc-copy') || '[TEXTO]';
    var titulo = _v('sc-titulo') || '[TÍTULO]';
    var cta = _v('sc-cta') || '[CTA]';
    var destino = _txt('sc-destino');

    var output = '';
    output += '*SUBIR CAMPANHA*\n';
    output += 'Cliente: ' + cliente + '\n';
    output += 'Conta/CA: ' + conta + '\n';
    output += 'Tipo de pedido: Execução operacional\n';
    output += 'Ação: Criar campanha nova do zero\n';
    output += 'Plataforma: ' + plataforma + '\n';
    output += 'Objetivo da campanha: ' + objetivo + '\n';
    output += 'Campanha: ' + campanha + '\n';
    output += 'Verba: ' + verba + '\n';
    output += '\n';
    output += 'Estrutura:\n';
    output += 'Campanha: ' + estruturaCampanha + '\n';

    var conjuntos = document.querySelectorAll('#sc-conjuntos-container .repeating-item');
    conjuntos.forEach(function (item, idx) {
        var num = String(idx + 1).padStart(2, '0');
        var publico = item.querySelector('.fld-publico').value.trim() || '[PÚBLICO]';
        var idade = item.querySelector('.fld-idade').value.trim() || '[IDADE]';
        var localizacao = item.querySelector('.fld-localizacao').value.trim() || '[LOCALIZAÇÃO]';
        var posicionamentos = item.querySelector('.fld-posicionamentos').value.trim() || '[POSICIONAMENTOS]';
        var orcamento = item.querySelector('.fld-orcamento').value.trim() || '[ORÇAMENTO]';
        output += '\nConjunto ' + num + ':\n';
        output += '- Público: ' + publico + '\n';
        output += '- Idade: ' + idade + '\n';
        output += '- Localização: ' + localizacao + '\n';
        output += '- Posicionamentos: ' + posicionamentos + '\n';
        output += '- Orçamento: ' + orcamento + '\n';
    });

    output += '\nCriativos/Drive:\n' + drive + '\n';
    output += '\nCopy/Legenda:\n' + copy + '\n';
    output += 'Título: ' + titulo + '\n';
    output += 'CTA: ' + cta + '\n';
    output += 'Destino: ' + destino + '\n';

    if (_checked('sc-tem-formulario')) {
        var campos = _v('sc-form-campos') || '[CAMPOS]';
        var perguntas = _v('sc-form-perguntas') || '[PERGUNTAS]';
        output += '\nFormulário nativo:\n';
        output += 'Campos:\n' + campos + '\n';
        output += '\nPerguntas:\n' + perguntas + '\n';
    }

    output += '\nObservações:\n';
    output += 'Criar tudo pausado e aguardar confirmação antes de ativar.\n';
    output += '\nNão fazer:\n';
    output += 'Não alterar campanhas existentes.\n';
    output += 'Não otimizar outras campanhas.\n';
    output += 'Não aumentar budget fora do pedido.\n';
    output += 'Não publicar ativo sem confirmação.';

    document.getElementById('sc-output').value = output;
}

/* ==============================
   2 - OTIMIZAÇÃO DIRETA
   ================================ */

function gerarOtimizacaoDireta() {
    var cliente = _v('od-cliente') || '[NOME DO CLIENTE]';
    var conta = _v('od-conta') || '[NOME OU ID DA CONTA]';
    var plataforma = _txt('od-plataforma');
    var campanhaAlvo = _v('od-campanha-alvo') || '[NOME EXATO DA CAMPANHA]';
    var objCampanha = _v('od-obj-campanha');
    var objConjunto = _v('od-obj-conjunto');
    var objAnuncio = _v('od-obj-anuncio');
    var objPublico = _v('od-obj-publico');
    var objCriativo = _v('od-obj-criativo');

    var output = '';
    output += '*OTIMIZAÇÃO DIRETA*\n';
    output += 'Cliente: ' + cliente + '\n';
    output += 'Conta/CA: ' + conta + '\n';
    output += 'Tipo de pedido: Execução operacional\n';
    output += 'Ação: Otimizar campanha existente conforme instruções abaixo\n';
    output += 'Plataforma: ' + plataforma + '\n';
    output += 'Campanha alvo: ' + campanhaAlvo + '\n';

    var acoes = document.querySelectorAll('#od-acoes-container .repeating-item');
    if (acoes.length > 0) {
        output += '\nO que fazer:\n';
        acoes.forEach(function (item) {
            var text = item.querySelector('textarea').value.trim();
            if (text) output += '- ' + text + '\n';
        });
    }

    output += '\nObjetos alvo:\n';
    output += '- Campanha: ' + (objCampanha || '-') + '\n';
    output += '- Conjunto: ' + (objConjunto || '-') + '\n';
    output += '- Anúncio: ' + (objAnuncio || '-') + '\n';
    output += '- Público: ' + (objPublico || '-') + '\n';
    output += '- Criativo: ' + (objCriativo || '-') + '\n';

    output += '\nRegras:\n';
    output += 'Executar somente o que está descrito.\n';
    output += 'Validar os objetos via API antes de alterar.\n';
    output += 'Não fazer análise antes, a menos que falte informação para executar.\n';
    output += 'Se algum objeto não for encontrado ou estiver ambíguo, bloquear e explicar.\n';

    output += '\nNão fazer:\n';
    output += 'Não analisar performance.\n';
    output += 'Não sugerir ações.\n';
    output += 'Não aumentar budget total.\n';
    output += 'Não mexer em campanhas fora do escopo.\n';
    output += 'Não criar campanhas novas, salvo se estiver escrito acima.';

    document.getElementById('od-output').value = output;
}

/* ==============================
   3 - OTIMIZAÇÃO PELA ANÁLISE
   ================================ */

function gerarOtimizacaoAnalise() {
    var cliente = _v('oa-cliente') || '[NOME DO CLIENTE]';
    var conta = _v('oa-conta') || '[NOME OU ID DA CONTA]';
    var plataforma = _txt('oa-plataforma');
    var campanhaAlvo = _v('oa-campanha-alvo') || '[NOME EXATO DA CAMPANHA]';
    var periodo = _txt('oa-periodo');
    var objetivo = _txt('oa-objetivo');
    var cplMax = _v('oa-cpl-max');
    var cplPriority = _v('oa-cpl-priority');
    var volumeMin = _v('oa-volume-min');

    var output = '';
    output += '*OTIMIZAÇÃO PELA ANÁLISE DO GT IA*\n';
    output += 'Cliente: ' + cliente + '\n';
    output += 'Conta/CA: ' + conta + '\n';
    output += 'Tipo de pedido: Execução operacional\n';
    output += 'Ação: Otimizar campanha existente\n';
    output += 'Plataforma: ' + plataforma + '\n';
    output += 'Campanha alvo: ' + campanhaAlvo + '\n';
    output += 'Período de análise: ' + periodo + '\n';
    output += 'Objetivo da otimização: ' + objetivo + '\n';

    var acoesPermitidas = _checkedValues('oa-acoes');
    if (acoesPermitidas.length > 0) {
        output += '\nAções permitidas:\n';
        acoesPermitidas.forEach(function (a) {
            output += '- ' + a + '\n';
        });
    }

    output += '\nCritérios:\n';
    if (cplMax) output += '- Pausar se CPL acima de R$ ' + cplMax + '\n';
    if (cplPriority) output += '- Priorizar se CPL abaixo de R$ ' + cplPriority + '\n';
    if (volumeMin) output += '- Considerar volume mínimo de ' + volumeMin + '\n';

    output += '\nNão fazer:\n';
    output += 'Não aumentar budget total.\n';
    output += 'Não mexer em campanhas fora da campanha alvo.\n';
    output += 'Não criar campanha nova.\n';
    output += 'Não ativar nada sem confirmação se houver dúvida.';

    document.getElementById('oa-output').value = output;
}

/* ==============================
   4 - ANÁLISE DE CONTAS
   ================================ */

function gerarAnaliseContas() {
    var cliente = _v('ac-cliente') || '[NOME DO CLIENTE]';
    var conta = _v('ac-conta') || '[NOME OU ID DA CONTA]';
    var plataforma = _txt('ac-plataforma');
    var periodo = _txt('ac-periodo');
    var escopo = _v('ac-escopo') || '- [NOME DA CAMPANHA]';
    var objetivo = _v('ac-objetivo') || 'Entender o que está bom, o que está ruim e quais ações devem ser feitas.';

    var output = '';
    output += '*ANÁLISE DE CONTAS*\n';
    output += 'Cliente: ' + cliente + '\n';
    output += 'Conta/CA: ' + conta + '\n';
    output += 'Tipo de pedido: Análise\n';
    output += 'Plataforma: ' + plataforma + '\n';
    output += '\nEscopo:\n';
    output += 'Analisar performance das campanhas abaixo:\n';
    output += escopo + '\n';
    output += '\nPeríodo: ' + periodo + '\n';
    output += '\nObjetivo da análise:\n' + objetivo + '\n';

    output += '\nMétricas principais:\n';
    output += '- Investimento\n';
    output += '- Impressões\n';
    output += '- Cliques\n';
    output += '- CTR\n';
    output += '- CPC\n';
    output += '- Leads\n';
    output += '- CPL\n';
    output += '- Conversões\n';
    output += '- Taxa de conversão\n';

    output += '\nFormato da resposta:\n';
    output += '1. Resumo direto\n';
    output += '2. Diagnóstico\n';
    output += '3. Principais problemas\n';
    output += '4. Oportunidades\n';
    output += '5. Ações recomendadas\n';
    output += '6. O que eu executaria primeiro\n';
    output += '7. Análise de público\n';
    output += '8. Análise de produto\n';
    output += '9. Análise de criativo\n';

    output += '\nNão fazer:\n';
    output += 'Não executar alterações.\n';
    output += 'Não pausar campanhas.\n';
    output += 'Não alterar budget.\n';
    output += 'Apenas analisar e recomendar.';

    document.getElementById('ac-output').value = output;
}

/* ==============================
   5 - EXECUÇÃO PÓS ANÁLISE
   ================================ */

function gerarExecPosAnalise() {
    var cliente = _v('epa-cliente') || '[NOME DO CLIENTE]';
    var conta = _v('epa-conta') || '[NOME OU ID DA CONTA]';

    var output = '';
    output += '*EXECUÇÃO PÓS ANÁLISE*\n';
    output += 'Cliente: ' + cliente + '\n';
    output += 'Conta/CA: ' + conta + '\n';
    output += 'Origem: Executar as ações aprovadas da análise anterior.\n';
    output += '\nAções aprovadas:\n';

    var acoes = document.querySelectorAll('#epa-acoes-container .repeating-item');
    acoes.forEach(function (item, idx) {
        var text = item.querySelector('textarea').value.trim();
        var num = String(idx + 1);
        output += '\nA' + num + ':\n';
        output += (text || '[DESCREVER A AÇÃO]') + '\n';
    });

    output += '\nRegras:\n';
    output += 'Executar somente as ações listadas.\n';
    output += 'Validar tudo via API antes de alterar.\n';
    output += 'Registrar o que foi alterado.\n';
    output += 'Manter rollback possível.\n';

    output += '\nNão fazer:\n';
    output += 'Não executar ações não listadas.\n';
    output += 'Não aumentar budget total.\n';
    output += 'Não mexer em campanhas fora do escopo.';

    document.getElementById('epa-output').value = output;
}

/* ==============================
   6 - GA4
   ================================ */

function gerarGA4() {
    var cliente = _v('ga4-cliente') || '[NOME DO CLIENTE]';
    var acao = _txt('ga4-acao');
    var conta = _v('ga4-conta') || '[NOME OU ID DA CONTA]';
    var propriedade = _v('ga4-propriedade') || '[NOME OU ID DA PROPRIEDADE]';
    var site = _v('ga4-site') || '[URL]';
    var objetivo = _v('ga4-objetivo') || '[DESCRIÇÃO]';
    var oqfazer = _v('ga4-oqfazer') || '- [AÇÃO 1]\n- [AÇÃO 2]';
    var outroEvento = _v('ga4-outro-evento');

    var eventos = _checkedValues('ga4-eventos');
    if (outroEvento) {
        eventos = eventos.filter(function (e) { return e !== 'outro'; });
        eventos.push(outroEvento);
    }

    var output = '';
    output += '*GA4*\n';
    output += 'Cliente: ' + cliente + '\n';
    output += 'Tipo de pedido: GA4\n';
    output += 'Ação: ' + acao + ' configuração no Google Analytics 4\n';
    output += 'Conta GA4: ' + conta + '\n';
    output += 'Propriedade GA4: ' + propriedade + '\n';
    output += 'Site/LP: ' + site + '\n';
    output += 'Objetivo: ' + objetivo + '\n';

    if (eventos.length > 0) {
        output += '\nEventos envolvidos:\n';
        eventos.forEach(function (e) {
            output += '- ' + e + '\n';
        });
    }

    output += '\nO que fazer:\n';
    output += oqfazer + '\n';

    output += '\nRegras:\n';
    output += 'Validar se os eventos estão chegando no GA4.\n';
    output += 'Conferir DebugView/Realtime quando aplicável.\n';
    output += 'Não criar evento duplicado se já existir um equivalente.\n';
    output += 'Se for marcar evento como conversão/key event, confirmar o evento exato antes.\n';

    output += '\nNão fazer:\n';
    output += 'Não mexer em propriedades fora do cliente.\n';
    output += 'Não alterar eventos que não fazem parte do escopo.\n';
    output += 'Não publicar/alterar sem confirmação se houver ambiguidade.';

    document.getElementById('ga4-output').value = output;
}

/* ==============================
   7 - TRACKING
   ================================ */

function gerarTracking() {
    var cliente = _v('tr-cliente') || '[NOME DO CLIENTE]';
    var acao = _txt('tr-acao');
    var container = _v('tr-container') || '[GTM-XXXXXXX]';
    var site = _v('tr-site') || '[URL]';
    var objetivo = _v('tr-objetivo') || '[DESCRIÇÃO]';
    var evento = _txt('tr-evento');
    var oqfazer = _v('tr-oqfazer') || '- [AÇÃO 1]\n- [AÇÃO 2]';
    var outraPlataforma = _v('tr-outra-plataforma');

    var plataformas = _checkedValues('tr-plataformas');
    if (outraPlataforma) {
        plataformas = plataformas.filter(function (p) { return p !== 'outra'; });
        if (outraPlataforma) plataformas.push(outraPlataforma);
    }

    var output = '';
    output += '*TRACKING*\n';
    output += 'Cliente: ' + cliente + '\n';
    output += 'Tipo de pedido: Tracking / GTM\n';
    output += 'Ação: ' + acao + ' configuração no Google Tag Manager\n';
    output += 'Container GTM: ' + container + '\n';
    output += 'Site/LP: ' + site + '\n';
    output += 'Objetivo: ' + objetivo + '\n';
    output += 'Evento principal: ' + evento + '\n';

    output += '\nO que fazer:\n';
    output += oqfazer + '\n';

    if (plataformas.length > 0) {
        output += '\nPlataformas envolvidas:\n';
        plataformas.forEach(function (p) {
            output += '- ' + p + '\n';
        });
    }

    output += '\nRegras:\n';
    output += 'Usar Preview/Debug antes de publicar.\n';
    output += 'Validar acionadores, tags e variáveis.\n';
    output += 'Não criar evento duplicado se já existir um equivalente.\n';
    output += 'Se precisar publicar, aguardar confirmação antes.\n';

    output += '\nNão fazer:\n';
    output += 'Não mexer em containers fora do cliente.\n';
    output += 'Não alterar eventos que não fazem parte do escopo.\n';
    output += 'Não publicar sem confirmação.';

    document.getElementById('tr-output').value = output;
}

/* ==============================
   Inicialização
   ================================ */

document.addEventListener('DOMContentLoaded', function () {
    // Create first conjunto
    adicionarConjunto();
    // Create first 3 ações for Otimização Direta
    adicionarAcaoOd();
    adicionarAcaoOd();
    adicionarAcaoOd();
    // Create first 3 ações for Exec Pós Análise
    adicionarAcaoEpa();
    adicionarAcaoEpa();
    adicionarAcaoEpa();

    gerarSubirCampanha();
    gerarOtimizacaoDireta();
    gerarOtimizacaoAnalise();
    gerarAnaliseContas();
    gerarExecPosAnalise();
    gerarGA4();
    gerarTracking();
});
