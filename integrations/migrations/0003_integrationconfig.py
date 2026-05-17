from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0002_alter_escalationrule_notify_employee_after_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IntegrationConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('azure_client_id',     models.CharField(blank=True, max_length=200)),
                ('azure_client_secret', models.CharField(blank=True, max_length=200)),
                ('azure_tenant_id',     models.CharField(blank=True, max_length=200)),
                ('azure_redirect_uri',  models.CharField(blank=True, max_length=500)),
                ('azure_role_map_json', models.TextField(blank=True, default='{}')),
                ('email_host',          models.CharField(blank=True, default='smtp.gmail.com', max_length=200)),
                ('email_port',          models.PositiveIntegerField(default=587)),
                ('email_host_user',     models.CharField(blank=True, max_length=200)),
                ('email_host_password', models.CharField(blank=True, max_length=200)),
                ('email_use_tls',       models.BooleanField(default=True)),
                ('default_from_email',  models.CharField(blank=True, default='goaltrack@yourorg.com', max_length=200)),
                ('teams_webhook_url',   models.URLField(blank=True, max_length=1000)),
                ('site_base_url',       models.CharField(blank=True, default='http://127.0.0.1:8000', max_length=500)),
                ('updated_at',          models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'Integration Configuration'},
        ),
    ]
