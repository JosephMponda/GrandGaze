from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from patients.models import Patient

from .forms import InvoiceForm, LineItemFormSet, PaymentForm
from .models import Invoice, ServiceCatalogItem
from .services import add_line_item, create_invoice, outstanding_balance, record_payment, unpaid_invoices_for


@login_required
def patient_invoices(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    invoices = Invoice.objects.filter(patient=patient).prefetch_related("line_items", "payments").order_by("-created_at")
    for inv in invoices:
        inv.balance = outstanding_balance(inv)
    return render(request, "billing/patient_invoices.html", {"patient": patient, "invoices": invoices})


@login_required
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


@login_required
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
