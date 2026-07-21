from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import connection

from accounts.models import Profile
from billing.models import InvoiceLineItem, ServiceCatalogItem
from billing.services import add_line_item, create_invoice, record_payment
from encounters.models import AllergyRecord
from encounters.services import create_encounter, sign_encounter
from imaging.models import ImagingModality
from imaging.services import create_request, enter_report
from inpatient.models import Bed, Ward
from inpatient.services import admit_patient, assign_bed
from laboratory.models import LabTest
from laboratory.services import create_order, enter_result
from patients.models import NextOfKin, Patient, PatientNumberSequence
from patients.services import register_patient
from pharmacy.models import Drug
from pharmacy.safety import CriticalSafetyBlock
from pharmacy.services import approve, dispense, prescribe
from vitals.services import record_vitals

ROLES = [
    ("Grace", "Banda", "nurse1", "NURSE", "OPD"),
    ("John", "Mkandawire", "clinician1", "CLINICIAN", "OPD"),
    ("Mary", "Phiri", "pharmacist1", "PHARMACIST", "Pharmacy"),
    ("Peter", "Kachale", "labtech1", "LAB_TECH", "Laboratory"),
    ("Esther", "Nkhoma", "radiog1", "RADIOGRAPHER", "Imaging"),
    ("Paul", "Banda", "billing1", "BILLING_OFFICER", "Billing"),
    ("Sarah", "Moyo", "admin1", "ADMIN", "Administration"),
    ("David", "Kamanga", "ict1", "ICT", "ICT"),
]

USERS = {}

