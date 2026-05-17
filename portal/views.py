from django.views.generic import View
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
import csv, uuid
from django.http import HttpResponse
from django.db.models import Q

from goals.models import GoalSheet, GoalCycle, AuditLog, SharedGoalTemplate, ThrustArea, Department, Goal

User = get_user_model()


class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin:
            messages.error(request, 'Admin access required.')
            return redirect('goals:sheet_list')
        return super().dispatch(request, *args, **kwargs)


class AdminDashboardView(AdminRequiredMixin, View):
    def get(self, request):
        total_users = User.objects.filter(role='employee').count()
        total_sheets = GoalSheet.objects.count()
        approved = GoalSheet.objects.filter(status=GoalSheet.STATUS_APPROVED).count()
        pending = GoalSheet.objects.filter(status=GoalSheet.STATUS_SUBMITTED).count()
        active_cycle = GoalCycle.objects.filter(is_active=True).order_by('-start_date').first()
        recent_logs = AuditLog.objects.select_related('user', 'goal_sheet').order_by('-timestamp')[:10]
        return render(request, 'portal/dashboard.html', {
            'total_users': total_users,
            'total_sheets': total_sheets,
            'approved': approved,
            'pending': pending,
            'active_cycle': active_cycle,
            'recent_logs': recent_logs,
        })


# ── Cycle Management ──────────────────────────────────────────────────────────

class CycleListView(AdminRequiredMixin, View):
    def get(self, request):
        cycles = GoalCycle.objects.all().order_by('-start_date')
        return render(request, 'portal/cycle_list.html', {'cycles': cycles})


class CycleCreateView(AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'portal/cycle_form.html', {'action': 'Create'})

    def post(self, request):
        name = request.POST.get('name', '').strip()
        phase = request.POST.get('phase', '')
        fiscal_year = request.POST.get('fiscal_year', '').strip()
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_active = request.POST.get('is_active') == 'on'

        if not all([name, phase, fiscal_year, start_date, end_date]):
            messages.error(request, 'All fields are required.')
            return render(request, 'portal/cycle_form.html', {'action': 'Create', 'post': request.POST})

        GoalCycle.objects.create(
            name=name, phase=phase, fiscal_year=fiscal_year,
            start_date=start_date, end_date=end_date,
            is_active=is_active, created_by=request.user
        )
        messages.success(request, f'Cycle "{name}" created successfully.')
        return redirect('portal:cycle_list')


class CycleEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        cycle = get_object_or_404(GoalCycle, pk=pk)
        return render(request, 'portal/cycle_form.html', {'action': 'Edit', 'cycle': cycle})

    def post(self, request, pk):
        cycle = get_object_or_404(GoalCycle, pk=pk)
        cycle.name = request.POST.get('name', cycle.name).strip()
        cycle.phase = request.POST.get('phase', cycle.phase)
        cycle.fiscal_year = request.POST.get('fiscal_year', cycle.fiscal_year).strip()
        cycle.start_date = request.POST.get('start_date', cycle.start_date)
        cycle.end_date = request.POST.get('end_date', cycle.end_date)
        cycle.is_active = request.POST.get('is_active') == 'on'
        cycle.save()
        messages.success(request, f'Cycle "{cycle.name}" updated.')
        return redirect('portal:cycle_list')


class CycleToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        cycle = get_object_or_404(GoalCycle, pk=pk)
        cycle.is_active = not cycle.is_active
        cycle.save()
        state = 'activated' if cycle.is_active else 'deactivated'
        messages.success(request, f'Cycle "{cycle.name}" {state}.')
        return redirect('portal:cycle_list')


# ── All Sheets ────────────────────────────────────────────────────────────────

