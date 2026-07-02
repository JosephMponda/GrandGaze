/**
 * MUST EMR Frontend App Logic
 * - CSRF token injection for HTMX
 * - Service worker registration
 * - Offline queue management (IndexedDB)
 * - Connection status indicator
 */

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

// indexdb implemetnted for offline sycnc
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

// for fomrs to be offline-capable for interception everytime it i marked offline=true kinda ...
// Only intercept forms marked with data-offline-capable="true"
document.addEventListener('htmx:beforeRequest', async (event) => {
  const form = event.detail.xhr.htmx?.target?.closest('[data-offline-capable="true"]');
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
      showToast('Saved offline — will sync when connected', 'info');
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
            showToast(`Conflict on ${item.form_type} — review and resubmit`, 'warning');
          } else {
            showToast(`Sync failed: ${data.message || 'Unknown error'}`, 'critical');
          }
        }
      } catch (error) {
        console.error('Sync error:', error);
        showToast('Sync failed — will retry', 'warning');
      }
    }
  } catch (error) {
    console.error('Failed to sync queued items:', error);
  }
}

//  Toast Notifications 
function showToast(message, severity = 'info') {
  const toast = document.createElement('div');
  toast.className = `fixed top-4 right-4 alert alert-${severity} shadow-lg z-50`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 4000);
}

//  Initialize 
initDB().catch((error) => console.error('Database init failed:', error));

// Update offline indicator on page load
if (!navigator.onLine) {
  offlineIndicator?.classList.remove('hidden');
}
