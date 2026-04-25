from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from crm.models import Opportunity, KIND_CHOICES
from crm.forms import ActivityForm
from crm.views.activity import _timeline_qs


@login_required
def opportunity_list(request):
    opportunities = Opportunity.objects.filter(deleted_at__isnull=True).order_by("-created_at")
    return render(request, "crm/opportunity_list.html", {"opportunities": opportunities})


@login_required
def opportunity_detail(request, pk):
    opportunity = get_object_or_404(Opportunity, pk=pk, deleted_at__isnull=True)
    pending, regular = _timeline_qs("opportunity", opportunity.pk)
    create_url = reverse("opportunity_activity_create", kwargs={"pk": opportunity.pk})
    return render(
        request,
        "crm/opportunity_detail.html",
        {
            "obj": opportunity,
            "parent_obj": opportunity,
            "parent_type": "opportunity",
            "create_activity_url": create_url,
            "pending_tasks": pending,
            "timeline_activities": regular,
            "form": ActivityForm(),
            "kind_choices": KIND_CHOICES,
        },
    )
