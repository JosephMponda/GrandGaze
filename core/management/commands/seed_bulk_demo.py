"""
Bulk demo-data seed command for GrandGaze.

Seeds:
  - 10 staff users for every role in accounts.models.Role (80 users total)
  - 30 patients covering a spread of clinical scenarios (malaria, pneumonia,
    NCDs, obstetric emergencies, paediatrics, trauma, elderly care, etc.),
    each with a full encounter -> vitals -> labs/imaging/pharmacy -> billing
    trail, using only the reference data already seeded by the app
    migrations (LabTest, Drug, ImagingModality, ServiceCatalogItem).
  - A handful of those patients are admitted as inpatients so Inpatient
    module screens have data too.

This file follows the exact same service-layer call pattern as the
existing `core/management/commands/seed_demo.py` (register_patient,
create_encounter, record_vitals, create_order/enter_result,
create_request/enter_report, prescribe/approve/dispense, create_invoice/
add_line_item/record_payment) so it is safe to run against the same schema.

Usage:
    python manage.py seed_bulk_demo
    python manage.py seed_bulk_demo --flush   # wipe demo data first
"""

from datetime import date
from decimal import Decimal
import random

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
from inpatient.services import admit_patient
from laboratory.models import LabTest
from laboratory.services import create_order, enter_result
from patients.models import NextOfKin, Patient
from patients.services import register_patient
from pharmacy.models import Drug
from pharmacy.safety import CriticalSafetyBlock
from pharmacy.services import approve, dispense, prescribe
from vitals.services import record_vitals

# ---------------------------------------------------------------------------
# Roles: 10 staff members per role (matches accounts.models.Role exactly)
# ---------------------------------------------------------------------------

ROLE_DEFS = [
    ("NURSE", "Nurse", "nurse", "OPD"),
    ("CLINICIAN", "Clinician", "clinician", "OPD"),
    ("PHARMACIST", "Pharmacist", "pharmacist", "Pharmacy"),
    ("LAB_TECH", "LabTech", "labtech", "Laboratory"),
    ("RADIOGRAPHER", "Radiographer", "radiog", "Imaging"),
    ("BILLING_OFFICER", "BillingOfficer", "billing", "Billing"),
    ("ADMIN", "Admin", "admin", "Administration"),
    ("ICT", "ICT", "ict", "ICT"),
]

STAFF_FIRST_NAMES = [
    "Grace", "John", "Mary", "Peter", "Esther", "Paul", "Sarah", "David",
    "Chisomo", "Blessings", "Patricia", "Frank", "Agnes", "Wisdom", "Ruth",
    "Harold", "Joyce", "Enock", "Violet", "Isaac", "Dorothy", "Andrew",
    "Faith", "Steven", "Ellen", "Moses", "Beatrice", "Charles", "Linda",
    "Gift", "Loveness", "Yohane", "Precious", "Bright", "Winnie", "Fred",
    "Catherine", "Emmanuel", "Rose", "Alfred", "Tadala", "Zione", "Hastings",
    "Bertha", "Clement", "Eness", "Owen", "Chikondi", "Vitumbiko", "Gladys",
    "Bester", "Kondwani", "Susan", "Nelson", "Thoko", "Boniface", "Mercy",
    "Alick", "Felistas", "Griffin", "Jane", "Rodrick", "Anna", "Elias",
    "Verah", "Osman", "Naomi", "Simeon", "Idah", "Wyson", "Elube", "Perry",
    "Chrissy", "Robert", "Alinane", "Steve", "Diana", "Amos", "Prisca",
    "Zondiwe", "Innocent", "Gertrude",
]

STAFF_LAST_NAMES = [
    "Banda", "Mkandawire", "Phiri", "Kachale", "Nkhoma", "Moyo", "Kamanga",
    "Chirwa", "Gondwe", "Mvula", "Zimba", "Nyirenda", "Chikapa", "Mbewe",
    "Chilenga", "Msiska", "Kaunda", "Chapola", "Chisale", "Kalua", "Longwe",
    "Mhango", "Chiumia", "Chikoti", "Malunga", "Kanyenda", "Chimwendo",
    "Kaira", "Simfukwe", "Chikwakwa", "Munthali", "Ngwira", "Chirambo",
    "Chilongo", "Kayira", "Sichinga", "Kaira", "Chapasuka", "Chiwaya",
]


