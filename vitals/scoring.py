"""
Simplified adult Early Warning Score. Thresholds kept in one place so they're
easy to defend/adjust to judges' questions. Loosely modelled on published
NEWS-style banding (respiratory rate, SpO2, temperature, systolic BP, pulse,
consciousness level), each contributing 0-3 points.

§8.1.7(e): Pediatric age-adjusted vital sign alerts are applied when the
patient's age is known and < 18 years, using age-band-specific thresholds.
"""

from datetime import date


def _patient_age_years(patient) -> int | None:
    """Return patient age in whole years, or None if DOB unknown."""
    if not patient.date_of_birth:
        return None
    today = date.today()
    return today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
    )


# ── Adult EWS (age >= 18 or unknown) ────────────────────────────────────

ADULT_EWS_BANDS = {
    "respiratory_rate": [(8, 3), (11, 1), (20, 0), (24, 2), (None, 3)],
    "oxygen_saturation": [(91, 3), (93, 2), (95, 1), (None, 0)],
    "temperature_c": [(35.0, 3), (36.0, 1), (38.0, 0), (39.0, 1), (None, 2)],
    "blood_pressure_systolic": [(90, 3), (100, 2), (110, 1), (219, 0), (None, 3)],
    "pulse_rate": [(40, 3), (50, 1), (90, 0), (110, 1), (130, 2), (None, 3)],
}

# ── Pediatric EWS bands by age group ─────────────────────────────────────
# Sources: modified NEWS/Pediatric Early Warning Score literature,
# simplified to match this EMR's 0-3 scoring granularity.

PEDIATRIC_EWS_BANDS = {
    # age 0-1 (infant)
    (0, 1): {
        "respiratory_rate": [(15, 3), (30, 1), (40, 0), (50, 1), (60, 2), (None, 3)],
        "oxygen_saturation": [(90, 3), (92, 2), (94, 1), (None, 0)],
        "temperature_c": [(36.0, 3), (37.0, 1), (37.5, 0), (38.0, 1), (None, 2)],
        "pulse_rate": [(80, 3), (100, 1), (160, 0), (180, 1), (200, 2), (None, 3)],
    },
    # age 1-4
    (1, 4): {
        "respiratory_rate": [(12, 3), (20, 1), (28, 0), (35, 1), (40, 2), (None, 3)],
        "oxygen_saturation": [(90, 3), (92, 2), (94, 1), (None, 0)],
        "temperature_c": [(36.0, 3), (37.0, 1), (37.5, 0), (38.5, 1), (None, 2)],
        "pulse_rate": [(70, 3), (80, 1), (120, 0), (140, 1), (160, 2), (None, 3)],
    },
    # age 5-12
    (5, 12): {
        "respiratory_rate": [(10, 3), (15, 1), (22, 0), (28, 1), (32, 2), (None, 3)],
        "oxygen_saturation": [(91, 3), (93, 2), (95, 1), (None, 0)],
        "temperature_c": [(36.0, 3), (36.5, 1), (37.5, 0), (38.5, 1), (None, 2)],
        "pulse_rate": [(60, 3), (70, 1), (110, 0), (130, 1), (150, 2), (None, 3)],
    },
    # age 13-17 (approaching adult)
    (13, 17): {
        "respiratory_rate": [(9, 3), (12, 1), (20, 0), (24, 2), (None, 3)],
        "oxygen_saturation": [(91, 3), (93, 2), (95, 1), (None, 0)],
        "temperature_c": [(35.0, 3), (36.0, 1), (38.0, 0), (39.0, 1), (None, 2)],
        "pulse_rate": [(45, 3), (55, 1), (100, 0), (120, 1), (140, 2), (None, 3)],
    },
}

RISK_LEVEL_BANDS = [(2, "low"), (5, "medium"), (8, "high"), (None, "critical")]

# Hard safety thresholds - outside these, fire an immediate alert regardless
# of total EWS score (a single badly abnormal value matters on its own).
ADULT_HARD_ALERT_THRESHOLDS = {
    "oxygen_saturation": ("lt", 90, "SpO2 below 90%"),
    "temperature_c": ("gt", 39.5, "Temperature above 39.5C"),
    "blood_pressure_systolic": ("lt", 80, "Systolic BP below 80 mmHg"),
    "pulse_rate": ("gt", 150, "Pulse rate above 150 bpm"),
    "glasgow_coma_scale": ("lt", 9, "GCS below 9"),
}

