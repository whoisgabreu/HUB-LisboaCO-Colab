const senhaInput = document.getElementById("senha");
const toggleIcon = document.getElementById("toggleSenha");

toggleIcon.addEventListener("click", () => {
    const isPassword = senhaInput.type === "password";
    senhaInput.type = isPassword ? "text" : "password";
    toggleIcon.classList.toggle("fa-eye");
    toggleIcon.classList.toggle("fa-eye-slash");
});