def _staff_name(seq: int) -> tuple[str, str]:
    first = STAFF_FIRST_NAMES[seq % len(STAFF_FIRST_NAMES)]
    last = STAFF_LAST_NAMES[seq % len(STAFF_LAST_NAMES)]
    return first, last


def create_users() -> dict[str, list[User]]:
    """Create 10 users per role. Returns {role_key: [10 User objects]}."""
    for _, group_name, _, _ in ROLE_DEFS:
        Group.objects.get_or_create(name=group_name)

    users_by_role: dict[str, list[User]] = {}
    seq = 0
    for role_key, group_name, prefix, dept in ROLE_DEFS:
        role_users = []
        for i in range(1, 11):
            username = f"{prefix}{i}"
            first, last = _staff_name(seq)
            seq += 1
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
                defaults={"role": role_key, "department": dept, "phone_number": f"099900{seq:04d}"},
            )
            user.groups.add(Group.objects.get(name=group_name))
            role_users.append(user)
        users_by_role[role_key] = role_users
    return users_by_role


def create_wards_and_beds():
    wards_data = [
        ("Medical Ward", "Medicine", 10),
        ("Surgical Ward", "Surgery", 8),
        ("Paediatric Ward", "Paediatrics", 8),
        ("Maternity Ward", "Obstetrics", 8),
    ]
    for name, dept, bed_count in wards_data:
        ward, _ = Ward.objects.get_or_create(name=name, defaults={"department": dept, "bed_count": bed_count})
        for i in range(1, bed_count + 1):
            Bed.objects.get_or_create(ward=ward, label=f"{ward.name[0]}-{i:02d}")


# ---------------------------------------------------------------------------
# 30 patients / 15 distinct clinical scenarios (2 patients per scenario)
# Only reference data that already exists via migrations is used:
#   LabTest:  Full Blood Count, Malaria RDT, HIV Rapid Test, Creatinine,
#             Random Blood Glucose, Urinalysis, Pregnancy Test
#   Drug:     Amoxicillin 250mg, Ceftriaxone 1g, Paracetamol 500mg,
#             Ibuprofen 200mg, ORS sachet, Artemether Lumefantrine,
#             Metformin 500mg, Ferrous Sulphate, Salbutamol inhaler,
#             Gentamicin
#   Imaging:  X-ray, Ultrasound
#   Billing:  CONS, FBC, MRDT, HIV, CXR, US, RX, BED, PROC
# ---------------------------------------------------------------------------

REGIONS = ["northern", "central", "southern"]
DISTRICTS = {
    "northern": ["Mzimba", "Karonga", "Rumphi"],
    "central": ["Lilongwe", "Salima", "Kasungu", "Dedza"],
    "southern": ["Zomba", "Blantyre", "Mangochi", "Thyolo"],
}
VILLAGES = ["Kawale", "Chimutu", "Mkanda", "Bwaila", "Nkhotakota Boma", "Chilinde",
            "Mtandire", "Chigumula", "Namitembo", "Chirimba", "Mzedi", "Chinsapo"]

PATIENT_FIRST_NAMES_F = ["Chifundo", "Grace", "Memory", "Mary", "Tadala", "Ellen",
                          "Loveness", "Precious", "Winnie", "Agnes", "Beatrice",
                          "Joyce", "Faith", "Violet", "Naomi", "Patricia", "Fatima",
                          "Mercy", "Ruth", "Nadia", "Esther", "Jane", "Lilian",
                          "Olivia", "Zione", "Danielle", "Hilda", "Christine", "Esther",
                          "Rachael", "Julia"]
PATIENT_FIRST_NAMES_M = ["Kondwani", "Yamikani", "Chisomo", "Thomas", "Isaac",
                          "Moses", "Frank", "Enock", "Bright", "Owen", "Elias",
                          "Steven", "Boniface", "Andrew", "Fred", "Gabriel", "Austin",
                          "Daniel", "James", "Alex", "Joseph", "Patrick", "Kenneth",
                          "Hastings", "Felix", "Jonathan", "Maxwell", "Samson", "Michael",
                          "Victor"]
PATIENT_LAST_NAMES = ["Mkandawire", "Banda", "Phiri", "Njewa", "Kumwenda", "Gondwe",
                       "Chirwa", "Nyirenda", "Mvula", "Zimba", "Mbewe", "Chikapa",
                       "Kaunda", "Chisale", "Longwe", "Moya", "Mhone", "Mwale",
                       "Nkhata", "Phiri", "Piri", "Kambale", "Ndhlovu", "Mkwayi",
                       "Jumbe", "Sitali", "Masangano", "Nkhoma", "Mbewe"]

