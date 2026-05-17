from django.urls import path
from . import views

app_name = 'goals'

urlpatterns = [
	path('', views.sheet_list, name='sheet_list'),
	path('create/', views.sheet_create_or_edit, name='sheet_create'),
	path('<int:pk>/edit/', views.sheet_create_or_edit, name='sheet_edit'),
	path('<int:pk>/', views.sheet_detail, name='sheet_detail'),
	path('<int:pk>/submit/', views.sheet_submit, name='sheet_submit'),
	# Quarterly achievement update (employee)
	path('<int:sheet_pk>/checkin/<int:cycle_pk>/', views.sheet_checkin, name='sheet_checkin'),
	# Manager review routes
	path('manager/review/', views.manager_sheet_list, name='manager_sheet_list'),
	path('manager/review/<int:pk>/', views.manager_sheet_review, name='manager_sheet_review'),
	path('manager/review/<int:pk>/approve/', views.manager_sheet_approve, name='manager_sheet_approve'),
	path('manager/review/<int:pk>/return/', views.manager_sheet_return, name='manager_sheet_return'),
]
