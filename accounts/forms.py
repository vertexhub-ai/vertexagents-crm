from django import forms
from django.core.exceptions import ValidationError

from .models import Account


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["name", "website", "industry", "size", "owner"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Acme Corp"}),
            "website": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://"}),
            "industry": forms.TextInput(attrs={"class": "form-input", "placeholder": "SaaS, Fintech…"}),
            "size": forms.Select(attrs={"class": "form-select"}),
            "owner": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Name is required.")
        name_lower = name.lower()
        qs = Account.objects.filter(name_lower=name_lower)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("An account with this name already exists (case-insensitive).")
        return name
