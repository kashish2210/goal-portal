"""
Management command: python manage.py seed_demo_users
Creates demo users + realistic goal sheets, goals, and check-in data.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random

from goals.models import (
    Department, ThrustArea, GoalCycle,
    GoalSheet, Goal, QuarterlyAchievement, ManagerCheckIn, AuditLog
)

User = get_user_model()
PASSWORD = '1234@abcd'


def get_or_create_user(username, role, first, last, email, employee_id, dept=None, manager=None):
    if User.objects.filter(username=username).exists():
        u = User.objects.get(username=username)
        u.set_password(PASSWORD)
        u.first_name = first
        u.last_name = last
        u.email = email
        u.role = role
        u.employee_id = employee_id
        if dept:
            u.department = dept
        if manager:
            u.manager = manager
        u.save()
        return u, False
    u = User.objects.create_user(
        username=username, password=PASSWORD,
        first_name=first, last_name=last,
        email=email, role=role,
        employee_id=employee_id,
        department=dept, manager=manager,
    )
    return u, True


class Command(BaseCommand):
    help = 'Seed demo users and realistic goal data. Password for all: 1234@abcd'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete all existing goal sheets before seeding')

    def handle(self, *args, **options):
        self.stdout.write('=== Seeding Demo Data ===')

        # ── Departments ──────────────────────────────────────────────────────
        eng,   _ = Department.objects.get_or_create(name='Engineering',  defaults={'code': 'ENG'})
        hr,    _ = Department.objects.get_or_create(name='HR & Admin',   defaults={'code': 'HRA'})
        sales, _ = Department.objects.get_or_create(name='Sales',        defaults={'code': 'SAL'})
        ops,   _ = Department.objects.get_or_create(name='Operations',   defaults={'code': 'OPS'})

        # ── Thrust Areas ─────────────────────────────────────────────────────
        ta_quality,  _ = ThrustArea.objects.get_or_create(name='Product Quality',       defaults={'department': eng})
        ta_csat,     _ = ThrustArea.objects.get_or_create(name='Customer Satisfaction', defaults={'department': sales})
        ta_process,  _ = ThrustArea.objects.get_or_create(name='Process Improvement',   defaults={'department': None})
        ta_revenue,  _ = ThrustArea.objects.get_or_create(name='Revenue Growth',        defaults={'department': sales})
        ta_people,   _ = ThrustArea.objects.get_or_create(name='People & Culture',      defaults={'department': hr})
        ta_digital,  _ = ThrustArea.objects.get_or_create(name='Digital Transformation',defaults={'department': eng})
        ta_ops,      _ = ThrustArea.objects.get_or_create(name='Operational Excellence',defaults={'department': ops})

        # ── Goal Cycles ──────────────────────────────────────────────────────
        cycle_gs, _ = GoalCycle.objects.get_or_create(
            phase='goal_setting', fiscal_year='25-26',
            defaults={
                'name': 'FY 25-26 Phase 1 - Goal Setting',
                'start_date': date(2025, 5, 1), 'end_date': date(2025, 6, 30),
                'is_active': True,
            }
        )
        cycle_q1, _ = GoalCycle.objects.get_or_create(
            phase='q1', fiscal_year='25-26',
            defaults={
                'name': 'FY 25-26 Q1 Check-in',
                'start_date': date(2025, 7, 1), 'end_date': date(2025, 9, 30),
                'is_active': False,
            }
        )

        # ── Users ────────────────────────────────────────────────────────────
        admin_user, c = get_or_create_user('admin', 'admin', 'Admin', 'User',
            'admin@goaltrack.demo', 'EMP-ADMIN001', dept=hr)
        self.stdout.write(f'  {"Created" if c else "Updated"} admin (Admin)')

        mgr1, c = get_or_create_user('manager', 'manager', 'Ravi', 'Sharma',
            'ravi.sharma@goaltrack.demo', 'EMP-MGR001', dept=eng)
        self.stdout.write(f'  {"Created" if c else "Updated"} manager (Manager - Engineering)')

        mgr2, c = get_or_create_user('manager2', 'manager', 'Sneha', 'Kulkarni',
            'sneha.kulkarni@goaltrack.demo', 'EMP-MGR002', dept=sales)
        self.stdout.write(f'  {"Created" if c else "Updated"} manager2 (Manager - Sales)')

        emp1, c = get_or_create_user('employee', 'employee', 'Priya', 'Patel',
            'priya.patel@goaltrack.demo', 'EMP-EMP001', dept=eng, manager=mgr1)
        self.stdout.write(f'  {"Created" if c else "Updated"} employee (Employee - Engineering)')

        emp2, c = get_or_create_user('arjun.nair', 'employee', 'Arjun', 'Nair',
            'arjun.nair@goaltrack.demo', 'EMP-EMP002', dept=eng, manager=mgr1)
        self.stdout.write(f'  {"Created" if c else "Updated"} arjun.nair (Employee - Engineering)')

        emp3, c = get_or_create_user('kavya.mehta', 'employee', 'Kavya', 'Mehta',
            'kavya.mehta@goaltrack.demo', 'EMP-EMP003', dept=sales, manager=mgr2)
        self.stdout.write(f'  {"Created" if c else "Updated"} kavya.mehta (Employee - Sales)')

        emp4, c = get_or_create_user('rahul.das', 'employee', 'Rahul', 'Das',
            'rahul.das@goaltrack.demo', 'EMP-EMP004', dept=sales, manager=mgr2)
        self.stdout.write(f'  {"Created" if c else "Updated"} rahul.das (Employee - Sales)')

        # ── Optional reset ────────────────────────────────────────────────────
        if options['reset']:
            GoalSheet.objects.all().delete()
            self.stdout.write('  Deleted all existing goal sheets.')

        # ── Helper: build a sheet for an employee ────────────────────────────
        def make_sheet(emp, cycle, status, goals_data, approved_by=None, return_remark=None):
            sheet, _ = GoalSheet.objects.get_or_create(employee=emp, cycle=cycle)
            sheet.status = status
            sheet.is_locked = (status == GoalSheet.STATUS_APPROVED)
            if status == GoalSheet.STATUS_SUBMITTED:
                sheet.submitted_at = timezone.now() - timedelta(days=random.randint(1, 5))
            if approved_by and status == GoalSheet.STATUS_APPROVED:
                sheet.approved_by = approved_by
                sheet.approved_at = timezone.now() - timedelta(days=random.randint(1, 3))
            if return_remark:
                sheet.return_remark = return_remark
            sheet.save()

            # Remove stale goals then recreate
            sheet.goals.all().delete()
            total_w = sum(g['w'] for g in goals_data)
            for i, gd in enumerate(goals_data):
                Goal.objects.create(
                    goal_sheet=sheet,
                    thrust_area=gd['ta'],
                    title=gd['title'],
                    uom=gd.get('uom', 'number'),
                    target=gd.get('target'),
                    target_date=gd.get('target_date'),
                    weightage=gd['w'],
                    order=i + 1,
                )
            return sheet

        # ── Priya's sheet — APPROVED ─────────────────────────────────────────
        self.stdout.write('\n  Building goal sheets...')
        sheet_priya = make_sheet(emp1, cycle_gs, GoalSheet.STATUS_APPROVED, [
            {'ta': ta_quality,  'title': 'Reduce defect rate to < 2% in sprint releases',   'uom': 'percentage', 'target': 2,    'w': 25},
            {'ta': ta_digital,  'title': 'Complete AWS Solutions Architect certification',    'uom': 'zero',                       'w': 20},
            {'ta': ta_process,  'title': 'Deliver CI/CD pipeline migration on schedule',      'uom': 'timeline', 'target_date': date(2025, 9, 30), 'w': 20},
            {'ta': ta_quality,  'title': 'Achieve 90%+ unit test coverage across owned modules','uom': 'percentage','target': 90,  'w': 20},
            {'ta': ta_people,   'title': 'Mentor 2 junior developers with structured plan',   'uom': 'number',  'target': 2,    'w': 15},
        ], approved_by=mgr1)

        # ── Arjun's sheet — SUBMITTED ────────────────────────────────────────
        sheet_arjun = make_sheet(emp2, cycle_gs, GoalSheet.STATUS_SUBMITTED, [
            {'ta': ta_quality,  'title': 'Ship mobile app v2.0 with zero P0 bugs',            'uom': 'number',  'target': 0,    'w': 30},
            {'ta': ta_digital,  'title': 'Migrate 3 microservices to Kubernetes',             'uom': 'number',  'target': 3,    'w': 25},
            {'ta': ta_process,  'title': 'Document all internal APIs in Confluence',          'uom': 'percentage','target': 100, 'w': 20},
            {'ta': ta_people,   'title': 'Complete leadership training module',               'uom': 'zero',                    'w': 15},
            {'ta': ta_quality,  'title': 'Reduce average bug resolution time to 24 hrs',     'uom': 'number',  'target': 24,   'w': 10},
        ])

        # ── Kavya's sheet — APPROVED ─────────────────────────────────────────
        sheet_kavya = make_sheet(emp3, cycle_gs, GoalSheet.STATUS_APPROVED, [
            {'ta': ta_revenue,  'title': 'Achieve quarterly revenue target of Rs 45L',        'uom': 'number',  'target': 4500000, 'w': 35},
            {'ta': ta_csat,     'title': 'Maintain NPS score >= 8.0 across accounts',         'uom': 'number',  'target': 8,    'w': 25},
            {'ta': ta_revenue,  'title': 'Onboard 5 new enterprise accounts',                 'uom': 'number',  'target': 5,    'w': 20},
            {'ta': ta_process,  'title': 'Update CRM pipeline weekly with < 2% data errors',  'uom': 'percentage','target': 98,  'w': 10},
            {'ta': ta_people,   'title': 'Complete SPIN Selling certification',               'uom': 'zero',                    'w': 10},
        ], approved_by=mgr2)

        # ── Rahul's sheet — RETURNED ─────────────────────────────────────────
        make_sheet(emp4, cycle_gs, GoalSheet.STATUS_RETURNED, [
            {'ta': ta_revenue,  'title': 'Close 10 new deals in Q1',                          'uom': 'number',  'target': 10,   'w': 50},
            {'ta': ta_csat,     'title': 'Achieve 4.5/5 customer satisfaction score',         'uom': 'number',  'target': 4.5,  'w': 50},
        ], return_remark='Weightage must be split more granularly (min 10% per goal, 5 goals recommended). Also please add a learning goal.')

        # ── Q1 Achievement data for Priya ─────────────────────────────────────
        self.stdout.write('  Building quarterly achievements for Priya...')
        actuals = [
            (1.8,   None, 'on_track', 'Defect rate improved to 1.8%. On track.'),
            (None,  None, 'completed','Passed AWS SAA-C03 exam on 15-Aug.'),
            (None,  date(2025, 9, 28), 'completed', 'Delivered 2 days ahead of schedule.'),
            (85,    None, 'on_track', 'At 85% — 3 modules still pending review.'),
            (1,     None, 'on_track', 'Mentoring Arjun Nair formally since July.'),
        ]
        goals_priya = list(sheet_priya.goals.order_by('order'))
        for goal, (actual, actual_date, status, notes) in zip(goals_priya, actuals):
            QuarterlyAchievement.objects.update_or_create(
                goal=goal, cycle=cycle_q1,
                defaults={
                    'actual': actual,
                    'actual_date': actual_date,
                    'status': status,
                    'notes': notes,
                    'updated_by': emp1,
                }
            )

        # ── Manager check-in for Priya ────────────────────────────────────────
        ManagerCheckIn.objects.update_or_create(
            employee=emp1, manager=mgr1, cycle=cycle_q1,
            defaults={
                'comment': (
                    'Priya is performing excellently this quarter. '
                    'Defect rate is well below target and certification done. '
                    'Need to accelerate unit test coverage — currently at 85%. '
                    'Discussed blockers: legacy modules lack test infra. Plan: allocate 20% sprint capacity.'
                ),
                'is_complete': True,
                'checked_in_at': timezone.now() - timedelta(days=2),
            }
        )

        # ── Q1 Achievements for Kavya ─────────────────────────────────────────
        self.stdout.write('  Building quarterly achievements for Kavya...')
        actuals_kavya = [
            (5200000, None, 'completed', 'Exceeded target by 15.5%. Strong Q1.'),
            (8.3,     None, 'completed', 'NPS at 8.3 across 12 accounts.'),
            (6,       None, 'completed', 'Onboarded 6 accounts, 1 ahead of plan.'),
            (97,      None, 'on_track',  'Minor data quality issues in 2 records.'),
            (None,    None, 'completed', 'SPIN certified in July batch.'),
        ]
        goals_kavya = list(sheet_kavya.goals.order_by('order'))
        for goal, (actual, actual_date, status, notes) in zip(goals_kavya, actuals_kavya):
            QuarterlyAchievement.objects.update_or_create(
                goal=goal, cycle=cycle_q1,
                defaults={
                    'actual': actual,
                    'actual_date': actual_date,
                    'status': status,
                    'notes': notes,
                    'updated_by': emp3,
                }
            )

        ManagerCheckIn.objects.update_or_create(
            employee=emp3, manager=mgr2, cycle=cycle_q1,
            defaults={
                'comment': (
                    'Outstanding quarter for Kavya. Revenue 15% above target. '
                    'Recommend for spotlight recognition. Discussed stretch goal for Q2: '
                    'target 2 international accounts for cross-border expansion.'
                ),
                'is_complete': True,
                'checked_in_at': timezone.now() - timedelta(days=1),
            }
        )

        # ── Audit log entries ─────────────────────────────────────────────────
        AuditLog.objects.get_or_create(
            user=mgr1, action=AuditLog.ACTION_APPROVE, goal_sheet=sheet_priya,
            defaults={'extra_notes': 'Approved during review meeting on 12-Jun-25.'}
        )
        AuditLog.objects.get_or_create(
            user=mgr2, action=AuditLog.ACTION_APPROVE, goal_sheet=sheet_kavya,
            defaults={'extra_notes': 'Approved with minor weightage adjustment.'}
        )

        self.stdout.write('\n=== Demo Login Credentials ===')
        self.stdout.write(f'  admin     (Admin)            - password: {PASSWORD}')
        self.stdout.write(f'  manager   (Manager / Eng)    - password: {PASSWORD}')
        self.stdout.write(f'  manager2  (Manager / Sales)  - password: {PASSWORD}')
        self.stdout.write(f'  employee  (Employee / Eng)   - password: {PASSWORD}')
        self.stdout.write(f'  arjun.nair (Employee / Eng)  - password: {PASSWORD}')
        self.stdout.write(f'  kavya.mehta (Employee / Sales)- password: {PASSWORD}')
        self.stdout.write(f'  rahul.das  (Employee / Sales) - password: {PASSWORD}')
        self.stdout.write('\nURL: http://127.0.0.1:8000/')
        self.stdout.write('Seed complete.')
