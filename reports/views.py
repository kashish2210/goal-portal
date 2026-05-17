import csv
from django.http import HttpResponse
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from goals.models import QuarterlyAchievement, GoalCycle, GoalSheet, Goal, ManagerCheckIn
from django.contrib.auth import get_user_model

User = get_user_model()


class AchievementReportView(LoginRequiredMixin, View):
    def get(self, request):
        cycles = GoalCycle.objects.order_by('-start_date')
        selected_cycle_id = request.GET.get('cycle')
        selected_cycle = None
        rows = []

        if selected_cycle_id:
            try:
                selected_cycle = GoalCycle.objects.get(pk=selected_cycle_id)
                qs = QuarterlyAchievement.objects.filter(
                    cycle=selected_cycle
                ).select_related('goal__goal_sheet__employee__department', 'goal__thrust_area')
                for ach in qs:
                    goal = ach.goal
                    emp = goal.goal_sheet.employee
                    score_pct = f"{float(ach.computed_score) * 100:.1f}%" if ach.computed_score is not None else "N/A"
                    rows.append({
                        'employee': emp,
                        'goal': goal,
                        'achievement': ach,
                        'score_pct': score_pct,
                    })
            except GoalCycle.DoesNotExist:
                messages.error(request, 'Cycle not found.')

        return render(request, 'reports/achievement.html', {
            'cycles': cycles,
            'selected_cycle': selected_cycle,
            'rows': rows,
        })


class AchievementExportView(LoginRequiredMixin, View):
    def get(self, request):
        cycle_id = request.GET.get('cycle')
        if not cycle_id:
            return HttpResponse('Missing cycle parameter', status=400)
        try:
            cycle = GoalCycle.objects.get(pk=cycle_id)
        except GoalCycle.DoesNotExist:
            return HttpResponse('Cycle not found', status=404)

        qs = QuarterlyAchievement.objects.filter(cycle=cycle).select_related(
            'goal__goal_sheet__employee', 'goal__thrust_area')

        filename = f"achievement_{cycle.name.replace(' ', '_')}.csv"
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(resp)
        writer.writerow(['Employee', 'Employee ID', 'Manager', 'Department',
                         'Cycle', 'Goal Title', 'UoM', 'Target', 'Actual', 'Score(%)', 'Status', 'Weightage'])

        for row in qs:
            goal = row.goal
            emp = goal.goal_sheet.employee
            mgr = emp.manager.get_full_name() if emp.manager else ''
            dept = emp.department.name if emp.department else ''
            score = f"{float(row.computed_score) * 100:.2f}" if row.computed_score is not None else ''
            writer.writerow([
                emp.get_full_name(), emp.employee_id or emp.username, mgr, dept,
                cycle.name, goal.title, goal.get_uom_display(), goal.target or '',
                row.actual or row.actual_date or '', score, row.get_status_display(), f"{goal.weightage}"
            ])
        return resp


class CompletionDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        cycles = GoalCycle.objects.order_by('-start_date')[:6]
        data = []
        for c in cycles:
            total_employees = User.objects.filter(role='employee').count()
            sheets_submitted = GoalSheet.objects.filter(cycle=c).exclude(status=GoalSheet.STATUS_DRAFT).count()
            sheets_approved = GoalSheet.objects.filter(cycle=c, status=GoalSheet.STATUS_APPROVED).count()
            checkins_done = ManagerCheckIn.objects.filter(cycle=c, is_complete=True).count()
            data.append({
                'cycle': c,
                'total_employees': total_employees,
                'sheets_submitted': sheets_submitted,
                'sheets_approved': sheets_approved,
                'checkins_done': checkins_done,
            })
        return render(request, 'reports/completion.html', {'data': data})
