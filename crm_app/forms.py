from django import forms

from .models import Account


class ContactConversionForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=50, required=False)
    title = forms.CharField(max_length=100, required=False)


ACCOUNT_MODE_CHOICES = [
    ('new', 'Create new account'),
    ('existing', 'Link to existing account'),
    ('skip', 'Skip'),
]


class AccountConversionForm(forms.Form):
    account_mode = forms.ChoiceField(
        choices=ACCOUNT_MODE_CHOICES,
        widget=forms.RadioSelect,
        initial='new',
    )
    existing_account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
        empty_label='— select account —',
    )
    new_account_name = forms.CharField(max_length=255, required=False)

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get('account_mode')
        if mode == 'existing' and not cleaned.get('existing_account'):
            raise forms.ValidationError('Please select an existing account.')
        if mode == 'new' and not cleaned.get('new_account_name', '').strip():
            raise forms.ValidationError('Please enter the new account name.')
        return cleaned


class OpportunityConversionForm(forms.Form):
    create_opportunity = forms.BooleanField(required=False, initial=True)
    opportunity_name = forms.CharField(max_length=255, required=False)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, required=False)
    expected_close_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('create_opportunity') and not cleaned.get('opportunity_name', '').strip():
            raise forms.ValidationError('Opportunity name is required.')
        return cleaned
