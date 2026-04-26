from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AccountForm
from .models import Account

PAGE_SIZE = 25


def _can_edit(user, account):
    return user.is_staff or user.is_superuser or account.owner == user


@login_required
def account_list(request):
    qs = Account.objects.select_related("owner")

    # owner filter: "mine" (default), "all", or specific user id
    owner_filter = request.GET.get("owner", "mine")
    if owner_filter == "mine":
        qs = qs.filter(owner=request.user)
    elif owner_filter != "all":
        qs = qs.filter(owner_id=owner_filter)

    # search
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(name__icontains=q)

    # sort
    sort = request.GET.get("sort", "name_lower")
    allowed_sorts = {
        "name": "name_lower",
        "-name": "-name_lower",
        "owner": "owner__username",
        "-owner": "-owner__username",
        "created": "created_at",
        "-created": "-created_at",
    }
    qs = qs.order_by(allowed_sorts.get(sort, "name_lower"))

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "accounts/list.html", {
        "page_obj": page_obj,
        "q": q,
        "owner_filter": owner_filter,
        "sort": sort,
    })


@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk)
    return render(request, "accounts/detail.html", {
        "account": account,
        "can_edit": _can_edit(request.user, account),
    })


@login_required
def account_create(request):
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            if not account.owner_id:
                account.owner = request.user
            account.save()
            messages.success(request, f'Account "{account.name}" created.')
            return redirect("accounts:detail", pk=account.pk)
    else:
        form = AccountForm(initial={"owner": request.user})

    return render(request, "accounts/form.html", {"form": form, "action": "Create"})


@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if not _can_edit(request.user, account):
        return HttpResponseForbidden("You do not have permission to edit this account.")

    if request.method == "POST":
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Account "{account.name}" updated.')
            return redirect("accounts:detail", pk=account.pk)
    else:
        form = AccountForm(instance=account)

    return render(request, "accounts/form.html", {"form": form, "action": "Edit", "account": account})


@login_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if not _can_edit(request.user, account):
        return HttpResponseForbidden("You do not have permission to delete this account.")

    if request.method == "POST":
        account.soft_delete(request.user)
        messages.success(request, f'Account "{account.name}" deleted.')
        return redirect("accounts:list")

    # GET: return confirm fragment (for HTMX modal or plain page)
    return render(request, "accounts/delete_confirm.html", {"account": account})
