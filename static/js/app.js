/**
 * MUST EMR Frontend App Logic
 * - CSRF token injection for HTMX
 * - Service worker registration
 * - Offline queue management (IndexedDB)
 * - Connection status indicator
 *
 * Wrapped in an IIFE to prevent "Identifier already declared" errors
 * when hx-boost re-executes this script on boosted navigations.
 */
(function () {
  // Guard: skip re-initialization if already loaded in this page lifecycle
  if (window.__MUST_EMR_APP_LOADED) return;
  window.__MUST_EMR_APP_LOADED = true;

  // CSRF Token Injection for HTMX
  // Django requires CSRF token on all state-changing requests (POST, PUT, DELETE)
  document.body.addEventListener('htmx:configRequest', (event) => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
      event.detail.headers['X-CSRFToken'] = csrfToken;
    }
  });

  // register service worker here
  // Handles offline caching and background sync
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/js/sw.js')
        .then((registration) => {
          console.log('Service Worker registered:', registration);
        })
        .catch((error) => {
          console.error('Service Worker registration failed:', error);
        });
    });
  }

  // indexdb implemented for offline sync
  const DB_NAME = 'must_emr_offline';
  const DB_VERSION = 1;
  const STORE_NAME = 'sync_queue';

  let db;

  async function initDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        db = request.result;
        resolve(db);
      };

      request.onupgradeneeded = (event) => {
        const database = event.target.result;
        if (!database.objectStoreNames.contains(STORE_NAME)) {
          database.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  async function addToQueue(item) {
    if (!db) await initDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.add({
        ...item,
        timestamp: new Date().toISOString(),
      });

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async function getQueuedItems() {
    if (!db) await initDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async function removeFromQueue(id) {
    if (!db) await initDB();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  // for forms to be offline-capable for interception everytime it is marked offline=true kinda ...
  // Only intercept forms marked with data-offline-capable="true"
  document.addEventListener('htmx:beforeRequest', async (event) => {
    const form = event.detail.elt?.closest('[data-offline-capable="true"]');
    if (!form) return;

    // Check if online
    if (!navigator.onLine) {
      event.preventDefault();

      const clientUuid = crypto.randomUUID();
      const formData = new FormData(form);
      const payload = Object.fromEntries(formData);

      try {
        await addToQueue({
          client_uuid: clientUuid,
          form_type: form.getAttribute('data-form-type') || 'unknown',
          method: form.method.toUpperCase() || 'POST',
          action: form.action,
          payload: payload,
        });

        // Show offline confirmation toast
        showToast('Saved offline - will sync when connected', 'info');
      } catch (error) {
        console.error('Failed to queue form submission:', error);
        showToast('Failed to save offline. Please try again.', 'critical');
      }
    }
  });

  //  Connection Status Indicator
  const offlineIndicator = document.getElementById('offline-indicator');

  window.addEventListener('offline', () => {
    offlineIndicator?.classList.remove('hidden');
  });

  window.addEventListener('online', () => {
    offlineIndicator?.classList.add('hidden');
    syncQueuedItems();
  });

  //  Sync Queued Items on Reconnect
  async function syncQueuedItems() {
    try {
      const items = await getQueuedItems();
      if (items.length === 0) return;

      for (const item of items) {
        try {
          const response = await fetch('/api/sync/submit/', {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
            },
            body: JSON.stringify(item),
          });

          if (response.ok) {
            await removeFromQueue(item.id);
            showToast(`Synced: ${item.form_type}`, 'success');
          } else {
            const data = await response.json();
            if (data.status === 'conflict') {
              showToast(`Conflict on ${item.form_type} - review and resubmit`, 'warning');
            } else {
              showToast(`Sync failed: ${data.message || 'Unknown error'}`, 'critical');
            }
          }
        } catch (error) {
          console.error('Sync error:', error);
          showToast('Sync failed - will retry', 'warning');
        }
      }
    } catch (error) {
      console.error('Failed to sync queued items:', error);
    }
  }

  // Toast Notifications (Alpine store-driven) 
  // Public API used by offline sync, HTMX error handling, and Django messages.
  window.showToast = function (message, type = 'info', duration = 4500) {
    // Wait for Alpine to be ready
    const dispatch = () => {
      if (window.Alpine && Alpine.store('toasts')) {
        Alpine.store('toasts').add(message, type, duration);
      } else {
        // Fallback: retry after Alpine initialises
        document.addEventListener('alpine:initialized', () => {
          Alpine.store('toasts').add(message, type, duration);
        }, { once: true });
      }
    };
    dispatch();
  };

  // HTMX Button Loading States 
  // On any HTMX request, find the triggering form's submit button and
  // replace its content with a spinner. Restored after the request completes.
  document.body.addEventListener('htmx:beforeRequest', (e) => {
    const trigger = e.detail.elt;
    const form = trigger.closest('form') || (trigger.tagName === 'FORM' ? trigger : null);
    if (!form) return;
    const btn = form.querySelector('[type="submit"]');
    if (!btn || btn.dataset.loading) return;
    btn.dataset.loading = 'true';
    btn.dataset.originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="animate-spin -ml-0.5 mr-2 h-4 w-4 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>Processing…`;
  });

  function restoreButtons() {
    document.querySelectorAll('[data-loading="true"]').forEach((btn) => {
      btn.innerHTML = btn.dataset.originalHtml || btn.innerHTML;
      btn.disabled = false;
      delete btn.dataset.loading;
      delete btn.dataset.originalHtml;
    });
  }

  document.body.addEventListener('htmx:afterRequest', (e) => {
    restoreButtons();
    // Surface Django-level 5xx errors as toast
    const status = e.detail.xhr?.status;
    if (status >= 500) {
      window.showToast('Server error (500). The backend team has been notified.', 'critical');
    }
  });

  document.body.addEventListener('htmx:responseError', () => {
    restoreButtons();
    window.showToast('Request failed. Check your connection and try again.', 'critical');
  });

  document.body.addEventListener('htmx:sendError', () => {
    restoreButtons();
    window.showToast('Cannot reach server. You may be offline.', 'warning');
  });

  // Also restore on regular (non-HTMX) form submit
  document.addEventListener('submit', (e) => {
    const btn = e.target.querySelector('[type="submit"]');
    if (!btn || btn.dataset.loading) return;
    btn.dataset.loading = 'true';
    btn.dataset.originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="animate-spin -ml-0.5 mr-2 h-4 w-4 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>Processing…`;
  });

  //  Initialize
  initDB().catch((error) => console.error('Database init failed:', error));

  // Update offline indicator on page load
  if (!navigator.onLine) {
    offlineIndicator?.classList.remove('hidden');
  }
})();
