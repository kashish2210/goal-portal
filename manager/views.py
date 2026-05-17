from django.views.generic import TemplateView, View
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model

from goals.models import GoalSheet, GoalCycle, ManagerCheckIn, AuditLog, QuarterlyAchievement, Goal
from goals.forms import QuarterlyAchievementForm

User = get_user_model()


class ManagerRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_manager or request.user.is_admin):
            messages.error(request, 'Manager access required.')
            return redirect('goals:sheet_list')
        return super().dispatch(request, *args, **kwargs)


class TeamDashboardView(ManagerRequiredMixin, View):
    def get(self, request):
        # Get all direct reports
        team = User.objects.filter(manager=request.user, role='employee').select_related('department')

        # Get active cycle
        active_cycle = GoalCycle.objects.filter(is_active=True).order_by('-start_date').first()

        # Aggregate sheet statuses for team
        team_data = []
        for emp in team:
            sheet = None
            if active_cycle:
                sheet = GoalSheet.objects.filter(employee=emp, cycle=active_cycle).first()
            team_data.append({'employee': emp, 'sheet': sheet})

        # Pending approvals count
        pending = GoalSheet.objects.filter(
            status=GoalSheet.STATUS_SUBMITTED,
            employee__manager=request.user
        ).count()

        return render(request, 'manager/dashboard.html', {
            'team_data': team_data,
            'active_cycle': active_cycle,
            'pending': pending,
        })


class SheetReviewView(ManagerRequiredMixin, View):
    def get(self, request, pk):
        sheet = get_object_or_404(GoalSheet, pk=pk)
        if not (request.user.is_admin or sheet.employee.manager_id == request.user.id):
            messages.error(request, 'Not authorized.')
            return redirect('manager:dashboard')
        goals = sheet.goals.all().select_related('thrust_area')
        return render(request, 'manager/sheet_review.html', {'sheet': sheet, 'goals': goals})

    def post(self, request, pk):
        sheet = get_object_or_404(GoalSheet, pk=pk)
        if not (request.user.is_admin or sheet.employee.manager_id == request.user.id):
            messages.error(request, 'Not authorized.')
            return redirect('manager:dashboard')

        action = request.POST.get('action')

        if action == 'approve':
            if sheet.status != GoalSheet.STATUS_SUBMITTED:
                messages.error(request, 'Only submitted sheets can be approved.')
                return redirect('manager:sheet_review', pk=pk)
            sheet.status = GoalSheet.STATUS_APPROVED
            sheet.approved_at = timezone.now()
            sheet.approved_by = request.user
            sheet.is_locked = True
            sheet.save()
            AuditLog.log(user=request.user, action=AuditLog.ACTION_APPROVE, goal_sheet=sheet)
            AuditLog.log(user=request.user, action=AuditLog.ACTION_LOCK, goal_sheet=sheet)
            messages.success(request, f"Goals approved and locked for {sheet.employee.get_full_name()}.")
            return redirect('manager:dashboard')

        elif action == 'return':
            remark = request.POST.get('return_remark', '').strip()
            if not remark:
                messages.error(request, 'Please provide a remark when returning goals.')
                return redirect('manager:sheet_review', pk=pk)
            sheet.status = GoalSheet.STATUS_RETURNED
            sheet.returned_at = timezone.now()
            sheet.return_remark = remark
            sheet.save()
            AuditLog.log(user=request.user, action=AuditLog.ACTION_RETURN, goal_sheet=sheet, extra_notes=remark)
            messages.success(request, 'Goals returned for rework.')
            return redirect('manager:dashboard')

        elif action == 'save_edits':
            # Inline edit of targets/weightages
            goals = sheet.goals.all()
            for goal in goals:
                new_target = request.POST.get(f'target_{goal.pk}')
                new_weightage = request.POST.get(f'weightage_{goal.pk}')
                changed = False
                if new_target is not None:
                    try:
                        val = float(new_target)
                        if goal.target != val:
                            AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_TARGET,
                                         goal_sheet=sheet, goal=goal,
                                         field_changed='target', old_value=goal.target, new_value=val)
                            goal.target = val
                            changed = True
                    except (ValueError, TypeError):
                        pass
                if new_weightage is not None:
                    try:
                        val = float(new_weightage)
                        if float(goal.weightage) != val:
                            AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_WEIGHT,
                                         goal_sheet=sheet, goal=goal,
                                         field_changed='weightage', old_value=goal.weightage, new_value=val)
                            goal.weightage = val
                            changed = True
                    except (ValueError, TypeError):
                        pass
                if changed:
                    goal.save(update_fields=['target', 'weightage'])
            messages.success(request, 'Edits saved successfully.')
            return redirect('manager:sheet_review', pk=pk)

        return redirect('manager:sheet_review', pk=pk)


