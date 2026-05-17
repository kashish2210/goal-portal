from django.urls import path
from . import views
 
app_name = 'reports'
 
urlpatterns = [
    # Achievement report: Planned vs Actual for all employees
    path('achievement/',
         views.AchievementReportView.as_view(),
         name='achievement'),
 
    path('achievement/export/',
         views.AchievementExportView.as_view(),
         name='achievement_export'),
 
    # Completion dashboard: who has/hasn't done check-ins
    path('completion/',
         views.CompletionDashboardView.as_view(),
         name='completion'),
]