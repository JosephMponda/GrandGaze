const VERSION = 'v12';
const STATIC_CACHE = `must-emr-static-${VERSION}`;
const PAGE_CACHE = `must-emr-pages-${VERSION}`;
const APP_SHELL = [
  '/', '/accounts/login/', '/static/css/app.css', '/static/js/htmx.min.js',
  '/static/js/alpinejs.min.js', '/static/js/chart.min.js', '/static/js/app.js?v=9',
  '/static/js/offline-client.js?v=12', '/static/css/offline-workspace.css?v=11',
  '/static/offline-workspace.html', '/static/img/must-logo.png',
  '/static/img/logos/GSL-Official-Logo.png', '/static/offline.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(STATIC_CACHE).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((names) => Promise.all(names
    .filter((name) => name.startsWith('must-emr-') && ![STATIC_CACHE, PAGE_CACHE].includes(name))
    .map((name) => caches.delete(name)))));
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.method !== 'GET') {
    // A logout must remove cached clinical pages from the browser profile.
    if (url.pathname === '/accounts/logout/') event.waitUntil(caches.delete(PAGE_CACHE));
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      if (response.ok) caches.open(STATIC_CACHE).then((cache) => cache.put(request, response.clone()));
      return response;
    })));
    return;
  }

  // hx-boosted links are fetch requests, not browser navigations, but are
  // still full clinical pages that must be available after a connection drop.
  if (request.mode === 'navigate' || request.headers.get('HX-Request') === 'true') {
    event.respondWith(fetch(request).then((response) => {
      if (response.ok && !url.pathname.startsWith('/accounts/logout')) {
        caches.open(PAGE_CACHE).then((cache) => cache.put(request, response.clone()));
      }
      return response;
    }).catch(async () => (await caches.match(request)) || (await caches.match('/static/offline.html'))));
  }
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'must-emr-sync-queue') {
    event.waitUntil(self.clients.matchAll({ type: 'window' }).then((clients) => {
      clients.forEach((client) => client.postMessage({ action: 'syncNow' }));
    }));
  }
});

self.addEventListener('message', (event) => {
  if (event.data?.action !== 'cachePage' || !event.data.url) return;
  const url = new URL(event.data.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/accounts/logout')) return;
  event.waitUntil(fetch(url, { credentials: 'same-origin' }).then((response) => {
    if (response.ok) return caches.open(PAGE_CACHE).then((cache) => cache.put(url, response));
    return undefined;
  }).catch(() => undefined));
});
