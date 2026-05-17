from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from django.apps import apps


# ─────────────────────────────────────────────
# DEPARTMENT
# ─────────────────────────────────────────────

class Department(models.Model):
	name        = models.CharField(max_length=120, unique=True)
	code        = models.CharField(max_length=20, unique=True, blank=True)
	description = models.TextField(blank=True)
	created_at  = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


# ─────────────────────────────────────────────
# CUSTOM USER
# ─────────────────────────────────────────────

class User(AbstractUser):
	ROLE_EMPLOYEE = 'employee'
	ROLE_MANAGER  = 'manager'
	ROLE_ADMIN    = 'admin'
	ROLE_CHOICES  = [
		(ROLE_EMPLOYEE, 'Employee'),
		(ROLE_MANAGER,  'Manager (L1)'),
		(ROLE_ADMIN,    'Admin / HR'),
	]

	role           = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
	department     = models.ForeignKey(
						 Department, null=True, blank=True,
						 on_delete=models.SET_NULL,
						 related_name='members')
	manager        = models.ForeignKey(
						 'self', null=True, blank=True,
						 on_delete=models.SET_NULL,
						 related_name='direct_reports',
						 limit_choices_to={'role': 'manager'})
	employee_id    = models.CharField(max_length=30, unique=True, blank=True)
	phone          = models.CharField(max_length=20, blank=True)
	profile_picture = models.ImageField(
						 upload_to='profiles/', null=True, blank=True)
	date_joined_org = models.DateField(null=True, blank=True)

	class Meta:
		ordering = ['last_name', 'first_name']

	def __str__(self):
		return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

	@property
	def is_employee(self):
		return self.role == self.ROLE_EMPLOYEE

	@property
	def is_manager(self):
		return self.role == self.ROLE_MANAGER

	@property
	def is_admin(self):
		return self.role == self.ROLE_ADMIN


# ─────────────────────────────────────────────
# THRUST AREA  (Goal Category)
# ─────────────────────────────────────────────

class ThrustArea(models.Model):
	name        = models.CharField(max_length=150)
	department  = models.ForeignKey(
					  Department, null=True, blank=True,
					  on_delete=models.SET_NULL,
					  related_name='thrust_areas',
					  help_text="Leave blank for org-wide thrust areas")
	description = models.TextField(blank=True)
	is_active   = models.BooleanField(default=True)
	created_at  = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']
		unique_together = ('name', 'department')

	def __str__(self):
		scope = self.department.name if self.department else 'Org-wide'
		return f"{self.name} [{scope}]"


# ─────────────────────────────────────────────
# GOAL CYCLE  (Phase / Quarter window)
# ─────────────────────────────────────────────

class GoalCycle(models.Model):
	PHASE_GOAL_SETTING = 'goal_setting'
	PHASE_Q1           = 'q1'
	PHASE_Q2           = 'q2'
	PHASE_Q3           = 'q3'
	PHASE_Q4           = 'q4'
	PHASE_CHOICES      = [
		(PHASE_GOAL_SETTING, 'Phase 1 — Goal Setting'),
		(PHASE_Q1,           'Q1 Check-in (July)'),
		(PHASE_Q2,           'Q2 Check-in (October)'),
		(PHASE_Q3,           'Q3 Check-in (January)'),
		(PHASE_Q4,           'Q4 / Annual (March–April)'),
	]

	name        = models.CharField(max_length=100)  # e.g. "FY 2025–26 Q1"
	phase       = models.CharField(max_length=20, choices=PHASE_CHOICES)
	fiscal_year = models.CharField(max_length=10, help_text="e.g. 2025-26")
	start_date  = models.DateField()
	end_date    = models.DateField()
	is_active   = models.BooleanField(default=False)
	created_by  = models.ForeignKey(
					  User, null=True, on_delete=models.SET_NULL,
					  related_name='cycles_created')
	created_at  = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-start_date']
		unique_together = ('phase', 'fiscal_year')

	def __str__(self):
		return f"{self.name} ({self.get_phase_display()})"

	@property
	def is_open(self):
		today = timezone.now().date()
		return self.is_active and self.start_date <= today <= self.end_date

	def clean(self):
		if self.start_date and self.end_date and self.start_date > self.end_date:
			raise ValidationError("Start date cannot be after end date.")


# ─────────────────────────────────────────────
# GOAL SHEET  (One per Employee per Cycle)
# ─────────────────────────────────────────────

