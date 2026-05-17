"""
Django signals — fire email + Teams notifications on GoalSheet status changes (5.2).
Connected in IntegrationsConfig.ready().
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from goals.models import GoalSheet
from .notifications import notify


@receiver(post_save, sender=GoalSheet)
def goalsheet_status_changed(sender, instance, created, **kwargs):
    sheet = instance
    employee = sheet.employee
    manager  = employee.manager

    # Build deep-link paths
    employee_path = f'/goals/{sheet.pk}/'
    manager_path  = f'/manager/sheets/{sheet.pk}/review/'

    if created:
        return  # No notification on bare creation

    if sheet.status == GoalSheet.STATUS_SUBMITTED:
        # Notify manager that employee submitted
        if manager and manager.email:
            notify(
                subject=f'[GoalTrack] {employee.get_full_name()} submitted their goal sheet',
                body=(
                    f'{employee.get_full_name()} has submitted their goal sheet for '
                    f'"{sheet.cycle.name}". Please review and approve.'
                ),
                recipient_email=manager.email,
                teams_title='Goal Sheet Submitted',
                deep_link_path=manager_path,
            )

    elif sheet.status == GoalSheet.STATUS_APPROVED:
        # Notify employee their sheet was approved
        if employee.email:
            notify(
                subject=f'[GoalTrack] Your goal sheet has been approved',
                body=(
                    f'Your goal sheet for "{sheet.cycle.name}" has been approved by '
                    f'{sheet.approved_by.get_full_name() if sheet.approved_by else "your manager"}.'
                ),
                recipient_email=employee.email,
                teams_title='Goal Sheet Approved',
                deep_link_path=employee_path,
            )

    elif sheet.status == GoalSheet.STATUS_RETURNED:
        # Notify employee their sheet was returned
        if employee.email:
            remark = sheet.return_remark or 'Please review and resubmit.'
            notify(
                subject=f'[GoalTrack] Your goal sheet has been returned for revision',
                body=(
                    f'Your goal sheet for "{sheet.cycle.name}" was returned.\n\n'
                    f'Manager remarks: {remark}'
                ),
                recipient_email=employee.email,
                teams_title='Goal Sheet Returned for Revision',
                deep_link_path=employee_path,
            )
