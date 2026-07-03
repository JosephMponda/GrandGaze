from django.contrib import admin

from .models import Invoice, InvoiceLineItem, Payment, ServiceCatalogItem


@admin.register(ServiceCatalogItem)
class ServiceCatalogItemAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_mwk")
    search_fields = ("name", "code")


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem


class PaymentInline(admin.TabularInline):
    model = Payment
    readonly_fields = ("received_at",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("pk", "patient", "status", "payer_type", "created_at")
    list_filter = ("status", "payer_type")
    search_fields = ("patient__first_name", "patient__last_name", "patient__patient_number")
    inlines = [InvoiceLineItemInline, PaymentInline]
    readonly_fields = ("created_at", "updated_at")
