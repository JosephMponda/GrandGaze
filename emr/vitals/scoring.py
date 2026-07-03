"""
Simplified adult Early Warning Score. Thresholds kept in one place so they're
easy to defend/adjust to judges' questions. Loosely modelled on published
NEWS-style banding (respiratory rate, SpO2, temperature, systolic BP, pulse,
consciousness level), each contributing 0-3 points.

# TODO: pediatric-adjusted variant, Phase 2 (brief §8.1.7 "pediatric
# age-adjusted vital sign alerts" is explicitly future scope — this is
# adult-only, don't claim otherwise).
"""

EWS_BANDS = {
    "respiratory_rate": [(8, 3), (11, 1), (20, 0), (24, 2), (None, 3)],
    "oxygen_saturation": [(91, 3), (93, 2), (95, 1), (None, 0)],
    "temperature_c": [(35.0, 3), (36.0, 1), (38.0, 0), (39.0, 1), (None, 2)],
    "blood_pressure_systolic": [(90, 3), (100, 2), (110, 1), (219, 0), (None, 3)],
    "pulse_rate": [(40, 3), (50, 1), (90, 0), (110, 1), (130, 2), (None, 3)],
}

RISK_LEVEL_BANDS = [(2, "low"), (5, "medium"), (8, "high"), (None, "critical")]

# Hard safety thresholds — outside these, fire an immediate alert regardless
# of total EWS score (a single badly abnormal value matters on its own).
HARD_ALERT_THRESHOLDS = {
    "oxygen_saturation": ("lt", 90, "SpO2 below 90%"),
    "temperature_c": ("gt", 39.5, "Temperature above 39.5°C"),
    "blood_pressure_systolic": ("lt", 80, "Systolic BP below 80 mmHg"),
    "pulse_rate": ("gt", 150, "Pulse rate above 150 bpm"),
    "glasgow_coma_scale": ("lt", 9, "GCS below 9"),
}


def _band_score(value, bands) -> int:
    if value is None:
        return 0
    for upper, points in bands:
        if upper is None or value <= upper:
            return points
    return 0


def compute_ews(vital_sign_set) -> tuple[int, str]:
    score = 0
    for field, bands in EWS_BANDS.items():
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
    """
    messages = []
    for field, (op, threshold, label) in HARD_ALERT_THRESHOLDS.items():
        value = getattr(vital_sign_set, field)
        if value is None:
            continue
        value = float(value)
        if (op == "lt" and value < threshold) or (op == "gt" and value > threshold):
            messages.append(label)
    return messages
