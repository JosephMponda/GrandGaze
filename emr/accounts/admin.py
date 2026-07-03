from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(SimpleHistoryAdmin):
    list_display = ("user", "role", "department", "is_active_staff")
    list_filter = ("role", "is_active_staff")
    search_fields = ("user__username", "user__first_name", "user__last_name")
