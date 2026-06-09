/**
 * face_auth.js — Camera capture, liveness detection, biometric registration & login
 */

let faceStream = null;
let faceCaptureInterval = null;
let faceCapturedFrames = [];
let faceIsCapturing = false;
let faceCaptureMode = null; // 'register', 'update', 'login'
let faceLoginEmail = null;
let faceLivenessChallenges = [];
let faceLivenessCurrentChallenge = 0;
let faceLivenessPassed = false;
let faceAnimationId = null;

function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function showToast(msg, type) {
    if (typeof window.showToast === 'function') {
        window.showToast(msg, type);
    } else {
        console.log(`[toast] ${type}: ${msg}`);
        alert(msg);
    }
}

async function getFaceStatus() {
    try {
        const res = await fetch('/api/face/biometry/status');
        if (!res.ok) throw new Error('Erro ao carregar status');
        return await res.json();
    } catch (e) {
        console.error('Face status error:', e);
        return null;
    }
}

async function updateFaceStatusUI() {
    const content = document.getElementById('face-status-content');
    if (!content) return;
    const status = await getFaceStatus();
    if (!status) {
        content.innerHTML = '<p class="face-result-error">Erro ao carregar status.</p>';
        return;
    }
    const registerBtn = document.getElementById('btn-face-register');
    const updateBtn = document.getElementById('btn-face-update');
    const deleteBtn = document.getElementById('btn-face-delete');
    if (status.has_biometry) {
        content.innerHTML = `
            <div class="face-status-item">
                <span class="face-status-label">Status</span>
                <span class="face-status-value active"><i class="fas fa-check-circle"></i> Ativo</span>
            </div>
            <div class="face-status-item">
                <span class="face-status-label">Registros biométricos</span>
                <span class="face-status-value">${status.total_faces}</span>
            </div>
            <div class="face-status-item">
                <span class="face-status-label">Total de amostras</span>
                <span class="face-status-value">${status.total_samples}</span>
            </div>
            <div class="face-status-item">
                <span class="face-status-label">Último cadastro</span>
                <span class="face-status-value">${status.last_registration ? new Date(status.last_registration).toLocaleString('pt-BR') : 'N/A'}</span>
            </div>
        `;
        if (registerBtn) registerBtn.style.display = 'none';
        if (updateBtn) updateBtn.style.display = '';
        if (deleteBtn) deleteBtn.style.display = '';
    } else {
        content.innerHTML = `
            <div class="face-status-item">
                <span class="face-status-label">Status</span>
                <span class="face-status-value inactive">Não cadastrada</span>
            </div>
            <div class="face-status-item">
                <span class="face-status-label">Registros biométricos</span>
                <span class="face-status-value">0</span>
            </div>
        `;
        if (registerBtn) registerBtn.style.display = '';
        if (updateBtn) updateBtn.style.display = 'none';
        if (deleteBtn) deleteBtn.style.display = 'none';
    }
}

async function startCamera() {
    if (faceStream) {
        faceStream.getTracks().forEach(t => t.stop());
    }
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' }
        });
        const video = document.getElementById('face-video');
        if (video) {
            video.srcObject = faceStream;
            await video.play();
        }
        return true;
    } catch (e) {
        console.error('Camera error:', e);
        showToast('Erro ao acessar a câmera. Verifique as permissões.', 'erro');
        return false;
    }
}

function stopCamera() {
    if (faceCaptureInterval) {
        clearInterval(faceCaptureInterval);
        faceCaptureInterval = null;
    }
    if (faceAnimationId) {
        cancelAnimationFrame(faceAnimationId);
        faceAnimationId = null;
    }
    if (faceStream) {
        faceStream.getTracks().forEach(t => t.stop());
        faceStream = null;
    }
    const video = document.getElementById('face-video');
    if (video) video.srcObject = null;
}

function captureFrame(quality) {
    const video = document.getElementById('face-video');
    const canvas = document.getElementById('face-canvas');
    if (!video || !canvas) return null;
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, 320, 240);
    return canvas.toDataURL('image/jpeg', quality || 0.5);
}

/* ─── LIVENESS CHALLENGES ────────────────────────────── */

const LIVENESS_CHALLENGES = [
    { id: 'blink', text: 'Pisque os olhos', duration: 2000 },
    { id: 'left', text: 'Olhe para a esquerda', duration: 2000 },
    { id: 'right', text: 'Olhe para a direita', duration: 2000 },
    { id: 'up', text: 'Olhe para cima', duration: 2000 },
    { id: 'smile', text: 'Sorria', duration: 2000 },
];