_next_of_kin_relationships = ["Spouse", "Mother", "Father", "Son", "Daughter",
                               "Brother", "Sister", "Guardian", "Aunt", "Uncle"]


def _phone(seq: int) -> str:
    return f"09{random.randint(900000, 999999):06d}"


def _demographics(seq: int, sex: str, dob: date, category: str = "outpatient"):
    region = random.choice(REGIONS)
    district = random.choice(DISTRICTS[region])
    village = random.choice(VILLAGES)
    first = random.choice(PATIENT_FIRST_NAMES_F if sex == "female" else PATIENT_FIRST_NAMES_M)
    last = random.choice(PATIENT_LAST_NAMES)
    kin_first = random.choice(PATIENT_FIRST_NAMES_M if sex == "female" else PATIENT_FIRST_NAMES_F)
    return {
        "first_name": first,
        "last_name": last,
        "sex": sex,
        "date_of_birth": dob,
        "village": village,
        "traditional_authority": f"T/A {village}",
        "district": district,
        "region": region,
        "phone_number": _phone(seq),
        "patient_category": category,
        "next_of_kin": {
            "name": f"{kin_first} {random.choice(PATIENT_LAST_NAMES)}",
            "relationship": random.choice(_next_of_kin_relationships),
            "phone_number": _phone(seq + 500),
        },
    }


