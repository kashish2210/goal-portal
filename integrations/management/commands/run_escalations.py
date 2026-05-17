"""
Management command: python manage.py run_escalations

Evaluates all active EscalationRules and fires notifications
through the escalation chain (employee → manager → HR).

Schedule via cron / Render cron job to run daily.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from goals.models import GoalCycle, GoalSheet, ManagerCheckIn
from integrations.models import EscalationRule, EscalationLog
from integrations.notifications import notify

User = get_user_model()


class Command(BaseCommand):
    help = 'Evaluate escalation rules and send notifications.'

    def handle(self, *args, **options):
        now   = timezone.now()
        today = now.date()
        fired = 0

        for rule in EscalationRule.objects.filter(is_active=True):
            if rule.trigger == EscalationRule.TRIGGER_NO_SUBMISSION:
                fired += self._check_no_submission(rule, today)
            elif rule.trigger == EscalationRule.TRIGGER_NO_APPROVAL:
                fired += self._check_no_approval(rule, today)
            elif rule.trigger == EscalationRule.TRIGGER_NO_CHECKIN:
                fired += self._check_no_checkin(rule, today)

        self.stdout.write(self.style.SUCCESS(f'Escalations fired: {fired}'))

    # ── Rule handlers ─────────────────────────────────────────────────────────

    def _check_no_submission(self, rule, today):
        """Employee has not submitted goals within N days of cycle open."""
        fired = 0
        active_cycles = GoalCycle.objects.filter(
            is_active=True, phase=GoalCycle.PHASE_GOAL_SETTING
        )
        for cycle in active_cycles:
            deadline = cycle.start_date + timedelta(days=rule.days_threshold)
            if today < deadline:
                continue  # Not yet overdue

            employees = User.objects.filter(role=User.ROLE_EMPLOYEE)
            for emp in employees:
                sheet = GoalSheet.objects.filter(employee=emp, cycle=cycle).first()
                if sheet and sheet.status != GoalSheet.STATUS_DRAFT:
                    continue  # Already submitted

                days_overdue = (today - deadline).days
                fired += self._fire_chain(rule, emp, sheet, days_overdue,
                    subject=f'Goal sheet not submitted — {cycle.name}',
                    body=(
                        f'{emp.get_full_name()} has not submitted their goal sheet '
                        f'for "{cycle.name}" (overdue by {days_overdue} day(s)).'
                    ),
                    deep_link=f'/goals/{sheet.pk}/' if sheet else '/goals/',
                )
        return fired

    def _check_no_approval(self, rule, today):
        """Manager has not approved goals within N days of submission."""
        fired = 0
        submitted_sheets = GoalSheet.objects.filter(
            status=GoalSheet.STATUS_SUBMITTED,
            submitted_at__isnull=False,
        ).select_related('employee', 'employee__manager')

        for sheet in submitted_sheets:
            submitted_date = sheet.submitted_at.date()
            deadline = submitted_date + timedelta(days=rule.days_threshold)
            if today < deadline:
                continue

            days_overdue = (today - deadline).days
            emp = sheet.employee
            fired += self._fire_chain(rule, emp, sheet, days_overdue,
                subject=f'Goal sheet pending approval — {sheet.cycle.name}',
                body=(
                    f'{emp.get_full_name()}\'s goal sheet for "{sheet.cycle.name}" '
                    f'has been awaiting manager approval for {days_overdue + rule.days_threshold} day(s).'
                ),
                deep_link=f'/manager/sheets/{sheet.pk}/review/',
            )
        return fired

    def _check_no_checkin(self, rule, today):
        """Quarterly check-in not completed within active window."""
        fired = 0
        checkin_cycles = GoalCycle.objects.filter(
            is_active=True
        ).exclude(phase=GoalCycle.PHASE_GOAL_SETTING)

        for cycle in checkin_cycles:
            deadline = cycle.start_date + timedelta(days=rule.days_threshold)
            if today < deadline:
                continue

            approved_sheets = GoalSheet.objects.filter(
                status=GoalSheet.STATUS_APPROVED,
                cycle__phase=GoalCycle.PHASE_GOAL_SETTING,
            ).select_related('employee')

            for sheet in approved_sheets:
                emp = sheet.employee
                checkin = ManagerCheckIn.objects.filter(
                    employee=emp, cycle=cycle, is_complete=True
                ).first()
                if checkin:
                    continue

                days_overdue = (today - deadline).days
                fired += self._fire_chain(rule, emp, sheet, days_overdue,
                    subject=f'Check-in not completed — {cycle.name}',
                    body=(
                        f'The quarterly check-in for {emp.get_full_name()} '
                        f'({cycle.name}) has not been completed (overdue by {days_overdue} day(s)).'
                    ),
                    deep_link=f'/goals/{sheet.pk}/',
                )
        return fired

    # ── Chain logic ───────────────────────────────────────────────────────────

    def _fire_chain(self, rule, subject_user, sheet, days_overdue,
                    subject, body, deep_link):
        """
        Determine which level of the escalation chain to notify based on
        how many days overdue the item is, then send if not already sent today.
        """
        fired = 0
        manager = subject_user.manager
        hr_users = User.objects.filter(role=User.ROLE_ADMIN)

        chain = []
        # Level 0: notify employee
        if days_overdue >= rule.notify_employee_after:
            chain.append((EscalationLog.LEVEL_EMPLOYEE, subject_user))
        # Level 1: notify manager
        if manager and days_overdue >= rule.notify_employee_after + rule.notify_manager_after:
            chain.append((EscalationLog.LEVEL_MANAGER, manager))
        # Level 2: notify HR
        if days_overdue >= rule.notify_employee_after + rule.notify_manager_after + rule.notify_hr_after:
            for hr in hr_users:
                chain.append((EscalationLog.LEVEL_HR, hr))

        for level, recipient in chain:
            # Deduplicate: only one notification per (rule, level, subject, day)
            already_sent = EscalationLog.objects.filter(
                rule=rule,
                level=level,
                subject_user=subject_user,
                sent_at__date=timezone.now().date(),
            ).exists()
            if already_sent:
                continue

            notify(
                subject=subject,
                body=body,
                recipient_email=recipient.email,
                teams_title=subject,
                deep_link_path=deep_link,
            )
            EscalationLog.objects.create(
                rule=rule,
                level=level,
                notified_user=recipient,
                subject_user=subject_user,
                goal_sheet=sheet,
                message=body,
            )
            fired += 1

        return fired
