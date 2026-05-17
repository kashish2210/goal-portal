import subprocess
import sys

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views import View
from django.http import JsonResponse

from .models import EscalationRule, EscalationLog, IntegrationConfig


class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            messages.error(request, 'Admin access required.')
            return redirect('goals:sheet_list')
        return super().dispatch(request, *args, **kwargs)


# ── Escalation Rules ──────────────────────────────────────────────────────────

class EscalationRuleListView(AdminRequiredMixin, View):
    def get(self, request):
        rules = EscalationRule.objects.all()
        return render(request, 'integrations/escalation_rules.html', {
            'rules': rules,
            'trigger_choices': EscalationRule.TRIGGER_CHOICES,
        })

    def post(self, request):
        name           = request.POST.get('name', '').strip()
        trigger        = request.POST.get('trigger', '')
        days_threshold = request.POST.get('days_threshold', 0)
        notify_emp     = request.POST.get('notify_employee_after', 0)
        notify_mgr     = request.POST.get('notify_manager_after', 2)
        notify_hr      = request.POST.get('notify_hr_after', 5)

        if not name or not trigger:
            messages.error(request, 'Name and trigger are required.')
            return redirect('integrations:escalation_rules')

        EscalationRule.objects.create(
            name=name,
            trigger=trigger,
            days_threshold=int(days_threshold),
            notify_employee_after=int(notify_emp),
            notify_manager_after=int(notify_mgr),
            notify_hr_after=int(notify_hr),
        )
        messages.success(request, f'Rule "{name}" created.')
        return redirect('integrations:escalation_rules')


class EscalationRuleToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(EscalationRule, pk=pk)
        rule.is_active = not rule.is_active
        rule.save()
        messages.success(request, f'Rule "{rule.name}" {"activated" if rule.is_active else "deactivated"}.')
        return redirect('integrations:escalation_rules')


# ── Escalation Log ────────────────────────────────────────────────────────────

class EscalationLogView(AdminRequiredMixin, View):
    def get(self, request):
        logs = EscalationLog.objects.select_related(
            'rule', 'notified_user', 'subject_user', 'goal_sheet'
        ).order_by('-sent_at')[:200]
        return render(request, 'integrations/escalation_log.html', {'logs': logs})


class EscalationResolveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        log = get_object_or_404(EscalationLog, pk=pk)
        log.resolved    = True
        log.resolved_at = timezone.now()
        log.resolved_by = request.user
        log.save()
        messages.success(request, 'Escalation marked as resolved.')
        return redirect('integrations:escalation_log')


# ── Integration Settings ──────────────────────────────────────────────────────

class IntegrationSettingsView(AdminRequiredMixin, View):
    def get(self, request):
        cfg = IntegrationConfig.get()
        return render(request, 'integrations/settings.html', {'cfg': cfg})

    def post(self, request):
        cfg = IntegrationConfig.get()
        p = request.POST

        cfg.azure_client_id     = p.get('azure_client_id', '').strip()
        cfg.azure_client_secret = p.get('azure_client_secret', '').strip()
        cfg.azure_tenant_id     = p.get('azure_tenant_id', '').strip()
        cfg.azure_redirect_uri  = p.get('azure_redirect_uri', '').strip()
        cfg.azure_role_map_json = p.get('azure_role_map_json', '{}').strip() or '{}'

        cfg.email_host         = p.get('email_host', '').strip()
        cfg.email_port         = int(p.get('email_port') or 587)
        cfg.email_host_user    = p.get('email_host_user', '').strip()
        new_pw = p.get('email_host_password', '').strip()
        if new_pw:
            cfg.email_host_password = new_pw
        cfg.email_use_tls      = 'email_use_tls' in p
        cfg.default_from_email = p.get('default_from_email', '').strip()

        cfg.teams_webhook_url  = p.get('teams_webhook_url', '').strip()
        cfg.site_base_url      = p.get('site_base_url', '').strip()

        cfg.updated_by = request.user
        cfg.save()
        messages.success(request, 'Integration settings saved successfully.')
        return redirect('integrations:settings')


# ── Admin Terminal ────────────────────────────────────────────────────────────

ALLOWED_COMMANDS = {
    'run_escalations': ['manage.py', 'run_escalations'],
    'migrate':         ['manage.py', 'migrate', '--run-syncdb'],
    'seed_demo_users': ['manage.py', 'seed_demo_users'],
    'check':           ['manage.py', 'check'],
    'showmigrations':  ['manage.py', 'showmigrations'],
}


class TerminalView(AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'integrations/terminal.html', {
            'commands': ALLOWED_COMMANDS.keys(),
        })

    def post(self, request):
        cmd_key = request.POST.get('command', '').strip()
        if cmd_key not in ALLOWED_COMMANDS:
            return JsonResponse({'output': f'Error: unknown command "{cmd_key}"', 'success': False})

        from django.conf import settings as django_settings
        cmd = [sys.executable] + ALLOWED_COMMANDS[cmd_key]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(django_settings.BASE_DIR),
            )
            output = result.stdout + result.stderr
            return JsonResponse({'output': output or '(no output)', 'success': result.returncode == 0})
        except subprocess.TimeoutExpired:
            return JsonResponse({'output': 'Error: command timed out after 60s.', 'success': False})
        except Exception as exc:
            return JsonResponse({'output': f'Error: {exc}', 'success': False})