# Each scenario is a template; two patients are generated per scenario
# with a small numeric "drift" so vitals aren't perfectly identical twins.
SCENARIOS = [
    dict(
        key="malaria_adult",
        sex="male", age_years=32, category="outpatient",
        type="outpatient",
        complaint="Fever with chills for 2 days, headache, body aches",
        diagnosis="Uncomplicated malaria",
        icd_code="1F40", icd_display="Malaria due to Plasmodium falciparum",
        plan="Artemether Lumefantrine course, review in 3 days if no improvement",
        vitals=dict(temperature_c=Decimal("39.2"), blood_pressure_systolic=125,
                    blood_pressure_diastolic=80, pulse_rate=95, respiratory_rate=18,
                    oxygen_saturation=98, weight_kg=Decimal("68.0"), height_cm=Decimal("172.0"),
                    pain_score=5),
        labs=[{"test_name": "Malaria RDT", "value_text": "Positive"}],
        pharmacy={"drug_name": "Artemether Lumefantrine", "dose": "4 tablets", "route": "oral",
                  "frequency": "twice daily for 3 days", "duration_days": 3},
        billing={"payer_type": "self_pay", "services": ["CONS", "MRDT", "RX"]},
    ),
    dict(
        key="antenatal_normal",
        sex="female", age_years=27, category="outpatient",
        type="outpatient",
        complaint="Routine antenatal visit, feeling well",
        diagnosis="Normal pregnancy, 24 weeks gestation",
        icd_code="QA0Y", icd_display="Antenatal care for normal pregnancy",
        plan="Continue ANC, next visit in 4 weeks, FBC for baseline",
        vitals=dict(temperature_c=Decimal("36.8"), blood_pressure_systolic=110,
                    blood_pressure_diastolic=70, pulse_rate=78, respiratory_rate=16,
                    oxygen_saturation=99, weight_kg=Decimal("62.0"), height_cm=Decimal("158.0"),
                    pain_score=0, pregnancy_status="pregnant"),
        labs=[{"test_name": "Full Blood Count", "value_numeric": Decimal("10.5")}],
        billing={"payer_type": "self_pay", "services": ["CONS", "FBC"]},
    ),
    dict(
        key="paeds_pneumonia",
        sex="male", age_years=6, category="outpatient",
        type="outpatient",
        complaint="Cough and fever for 5 days, difficulty breathing",
        diagnosis="Community-acquired pneumonia",
        icd_code="CA40", icd_display="Pneumonia due to bacteria",
        plan="Amoxicillin 250mg TDS for 7 days, review if no improvement in 48 hours",
        allergies=[{"allergen": "Penicillin", "reaction": "Rash and itching", "severity": "moderate"}],
        vitals=dict(temperature_c=Decimal("38.9"), blood_pressure_systolic=100,
                    blood_pressure_diastolic=65, pulse_rate=110, respiratory_rate=28,
                    oxygen_saturation=94, weight_kg=Decimal("18.0"), height_cm=Decimal("112.0"),
                    pain_score=4),
        imaging={"modality_name": "X-ray", "indication": "Suspected pneumonia",
                 "findings": "Consolidation in right lower lobe with air bronchogram",
                 "impression": "Right lower lobe pneumonia", "critical": False},
        pharmacy={"drug_name": "Amoxicillin 250mg", "dose": "250 mg", "route": "oral",
                  "frequency": "three times daily", "duration_days": 7,
                  # Deliberately blocked by the penicillin-allergy safety check above;
                  # fallback below is what actually gets dispensed.
                  "fallback": {"drug_name": "Ceftriaxone 1g", "dose": "500 mg", "route": "IM",
                               "frequency": "once daily", "duration_days": 7}},
        billing={"payer_type": "self_pay", "services": ["CONS", "CXR", "RX"]},
    ),
    dict(
        key="t2dm_followup",
        sex="female", age_years=61, category="outpatient",
        type="follow_up",
        complaint="Diabetes follow-up, occasional dizziness",
        diagnosis="Type 2 diabetes mellitus, poorly controlled",
        icd_code="5A11", icd_display="Type 2 diabetes mellitus",
        plan="Increase Metformin to 500mg BD, review blood glucose, diet counselling",
        vitals=dict(temperature_c=Decimal("36.5"), blood_pressure_systolic=145,
                    blood_pressure_diastolic=90, pulse_rate=82, respiratory_rate=16,
                    oxygen_saturation=98, weight_kg=Decimal("78.0"), height_cm=Decimal("162.0"),
                    pain_score=1, blood_glucose=Decimal("13.5")),
        labs=[{"test_name": "Random Blood Glucose", "value_numeric": Decimal("13.5")}],
        pharmacy={"drug_name": "Metformin 500mg", "dose": "500 mg", "route": "oral",
                  "frequency": "twice daily", "duration_days": 30},
        billing={"payer_type": "self_pay", "services": ["CONS", "FBC", "RX"]},
    ),
    dict(
        key="threatened_abortion",
        sex="female", age_years=24, category="emergency",
        type="emergency",
        complaint="Lower abdominal pain for 1 day, vaginal spotting",
        diagnosis="Threatened abortion, 10 weeks pregnant",
        icd_code="JA00.0", icd_display="Threatened abortion",
        plan="Admit for observation, ultrasound to confirm viability, bed rest",
        vitals=dict(temperature_c=Decimal("37.1"), blood_pressure_systolic=100,
                    blood_pressure_diastolic=60, pulse_rate=95, respiratory_rate=18,
                    oxygen_saturation=99, weight_kg=Decimal("60.0"), height_cm=Decimal("165.0"),
                    pain_score=6, pregnancy_status="pregnant"),
        labs=[{"test_name": "Full Blood Count", "value_numeric": Decimal("9.0")},
              {"test_name": "Pregnancy Test", "value_text": "Positive"}],
        imaging={"modality_name": "Ultrasound", "indication": "Assess fetal viability",
                 "findings": "Intrauterine pregnancy ~10w2d, fetal heartbeat present, small subchorionic hematoma",
                 "impression": "Threatened abortion, fetal heart activity present - good prognosis", "critical": True},
        billing={"payer_type": "self_pay", "services": ["CONS", "FBC", "US"]},
        admit=True, admit_ward="Maternity Ward", admit_diagnosis="Threatened abortion - observation",
    ),
    dict(
        key="hiv_testing",
        sex="male", age_years=29, category="outpatient",
        type="outpatient",
        complaint="Requesting HIV test, no symptoms, new relationship",
        diagnosis="HIV testing and counselling - result negative",
        icd_code="QA22", icd_display="Encounter for HIV testing",
        plan="Counsel on prevention, offer PrEP information, repeat test in 3 months if exposure risk",
        vitals=dict(temperature_c=Decimal("36.6"), blood_pressure_systolic=118,
                    blood_pressure_diastolic=76, pulse_rate=72, respiratory_rate=16,
                    oxygen_saturation=99, weight_kg=Decimal("70.0"), height_cm=Decimal("175.0"),
                    pain_score=0),
        labs=[{"test_name": "HIV Rapid Test", "value_text": "Negative"}],
        billing={"payer_type": "self_pay", "services": ["CONS", "HIV"]},
    ),
    dict(
        key="asthma_exacerbation",
        sex="female", age_years=15, category="emergency",
        type="emergency",
        complaint="Sudden shortness of breath and wheeze for 3 hours",
        diagnosis="Acute asthma exacerbation, moderate severity",
        icd_code="CA23.0", icd_display="Asthma, acute exacerbation",
        plan="Salbutamol nebulisation, observe response, discharge with inhaler if stable",
        vitals=dict(temperature_c=Decimal("36.9"), blood_pressure_systolic=112,
                    blood_pressure_diastolic=72, pulse_rate=118, respiratory_rate=30,
                    oxygen_saturation=92, weight_kg=Decimal("45.0"), height_cm=Decimal("158.0"),
                    pain_score=2),
        pharmacy={"drug_name": "Salbutamol inhaler", "dose": "2 puffs", "route": "inhaled",
                  "frequency": "every 4-6 hours as needed", "duration_days": 14},
        billing={"payer_type": "self_pay", "services": ["CONS", "RX"]},
    ),
    dict(
        key="gastroenteritis_child",
        sex="male", age_years=2, category="outpatient",
        type="outpatient",
        complaint="Watery diarrhoea and vomiting for 2 days, reduced feeding",
        diagnosis="Acute gastroenteritis with mild dehydration",
        icd_code="1A40", icd_display="Diarrhoea, presumed infectious origin",
        plan="ORS, continue breastfeeding, zinc supplementation, review in 2 days",
        vitals=dict(temperature_c=Decimal("37.6"), blood_pressure_systolic=90,
                    blood_pressure_diastolic=55, pulse_rate=128, respiratory_rate=32,
                    oxygen_saturation=97, weight_kg=Decimal("11.5"), height_cm=Decimal("84.0"),
                    pain_score=2),
        pharmacy={"drug_name": "ORS sachet", "dose": "1 sachet in 1L water", "route": "oral",
                  "frequency": "after each loose stool", "duration_days": 5},
        billing={"payer_type": "self_pay", "services": ["CONS", "RX"]},
    ),
    dict(
        key="anaemia_pregnancy",
        sex="female", age_years=33, category="outpatient",
        type="follow_up",
        complaint="Fatigue and dizziness on standing, known pregnant, 30 weeks",
        diagnosis="Iron deficiency anaemia in pregnancy",
        icd_code="JA61.0", icd_display="Anaemia complicating pregnancy",
        plan="Start ferrous sulphate, dietary counselling, recheck FBC in 4 weeks",
        vitals=dict(temperature_c=Decimal("36.7"), blood_pressure_systolic=105,
                    blood_pressure_diastolic=68, pulse_rate=88, respiratory_rate=18,
                    oxygen_saturation=98, weight_kg=Decimal("58.0"), height_cm=Decimal("160.0"),
                    pain_score=0, pregnancy_status="pregnant"),
        labs=[{"test_name": "Full Blood Count", "value_numeric": Decimal("7.8")}],
        pharmacy={"drug_name": "Ferrous Sulphate", "dose": "200 mg", "route": "oral",
                  "frequency": "once daily", "duration_days": 60},
        billing={"payer_type": "self_pay", "services": ["CONS", "FBC", "RX"]},
    ),
    dict(
        key="hypertensive_urgency_elderly",
        sex="male", age_years=72, category="emergency",
        type="emergency",
        complaint="Severe headache and blurred vision for 6 hours",
        diagnosis="Hypertensive urgency",
        icd_code="BA00", icd_display="Hypertensive urgency",
        plan="Admit for BP control and monitoring, renal function screen",
        vitals=dict(temperature_c=Decimal("36.6"), blood_pressure_systolic=196,
                    blood_pressure_diastolic=114, pulse_rate=92, respiratory_rate=20,
                    oxygen_saturation=96, weight_kg=Decimal("74.0"), height_cm=Decimal("168.0"),
                    pain_score=6),
        labs=[{"test_name": "Creatinine", "value_numeric": Decimal("135")}],
        billing={"payer_type": "self_pay", "services": ["CONS", "FBC", "BED"]},
        admit=True, admit_ward="Medical Ward", admit_diagnosis="Hypertensive urgency - BP control and monitoring",
    ),
    dict(
        key="uti_adult",
        sex="female", age_years=41, category="outpatient",
        type="outpatient",
        complaint="Burning on urination and frequency for 3 days",
        diagnosis="Uncomplicated urinary tract infection",
        icd_code="GC08.0", icd_display="Lower urinary tract infection",
        plan="Gentamicin course, increase oral fluids, review if symptoms persist",
        vitals=dict(temperature_c=Decimal("37.3"), blood_pressure_systolic=118,
                    blood_pressure_diastolic=76, pulse_rate=84, respiratory_rate=16,
                    oxygen_saturation=99, weight_kg=Decimal("64.0"), height_cm=Decimal("163.0"),
                    pain_score=3),
        labs=[{"test_name": "Urinalysis", "value_text": "Leukocytes and nitrites positive"}],
        pharmacy={"drug_name": "Gentamicin", "dose": "80 mg", "route": "IM",
                  "frequency": "once daily", "duration_days": 5},
        billing={"payer_type": "self_pay", "services": ["CONS", "RX"]},
    ),
    dict(
        key="minor_trauma",
        sex="male", age_years=19, category="emergency",
        type="emergency",
        complaint="Fall from bicycle, pain and swelling of right forearm",
        diagnosis="Suspected right forearm fracture",
        icd_code="NA0Y", icd_display="Fracture of forearm",
        plan="X-ray forearm, analgesia, refer to orthopaedic clinic if fracture confirmed",
        vitals=dict(temperature_c=Decimal("36.8"), blood_pressure_systolic=124,
                    blood_pressure_diastolic=80, pulse_rate=98, respiratory_rate=18,
                    oxygen_saturation=99, weight_kg=Decimal("62.0"), height_cm=Decimal("170.0"),
                    pain_score=7),
        imaging={"modality_name": "X-ray", "indication": "Suspected forearm fracture",
                 "findings": "Complete transverse fracture of distal radius with mild displacement",
                 "impression": "Distal radius fracture", "critical": False},
        pharmacy={"drug_name": "Ibuprofen 200mg", "dose": "400 mg", "route": "oral",
                  "frequency": "three times daily", "duration_days": 5},
        billing={"payer_type": "self_pay", "services": ["CONS", "CXR", "RX"]},
    ),
    dict(
        key="febrile_child_malaria_severe",
        sex="female", age_years=4, category="emergency",
        type="emergency",
        complaint="High fever, lethargy and one episode of convulsion",
        diagnosis="Severe malaria with febrile convulsion",
        icd_code="1F41", icd_display="Severe malaria",
        plan="Admit paediatric ward, IV antimalarial per protocol, monitor for further seizures",
        vitals=dict(temperature_c=Decimal("40.1"), blood_pressure_systolic=88,
                    blood_pressure_diastolic=52, pulse_rate=140, respiratory_rate=34,
                    oxygen_saturation=93, weight_kg=Decimal("16.0"), height_cm=Decimal("100.0"),
                    pain_score=3, glasgow_coma_scale=13),
        labs=[{"test_name": "Malaria RDT", "value_text": "Positive"},
              {"test_name": "Full Blood Count", "value_numeric": Decimal("8.2")}],
        billing={"payer_type": "self_pay", "services": ["CONS", "MRDT", "FBC", "BED"]},
        admit=True, admit_ward="Paediatric Ward", admit_diagnosis="Severe malaria - IV treatment and monitoring",
    ),
    dict(
        key="postop_wound_review",
        sex="male", age_years=45, category="referred",
        type="follow_up",
        complaint="Wound review after appendectomy 1 week ago, mild discomfort",
        diagnosis="Post-appendectomy wound, healing well",
        icd_code="QA21", icd_display="Follow-up examination after surgery",
        plan="Wound clean and dry, remove sutures, continue mild analgesia",
        vitals=dict(temperature_c=Decimal("36.9"), blood_pressure_systolic=120,
                    blood_pressure_diastolic=78, pulse_rate=76, respiratory_rate=16,
                    oxygen_saturation=99, weight_kg=Decimal("71.0"), height_cm=Decimal("174.0"),
                    pain_score=2),
        pharmacy={"drug_name": "Paracetamol 500mg", "dose": "1 g", "route": "oral",
                  "frequency": "three times daily", "duration_days": 3},
        billing={"payer_type": "self_pay", "services": ["CONS", "RX"]},
    ),
    dict(
        key="student_general_checkup",
        sex="female", age_years=20, category="student",
        type="outpatient",
        complaint="General malaise and low-grade fever before exams",
        diagnosis="Viral upper respiratory tract infection",
        icd_code="CA07", icd_display="Acute upper respiratory infection",
        plan="Supportive care, rest and fluids, paracetamol for fever, review if worsening",
        vitals=dict(temperature_c=Decimal("37.8"), blood_pressure_systolic=112,
                    blood_pressure_diastolic=72, pulse_rate=88, respiratory_rate=18,
                    oxygen_saturation=98, weight_kg=Decimal("56.0"), height_cm=Decimal("161.0"),
                    pain_score=1),
        pharmacy={"drug_name": "Paracetamol 500mg", "dose": "1 g", "route": "oral",
                  "frequency": "three times daily as needed", "duration_days": 3},
        billing={"payer_type": "self_pay", "services": ["CONS", "RX"]},
    ),
]


