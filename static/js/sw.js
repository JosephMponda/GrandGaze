/**
 * MUST EMR Service Worker
 * Handles offline caching and network interception
 * 
 * Caching strategy:
 * - Network-first for GET requests (with cache fallback)
 * - Form POSTs queued locally via IndexedDB (in app.js)
 * - Static assets cached aggressively
 */

const CACHE_VERSION = 'v3';
const CACHE_NAME = `must-emr-${CACHE_VERSION}`;

// Assets to cache on install (app shell + static dependencies)
const ASSETS_TO_CACHE = [
  '/',
  '/accounts/login/',
  '/static/css/app.css',
  '/static/js/htmx.min.js',
  '/static/js/alpinejs.min.js',
  '/static/js/idb.min.js',
  '/static/js/app.js',
  '/static/img/must-logo.png',
  '/static/img/logos/GSL-Official-Logo.png',
];

// ===== Install Event =====
// Pre-cache essential assets for offline app shell
self.addEventListener('install', (event) => {
  console.log('Service Worker: Install event');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Service Worker: Caching assets');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  // Immediately take control, don't wait for other clients
  self.skipWaiting();
});

// ===== Activate Event =====
// Clean up old cache versions
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activate event');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// ===== Fetch Event =====
// Intercept network requests
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only handle HTTP/HTTPS requests
  if (!request.url.startsWith('http')) {
    return;
  }

  // Network-first strategy for GET requests
  if (request.method === 'GET') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful responses
          if (response.ok) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return response;
        })
        .catch(() => {
          // Fall back to cache on network error
          return caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
              console.log('Service Worker: Serving from cache:', request.url);
              return cachedResponse;
            }
            // No cache hit, show offline page if available
            return caches.match('/offline.html') || new Response('Offline', { status: 503 });
          });
        })
    );
  }

  // For POST/PUT/DELETE, let the app handle queuing
  // Don't intercept state-changing requests here
});

// ===== Message Event =====
// Handle messages from the app (e.g., manual cache clear)
self.addEventListener('message', (event) => {
  if (event.data.action === 'clearCache') {
    caches.delete(CACHE_NAME).then(() => {
      console.log('Service Worker: Cache cleared');
      event.ports[0].postMessage({ success: true });
    });
  }

  if (event.data.action === 'getStatus') {
    event.ports[0].postMessage({ status: 'active' });
  }
});

// ===== Background Sync (Future) =====
// When network returns, browser will trigger this to replay queued submissions
// Currently handled by app.js online event, but SW is ready for future expansion
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-queue') {
    event.waitUntil(
      // Signal the client to sync
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ action: 'syncNow' });
        });
      })
    );
  }
});
