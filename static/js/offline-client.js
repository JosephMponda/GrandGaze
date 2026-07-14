/* Local-first clinical workspace. It intentionally has no framework runtime:
 * all clinical state is stored in IndexedDB and the server is used only for
 * initial replication and later synchronization. */
(function () {
  const DB_NAME = 'must_emr_local';
  const DB_VERSION = 1;
  const STORES = ['meta', 'patients', 'encounters', 'vitals', 'outbox'];
  let database;
  let ownerId = localStorage.getItem('must_emr_offline_owner') || '';

  const uuid = () => crypto.randomUUID();

  function open() {
    if (database) return Promise.resolve(database);
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => { database = request.result; resolve(database); };
      request.onupgradeneeded = () => {
        const db = request.result;
        STORES.forEach((name) => {
          if (!db.objectStoreNames.contains(name)) db.createObjectStore(name, { keyPath: 'id' });
        });
      };
    });
  }

  async function store(name, mode, callback) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(name, mode);
      const request = callback(tx.objectStore(name));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
      tx.onabort = () => reject(tx.error);
    });
  }

  const put = (name, value) => store(name, 'readwrite', (s) => s.put(value));
  const get = (name, id) => store(name, 'readonly', (s) => s.get(id));
  const remove = (name, id) => store(name, 'readwrite', (s) => s.delete(id));
  const all = async (name) => (await store(name, 'readonly', (s) => s.getAll())).filter((row) => row.owner_id === ownerId);

  async function configure(owner) {
    if (!owner) return;
    if (ownerId && ownerId !== String(owner)) {
      // Never expose one staff member's local clinical data to another user.
      const db = await open();
      await Promise.all(STORES.filter((name) => name !== 'meta').map((name) => new Promise((resolve, reject) => {
        const tx = db.transaction(name, 'readwrite');
        tx.objectStore(name).clear();
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error);
      })));
    }
    ownerId = String(owner);
    localStorage.setItem('must_emr_offline_owner', ownerId);
    await put('meta', { id: 'session', owner_id: ownerId, updated_at: new Date().toISOString() });
  }

  async function bootstrap() {
    if (!ownerId || !navigator.onLine) return false;
    const response = await fetch('/api/offline/bootstrap/', { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) throw new Error('Could not download the offline patient directory.');
    const snapshot = await response.json();
    await Promise.all(snapshot.patients.map((patient) => put('patients', {
      ...patient,
      id: `server:${patient.server_id}`,
      owner_id: ownerId,
      sync_state: 'synced',
      updated_at: snapshot.generated_at,
    })));
    await put('meta', { id: 'snapshot', owner_id: ownerId, updated_at: snapshot.generated_at });
    return true;
  }

  async function queue(form_type, entity, local_id) {
    await put('outbox', {
      id: uuid(), owner_id: ownerId, form_type, entity, local_id,
      client_uuid: uuid(), created_at: new Date().toISOString(), state: 'pending', attempts: 0,
    });
  }

  async function createPatient(data) {
    const id = `local:${uuid()}`;
    const patient = { id, owner_id: ownerId, ...data, sync_state: 'pending', created_at: new Date().toISOString() };
    await put('patients', patient);
    await queue('patient_registration', 'patients', id);
    return patient;
  }

  async function createEncounter(patient, data) {
    const id = `local:${uuid()}`;
    await put('encounters', { id, owner_id: ownerId, patient_local_id: patient.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('encounter_note', 'encounters', id);
  }

  async function createVitals(patient, encounter, data) {
    const id = `local:${uuid()}`;
    await put('vitals', { id, owner_id: ownerId, patient_local_id: patient.id, encounter_local_id: encounter.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('vitals_entry', 'vitals', id);
  }

  async function payloadFor(item, record) {
    if (item.entity === 'patients') {
      const { id, owner_id, server_id, sync_state, created_at, updated_at, ...payload } = record;
      return payload;
    }
    if (item.entity === 'encounters') {
      const patient = await get('patients', record.patient_local_id);
      if (!patient?.server_id) return null;
      const { id, owner_id, patient_local_id, server_id, sync_state, created_at, ...payload } = record;
      return { ...payload, patient_id: patient.server_id };
    }
    const encounter = await get('encounters', record.encounter_local_id);
    if (!encounter?.server_id) return null;
    const { id, owner_id, patient_local_id, encounter_local_id, server_id, sync_state, created_at, ...payload } = record;
    return { ...payload, encounter_id: encounter.server_id };
  }

  async function sync() {
    if (!ownerId || !navigator.onLine) return { applied: 0, review: 0 };
    const outbox = (await all('outbox')).sort((a, b) => a.created_at.localeCompare(b.created_at));
    let applied = 0;
    let review = 0;
    for (const item of outbox) {
      if (item.state === 'needs_review') { review += 1; continue; }
      const record = await get(item.entity, item.local_id);
      const payload_json = record && await payloadFor(item, record);
      if (!payload_json) break; // Parent local record must synchronize first.
      try {
        const response = await fetch('/api/sync/submit/', {
          method: 'POST', credentials: 'same-origin', headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': localStorage.getItem('must_emr_offline_csrf') || '',
          },
          body: JSON.stringify({ client_uuid: item.client_uuid, form_type: item.form_type, payload_json }),
        });
        const result = await response.json().catch(() => ({}));
        if (response.ok && ['applied', 'already_applied'].includes(result.status)) {
          const server_id = result.result?.patient_id || result.result?.encounter_id || result.result?.vitals_id;
          await put(item.entity, { ...record, server_id, sync_state: 'synced', synced_at: new Date().toISOString() });
          await remove('outbox', item.id);
          applied += 1;
        } else if (response.status < 500) {
          await put('outbox', { ...item, state: 'needs_review', error: result.error || result.conflict_note || 'Validation failed.' });
          await put(item.entity, { ...record, sync_state: 'needs_review' });
          review += 1;
        } else break;
      } catch (_) { break; }
    }
    return { applied, review };
  }

  async function state() {
    return {
      patients: await all('patients'),
      encounters: await all('encounters'),
      vitals: await all('vitals'),
      outbox: await all('outbox'),
      snapshot: await get('meta', 'snapshot'),
    };
  }

  async function renderWorkspace(root) {
    const refresh = async () => {
      const data = await state();
      const selectedId = root.dataset.patientId;
      const selected = data.patients.find((patient) => patient.id === selectedId) || data.patients[0];
      root.dataset.patientId = selected?.id || '';
      const patientRows = data.patients.sort((a, b) => `${a.last_name}${a.first_name}`.localeCompare(`${b.last_name}${b.first_name}`))
        .map((p) => `<button class="offline-patient ${p.id === selected?.id ? 'selected' : ''}" data-patient-id="${p.id}"><strong>${escape(p.last_name)}, ${escape(p.first_name)}</strong><span>${escape(p.patient_number || 'Not yet assigned')} · ${p.sync_state}</span></button>`).join('');
      const patientEncounters = data.encounters.filter((e) => e.patient_local_id === selected?.id);
      const patientVitals = data.vitals.filter((v) => v.patient_local_id === selected?.id);
      const reviewItems = data.outbox.filter((item) => item.state === 'needs_review');
      const syncMessage = root.dataset.syncMessage || '';
      root.innerHTML = `<header class="offline-head"><div><p>Local-first clinical workspace</p><h1>MUST EMR Offline</h1></div><div><span class="offline-pill ${navigator.onLine ? 'online' : ''}">${navigator.onLine ? 'Connection available' : 'Working offline'}</span><a class="offline-return" href="/accounts/dashboard/">Return online</a><button data-action="sync">Sync now</button></div></header>
        <p class="offline-status">${data.outbox.length} change${data.outbox.length === 1 ? '' : 's'} waiting. Directory snapshot: ${data.snapshot?.updated_at ? new Date(data.snapshot.updated_at).toLocaleString() : 'not downloaded yet'}. ${escape(syncMessage)}</p>
        ${reviewItems.length ? `<section class="offline-review"><strong>${reviewItems.length} item${reviewItems.length === 1 ? '' : 's'} needs review</strong>${reviewItems.map((item) => `<p>${escape(item.form_type)}: ${escape(item.error || 'The server rejected this change. Create a corrected record before retrying.')}</p>`).join('')}</section>` : ''}
        <section class="offline-grid"><aside><div class="offline-actions"><button data-action="new-patient">Register patient</button><button data-action="refresh">Refresh directory</button></div><input id="offline-search" placeholder="Search local patients" autocomplete="off"><div id="offline-patients">${patientRows || '<p class="offline-empty">No local patients. Connect once and refresh the directory.</p>'}</div></aside>
        <main>${selected ? `<h2>${escape(selected.first_name)} ${escape(selected.other_names || '')} ${escape(selected.last_name)}</h2><p class="offline-muted">${escape(selected.patient_number || 'Local patient')} · ${escape(selected.sex || 'Unknown')} · ${escape(selected.phone_number || 'No phone')}</p><div class="offline-cards"><article><h3>Encounters</h3><p>${patientEncounters.length} local record(s)</p><button data-action="new-encounter">Add encounter</button></article><article><h3>Vitals</h3><p>${patientVitals.length} local record(s)</p><button data-action="new-vitals" ${patientEncounters.length ? '' : 'disabled'}>Record vitals</button></article></div><div class="offline-history">${patientEncounters.map((e) => `<p><strong>Encounter:</strong> ${escape(e.presenting_complaint)} <small>${e.sync_state}</small></p>`).join('')}${patientVitals.map((v) => `<p><strong>Vitals:</strong> pulse ${escape(v.pulse_rate || '-')} · BP ${escape(v.blood_pressure_systolic || '-')}/${escape(v.blood_pressure_diastolic || '-')} <small>${v.sync_state}</small></p>`).join('')}</div>` : '<h2>Select or register a patient</h2>'}</main></section>`;
      root.querySelectorAll('[data-patient-id]').forEach((button) => button.addEventListener('click', () => { root.dataset.patientId = button.dataset.patientId; refresh(); }));
      root.querySelector('[data-action="sync"]')?.addEventListener('click', async (event) => {
        event.currentTarget.disabled = true;
        event.currentTarget.textContent = 'Syncing...';
        const outcome = await sync();
        root.dataset.syncMessage = outcome.applied
          ? `${outcome.applied} change${outcome.applied === 1 ? '' : 's'} synced.`
          : outcome.review ? 'No changes synced. Review the item below.' : 'Nothing ready to sync.';
        await refresh();
      });
      root.querySelector('[data-action="refresh"]')?.addEventListener('click', async () => { try { await bootstrap(); } catch (error) { alert(error.message); } await refresh(); });
      root.querySelector('[data-action="new-patient"]')?.addEventListener('click', () => patientForm(root, refresh));
      root.querySelector('[data-action="new-encounter"]')?.addEventListener('click', () => encounterForm(root, selected, refresh));
      root.querySelector('[data-action="new-vitals"]')?.addEventListener('click', () => vitalsForm(root, selected, patientEncounters.at(-1), refresh));
      root.querySelector('#offline-search')?.addEventListener('input', (event) => {
        const term = event.target.value.toLowerCase();
        root.querySelectorAll('.offline-patient').forEach((row) => { row.hidden = !row.textContent.toLowerCase().includes(term); });
      });
    };
    refresh();
  }

  function form(root, title, fields, submit) {
    const control = ([name, label, type = 'text', required = false, options = []]) => type === 'select'
      ? `<label>${label}<select name="${name}" ${required ? 'required' : ''}>${options.map(([value, text]) => `<option value="${value}">${text}</option>`).join('')}</select></label>`
      : `<label>${label}<input name="${name}" type="${type}" ${required ? 'required' : ''}></label>`;
    root.innerHTML = `<section class="offline-form"><button data-back>Back</button><h2>${title}</h2><form>${fields.map(control).join('')}<button type="submit">Save on this device</button></form></section>`;
    root.querySelector('[data-back]').addEventListener('click', () => renderWorkspace(root));
    root.querySelector('form').addEventListener('submit', async (event) => { event.preventDefault(); await submit(Object.fromEntries(new FormData(event.target))); await renderWorkspace(root); });
  }
  const patientForm = (root, done) => form(root, 'Register patient', [['first_name', 'First name', 'text', true], ['last_name', 'Last name', 'text', true], ['sex', 'Sex', 'select', true, [['male', 'Male'], ['female', 'Female'], ['other', 'Other'], ['unknown', 'Unknown']]], ['date_of_birth', 'Date of birth', 'date'], ['phone_number', 'Phone number']], async (data) => { if (!data.date_of_birth) data.age_estimated = 'on'; await createPatient(data); await done(); });
  const encounterForm = (root, patient, done) => form(root, `Encounter for ${patient.first_name} ${patient.last_name}`, [['presenting_complaint', 'Presenting complaint', 'text', true], ['history_of_presenting_complaint', 'History'], ['diagnosis', 'Diagnosis'], ['clinical_plan', 'Clinical plan']], async (data) => { data.encounter_type = 'outpatient'; await createEncounter(patient, data); await done(); });
  const vitalsForm = (root, patient, encounter, done) => form(root, `Vitals for ${patient.first_name} ${patient.last_name}`, [['temperature_c', 'Temperature C', 'number'], ['pulse_rate', 'Pulse rate', 'number'], ['blood_pressure_systolic', 'Systolic BP', 'number'], ['blood_pressure_diastolic', 'Diastolic BP', 'number'], ['respiratory_rate', 'Respiratory rate', 'number'], ['oxygen_saturation', 'Oxygen saturation', 'number']], async (data) => { await createVitals(patient, encounter, data); await done(); });
  const escape = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);

  window.MUSTOffline = { configure, bootstrap, sync, state, renderWorkspace };
  function mountWorkspace() {
    const root = document.getElementById('offline-workspace');
    if (!root) return;
    renderWorkspace(root).catch((error) => {
      console.error('Offline workspace failed to start:', error);
      root.innerHTML = `<section class="offline-form"><h1>Offline workspace could not start</h1><p>${escape(error.message || 'Local storage is unavailable in this browser.')}</p><p>Return to the main application while connected, then open this workspace again.</p></section>`;
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountWorkspace, { once: true });
  else mountWorkspace();
})();
