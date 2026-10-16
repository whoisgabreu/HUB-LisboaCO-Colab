// GERENCIAMENTO DE USUÁRIOS JS

let allUsers = [];
let currentTab = 'ativos';
let onlyBirthdays = false;

document.addEventListener('DOMContentLoaded', () => {
    loadUsers();
    bindMasks();
});

async function loadUsers() {
    try {
        const response = await fetch('/api/admin/usuarios');
        allUsers = await response.json();
        updateSummary();
        filterUsers();
    } catch (e) {
        console.error("Erro ao carregar usuários:", e);
    }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function soDigitos(v) { return (v || "").replace(/\D/g, ""); }

function mascaraTelefone(v) {
    const d = soDigitos(v).slice(0, 11);
    if (d.length <= 2) return d.length ? `(${d}` : "";
    if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
    if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

function mascaraCpf(v) {
    const d = soDigitos(v).slice(0, 11);
    if (d.length <= 3) return d;
    if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
    if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
    return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

function idade(dataISO) {
    if (!dataISO) return null;
    const d = new Date(dataISO + (dataISO.length === 10 ? "T00:00:00" : ""));
    if (isNaN(d)) return null;
    const hoje = new Date();
    let anos = hoje.getFullYear() - d.getFullYear();
    const m = hoje.getMonth() - d.getMonth();
    if (m < 0 || (m === 0 && hoje.getDate() < d.getDate())) anos--;
    return anos;
}

function dataBR(dataISO) {
    if (!dataISO) return "";
    const [a, m, dd] = dataISO.split("-");
    if (!a || !m || !dd) return "";
    return `${dd}/${m}/${a}`;
}

function ehAniversarianteDoMes(dataISO) {
    if (!dataISO) return false;
    return parseInt(dataISO.split("-")[1], 10) === (new Date().getMonth() + 1);
}

function bindMasks() {
    const tel = document.getElementById('userTelefone');
    const cpf = document.getElementById('userCpf');
    if (tel) tel.addEventListener('input', (e) => { e.target.value = mascaraTelefone(e.target.value); });
    if (cpf) cpf.addEventListener('input', (e) => { e.target.value = mascaraCpf(e.target.value); });
}

// ── Resumo / abas / filtros ───────────────────────────────────────────────────
function updateSummary() {
    const ativos = allUsers.filter(u => u.ativo).length;
    const inativos = allUsers.filter(u => !u.ativo).length;
    const admins = allUsers.filter(u => (u.nivel_acesso || '') === 'Admin').length;
    const aniversariantes = allUsers.filter(u => ehAniversarianteDoMes(u.data_nascimento)).length;

    document.getElementById('sum-total').textContent = allUsers.length;
    document.getElementById('sum-ativos').textContent = ativos;
    document.getElementById('sum-inativos').textContent = inativos;
    document.getElementById('sum-admins').textContent = admins;
    document.getElementById('sum-aniversariantes').textContent = aniversariantes;

    const ca = document.getElementById('count-ativos');
    const ci = document.getElementById('count-inativos');
    if (ca) ca.textContent = ativos;
    if (ci) ci.textContent = inativos;
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.user-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    filterUsers();
}

function toggleBirthdayFilter() {
    onlyBirthdays = !onlyBirthdays;
    document.getElementById('birthdayFilter').classList.toggle('active', onlyBirthdays);
    filterUsers();
}

function badgesHtml(arr, cls) {
    if (!arr || !arr.length) return `<span class="birth-empty">—</span>`;
    return arr.map(v => `<span class="mini-badge ${cls}">${v}</span>`).join("");
}

function renderUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';

    if (!users.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--text-muted);">Nenhum usuário encontrado.</td></tr>`;
        return;
    }

    users.forEach(u => {
        const tr = document.createElement('tr');
        tr.className = u.ativo ? '' : 'inactive-row';

        const avatarInner = u.profile_picture
            ? `<img src="/static/images/profile_pictures/${u.profile_picture}" alt="${u.nome}">`
            : `<span>${u.nome.charAt(0).toUpperCase()}</span>`;

        const posicoes = u.posicoes || [];
        const squads = (u.squads || []).map(s => s.nome);

        tr.innerHTML = `
            <td>
                <div class="user-info-cell">
                    <div class="user-avatar ${u.profile_picture ? 'has-photo' : ''}">${avatarInner}</div>
                    <div class="user-details">
                        <span class="user-name">${u.nome}</span>
                        <span class="user-email">${u.email}</span>
                    </div>
                </div>
            </td>
            <td><span class="role-badge">${u.cargo || 'N/A'}</span></td>
            <td><div class="badges-cell">${badgesHtml(posicoes, 'pos')}</div></td>
            <td><div class="badges-cell">${badgesHtml(squads, 'squad')}</div></td>
            <td>
                <span class="access-badge ${(u.nivel_acesso || '').toLowerCase() === 'admin' ? 'admin' : ''}">
                    ${u.nivel_acesso || 'N/A'}
                </span>
            </td>
            <td>
                <div class="status-indicator ${u.ativo ? 'active' : 'inactive'}">
                    <span class="status-dot"></span>
                    ${u.ativo ? 'Ativo' : 'Inativo'}
                </div>
            </td>
            <td>
                <div class="actions-cell">
                    <button class="btn-icon" title="Editar" onclick="openEditUserModal('${u.email}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon reset" title="Reset de Senha" onclick="resetPassword('${u.email}')">
                        <i class="fas fa-key"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterUsers() {
    const searchTerm    = document.getElementById('userSearchInput').value.toLowerCase();
    const squadFilter   = document.getElementById('squadFilter').value;
    const posicaoFilter = document.getElementById('posicaoFilter').value;

    const filtered = allUsers.filter(u => {
        const matchesTab      = currentTab === 'ativos' ? u.ativo : !u.ativo;
        const matchesSearch   = u.nome.toLowerCase().includes(searchTerm) || u.email.toLowerCase().includes(searchTerm);
        const matchesSquad    = !squadFilter || (u.squads || []).some(s => String(s.id) === String(squadFilter));
        const matchesPosicao  = !posicaoFilter || (u.posicoes || []).includes(posicaoFilter);
        const matchesBirthday = !onlyBirthdays || ehAniversarianteDoMes(u.data_nascimento);
        return matchesTab && matchesSearch && matchesSquad && matchesPosicao && matchesBirthday;
    });

    renderUsers(filtered);
}

// ── Modal ────────────────────────────────────────────────────────────────────
const modal = document.getElementById('userModal');
const form = document.getElementById('userForm');

function limparAreas() {
    document.querySelectorAll('#userPosicoes input, #userSquads input').forEach(cb => { cb.checked = false; });
}

function openNewUserModal() {
    document.getElementById('userModalTitle').textContent = 'Novo Usuário';
    document.getElementById('originalEmail').value = '';
    document.getElementById('passwordGroup').style.display = 'block';
    document.getElementById('userPodeEditarKanban').checked = false;
    document.getElementById('userPodeGerenciarFeed').checked = false;
    document.getElementById('userAtivo').value = 'true';
    form.reset();
    limparAreas();
    resetUserFormTabs();
    modal.classList.add('active');
}

function openEditUserModal(email) {
    const u = allUsers.find(user => user.email === email);
    if (!u) return;

    document.getElementById('userModalTitle').textContent = 'Editar Usuário';
    document.getElementById('originalEmail').value = u.email;
    document.getElementById('passwordGroup').style.display = 'none';

    document.getElementById('userName').value = u.nome;
    document.getElementById('userEmail').value = u.email;
    document.getElementById('userDataNascimento').value = u.data_nascimento || '';
    document.getElementById('userDataAdmissao').value = u.data_admissao || '';
    document.getElementById('userTelefone').value = mascaraTelefone(u.telefone || '');
    document.getElementById('userCpf').value = mascaraCpf(u.cpf || '');
    document.getElementById('userFuncao').value = u.cargo || '';
    document.getElementById('userSenioridade').value = u.senioridade || '';
    document.getElementById('userNivel').value = u.nivel || '';
    document.getElementById('userNivelAcesso').value = u.nivel_acesso;
    document.getElementById('userAtivo').value = u.ativo.toString();
    document.getElementById('userPodeEditarKanban').checked = !!u.pode_editar_kanban;
    document.getElementById('userPodeGerenciarFeed').checked = !!u.pode_gerenciar_feed;

    limparAreas();
    const posicoes = u.posicoes || [];
    document.querySelectorAll('#userPosicoes input').forEach(cb => { cb.checked = posicoes.includes(cb.value); });
    const squadIds = (u.squads || []).map(s => String(s.id));
    document.querySelectorAll('#userSquads input').forEach(cb => { cb.checked = squadIds.includes(cb.value); });

    resetUserFormTabs();
    modal.classList.add('active');
}

function closeUserModal() { modal.classList.remove('active'); }

// ── Abas do formulário ────────────────────────────────────────────────────────
function switchUserFormTab(tab) {
    document.querySelectorAll('#userForm .admin-form-tab')
        .forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('#userForm .admin-form-panel')
        .forEach(p => p.classList.toggle('active', p.dataset.panel === tab));
}

function resetUserFormTabs() {
    document.querySelectorAll('#userForm .campo-erro').forEach(el => el.classList.remove('campo-erro'));
    switchUserFormTab('dados');
}

const ABA_DO_CAMPO = { userName: 'dados', userEmail: 'dados', userNivelAcesso: 'acesso' };

function validarFormUsuario() {
    const obrigatorios = ['userName', 'userEmail', 'userNivelAcesso'];
    document.querySelectorAll('#userForm .campo-erro').forEach(el => el.classList.remove('campo-erro'));
    for (const id of obrigatorios) {
        const el = document.getElementById(id);
        if (!el) continue;
        const vazio = !el.value || !String(el.value).trim();
        const emailInvalido = id === 'userEmail' && !/^\S+@\S+\.\S+$/.test(el.value);
        if (vazio || emailInvalido) {
            switchUserFormTab(ABA_DO_CAMPO[id] || 'dados');
            el.classList.add('campo-erro');
            el.focus();
            return false;
        }
    }
    return true;
}

form.onsubmit = async (e) => {
    e.preventDefault();
    if (!validarFormUsuario()) return;
    const originalEmail = document.getElementById('originalEmail').value;
    const isEdit = originalEmail !== '';

    const posicoes = [...document.querySelectorAll('#userPosicoes input:checked')].map(cb => cb.value);
    const squads = [...document.querySelectorAll('#userSquads input:checked')].map(cb => parseInt(cb.value, 10));

    const payload = {
        nome: document.getElementById('userName').value,
        email: document.getElementById('userEmail').value,
        data_nascimento: document.getElementById('userDataNascimento').value || null,
        data_admissao: document.getElementById('userDataAdmissao').value || null,
        telefone: document.getElementById('userTelefone').value,
        cpf: document.getElementById('userCpf').value,
        cargo: document.getElementById('userFuncao').value,
        senioridade: document.getElementById('userSenioridade').value,
        nivel: document.getElementById('userNivel').value,
        posicoes: posicoes,
        squads: squads,
        nivel_acesso: document.getElementById('userNivelAcesso').value,
        ativo: document.getElementById('userAtivo').value === 'true',
        pode_editar_kanban: document.getElementById('userPodeEditarKanban').checked,
        pode_gerenciar_feed: document.getElementById('userPodeGerenciarFeed').checked
    };

    if (!isEdit) {
        payload.senha = document.getElementById('userPassword').value || 'v4company';
    }

    try {
        const url = isEdit ? `/api/admin/usuarios/${originalEmail}` : '/api/admin/usuarios';
        const method = isEdit ? 'PUT' : 'POST';
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resData = await response.json();
        if (response.ok) {
            alert(resData.message);
            closeUserModal();
            loadUsers();
        } else {
            alert("Erro: " + resData.error);
        }
    } catch (e) {
        alert("Erro na requisição.");
    }
};

// ── Reset de senha ───────────────────────────────────────────────────────────
const resetModal = document.getElementById('resetPasswordModal');
const resetForm = document.getElementById('resetPasswordForm');

function openResetModal(email) {
    document.getElementById('resetEmail').value = email;
    document.getElementById('resetTargetEmail').textContent = email;
    document.getElementById('newPassword').value = 'v4company';
    resetModal.classList.add('active');
}

function closeResetModal() { resetModal.classList.remove('active'); }

resetForm.onsubmit = async (e) => {
    e.preventDefault();
    const email = document.getElementById('resetEmail').value;
    const nova_senha = document.getElementById('newPassword').value;
    try {
        const response = await fetch('/api/admin/usuarios/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, nova_senha })
        });
        const data = await response.json();
        if (response.ok) {
            showToast(data.message, 'success');
            closeResetModal();
        } else {
            showToast("Erro: " + data.error, 'error');
        }
    } catch (e) {
        showToast("Erro na requisição.", 'error');
    }
};

function resetPassword(email) { openResetModal(email); }