def _drift(value, seq: int, step):
    """Small deterministic variation so the 2nd patient in a scenario isn't identical."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value + Decimal(step) * (seq % 3)
    return value + step * (seq % 3)


def build_patients() -> list[dict]:
    """Build 30 patient dicts: each of the 15 SCENARIOS used twice, with
    light demographic and vital-sign drift between the two instances."""
    today = date.today()
    patients = []
    seq = 0
    for scenario in SCENARIOS:
        for rep in range(2):
            dob_year = today.year - scenario["age_years"] - rep  # 2nd instance is ~1yr older
            dob = date(dob_year, ((seq * 7) % 12) + 1, ((seq * 11) % 28) + 1)
            demo = _demographics(seq, scenario["sex"], dob, scenario.get("category", "outpatient"))

            vitals = dict(scenario["vitals"])
            vitals["temperature_c"] = _drift(vitals.get("temperature_c"), seq, "0.1")
            if vitals.get("pulse_rate") is not None:
                vitals["pulse_rate"] = _drift(vitals["pulse_rate"], seq, 1)

            data = {
                **demo,
                "encounters": [{
                    "type": scenario["type"],
                    "complaint": scenario["complaint"],
                    "diagnosis": scenario["diagnosis"],
                    "icd_code": scenario.get("icd_code", ""),
                    "icd_display": scenario.get("icd_display", ""),
                    "plan": scenario["plan"],
                    "vitals": vitals,
                    "labs": scenario.get("labs", []),
                    "imaging": scenario.get("imaging"),
                    "pharmacy": scenario.get("pharmacy"),
                    "allergies": scenario.get("allergies", []),
                }],
                "billing": scenario.get("billing"),
                "admit": scenario.get("admit", False),
                "admit_ward": scenario.get("admit_ward"),
                "admit_diagnosis": scenario.get("admit_diagnosis"),
                "scenario_key": scenario["key"],
            }
            patients.append(data)
            seq += 1
    return patients


class Command(BaseCommand):
    help = "Seed 10 staff per role (80 users) and 30 patients across 15 clinical scenarios"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo data before seeding")

    def _flush(self):
        self.stdout.write("Flushing existing demo data...")
        tables = [
            "billing_payment", "billing_invoicelineitem", "billing_invoice",
            "pharmacy_dispensingrecord", "pharmacy_prescription",
            "imaging_imagingreport", "imaging_imagingrequest",
            "laboratory_labresult", "laboratory_laborder",
            "vitals_earlywarningscore", "vitals_vitalsignset",
            "reporting_alertevent",
            "encounters_encounteraddendum", "encounters_allergyrecord", "encounters_encounter",
            "emergency_triageencounter", "emergency_historicaltriageencounter",
            "dialysis_dialysissession", "dialysis_dialysisprescription", "dialysis_ckddiagnosis",
            "dialysis_historicaldialysissession", "dialysis_historicaldialysisprescription",
            "dialysis_historicalckddiagnosis",
            "inpatient_wardroundnote", "inpatient_admission", "inpatient_bed", "inpatient_ward",
            "inpatient_historicalwardroundnote", "inpatient_historicaladmission",
            "patients_nextofkin", "patients_duplicateconfirmation", "patients_patient",
            "patients_patientnumbersequence",
            "accounts_profile",
        ]
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
        self.stdout.write(self.style.SUCCESS("  Done."))

    def _seed_patient(self, data, users_by_role, idx):
        nurse = users_by_role["NURSE"][idx % 10]
        clinician = users_by_role["CLINICIAN"][idx % 10]
        billing_officer = users_by_role["BILLING_OFFICER"][idx % 10]

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
                "patient_category": data["patient_category"],
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
                    patient=patient, allergen=allergy["allergen"],
                    defaults={"reaction": allergy["reaction"], "severity": allergy["severity"], "recorded_by": clinician},
                )

            if vitals_data := enc_data.get("vitals"):
                record_vitals(encounter=encounter, recorded_by=nurse, data=vitals_data)

            if labs := enc_data.get("labs"):
                lab_tech = users_by_role["LAB_TECH"][idx % 10]
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
                radiographer = users_by_role["RADIOGRAPHER"][idx % 10]
                try:
                    modality = ImagingModality.objects.get(name=imaging["modality_name"])
                except ImagingModality.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Modality '{imaging['modality_name']}' not found, skipping"))
                    continue
                im_req = create_request(
                    patient=patient, modality=modality, requested_by=clinician,
                    clinical_indication=imaging["indication"], encounter=encounter,
                    pregnancy_status_checked=True,
                )
                enter_report(
                    request=im_req,
                    data={"findings": imaging["findings"], "impression": imaging["impression"],
                          "is_critical_finding": imaging["critical"]},
                    reported_by=radiographer,
                )

            if pharmacy := enc_data.get("pharmacy"):
                pharmacist = users_by_role["PHARMACIST"][idx % 10]
                try:
                    drug = Drug.objects.get(name=pharmacy["drug_name"])
                except Drug.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Drug '{pharmacy['drug_name']}' not found, skipping"))
                    continue
                presc_data = {
                    "dose": pharmacy["dose"], "route": pharmacy["route"],
                    "frequency": pharmacy["frequency"], "duration_days": pharmacy["duration_days"],
                    "encounter": encounter,
                }
                try:
                    presc, warnings = prescribe(patient=patient, drug=drug, prescribed_by=clinician, data=presc_data)
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
                        patient=patient, drug=drug, prescribed_by=clinician,
                        data={"dose": fallback["dose"], "route": fallback["route"],
                              "frequency": fallback["frequency"], "duration_days": fallback["duration_days"],
                              "encounter": encounter},
                    )
                    self.stdout.write(self.style.SUCCESS(f"  Prescribed {drug.generic_name} instead (allergy-safe alternative)"))
                approved_presc = approve(prescription=presc, approved_by=pharmacist)
                dispense(prescription=approved_presc, dispensed_by=pharmacist,
                          data={"quantity_dispensed": f"{presc.duration_days * 2} tablets"})

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

        if data.get("admit") and data.get("admit_ward"):
            ward = Ward.objects.filter(name=data["admit_ward"]).first()
            bed = Bed.objects.filter(ward=ward, is_occupied=False).first() if ward else None
            if ward and bed:
                admit_patient(patient, clinician, data.get("admit_diagnosis", "Admitted for observation"), bed=bed)
                self.stdout.write(self.style.SUCCESS(f"    -> Admitted to {ward.name} ({bed.label})"))

        return patient

    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        self.stdout.write(self.style.NOTICE("Seeding roles and patient scenarios..."))

        self.stdout.write("Creating 10 staff users per role (80 total)...")
        users_by_role = create_users()
        total_users = sum(len(v) for v in users_by_role.values())
        self.stdout.write(self.style.SUCCESS(f"  Created/updated {total_users} users across {len(users_by_role)} roles"))

        self.stdout.write("Creating wards and beds...")
        create_wards_and_beds()
        self.stdout.write(self.style.SUCCESS("  Wards and beds ready"))

        self.stdout.write("Building 30 patients across 15 clinical scenarios...")
        patients_data = build_patients()

        self.stdout.write("Creating patients and clinical data...")
        for i, pdata in enumerate(patients_data, 1):
            patient = self._seed_patient(pdata, users_by_role, i - 1)
            name = f"{patient.first_name} {patient.last_name}"
            self.stdout.write(self.style.SUCCESS(
                f"  [{i:02d}] {name} ({patient.patient_number}) - {pdata['scenario_key']}"
            ))

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully!"))
        self.stdout.write(f"Users: 10 per role x 8 roles = {total_users}")
        self.stdout.write("  Usernames: nurse1-10, clinician1-10, pharmacist1-10, labtech1-10,")
        self.stdout.write("             radiog1-10, billing1-10, admin1-10, ict1-10")
        self.stdout.write("  All passwords: test123")
        self.stdout.write(f"Patients: {len(patients_data)} across {len(SCENARIOS)} clinical scenarios")
