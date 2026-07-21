/* Local-first clinical workspace. It intentionally has no framework runtime:
 * all clinical state is stored in IndexedDB and the server is used only for
 * initial replication and later synchronization. */
(function () {
  const DB_NAME = 'must_emr_local';
  const DB_VERSION = 8;
  const STORES = ['meta', 'patients', 'encounters', 'vitals', 'outbox', 'admissions', 'wards', 'prescriptions', 'ward_rounds', 'mar_entries', 'care_plans', 'fluid_entries', 'procedure_notes', 'nursing_assessments', 'referrals', 'drugs', 'lab_orders', 'lab_results', 'lab_tests', 'imaging_requests', 'imaging_results', 'imaging_modalities', 'triage_encounters', 'dialysis_prescriptions', 'dialysis_sessions', 'invoices', 'payments', 'service_catalog'];
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
    if (snapshot.wards) {
      await Promise.all(snapshot.wards.map((ward) => put('wards', {
        ...ward, id: `server:${ward.server_id}`, owner_id: ownerId, sync_state: 'synced',
      })));
    }
    if (snapshot.beds) {
      await Promise.all(snapshot.beds.map((bed) => put('wards', {
        ...bed, id: `server:${bed.server_id}`, owner_id: ownerId, sync_state: 'synced', _type: 'bed',
      })));
    }
    if (snapshot.admissions) {
      await Promise.all(snapshot.admissions.map((admission) => put('admissions', {
        ...admission, id: `server:${admission.server_id}`, owner_id: ownerId, sync_state: 'synced',
      })));
    }
    if (snapshot.prescriptions) {
      await Promise.all(snapshot.prescriptions.map((rx) => put('prescriptions', {
        ...rx, id: `server:${rx.server_id}`, owner_id: ownerId, sync_state: 'synced',
      })));
    }
    if (snapshot.drugs) {
      await Promise.all(snapshot.drugs.map((drug) => put('drugs', {
        ...drug, id: `server:${drug.server_id}`, owner_id: ownerId, sync_state: 'synced',
      })));
    }
    if (snapshot.lab_tests) {
      await Promise.all(snapshot.lab_tests.map((test) => put('lab_tests', {
        ...test, id: `server:${test.server_id}`, owner_id: ownerId, sync_state: 'synced',
      })));
    }
    if (snapshot.imaging_modalities) {
      await Promise.all(snapshot.imaging_modalities.map((mod) => put('imaging_modalities', {
        ...mod, id: `server:${mod.server_id}`, owner_id: ownerId, sync_state: 'synced',
      })));
    }
    if (snapshot.service_catalog) {
      await Promise.all(snapshot.service_catalog.map((svc) => put('service_catalog', {
        ...svc, id: `server:${svc.server_id}`, owner_id: ownerId, sync_state: 'synced',
      })));
    }
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

  async function createWardRoundNote(admission, data) {
    const id = `local:${uuid()}`;
    await put('ward_rounds', { id, owner_id: ownerId, admission_local_id: admission.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('ward_round_note', 'ward_rounds', id);
  }

  async function createMAREntry(admission, prescription, data) {
    const id = `local:${uuid()}`;
    await put('mar_entries', { id, owner_id: ownerId, admission_local_id: admission.id, prescription_local_id: prescription.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('mar_entry', 'mar_entries', id);
  }

  async function createCarePlan(admission, data) {
    const id = `local:${uuid()}`;
    await put('care_plans', { id, owner_id: ownerId, admission_local_id: admission.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('care_plan_create', 'care_plans', id);
  }

  async function evaluateCarePlan(plan, data) {
    const id = `local:${uuid()}`;
    await put('care_plans', { ...plan, evaluation: data.evaluation, goal_status: data.goal_status, sync_state: 'pending', evaluated_at: new Date().toISOString() });
    await queue('care_plan_evaluate', 'care_plans', plan.id);
  }

  async function createFluidEntry(admission, data) {
    const id = `local:${uuid()}`;
    await put('fluid_entries', { id, owner_id: ownerId, admission_local_id: admission.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('fluid_balance_entry', 'fluid_entries', id);
  }

  async function createProcedureNote(admission, data) {
    const id = `local:${uuid()}`;
    await put('procedure_notes', { id, owner_id: ownerId, admission_local_id: admission.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('procedure_note', 'procedure_notes', id);
  }

  async function createNursingAssessment(admission, data) {
    const id = `local:${uuid()}`;
    await put('nursing_assessments', { id, owner_id: ownerId, admission_local_id: admission.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('nursing_assessment', 'nursing_assessments', id);
  }

  async function createReferral(patient, data) {
    const id = `local:${uuid()}`;
    await put('referrals', { id, owner_id: ownerId, patient_local_id: patient.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() });
    await queue('referral', 'referrals', id);
  }

  async function prescribeDrug(patient, drug, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, patient_local_id: patient.id, drug_local_id: drug.id, drug_name: drug.name, sync_state: 'pending', ...data, created_at: new Date().toISOString() };
    await put('prescriptions', record);
    await queue('pharmacy_prescribe', 'prescriptions', id);
  }

  async function approvePrescription(rx, data) {
    const id = `local:${uuid()}`;
    await put('prescriptions', { ...rx, status: 'approved', sync_state: 'pending' });
    await queue('pharmacy_approve', 'prescriptions', rx.id);
  }

  async function dispensePrescription(rx, data) {
    const id = `local:${uuid()}`;
    await put('prescriptions', { ...rx, status: 'dispensed', sync_state: 'pending' });
    await queue('pharmacy_dispense', 'prescriptions', rx.id);
  }

  async function createLabOrder(patient, labTest, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, patient_local_id: patient.id, test_local_id: labTest.id, test_name: labTest.name, sync_state: 'pending', ...data, created_at: new Date().toISOString() };
    await put('lab_orders', record);
    await queue('lab_order', 'lab_orders', id);
  }

  async function collectLabSpecimen(order, data) {
    await put('lab_orders', { ...order, status: 'specimen_collected', sync_state: 'pending' });
    await queue('lab_collect', 'lab_orders', order.id);
  }

  async function enterLabResult(order, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, order_local_id: order.id, test_name: order.test_name, sync_state: 'pending', ...data, entered_at: new Date().toISOString() };
    await put('lab_results', record);
    await queue('lab_result', 'lab_results', id);
  }

  async function verifyLabResult(result, data) {
    await put('lab_results', { ...result, verified: true, sync_state: 'pending' });
    await queue('lab_verify', 'lab_results', result.id);
  }

  async function createImagingRequest(patient, modality, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, patient_local_id: patient.id, modality_local_id: modality.id, modality_name: modality.name, sync_state: 'pending', ...data, created_at: new Date().toISOString() };
    await put('imaging_requests', record);
    await queue('imaging_request', 'imaging_requests', id);
  }

  async function enterImagingReport(imagingRequest, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, request_local_id: imagingRequest.id, modality_name: imagingRequest.modality_name, sync_state: 'pending', ...data, reported_at: new Date().toISOString() };
    await put('imaging_results', record);
    await queue('imaging_report', 'imaging_results', id);
  }

  async function createTriage(patient, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, patient_local_id: patient.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() };
    await put('triage_encounters', record);
    await queue('triage', 'triage_encounters', id);
  }

  async function resolveTriage(triage, data) {
    await put('triage_encounters', { ...triage, outcome: data.outcome, disposition_note: data.disposition_note, resolved_at: new Date().toISOString(), sync_state: 'pending' });
    await queue('resolve_triage', 'triage_encounters', triage.id);
  }

  async function createDialysisPrescription(patient, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, patient_local_id: patient.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() };
    await put('dialysis_prescriptions', record);
    await queue('dialysis_prescription', 'dialysis_prescriptions', id);
  }

  async function recordDialysisSession(prescription, data) {
    const id = `local:${uuid()}`;
    const record = { id, owner_id: ownerId, prescription_local_id: prescription.id, sync_state: 'pending', ...data, created_at: new Date().toISOString() };
    await put('dialysis_sessions', record);
    await queue('dialysis_session', 'dialysis_sessions', id);
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
    if (item.entity === 'vitals') {
      const encounter = await get('encounters', record.encounter_local_id);
      if (!encounter?.server_id) return null;
      const { id, owner_id, patient_local_id, encounter_local_id, server_id, sync_state, created_at, ...payload } = record;
      return { ...payload, encounter_id: encounter.server_id };
    }
    // Inpatient entities: resolve admission_id from local store
    const inpatientEntities = ['ward_rounds', 'mar_entries', 'care_plans', 'fluid_entries', 'procedure_notes', 'nursing_assessments'];
    if (inpatientEntities.includes(item.entity)) {
      const admission = await get('admissions', record.admission_local_id);
      if (!admission?.server_id) return null;
      const { id, owner_id, admission_local_id, prescription_local_id, server_id, sync_state, created_at, ...payload } = record;
      payload.admission_id = admission.server_id;
      // MAR entries also need prescription_id
      if (item.entity === 'mar_entries' && prescription_local_id) {
        const rx = await get('prescriptions', prescription_local_id);
        if (!rx?.server_id) return null;
        payload.prescription_id = rx.server_id;
      }
      return payload;
    }
    if (item.entity === 'referrals') {
      const patient = await get('patients', record.patient_local_id);
      if (!patient?.server_id) return null;
      const { id, owner_id, patient_local_id, server_id, sync_state, created_at, ...payload } = record;
      return { ...payload, patient_id: patient.server_id };
    }
    if (item.entity === 'prescriptions') {
      const patient = await get('patients', record.patient_local_id);
      if (!patient?.server_id) return null;
      const drug = record.drug_local_id ? await get('prescriptions', record.drug_local_id) : null;
      const { id, owner_id, patient_local_id, drug_local_id, drug_name, server_id, sync_state, created_at, ...payload } = record;
      payload.patient_id = patient.server_id;
      if (drug?.server_id) payload.drug_id = drug.server_id;
      else if (record.drug_id) payload.drug_id = record.drug_id;
      return payload;
    }
    if (item.entity === 'lab_orders') {
      const patient = await get('patients', record.patient_local_id);
      if (!patient?.server_id) return null;
      const labTest = await get('lab_tests', record.test_local_id);
      const { id, owner_id, patient_local_id, test_local_id, test_name, server_id, sync_state, created_at, ...payload } = record;
      payload.patient_id = patient.server_id;
      if (labTest?.server_id) payload.test_id = labTest.server_id;
      else if (record.test_id) payload.test_id = record.test_id;
      return payload;
    }
    if (item.entity === 'lab_results') {
      const order = await get('lab_orders', record.order_local_id);
      if (!order?.server_id) return null;
      const { id, owner_id, order_local_id, test_name, server_id, sync_state, created_at, entered_at, verified, ...payload } = record;
      payload.order_id = order.server_id;
      return payload;
    }
    if (item.entity === 'imaging_requests') {
      const patient = await get('patients', record.patient_local_id);
      if (!patient?.server_id) return null;
      const modality = await get('imaging_modalities', record.modality_local_id);
      const { id, owner_id, patient_local_id, modality_local_id, modality_name, server_id, sync_state, created_at, ...payload } = record;
      payload.patient_id = patient.server_id;
      if (modality?.server_id) payload.modality_id = modality.server_id;
      else if (record.modality_id) payload.modality_id = record.modality_id;
      return payload;
    }
    if (item.entity === 'imaging_results') {
      const imagingReq = await get('imaging_requests', record.request_local_id);
      if (!imagingReq?.server_id) return null;
      const { id, owner_id, request_local_id, modality_name, server_id, sync_state, created_at, reported_at, ...payload } = record;
      payload.request_id = imagingReq.server_id;
      return payload;
    }
    if (item.entity === 'triage_encounters') {
      const patient = await get('patients', record.patient_local_id);
      if (!patient?.server_id) return null;
      const { id, owner_id, patient_local_id, server_id, sync_state, created_at, resolved_at, ...payload } = record;
      payload.patient_id = patient.server_id;
      return payload;
    }
    if (item.entity === 'dialysis_prescriptions') {
      const patient = await get('patients', record.patient_local_id);
      if (!patient?.server_id) return null;
      const { id, owner_id, patient_local_id, server_id, sync_state, created_at, ...payload } = record;
      payload.patient_id = patient.server_id;
      return payload;
    }
    if (item.entity === 'dialysis_sessions') {
      const prescription = await get('dialysis_prescriptions', record.prescription_local_id);
      if (!prescription?.server_id) return null;
      const { id, owner_id, prescription_local_id, server_id, sync_state, created_at, ...payload } = record;
      payload.prescription_id = prescription.server_id;
      return payload;
    }
    return null;
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
          const server_id = result.result?.patient_id || result.result?.encounter_id || result.result?.vitals_id || result.result?.record_id;
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

  const TIP_STORAGE_KEY = 'must_emr_offline_tips_dismissed';

  function tipsDismissed() {
    return localStorage.getItem(TIP_STORAGE_KEY) === 'true';
  }

  function dismissTips(root) {
    localStorage.setItem(TIP_STORAGE_KEY, 'true');
    root.querySelector('.offline-tip')?.remove();
  }

  async function state() {
    return {
      patients: await all('patients'),
      encounters: await all('encounters'),
      vitals: await all('vitals'),
      outbox: await all('outbox'),
      snapshot: await get('meta', 'snapshot'),
      admissions: await all('admissions'),
      wards: (await all('wards')).filter((w) => !w._type),
      beds: (await all('wards')).filter((w) => w._type === 'bed'),
      prescriptions: await all('prescriptions'),
      ward_rounds: await all('ward_rounds'),
      mar_entries: await all('mar_entries'),
      care_plans: await all('care_plans'),
      fluid_entries: await all('fluid_entries'),
      procedure_notes: await all('procedure_notes'),
      nursing_assessments: await all('nursing_assessments'),
      referrals: await all('referrals'),
      drugs: await all('drugs'),
      lab_orders: await all('lab_orders'),
      lab_results: await all('lab_results'),
      lab_tests: await all('lab_tests'),
      imaging_requests: await all('imaging_requests'),
      imaging_results: await all('imaging_results'),
      imaging_modalities: await all('imaging_modalities'),
      triage_encounters: await all('triage_encounters'),
      dialysis_prescriptions: await all('dialysis_prescriptions'),
      dialysis_sessions: await all('dialysis_sessions'),
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
      // Find active admission for selected patient
      const patientAdmission = selected ? data.admissions.find((a) => a.patient_id === (selected.server_id || parseInt(selected.id?.replace('server:', '')))) : null;
      const admissionWardRounds = patientAdmission ? data.ward_rounds.filter((r) => r.admission_local_id === patientAdmission.id) : [];
      const admissionMAR = patientAdmission ? data.mar_entries.filter((m) => m.admission_local_id === patientAdmission.id) : [];
      const admissionCarePlans = patientAdmission ? data.care_plans.filter((c) => c.admission_local_id === patientAdmission.id) : [];
      const admissionFluid = patientAdmission ? data.fluid_entries.filter((f) => f.admission_local_id === patientAdmission.id) : [];
      const admissionProcedures = patientAdmission ? data.procedure_notes.filter((p) => p.admission_local_id === patientAdmission.id) : [];
      const admissionAssessments = patientAdmission ? data.nursing_assessments.filter((a) => a.admission_local_id === patientAdmission.id) : [];
      const patientReferrals = selected ? data.referrals.filter((r) => r.patient_local_id === selected.id) : [];
      const patientPrescriptions = selected ? data.prescriptions.filter((p) => p.patient_id === (selected.server_id || parseInt(selected.id?.replace('server:', '')))) : [];
      const inpatientSection = patientAdmission ? `<section class="offline-inpatient"><h3>Inpatient — ${escape(patientAdmission.admission_diagnosis)}</h3><p class="offline-muted">${escape(patientAdmission.ward_name || 'Unknown ward')} · ${escape(patientAdmission.bed_label || 'No bed')}</p><div class="offline-cards">
        <article><h3>Ward Round</h3><p>${admissionWardRounds.length} note(s)</p><button data-action="new-ward-round">Add note</button></article>
        <article><h3>Care Plans</h3><p>${admissionCarePlans.length} plan(s)</p><button data-action="new-care-plan">Add plan</button></article>
        <article><h3>Fluid Balance</h3><p>${admissionFluid.length} entry(ies)</p><button data-action="new-fluid-entry">Record fluid</button></article>
        <article><h3>Procedure Note</h3><p>${admissionProcedures.length} note(s)</p><button data-action="new-procedure-note">Add note</button></article>
        <article><h3>Nursing Assessment</h3><p>${admissionAssessments.length} assessment(s)</p><button data-action="new-nursing-assessment">Add assessment</button></article>
        ${patientPrescriptions.length ? `<article><h3>MAR</h3><p>${admissionMAR.length} administration(s)</p><button data-action="new-mar">Record administration</button></article>` : ''}
        <article><h3>Referral</h3><p>${patientReferrals.length} referral(s)</p><button data-action="new-referral">Create referral</button></article>
      </div></section>` : '';
      const activeRx = data.prescriptions.filter((p) => p.patient_id === (selected?.server_id || parseInt(selected?.id?.replace('server:', ''))) && ['prescribed', 'approved'].includes(p.status));
      const pharmacySection = `<section class="offline-inpatient"><h3>Pharmacy</h3><div class="offline-cards">
        <article><h3>Prescribe</h3><p>${data.drugs.length} drugs in catalog</p><button data-action="new-prescription">New prescription</button></article>
        ${activeRx.length ? `<article><h3>Pending Rx</h3><p>${activeRx.length} waiting</p>${activeRx.slice(0, 5).map((rx) => `<p class="offline-rx">${escape(rx.drug_name)} ${escape(rx.dose)} <small>${rx.status}</small></p><div class="offline-rx-actions">${rx.status === 'prescribed' ? `<button data-action="approve-rx" data-rx-id="${rx.id}">Approve</button>` : ''}${rx.status === 'approved' ? `<button data-action="dispense-rx" data-rx-id="${rx.id}">Dispense</button>` : ''}</div>`).join('')}</article>` : ''}
      </div></section>`;
      // Laboratory
      const patientLabOrders = selected ? data.lab_orders.filter((o) => o.patient_local_id === selected.id) : [];
      const pendingOrders = patientLabOrders.filter((o) => ['ordered', 'specimen_collected'].includes(o.status));
      const pendingResults = data.lab_results.filter((r) => patientLabOrders.some((o) => o.id === r.order_local_id) && !r.verified);
      const labSection = `<section class="offline-inpatient"><h3>Laboratory</h3><div class="offline-cards">
        <article><h3>Order Test</h3><p>${data.lab_tests.length} tests in catalog</p><button data-action="new-lab-order">Order test</button></article>
        ${pendingOrders.length ? `<article><h3>Pending Orders</h3><p>${pendingOrders.length} waiting</p>${pendingOrders.slice(0, 5).map((o) => `<p class="offline-rx">${escape(o.test_name)} <small>${o.status}</small></p><div class="offline-rx-actions">${o.status === 'ordered' ? `<button data-action="collect-specimen" data-order-id="${o.id}">Collect</button>` : `<button data-action="enter-result" data-order-id="${o.id}">Enter result</button>`}</div>`).join('')}</article>` : ''}
        ${pendingResults.length ? `<article><h3>Pending Verification</h3><p>${pendingResults.length} result(s)</p>${pendingResults.slice(0, 5).map((r) => `<p class="offline-rx">${escape(r.test_name)}: ${escape(r.value_text || r.value_numeric || '-')} <small>${r.verified ? 'verified' : 'pending'}</small></p>${!r.verified ? `<div class="offline-rx-actions"><button data-action="verify-result" data-result-id="${r.id}">Verify</button></div>` : ''}`).join('')}</article>` : ''}
      </div></section>`;
      // Imaging
      const patientImagingRequests = selected ? data.imaging_requests.filter((r) => r.patient_local_id === selected.id) : [];
      const pendingImaging = patientImagingRequests.filter((r) => r.status !== 'reported');
      const imagingResults = data.imaging_results.filter((r) => patientImagingRequests.some((req) => req.id === r.request_local_id));
      const imagingSection = `<section class="offline-inpatient"><h3>Imaging</h3><div class="offline-cards">
        <article><h3>Request Imaging</h3><p>${data.imaging_modalities.length} modalities</p><button data-action="new-imaging-request">New request</button></article>
        ${pendingImaging.length ? `<article><h3>Pending</h3><p>${pendingImaging.length} request(s)</p>${pendingImaging.slice(0, 5).map((r) => `<p class="offline-rx">${escape(r.modality_name)} — ${escape(r.clinical_indication?.substring(0, 40))} <small>${r.status}</small></p>${r.status !== 'reported' ? `<div class="offline-rx-actions"><button data-action="enter-imaging-report" data-request-id="${r.id}">Enter report</button></div>` : ''}`).join('')}</article>` : ''}
        ${imagingResults.length ? `<article><h3>Reports</h3><p>${imagingResults.length} report(s)</p>${imagingResults.slice(0, 5).map((r) => `<p class="offline-rx">${escape(r.modality_name)}: ${escape(r.impression?.substring(0, 40))} ${r.is_critical_finding ? '<strong>CRITICAL</strong>' : ''} <small>${r.sync_state}</small></p>`).join('')}</article>` : ''}
      </div></section>`;
      // Emergency
      const activeTriage = data.triage_encounters.filter((t) => !t.outcome);
      const emergencySection = `<section class="offline-inpatient"><h3>Emergency</h3><div class="offline-cards">
        <article><h3>Triage</h3><p>${activeTriage.length} active</p><button data-action="new-triage">Triage patient</button></article>
        ${activeTriage.length ? `<article><h3>Waiting</h3><p>${activeTriage.length} patient(s)</p>${activeTriage.slice(0, 5).map((t) => `<p class="offline-rx">${escape(t.triage_category)} — ${escape(t.presenting_condition?.substring(0, 40))} <small>${t.sync_state}</small></p><div class="offline-rx-actions"><button data-action="resolve-triage" data-triage-id="${t.id}">Resolve</button></div>`).join('')}</article>` : ''}
      </div></section>`;
      // Dialysis
      const patientDialysisPrescriptions = selected ? data.dialysis_prescriptions.filter((p) => p.patient_local_id === selected.id) : [];
      const activeDialysis = patientDialysisPrescriptions.filter((p) => p.is_active !== false);
      const patientDialysisSessions = selected ? data.dialysis_sessions.filter((s) => patientDialysisPrescriptions.some((p) => p.id === s.prescription_local_id)) : [];
      const dialysisSection = `<section class="offline-inpatient"><h3>Dialysis</h3><div class="offline-cards">
        <article><h3>Prescribe</h3><p>${activeDialysis.length} active prescription(s)</p><button data-action="new-dialysis-prescription">New prescription</button></article>
        ${activeDialysis.length ? `<article><h3>Record Session</h3><p>${patientDialysisSessions.length} session(s) recorded</p><button data-action="new-dialysis-session">Record session</button></article>` : ''}
      </div></section>`;
      root.innerHTML = `<header class="offline-head"><div><p>Local-first clinical workspace</p><p class="offline-reload-warning"><strong>PLEASE RELOAD THE PAGE IF THE TEXT IS NOT DISPLAYING CORRECTLY</strong></p><h1>MUST EMR Offline</h1></div><div><span class="offline-pill ${navigator.onLine ? 'online' : ''}">${navigator.onLine ? 'Connection available' : 'Working offline'}</span><a class="offline-return" href="/accounts/dashboard/">Return online</a><button data-action="sync">Sync now</button></div></header>
        ${!tipsDismissed() ? `<section class="offline-tip"><div><strong>Offline workspace quick start</strong><button data-action="dismiss-tips" aria-label="Dismiss tips">×</button></div><ol><li>Open this page while online, then click <strong>Refresh directory</strong> to download the patient snapshot.</li><li>Create or select a patient, add an encounter, then record vitals.</li><li>When you next go online, click <strong>Sync now</strong> to send local changes to the server.</li></ol><p>If the workspace appears empty on first load, reload the page once and then refresh the directory again.</p></section>` : ''}
        <p class="offline-status">${data.outbox.length} change${data.outbox.length === 1 ? '' : 's'} waiting. Directory snapshot: ${data.snapshot?.updated_at ? new Date(data.snapshot.updated_at).toLocaleString() : 'not downloaded yet'}. ${escape(syncMessage)}</p>
        ${reviewItems.length ? `<section class="offline-review"><strong>${reviewItems.length} item${reviewItems.length === 1 ? '' : 's'} needs review</strong>${reviewItems.map((item) => `<p>${escape(item.form_type)}: ${escape(item.error || 'The server rejected this change. Create a corrected record before retrying.')}</p>`).join('')}</section>` : ''}
        <section class="offline-grid"><aside><div class="offline-actions"><button data-action="new-patient">Register patient</button><button data-action="refresh" title="Refresh the local patient directory">Refresh directory</button></div><div class="offline-button-guidance"><span><strong>Refresh</strong> downloads the most recent local patient snapshot.</span><span><strong>Sync</strong> sends your offline edits when you reconnect.</span></div><input id="offline-search" placeholder="Search local patients" autocomplete="off"><div id="offline-patients">${patientRows || '<p class="offline-empty">No local patients. Connect once and refresh the directory.</p>'}</div></aside>
        <main>${selected ? `<h2>${escape(selected.first_name)} ${escape(selected.other_names || '')} ${escape(selected.last_name)}</h2><p class="offline-muted">${escape(selected.patient_number || 'Local patient')} · ${escape(selected.sex || 'Unknown')} · ${escape(selected.phone_number || 'No phone')}</p><div class="offline-cards"><article><h3>Encounters</h3><p>${patientEncounters.length} local record(s)</p><button data-action="new-encounter">Add encounter</button></article><article><h3>Vitals</h3><p>${patientVitals.length} local record(s)</p><button data-action="new-vitals" ${patientEncounters.length ? '' : 'disabled'}>Record vitals</button></article></div>${inpatientSection}${pharmacySection}${labSection}${imagingSection}${emergencySection}${dialysisSection}<div class="offline-history">${patientEncounters.map((e) => `<p><strong>Encounter:</strong> ${escape(e.presenting_complaint)} <small>${e.sync_state}</small></p>`).join('')}${patientVitals.map((v) => `<p><strong>Vitals:</strong> pulse ${escape(v.pulse_rate || '-')} · BP ${escape(v.blood_pressure_systolic || '-')}/${escape(v.blood_pressure_diastolic || '-')} <small>${v.sync_state}</small></p>`).join('')}${admissionWardRounds.map((r) => `<p><strong>Ward Round:</strong> ${escape(r.note)} <small>${r.sync_state}</small></p>`).join('')}${admissionCarePlans.map((c) => `<p><strong>Care Plan:</strong> ${escape(c.problem)} — ${escape(c.goal_status || 'ongoing')} <small>${c.sync_state}</small></p>`).join('')}${admissionFluid.map((f) => `<p><strong>Fluid:</strong> ${escape(f.fluid_type)} ${escape(f.volume_ml)}ml <small>${f.sync_state}</small></p>`).join('')}${admissionProcedures.map((p) => `<p><strong>Procedure:</strong> ${escape(p.procedure_name)} <small>${p.sync_state}</small></p>`).join('')}${admissionAssessments.map((a) => `<p><strong>Assessment:</strong> ${escape(a.assessment_note?.substring(0, 80))} <small>${a.sync_state}</small></p>`).join('')}${admissionMAR.map((m) => `<p><strong>MAR:</strong> Rx#${escape(m.prescription_local_id)} ${escape(m.dose_given)} <small>${m.sync_state}</small></p>`).join('')}${patientReferrals.map((r) => `<p><strong>Referral:</strong> ${escape(r.destination)} <small>${r.sync_state}</small></p>`).join('')}</div>` : '<h2>Select or register a patient</h2>'}</main></section>`;
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
      root.querySelector('[data-action="dismiss-tips"]')?.addEventListener('click', () => dismissTips(root));
      root.querySelector('[data-action="refresh"]')?.addEventListener('click', async () => { try { await bootstrap(); } catch (error) { alert(error.message); } await refresh(); });
      root.querySelector('[data-action="new-patient"]')?.addEventListener('click', () => patientForm(root, refresh));
      root.querySelector('[data-action="new-encounter"]')?.addEventListener('click', () => encounterForm(root, selected, refresh));
      root.querySelector('[data-action="new-vitals"]')?.addEventListener('click', () => vitalsForm(root, selected, patientEncounters.at(-1), refresh));
      root.querySelector('[data-action="new-ward-round"]')?.addEventListener('click', () => wardRoundForm(root, patientAdmission, refresh));
      root.querySelector('[data-action="new-care-plan"]')?.addEventListener('click', () => carePlanForm(root, patientAdmission, refresh));
      root.querySelector('[data-action="new-fluid-entry"]')?.addEventListener('click', () => fluidBalanceForm(root, patientAdmission, refresh));
      root.querySelector('[data-action="new-procedure-note"]')?.addEventListener('click', () => procedureNoteForm(root, patientAdmission, refresh));
      root.querySelector('[data-action="new-nursing-assessment"]')?.addEventListener('click', () => nursingAssessmentForm(root, patientAdmission, refresh));
      root.querySelector('[data-action="new-mar"]')?.addEventListener('click', () => marForm(root, patientAdmission, patientPrescriptions, refresh));
      root.querySelector('[data-action="new-referral"]')?.addEventListener('click', () => referralForm(root, selected, refresh));
      root.querySelector('[data-action="new-prescription"]')?.addEventListener('click', () => prescribeForm(root, selected, data.drugs, refresh));
      root.querySelector('[data-action="approve-rx"]')?.addEventListener('click', (event) => { const rxId = event.currentTarget.dataset.rxId; const rx = data.prescriptions.find((p) => p.id === rxId); if (rx) approveForm(root, rx, refresh); });
      root.querySelector('[data-action="dispense-rx"]')?.addEventListener('click', (event) => { const rxId = event.currentTarget.dataset.rxId; const rx = data.prescriptions.find((p) => p.id === rxId); if (rx) dispenseForm(root, rx, refresh); });
      root.querySelector('[data-action="new-lab-order"]')?.addEventListener('click', () => labOrderForm(root, selected, data.lab_tests, refresh));
      root.querySelector('[data-action="collect-specimen"]')?.addEventListener('click', (event) => { const orderId = event.currentTarget.dataset.orderId; const order = data.lab_orders.find((o) => o.id === orderId); if (order) collectSpecimenForm(root, order, refresh); });
      root.querySelector('[data-action="enter-result"]')?.addEventListener('click', (event) => { const orderId = event.currentTarget.dataset.orderId; const order = data.lab_orders.find((o) => o.id === orderId); if (order) labResultForm(root, order, refresh); });
      root.querySelector('[data-action="verify-result"]')?.addEventListener('click', (event) => { const resultId = event.currentTarget.dataset.resultId; const result = data.lab_results.find((r) => r.id === resultId); if (result) verifyResultForm(root, result, refresh); });
      root.querySelector('[data-action="new-imaging-request"]')?.addEventListener('click', () => imagingRequestForm(root, selected, data.imaging_modalities, refresh));
      root.querySelector('[data-action="enter-imaging-report"]')?.addEventListener('click', (event) => { const requestId = event.currentTarget.dataset.requestId; const imagingReq = data.imaging_requests.find((r) => r.id === requestId); if (imagingReq) imagingReportForm(root, imagingReq, refresh); });
      root.querySelector('[data-action="new-triage"]')?.addEventListener('click', () => triageForm(root, selected, refresh));
      root.querySelector('[data-action="resolve-triage"]')?.addEventListener('click', (event) => { const triageId = event.currentTarget.dataset.triageId; const triage = data.triage_encounters.find((t) => t.id === triageId); if (triage) resolveTriageForm(root, triage, refresh); });
      root.querySelector('[data-action="new-dialysis-prescription"]')?.addEventListener('click', () => dialysisPrescriptionForm(root, selected, refresh));
      root.querySelector('[data-action="new-dialysis-session"]')?.addEventListener('click', () => dialysisSessionForm(root, activeDialysis, refresh));
      root.querySelector('#offline-search')?.addEventListener('input', (event) => {
        const term = event.target.value.toLowerCase();
        root.querySelectorAll('.offline-patient').forEach((row) => { row.hidden = !row.textContent.toLowerCase().includes(term); });
      });
    };
    refresh();
  }

  function form(root, title, fields, submit) {
    const control = ([name, label, type = 'text', required = false, options = [], defaultValue = '']) => {
      if (type === 'select') return `<label>${label}<select name="${name}" ${required ? 'required' : ''}>${options.map(([value, text]) => `<option value="${value}"${value === defaultValue ? ' selected' : ''}>${text}</option>`).join('')}</select></label>`;
      if (type === 'textarea') return `<label>${label}<textarea name="${name}" rows="3" ${required ? 'required' : ''}>${defaultValue}</textarea></label>`;
      return `<label>${label}<input name="${name}" type="${type}" ${required ? 'required' : ''} value="${defaultValue}"></label>`;
    };
    root.innerHTML = `<section class="offline-form"><button data-back>Back</button><h2>${title}</h2><form>${fields.map(control).join('')}<button type="submit">Save on this device</button></form></section>`;
    root.querySelector('[data-back]').addEventListener('click', () => renderWorkspace(root));
    root.querySelector('form').addEventListener('submit', async (event) => { event.preventDefault(); await submit(Object.fromEntries(new FormData(event.target))); await renderWorkspace(root); });
  }
  const patientForm = (root, done) => form(root, 'Register patient', [['first_name', 'First name', 'text', true], ['last_name', 'Last name', 'text', true], ['sex', 'Sex', 'select', true, [['male', 'Male'], ['female', 'Female'], ['other', 'Other'], ['unknown', 'Unknown']]], ['date_of_birth', 'Date of birth', 'date'], ['phone_number', 'Phone number']], async (data) => { if (!data.date_of_birth) data.age_estimated = 'on'; await createPatient(data); await done(); });
  const encounterForm = (root, patient, done) => form(root, `Encounter for ${patient.first_name} ${patient.last_name}`, [['presenting_complaint', 'Presenting complaint', 'text', true], ['history_of_presenting_complaint', 'History'], ['diagnosis', 'Diagnosis'], ['clinical_plan', 'Clinical plan']], async (data) => { data.encounter_type = 'outpatient'; await createEncounter(patient, data); await done(); });
  const vitalsForm = (root, patient, encounter, done) => form(root, `Vitals for ${patient.first_name} ${patient.last_name}`, [['temperature_c', 'Temperature C', 'number'], ['pulse_rate', 'Pulse rate', 'number'], ['blood_pressure_systolic', 'Systolic BP', 'number'], ['blood_pressure_diastolic', 'Diastolic BP', 'number'], ['respiratory_rate', 'Respiratory rate', 'number'], ['oxygen_saturation', 'Oxygen saturation', 'number']], async (data) => { await createVitals(patient, encounter, data); await done(); });
  const wardRoundForm = (root, admission, done) => form(root, 'Ward Round Note', [['note', 'Clinical note', 'textarea', true], ['diagnosis_update', 'Diagnosis update'], ['plan_update', 'Plan update']], async (data) => { await createWardRoundNote(admission, data); await done(); });
  const carePlanForm = (root, admission, done) => form(root, 'Care Plan', [['problem', 'Problem', 'text', true], ['goal', 'Goal', 'textarea', true], ['interventions', 'Interventions', 'textarea', true]], async (data) => { await createCarePlan(admission, data); await done(); });
  const fluidBalanceForm = (root, admission, done) => form(root, 'Fluid Balance', [['fluid_type', 'Fluid type', 'select', true, [['oral', 'Oral intake'], ['iv_fluid', 'IV fluid'], ['blood', 'Blood products'], ['other_input', 'Other input'], ['urine', 'Urine'], ['stool', 'Stool'], ['vomit', 'Vomit/NG output'], ['drain', 'Drain output'], ['other_output', 'Other output']]], ['volume_ml', 'Volume (ml)', 'number', true]], async (data) => { data.volume_ml = parseInt(data.volume_ml); await createFluidEntry(admission, data); await done(); });
  const procedureNoteForm = (root, admission, done) => form(root, 'Procedure Note', [['procedure_name', 'Procedure name', 'text', true], ['indication', 'Indication'], ['anaesthesia_type', 'Anaesthesia'], ['findings', 'Findings', 'textarea', true], ['complications', 'Complications'], ['outcome', 'Outcome'], ['notes', 'Post-procedure notes']], async (data) => { await createProcedureNote(admission, data); await done(); });
  const nursingAssessmentForm = (root, admission, done) => form(root, 'Nursing Assessment', [['assessment_note', 'Assessment note', 'textarea', true]], async (data) => { data.problems = []; await createNursingAssessment(admission, data); await done(); });
  const marForm = (root, admission, prescriptions, done) => form(root, 'MAR Entry', [['prescription_local_id', 'Prescription', 'select', true, prescriptions.map((p) => [p.id, `${p.drug_name} ${p.dose} ${p.frequency}`])], ['dose_given', 'Dose given', 'text', true], ['route', 'Route', 'select', true, [['oral', 'Oral'], ['iv', 'IV'], ['im', 'IM'], ['sc', 'SC'], ['topical', 'Topical'], ['rectal', 'Rectal'], ['other', 'Other']]], ['site', 'Site'], ['notes', 'Notes']], async (data) => { const rx = prescriptions.find((p) => p.id === data.prescription_local_id); data.route = data.route; await createMAREntry(admission, rx, data); await done(); });
  const referralForm = (root, patient, done) => form(root, 'Create Referral', [['destination', 'Destination department', 'select', true, [['Laboratory', 'Laboratory'], ['Imaging', 'Imaging / Radiology'], ['Pharmacy', 'Pharmacy'], ['Theatre', 'Theatre'], ['ICU', 'ICU / HDU'], ['Ward', 'Ward'], ['Physiotherapy', 'Physiotherapy'], ['Other facility', 'Other facility']]], ['reason', 'Reason'], ['source', 'Source', 'text', false, [], 'Ward']], async (data) => { if (!data.source) data.source = 'Ward'; await createReferral(patient, data); await done(); });
  const prescribeForm = (root, patient, drugs, done) => form(root, `Prescribe for ${patient.first_name} ${patient.last_name}`, [['drug_id', 'Drug', 'select', true, drugs.map((d) => [d.id, `${d.generic_name} (${d.formulation})`])], ['dose', 'Dose', 'text', true], ['route', 'Route', 'select', true, [['oral', 'Oral'], ['iv', 'IV'], ['im', 'IM'], ['sc', 'SC'], ['topical', 'Topical'], ['rectal', 'Rectal'], ['other', 'Other']]], ['frequency', 'Frequency', 'text', true], ['duration_days', 'Duration (days)', 'number'], ['notes', 'Notes']], async (data) => { data.duration_days = data.duration_days ? parseInt(data.duration_days) : null; const drug = drugs.find((d) => String(d.id) === String(data.drug_id)); data.drug_id = parseInt(data.drug_id); await prescribeDrug(patient, drug, data); await done(); });
  const approveForm = (root, rx, done) => form(root, `Approve: ${rx.drug_name || 'Prescription'}`, [], async (data) => { await approvePrescription(rx, data); await done(); });
  const dispenseForm = (root, rx, done) => form(root, `Dispense: ${rx.drug_name || 'Prescription'}`, [['quantity_dispensed', 'Quantity', 'text', true], ['stock_note', 'Stock note']], async (data) => { await dispensePrescription(rx, data); await done(); });
  const labOrderForm = (root, patient, labTests, done) => form(root, `Order Lab Test for ${patient.first_name} ${patient.last_name}`, [['test_id', 'Test', 'select', true, labTests.map((t) => [t.id, `${t.name} (${t.specimen_type})`])], ['encounter_id', 'Encounter ID (optional)', 'text']], async (data) => { data.encounter_id = data.encounter_id ? parseInt(data.encounter_id) : null; const labTest = labTests.find((t) => String(t.id) === String(data.test_id)); data.test_id = parseInt(data.test_id); await createLabOrder(patient, labTest, data); await done(); });
  const collectSpecimenForm = (root, order, done) => form(root, `Collect: ${order.test_name || 'Specimen'}`, [], async (data) => { await collectLabSpecimen(order, data); await done(); });
  const labResultForm = (root, order, done) => form(root, `Enter Result: ${order.test_name || 'Test'}`, [['value_text', 'Result (text)', 'text', true], ['value_numeric', 'Result (numeric)', 'number'], ['notes', 'Notes']], async (data) => { data.value_numeric = data.value_numeric ? parseFloat(data.value_numeric) : null; await enterLabResult(order, data); await done(); });
  const verifyResultForm = (root, result, done) => form(root, `Verify: ${result.test_name || 'Result'}`, [], async (data) => { await verifyLabResult(result, data); await done(); });
  const imagingRequestForm = (root, patient, modalities, done) => form(root, `Request Imaging for ${patient.first_name} ${patient.last_name}`, [['modality_id', 'Modality', 'select', true, modalities.map((m) => [m.id, m.name])], ['clinical_indication', 'Clinical indication', 'textarea', true], ['pregnancy_status_checked', 'Pregnancy status checked', 'checkbox']], async (data) => { data.clinical_indication = data.clinical_indication || ''; data.pregnancy_status_checked = data.pregnancy_status_checked === 'on'; const modality = modalities.find((m) => String(m.id) === String(data.modality_id)); data.modality_id = parseInt(data.modality_id); await createImagingRequest(patient, modality, data); await done(); });
  const imagingReportForm = (root, imagingReq, done) => form(root, `Report: ${imagingReq.modality_name || 'Imaging'}`, [['findings', 'Findings', 'textarea', true], ['impression', 'Impression', 'textarea', true], ['is_critical_finding', 'Critical finding', 'checkbox'], ['image_reference', 'Image reference']], async (data) => { data.findings = data.findings || ''; data.impression = data.impression || ''; data.is_critical_finding = data.is_critical_finding === 'on'; await enterImagingReport(imagingReq, data); await done(); });
  const triageForm = (root, patient, done) => form(root, `Triage: ${patient.first_name} ${patient.last_name}`, [['triage_category', 'Category', 'select', true, [['immediate', 'Immediate (Resuscitation)'], ['emergency', 'Emergency'], ['urgent', 'Urgent'], ['standard', 'Standard'], ['non_urgent', 'Non-Urgent']]], ['presenting_condition', 'Presenting condition', 'textarea', true], ['outcome', 'Outcome', 'select', false, [['', '---'], ['discharged', 'Discharged'], ['admitted', 'Admitted'], ['referred', 'Referred'], ['dead', 'Dead']]], ['disposition_note', 'Disposition note']], async (data) => { await createTriage(patient, data); await done(); });
  const resolveTriageForm = (root, triage, done) => form(root, `Resolve: ${triage.triage_category || 'Triage'}`, [['outcome', 'Outcome', 'select', true, [['discharged', 'Discharged'], ['admitted', 'Admitted'], ['referred', 'Referred'], ['dead', 'Dead']]], ['disposition_note', 'Disposition note']], async (data) => { await resolveTriage(triage, data); await done(); });
  const dialysisPrescriptionForm = (root, patient, done) => form(root, `Dialysis Prescription for ${patient.first_name} ${patient.last_name}`, [['frequency_per_week', 'Sessions per week', 'number', true], ['vascular_access', 'Vascular access', 'select', true, [['av_fistula', 'AV Fistula'], ['av_graft', 'AV Graft'], ['tunneled_catheter', 'Tunneled Catheter'], ['temporary_catheter', 'Temporary Catheter'], ['peritoneal', 'Peritoneal']]], ['target_fluid_removal_l', 'Target fluid removal (L)', 'number']], async (data) => { data.frequency_per_week = parseInt(data.frequency_per_week); data.target_fluid_removal_l = data.target_fluid_removal_l ? parseFloat(data.target_fluid_removal_l) : null; await createDialysisPrescription(patient, data); await done(); });
  const dialysisSessionForm = (root, prescriptions, done) => form(root, 'Record Dialysis Session', [['prescription_local_id', 'Prescription', 'select', true, prescriptions.map((p) => [p.id, `${p.frequency_per_week}x/week — ${p.vascular_access}`])], ['pre_weight_kg', 'Pre-dialysis weight (kg)', 'number', true], ['post_weight_kg', 'Post-dialysis weight (kg)', 'number', true], ['complications', 'Complications'], ['notes', 'Notes']], async (data) => { data.pre_weight_kg = parseFloat(data.pre_weight_kg); data.post_weight_kg = parseFloat(data.post_weight_kg); const rx = prescriptions.find((p) => p.id === data.prescription_local_id); await recordDialysisSession(rx, data); await done(); });
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
