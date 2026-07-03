from django.contrib import admin

from .models import DispensingRecord, Drug, DrugAllergyMap, Prescription


admin.site.register(Drug)
admin.site.register(DrugAllergyMap)
admin.site.register(Prescription)
admin.site.register(DispensingRecord)

