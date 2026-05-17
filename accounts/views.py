from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
import subprocess, sys


class RegisterView(CreateView):
	form_class = CustomUserCreationForm
	template_name = 'accounts/register.html'
	success_url = reverse_lazy('accounts:login')


class ProfileView(LoginRequiredMixin, View):
	def get(self, request):
		ctx = {'active_tab': request.GET.get('tab', 'profile')}
		if request.user.is_admin:
			from integrations.models import IntegrationConfig
			from integrations.views import ALLOWED_COMMANDS
			ctx['cfg'] = IntegrationConfig.get()
			ctx['commands'] = list(ALLOWED_COMMANDS.keys())
		return render(request, 'accounts/profile.html', ctx)

	def post(self, request):
		if not request.user.is_admin:
			messages.error(request, 'Admin access required.')
			return redirect('accounts:profile')

		action = request.POST.get('action', '')

		if action == 'save_integrations':
			from integrations.models import IntegrationConfig
			cfg = IntegrationConfig.get()
			p = request.POST
			cfg.azure_client_id     = p.get('azure_client_id', '').strip()
			cfg.azure_client_secret = p.get('azure_client_secret', '').strip()
			cfg.azure_tenant_id     = p.get('azure_tenant_id', '').strip()
			cfg.azure_redirect_uri  = p.get('azure_redirect_uri', '').strip()
			cfg.azure_role_map_json = p.get('azure_role_map_json', '{}').strip() or '{}'
			cfg.email_host          = p.get('email_host', '').strip()
			cfg.email_port          = int(p.get('email_port') or 587)
			cfg.email_host_user     = p.get('email_host_user', '').strip()
			new_pw = p.get('email_host_password', '').strip()
			if new_pw:
				cfg.email_host_password = new_pw
			cfg.email_use_tls       = 'email_use_tls' in p
			cfg.default_from_email  = p.get('default_from_email', '').strip()
			cfg.teams_webhook_url   = p.get('teams_webhook_url', '').strip()
			cfg.site_base_url       = p.get('site_base_url', '').strip()
			cfg.updated_by = request.user
			cfg.save()
			messages.success(request, 'Integration settings saved.')
			return redirect('/auth/profile/?tab=integrations')

		if action == 'run_command':
			from integrations.views import ALLOWED_COMMANDS
			from django.conf import settings as django_settings
			cmd_key = request.POST.get('command', '').strip()
			if cmd_key not in ALLOWED_COMMANDS:
				return JsonResponse({'output': f'Unknown command: {cmd_key}', 'success': False})
			cmd = [sys.executable] + ALLOWED_COMMANDS[cmd_key]
			try:
				result = subprocess.run(
					cmd, capture_output=True, text=True, timeout=60,
					cwd=str(django_settings.BASE_DIR),
				)
				output = result.stdout + result.stderr
				return JsonResponse({'output': output or '(no output)', 'success': result.returncode == 0})
			except subprocess.TimeoutExpired:
				return JsonResponse({'output': 'Timed out after 60s.', 'success': False})
			except Exception as exc:
				return JsonResponse({'output': f'Error: {exc}', 'success': False})

		return redirect('accounts:profile')


class ProfileEditView(LoginRequiredMixin, View):
	template_name = 'accounts/profile_edit.html'

	def get(self, request):
		return render(request, self.template_name)
