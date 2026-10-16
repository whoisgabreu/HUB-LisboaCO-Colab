/* Página Perfil: mini-cards, projetos em que atuo e edição do perfil. */
(function () {
    const dados = { resumo: null };

    function toastMsg(msg, erro) {
        if (typeof toast !== 'undefined' && toast[erro ? 'error' : 'success']) {
            toast[erro ? 'error' : 'success'](msg);
        } else {
            console.log(msg);
        }
    }

    function fmtTempo(tc) {
        if (!tc) return null;
        const anos = tc.anos || 0, meses = tc.meses || 0, dias = tc.dias || 0;
        if (anos >= 1) return anos + ' ano' + (anos > 1 ? 's' : '') + (meses ? ' e ' + meses + ' mes' + (meses > 1 ? 'es' : '') : '');
        if (meses >= 1) return meses + ' mes' + (meses > 1 ? 'es' : '');
        return dias + ' dia' + (dias !== 1 ? 's' : '');
    }

    function fmtTempoCurto(tc) {
        if (!tc) return '—';
        if (tc.anos >= 1) return tc.anos + 'a' + (tc.meses ? ' ' + tc.meses + 'm' : '');
        if (tc.meses >= 1) return tc.meses + 'm';
        return tc.dias + 'd';
    }

    function fmtFee(v, moeda) {
        if (v == null) return '';
        const n = Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return (moeda ? moeda + ' ' : '') + n;
    }

    async function carregarResumo() {
        try {
            const r = await fetch('/api/perfil', { credentials: 'same-origin' });
            const d = await r.json();
            if (d.erro) return;
            dados.resumo = d;

            const cargo = document.getElementById('perfilCargo');
            if (cargo && d.funcao) cargo.textContent = d.funcao;

            const tc = fmtTempo(d.tempo_casa);
            const tempoEl = document.getElementById('perfilTempo');
            if (tempoEl) tempoEl.textContent = tc ? ('Na empresa há ' + tc) : '';

            const sp = document.getElementById('statProjetos');
            if (sp) sp.textContent = d.projetos_ativos != null ? d.projetos_ativos : '0';

            const sr = document.getElementById('statRanking');
            if (sr) sr.textContent = d.posicao_ranking ? ('#' + d.posicao_ranking) : '—';

            const st = document.getElementById('statTempo');
            if (st) st.textContent = fmtTempoCurto(d.tempo_casa);
        } catch (e) { /* silencioso */ }
    }

    async function carregarProjetos() {
        const body = document.getElementById('projetosWidgetBody');
        if (!body) return;
        try {
            const r = await fetch('/api/perfil/projetos', { credentials: 'same-origin' });
            const d = await r.json();
            const projetos = d.projetos || [];
            if (!projetos.length) {
                body.innerHTML = '<div class="feed-widget-empty">Nenhum projeto ativo.</div>';
                return;
            }
            body.innerHTML = '<div class="perfil-projetos">' + projetos.map(p => {
                const fee = fmtFee(p.fee, p.moeda);
                const meta = [p.status, p.fase].filter(Boolean).join(' · ');
                return '<div class="perfil-projeto" onclick="location.href=\'/hub-projetos\'" title="Abrir no Hub de Projetos">' +
                    '<div class="perfil-projeto-nome">' + esc(p.nome || 'Projeto') + '</div>' +
                    (meta ? '<div class="perfil-projeto-meta">' + esc(meta) + '</div>' : '') +
                    (fee ? '<div class="perfil-projeto-fee">' + esc(fee) + '</div>' : '') +
                    '</div>';
            }).join('') + '</div>';
        } catch (e) {
            body.innerHTML = '<div class="feed-widget-empty">Erro ao buscar projetos.</div>';
        }
    }

    function esc(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    async function carregarAtividade() {
        const canvas = document.getElementById('perfilAtividadeChart');
        if (!canvas || typeof Chart === 'undefined') return;
        try {
            const r = await fetch('/api/perfil/atividade?semanas=8', { credentials: 'same-origin' });
            const d = await r.json();
            if (d.erro) return;
            new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: d.labels || [],
                    datasets: [
                        { label: 'Postagens', data: d.posts || [], backgroundColor: 'rgba(214,22,22,0.75)', borderRadius: 4 },
                        { label: 'Reações recebidas', data: d.reacoes || [], backgroundColor: 'rgba(59,130,246,0.7)', borderRadius: 4 },
                    ],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#9ca3af', boxWidth: 12, font: { size: 11 } } } },
                    scales: {
                        x: { ticks: { color: '#9ca3af', font: { size: 10 } }, grid: { display: false } },
                        y: { beginAtZero: true, ticks: { color: '#9ca3af', precision: 0, font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.06)' } },
                    },
                },
            });
        } catch (e) { /* silencioso */ }
    }

    function mascaraTelefone(v) {
        const d = String(v || '').replace(/\D/g, '').slice(0, 11);
        if (d.length <= 10) return d.replace(/^(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3').replace(/-$/, '');
        return d.replace(/^(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3').replace(/-$/, '');
    }

    function abrirEdicao() {
        const d = dados.resumo || {};
        document.getElementById('perfilFuncao').value = d.funcao || '';
        document.getElementById('perfilTelefone').value = mascaraTelefone(d.telefone || '');
        document.getElementById('perfilNascimento').value = d.data_nascimento || '';
        const img = document.getElementById('perfilModalImg');
        const icone = document.getElementById('perfilModalIcone');
        if (d.profile_picture) {
            img.src = '/static/images/profile_pictures/' + d.profile_picture;
            img.style.display = '';
            icone.style.display = 'none';
        } else {
            img.style.display = 'none';
            icone.style.display = '';
        }
        document.getElementById('perfilEditModal').classList.add('ativa');
    }

    function fecharEdicao() {
        document.getElementById('perfilEditModal').classList.remove('ativa');
    }

    async function salvarEdicao() {
        const btn = document.getElementById('perfilSalvarBtn');
        const payload = {
            funcao: document.getElementById('perfilFuncao').value,
            telefone: document.getElementById('perfilTelefone').value,
            data_nascimento: document.getElementById('perfilNascimento').value || null,
        };
        btn.disabled = true;
        try {
            const r = await fetch('/api/perfil', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(payload),
            });
            const d = await r.json();
            if (!r.ok || d.erro) { toastMsg(d.erro || 'Erro ao salvar.', true); return; }
            dados.resumo = d.perfil || dados.resumo;
            const cargo = document.getElementById('perfilCargo');
            if (cargo && payload.funcao) cargo.textContent = payload.funcao;
            toastMsg('Perfil atualizado!');
            fecharEdicao();
        } catch (e) {
            toastMsg('Erro ao salvar.', true);
        } finally {
            btn.disabled = false;
        }
    }

    function configurarFoto() {
        const input = document.getElementById('perfilFotoInput');
        if (!input) return;
        input.addEventListener('change', async function () {
            const file = this.files[0];
            if (!file) return;
            if (file.size > 2 * 1024 * 1024) { toastMsg('A imagem deve ter no máximo 2MB.', true); this.value = ''; return; }
            const img = document.getElementById('perfilModalImg');
            const icone = document.getElementById('perfilModalIcone');
            img.src = URL.createObjectURL(file);
            img.style.display = '';
            icone.style.display = 'none';
            const fd = new FormData();
            fd.append('foto', file);
            try {
                const r = await fetch('/upload-profile-picture', { method: 'POST', body: fd, credentials: 'same-origin' });
                const d = await r.json();
                if (!r.ok) { toastMsg(d.erro || 'Erro ao enviar foto.', true); return; }
                toastMsg('Foto atualizada!');
                if (dados.resumo) dados.resumo.profile_picture = (dados.resumo.email || '') + '.png';
            } catch (e) {
                toastMsg('Erro ao enviar foto.', true);
            }
        });
    }

    window.Perfil = { abrirEdicao: abrirEdicao, fecharEdicao: fecharEdicao, salvarEdicao: salvarEdicao };

    document.addEventListener('DOMContentLoaded', function () {
        carregarResumo();
        carregarProjetos();
        carregarAtividade();
        configurarFoto();
        const modal = document.getElementById('perfilEditModal');
        if (modal) {
            modal.addEventListener('click', function (e) { if (e.target === modal) fecharEdicao(); });
            document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fecharEdicao(); });
        }
    });
})();