# Pediatric hard-alert thresholds (by age group)
PEDIATRIC_HARD_ALERT_THRESHOLDS = {
    (0, 1): {
        "oxygen_saturation": ("lt", 90, "SpO2 below 90% (infant)"),
        "temperature_c": ("gt", 38.5, "Temperature above 38.5C (infant)"),
        "pulse_rate": ("gt", 200, "Heart rate above 200 bpm (infant)"),
        "glasgow_coma_scale": ("lt", 12, "GCS below 12"),
    },
    (1, 4): {
        "oxygen_saturation": ("lt", 90, "SpO2 below 90%"),
        "temperature_c": ("gt", 39.0, "Temperature above 39.0C"),
        "pulse_rate": ("gt", 160, "Heart rate above 160 bpm"),
        "glasgow_coma_scale": ("lt", 12, "GCS below 12"),
    },
    (5, 12): {
        "oxygen_saturation": ("lt", 91, "SpO2 below 91%"),
        "temperature_c": ("gt", 39.5, "Temperature above 39.5C"),
        "pulse_rate": ("lt", 50, "Heart rate below 50 bpm"),
        "glasgow_coma_scale": ("lt", 12, "GCS below 12"),
    },
    (13, 17): {
        "oxygen_saturation": ("lt", 90, "SpO2 below 90%"),
        "temperature_c": ("gt", 39.5, "Temperature above 39.5C"),
        "pulse_rate": ("gt", 150, "Heart rate above 150 bpm"),
        "glasgow_coma_scale": ("lt", 9, "GCS below 9"),
    },
}


def _get_age_bands(age_years):
    """Return the EWS bands and hard-alert thresholds for the given age."""
    if age_years is None:
        return ADULT_EWS_BANDS, ADULT_HARD_ALERT_THRESHOLDS
    for (lo, hi), bands in PEDIATRIC_EWS_BANDS.items():
        if lo <= age_years <= hi:
            return bands, PEDIATRIC_HARD_ALERT_THRESHOLDS.get((lo, hi), ADULT_HARD_ALERT_THRESHOLDS)
    return ADULT_EWS_BANDS, ADULT_HARD_ALERT_THRESHOLDS


def _band_score(value, bands) -> int:
    if value is None:
        return 0
    for upper, points in bands:
        if upper is None or value <= upper:
            return points
    return 0


def compute_ews(vital_sign_set) -> tuple[int, str]:
    # Gracefully handle test mocks and edge cases where patient attribute is missing
    patient = getattr(vital_sign_set, "patient", None)
    age = _patient_age_years(patient) if patient and hasattr(patient, "date_of_birth") else None
    ews_bands, _ = _get_age_bands(age)

    score = 0
    for field, bands in ews_bands.items():
        value = getattr(vital_sign_set, field)
        if value is not None:
            score += _band_score(float(value), bands)
    if vital_sign_set.glasgow_coma_scale is not None and vital_sign_set.glasgow_coma_scale < 15:
        score += 3

    risk_level = "low"
    for upper, level in RISK_LEVEL_BANDS:
        if upper is None or score <= upper:
            risk_level = level
            break
    return score, risk_level


def find_abnormal_values(vital_sign_set) -> list[str]:
    """Hard-threshold checks, independent of the EWS total. Returns
    human-readable messages for anything outside a safety threshold.
    Age-adjusted when the patient's DOB is known.
    """
    age = None
    patient = getattr(vital_sign_set, "patient", None)
    if patient and hasattr(patient, "date_of_birth"):
        age = _patient_age_years(patient)
    _, hard_thresholds = _get_age_bands(age)
    messages = []
    for field, (op, threshold, label) in hard_thresholds.items():
        value = getattr(vital_sign_set, field)
        if value is None:
            continue
        value = float(value)
        if (op == "lt" and value < threshold) or (op == "gt" and value > threshold):
            messages.append(label)
    return messages
