(function () {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const menuButton = document.getElementById("dgHamburger");
  const sidebar = document.getElementById("dgSidebar");
  const overlay = document.querySelector("[data-dg-sidebar-overlay]");
  const closeButton = document.querySelector("[data-dg-menu-close]");
  const mobileBreakpoint = 900;
  let desktopCollapsed = false;

  function isMobile() {
    return window.innerWidth <= mobileBreakpoint;
  }

  function syncTheme() {
    const light = root.classList.contains("tema-claro") || body.classList.contains("tema-claro");
    root.setAttribute("data-bs-theme", light ? "light" : "dark");
  }

  function setSidebar(open) {
    if (isMobile()) {
      body.classList.remove("dg-sidebar-collapsed");
      body.classList.toggle("dg-sidebar-open", open);
    } else {
      desktopCollapsed = !open;
      body.classList.remove("dg-sidebar-open");
      body.classList.toggle("dg-sidebar-collapsed", desktopCollapsed);
    }
    if (menuButton) menuButton.setAttribute("aria-expanded", String(open));
    if (open && closeButton) closeButton.focus({ preventScroll: true });
  }

  function syncSidebarViewport() {
    body.classList.remove("dg-sidebar-open");
    body.classList.toggle("dg-sidebar-collapsed", !isMobile() && desktopCollapsed);
    if (menuButton) {
      menuButton.setAttribute("aria-expanded", String(!isMobile() && !desktopCollapsed));
    }
  }

  menuButton?.addEventListener("click", function () {
    const open = isMobile()
      ? !body.classList.contains("dg-sidebar-open")
      : body.classList.contains("dg-sidebar-collapsed");
    setSidebar(open);
  });
  closeButton?.addEventListener("click", function () { setSidebar(false); });
  overlay?.addEventListener("click", function () { setSidebar(false); });

  sidebar?.querySelectorAll(".dg-nav-item").forEach(function (link) {
    link.addEventListener("click", function () {
      if (isMobile()) setSidebar(false);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isMobile() && body.classList.contains("dg-sidebar-open")) {
      setSidebar(false);
      menuButton?.focus({ preventScroll: true });
    }
  });

  window.addEventListener("resize", syncSidebarViewport);

  window.addEventListener("storage", function (event) {
    if (event.key !== "tema") return;
    const light = event.newValue !== "escuro";
    root.classList.toggle("tema-claro", light);
    body.classList.toggle("tema-claro", light);
    syncTheme();
  });

  new MutationObserver(syncTheme).observe(root, { attributes: true, attributeFilter: ["class"] });
  new MutationObserver(syncTheme).observe(body, { attributes: true, attributeFilter: ["class"] });
  syncSidebarViewport();
  syncTheme();

  if (window.bootstrap?.Tooltip) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (element) {
      window.bootstrap.Tooltip.getOrCreateInstance(element, { trigger: "hover focus" });
    });
  }
})();
