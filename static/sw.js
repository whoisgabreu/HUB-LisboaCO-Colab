/* Service Worker do HUB Lisboa&CO
 * Estratégia: network-first para navegação (fallback offline) e
 * stale-while-revalidate para assets estáticos. Nunca cacheia API,
 * login ou imagens de usuário/feed.
 */
const CACHE_VERSION = "hub-pwa-v5";
const CACHE_NAME = `${CACHE_VERSION}-static`;
const OFFLINE_URL = "/offline";

const PRECACHE_URLS = [
  OFFLINE_URL,
  "/manifest.webmanifest",
  "/static/style/styles.css",
  "/static/style/tema-claro.css",
  "/static/style/hub-modal.css",
  "/static/style/pwa.css",
  "/static/js/app.js",
  "/static/js/hub-modal.js",
  "/static/js/pwa.js",
  "/static/images/v4-logo.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-maskable-512.png",
  "/static/favicon.ico",
  "/static/apple-touch-icon.png",
  "/static/vendor/fontawesome/css/all.min.css",
  "/static/vendor/fontawesome/webfonts/fa-solid-900.woff2",
  "/static/vendor/fontawesome/webfonts/fa-regular-400.woff2",
  "/static/vendor/fontawesome/webfonts/fa-brands-400.woff2",
  "/static/vendor/fonts/fonts.css",
  "/static/vendor/fonts/files/inter-400-latin.woff2",
  "/static/vendor/fonts/files/inter-400-latin-ext.woff2",
  "/static/vendor/fonts/files/poppins-300-latin.woff2",
  "/static/vendor/fonts/files/poppins-300-latin-ext.woff2",
  "/static/vendor/fonts/files/poppins-400-latin.woff2",
  "/static/vendor/fonts/files/poppins-400-latin-ext.woff2",
  "/static/vendor/fonts/files/poppins-500-latin.woff2",
  "/static/vendor/fonts/files/poppins-500-latin-ext.woff2",
  "/static/vendor/fonts/files/poppins-600-latin.woff2",
  "/static/vendor/fonts/files/poppins-600-latin-ext.woff2",
  "/static/vendor/fonts/files/poppins-700-latin.woff2",
  "/static/vendor/fonts/files/poppins-700-latin-ext.woff2",
];

const NAO_CACHEAR = [
  "/api/",
  "/auth/",
];

function deveIgnorar(url) {
  if (url.origin !== self.location.origin) return true;
  if (NAO_CACHEAR.some((prefixo) => url.pathname.startsWith(prefixo))) {
    return true;
  }
  if (url.pathname === "/login" || url.pathname.startsWith("/login/")) return true;
  if (url.pathname.startsWith("/static/images/profile_pictures/")) return true;
  if (url.pathname.startsWith("/static/images/feed/")) return true;
  return false;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((nomes) =>
      Promise.all(
        nomes
          .filter((nome) => nome !== CACHE_NAME)
          .map((nome) => caches.delete(nome))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const rede = fetch(request)
    .then((resp) => {
      if (resp && resp.ok) cache.put(request, resp.clone());
      return resp;
    })
    .catch(() => null);

  if (cached) return cached;
  const resp = await rede;
  return resp || new Response("", { status: 504, statusText: "Offline" });
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (deveIgnorar(url)) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(async () => {
        const offline = await caches.match(OFFLINE_URL);
        return offline || new Response("Sem conexão.", {
          status: 503,
          headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
      })
    );
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(staleWhileRevalidate(request));
  }
});
