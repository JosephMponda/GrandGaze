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
            body: JSON.stringify({ client_uuid: item.client_uuid, form_type: item.form_type, payload_json: item.payload_json }),
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

/* ── Onboarding Tours ─────────────────────────────────────────────────── */
(function () {
  var page = document.body.dataset.page;

  var tours = {

    /* ── Dashboard ── */
    'accounts:dashboard': {
      id: 'dashboard',
      steps: [
        { element: '#welcome-card', title: 'Command Center', content: 'The clinical command center gives you a live overview of the entire system — patient volume, open encounters, alerts, and pending work items.', placement: 'bottom' },
        { element: '#stat-cards', title: 'Quick Stats', content: 'These cards show key metrics at a glance: patients registered today, open encounters, critical alerts, and pending tasks. Click any card to drill down.', placement: 'bottom' },
        { element: '#welcome-card a[href*="register"]', title: 'Register Patient', content: 'Click here to start a new patient registration. This is the fastest way to add a patient to the Master Patient Index.', placement: 'bottom' },
        { element: '#welcome-card a[href*="analytics"]', title: 'View Analytics', content: 'Open the analytics dashboard for charts, trends, and operational reports across the facility.', placement: 'bottom' },
        { element: '#quick-links-section', title: 'Quick Links', content: 'These role-gated buttons let you jump straight to frequently used sections — patient search, alerts, inpatient board, and more.', placement: 'bottom' },
        { element: '#recent-alerts-section', title: 'Recent Alerts', content: 'Critical clinical alerts appear here. Each alert shows the patient name, severity, and time raised. Click to review and acknowledge.', placement: 'top' },
        { element: '#tasks-section', title: 'Assigned Tasks', content: 'Tasks assigned to you are listed here. Use the checkboxes to mark items complete or update their status directly from the dashboard.', placement: 'top' },
        { element: '#activityChart', title: 'Workload Charts', content: 'Visual workload and severity charts help you quickly assess team capacity and patient acuity across departments.', placement: 'left' },
      ]
    },

    /* ── Register Patient ── */
    'patients:register': {
      id: 'patient_register',
      steps: [
        { element: '#registration-title', title: 'Patient Registration', content: 'This form adds a new patient to the Master Patient Index. All fields marked with an asterisk (*) are required.', placement: 'bottom' },
        { element: 'form', title: 'Form Fields', content: 'Enter the patient\'s full name, date of birth, sex, phone number, and address. The patient number will be auto-generated on save.', placement: 'top' },
        { element: 'button[type="submit"]', title: 'Save Patient', content: 'Click this button to save the patient record. After saving, you\'ll be redirected to the patient\'s profile page.', placement: 'bottom' },
        { element: '.btn-secondary', title: 'Cancel Button', content: 'Use this to cancel the registration and return to the dashboard without saving.', placement: 'bottom' },
      ]
    },

    /* ── Patient List ── */
    'patients:list': {
      id: 'patient_list',
      steps: [
        { element: 'h1', title: 'Patient List', content: 'Browse all registered patients in the system. Use the search and filter tools to find specific patients quickly.', placement: 'bottom' },
        { element: 'input[name="q"]', title: 'Search Bar', content: 'Type a patient name or patient number to search. Results filter in real-time when you click the Filter button.', placement: 'bottom' },
        { element: 'input[name="date_from"]', title: 'Date Filter', content: 'Filter by registration date. Combine with time filter for precise searches.', placement: 'bottom' },
        { element: 'input[name="time_to"]', title: 'Time Filter', content: 'Filter by registration time of day. Useful for finding patients registered during specific shifts.', placement: 'bottom' },
        { element: 'table', title: 'Patient Table', content: 'Each row represents a patient. The Registered column shows the exact date and time of registration. Click any patient row to view their full profile.', placement: 'top' },
        { element: 'a[href*="register"]', title: 'Quick Register', content: 'Need to add a new patient? Use this button to jump directly to the registration form.', placement: 'bottom' },
      ]
    },

    /* ── Patient Profile ── */
    'patients:profile': {
      id: 'patient_profile',
      steps: [
        { element: '.flex.h-16.w-16', title: 'Patient Avatar', content: 'The patient\'s initials appear here alongside their full name and patient number. The category badge (Outpatient / Inpatient) shows their current status.', placement: 'right' },
        { element: '.grid.grid-cols-1.gap-4', title: 'Patient Summary', content: 'Demographic details and alert counts at a glance — sex, date of birth, open and critical alerts.', placement: 'bottom' },
        { element: 'a[href*="edit"]', title: 'Edit Patient', content: 'Update patient demographics, contact information, or consents from this button.', placement: 'bottom' },
        { element: 'a[href*="admit"]', title: 'Admit Patient', content: 'Convert this patient to inpatient status. This initiates the admission workflow.', placement: 'bottom' },
        { element: '.border-b.border-gray-200', title: 'Tab Navigation', content: 'Use these tabs to explore different sections: Encounters, Vitals, Pharmacy, Billing, Labs, Imaging, and Clinical Notes.', placement: 'top' },
      ]
    },

    /* ── Open Encounters ── */
    'encounters:open': {
      id: 'open_encounters',
      steps: [
        { element: 'h1', title: 'Open Encounters', content: 'This page lists all clinical encounters that have not yet been signed and locked. These are active notes requiring your attention.', placement: 'bottom' },
        { element: '.grid.gap-3.sm\\:grid-cols-3', title: 'Total Count', content: 'Shows the total number of unsigned encounters currently in the system.', placement: 'bottom' },
        { element: '.divide-y.divide-gray-100 > a', title: 'Encounter List', content: 'Each item shows the patient name, encounter type, and time created. Click any encounter to open it, review clinical data, and sign it.', placement: 'top' },
        { element: 'a[href*="dashboard"]', title: 'Back to Dashboard', content: 'Return to the main dashboard at any time.', placement: 'bottom' },
      ]
    },

    /* ── Encounter Detail ── */
    'encounters:detail': {
      id: 'encounter_detail',
      steps: [
        { element: 'h1 span:first-child', title: 'Clinical Encounter', content: 'This is the workspace for a single clinical encounter. Review patient information, document findings, and manage orders.', placement: 'bottom' },
        { element: '.bg-gray-50\\.overflow-y-auto', title: 'Patient Context Panel', content: 'The left sidebar shows the patient\'s vitals, allergies, and recent clinical context to inform your decision-making.', placement: 'right' },
        { element: '[name="diagnosis"]', title: 'Clinical Note', content: 'Document the history, examination findings, diagnosis, and treatment plan here. Structured templates help ensure completeness.', placement: 'left' },
        { element: 'button[name="sign"]', title: 'Sign & Lock', content: 'Once the encounter is complete, click this button to sign and lock the note. Signed encounters cannot be edited — only amended.', placement: 'bottom' },
      ]
    },

    /* ── Pharmacy Queue ── */
    'pharmacy:queue': {
      id: 'pharmacy_queue',
      steps: [
        { element: 'h1', title: 'Pharmacy Queue', content: 'Live prescription queue showing all medications awaiting dispensation. Monitor queue size and stock levels at a glance.', placement: 'bottom' },
        { element: '.grid.grid-cols-1.gap-3.sm\\:grid-cols-2', title: 'Queue Stats', content: 'Queue size shows pending prescriptions; low stock items flags medications that need reordering.', placement: 'bottom' },
        { element: '.divide-y.divide-gray-100', title: 'Prescription List', content: 'Each entry shows the patient, medication, dosage, and prescriber. Click to process or dispense.', placement: 'top' },
        { element: 'a[href*="stock"]', title: 'Stock Management', content: 'Access the full inventory view to check stock levels, record new stock receipts, and manage suppliers.', placement: 'bottom' },
      ]
    },

    /* ── Billing Dashboard ── */
    'billing:dashboard': {
      id: 'billing_dashboard',
      steps: [
        { element: 'h1', title: 'Billing Dashboard', content: 'Monitor invoice volume, payment flow, and outstanding balances from one screen.', placement: 'bottom' },
        { element: '.grid.grid-cols-1.gap-4.sm\\:grid-cols-2.xl\\:grid-cols-4', title: 'Revenue Stats', content: 'Key financial metrics: total invoices, outstanding amount, unpaid count, and today\'s revenue.', placement: 'bottom' },
        { element: 'a[href*="create"]', title: 'Create Invoice', content: 'Generate a new invoice for a patient. Select from existing encounters to auto-populate billing items.', placement: 'bottom' },
        { element: 'table', title: 'Invoice List', content: 'Browse all invoices with status indicators. Click any invoice to view details, record payments, or print.', placement: 'top' },
      ]
    },

    /* ── Analytics Dashboard ── */
    'reporting:analytics_dashboard': {
      id: 'analytics',
      steps: [
        { element: 'h1', title: 'Analytics Dashboard', content: 'Visual reports and trends across the facility. Use these charts to identify patterns and inform operational decisions.', placement: 'bottom' },
        { element: '.grid.grid-cols-1.gap-4.sm\\:grid-cols-2.xl\\:grid-cols-6', title: 'Key Metrics', content: 'At-a-glance counts for patients today, open encounters, pending labs, imaging, prescriptions, and unacknowledged alerts.', placement: 'bottom' },
        { element: '#moduleChart', title: 'Live Workload Mix', content: 'Bar chart showing open item counts by module. Click any bar to jump to that module\'s queue.', placement: 'top' },
        { element: '#severityChart', title: 'Alert Severity', content: 'Doughnut chart breaking down alerts by severity — critical, warning, and info. The legend below shows exact counts.', placement: 'left' },
        { element: '#analytics-alerts-section', title: 'Recent Alerts', content: 'Latest clinical alerts listed here with severity indicators. Click "View full feed" to see all recent alerts.', placement: 'top' },
      ]
    },

    /* ── Recent Alerts ── */
    'reporting:recent_alerts': {
      id: 'recent_alerts',
      steps: [
        { element: 'h1', title: 'Recent Alerts', content: 'Clinical alerts raised within the last 4 hours. Each alert requires review and acknowledgment.', placement: 'bottom' },
        { element: '.grid.grid-cols-1.gap-3.sm\\:grid-cols-2', title: 'Alert Summary', content: 'Shows total alerts raised and the number of unacknowledged alerts requiring action.', placement: 'bottom' },
        { element: '.divide-y.divide-gray-100', title: 'Alert List', content: 'Each alert shows the patient name, severity (color-coded), type, and time. Click an alert to view details and acknowledge it.', placement: 'top' },
      ]
    },

    /* ── Audit Trail ── */
    'accounts:audit_trail': {
      id: 'audit_trail',
      steps: [
        { element: 'h1', title: 'Audit Trail', content: 'Complete history of all changes made across the system. Every create, update, and delete operation is logged for compliance.', placement: 'bottom' },
        { element: '#audit-model-tabs', title: 'Model Tabs', content: 'Filter by data category — Patients, Admissions, Staff, Tasks, and more. Select a tab to see changes for that model.', placement: 'bottom' },
        { element: '#audit-stats', title: 'Stats Bar', content: 'Shows total changes, unique patients affected, and a color-coded legend: green for Created, amber for Modified, red for Deleted.', placement: 'bottom' },
        { element: '.space-y-2', title: 'Change Groups', content: 'Changes are grouped by entity (patient or record). Click a group header to expand and see individual changes. Each change shows who made it, what field changed, and the old/new values.', placement: 'top' },
      ]
    },

    /* ── Control Panel ── */
    'accounts:control_panel': {
      id: 'control_panel',
      steps: [
        { element: 'h1', title: 'Control Panel', content: 'Staff management console. View all registered users, their roles, and manage staff profiles.', placement: 'bottom' },
        { element: '#roleChart', title: 'Role Distribution', content: 'Pie chart showing staff distribution by role. Hover over segments for counts.', placement: 'top' },
        { element: '#staff-directory .flex.flex-wrap.gap-2', title: 'Filter Pills', content: 'Click a role pill to filter the staff directory by role. The chart segment also triggers this filter when clicked.', placement: 'bottom' },
        { element: '#staff-directory', title: 'Staff Directory', content: 'Search and browse all staff members. Click any row to view or edit the user\'s profile details.', placement: 'top' },
      ]
    },
  };

  var tour = tours[page];
  if (tour) {
    window.__pageTour = tour;
    window.SystemTour.autoStart(tour);
  }
})();