function shuffleChallenges() {
    const shuffled = [...LIVENESS_CHALLENGES];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled.slice(0, 2);
}

async function runLivenessSequence() {
    return new Promise((resolve) => {
        faceLivenessChallenges = shuffleChallenges();
        faceLivenessCurrentChallenge = 0;
        faceLivenessPassed = false;
        const livenessArea = document.getElementById('face-liveness-area');
        const challengeEl = document.getElementById('face-liveness-challenge');
        const progressEl = document.getElementById('face-capture-progress');
        const progressFill = document.getElementById('face-progress-fill');
        const progressText = document.getElementById('face-progress-text');
        if (livenessArea) livenessArea.style.display = 'block';
        if (progressEl) progressEl.style.display = 'none';
        let challengeIndex = 0;
        let capturedDuringChallenges = [];
        function runNextChallenge() {
            if (challengeIndex >= faceLivenessChallenges.length) {
                if (livenessArea) livenessArea.style.display = 'none';
                faceLivenessPassed = true;
                if (progressEl) progressEl.style.display = '';
                if (progressFill) progressFill.style.width = '0%';
                if (progressText) progressText.textContent = '0/10';
                resolve({ success: true, frames: capturedDuringChallenges, challengeCount: challengeIndex });
                return;
            }
            const challenge = faceLivenessChallenges[challengeIndex];
            if (challengeEl) challengeEl.textContent = challenge.text;
            if (challengeEl) challengeEl.style.animation = 'none';
            setTimeout(() => { if (challengeEl) challengeEl.style.animation = 'pulse 0.5s ease'; }, 10);
            let challengeFrames = 0;
            const maxChallengeFrames = 4;
            const collectInterval = setInterval(() => {
                if (faceIsCapturing === false) {
                    clearInterval(collectInterval);
                    return;
                }
                const frame = captureFrame();
                if (frame) {
                    capturedDuringChallenges.push(frame);
                    challengeFrames++;
                }
                if (challengeFrames >= maxChallengeFrames) {
                    clearInterval(collectInterval);
                    challengeIndex++;
                    setTimeout(runNextChallenge, 200);
                }
            }, 150);
        }
        runNextChallenge();
    });
}

async function captureRemainingFrames(minTotal) {
    const progressEl = document.getElementById('face-capture-progress');
    const progressFill = document.getElementById('face-progress-fill');
    const progressText = document.getElementById('face-progress-text');
    const instruction = document.getElementById('face-camera-instruction');
    if (progressEl) progressEl.style.display = '';
    if (instruction) instruction.textContent = 'Mantenha o rosto no centro';
    return new Promise((resolve) => {
        const collected = [];
        const interval = setInterval(() => {
            if (faceIsCapturing === false) {
                clearInterval(interval);
                resolve(collected);
                return;
            }
            const frame = captureFrame();
            if (frame) collected.push(frame);
            const total = collected.length;
            if (progressFill) progressFill.style.width = `${Math.min(100, (total / minTotal) * 100)}%`;
            if (progressText) progressText.textContent = `${total}/${minTotal}`;
            if (total >= minTotal) {
                clearInterval(interval);
                resolve(collected);
            }
        }, 100);
    });
}

/* ─── REGISTRATION FLOW ──────────────────────────────── */

