from django.urls import path
from . import views
 
app_name = 'dashboard'
 
urlpatterns = [
    path('',
         views.RootRedirectView.as_view(),
         name='root'),
 
    path('home/',
         views.DashboardHomeView.as_view(),
         name='home'),
]