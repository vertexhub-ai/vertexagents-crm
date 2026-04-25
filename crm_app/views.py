from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AccountConversionForm, ContactConversionForm, OpportunityConversionForm
from .models import Lead
from .services import convert_lead


def lead_list(request):
    leads = Lead.objects.select_related('owner').order_by('-created_at')
    if request.GET.get('status'):
        leads = leads.filter(status=request.GET['status'])
    if request.GET.get('owner'):
        leads = leads.filter(owner_id=request.GET['owner'])
    return render(request, 'crm_app/lead_list.html', {'leads': leads})


def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    return render(request, 'crm_app/lead_detail.html', {'lead': lead})


@login_required
def lead_convert(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    if lead.status != 'qualified':
        messages.error(
            request,
            f'Cannot convert a lead with status "{lead.get_status_display()}". '
            'The lead must be qualified first.',
        )
        return redirect('lead_detail', pk=pk)

    if request.method == 'POST':
        contact_form = ContactConversionForm(request.POST, prefix='contact')
        account_form = AccountConversionForm(request.POST, prefix='account')
        opp_form = OpportunityConversionForm(request.POST, prefix='opp')

        if contact_form.is_valid() and account_form.is_valid() and opp_form.is_valid():
            cd = contact_form.cleaned_data
            ad = account_form.cleaned_data
            od = opp_form.cleaned_data

            account_choice = {'mode': ad['account_mode']}
            if ad['account_mode'] == 'existing':
                account_choice['account_id'] = ad['existing_account'].id
            elif ad['account_mode'] == 'new':
                account_choice['account_name'] = ad['new_account_name']

            opportunity_data = None
            if od.get('create_opportunity'):
                opportunity_data = {
                    'create': True,
                    'name': od['opportunity_name'],
                    'amount': od.get('amount'),
                    'expected_close_date': od.get('expected_close_date'),
                }

            try:
                result = convert_lead(
                    lead=lead,
                    contact_data=cd,
                    account_choice=account_choice,
                    opportunity_data=opportunity_data,
                    user=request.user,
                )
                messages.success(
                    request,
                    f'Lead converted successfully. Contact: {result.contact}.'
                )
                return redirect('lead_detail', pk=pk)
            except Exception as exc:
                messages.error(request, f'Conversion failed: {exc}')

    else:
        opp_name = (lead.company_name or f'{lead.first_name} {lead.last_name}') + ' — Opportunity'
        contact_form = ContactConversionForm(prefix='contact', initial={
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'email': lead.email,
            'phone': lead.phone,
            'title': lead.title,
        })
        account_form = AccountConversionForm(prefix='account', initial={
            'account_mode': 'new',
            'new_account_name': lead.company_name,
        })
        opp_form = OpportunityConversionForm(prefix='opp', initial={
            'create_opportunity': True,
            'opportunity_name': opp_name,
        })

    return render(request, 'crm_app/lead_convert.html', {
        'lead': lead,
        'contact_form': contact_form,
        'account_form': account_form,
        'opp_form': opp_form,
    })
