/**
 * placeholders.js - Logic for development pages
 */

document.addEventListener('DOMContentLoaded', () => {
    // Fill common user info even on placeholder pages
    const sessionUser = {
        name: "Gabriel Henrique",
        role: "Assistente Tech - Gerência - Admin"
    };

    const headerName = document.getElementById('headerUserName');
    if (headerName) headerName.innerText = sessionUser.name;

    const headerRole = document.getElementById('headerUserRole');
    if (headerRole) headerRole.innerText = sessionUser.role;

    const sidebarName = document.getElementById('sidebarUserName');
    if (sidebarName) sidebarName.innerText = sessionUser.name;
});
