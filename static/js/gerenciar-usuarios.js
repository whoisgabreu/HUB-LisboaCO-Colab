// GERENCIAMENTO DE USUÁRIOS JS

let allUsers = [];

document.addEventListener('DOMContentLoaded', () => {
    loadUsers();
});

async function loadUsers() {
    try {
        const response = await fetch('/api/admin/usuarios');
        allUsers = await response.json();
        renderUsers(allUsers);
    } catch (e) {
        console.error("Erro ao carregar usuários:", e);
    }
}

function renderUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';

    users.forEach(u => {
        const tr = document.createElement('tr');
        tr.className = u.ativo ? '' : 'inactive-row';
        tr.setAttribute('data-name', u.nome);
        tr.setAttribute('data-email', u.email);
        tr.setAttribute('data-squad', u.squad || '');
        tr.setAttribute('data-posicao', u.posicao || '');

        tr.innerHTML = `
            <td>
                <div class="user-info-cell">
                    <div class="user-avatar">${u.nome.charAt(0)}</div>
                    <div class="user-details">
                        <span class="user-name">${u.nome}</span>
                        <span class="user-email">${u.email}</span>
                    </div>
                </div>
            </td>
            <td>
                <span class="role-badge">${u.funcao || 'N/A'}</span>
                <span class="squad-badge">${u.squad || 'Sem Squad'}</span>
            </td>
            <td>${u.posicao || 'N/A'}</td>
            <td>
                <span class="access-badge ${u.nivel_acesso.toLowerCase() === 'admin' ? 'admin' : ''}">
                    ${u.nivel_acesso}
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
    const searchTerm = document.getElementById('userSearchInput').value.toLowerCase();
    const squadFilter = document.getElementById('squadFilter').value.toLowerCase();
    const posicaoFilter = document.getElementById('posicaoFilter').value.toLowerCase();
    
    const filtered = allUsers.filter(u => {
        const matchesSearch = u.nome.toLowerCase().includes(searchTerm) || u.email.toLowerCase().includes(searchTerm);
        const matchesSquad = !squadFilter || (u.squad && u.squad.toLowerCase() === squadFilter);
        const matchesPosicao = !posicaoFilter || (u.posicao && u.posicao.toLowerCase() === posicaoFilter);
        
        return matchesSearch && matchesSquad && matchesPosicao;
    });
    
    renderUsers(filtered);
}

// MODAL LOGIC
const modal = document.getElementById('userModal');
const form = document.getElementById('userForm');

function openNewUserModal() {
    document.getElementById('userModalTitle').textContent = 'Novo Usuário';
    document.getElementById('originalEmail').value = '';
    document.getElementById('passwordGroup').style.display = 'block';
    form.reset();
    modal.classList.add('active');
}

function openEditUserModal(email) {
    const u = allUsers.find(user => user.email === email);
    if (!u) return;

    document.getElementById('userModalTitle').textContent = 'Editar Usuário';
    document.getElementById('originalEmail').value = u.email;
    document.getElementById('passwordGroup').style.display = 'none'; // Não altera senha por aqui
    
    document.getElementById('userName').value = u.nome;
    document.getElementById('userEmail').value = u.email;
    document.getElementById('userFuncao').value = u.funcao || '';
    document.getElementById('userSenioridade').value = u.senioridade || '';
    document.getElementById('userNivel').value = u.nivel || '';
    document.getElementById('userSquad').value = u.squad || '';
    document.getElementById('userPosicao').value = u.posicao || '';
    document.getElementById('userNivelAcesso').value = u.nivel_acesso;
    document.getElementById('userAtivo').value = u.ativo.toString();

    modal.classList.add('active');
}

function closeUserModal() {
    modal.classList.remove('active');
}

form.onsubmit = async (e) => {
    e.preventDefault();
    const originalEmail = document.getElementById('originalEmail').value;
    const isEdit = originalEmail !== '';
    
    const payload = {
        nome: document.getElementById('userName').value,
        email: document.getElementById('userEmail').value,
        funcao: document.getElementById('userFuncao').value,
        senioridade: document.getElementById('userSenioridade').value,
        nivel: document.getElementById('userNivel').value,
        squad: document.getElementById('userSquad').value,
        posicao: document.getElementById('userPosicao').value,
        nivel_acesso: document.getElementById('userNivelAcesso').value,
        ativo: document.getElementById('userAtivo').value === 'true'
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

// RESET PASSWORD MODAL LOGIC
const resetModal = document.getElementById('resetPasswordModal');
const resetForm = document.getElementById('resetPasswordForm');

function openResetModal(email) {
    document.getElementById('resetEmail').value = email;
    document.getElementById('resetTargetEmail').textContent = email;
    document.getElementById('newPassword').value = 'v4company';
    resetModal.classList.add('active');
}

function closeResetModal() {
    resetModal.classList.remove('active');
}

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

// Update table actions to call openResetModal
function resetPassword(email) {
    openResetModal(email);
}
