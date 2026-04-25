from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from crm.forms import ContactForm
from crm.models import Account, Contact


def _can_edit(user, contact):
    return user.role == "admin" or contact.owner_id == user.pk


@login_required
def contact_list(request):
    qs = Contact.objects.select_related("owner", "account")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(account__name__icontains=q)
        )

    owner_filter = request.GET.get("owner", "mine")
    if owner_filter == "mine":
        qs = qs.filter(owner=request.user)

    account_id = request.GET.get("account", "").strip()
    if account_id:
        qs = qs.filter(account_id=account_id)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    # Populate account filter dropdown with accounts visible to this user
    if request.user.role == "admin":
        accounts = Account.objects.order_by("name")
    else:
        accounts = Account.objects.filter(owner=request.user).order_by("name")

    return render(
        request,
        "contacts/list.html",
        {
            "page_obj": page,
            "q": q,
            "owner_filter": owner_filter,
            "account_filter": account_id,
            "accounts": accounts,
        },
    )


@login_required
def contact_detail(request, pk):
    contact = get_object_or_404(Contact.objects.select_related("account", "owner"), pk=pk)
    return render(request, "contacts/detail.html", {"contact": contact})


@login_required
def contact_create(request):
    initial = {}
    account_id = request.GET.get("account_id", "").strip()
    if account_id:
        try:
            initial["account"] = Account.objects.get(pk=account_id)
        except (Account.DoesNotExist, ValueError):
            pass

    form = ContactForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        contact = form.save(commit=False)
        contact.owner = request.user
        contact.save()
        return redirect("contacts:detail", pk=contact.pk)
    return render(request, "contacts/form.html", {"form": form, "action": "Create"})


@login_required
def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if not _can_edit(request.user, contact):
        return HttpResponseForbidden()
    form = ContactForm(request.POST or None, instance=contact)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("contacts:detail", pk=contact.pk)
    return render(
        request,
        "contacts/form.html",
        {"form": form, "contact": contact, "action": "Edit"},
    )


@login_required
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if not _can_edit(request.user, contact):
        return HttpResponseForbidden()
    if request.method == "POST":
        contact.soft_delete(request.user)
        if request.headers.get("HX-Request"):
            from django.http import HttpResponse
            return HttpResponse(status=204, headers={"HX-Redirect": "/contacts/"})
        return redirect("contacts:list")
    return render(request, "contacts/confirm_delete.html", {"contact": contact})