async function startFaceRegistration() {
    if (faceIsCapturing) return;
    faceCaptureMode = 'register';
    faceIsCapturing = true;
    const cameraArea = document.getElementById('face-camera-area');
    const actions = document.getElementById('face-actions');
    const registerBtn = document.getElementById('btn-face-register');
    const cancelBtn = document.getElementById('btn-face-cancel');
    const instruction = document.getElementById('face-camera-instruction');
    if (cameraArea) cameraArea.style.display = '';
    if (registerBtn) registerBtn.style.display = 'none';
    if (cancelBtn) cancelBtn.style.display = '';
    if (instruction) instruction.textContent = 'Abrindo câmera...';
    const ok = await startCamera();
    if (!ok) {
        faceIsCapturing = false;
        if (cameraArea) cameraArea.style.display = 'none';
        if (registerBtn) registerBtn.style.display = '';
        if (cancelBtn) cancelBtn.style.display = 'none';
        return;
    }
    if (instruction) instruction.textContent = 'Posicione seu rosto no centro';
    await new Promise(r => setTimeout(r, 1000));
    if (instruction) instruction.textContent = 'Execute os desafios de vivacidade';
    const livenessResult = await runLivenessSequence();
    if (!faceIsCapturing) return;
    if (!livenessResult.success) {
        showToast('Falha na validação de vivacidade.', 'erro');
        cleanupFaceCapture();
        return;
    }
    if (instruction) instruction.textContent = 'Capturando amostras...';
    const remainingFrames = await captureRemainingFrames(10);
    if (!faceIsCapturing) return;
    const allFrames = [...livenessResult.frames, ...remainingFrames];
    if (allFrames.length < 8) {
        showToast(`Poucos frames capturados (${allFrames.length}). Tente novamente.`, 'erro');
        cleanupFaceCapture();
        return;
    }
    if (instruction) instruction.textContent = 'Processando...';
    try {
        const res = await fetch('/api/face/biometry/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ frames: allFrames })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            const body = document.getElementById('face-camera-area');
            if (body) {
                body.innerHTML = `
                    <div class="face-success-overlay" style="min-height:200px">
                        <div class="face-success-icon"><i class="fas fa-check-circle"></i></div>
                        <p class="face-success-text">Biometria cadastrada!</p>
                    </div>
                `;
            }
            await new Promise(r => setTimeout(r, 1200));
            cleanupFaceCapture();
            await updateFaceStatusUI();
        } else {
            showToast(data.error || 'Erro ao cadastrar biometria.', 'erro');
            cleanupFaceCapture();
        }
    } catch (e) {
        showToast('Erro de conexão ao cadastrar biometria.', 'erro');
        cleanupFaceCapture();
    }
}

async function startFaceUpdate() {
    if (faceIsCapturing) return;
    faceCaptureMode = 'update';
    faceIsCapturing = true;
    const cameraArea = document.getElementById('face-camera-area');
    const actions = document.getElementById('face-actions');
    const updateBtn = document.getElementById('btn-face-update');
    const deleteBtn = document.getElementById('btn-face-delete');
    const cancelBtn = document.getElementById('btn-face-cancel');
    const instruction = document.getElementById('face-camera-instruction');
    if (cameraArea) cameraArea.style.display = '';
    if (updateBtn) updateBtn.style.display = 'none';
    if (deleteBtn) deleteBtn.style.display = 'none';
    if (cancelBtn) cancelBtn.style.display = '';
    if (instruction) instruction.textContent = 'Abrindo câmera...';
    const ok = await startCamera();
    if (!ok) {
        faceIsCapturing = false;
        if (cameraArea) cameraArea.style.display = 'none';
        if (updateBtn) updateBtn.style.display = '';
        if (deleteBtn) deleteBtn.style.display = '';
        if (cancelBtn) cancelBtn.style.display = 'none';
        await updateFaceStatusUI();
        return;
    }
    if (instruction) instruction.textContent = 'Posicione seu rosto no centro';
    await new Promise(r => setTimeout(r, 1000));
    if (instruction) instruction.textContent = 'Execute os desafios de vivacidade';
    const livenessResult = await runLivenessSequence();
    if (!faceIsCapturing) return;
    if (!livenessResult.success) {
        showToast('Falha na validação de vivacidade.', 'erro');
        cleanupFaceCapture();
        return;
    }
    if (instruction) instruction.textContent = 'Capturando amostras...';
    const remainingFrames = await captureRemainingFrames(10);
    if (!faceIsCapturing) return;
    const allFrames = [...livenessResult.frames, ...remainingFrames];
    if (allFrames.length < 8) {
        showToast(`Poucos frames capturados (${allFrames.length}). Tente novamente.`, 'erro');
        cleanupFaceCapture();
        return;
    }
    if (instruction) instruction.textContent = 'Processando...';
    try {
        const res = await fetch('/api/face/biometry/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ frames: allFrames })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast('Biometria facial atualizada com sucesso!', 'sucesso');
            await updateFaceStatusUI();
        } else {
            showToast(data.error || 'Erro ao atualizar biometria.', 'erro');
        }
    } catch (e) {
        showToast('Erro de conexão ao atualizar biometria.', 'erro');
    }
    cleanupFaceCapture();
}

function confirmFaceDelete() {
    if (!confirm('Tem certeza que deseja remover sua biometria facial? O login facial será desativado.')) return;
    fetch('/api/face/biometry/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast('Biometria facial removida com sucesso.', 'sucesso');
            updateFaceStatusUI();
        } else {
            showToast(data.error || 'Erro ao remover biometria.', 'erro');
        }
    })
    .catch(() => showToast('Erro de conexão ao remover biometria.', 'erro'));
}