class GoalSheet(models.Model):
	STATUS_DRAFT     = 'draft'
	STATUS_SUBMITTED = 'submitted'
	STATUS_APPROVED  = 'approved'
	STATUS_RETURNED  = 'returned'
	STATUS_CHOICES   = [
		(STATUS_DRAFT,     'Draft'),
		(STATUS_SUBMITTED, 'Submitted for Approval'),
		(STATUS_APPROVED,  'Approved'),
		(STATUS_RETURNED,  'Returned for Rework'),
	]

	employee      = models.ForeignKey(
						User, on_delete=models.PROTECT,
						related_name='goal_sheets',
						limit_choices_to={'role': 'employee'})
	cycle         = models.ForeignKey(
						GoalCycle, on_delete=models.PROTECT,
						related_name='goal_sheets')
	status        = models.CharField(
						max_length=20, choices=STATUS_CHOICES,
						default=STATUS_DRAFT)
	is_locked     = models.BooleanField(default=False)

	# Workflow timestamps
	submitted_at  = models.DateTimeField(null=True, blank=True)
	approved_at   = models.DateTimeField(null=True, blank=True)
	approved_by   = models.ForeignKey(
						User, null=True, blank=True,
						on_delete=models.SET_NULL,
						related_name='approved_sheets')
	returned_at   = models.DateTimeField(null=True, blank=True)
	return_remark = models.TextField(blank=True)

	created_at    = models.DateTimeField(auto_now_add=True)
	updated_at    = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		unique_together = ('employee', 'cycle')

	def __str__(self):
		return f"{self.employee.get_full_name()} — {self.cycle.name} [{self.get_status_display()}]"

	def clean(self):
		# A goal_setting cycle sheet should only be created in goal_setting phase
		if self.cycle and self.cycle.phase != GoalCycle.PHASE_GOAL_SETTING:
			raise ValidationError(
				"Goal Sheets can only be created during the Goal Setting phase.")

	# ── Computed helpers ──────────────────────

	@property
	def total_weightage(self):
		return self.goals.aggregate(
			total=models.Sum('weightage')
		)['total'] or Decimal('0')

	@property
	def goal_count(self):
		return self.goals.count()

	def can_submit(self):
		"""Check if the sheet is ready to submit."""
		if self.status != self.STATUS_DRAFT:
			return False, "Sheet is not in draft status."
		if self.goal_count == 0:
			return False, "Add at least one goal before submitting."
		if self.goal_count > 8:
			return False, "Maximum 8 goals allowed."
		if self.total_weightage != Decimal('100'):
			return False, f"Total weightage must be 100%. Current: {self.total_weightage}%"
		return True, "OK"

	def lock(self):
		self.is_locked = True
		self.save(update_fields=['is_locked'])

	def unlock(self):
		self.is_locked = False
		self.save(update_fields=['is_locked'])


# ─────────────────────────────────────────────
# SHARED GOAL TEMPLATE  (Admin/Manager → Dept KPI)
# ─────────────────────────────────────────────

class SharedGoalTemplate(models.Model):
	"""
	A departmental KPI that an Admin or Manager pushes to multiple employees.
	Recipients' Goals inherit title + target (read-only); only weightage is editable.
	"""
	UOM_NUMERIC_MIN = 'numeric_min'  # Higher is better (Sales Revenue)
	UOM_NUMERIC_MAX = 'numeric_max'  # Lower is better (TAT, Cost)
	UOM_PCT_MIN     = 'pct_min'      # % Higher is better
	UOM_PCT_MAX     = 'pct_max'      # % Lower is better
	UOM_TIMELINE    = 'timeline'     # Date-based completion
	UOM_ZERO        = 'zero'         # Zero = 100% success

	UOM_CHOICES = [
		(UOM_NUMERIC_MIN, 'Numeric — Higher is Better'),
		(UOM_NUMERIC_MAX, 'Numeric — Lower is Better'),
		(UOM_PCT_MIN,     '% — Higher is Better'),
		(UOM_PCT_MAX,     '% — Lower is Better'),
		(UOM_TIMELINE,    'Timeline (Date-based)'),
		(UOM_ZERO,        'Zero-based (0 = Success)'),
	]

	title        = models.CharField(max_length=200)
	description  = models.TextField(blank=True)
	thrust_area  = models.ForeignKey(
					   ThrustArea, on_delete=models.PROTECT,
					   related_name='shared_templates')
	uom          = models.CharField(max_length=20, choices=UOM_CHOICES)
	target       = models.DecimalField(
					   max_digits=14, decimal_places=2,
					   null=True, blank=True,
					   help_text="Numeric / % target (leave blank for Timeline/Zero)")
	target_date  = models.DateField(
					   null=True, blank=True,
					   help_text="Deadline for Timeline UoM")
	cycle        = models.ForeignKey(
					   GoalCycle, on_delete=models.PROTECT,
					   related_name='shared_templates')
	department   = models.ForeignKey(
					   Department, on_delete=models.PROTECT,
					   related_name='shared_templates')
	pushed_by    = models.ForeignKey(
					   User, on_delete=models.PROTECT,
					   related_name='shared_templates_created')
	created_at   = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"[Shared] {self.title} — {self.cycle.name}"


