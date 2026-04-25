from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from crm.forms import ActivityForm
from crm.models import Activity, Lead, Contact, Account, Opportunity, KIND_CHOICES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _timeline_qs(parent_type, parent_pk):
    """Return (pending_tasks_qs, regular_activities_qs) for a parent."""
    filter_kw = {f"{parent_type}_id": parent_pk, "deleted_at__isnull": True}

    pending = (
        Activity.objects.filter(
            **filter_kw,
            kind__in=["task", "meeting"],
            due_at__isnull=False,
            completed_at__isnull=True,
        )
        .select_related("author")
        .order_by("due_at")
    )
    pending_ids = list(pending.values_list("pk", flat=True))

    regular = (
        Activity.objects.filter(**filter_kw)
        .exclude(pk__in=pending_ids)
        .select_related("author")
        .order_by("-created_at")
    )
    return pending, regular


def _render_timeline(request, parent_type, parent_obj, form=None):
    pending, regular = _timeline_qs(parent_type, parent_obj.pk)
    create_url = reverse(f"{parent_type}_activity_create", kwargs={"pk": parent_obj.pk})
    if form is None:
        form = ActivityForm()
    return render(
        request,
        "partials/timeline.html",
        {
            "parent_obj": parent_obj,
            "parent_type": parent_type,
            "create_activity_url": create_url,
            "pending_tasks": pending,
            "timeline_activities": regular,
            "form": form,
            "kind_choices": KIND_CHOICES,
        },
    )


def _get_activity_parent(activity):
    if activity.lead_id:
        return "lead", activity.lead
    if activity.contact_id:
        return "contact", activity.contact
    if activity.account_id:
        return "account", activity.account
    if activity.opportunity_id:
        return "opportunity", activity.opportunity
    return None, None


# ---------------------------------------------------------------------------
# Create views (one per parent type — URL carries parent PK)
# ---------------------------------------------------------------------------

def _create_activity(request, parent_type, parent_pk, ParentModel):
    parent_obj = get_object_or_404(ParentModel, pk=parent_pk, deleted_at__isnull=True)
    if request.method == "POST":
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.author = request.user
            setattr(activity, parent_type, parent_obj)
            activity.save()
            return _render_timeline(request, parent_type, parent_obj)
        return _render_timeline(request, parent_type, parent_obj, form=form)
    return _render_timeline(request, parent_type, parent_obj)


@login_required
def lead_activity_create(request, pk):
    return _create_activity(request, "lead", pk, Lead)


@login_required
def contact_activity_create(request, pk):
    return _create_activity(request, "contact", pk, Contact)


@login_required
def account_activity_create(request, pk):
    return _create_activity(request, "account", pk, Account)


@login_required
def opportunity_activity_create(request, pk):
    return _create_activity(request, "opportunity", pk, Opportunity)


# ---------------------------------------------------------------------------
# Complete a task
# ---------------------------------------------------------------------------

@login_required
@require_POST
def activity_complete(request, pk):
    activity = get_object_or_404(Activity, pk=pk, deleted_at__isnull=True)
    activity.completed_at = timezone.now()
    activity.save(update_fields=["completed_at"])
    parent_type, parent_obj = _get_activity_parent(activity)
    return _render_timeline(request, parent_type, parent_obj)


# ---------------------------------------------------------------------------
# Edit an activity (owner or admin)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def activity_edit(request, pk):
    activity = get_object_or_404(Activity, pk=pk, deleted_at__isnull=True)
    if activity.author != request.user and not request.user.is_staff:
        return HttpResponse(status=403)
    form = ActivityForm(request.POST, instance=activity)
    parent_type, parent_obj = _get_activity_parent(activity)
    if form.is_valid():
        form.save()
        return _render_timeline(request, parent_type, parent_obj)
    return _render_timeline(request, parent_type, parent_obj, form=form)


# ---------------------------------------------------------------------------
# Soft-delete an activity (owner or admin)
# ---------------------------------------------------------------------------

@login_required
def activity_delete(request, pk):
    if request.method not in ("POST", "DELETE"):
        return HttpResponse(status=405)
    activity = get_object_or_404(Activity, pk=pk, deleted_at__isnull=True)
    if activity.author != request.user and not request.user.is_staff:
        return HttpResponse(status=403)
    parent_type, parent_obj = _get_activity_parent(activity)
    activity.soft_delete()
    return _render_timeline(request, parent_type, parent_obj)
