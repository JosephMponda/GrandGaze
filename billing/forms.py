from django import forms

from .models import Invoice, InvoiceLineItem, Payment, ServiceCatalogItem


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["payer_type"]


class LineItemForm(forms.Form):
    service_item = forms.ModelChoiceField(queryset=ServiceCatalogItem.objects.all(), label="Service")
    quantity = forms.IntegerField(min_value=1, initial=1)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount_mwk", "method", "reference"]
        widgets = {"amount_mwk": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"})}


LineItemFormSet = forms.formset_factory(LineItemForm, extra=1, can_delete=False)


# ── Offline sync forms ──────────────────────────────────────────────────


class OfflineInvoiceCreateForm(forms.Form):
    patient_id = forms.IntegerField()
    payer_type = forms.ChoiceField(choices=Invoice.PayerType.choices)
    line_items = forms.CharField(max_length=5000, help_text='JSON: [{"service_item_id": 1, "quantity": 1}]')


class OfflinePaymentForm(forms.Form):
    invoice_id = forms.IntegerField()
    amount_mwk = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    method = forms.ChoiceField(choices=Payment.Method.choices)
    reference = forms.CharField(required=False, max_length=255)
