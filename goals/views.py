from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import GoalSheet, GoalCycle, AuditLog, Goal, QuarterlyAchievement
from .forms import GoalSheetForm, GoalFormSet, QuarterlyAchievementForm


@login_required
def sheet_list(request):
	"""List goal sheets for the current user (employee)."""
	sheets = GoalSheet.objects.filter(employee=request.user).order_by('-created_at')
	return render(request, 'goals/sheet_list.html', {'sheets': sheets})


@login_required
def sheet_create_or_edit(request, pk=None):
	"""Create a new GoalSheet or edit an existing draft.

	Handles inline goals via a formset.
	"""
	if pk:
		sheet = get_object_or_404(GoalSheet, pk=pk, employee=request.user)
		if sheet.is_locked:
			messages.error(request, 'This goal sheet is locked and cannot be edited.')
			return redirect('goals:sheet_detail', pk=sheet.pk)
	else:
		# Find active goal-setting cycle
		try:
			cycle = GoalCycle.objects.filter(is_active=True, phase=GoalCycle.PHASE_GOAL_SETTING).latest('start_date')
		except GoalCycle.DoesNotExist:
			messages.error(request, 'No active Goal Setting cycle is available.')
			return redirect('goals:sheet_list')
		sheet = GoalSheet(employee=request.user, cycle=cycle)

	if request.method == 'POST':
		form = GoalSheetForm(request.POST, instance=sheet)
		formset = GoalFormSet(request.POST, instance=sheet)
		if form.is_valid() and formset.is_valid():
			sheet = form.save(commit=False)
			sheet.employee = request.user
			# Snapshot existing goals for audit
			original = {}
			if sheet.pk:
				for g in sheet.goals.all():
					original[g.pk] = {
						'title': g.title,
						'target': g.target,
						'weightage': g.weightage,
					}

			sheet.save()
			formset.instance = sheet
			saved = formset.save()

			# Handle deletions
			for f in formset.deleted_forms:
				try:
					inst = f.instance
					AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_GOAL,
								 goal_sheet=sheet, goal=inst,
								 extra_notes='Deleted goal')
				except Exception:
					pass

			# Log new and changed goals
			for g in sheet.goals.all():
				if g.pk not in original:
					AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_GOAL,
								 goal_sheet=sheet, goal=g,
								 extra_notes='Created goal')
					continue
				orig = original[g.pk]
				if orig['weightage'] != g.weightage:
					AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_WEIGHT,
								 goal_sheet=sheet, goal=g,
								 field_changed='weightage', old_value=orig['weightage'], new_value=g.weightage)
				if orig['target'] != g.target:
					AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_TARGET,
								 goal_sheet=sheet, goal=g,
								 field_changed='target', old_value=orig['target'], new_value=g.target)

			messages.success(request, 'Goal sheet saved.')
			return redirect('goals:sheet_detail', pk=sheet.pk)
	else:
		form = GoalSheetForm(instance=sheet)
		formset = GoalFormSet(instance=sheet)

	return render(request, 'goals/sheet_create.html', {
		'form': form, 'formset': formset, 'sheet': sheet
	})


@login_required
def sheet_detail(request, pk):
	sheet = get_object_or_404(GoalSheet, pk=pk)
	return render(request, 'goals/sheet_detail.html', {'sheet': sheet})


@login_required
def sheet_submit(request, pk):
	sheet = get_object_or_404(GoalSheet, pk=pk, employee=request.user)
	can, reason = sheet.can_submit()
	if not can:
		messages.error(request, reason)
		return redirect('goals:sheet_edit', pk=sheet.pk)

	sheet.status = GoalSheet.STATUS_SUBMITTED
	sheet.submitted_at = timezone.now()
	sheet.save()
	AuditLog.log(user=request.user, action=AuditLog.ACTION_SUBMIT, goal_sheet=sheet)
	messages.success(request, 'Goal sheet submitted for approval.')
	return redirect('goals:sheet_detail', pk=sheet.pk)


# -------------------- Manager review flows --------------------

@login_required
def manager_sheet_list(request):
	"""List submitted sheets for manager's direct reports."""
	if not request.user.is_manager and not request.user.is_admin:
		messages.error(request, 'Access denied.')
		return redirect('goals:sheet_list')

	sheets = GoalSheet.objects.filter(status=GoalSheet.STATUS_SUBMITTED,
									  employee__manager=request.user).order_by('submitted_at')
	return render(request, 'manager/sheet_list.html', {'sheets': sheets})


