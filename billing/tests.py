import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse

from accounts.models import Profile, Role
from patients.models import Patient

from .models import Invoice, Payment, ServiceCatalogItem
from . import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def billing_officer():
    Group.objects.get_or_create(name="BillingOfficer")
    u = User.objects.create_user("bill1", password="TestPass123!")
    Profile.objects.create(user=u, role=Role.BILLING_OFFICER)
    u.groups.add(Group.objects.get(name="BillingOfficer"))
    return u


@pytest.fixture
def patient(billing_officer):
    return Patient.objects.create(
        first_name="Grace", last_name="Banda", sex="female", registered_by=billing_officer,
    )


@pytest.fixture
def service_item():
    item, _ = ServiceCatalogItem.objects.get_or_create(code="CONS", defaults={"name": "Consultation", "price_mwk": 5000})
    return item


# --- services: happy path ---


def test_create_invoice(patient, billing_officer):
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    assert inv.pk is not None
    assert inv.status == Invoice.Status.DRAFT


def test_add_line_item(patient, billing_officer, service_item):
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    line = services.add_line_item(invoice=inv, service_item=service_item, quantity=2)
    assert line.amount_mwk == 10000  # 5000 * 2
    assert line.invoice == inv


def test_record_payment_marks_paid(patient, billing_officer, service_item):
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    services.add_line_item(invoice=inv, service_item=service_item, quantity=1)
    services.record_payment(invoice=inv, amount_mwk=5000, method="cash", received_by=billing_officer)
    inv.refresh_from_db()
    assert inv.status == Invoice.Status.PAID


def test_record_payment_marks_partial(patient, billing_officer, service_item):
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    services.add_line_item(invoice=inv, service_item=service_item, quantity=1)
    services.record_payment(invoice=inv, amount_mwk=2000, method="cash", received_by=billing_officer)
    inv.refresh_from_db()
    assert inv.status == Invoice.Status.PARTIALLY_PAID


def test_outstanding_balance(patient, billing_officer, service_item):
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    services.add_line_item(invoice=inv, service_item=service_item, quantity=1)
    assert services.outstanding_balance(inv) == 5000
    services.record_payment(invoice=inv, amount_mwk=3000, method="cash", received_by=billing_officer)
    assert services.outstanding_balance(inv) == 2000


def test_unpaid_invoices_for(patient, billing_officer, service_item):
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    services.add_line_item(invoice=inv, service_item=service_item, quantity=1)
    unpaid = services.unpaid_invoices_for(patient)
    assert inv in unpaid


# --- views ---


def test_requires_login(client, patient):
    url = reverse("billing:patient_invoices", args=[patient.pk])
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url


def test_invoice_detail_shows_balance(client, patient, billing_officer, service_item):
    client.force_login(billing_officer)
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    services.add_line_item(invoice=inv, service_item=service_item, quantity=1)
    url = reverse("billing:invoice_detail", args=[inv.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert "5000" in response.content.decode()


def test_payment_recording_updates_status(client, patient, billing_officer, service_item):
    client.force_login(billing_officer)
    inv = services.create_invoice(patient=patient, created_by=billing_officer)
    services.add_line_item(invoice=inv, service_item=service_item, quantity=1)
    url = reverse("billing:invoice_detail", args=[inv.pk])
    response = client.post(url, {"amount_mwk": 5000, "method": "cash", "reference": ""})
    assert response.status_code == 302
    inv.refresh_from_db()
    assert inv.status == Invoice.Status.PAID
