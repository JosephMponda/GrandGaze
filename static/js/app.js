/**
 * Client-side offline support for clinical submissions.
 * Only forms explicitly marked data-offline-capable are queued. This avoids
 * treating a server-only workflow as completed when the device is offline.
 */
(function () {
  if (window.__MUST_EMR_APP_LOADED) return;
  window.__MUST_EMR_APP_LOADED = true;

  const DB_NAME = 'must_emr_offline';
  const DB_VERSION = 2;
  const STORE_NAME = 'sync_queue';
  let offlineUser = currentOfflineUser();
  let dbPromise;
  let syncing = false;
  let lastOfflineToast = 0;
  let serverReachable = navigator.onLine;

  async function probeServer() {
    if (!navigator.onLine) {
      serverReachable = false;
      updateConnectionStatus();
      return false;
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    try {
      const response = await fetch('/health/', {
        cache: 'no-store', credentials: 'same-origin', signal: controller.signal,
      });
      serverReachable = response.ok;
    } catch (_) {
      serverReachable = false;
    } finally {
      clearTimeout(timeout);
      updateConnectionStatus();
    }
    return serverReachable;
  }

  function openDB() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      request.onupgradeneeded = () => {
        const store = request.result.objectStoreNames.contains(STORE_NAME)
          ? request.transaction.objectStore(STORE_NAME)
          : request.result.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
        if (!store.indexNames.contains('created_at')) store.createIndex('created_at', 'created_at');
      };
    });
    return dbPromise;
  }

  async function withStore(mode, operation) {
    const database = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, mode);
      const request = operation(transaction.objectStore(STORE_NAME));
      transaction.onabort = () => reject(transaction.error);
      transaction.onerror = () => reject(transaction.error);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  const queueSubmission = (submission) => withStore('readwrite', (store) => store.add(submission));
  const deleteSubmission = (id) => withStore('readwrite', (store) => store.delete(id));
  const updateSubmission = (submission) => withStore('readwrite', (store) => store.put(submission));
  const queuedSubmissions = async () => {
    const items = await withStore('readonly', (store) => store.getAll());
    return items.sort((a, b) => a.created_at.localeCompare(b.created_at));
  };

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content
      || document.querySelector('[name=csrfmiddlewaretoken]')?.value
      || '';
  }

  function currentOfflineUser() {
    return document.getElementById('offline-session')?.dataset.user || document.body.dataset.offlineUser || '';
  }

  function prepareLocalWorkspace() {
    if (!offlineUser || !window.MUSTOffline) return Promise.resolve();
    localStorage.setItem('must_emr_offline_csrf', csrfToken());
    return window.MUSTOffline.configure(offlineUser).then(async () => {
      if (!sessionStorage.getItem(`must-emr-bootstrap-${offlineUser}`) && await probeServer()) {
        await window.MUSTOffline.bootstrap();
        sessionStorage.setItem(`must-emr-bootstrap-${offlineUser}`, 'true');
      }
    });
  }

  function formPayload(form) {
    const payload = {};
    new FormData(form).forEach((value, key) => {
      if (key === 'csrfmiddlewaretoken') return;
      if (value instanceof File) throw new Error('Attachments cannot be stored for offline sync.');
      if (Object.hasOwn(payload, key)) {
        payload[key] = Array.isArray(payload[key]) ? payload[key].concat(value) : [payload[key], value];
      } else {
        payload[key] = value;
      }
    });
    Object.entries(form.dataset).forEach(([key, value]) => {
      if (key.startsWith('offline') && key !== 'offlineCapable' && key !== 'offlineFormType') {
        payload[key.replace(/^offline/, '').replace(/^[A-Z]/, (letter) => letter.toLowerCase())] = value;
      }
    });
    return payload;
  }

  function setFormSavedState(form) {
    form.reset();
    form.querySelectorAll('[type="submit"]').forEach((button) => {
      button.disabled = false;
      if (button.dataset.originalHtml) button.innerHTML = button.dataset.originalHtml;
    });
  }

  async function queueForm(form) {
    const formType = form.dataset.formType;
    if (!formType) return false;
    if (form.__mustQueuePromise) return form.__mustQueuePromise;
    form.__mustQueuePromise = (async () => {
    try {
      await queueSubmission({
        client_uuid: crypto.randomUUID(),
        form_type: formType,
        payload_json: formPayload(form),
        owner_id: offlineUser,
        created_at: new Date().toISOString(),
        attempts: 0,
        state: 'pending',
      });
      setFormSavedState(form);
      updateQueueIndicator();
      requestBackgroundSync();
      window.showToast('Saved on this device. It will sync when the connection returns.', 'info');
      return true;
    } catch (error) {
      console.error('Offline queue failure:', error);
      window.showToast(error.message || 'Could not save this change on the device.', 'critical');
      return false;
    }
    })();
    try {
      return await form.__mustQueuePromise;
    } finally {
      delete form.__mustQueuePromise;
    }
  }

  async function requestBackgroundSync() {
    try {
      const registration = await navigator.serviceWorker?.ready;
      if (registration?.sync) await registration.sync.register('must-emr-sync-queue');
    } catch (_) {
      // The online event remains the compatibility fallback.
    }
  }

  async function syncQueuedItems() {
    if (syncing || !navigator.onLine || !serverReachable) return;
    syncing = true;
    try {
      const items = (await queuedSubmissions()).filter((item) => item.owner_id === offlineUser);
      let applied = 0;
      for (const item of items) {
        if (item.state === 'needs_review') continue;
        try {
          const response = await fetch('/api/sync/submit/', {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            body: JSON.stringify(item),
          });
          const data = await response.json().catch(() => ({}));
          if (response.ok && ['applied', 'already_applied'].includes(data.status)) {
            await deleteSubmission(item.id);
            applied += 1;
          } else if (response.ok && data.status === 'conflict') {
            item.state = 'needs_review';
            item.error = data.conflict_note || 'Server reported a clinical conflict.';
            await updateSubmission(item);
          } else if (response.status >= 400 && response.status < 500) {
            item.state = 'needs_review';
            item.error = data.error || 'The server could not validate this saved change.';
            await updateSubmission(item);
          } else {
            item.attempts += 1;
            await updateSubmission(item);
            break;
          }
        } catch (_) {
          serverReachable = false;
          updateConnectionStatus();
          break;
        }
      }
      if (applied) window.showToast(`${applied} offline change${applied === 1 ? '' : 's'} synced.`, 'success');
    } finally {
      syncing = false;
      updateQueueIndicator();
    }
  }

  async function updateQueueIndicator() {
    try {
      const items = (await queuedSubmissions()).filter((item) => item.owner_id === offlineUser);
      const pending = items.filter((item) => item.state !== 'needs_review').length;
      const review = items.length - pending;
      const label = document.getElementById('offline-queue-count');
      if (label) label.textContent = review ? `${pending} waiting, ${review} needs review` : `${pending} waiting to sync`;
      document.getElementById('offline-queue-status')?.classList.toggle('hidden', !items.length);
    } catch (_) { /* IndexedDB may be unavailable in a private browser session. */ }
  }

  function updateConnectionStatus() {
    const offline = !navigator.onLine || !serverReachable;
    document.getElementById('offline-indicator')?.classList.toggle('hidden', !offline);
    document.getElementById('connection-online')?.classList.toggle('hidden', offline);
    document.getElementById('connection-offline')?.classList.toggle('hidden', !offline);
  }

  window.showToast = function (message, type = 'info', duration = 4500) {
    const add = () => Alpine.store('toasts').add(message, type, duration);
    if (window.Alpine && Alpine.store('toasts')) add();
    else document.addEventListener('alpine:initialized', add, { once: true });
  };

  document.body.addEventListener('htmx:configRequest', (event) => {
    event.detail.headers['X-CSRFToken'] = csrfToken();
  });

  // hx-boost can replace the authenticated page without rerunning app.js.
  // Read the fresh identity marker before configuring the local replica.
  document.body.addEventListener('htmx:afterSettle', () => {
    const nextUser = currentOfflineUser();
    if (nextUser && nextUser !== offlineUser) {
      offlineUser = nextUser;
      prepareLocalWorkspace().catch((error) => console.error('Offline workspace setup failed:', error));
    }
  });

  // HTMX has already captured the native submit by this point, so prevent its
  // request here and store the form locally instead.
  document.body.addEventListener('htmx:beforeRequest', (event) => {
    const form = event.detail.elt?.closest?.('form[data-offline-capable="true"]');
    if (!form || serverReachable) return;
    event.preventDefault();
    queueForm(form);
  });

  document.addEventListener('submit', (event) => {
    const form = event.target.closest?.('form[data-offline-capable="true"]');
    if (!form || window.htmx?.closest(form, '[hx-post], [hx-put], [hx-delete]')) return;
    event.preventDefault();
    // Regular Django forms would otherwise navigate to a browser error page
    // when the LAN/server is down. Probe first, then submit or queue.
    probeServer().then((reachable) => {
      if (reachable) form.submit();
      else queueForm(form);
    });
  }, true);

  window.addEventListener('offline', () => {
    updateConnectionStatus();
    const now = Date.now();
    if (now - lastOfflineToast > 8000) {
      window.showToast('Connection lost. Supported clinical forms will save on this device.', 'warning');
      lastOfflineToast = now;
    }
  });
  window.addEventListener('online', () => {
    probeServer().then((reachable) => {
      if (!reachable) return;
      syncQueuedItems();
      window.MUSTOffline?.sync();
    });
  });

  navigator.serviceWorker?.addEventListener('message', (event) => {
    if (event.data?.action === 'syncNow') syncQueuedItems();
  });
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/js/sw.js').then(() => navigator.serviceWorker.ready)
        .then((registration) => registration.active?.postMessage({ action: 'cachePage', url: window.location.href }))
        .catch((error) => console.error('Service worker registration failed:', error));
    });
  }

  document.body.addEventListener('htmx:sendError', (event) => {
    serverReachable = false;
    updateConnectionStatus();
    const form = event.detail.elt?.closest?.('form[data-offline-capable="true"]');
    if (form) {
      queueForm(form);
      return;
    }
    window.showToast('The server could not be reached. This screen is available only while connected.', 'warning');
  });

  openDB().then(async () => {
    updateQueueIndicator();
    try { await prepareLocalWorkspace(); } catch (error) { console.error('Offline workspace setup failed:', error); }
    probeServer().then((reachable) => {
      if (!reachable) return;
      syncQueuedItems();
      window.MUSTOffline?.sync();
    });
    setInterval(() => probeServer().then((reachable) => {
      if (!reachable) return;
      syncQueuedItems();
      window.MUSTOffline?.sync();
    }), 15000);
  })
    .catch((error) => console.error('IndexedDB is unavailable:', error));
})();