PATIENTS_DATA = [
    {
        "first_name": "Chifundo",
        "last_name": "Mkandawire",
        "sex": "male",
        "date_of_birth": date(1982, 5, 12),
        "village": "Mkanda",
        "traditional_authority": "M'mbelwa",
        "district": "Mzimba",
        "region": "northern",
        "phone_number": "0999123456",
        "next_of_kin": {"name": "Mary Mkandawire", "relationship": "Spouse", "phone_number": "0888123456"},
        "encounters": [
            {
                "type": "outpatient",
                "complaint": "Fever with chills for 2 days, headache, body aches",
                "diagnosis": "Uncomplicated malaria",
                "icd_code": "1F40",
                "icd_display": "Malaria due to Plasmodium falciparum",
                "plan": "Artemether Lumefantrine course, review in 3 days if no improvement",
                "vitals": {
                    "temperature_c": Decimal("39.2"),
                    "blood_pressure_systolic": 125,
                    "blood_pressure_diastolic": 80,
                    "pulse_rate": 95,
                    "respiratory_rate": 18,
                    "oxygen_saturation": 98,
                    "weight_kg": Decimal("68.0"),
                    "height_cm": Decimal("172.0"),
                    "pain_score": 5,
                },
                "labs": [{"test_name": "Malaria RDT", "value_text": "Positive"}],
                "pharmacy": {
                    "drug_name": "Artemether Lumefantrine",
                    "dose": "4 tablets",
                    "route": "oral",
                    "frequency": "twice daily for 3 days",
                    "duration_days": 3,
                },
            }
        ],
        "billing": {"payer_type": "self_pay", "services": ["CONS", "MRDT", "RX"]},
    },
    {
        "first_name": "Grace",
        "last_name": "Banda",
        "sex": "female",
        "date_of_birth": date(1995, 8, 25),
        "village": "Chimutu",
        "traditional_authority": "T/A Chikowi",
        "district": "Zomba",
        "region": "southern",
        "phone_number": "0999456789",
        "next_of_kin": {"name": "James Banda", "relationship": "Husband", "phone_number": "0888654321"},
        "encounters": [
            {
                "type": "outpatient",
                "complaint": "Routine antenatal visit, feeling well",
                "diagnosis": "Normal pregnancy, 24 weeks gestation",
                "icd_code": "QA0Y",
                "icd_display": "Antenatal care for normal pregnancy",
                "plan": "Continue ANC, next visit in 4 weeks, FBC for baseline",
                "vitals": {
                    "temperature_c": Decimal("36.8"),
                    "blood_pressure_systolic": 110,
                    "blood_pressure_diastolic": 70,
                    "pulse_rate": 78,
                    "respiratory_rate": 16,
                    "oxygen_saturation": 99,
                    "weight_kg": Decimal("62.0"),
                    "height_cm": Decimal("158.0"),
                    "pain_score": 0,
                    "pregnancy_status": "pregnant",
                },
                "labs": [{"test_name": "Full Blood Count", "value_numeric": Decimal("10.5")}],
            }
        ],
        "billing": {"payer_type": "self_pay", "services": ["CONS", "FBC"]},
    },
    {
        "first_name": "Kondwani",
        "last_name": "Phiri",
        "sex": "male",
        "date_of_birth": date(2018, 3, 10),
        "village": "Kawale",
        "traditional_authority": "T/A Chadza",
        "district": "Lilongwe",
        "region": "central",
        "phone_number": "0999789123",
        "next_of_kin": {"name": "Martha Phiri", "relationship": "Mother", "phone_number": "0999789456"},
        "encounters": [
            {
                "type": "outpatient",
                "complaint": "Cough and fever for 5 days, difficulty breathing",
                "diagnosis": "Community-acquired pneumonia",
                "icd_code": "CA40",
                "icd_display": "Pneumonia due to bacteria",
                "plan": "Amoxicillin 250mg 1 capsule TDS for 7 days, review if no improvement in 48 hours",
                "allergies": [{"allergen": "Penicillin", "reaction": "Rash and itching", "severity": "moderate"}],
                "vitals": {
                    "temperature_c": Decimal("38.9"),
                    "blood_pressure_systolic": 100,
                    "blood_pressure_diastolic": 65,
                    "pulse_rate": 110,
                    "respiratory_rate": 28,
                    "oxygen_saturation": 94,
                    "weight_kg": Decimal("28.0"),
                    "height_cm": Decimal("132.0"),
                    "pain_score": 4,
                },
                "imaging": {
                    "modality_name": "X-ray",
                    "indication": "Chest pain, persistent cough, suspected pneumonia",
                    "findings": "Consolidation in right lower lobe with air bronchogram",
                    "impression": "Right lower lobe pneumonia",
                    "critical": False,
                },
                "pharmacy": {
                    "drug_name": "Amoxicillin 250mg",
                    "dose": "250 mg",
                    "route": "oral",
                    "frequency": "three times daily",
                    "duration_days": 7,
                    # Deliberately left blocked: this patient has a documented
                    # penicillin allergy (see the AllergyRecord above), so this
                    # attempt is expected to be rejected by the critical-safety
                    # check with no override possible - see `fallback` below
                    # for what actually gets prescribed instead. This is a
                    # demo of the safety block working, not a bug.
                    "fallback": {
                        "drug_name": "Ceftriaxone 1g",
                        "dose": "500 mg",
                        "route": "IM",
                        "frequency": "once daily",
                        "duration_days": 7,
                    },
                },
            }
        ],
        "billing": {"payer_type": "self_pay", "services": ["CONS", "CXR", "RX"]},
    },
    {
        "first_name": "Mary",
        "last_name": "Njewa",
        "sex": "female",
        "date_of_birth": date(1965, 11, 3),
        "village": "Nkhotakota Boma",
        "traditional_authority": "T/A Mphonde",
        "district": "Nkhotakota",
        "region": "central",
        "phone_number": "0999234567",
        "next_of_kin": {"name": "Thomas Njewa", "relationship": "Son", "phone_number": "0888678901"},
        "encounters": [
            {
                "type": "follow_up",
                "complaint": "Diabetes follow-up, occasional dizziness",
                "diagnosis": "Type 2 diabetes mellitus, poorly controlled",
                "icd_code": "5A11",
                "icd_display": "Type 2 diabetes mellitus",
                "plan": "Increase Metformin to 500mg BD, review blood glucose, diet counselling",
                "vitals": {
                    "temperature_c": Decimal("36.5"),
                    "blood_pressure_systolic": 145,
                    "blood_pressure_diastolic": 90,
                    "pulse_rate": 82,
                    "respiratory_rate": 16,
                    "oxygen_saturation": 98,
                    "weight_kg": Decimal("78.0"),
                    "height_cm": Decimal("162.0"),
                    "pain_score": 1,
                    "blood_glucose": Decimal("13.5"),
                },
                "labs": [{"test_name": "Random Blood Glucose", "value_numeric": Decimal("13.5")}],
                "pharmacy": {
                    "drug_name": "Metformin 500mg",
                    "dose": "500 mg",
                    "route": "oral",
                    "frequency": "twice daily",
                    "duration_days": 30,
                },
            }
        ],
        "billing": {"payer_type": "self_pay", "services": ["CONS", "FBC", "RX"]},
    },
    {
        "first_name": "Memory",
        "last_name": "Kumwenda",
        "sex": "female",
        "date_of_birth": date(1991, 12, 18),
        "village": "Bwaila",
        "traditional_authority": "T/A Kalonga",
        "district": "Salima",
        "region": "central",
        "phone_number": "0999567123",
        "next_of_kin": {"name": "Andrew Kumwenda", "relationship": "Brother", "phone_number": "0999567890"},
        "encounters": [
            {
                "type": "emergency",
                "complaint": "Lower abdominal pain for 1 day, vaginal spotting",
                "diagnosis": "Threatened abortion, 10 weeks pregnant",
                "icd_code": "JA00.0",
                "icd_display": "Threatened abortion",
                "plan": "Admit for observation, ultrasound to confirm viability, bed rest",
                "vitals": {
                    "temperature_c": Decimal("37.1"),
                    "blood_pressure_systolic": 100,
                    "blood_pressure_diastolic": 60,
                    "pulse_rate": 95,
                    "respiratory_rate": 18,
                    "oxygen_saturation": 99,
                    "weight_kg": Decimal("60.0"),
                    "height_cm": Decimal("165.0"),
                    "pain_score": 6,
                    "pregnancy_status": "pregnant",
                },
                "labs": [
                    {"test_name": "Full Blood Count", "value_numeric": Decimal("9.0")},
                    {"test_name": "Pregnancy Test", "value_text": "Positive"},
                ],
                "imaging": {
                    "modality_name": "Ultrasound",
                    "indication": "Threatened abortion, assess fetal viability and gestational age",
                    "findings": "Intrauterine pregnancy of approximately 10 weeks 2 days. Fetal heartbeat detected. Small subchorionic hematoma noted.",
                    "impression": "Threatened abortion with subchorionic hematoma, fetal heart activity present - good prognosis",
                    "critical": True,
                },
            }
        ],
        "billing": {"payer_type": "self_pay", "services": ["CONS", "FBC", "US"]},
    },
]


