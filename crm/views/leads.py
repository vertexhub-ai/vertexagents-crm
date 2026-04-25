from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from crm.models import Lead, KIND_CHOICES
from crm.forms import ActivityForm
from crm.views.activity import _timeline_qs
from django.urls import reverse


@login_required
def lead_list(request):
    leads = Lead.objects.filter(deleted_at__isnull=True).order_by("-created_at")
    return render(request, "crm/lead_list.html", {"leads": leads})


@login_required
def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk, deleted_at__isnull=True)
    pending, regular = _timeline_qs("lead", lead.pk)
    create_url = reverse("lead_activity_create", kwargs={"pk": lead.pk})
    return render(
        request,
        "crm/lead_detail.html",
        {
            "obj": lead,
            "parent_obj": lead,
            "parent_type": "lead",
            "create_activity_url": create_url,
            "pending_tasks": pending,
            "timeline_activities": regular,
            "form": ActivityForm(),
            "kind_choices": KIND_CHOICES,
        },
    )
