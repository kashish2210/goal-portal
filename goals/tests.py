from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError

from .models import Department, User, ThrustArea, GoalCycle, GoalSheet, Goal


class GoalValidationTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Engineering', code='ENG')
        self.manager = User.objects.create_user(username='mgr', password='x', role=User.ROLE_MANAGER)
        self.emp = User.objects.create_user(username='emp', password='x', role=User.ROLE_EMPLOYEE, manager=self.manager, department=self.dept)
        self.thrust = ThrustArea.objects.create(name='Delivery', department=self.dept)
        self.cycle = GoalCycle.objects.create(name='FY Test', phase=GoalCycle.PHASE_GOAL_SETTING, fiscal_year='2025-26', start_date='2025-05-01', end_date='2026-04-30', is_active=True, created_by=self.manager)
        self.sheet = GoalSheet.objects.create(employee=self.emp, cycle=self.cycle)

    def test_min_weightage_enforced(self):
        g = Goal(goal_sheet=self.sheet, thrust_area=self.thrust, title='Low weight', uom=Goal.UOM_NUMERIC_MIN, target=Decimal('100'), weightage=Decimal('5.00'))
        with self.assertRaises(ValidationError):
            g.full_clean()

    def test_max_goals_per_sheet(self):
        # create 8 valid goals
        for i in range(8):
            Goal.objects.create(goal_sheet=self.sheet, thrust_area=self.thrust, title=f'G{i}', uom=Goal.UOM_NUMERIC_MIN, target=Decimal('10'), weightage=Decimal('12.50'))

        # ninth should fail validation
        g9 = Goal(goal_sheet=self.sheet, thrust_area=self.thrust, title='G9', uom=Goal.UOM_NUMERIC_MIN, target=Decimal('10'), weightage=Decimal('10'))
        with self.assertRaises(ValidationError):
            g9.full_clean()

    def test_total_weightage_must_be_100_to_submit(self):
        Goal.objects.create(goal_sheet=self.sheet, thrust_area=self.thrust, title='A', uom=Goal.UOM_NUMERIC_MIN, target=Decimal('10'), weightage=Decimal('30'))
        Goal.objects.create(goal_sheet=self.sheet, thrust_area=self.thrust, title='B', uom=Goal.UOM_NUMERIC_MIN, target=Decimal('10'), weightage=Decimal('30'))
        Goal.objects.create(goal_sheet=self.sheet, thrust_area=self.thrust, title='C', uom=Goal.UOM_NUMERIC_MIN, target=Decimal('10'), weightage=Decimal('30'))

        can, reason = self.sheet.can_submit()
        self.assertFalse(can)

        # adjust last goal to make total 100
        last = self.sheet.goals.last()
        last.weightage = Decimal('40')
        last.save()
        can, reason = self.sheet.can_submit()
        self.assertTrue(can)
from django.test import TestCase

# Create your tests here.