def create_users():
    group_name_map = {
        "NURSE": "Nurse",
        "CLINICIAN": "Clinician",
        "PHARMACIST": "Pharmacist",
        "LAB_TECH": "LabTech",
        "RADIOGRAPHER": "Radiographer",
        "BILLING_OFFICER": "BillingOfficer",
        "ADMIN": "Admin",
        "ICT": "ICT",
    }
    for role_name in group_name_map.values():
        Group.objects.get_or_create(name=role_name)
    for first, last, username, role_key, dept in ROLES:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first,
                "last_name": last,
                "email": f"{username}@example.com",
                "is_staff": True,
            },
        )
        if created:
            user.set_password("test123")
            user.save()
        Profile.objects.update_or_create(
            user=user,
            defaults={"role": role_key, "department": dept, "phone_number": f"0999000{username[-1]}"},
        )
        group_name = group_name_map[role_key]
        user.groups.add(Group.objects.get(name=group_name))
        USERS[role_key] = user
    return USERS


def create_wards_and_beds():
    wards_data = [
        ("Medical Ward", "Medicine", 18),
        ("Surgical Ward", "Surgery", 16),
        ("Paediatric Ward", "Paediatrics", 16),
        ("Maternity Ward", "Obstetrics", 16),
    ]
    for name, dept, bed_count in wards_data:
        ward, _ = Ward.objects.get_or_create(name=name, defaults={"department": dept, "bed_count": bed_count})
        for i in range(1, bed_count + 1):
            Bed.objects.get_or_create(ward=ward, label=f"{ward.name[0]}-{i:02d}")
    return Ward.objects.all()


def seed_demo_admission(patient, beds):
    """Admit patient #5 (Mary Gondwe, the dialysis patient) as a demo."""
    clinician = USERS["CLINICIAN"]
    ward = Ward.objects.filter(name="Medical Ward").first()
    if not ward:
        return
    bed = Bed.objects.filter(ward=ward, is_occupied=False).first()
    if not bed:
        return
    admission = admit_patient(patient, clinician, "CKD Stage 4 - initiate hemodialysis", bed=bed)
    return admission