function cleanupFaceCapture() {
    stopCamera();
    faceIsCapturing = false;
    faceCaptureMode = null;
    const cameraArea = document.getElementById('face-camera-area');
    const registerBtn = document.getElementById('btn-face-register');
    const updateBtn = document.getElementById('btn-face-update');
    const deleteBtn = document.getElementById('btn-face-delete');
    const cancelBtn = document.getElementById('btn-face-cancel');
    const livenessArea = document.getElementById('face-liveness-area');
    const progressEl = document.getElementById('face-capture-progress');
    const instruction = document.getElementById('face-camera-instruction');
    if (cameraArea) cameraArea.style.display = 'none';
    if (livenessArea) livenessArea.style.display = 'none';
    if (progressEl) progressEl.style.display = 'none';
    if (cancelBtn) cancelBtn.style.display = 'none';
    if (instruction) instruction.textContent = 'Posicione seu rosto no centro';
    updateFaceStatusUI();
}

function cancelFaceCapture() {
    cleanupFaceCapture();
}

/* ─── FACE LOGIN ──────────────────────────────────────── */

async function checkFaceBiometry(email) {
    try {
        const res = await fetch('/api/face/login/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        if (!res.ok) return null;
        return await res.json();
    } catch (e) {
        return null;
    }
}

function showLoginError(msg) {
    let errorDiv = document.querySelector('.error-message');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        const form = document.querySelector('.login-form');
        const btn = document.getElementById('login-btn');
        if (btn && btn.parentNode) {
            btn.parentNode.insertBefore(errorDiv, btn);
        } else if (form) {
            form.appendChild(errorDiv);
        }
    }
    errorDiv.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i><p>${msg}</p>`;
    errorDiv.style.display = 'flex';
}

async function handleFaceLoginClick() {
    const emailInput = document.getElementById('login-email');
    if (!emailInput || !emailInput.value.trim()) {
        showLoginError('Informe seu e-mail primeiro.');
        return;
    }
    const email = emailInput.value.trim();
    const result = await checkFaceBiometry(email);
    if (!result) {
        showLoginError('Erro ao verificar disponibilidade facial.');
        return;
    }
    if (!result.user_exists) {
        showLoginError('Usuário não encontrado.');
        return;
    }
    if (!result.has_face_biometry) {
        showLoginError('Você ainda não possui biometria facial cadastrada. Faça login com senha e registre em Perfil > Biometria Facial.');
        return;
    }
    const errorDiv = document.querySelector('.error-message');
    if (errorDiv) errorDiv.style.display = 'none';
    startFaceLoginWithEmail(email);
}

async function startFaceLogin() {
    const emailInput = document.getElementById('login-email');
    if (!emailInput || !emailInput.value) {
        showToast('Informe seu e-mail primeiro.', 'erro');
        return;
    }
    startFaceLoginWithEmail(emailInput.value.trim());
}

async function startFaceLoginWithEmail(email) {
    const emailInput = document.getElementById('login-email');
    if (!emailInput || !emailInput.value) {
        showToast('Informe seu e-mail primeiro.', 'erro');
        return;
    }
    faceLoginEmail = email;
    faceCaptureMode = 'login';
    faceIsCapturing = true;
    const existingModal = document.querySelector('.face-camera-modal-overlay');
    if (existingModal) existingModal.remove();
    const modal = document.createElement('div');
    modal.className = 'face-camera-modal-overlay';
    modal.innerHTML = `
        <div class="face-camera-modal">
            <div class="face-camera-modal-header">
                <h3>Autenticação Facial</h3>
                <button onclick="cancelFaceLogin()"><i class="fas fa-times"></i></button>
            </div>
            <div class="face-camera-modal-body">
                <video id="face-login-video" autoplay playsinline></video>
                <canvas id="face-login-canvas" style="display:none;"></canvas>
                <div class="face-detection-overlay">
                    <div class="face-guide-ring"></div>
                    <p id="face-login-instruction" class="face-instruction">Posicione seu rosto no centro</p>
            </div>
            <div id="face-login-liveness" class="face-liveness-area" style="display:none;">
                <p class="face-liveness-title">Desafio de Vivacidade</p>
                <p id="face-login-challenge" class="face-liveness-challenge">Pisque os olhos</p>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' }
        });
        const video = document.getElementById('face-login-video');
        if (video) {
            video.srcObject = faceStream;
            await video.play();
        }
    } catch (e) {
        showToast('Erro ao acessar a câmera.', 'erro');
        cancelFaceLogin();
        return;
    }
    const instruction = document.getElementById('face-login-instruction');
    if (instruction) instruction.textContent = 'Pisque os olhos';
    await runLoginLivenessSequence();
    if (!faceIsCapturing) return;
    if (instruction) instruction.textContent = 'Autenticando...';
    await new Promise(r => setTimeout(r, 300));
    const finalFrame = captureLoginFrame();
    if (!finalFrame) {
        showToast('Erro ao capturar frame final.', 'erro');
        cancelFaceLogin();
        return;
    }
    try {
        const res = await fetch('/api/face/login/authenticate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: faceLoginEmail, frame: finalFrame })
        });
        const data = await res.json();
        console.log('[FaceAuth] login response:', res.status, data);
        if (res.ok && data.success) {
            const body = document.querySelector('.face-camera-modal-body');
            if (body) {
                body.innerHTML = `
                    <div class="face-success-overlay">
                        <div class="face-success-icon"><i class="fas fa-check-circle"></i></div>
                        <p class="face-success-text">Autenticado com sucesso!</p>
                    </div>
                `;
            }
            const header = document.querySelector('.face-camera-modal-header');
            if (header) header.style.display = 'none';
            const liveness = document.getElementById('face-login-liveness');
            if (liveness) liveness.style.display = 'none';
            await new Promise(r => setTimeout(r, 1200));
            cancelFaceLogin();
            window.location.href = data.redirect || '/';
        } else {
            const body = document.querySelector('.face-camera-modal-body');
            if (body) {
                body.innerHTML = `
                    <div class="face-success-overlay">
                        <div class="face-success-icon face-fail-icon"><i class="fas fa-times-circle"></i></div>
                        <p class="face-success-text">Rosto não reconhecido</p>
                        <p class="face-success-sub">Tente novamente</p>
                    </div>
                `;
            }
            const header = document.querySelector('.face-camera-modal-header');
            if (header) header.style.display = 'none';
            const liveness = document.getElementById('face-login-liveness');
            if (liveness) liveness.style.display = 'none';
            await new Promise(r => setTimeout(r, 1500));
            cancelFaceLogin();
        }
    } catch (e) {
        console.error('[FaceAuth] login error:', e);
        showToast('Erro de conexão.', 'erro');
        cancelFaceLogin();
    }
}

