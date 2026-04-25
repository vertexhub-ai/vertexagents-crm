from django import forms
from .models import Activity


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["kind", "subject", "body", "due_at"]
        widgets = {
            "kind": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "subject": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "placeholder": "Subject"}
            ),
            "body": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 3, "placeholder": "Notes (optional)"}
            ),
            "due_at": forms.DateTimeInput(
                attrs={"class": "form-control form-control-sm", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"].required = False
        self.fields["due_at"].required = False
