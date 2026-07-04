from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import Invoice, InvoiceLineItem, Payment


def create_invoice(*, patient, created_by, payer_type="self_pay") -> Invoice:
    return Invoice.objects.create(patient=patient, created_by=created_by, payer_type=payer_type)


def add_line_item(*, invoice, service_item, quantity=1) -> InvoiceLineItem:
    amount_mwk = service_item.price_mwk * quantity
    return InvoiceLineItem.objects.create(
        invoice=invoice,
        service_item=service_item,
        quantity=quantity,
        amount_mwk=amount_mwk,
    )


def record_payment(*, invoice, amount_mwk, method, received_by, reference="") -> Payment:
    if amount_mwk is None or Decimal(amount_mwk) <= 0:
        raise ValueError("Payment amount must be greater than zero.")
    with transaction.atomic():
        # Lock the invoice row so two concurrent payments can't both read a
        # stale total_paid and leave invoice.status wrong (e.g. stuck on
        # "partially_paid" when the combined payments actually paid it off).
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        payment = Payment.objects.create(
            invoice=invoice,
            amount_mwk=amount_mwk,
            method=method,
            reference=reference,
            received_by=received_by,
        )
        total_paid = Payment.objects.filter(invoice=invoice).aggregate(total=Sum("amount_mwk"))["total"] or 0
        total_billed = InvoiceLineItem.objects.filter(invoice=invoice).aggregate(total=Sum("amount_mwk"))["total"] or 0
        if total_paid >= total_billed:
            invoice.status = Invoice.Status.PAID
        elif total_paid > 0:
            invoice.status = Invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=["status"])
    return payment


def outstanding_balance(invoice) -> int:
    total_billed = InvoiceLineItem.objects.filter(invoice=invoice).aggregate(total=Sum("amount_mwk"))["total"] or 0
    total_paid = Payment.objects.filter(invoice=invoice).aggregate(total=Sum("amount_mwk"))["total"] or 0
    return total_billed - total_paid


def unpaid_invoices_for(patient) -> list[Invoice]:
    return list(
        Invoice.objects.filter(patient=patient)
        .exclude(status__in=[Invoice.Status.PAID, Invoice.Status.WAIVED])
        .order_by("-created_at")
    )