@login_required
def manager_sheet_review(request, pk):
	"""Manager reviews a submitted sheet; can edit targets/weightages inline."""
	sheet = get_object_or_404(GoalSheet, pk=pk)
	# authorization: manager of the employee or admin
	if not (request.user.is_admin or sheet.employee.manager_id == request.user.id):
		messages.error(request, 'You are not authorized to review this sheet.')
		return redirect('goals:sheet_list')

	if sheet.status != GoalSheet.STATUS_SUBMITTED:
		messages.warning(request, 'Only submitted sheets can be reviewed.')

	if request.method == 'POST':
		formset = GoalFormSet(request.POST, instance=sheet)
		if formset.is_valid():
			# detect changes for audit
			for f in formset.forms:
				if not f.instance.pk:
					continue
				orig = type(f.instance).objects.get(pk=f.instance.pk)
				new_weight = f.cleaned_data.get('weightage')
				new_target = f.cleaned_data.get('target')
				if new_weight is not None and orig.weightage != new_weight:
					AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_WEIGHT,
								 goal_sheet=sheet, goal=orig,
								 field_changed='weightage', old_value=orig.weightage, new_value=new_weight)
				if new_target is not None and orig.target != new_target:
					AuditLog.log(user=request.user, action=AuditLog.ACTION_EDIT_TARGET,
								 goal_sheet=sheet, goal=orig,
								 field_changed='target', old_value=orig.target, new_value=new_target)

			formset.save()
			messages.success(request, 'Changes saved.')
			return redirect('goals:manager_sheet_review', pk=sheet.pk)
	else:
		formset = GoalFormSet(instance=sheet)

	# Build pairs of (form, goal, original) for improved UI/diffs
	goals_list = list(sheet.goals.all())
	pairs = []
	for idx, f in enumerate(formset.forms):
		g = goals_list[idx] if idx < len(goals_list) else None
		orig = {'target': g.target if g else None, 'weightage': g.weightage if g else None}
		pairs.append({'form': f, 'goal': g, 'orig': orig})

	return render(request, 'manager/sheet_review.html', {'sheet': sheet, 'pairs': pairs, 'formset': formset})


@login_required
def manager_sheet_approve(request, pk):
	sheet = get_object_or_404(GoalSheet, pk=pk)
	if not (request.user.is_admin or sheet.employee.manager_id == request.user.id):
		messages.error(request, 'Not authorized.')
		return redirect('goals:sheet_list')
	if sheet.status != GoalSheet.STATUS_SUBMITTED:
		messages.error(request, 'Only submitted sheets can be approved.')
		return redirect('goals:manager_sheet_review', pk=pk)
	# Approve must be a POST to avoid accidental approvals
	if request.method != 'POST':
		messages.error(request, 'Approve must be submitted via the review form.')
		return redirect('goals:manager_sheet_review', pk=pk)

	sheet.status = GoalSheet.STATUS_APPROVED
	sheet.approved_at = timezone.now()
	sheet.approved_by = request.user
	sheet.lock()
	sheet.save()
	AuditLog.log(user=request.user, action=AuditLog.ACTION_APPROVE, goal_sheet=sheet)
	AuditLog.log(user=request.user, action=AuditLog.ACTION_LOCK, goal_sheet=sheet)
	messages.success(request, 'Sheet approved and locked.')
	return redirect('goals:manager_sheet_list')


@login_required
def manager_sheet_return(request, pk):
	sheet = get_object_or_404(GoalSheet, pk=pk)
	if not (request.user.is_admin or sheet.employee.manager_id == request.user.id):
		messages.error(request, 'Not authorized.')
		return redirect('goals:sheet_list')

	if request.method == 'POST':
		remark = request.POST.get('return_remark', '')
		sheet.status = GoalSheet.STATUS_RETURNED
		sheet.returned_at = timezone.now()
		sheet.return_remark = remark
		sheet.save()
		AuditLog.log(user=request.user, action=AuditLog.ACTION_RETURN, goal_sheet=sheet, extra_notes=remark)
		messages.success(request, 'Sheet returned for rework.')
		return redirect('goals:manager_sheet_list')

	return render(request, 'manager/confirm_return.html', {'sheet': sheet})


@login_required
def sheet_checkin(request, sheet_pk, cycle_pk):
	"""Employee logs quarterly actuals for their goals."""
	sheet = get_object_or_404(GoalSheet, pk=sheet_pk, employee=request.user)
	cycle = get_object_or_404(GoalCycle, pk=cycle_pk)

	if sheet.status != GoalSheet.STATUS_APPROVED:
		messages.error(request, 'You can only enter check-in data for approved goal sheets.')
		return redirect('goals:sheet_detail', pk=sheet_pk)

	goals = sheet.goals.all().select_related('thrust_area')

	if request.method == 'POST':
		for goal in goals:
			actual = request.POST.get(f'actual_{goal.pk}') or None
			actual_date = request.POST.get(f'actual_date_{goal.pk}') or None
			status = request.POST.get(f'status_{goal.pk}', goal.STATUS_NOT_STARTED)
			notes = request.POST.get(f'notes_{goal.pk}', '')
			QuarterlyAchievement.objects.update_or_create(
				goal=goal,
				cycle=cycle,
				defaults={
					'actual': actual,
					'actual_date': actual_date,
					'status': status,
					'notes': notes,
					'updated_by': request.user,
				}
			)
		AuditLog.log(user=request.user, action=AuditLog.ACTION_ACH_UPDATE,
					 goal_sheet=sheet, extra_notes=f'Check-in for {cycle.name}')
		messages.success(request, 'Achievement data saved successfully.')
		return redirect('goals:sheet_detail', pk=sheet_pk)

	# Build goal+achievement pairs
	pairs = []
	for goal in goals:
		ach = QuarterlyAchievement.objects.filter(goal=goal, cycle=cycle).first()
		pairs.append({'goal': goal, 'achievement': ach})

	return render(request, 'goals/sheet_checkin.html', {
		'sheet': sheet,
		'cycle': cycle,
		'pairs': pairs,
		'status_choices': Goal.STATUS_CHOICES,
	})
