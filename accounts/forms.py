from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from .models import Profile, Role, assign_user_role_group


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"autocomplete": "username"})
        self.fields["password"].widget.attrs.update({"autocomplete": "current-password"})

User = get_user_model()


class StaffProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-input'}))

    class Meta:
        model = Profile
        fields = [
            "photo", "phone_number", "department", "role", "qualifications",
            "bio", "specialty", "employee_id", "date_of_birth", "gender", "emergency_contact",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "qualifications": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "bio": forms.Textarea(attrs={"rows": 4, "class": "form-input"}),
            "role": forms.Select(attrs={"class": "form-input"}),
            "department": forms.TextInput(attrs={"class": "form-input"}),
            "specialty": forms.TextInput(attrs={"class": "form-input"}),
            "employee_id": forms.TextInput(attrs={"class": "form-input"}),
            "gender": forms.Select(attrs={"class": "form-input"}),
            "phone_number": forms.TextInput(attrs={"class": "form-input"}),
            "emergency_contact": forms.TextInput(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            profile.save()
        return profile


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
            role = self.cleaned_data["role"]
            Profile.objects.create(
                user=user,
                role=role,
                department=self.cleaned_data["department"],
                phone_number=self.cleaned_data["phone_number"]
            )
            assign_user_role_group(user, role)
        return user
