from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from crm.models import Contact, KIND_CHOICES
from crm.forms import ActivityForm
from crm.views.activity import _timeline_qs


@login_required
def contact_list(request):
    contacts = Contact.objects.filter(deleted_at__isnull=True).order_by("-created_at")
    return render(request, "crm/contact_list.html", {"contacts": contacts})


@login_required
def contact_detail(request, pk):
    contact = get_object_or_404(Contact, pk=pk, deleted_at__isnull=True)
    pending, regular = _timeline_qs("contact", contact.pk)
    create_url = reverse("contact_activity_create", kwargs={"pk": contact.pk})
    return render(
        request,
        "crm/contact_detail.html",
        {
            "obj": contact,
            "parent_obj": contact,
            "parent_type": "contact",
            "create_activity_url": create_url,
            "pending_tasks": pending,
            "timeline_activities": regular,
            "form": ActivityForm(),
            "kind_choices": KIND_CHOICES,
        },
    )
