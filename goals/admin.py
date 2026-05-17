from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Department, ThrustArea, GoalCycle,
    GoalSheet, Goal, SharedGoalTemplate,
    QuarterlyAchievement, ManagerCheckIn, AuditLog
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'department', 'manager', 'employee_id']
    list_filter = ['role', 'department']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'employee_id']
    fieldsets = UserAdmin.fieldsets + (
        ('GoalTrack Profile', {
            'fields': ('role', 'department', 'manager', 'employee_id', 'phone', 'profile_picture', 'date_joined_org')
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']


@admin.register(ThrustArea)
class ThrustAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'is_active']
    list_filter = ['department', 'is_active']


@admin.register(GoalCycle)
class GoalCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'phase', 'fiscal_year', 'start_date', 'end_date', 'is_active']
    list_filter = ['phase', 'is_active']
    list_editable = ['is_active']


@admin.register(GoalSheet)
class GoalSheetAdmin(admin.ModelAdmin):
    list_display = ['employee', 'cycle', 'status', 'is_locked', 'submitted_at']
    list_filter = ['status', 'cycle', 'is_locked']
    search_fields = ['employee__username', 'employee__first_name', 'employee__last_name']


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['title', 'goal_sheet', 'uom', 'weightage', 'status', 'is_shared']
    list_filter = ['uom', 'status', 'is_shared']
    search_fields = ['title', 'goal_sheet__employee__username']


@admin.register(QuarterlyAchievement)
class QuarterlyAchievementAdmin(admin.ModelAdmin):
    list_display = ['goal', 'cycle', 'actual', 'status', 'computed_score', 'updated_at']
    list_filter = ['cycle', 'status']


@admin.register(ManagerCheckIn)
class ManagerCheckInAdmin(admin.ModelAdmin):
    list_display = ['employee', 'manager', 'cycle', 'is_complete', 'checked_in_at']
    list_filter = ['cycle', 'is_complete']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'goal_sheet', 'field_changed']
    list_filter = ['action']
    readonly_fields = ['timestamp']
