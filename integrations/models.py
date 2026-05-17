from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# ─────────────────────────────────────────────
# 5.x  INTEGRATION CONFIGURATION  (DB-stored)
# ─────────────────────────────────────────────

class IntegrationConfig(models.Model):
    """Singleton-style table (only one row used) for admin-configurable integration settings."""

    # Azure AD / Entra ID
    azure_client_id     = models.CharField(max_length=200, blank=True)
    azure_client_secret = models.CharField(max_length=200, blank=True)
    azure_tenant_id     = models.CharField(max_length=200, blank=True)
    azure_redirect_uri  = models.CharField(max_length=500, blank=True)
    # JSON-encoded role map: {"<group-id>": "admin", ...}
    azure_role_map_json = models.TextField(blank=True, default='{}')

    # Email
    email_host          = models.CharField(max_length=200, blank=True, default='smtp.gmail.com')
    email_port          = models.PositiveIntegerField(default=587)
    email_host_user     = models.CharField(max_length=200, blank=True)
    email_host_password = models.CharField(max_length=200, blank=True)
    email_use_tls       = models.BooleanField(default=True)
    default_from_email  = models.CharField(max_length=200, blank=True, default='goaltrack@yourorg.com')

    # Microsoft Teams
    teams_webhook_url   = models.URLField(max_length=1000, blank=True)

    # Site
    site_base_url       = models.CharField(max_length=500, blank=True, default='http://127.0.0.1:8000')

    updated_at          = models.DateTimeField(auto_now=True)
    updated_by          = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )

    class Meta:
        verbose_name = 'Integration Configuration'

    def __str__(self):
        return f'Integration Config (updated {self.updated_at:%Y-%m-%d %H:%M})'

    @classmethod
    def get(cls):
        """Always returns the single config row, creating it if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ─────────────────────────────────────────────
# 5.3  ESCALATION MODULE
# ─────────────────────────────────────────────

class EscalationRule(models.Model):
    """Configurable rule that triggers escalation notifications."""

    TRIGGER_NO_SUBMISSION   = 'no_submission'    # Employee hasn't submitted within N days of cycle open
    TRIGGER_NO_APPROVAL     = 'no_approval'      # Manager hasn't approved within N days of submission
    TRIGGER_NO_CHECKIN      = 'no_checkin'       # Check-in not completed within active window

    TRIGGER_CHOICES = [
        (TRIGGER_NO_SUBMISSION, 'Employee has not submitted goals within N days of cycle open'),
        (TRIGGER_NO_APPROVAL,   'Manager has not approved goals within N days of submission'),
        (TRIGGER_NO_CHECKIN,    'Quarterly check-in not completed within active window'),
    ]

    name            = models.CharField(max_length=150)
    trigger         = models.CharField(max_length=30, choices=TRIGGER_CHOICES)
    days_threshold  = models.PositiveIntegerField(
        help_text='Number of days before escalation fires'
    )
    # Escalation chain intervals (days between each level)
    notify_employee_after   = models.PositiveIntegerField(default=0,  help_text='Days after threshold to notify employee')
    notify_manager_after    = models.PositiveIntegerField(default=2,  help_text='Days after employee notification to notify manager')
    notify_hr_after         = models.PositiveIntegerField(default=5,  help_text='Days after manager notification to notify HR/skip-level')
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['trigger', 'days_threshold']

    def __str__(self):
        return f'{self.name} ({self.get_trigger_display()}, {self.days_threshold}d)'


class EscalationLog(models.Model):
    """Immutable record of every escalation notification sent."""

    LEVEL_EMPLOYEE  = 'employee'
    LEVEL_MANAGER   = 'manager'
    LEVEL_HR        = 'hr'
    LEVEL_CHOICES   = [
        (LEVEL_EMPLOYEE, 'Employee'),
        (LEVEL_MANAGER,  'Manager'),
        (LEVEL_HR,       'HR / Skip-level'),
    ]

    rule        = models.ForeignKey(EscalationRule, on_delete=models.PROTECT, related_name='logs')
    level       = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    notified_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='escalation_notifications'
    )
    # The subject of the escalation (the employee whose goal is overdue)
    subject_user  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='escalations_about'
    )
    goal_sheet  = models.ForeignKey(
        'goals.GoalSheet', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='escalation_logs'
    )
    message     = models.TextField()
    sent_at     = models.DateTimeField(auto_now_add=True)
    resolved    = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='escalations_resolved'
    )

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f'[{self.get_level_display()}] {self.rule.name} — {self.subject_user} @ {self.sent_at:%Y-%m-%d}'
