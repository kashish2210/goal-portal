from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin


class RootRedirectView(LoginRequiredMixin, View):
	def get(self, request):
		# Simple role-based redirect
		user = request.user
		try:
			if hasattr(user, 'is_admin') and user.is_admin:
				return redirect('portal:dashboard')
			if hasattr(user, 'is_manager') and user.is_manager:
				return redirect('manager:dashboard')
		except Exception:
			pass
		return redirect('goals:sheet_list')


class DashboardHomeView(LoginRequiredMixin, View):
	def get(self, request):
		return render(request, 'dashboards/home.html')
