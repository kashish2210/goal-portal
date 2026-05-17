from django.urls import path
from . import views
 
app_name = 'manager'
 
urlpatterns = [
    # Team dashboard: list all direct reports and their sheet statuses
    path('',
         views.TeamDashboardView.as_view(),
         name='dashboard'),
 
    # Review and approve / return a specific goal sheet
    path('sheet/<int:pk>/review/',
         views.SheetReviewView.as_view(),
         name='sheet_review'),
 
    path('sheet/<int:pk>/approve/',
         views.SheetApproveView.as_view(),
         name='sheet_approve'),
 
    path('sheet/<int:pk>/return/',
         views.SheetReturnView.as_view(),
         name='sheet_return'),
 
    # Inline edit of a goal's target / weightage during approval
    path('sheet/<int:sheet_pk>/goal/<int:goal_pk>/inline-edit/',
         views.GoalInlineEditView.as_view(),
         name='goal_inline_edit'),
 
    # Quarterly check-in
    path('checkin/<int:employee_pk>/<int:cycle_pk>/',
         views.CheckInView.as_view(),
         name='check_in'),
 
    path('checkins/',
         views.CheckInListView.as_view(),
         name='check_in_list'),
]