# ─────────────────────────────────────────────
# GOAL  (Individual goal on a GoalSheet)
# ─────────────────────────────────────────────

class Goal(models.Model):
	# Re-use UoM choices from SharedGoalTemplate for consistency
	UOM_NUMERIC_MIN = SharedGoalTemplate.UOM_NUMERIC_MIN
	UOM_NUMERIC_MAX = SharedGoalTemplate.UOM_NUMERIC_MAX
	UOM_PCT_MIN     = SharedGoalTemplate.UOM_PCT_MIN
	UOM_PCT_MAX     = SharedGoalTemplate.UOM_PCT_MAX
	UOM_TIMELINE    = SharedGoalTemplate.UOM_TIMELINE
	UOM_ZERO        = SharedGoalTemplate.UOM_ZERO
	UOM_CHOICES     = SharedGoalTemplate.UOM_CHOICES

	STATUS_NOT_STARTED = 'not_started'
	STATUS_ON_TRACK    = 'on_track'
	STATUS_COMPLETED   = 'completed'
	STATUS_CHOICES     = [
		(STATUS_NOT_STARTED, 'Not Started'),
		(STATUS_ON_TRACK,    'On Track'),
		(STATUS_COMPLETED,   'Completed'),
	]

	goal_sheet          = models.ForeignKey(
							  GoalSheet, on_delete=models.CASCADE,
							  related_name='goals')
	thrust_area         = models.ForeignKey(
							  ThrustArea, on_delete=models.PROTECT,
							  related_name='goals')
	title               = models.CharField(max_length=200)
	description         = models.TextField(blank=True)
	uom                 = models.CharField(max_length=20, choices=UOM_CHOICES)
	target              = models.DecimalField(
							  max_digits=14, decimal_places=2,
							  null=True, blank=True)
	target_date         = models.DateField(
							  null=True, blank=True,
							  help_text="Used when UoM is Timeline")
	weightage           = models.DecimalField(
							  max_digits=5, decimal_places=2,
							  validators=[
								  MinValueValidator(Decimal('10.00'),
									  message="Minimum weightage is 10%."),
								  MaxValueValidator(Decimal('100.00'),
									  message="Maximum weightage per goal is 100%.")
							  ])
	status              = models.CharField(
							  max_length=20, choices=STATUS_CHOICES,
							  default=STATUS_NOT_STARTED)
	order               = models.PositiveSmallIntegerField(default=0)

	# Shared goal linkage
	is_shared           = models.BooleanField(default=False)
	shared_template     = models.ForeignKey(
							  SharedGoalTemplate, null=True, blank=True,
							  on_delete=models.SET_NULL,
							  related_name='derived_goals')
	# Primary owner flag — only one goal per shared template is "primary"
	is_shared_primary   = models.BooleanField(default=False)

	created_at          = models.DateTimeField(auto_now_add=True)
	updated_at          = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['order', 'created_at']

	def __str__(self):
		return f"{self.title} ({self.weightage}%) — {self.goal_sheet.employee.username}"

	def clean(self):
		sheet = self.goal_sheet
		# Shared goals: title & target are read-only (enforced at form level too)
		if self.is_shared and self.shared_template:
			if self.title != self.shared_template.title:
				raise ValidationError(
					"Title of a shared goal cannot be changed.")
			if self.target != self.shared_template.target:
				raise ValidationError(
					"Target of a shared goal cannot be changed.")

		# Timeline UoM needs a date; numeric UoMs need a number
		if self.uom == self.UOM_TIMELINE and not self.target_date:
			raise ValidationError("Timeline goals require a target date.")
		if self.uom not in (self.UOM_TIMELINE, self.UOM_ZERO) and self.target is None:
			raise ValidationError("Numeric / % goals require a numeric target.")

		# Weightage total validation (checked on the sheet, but also guard here)
		if sheet.pk:
			existing_qs = sheet.goals.exclude(pk=self.pk)
			existing_total = existing_qs.aggregate(
				t=models.Sum('weightage'))['t'] or Decimal('0')
			new_total = existing_total + self.weightage
			if new_total > Decimal('100'):
				raise ValidationError(
					f"Adding this goal makes total weightage {new_total}% — exceeds 100%.")

			# Max 8 goals per sheet
			if not self.pk and existing_qs.count() >= 8:
				raise ValidationError("A goal sheet cannot have more than 8 goals.")

	# ── Score computation ─────────────────────

	def compute_score(self, actual=None, actual_date=None):
		"""
		Returns a score in range [0, 1] (multiply by 100 for %).
		Returns None if computation is not possible.
		"""
		if self.uom in (self.UOM_NUMERIC_MIN, self.UOM_PCT_MIN):
			if actual is None or self.target == 0:
				return None
			return min(Decimal(str(actual)) / self.target, Decimal('1'))

		elif self.uom in (self.UOM_NUMERIC_MAX, self.UOM_PCT_MAX):
			if actual is None or actual == 0:
				return None
			return min(self.target / Decimal(str(actual)), Decimal('1'))

		elif self.uom == self.UOM_TIMELINE:
			if actual_date is None or self.target_date is None:
				return None
			return Decimal('1') if actual_date <= self.target_date else Decimal('0')

		elif self.uom == self.UOM_ZERO:
			if actual is None:
				return None
			return Decimal('1') if actual == 0 else Decimal('0')

		return None

	def save(self, *args, **kwargs):
		# Detect changes for audit logging if sheet is locked
		AuditLog = apps.get_model('goals', 'AuditLog')
		if self.pk:
			orig = type(self).objects.filter(pk=self.pk).first()
		else:
			orig = None

		super().save(*args, **kwargs)

		try:
			sheet = self.goal_sheet
			if sheet.is_locked and orig:
				# title change
				if orig.title != self.title:
					AuditLog.log(user=None, action=AuditLog.ACTION_EDIT_GOAL,
								 goal_sheet=sheet, goal=self,
								 field_changed='title', old_value=orig.title, new_value=self.title,
								 extra_notes='Post-lock edit')
				if orig.target != self.target:
					AuditLog.log(user=None, action=AuditLog.ACTION_EDIT_TARGET,
								 goal_sheet=sheet, goal=self,
								 field_changed='target', old_value=orig.target, new_value=self.target,
								 extra_notes='Post-lock edit')
				if orig.weightage != self.weightage:
					AuditLog.log(user=None, action=AuditLog.ACTION_EDIT_WEIGHT,
								 goal_sheet=sheet, goal=self,
								 field_changed='weightage', old_value=orig.weightage, new_value=self.weightage,
								 extra_notes='Post-lock edit')
		except Exception:
			pass


