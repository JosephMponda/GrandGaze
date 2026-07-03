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


LineItemFormSet = forms.formset_factory(LineItemForm, extra=1, can_delete=False)