class Command(BaseCommand):
    help = "Seed the database with realistic demo data for the full patient journey"

    def _seed_patient(self, data):
        nurse = USERS["NURSE"]
        clinician = USERS["CLINICIAN"]
        billing_officer = USERS["BILLING_OFFICER"]

        patient = register_patient(
            data={
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "sex": data["sex"],
                "date_of_birth": data["date_of_birth"],
                "village": data["village"],
                "traditional_authority": data["traditional_authority"],
                "district": data["district"],
                "region": data["region"],
                "phone_number": data["phone_number"],
                "age_estimated": data.get("age_estimated", False),
            },
            registered_by=nurse,
        )

        if nok := data.get("next_of_kin"):
            NextOfKin.objects.get_or_create(
                patient=patient,
                name=nok["name"],
                defaults={"relationship": nok["relationship"], "phone_number": nok.get("phone_number", "")},
            )

        for enc_data in data["encounters"]:
            encounter = create_encounter(
                patient=patient,
                clinician=clinician,
                data={
                    "encounter_type": enc_data["type"],
                    "presenting_complaint": enc_data["complaint"],
                    "diagnosis": enc_data["diagnosis"],
                    "icd_code": enc_data.get("icd_code", ""),
                    "icd_display": enc_data.get("icd_display", ""),
                    "clinical_plan": enc_data["plan"],
                },
            )

            for allergy in enc_data.get("allergies", []):
                AllergyRecord.objects.get_or_create(
                    patient=patient,
                    allergen=allergy["allergen"],
                    defaults={
                        "reaction": allergy["reaction"],
                        "severity": allergy["severity"],
                        "recorded_by": clinician,
                    },
                )

            if vitals_data := enc_data.get("vitals"):
                record_vitals(encounter=encounter, recorded_by=nurse, data=vitals_data)

            if labs := enc_data.get("labs"):
                lab_tech = USERS["LAB_TECH"]
                for lab in labs:
                    try:
                        lab_test = LabTest.objects.get(name=lab["test_name"])
                    except LabTest.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"  Lab test '{lab['test_name']}' not found, skipping"))
                        continue
                    lab_order = create_order(patient=patient, test=lab_test, ordered_by=clinician, encounter=encounter)
                    kwargs = {}
                    if "value_numeric" in lab:
                        kwargs["value_numeric"] = lab["value_numeric"]
                    if "value_text" in lab:
                        kwargs["value_text"] = lab["value_text"]
                    if kwargs:
                        enter_result(order=lab_order, data=kwargs, entered_by=lab_tech)

            if imaging := enc_data.get("imaging"):
                radiographer = USERS["RADIOGRAPHER"]
                try:
                    modality = ImagingModality.objects.get(name=imaging["modality_name"])
                except ImagingModality.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Modality '{imaging['modality_name']}' not found, skipping"))
                    continue
                im_req = create_request(
                    patient=patient,
                    modality=modality,
                    requested_by=clinician,
                    clinical_indication=imaging["indication"],
                    encounter=encounter,
                    pregnancy_status_checked=True,
                )
                enter_report(
                    request=im_req,
                    data={
                        "findings": imaging["findings"],
                        "impression": imaging["impression"],
                        "is_critical_finding": imaging["critical"],
                    },
                    reported_by=radiographer,
                )

            if pharmacy := enc_data.get("pharmacy"):
                pharmacist = USERS["PHARMACIST"]
                try:
                    drug = Drug.objects.get(name=pharmacy["drug_name"])
                except Drug.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Drug '{pharmacy['drug_name']}' not found, skipping"))
                    continue
                presc_data = {
                    "dose": pharmacy["dose"],
                    "route": pharmacy["route"],
                    "frequency": pharmacy["frequency"],
                    "duration_days": pharmacy["duration_days"],
                    "encounter": encounter,
                }
                if "safety_override_reason" in pharmacy:
                    presc_data["safety_override_reason"] = pharmacy["safety_override_reason"]
                try:
                    presc, warnings = prescribe(
                        patient=patient,
                        drug=drug,
                        prescribed_by=clinician,
                        data=presc_data,
                    )
                except CriticalSafetyBlock as exc:
                    self.stdout.write(self.style.WARNING(
                        f"  Prescription of {drug.generic_name} for {patient.full_name} correctly "
                        f"BLOCKED by critical safety check: {'; '.join(w.message for w in exc.warnings)}"
                    ))
                    fallback = pharmacy.get("fallback")
                    if not fallback:
                        continue
                    try:
                        drug = Drug.objects.get(name=fallback["drug_name"])
                    except Drug.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"  Fallback drug '{fallback['drug_name']}' not found, skipping"))
                        continue
                    presc, warnings = prescribe(
                        patient=patient,
                        drug=drug,
                        prescribed_by=clinician,
                        data={
                            "dose": fallback["dose"],
                            "route": fallback["route"],
                            "frequency": fallback["frequency"],
                            "duration_days": fallback["duration_days"],
                            "encounter": encounter,
                        },
                    )
                    self.stdout.write(self.style.SUCCESS(f"  Prescribed {drug.generic_name} instead (penicillin-allergy-safe alternative)"))
                approved_presc = approve(prescription=presc, approved_by=pharmacist)
                dispense(
                    prescription=approved_presc,
                    dispensed_by=pharmacist,
                    data={"quantity_dispensed": f"{presc.duration_days * 2} tablets"},
                )

            sign_encounter(encounter=encounter, clinician=clinician)

        if billing := data.get("billing"):
            invoice = create_invoice(patient=patient, created_by=billing_officer, payer_type=billing["payer_type"])
            for service_code in billing["services"]:
                try:
                    item = ServiceCatalogItem.objects.get(code=service_code)
                except ServiceCatalogItem.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Service '{service_code}' not found, skipping"))
                    continue
                add_line_item(invoice=invoice, service_item=item)
            total = sum(ln.amount_mwk for ln in InvoiceLineItem.objects.filter(invoice=invoice))
            record_payment(invoice=invoice, amount_mwk=total, method="cash", received_by=billing_officer)

        return patient

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing demo data before seeding",
        )

    def _flush(self):
        self.stdout.write("Flushing existing demo data...")
        tables = [
            "billing_payment",
            "billing_invoicelineitem",
            "billing_invoice",
            "pharmacy_dispensingrecord",
            "pharmacy_prescription",
            "imaging_imagingreport",
            "imaging_imagingrequest",
            "laboratory_labresult",
            "laboratory_laborder",
            "vitals_earlywarningscore",
            "vitals_vitalsignset",
            "reporting_alertevent",
            "encounters_encounteraddendum",
            "encounters_allergyrecord",
            "encounters_encounter",
            "emergency_triageencounter",
            "emergency_historicaltriageencounter",
            "dialysis_dialysissession",
            "dialysis_dialysisprescription",
            "dialysis_ckddiagnosis",
            "dialysis_historicaldialysissession",
            "dialysis_historicaldialysisprescription",
            "dialysis_historicalckddiagnosis",
            "inpatient_wardroundnote",
            "inpatient_admission",
            "inpatient_bed",
            "inpatient_ward",
            "inpatient_historicalwardroundnote",
            "inpatient_historicaladmission",
            "patients_nextofkin",
            "patients_duplicateconfirmation",
            "patients_patient",
            "patients_patientnumbersequence",
            "accounts_profile",
        ]
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
        self.stdout.write(self.style.SUCCESS("  Done."))

    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        self.stdout.write(self.style.NOTICE("Seeding demo data..."))

        self.stdout.write("Creating users...")
        create_users()
        self.stdout.write(self.style.SUCCESS(f"  Created {len(USERS)} users"))

        self.stdout.write("Creating wards and beds...")
        create_wards_and_beds()
        self.stdout.write(self.style.SUCCESS("  Wards and beds created"))

        self.stdout.write("Creating patients and clinical data...")
        patients = []
        for i, pdata in enumerate(PATIENTS_DATA, 1):
            patient = self._seed_patient(pdata)
            patients.append(patient)
            name = f"{patient.first_name} {patient.last_name}"
            self.stdout.write(self.style.SUCCESS(f"  [{i}] {name} ({patient.patient_number})"))

        self.stdout.write("Creating demo admission for patient #5...")
        if len(patients) >= 5:
            seed_demo_admission(patients[4], None)
            self.stdout.write(self.style.SUCCESS("  Patient #5 admitted to Medical Ward"))

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully!"))
        self.stdout.write("Users: nurse1, clinician1, pharmacist1, labtech1, radiog1, billing1, admin1, ict1")
        self.stdout.write("All passwords: test123")