# ─────────────────────────────────────────────
# QUARTERLY ACHIEVEMENT
# ─────────────────────────────────────────────

class QuarterlyAchievement(models.Model):
	"""
	One record per Goal per Check-in Cycle.
	Employees enter actuals; system computes score.
	"""
	goal            = models.ForeignKey(
						  Goal, on_delete=models.CASCADE,
						  related_name='achievements')
	cycle           = models.ForeignKey(
						  GoalCycle, on_delete=models.PROTECT,
						  related_name='achievements')
	actual          = models.DecimalField(
						  max_digits=14, decimal_places=2,
						  null=True, blank=True,
						  help_text="Numeric / % actual value")
	actual_date     = models.DateField(
						  null=True, blank=True,
						  help_text="Completion date for Timeline goals")
	status          = models.CharField(
						  max_length=20,
						  choices=Goal.STATUS_CHOICES,
						  default=Goal.STATUS_NOT_STARTED)
	computed_score  = models.DecimalField(
						  max_digits=7, decimal_places=4,
						  null=True, blank=True,
						  help_text="Score 0–1 (100% = 1.0000). Tracking only, not rating.")
	notes           = models.TextField(blank=True)
	updated_by      = models.ForeignKey(
						  User, null=True, on_delete=models.SET_NULL,
						  related_name='achievements_updated')
	created_at      = models.DateTimeField(auto_now_add=True)
	updated_at      = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']
		unique_together = ('goal', 'cycle')

	def __str__(self):
		score = f"{float(self.computed_score)*100:.1f}%" if self.computed_score is not None else "N/A"
		return f"{self.goal.title} | {self.cycle.name} | Score: {score}"

	def save(self, *args, **kwargs):
		# Auto-compute score before saving
		self.computed_score = self.goal.compute_score(
			actual=self.actual,
			actual_date=self.actual_date
		)
		super().save(*args, **kwargs)

		# Sync status to the parent Goal
		try:
			self.goal.status = self.status
			self.goal.save(update_fields=['status'])
		except Exception:
			pass

		# For shared goals: sync actual to all sibling goals
		try:
			if self.goal.is_shared and self.goal.is_shared_primary and self.goal.shared_template:
				self._sync_shared_achievement()
		except Exception:
			pass

	def _sync_shared_achievement(self):
		"""Propagate primary owner's actual to all linked sibling goals."""
		sibling_goals = Goal.objects.filter(
			shared_template=self.goal.shared_template
		).exclude(pk=self.goal.pk)

		for sibling in sibling_goals:
			QuarterlyAchievement.objects.update_or_create(
				goal=sibling,
				cycle=self.cycle,
				defaults={
					'actual':       self.actual,
					'actual_date':  self.actual_date,
					'status':       self.status,
					'notes':        '[Synced from primary owner]',
					'updated_by':   self.updated_by,
				}
			)


