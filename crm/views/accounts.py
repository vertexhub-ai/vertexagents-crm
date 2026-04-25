from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from crm.forms import AccountForm
from crm.models import Account


def _can_edit(user, account):
    return user.role == "admin" or account.owner_id == user.pk


def _account_options(request):
    """Return top-10 account rows for the HTMX autocomplete partial."""
    q = request.GET.get("q", "").strip()
    if request.user.role == "admin":
        qs = Account.objects.all()
    else:
        qs = Account.objects.filter(owner=request.user)
    if q:
        qs = qs.filter(name__icontains=q)
    accounts = qs.order_by("name")[:10]
    return render(request, "accounts/_options.html", {"accounts": accounts})


@login_required
def account_list(request):
    if request.GET.get("format") == "options":
        return _account_options(request)

    if request.user.role == "admin":
        qs = Account.objects.select_related("owner")
    else:
        qs = Account.objects.filter(owner=request.user).select_related("owner")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(name__icontains=q)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/list.html", {"page_obj": page, "q": q})


@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk)
    return render(request, "accounts/detail.html", {"account": account})


@login_required
def account_create(request):
    form = AccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = form.save(commit=False)
        account.owner = request.user
        account.save()
        return redirect("accounts:detail", pk=account.pk)
    return render(request, "accounts/form.html", {"form": form, "action": "Create"})


@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if not _can_edit(request.user, account):
        return HttpResponseForbidden()
    form = AccountForm(request.POST or None, instance=account)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("accounts:detail", pk=account.pk)
    return render(request, "accounts/form.html", {"form": form, "account": account, "action": "Edit"})


@login_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if not _can_edit(request.user, account):
        return HttpResponseForbidden()
    if request.method == "POST":
        account.soft_delete(request.user)
        return redirect("accounts:list")
    return render(request, "accounts/confirm_delete.html", {"account": account})
