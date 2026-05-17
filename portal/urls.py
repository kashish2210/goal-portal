from django.urls import path
from . import views
 
app_name = 'portal'
 
urlpatterns = [
    # Overview dashboard
    path('',
         views.AdminDashboardView.as_view(),
         name='dashboard'),

    # Analytics dashboard
    path('analytics/',
         views.AnalyticsView.as_view(),
         name='analytics'),
 
    # ── Cycle management ──────────────────────────────────────────────────────
    path('cycles/',
         views.CycleListView.as_view(),
         name='cycle_list'),
 
    path('cycles/create/',
         views.CycleCreateView.as_view(),
         name='cycle_create'),
 
    path('cycles/<int:pk>/edit/',
         views.CycleEditView.as_view(),
         name='cycle_edit'),
 
    path('cycles/<int:pk>/toggle/',
         views.CycleToggleView.as_view(),
         name='cycle_toggle'),
 
    # ── Shared / Departmental Goals ───────────────────────────────────────────
    path('shared-goals/',
         views.SharedGoalListView.as_view(),
         name='shared_goal_list'),
 
    path('shared-goals/push/',
         views.SharedGoalPushView.as_view(),
         name='shared_goal_push'),
 
    path('shared-goals/<int:pk>/edit/',
         views.SharedGoalEditView.as_view(),
         name='shared_goal_edit'),
 
    # ── Goal Sheet Admin Actions ──────────────────────────────────────────────
    path('sheets/',
         views.AllSheetsView.as_view(),
         name='all_sheets'),
 
    path('sheets/<int:pk>/unlock/',
         views.SheetUnlockView.as_view(),
         name='sheet_unlock'),
 
    # ── Org / User management ─────────────────────────────────────────────────
    path('users/',
         views.UserListView.as_view(),
         name='user_list'),
 
    path('users/create/',
         views.UserCreateView.as_view(),
         name='user_create'),
 
    path('users/<int:pk>/edit/',
         views.UserEditView.as_view(),
         name='user_edit'),
 
    path('users/<int:pk>/reset-password/',
         views.UserResetPasswordView.as_view(),
         name='user_reset_password'),
 
    path('users/<int:pk>/toggle-active/',
         views.UserToggleActiveView.as_view(),
         name='user_toggle_active'),
 
    path('departments/',
         views.DepartmentListView.as_view(),
         name='department_list'),
 
    path('thrust-areas/',
         views.ThrustAreaListView.as_view(),
         name='thrust_area_list'),
 
    # ── Audit Log ─────────────────────────────────────────────────────────────
    path('audit-log/',
         views.AuditLogView.as_view(),
         name='audit_log'),
 
     path('audit-log/export/',
         views.AuditLogExportView.as_view(),
         name='audit_log_export'),

    # ── Impersonate ────────────────────────────────────────────────────────────
    path('impersonate/',
         views.ImpersonateListView.as_view(),
         name='impersonate_list'),

    path('impersonate/<int:pk>/start/',
         views.ImpersonateStartView.as_view(),
         name='impersonate_start'),

    path('impersonate/stop/',
         views.ImpersonateStopView.as_view(),
         name='impersonate_stop'),
]