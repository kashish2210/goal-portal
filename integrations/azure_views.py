"""
Microsoft Entra ID (Azure AD) SSO — OAuth2 / OIDC flow (5.1).
Credentials are read from IntegrationConfig (DB) first, then settings.py fallback.
"""

import uuid
import json
import logging

from django.contrib.auth import get_user_model, login
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.views import View

logger = logging.getLogger(__name__)
User = get_user_model()

SCOPES = ['User.Read', 'User.ReadBasic.All']


def _get_cfg():
    """Return IntegrationConfig row (lazy import to avoid circular)."""
    from .models import IntegrationConfig
    return IntegrationConfig.get()


def _msal_app():
    import msal
    cfg = _get_cfg()
    client_id     = cfg.azure_client_id     or ''
    client_secret = cfg.azure_client_secret or ''
    tenant_id     = cfg.azure_tenant_id     or ''
    if not (client_id and client_secret and tenant_id):
        raise ValueError(
            'Azure AD credentials are not configured. '
            'Go to Admin → Integration Settings to set them up.'
        )
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=f'https://login.microsoftonline.com/{tenant_id}',
    )


class AzureLoginView(View):
    def get(self, request):
        try:
            app = _msal_app()
        except ValueError as exc:
            from django.contrib import messages
            messages.error(request, str(exc))
            return redirect('accounts:login')

        cfg = _get_cfg()
        redirect_uri = cfg.azure_redirect_uri or request.build_absolute_uri('/integrations/azure/callback/')
        state = str(uuid.uuid4())
        request.session['azure_state'] = state
        auth_url = app.get_authorization_request_url(
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect_uri,
        )
        return redirect(auth_url)


class AzureCallbackView(View):
    def get(self, request):
        if request.GET.get('state') != request.session.pop('azure_state', None):
            return HttpResponseBadRequest('Invalid state parameter.')

        error = request.GET.get('error')
        if error:
            logger.warning('Azure AD auth error: %s — %s', error, request.GET.get('error_description'))
            return HttpResponseBadRequest(f'Azure AD error: {error}')

        cfg = _get_cfg()
        redirect_uri = cfg.azure_redirect_uri or request.build_absolute_uri('/integrations/azure/callback/')

        try:
            app = _msal_app()
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))

        result = app.acquire_token_by_authorization_code(
            code=request.GET.get('code'),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )

        if 'error' in result:
            logger.error('Token acquisition failed: %s', result.get('error_description'))
            return HttpResponseBadRequest('Could not acquire token from Azure AD.')

        claims = result.get('id_token_claims', {})
        user = self._sync_user(claims, result['access_token'], cfg)
        if user is None:
            return HttpResponseBadRequest('Could not resolve user from Azure AD claims.')

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('/')

    def _graph_get(self, path, access_token):
        import urllib.request
        req = urllib.request.Request(
            f'https://graph.microsoft.com/v1.0{path}',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            logger.warning('Graph API call failed (%s): %s', path, exc)
            return {}

    def _resolve_role(self, group_ids, cfg):
        try:
            role_map = json.loads(cfg.azure_role_map_json or '{}')
        except Exception:
            role_map = {}
        for gid in group_ids:
            if gid in role_map:
                return role_map[gid]
        return User.ROLE_EMPLOYEE

    def _sync_user(self, claims, access_token, cfg):
        oid        = claims.get('oid') or claims.get('sub')
        email      = claims.get('preferred_username') or claims.get('email', '')
        first_name = claims.get('given_name', '')
        last_name  = claims.get('family_name', '')
        if not oid:
            return None

        groups_data = self._graph_get('/me/memberOf?$select=id', access_token)
        group_ids   = [g.get('id') for g in groups_data.get('value', []) if g.get('id')]
        role        = self._resolve_role(group_ids, cfg)

        manager_data  = self._graph_get('/me/manager?$select=mail', access_token)
        manager_email = manager_data.get('mail', '')

        username = f'azure_{oid}'
        user, _ = User.objects.get_or_create(username=username)
        user.first_name = first_name
        user.last_name  = last_name
        user.email      = email
        user.role       = role

        if manager_email:
            mgr = User.objects.filter(email=manager_email).first()
            if mgr:
                user.manager = mgr

        user.save()
        return user
