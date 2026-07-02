"""
Field-level encryption at rest for PHI/PII (National ID, phone numbers) per
AGENTS.md §2/§7 and brief §9.4.

NOTE for the team: AGENTS.md allowlists `django-cryptography` for this, but
that package is unmaintained and hard-incompatible with Django >=5.0 (it
imports `django.utils.baseconv`, removed in Django 5.0). Rather than add a
different new dependency, this uses `cryptography.fernet` directly — it's
already a transitive dependency pulled in by django-axes, so this adds
nothing new to the dependency tree. If the team prefers a different fix
(e.g. pinning Django <5.0, or a different package), update
ALLOWED_PACKAGES.md accordingly; flagging this here rather than deciding
unilaterally is exactly what AGENTS.md §5 asks for.

IMPORTANT — Fernet is non-deterministic (same plaintext encrypts to
different ciphertext each time). That's correct for security, but it means
`Patient.objects.filter(national_id="...")` against the encrypted column
will never match anything. Any field that needs exact-match lookup (e.g.
duplicate detection on national_id/phone_number) must ALSO store a
deterministic HMAC "blind index" via `hash_lookup_value()` in a companion
indexed column, and queries must filter on that hash column instead of the
encrypted column. See patients/models.py Patient.save() for the pattern.
"""
import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    key = getattr(settings, "CRYPTOGRAPHY_KEY", None) or settings.SECRET_KEY
    # Fernet needs a 32-byte urlsafe-base64 key; derive one deterministically
    # from whatever key string is configured so ops only manages one secret.
    derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
    return Fernet(derived)


def hash_lookup_value(value: str) -> str:
    """Deterministic blind index for exact-match queries on an encrypted
    field. Not reversible — safe to index in the DB alongside the ciphertext.
    """
    key = getattr(settings, "CRYPTOGRAPHY_KEY", None) or settings.SECRET_KEY
    return hmac.new(key.encode(), str(value).encode(), hashlib.sha256).hexdigest()


class EncryptedCharField(models.CharField):
    """Transparently encrypts/decrypts a CharField's value at rest."""

    def __init__(self, *args, **kwargs):
        # Stored ciphertext is longer than plaintext; widen max_length generously.
        kwargs["max_length"] = max(kwargs.get("max_length", 0), 1024)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return _get_fernet().encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Value predates encryption or key rotated — surface raw value
            # rather than crash; ops should re-encrypt via a data migration.
            return value

    def to_python(self, value):
        return value
