from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
 
app_name = 'accounts'
 
urlpatterns = [
    path('login/',
         auth_views.LoginView.as_view(template_name='accounts/login.html'),
         name='login'),
 
    path('logout/',
         auth_views.LogoutView.as_view(next_page='accounts:login'),
         name='logout'),
 
    path('register/',
         views.RegisterView.as_view(),
         name='register'),
 
    path('profile/',
         views.ProfileView.as_view(),
         name='profile'),
 
    path('profile/edit/',
         views.ProfileEditView.as_view(),
         name='profile_edit'),
 
    path('change-password/',
         auth_views.PasswordChangeView.as_view(
             template_name='accounts/change_password.html',
             success_url='/auth/change-password/done/'),
         name='change_password'),

    path('change-password/done/',
         auth_views.PasswordChangeDoneView.as_view(
             template_name='accounts/change_password.html'),
         name='password_change_done'),
]