# ─────────────────────────────────────────────
# MANAGER CHECK-IN
# ─────────────────────────────────────────────

class ManagerCheckIn(models.Model):
	"""
	Structured check-in record by Manager (L1) per Employee per Cycle.
	"""
	employee        = models.ForeignKey(
						  User, on_delete=models.PROTECT,
						  related_name='check_ins_received',
						  limit_choices_to={'role': 'employee'})
	manager         = models.ForeignKey(
						  User, on_delete=models.PROTECT,
						  related_name='check_ins_given',
						  limit_choices_to={'role': 'manager'})
	cycle           = models.ForeignKey(
						  GoalCycle, on_delete=models.PROTECT,
						  related_name='check_ins')
	comment         = models.TextField(
						  help_text="Structured discussion notes from the check-in session")
	is_complete     = models.BooleanField(default=False)
	checked_in_at   = models.DateTimeField(auto_now_add=True)
	updated_at      = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-checked_in_at']
		unique_together = ('employee', 'cycle')

	def __str__(self):
		return f"Check-in: {self.employee.get_full_name()} by {self.manager.get_full_name()} [{self.cycle.name}]"


# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────

class AuditLog(models.Model):
	"""
	Immutable log of all post-lock changes and key workflow events.
	"""
	ACTION_SUBMIT      = 'submit'
	ACTION_APPROVE     = 'approve'
	ACTION_RETURN      = 'return'
	ACTION_LOCK        = 'lock'
	ACTION_UNLOCK      = 'unlock'
	ACTION_EDIT_GOAL   = 'edit_goal'
	ACTION_EDIT_TARGET = 'edit_target'
	ACTION_EDIT_WEIGHT = 'edit_weightage'
	ACTION_ACH_UPDATE  = 'achievement_update'
	ACTION_CHECKIN     = 'checkin'
	ACTION_CHOICES     = [
		(ACTION_SUBMIT,      'Sheet Submitted'),
		(ACTION_APPROVE,     'Sheet Approved'),
		(ACTION_RETURN,      'Sheet Returned'),
		(ACTION_LOCK,        'Sheet Locked'),
		(ACTION_UNLOCK,      'Admin Unlocked Sheet'),
		(ACTION_EDIT_GOAL,   'Goal Edited'),
		(ACTION_EDIT_TARGET, 'Target Edited'),
		(ACTION_EDIT_WEIGHT, 'Weightage Edited'),
		(ACTION_ACH_UPDATE,  'Achievement Updated'),
		(ACTION_CHECKIN,     'Manager Check-in Logged'),
	]

	user          = models.ForeignKey(
						User, null=True, on_delete=models.SET_NULL,
						related_name='audit_logs')
	goal_sheet    = models.ForeignKey(
						GoalSheet, null=True, blank=True,
						on_delete=models.SET_NULL,
						related_name='audit_logs')
	goal          = models.ForeignKey(
						Goal, null=True, blank=True,
						on_delete=models.SET_NULL,
						related_name='audit_logs')
	action        = models.CharField(max_length=30, choices=ACTION_CHOICES)
	field_changed = models.CharField(max_length=80, blank=True)
	old_value     = models.TextField(blank=True)
	new_value     = models.TextField(blank=True)
	extra_notes   = models.TextField(blank=True)
	ip_address    = models.GenericIPAddressField(null=True, blank=True)
	timestamp     = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-timestamp']

	def __str__(self):
		return (f"[{self.timestamp:%Y-%m-%d %H:%M}] "
				f"{self.user} — {self.get_action_display()}")

	@classmethod
	def log(cls, user, action, goal_sheet=None, goal=None,
			field_changed='', old_value='', new_value='',
			extra_notes='', ip_address=None):
		"""Convenience factory method."""
		return cls.objects.create(
			user=user,
			action=action,
			goal_sheet=goal_sheet,
			goal=goal,
			field_changed=field_changed,
			old_value=str(old_value),
			new_value=str(new_value),
			extra_notes=extra_notes,
			ip_address=ip_address,
		)



