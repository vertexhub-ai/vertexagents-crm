from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from crm.models import Account, KIND_CHOICES
from crm.forms import ActivityForm
from crm.views.activity import _timeline_qs


@login_required
def account_list(request):
    accounts = Account.objects.filter(deleted_at__isnull=True).order_by("-created_at")
    return render(request, "crm/account_list.html", {"accounts": accounts})


@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk, deleted_at__isnull=True)
    pending, regular = _timeline_qs("account", account.pk)
    create_url = reverse("account_activity_create", kwargs={"pk": account.pk})
    return render(
        request,
        "crm/account_detail.html",
        {
            "obj": account,
            "parent_obj": account,
            "parent_type": "account",
            "create_activity_url": create_url,
            "pending_tasks": pending,
            "timeline_activities": regular,
            "form": ActivityForm(),
            "kind_choices": KIND_CHOICES,
        },
    )
