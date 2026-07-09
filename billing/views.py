from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from collections import OrderedDict

from accounts.permissions import role_required
from patients.models import Patient

from .forms import InvoiceForm, LineItemFormSet, PaymentForm
from .models import Invoice, Payment, ServiceCatalogItem
from .services import add_line_item, create_invoice, outstanding_balance, record_payment, unpaid_invoices_for


@role_required("BillingOfficer", "Admin")
def dashboard(request):
    recent = Invoice.objects.select_related("patient").order_by("-created_at")[:20]
    counts = Invoice.objects.aggregate(
        total=Count("pk"),
        unpaid=Count("pk", filter=Q(status__in=["draft", "issued", "partially_paid"])),
        paid=Count("pk", filter=Q(status="paid")),
    )
    invoice_daily = list(
        Invoice.objects.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("pk"))
        .order_by("-day")[:7]
    )
    payment_daily = list(
        Payment.objects.annotate(day=TruncDate("received_at"))
        .values("day")
        .annotate(total=Sum("amount_mwk"))
        .order_by("-day")[:7]
    )
    day_map = OrderedDict()
    for row in reversed(invoice_daily):
        if row["day"]:
            day_map[row["day"]] = {"invoice_count": row["total"], "payment_total": 0}
    for row in reversed(payment_daily):
        if row["day"]:
            day_map.setdefault(row["day"], {"invoice_count": 0, "payment_total": 0})
            day_map[row["day"]]["payment_total"] = float(row["total"] or 0)
    labels = [day.strftime("%d %b") for day in day_map.keys()]
    outstanding = 0
    for invoice in Invoice.objects.prefetch_related("line_items", "payments").filter(status__in=["draft", "issued", "partially_paid"]):
        outstanding += outstanding_balance(invoice)
    return render(
        request,
        "billing/dashboard.html",
        {
            "recent": recent,
            "counts": counts,
            "outstanding": outstanding,
            "trend": {
                "labels": labels,
                "invoice_counts": [series["invoice_count"] for series in day_map.values()],
                "payment_totals": [series["payment_total"] for series in day_map.values()],
            },
        },
    )


@login_required
def patient_invoices(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    invoices = Invoice.objects.filter(patient=patient).prefetch_related("line_items", "payments").order_by("-created_at")
    for inv in invoices:
        inv.balance = outstanding_balance(inv)
    return render(request, "billing/patient_invoices.html", {"patient": patient, "invoices": invoices})


@login_required
def patient_tab(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    invoices = Invoice.objects.filter(patient=patient).prefetch_related("line_items", "payments").order_by("-created_at")
    for inv in invoices:
        inv.balance = outstanding_balance(inv)
    return render(request, "billing/_patient_tab.html", {"patient": patient, "invoices": invoices})


@role_required("BillingOfficer", "Admin")
def create_invoice_view(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        formset = LineItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = create_invoice(patient=patient, created_by=request.user, payer_type=form.cleaned_data["payer_type"])
            for line_form in formset:
                if line_form.cleaned_data.get("service_item"):
                    add_line_item(invoice=invoice, service_item=line_form.cleaned_data["service_item"], quantity=line_form.cleaned_data["quantity"])
            return redirect("billing:patient_invoices", patient_id=patient.pk)
    else:
        form = InvoiceForm()
        formset = LineItemFormSet()
    return render(request, "billing/create_invoice.html", {"patient": patient, "form": form, "formset": formset})


@role_required("BillingOfficer", "Admin")
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice.objects.prefetch_related("line_items__service_item", "payments"), pk=invoice_id)
    balance = outstanding_balance(invoice)
    total_billed = sum(item.amount_mwk for item in invoice.line_items.all())
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            record_payment(
                invoice=invoice,
                amount_mwk=form.cleaned_data["amount_mwk"],
                method=form.cleaned_data["method"],
                reference=form.cleaned_data.get("reference", ""),
                received_by=request.user,
            )
            return redirect("billing:invoice_detail", invoice_id=invoice.pk)
    else:
        form = PaymentForm()
    return render(request, "billing/invoice_detail.html", {"invoice": invoice, "balance": balance, "total_billed": total_billed, "form": form})


@login_required
def invoice_print(request, invoice_id):
    """§8.1.14(c): Printable invoice/receipt. Minimal layout for browser print."""
    invoice = get_object_or_404(Invoice.objects.prefetch_related("line_items__service_item", "payments", "patient"), pk=invoice_id)
    balance = outstanding_balance(invoice)
    total_billed = sum(item.amount_mwk for item in invoice.line_items.all())
    return render(request, "billing/invoice_print.html", {"invoice": invoice, "balance": balance, "total_billed": total_billed})
