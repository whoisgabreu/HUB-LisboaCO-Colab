/**
 * hub-modal.js — Modal global de alerta/confirmação/prompt do HUB.
 *
 * Substitui os diálogos nativos (alert/confirm/prompt) por um overlay
 * centralizado e tematizado. `window.alert` é sobrescrito automaticamente;
 * `confirm` e `prompt` são assíncronos (use `await HubModal.confirm(...)`).
 */
(function () {
    "use strict";

    let overlay = null;
    let resolver = null;
    let lastFocus = null;

    function ensure() {
        if (overlay) return overlay;
        overlay = document.createElement("div");
        overlay.className = "hub-modal-overlay";
        overlay.innerHTML = [
            '<div class="hub-modal" role="dialog" aria-modal="true">',
            '  <div class="hub-modal-title" data-hm-title></div>',
            '  <div class="hub-modal-msg" data-hm-msg></div>',
            '  <input type="text" class="hub-modal-input" data-hm-input hidden>',
            '  <div class="hub-modal-actions">',
            '    <button type="button" class="hub-modal-btn" data-hm-cancel hidden></button>',
            '    <button type="button" class="hub-modal-btn primary" data-hm-ok>OK</button>',
            '  </div>',
            '</div>',
        ].join("");
        document.body.appendChild(overlay);

        overlay.addEventListener("mousedown", (e) => {
            if (e.target === overlay) close(false);
        });
        overlay.querySelector("[data-hm-ok]").addEventListener("click", () => {
            const input = overlay.querySelector("[data-hm-input]");
            close(input.hidden ? true : input.value);
        });
        overlay.querySelector("[data-hm-cancel]").addEventListener("click", () => close(false));
        overlay.querySelector("[data-hm-input]").addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                overlay.querySelector("[data-hm-ok]").click();
            }
        });
        return overlay;
    }

    function onKey(e) {
        if (!overlay || !overlay.classList.contains("aberto")) return;
        if (e.key === "Escape") {
            e.preventDefault();
            close(false);
        } else if (e.key === "Enter") {
            const input = overlay.querySelector("[data-hm-input]");
            if (!input.hidden && document.activeElement === input) return;
            e.preventDefault();
            overlay.querySelector("[data-hm-ok]").click();
        }
    }

    function close(result) {
        if (!overlay) return;
        overlay.classList.remove("aberto");
        document.removeEventListener("keydown", onKey, true);
        const done = resolver;
        resolver = null;
        setTimeout(() => {
            if (overlay) overlay.style.display = "none";
            if (lastFocus && lastFocus.focus) {
                try { lastFocus.focus(); } catch (e) { /* ignore */ }
            }
            lastFocus = null;
        }, 160);
        if (done) done(result);
    }

    function open(opts) {
        ensure();
        return new Promise((resolve) => {
            resolver = resolve;
            lastFocus = document.activeElement;

            const titleEl = overlay.querySelector("[data-hm-title]");
            const msgEl = overlay.querySelector("[data-hm-msg]");
            const input = overlay.querySelector("[data-hm-input]");
            const ok = overlay.querySelector("[data-hm-ok]");
            const cancel = overlay.querySelector("[data-hm-cancel]");
            const box = overlay.querySelector(".hub-modal");

            box.classList.toggle("hub-modal-wide", !!opts.wide);

            titleEl.textContent = opts.title || "";
            titleEl.style.display = opts.title ? "" : "none";

            msgEl.style.whiteSpace = opts.html ? "normal" : "pre-wrap";
            if (opts.html) {
                msgEl.innerHTML = opts.message == null ? "" : String(opts.message);
            } else {
                msgEl.textContent = opts.message == null ? "" : String(opts.message);
            }

            ok.textContent = opts.okLabel || (opts.prompt ? "Salvar" : "OK");
            ok.classList.toggle("danger", !!opts.danger);

            if (opts.cancel) {
                cancel.hidden = false;
                cancel.textContent = opts.cancelLabel || "Cancelar";
            } else {
                cancel.hidden = true;
            }

            if (opts.prompt) {
                input.hidden = false;
                input.value = opts.defaultValue == null ? "" : String(opts.defaultValue);
                input.placeholder = opts.placeholder || "";
            } else {
                input.hidden = true;
            }

            overlay.style.display = "flex";
            void overlay.offsetWidth; // força reflow p/ animação
            overlay.classList.add("aberto");
            document.addEventListener("keydown", onKey, true);

            setTimeout(() => {
                if (opts.prompt) {
                    input.focus();
                    input.select();
                } else {
                    ok.focus();
                }
            }, 30);
        });
    }

    const HubModal = {
        alert(message, opts) {
            return open(Object.assign({ cancel: false, okLabel: "OK" }, opts || {}, { message }));
        },
        confirm(message, opts) {
            return open(Object.assign(
                { cancel: true, okLabel: "Confirmar", cancelLabel: "Cancelar" },
                opts || {},
                { message },
            )).then((r) => r === true);
        },
        prompt(message, opts) {
            return open(Object.assign(
                { cancel: true, prompt: true, okLabel: "Salvar", cancelLabel: "Cancelar" },
                opts || {},
                { message },
            )).then((r) => (r === false ? null : r));
        },
    };

    window.HubModal = HubModal;
    // alert() é sincrono e ninguém usa seu retorno → troca transparente.
    window.alert = function (m) { HubModal.alert(m); };
})();
