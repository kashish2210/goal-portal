from django.shortcuts import render
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin


# Minimal account views to satisfy URL routing and basic flows.
class RegisterView(CreateView):
	form_class = CustomUserCreationForm
	template_name = 'accounts/register.html'
	success_url = reverse_lazy('accounts:login')


class ProfileView(LoginRequiredMixin, TemplateView):
	template_name = 'accounts/profile.html'


class ProfileEditView(LoginRequiredMixin, TemplateView):
	template_name = 'accounts/profile_edit.html'

