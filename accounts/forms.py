from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Profile, Role

User = get_user_model()

class StaffUserForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Role.choices, required=True, widget=forms.Select(attrs={'class': 'form-input'}))
    department = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    phone_number = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}), required=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password"]

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                role=self.cleaned_data["role"],
                department=self.cleaned_data["department"],
                phone_number=self.cleaned_data["phone_number"]
            )
        return user