async function runLoginLivenessSequence() {
    const livenessArea = document.getElementById('face-login-liveness');
    const challengeEl = document.getElementById('face-login-challenge');
    if (livenessArea) livenessArea.style.display = 'block';
    if (!faceIsCapturing) return;
    if (challengeEl) challengeEl.textContent = 'Pisque os olhos';
    if (challengeEl) challengeEl.style.animation = 'none';
    setTimeout(() => { if (challengeEl) challengeEl.style.animation = 'pulse 0.5s ease'; }, 10);
    await new Promise(r => setTimeout(r, 2000));
    if (livenessArea) livenessArea.style.display = 'none';
}

function captureLoginFrame() {
    const video = document.getElementById('face-login-video');
    const canvas = document.getElementById('face-login-canvas');
    if (!video || !canvas) return null;
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, 320, 240);
    return canvas.toDataURL('image/jpeg', 0.5);
}

function cancelFaceLogin() {
    stopCamera();
    faceIsCapturing = false;
    faceCaptureMode = null;
    faceLoginEmail = null;
    const modal = document.querySelector('.face-camera-modal-overlay');
    if (modal) modal.remove();
}

/* ─── INIT ────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver(() => {
        const biometriaSection = document.getElementById('config-biometria');
        if (biometriaSection && biometriaSection.classList.contains('active')) {
            updateFaceStatusUI();
        }
    });
    const modal = document.getElementById('modalConfiguracoes');
    if (modal) {
        observer.observe(modal, { attributes: true, subtree: true, attributeFilter: ['class'] });
    }
    const emailInput = document.getElementById('login-email');
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            if (this.value.trim()) {
                checkFaceBiometry(this.value.trim());
            }
        });
    }
});

/* Re-avalia a aba de biometria quando ela é exibida */
const origSwitchConfigTab = window.switchConfigTab;
if (origSwitchConfigTab) {
    window.switchConfigTab = function(event, tabName) {
        origSwitchConfigTab(event, tabName);
        if (tabName === 'biometria') {
            setTimeout(updateFaceStatusUI, 300);
        } else {
            if (faceIsCapturing) {
                cleanupFaceCapture();
            }
        }
    };
}