class AllSheetsView(AdminRequiredMixin, View):
    def get(self, request):
        cycle_id = request.GET.get('cycle')
        status_filter = request.GET.get('status', '')
        sheets = GoalSheet.objects.all().select_related('employee', 'cycle', 'approved_by')
        if cycle_id:
            sheets = sheets.filter(cycle_id=cycle_id)
        if status_filter:
            sheets = sheets.filter(status=status_filter)
        sheets = sheets.order_by('-created_at')
        cycles = GoalCycle.objects.all().order_by('-start_date')
        return render(request, 'portal/all_sheets.html', {
            'sheets': sheets,
            'cycles': cycles,
            'status_choices': GoalSheet.STATUS_CHOICES,
            'selected_cycle': cycle_id,
            'selected_status': status_filter,
        })


class SheetUnlockView(AdminRequiredMixin, View):
    def post(self, request, pk):
        sheet = get_object_or_404(GoalSheet, pk=pk)
        sheet.is_locked = False
        sheet.save()
        AuditLog.log(user=request.user, action=AuditLog.ACTION_UNLOCK, goal_sheet=sheet,
                     extra_notes='Admin unlocked the sheet.')
        messages.success(request, f'Sheet for {sheet.employee.get_full_name()} has been unlocked.')
        return redirect('portal:all_sheets')


# ── Users ─────────────────────────────────────────────────────────────────────

class UserListView(AdminRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        role_filter = request.GET.get('role', '')
        dept_filter = request.GET.get('dept', '')
        users = User.objects.all().select_related('department', 'manager').order_by('role', 'last_name')
        if q:
            users = users.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(username__icontains=q) | Q(email__icontains=q) |
                Q(employee_id__icontains=q)
            )
        if role_filter:
            users = users.filter(role=role_filter)
        if dept_filter:
            users = users.filter(department_id=dept_filter)

        # Stats
        stats = {
            'total': User.objects.count(),
            'employees': User.objects.filter(role='employee').count(),
            'managers': User.objects.filter(role='manager').count(),
            'admins': User.objects.filter(role='admin').count(),
        }
        departments = Department.objects.all()
        return render(request, 'portal/user_list.html', {
            'users': users,
            'q': q,
            'role_filter': role_filter,
            'dept_filter': dept_filter,
            'role_choices': User.ROLE_CHOICES,
            'departments': departments,
            'stats': stats,
        })


class UserCreateView(AdminRequiredMixin, View):
    def get(self, request):
        managers = User.objects.filter(role='manager').select_related('department')
        departments = Department.objects.all()
        return render(request, 'portal/user_create.html', {
            'managers': managers,
            'departments': departments,
            'role_choices': User.ROLE_CHOICES,
        })

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'employee')
        employee_id = request.POST.get('employee_id', '').strip()
        phone = request.POST.get('phone', '').strip()
        dept_id = request.POST.get('department') or None
        mgr_id = request.POST.get('manager') or None

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return redirect('portal:user_create')
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is already taken.')
            return redirect('portal:user_create')
        if not employee_id:
            employee_id = f'EMP-{uuid.uuid4().hex[:8].upper()}'

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            employee_id=employee_id,
            phone=phone,
            department_id=dept_id,
            manager_id=mgr_id,
        )
        messages.success(request, f'User "{username}" created successfully.')
        return redirect('portal:user_edit', pk=user.pk)


class UserEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        managers = User.objects.filter(role='manager').exclude(pk=pk)
        departments = Department.objects.all()
        sheets = GoalSheet.objects.filter(employee=target).select_related('cycle').order_by('-created_at')[:5]
        return render(request, 'portal/user_edit.html', {
            'target': target,
            'managers': managers,
            'departments': departments,
            'role_choices': User.ROLE_CHOICES,
            'sheets': sheets,
        })

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        target.first_name = request.POST.get('first_name', target.first_name)
        target.last_name = request.POST.get('last_name', target.last_name)
        target.email = request.POST.get('email', target.email)
        target.role = request.POST.get('role', target.role)
        target.employee_id = request.POST.get('employee_id', target.employee_id)
        target.phone = request.POST.get('phone', target.phone)
        dept_id = request.POST.get('department')
        mgr_id = request.POST.get('manager')
        target.department_id = dept_id if dept_id else None
        target.manager_id = mgr_id if mgr_id else None
        target.save()
        messages.success(request, f'User {target.username} updated successfully.')
        return redirect('portal:user_edit', pk=pk)


