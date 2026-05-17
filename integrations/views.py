from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views import View

from .models import EscalationRule, EscalationLog


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
