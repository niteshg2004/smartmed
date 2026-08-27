from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password_confirm = forms.CharField(widget=forms.PasswordInput, min_length=8, label="Confirm password")

    class Meta:
        model = User
        fields = ["name", "email", "phone", "role"]

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role == User.Role.ADMIN:
            raise forms.ValidationError(
                "Admin/pharmacist accounts cannot be self-registered. Contact a system administrator."
            )
        return role

    def clean(self):
        cleaned = super().clean()
        pw, pw2 = cleaned.get("password"), cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            name=self.cleaned_data["name"],
            phone=self.cleaned_data.get("phone", ""),
            role=self.cleaned_data["role"],
        )
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