class UserResetPasswordView(AdminRequiredMixin, View):
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        new_password = request.POST.get('new_password', '').strip()
        if not new_password or len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return redirect('portal:user_edit', pk=pk)
        target.set_password(new_password)
        target.save()
        messages.success(request, f'Password for {target.username} has been reset.')
        return redirect('portal:user_edit', pk=pk)


class UserToggleActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('portal:user_list')
        target.is_active = not target.is_active
        target.save()
        state = 'activated' if target.is_active else 'deactivated'
        messages.success(request, f'User {target.username} has been {state}.')
        return redirect('portal:user_list')


# ── Departments ───────────────────────────────────────────────────────────────

class DepartmentListView(AdminRequiredMixin, View):
    def get(self, request):
        depts = Department.objects.all().prefetch_related('members', 'thrust_areas')
        return render(request, 'portal/department_list.html', {'depts': depts})


class ThrustAreaListView(AdminRequiredMixin, View):
    def get(self, request):
        areas = ThrustArea.objects.all().select_related('department')
        depts = Department.objects.all()
        return render(request, 'portal/thrust_area_list.html', {'areas': areas, 'depts': depts})

    def post(self, request):
        name = request.POST.get('name', '').strip()
        dept_id = request.POST.get('department')
        if not name:
            messages.error(request, 'Name is required.')
            return redirect('portal:thrust_area_list')
        ThrustArea.objects.get_or_create(
            name=name,
            department_id=dept_id if dept_id else None,
        )
        messages.success(request, f'Thrust Area "{name}" created.')
        return redirect('portal:thrust_area_list')


# ── Shared Goals ──────────────────────────────────────────────────────────────

class SharedGoalListView(AdminRequiredMixin, View):
    def get(self, request):
        templates = SharedGoalTemplate.objects.all().select_related('thrust_area', 'cycle', 'department', 'pushed_by')
        return render(request, 'portal/shared_goal_list.html', {'templates': templates})


class SharedGoalPushView(AdminRequiredMixin, View):
    def get(self, request):
        cycles = GoalCycle.objects.all().order_by('-start_date')
        depts = Department.objects.all()
        thrust_areas = ThrustArea.objects.all().select_related('department')
        uom_choices = SharedGoalTemplate.UOM_CHOICES
        return render(request, 'portal/shared_goal_push.html', {
            'cycles': cycles, 'depts': depts,
            'thrust_areas': thrust_areas, 'uom_choices': uom_choices,
        })

    def post(self, request):
        title = request.POST.get('title', '').strip()
        thrust_id = request.POST.get('thrust_area')
        uom = request.POST.get('uom')
        target = request.POST.get('target') or None
        target_date = request.POST.get('target_date') or None
        cycle_id = request.POST.get('cycle')
        dept_id = request.POST.get('department')

        if not all([title, thrust_id, uom, cycle_id, dept_id]):
            messages.error(request, 'All required fields must be filled.')
            return redirect('portal:shared_goal_push')

        template = SharedGoalTemplate.objects.create(
            title=title, thrust_area_id=thrust_id, uom=uom,
            target=target, target_date=target_date,
            cycle_id=cycle_id, department_id=dept_id,
            pushed_by=request.user,
        )

        # Push to all employees in the department with an approved/draft sheet
        dept_employees = User.objects.filter(department_id=dept_id, role='employee')
        pushed_count = 0
        cycle = GoalCycle.objects.get(pk=cycle_id)
        for emp in dept_employees:
            sheet = GoalSheet.objects.filter(employee=emp, cycle=cycle).first()
            if not sheet:
                sheet = GoalSheet.objects.create(employee=emp, cycle=cycle)
            if sheet.is_locked:
                continue
            # Avoid duplicate push
            if not Goal.objects.filter(goal_sheet=sheet, shared_template=template).exists():
                Goal.objects.create(
                    goal_sheet=sheet,
                    thrust_area_id=thrust_id,
                    title=title,
                    uom=uom,
                    target=target,
                    target_date=target_date,
                    weightage=10,  # Default; employee can adjust
                    is_shared=True,
                    shared_template=template,
                    order=100,
                )
                pushed_count += 1

        messages.success(request, f'Shared goal pushed to {pushed_count} employee(s).')
        return redirect('portal:shared_goal_list')


class SharedGoalEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        template = get_object_or_404(SharedGoalTemplate, pk=pk)
        return render(request, 'portal/shared_goal_edit.html', {'template': template})


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogView(AdminRequiredMixin, View):
    def get(self, request):
        logs = AuditLog.objects.all().select_related('user', 'goal_sheet', 'goal').order_by('-timestamp')[:200]
        return render(request, 'portal/audit_log.html', {'logs': logs})


class AuditLogExportView(AdminRequiredMixin, View):
    def get(self, request):
        logs = AuditLog.objects.all().select_related('user', 'goal_sheet').order_by('-timestamp')
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="audit_log.csv"'
        writer = csv.writer(resp)
        writer.writerow(['Timestamp', 'User', 'Action', 'Goal Sheet', 'Field Changed', 'Old Value', 'New Value', 'Notes'])
        for log in logs:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else '',
                log.get_action_display(),
                str(log.goal_sheet) if log.goal_sheet else '',
                log.field_changed,
                log.old_value,
                log.new_value,
                log.extra_notes,
            ])
        return resp


# ── Impersonate ───────────────────────────────────────────────────────────────

class ImpersonateListView(AdminRequiredMixin, View):
    """Show list of users the admin can impersonate."""
    def get(self, request):
        if request.session.get('impersonating'):
            messages.error(request, 'Stop your current impersonation first.')
            return redirect('portal:dashboard')
        users = User.objects.exclude(pk=request.user.pk).order_by('role', 'last_name')
        return render(request, 'portal/impersonate_list.html', {'users': users})


class ImpersonateStartView(AdminRequiredMixin, View):
    """Admin logs in AS another user (stored in session)."""
    def post(self, request, pk):
        if request.session.get('impersonating'):
            messages.error(request, 'Already impersonating. Stop first.')
            return redirect('portal:dashboard')
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, 'You cannot impersonate yourself.')
            return redirect('portal:impersonate_list')

        # Store real admin id, then switch the session user
        request.session['impersonating'] = True
        request.session['real_user_id'] = request.user.pk
        request.session['real_user_name'] = request.user.username

        from django.contrib.auth import login
        login(request, target, backend='django.contrib.auth.backends.ModelBackend')

        messages.warning(request,
            f'You are now viewing the portal as "{target.username}" ({target.get_role_display()}). '
            f'Click "Stop Impersonating" to return.')

        # Redirect to role-appropriate home
        if target.is_admin:
            return redirect('portal:dashboard')
        elif target.is_manager:
            return redirect('manager:dashboard')
        return redirect('goals:sheet_list')


class ImpersonateStopView(LoginRequiredMixin, View):
    """Restore the real admin session."""
    def get(self, request):
        return self._stop(request)

    def post(self, request):
        return self._stop(request)

    def _stop(self, request):
        real_id = request.session.pop('real_user_id', None)
        request.session.pop('impersonating', None)
        request.session.pop('real_user_name', None)

        if real_id:
            real_user = get_object_or_404(User, pk=real_id)
            from django.contrib.auth import login
            login(request, real_user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Back to your admin account ({real_user.username}).')
            return redirect('portal:dashboard')

        messages.info(request, 'You were not impersonating anyone.')
        return redirect('/')
