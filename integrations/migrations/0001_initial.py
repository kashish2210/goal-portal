from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('goals', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EscalationRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('trigger', models.CharField(choices=[
                    ('no_submission', 'Employee has not submitted goals within N days of cycle open'),
                    ('no_approval',   'Manager has not approved goals within N days of submission'),
                    ('no_checkin',    'Quarterly check-in not completed within active window'),
                ], max_length=30)),
                ('days_threshold', models.PositiveIntegerField(help_text='Number of days before escalation fires')),
                ('notify_employee_after', models.PositiveIntegerField(default=0)),
                ('notify_manager_after',  models.PositiveIntegerField(default=2)),
                ('notify_hr_after',       models.PositiveIntegerField(default=5)),
                ('is_active',  models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['trigger', 'days_threshold']},
        ),
        migrations.CreateModel(
            name='EscalationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[
                    ('employee', 'Employee'),
                    ('manager',  'Manager'),
                    ('hr',       'HR / Skip-level'),
                ], max_length=20)),
                ('message',     models.TextField()),
                ('sent_at',     models.DateTimeField(auto_now_add=True)),
                ('resolved',    models.BooleanField(default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('rule', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name='logs', to='integrations.escalationrule')),
                ('notified_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='escalation_notifications', to=settings.AUTH_USER_MODEL)),
                ('subject_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='escalations_about', to=settings.AUTH_USER_MODEL)),
                ('goal_sheet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='escalation_logs', to='goals.goalsheet')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='escalations_resolved', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-sent_at']},
        ),
    ]
