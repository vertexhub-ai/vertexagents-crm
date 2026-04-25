from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DisqualifyForm, LeadForm
from .models import Lead, Source, Status


def _can_edit(user, lead):
    """Non-converted leads are always editable. Converted leads require admin/staff."""
    if not lead.is_converted:
        return True
    return user.is_staff or getattr(user, "role", None) == "admin"


@login_required
def lead_list(request):
    qs = Lead.objects.select_related("owner").order_by("-created_at")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(company_name__icontains=q)
            | Q(email__icontains=q)
        )

    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)

    source = request.GET.get("source", "")
    if source:
        qs = qs.filter(source=source)

    owner = request.GET.get("owner", "mine")
    if owner == "mine":
        qs = qs.filter(owner=request.user)
    elif owner != "all":
        qs = qs.filter(owner_id=owner)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "leads/list.html", {
        "page_obj": page,
        "status_choices": Status.choices,
        "source_choices": Source.choices,
        "q": q,
        "selected_status": status,
        "selected_source": source,
        "selected_owner": owner,
    })


@login_required
def lead_detail(request, pk):
    lead = get_object_or_404(Lead.all_objects, pk=pk)
    return render(request, "leads/detail.html", {"lead": lead})


@login_required
def lead_create(request):
    if request.method == "POST":
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            if not lead.owner_id:
                lead.owner = request.user
            lead.save()
            return redirect("leads:detail", pk=lead.pk)
    else:
        form = LeadForm(initial={"owner": request.user})
    return render(request, "leads/form.html", {"form": form, "action": "Create"})


@login_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if not _can_edit(request.user, lead):
        return render(request, "leads/form.html", {
            "lead": lead,
            "converted_banner": True,
            "form": None,
            "action": "Edit",
        })
    if request.method == "POST":
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            return redirect("leads:detail", pk=lead.pk)
    else:
        form = LeadForm(instance=lead)
    return render(request, "leads/form.html", {"form": form, "lead": lead, "action": "Edit"})


@login_required
def lead_disqualify(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == "POST":
        form = DisqualifyForm(request.POST)
        if form.is_valid():
            lead.status = Status.DISQUALIFIED
            lead.disqualified_reason = form.cleaned_data["disqualified_reason"]
            lead.save(update_fields=["status", "disqualified_reason", "updated_at"])
            return redirect("leads:detail", pk=lead.pk)
    else:
        form = DisqualifyForm()
    return render(request, "leads/disqualify.html", {"form": form, "lead": lead})


@login_required
@require_POST
def lead_delete(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    lead.soft_delete(request.user)
    return redirect("leads:list")
