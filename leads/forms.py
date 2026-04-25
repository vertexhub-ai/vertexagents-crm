from django import forms

from .models import Lead, Status

EDITABLE_STATUS_CHOICES = [
    (Status.NEW, Status.NEW.label),
    (Status.CONTACTED, Status.CONTACTED.label),
    (Status.QUALIFIED, Status.QUALIFIED.label),
]


class LeadForm(forms.ModelForm):
    status = forms.ChoiceField(choices=EDITABLE_STATUS_CHOICES)

    class Meta:
        model = Lead
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "company_name",
            "title",
            "source",
            "status",
            "owner",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "company_name": forms.TextInput(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["last_name"].required = True
        # If editing a disqualified lead, allow that status to show (read context)
        instance = kwargs.get("instance")
        if instance and instance.status == Status.DISQUALIFIED:
            self.fields["status"].choices = EDITABLE_STATUS_CHOICES + [
                (Status.DISQUALIFIED, Status.DISQUALIFIED.label)
            ]


class DisqualifyForm(forms.Form):
    disqualified_reason = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-input w-full"}),
        error_messages={"required": "A reason is required to disqualify this lead."},
    )
