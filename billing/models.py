from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

import simple_history.models


class ServiceCatalogItem(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    price_mwk = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — MWK {self.price_mwk}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PAID = "paid", "Paid"
        WAIVED = "waived", "Waived"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"

    class PayerType(models.TextChoices):
        SELF_PAY = "self_pay", "Self Pay"
        INSURANCE = "insurance", "Insurance"
        INSTITUTIONAL = "institutional", "Institutional"
        WAIVER = "waiver", "Waiver"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="invoices")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    payer_type = models.CharField(max_length=20, choices=PayerType.choices, default=PayerType.SELF_PAY)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = simple_history.models.HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice #{self.pk} — {self.patient.full_name} ({self.status})"


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    service_item = models.ForeignKey(ServiceCatalogItem, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)
    amount_mwk = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.service_item.name} x{self.quantity} — MWK {self.amount_mwk}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        BANK = "bank", "Bank"
        INSURANCE = "insurance", "Insurance"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount_mwk = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    method = models.CharField(max_length=20, choices=Method.choices)
    reference = models.CharField(max_length=255, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_mwk__gt=0),
                name="payment_amount_mwk_positive",
            )
        ]

    def __str__(self):
        return f"{self.method} MWK {self.amount_mwk} on Invoice #{self.invoice.pk}"
