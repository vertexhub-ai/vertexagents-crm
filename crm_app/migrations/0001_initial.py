import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Account — no FK dependencies
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        # Lead — with converted_account FK (Account already exists); converted_contact/opportunity added below
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('title', models.CharField(blank=True, max_length=100)),
                ('company_name', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(
                    choices=[
                        ('new', 'New'),
                        ('contacted', 'Contacted'),
                        ('qualified', 'Qualified'),
                        ('disqualified', 'Disqualified'),
                        ('converted', 'Converted'),
                    ],
                    default='new',
                    max_length=20,
                )),
                ('converted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('converted_account', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='converted_from_leads',
                    to='crm_app.account',
                )),
                ('owner', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='leads',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        # Contact — source_lead FK to Lead (which now exists)
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('title', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='contacts',
                    to='crm_app.account',
                )),
                ('owner', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='contacts',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('source_lead', models.OneToOneField(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='converted_contact_record',
                    to='crm_app.lead',
                )),
            ],
        ),
        # Opportunity — source_lead FK to Lead
        migrations.CreateModel(
            name='Opportunity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('stage', models.CharField(
                    choices=[
                        ('new', 'New'),
                        ('discovery', 'Discovery'),
                        ('proposal', 'Proposal'),
                        ('negotiation', 'Negotiation'),
                        ('closed_won', 'Closed Won'),
                        ('closed_lost', 'Closed Lost'),
                    ],
                    default='new',
                    max_length=50,
                )),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('expected_close_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='opportunities',
                    to='crm_app.account',
                )),
                ('contact', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='opportunities',
                    to='crm_app.contact',
                )),
                ('owner', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='opportunities',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('source_lead', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='source_opportunities',
                    to='crm_app.lead',
                )),
            ],
        ),
        # Add Lead.converted_contact FK now that Contact table exists
        migrations.AddField(
            model_name='lead',
            name='converted_contact',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lead_conversion',
                to='crm_app.contact',
            ),
        ),
        # Add Lead.converted_opportunity FK now that Opportunity table exists
        migrations.AddField(
            model_name='lead',
            name='converted_opportunity',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lead_conversion',
                to='crm_app.opportunity',
            ),
        ),
    ]