class SheetApproveView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        return redirect('manager:sheet_review', pk=pk)


class SheetReturnView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        return redirect('manager:sheet_review', pk=pk)


class GoalInlineEditView(ManagerRequiredMixin, View):
    def post(self, request, sheet_pk, goal_pk):
        return redirect('manager:sheet_review', pk=sheet_pk)


class CheckInView(ManagerRequiredMixin, View):
    def get(self, request, employee_pk, cycle_pk):
        employee = get_object_or_404(User, pk=employee_pk)
        cycle = get_object_or_404(GoalCycle, pk=cycle_pk)

        if not (request.user.is_admin or employee.manager_id == request.user.id):
            messages.error(request, 'Not authorized.')
            return redirect('manager:dashboard')

        sheet = GoalSheet.objects.filter(employee=employee, cycle=cycle).first()
        checkin = ManagerCheckIn.objects.filter(employee=employee, cycle=cycle).first()
        achievements = []
        if sheet:
            for goal in sheet.goals.all():
                ach = QuarterlyAchievement.objects.filter(goal=goal, cycle=cycle).first()
                achievements.append({'goal': goal, 'achievement': ach})

        return render(request, 'manager/checkin_form.html', {
            'employee': employee,
            'cycle': cycle,
            'sheet': sheet,
            'checkin': checkin,
            'achievements': achievements,
        })

    def post(self, request, employee_pk, cycle_pk):
        employee = get_object_or_404(User, pk=employee_pk)
        cycle = get_object_or_404(GoalCycle, pk=cycle_pk)

        if not (request.user.is_admin or employee.manager_id == request.user.id):
            messages.error(request, 'Not authorized.')
            return redirect('manager:dashboard')

        comment = request.POST.get('comment', '').strip()
        is_complete = request.POST.get('is_complete') == 'on'

        checkin, _ = ManagerCheckIn.objects.update_or_create(
            employee=employee,
            cycle=cycle,
            defaults={
                'manager': request.user,
                'comment': comment,
                'is_complete': is_complete,
            }
        )
        AuditLog.log(user=request.user, action=AuditLog.ACTION_CHECKIN,
                     extra_notes=f"Check-in for {employee.get_full_name()} in {cycle.name}")
        messages.success(request, 'Check-in saved successfully.')
        return redirect('manager:check_in_list')


class CheckInListView(ManagerRequiredMixin, View):
    def get(self, request):
        cycles = GoalCycle.objects.order_by('-start_date')[:6]
        team = User.objects.filter(manager=request.user, role='employee')

        data = []
        for cycle in cycles:
            cycle_data = []
            for emp in team:
                checkin = ManagerCheckIn.objects.filter(employee=emp, cycle=cycle).first()
                sheet = GoalSheet.objects.filter(employee=emp, cycle=cycle).first()
                cycle_data.append({'employee': emp, 'checkin': checkin, 'sheet': sheet})
            if cycle_data:
                data.append({'cycle': cycle, 'entries': cycle_data})

        return render(request, 'manager/checkin_list.html', {'data': data})
