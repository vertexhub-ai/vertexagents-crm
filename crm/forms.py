from django import forms
from .models import Account, Contact


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["name", "website", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "autofocus": True}),
            "website": forms.URLInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
        }


class ContactForm(forms.ModelForm):
    # Rendered as a hidden input; the visible autocomplete widget is in the template.
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Contact
        fields = ["first_name", "last_name", "email", "phone", "title", "account"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-input", "autofocus": True}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        qs = Contact.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A contact with this email already exists.")
        return email
