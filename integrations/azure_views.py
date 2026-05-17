"""
Microsoft Entra ID (Azure AD) SSO — OAuth2 / OIDC flow (5.1).

Required settings.py additions:
    AZURE_AD_CLIENT_ID     = '<app-client-id>'
    AZURE_AD_CLIENT_SECRET = '<client-secret>'
    AZURE_AD_TENANT_ID     = '<tenant-id>'
    AZURE_AD_REDIRECT_URI  = 'https://your-domain.com/integrations/azure/callback/'

    # Map Azure AD group object-IDs to portal roles
    AZURE_AD_ROLE_MAP = {
        '<admin-group-object-id>':    'admin',
        '<manager-group-object-id>':  'manager',
        '<employee-group-object-id>': 'employee',
    }

Requires:  pip install msal
"""

import uuid
import logging

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.views import View

logger = logging.getLogger(__name__)
User = get_user_model()


def _msal_app():
    import msal  # lazy import — only needed when Azure SSO is used
    return msal.ConfidentialClientApplication(
        client_id=settings.AZURE_AD_CLIENT_ID,
        client_credential=settings.AZURE_AD_CLIENT_SECRET,
        authority=f'https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}',
    )


SCOPES = ['User.Read', 'User.ReadBasic.All']


class AzureLoginView(View):
    """Redirect the browser to Microsoft's login page."""

    def get(self, request):
        state = str(uuid.uuid4())
        request.session['azure_state'] = state
        auth_url = _msal_app().get_authorization_request_url(
            scopes=SCOPES,
            state=state,
            redirect_uri=settings.AZURE_AD_REDIRECT_URI,
        )
        return redirect(auth_url)


class AzureCallbackView(View):
    """
    Handle the OAuth2 callback from Microsoft.
    - Exchanges code for tokens
    - Reads user profile + group memberships
    - Creates or updates the local User record
    - Logs the user in
    """

    def get(self, request):
        # CSRF-equivalent state check
        if request.GET.get('state') != request.session.pop('azure_state', None):
            return HttpResponseBadRequest('Invalid state parameter.')

        error = request.GET.get('error')
        if error:
            logger.warning('Azure AD auth error: %s — %s', error, request.GET.get('error_description'))
            return HttpResponseBadRequest(f'Azure AD error: {error}')

        code = request.GET.get('code')
        result = _msal_app().acquire_token_by_authorization_code(
            code=code,
            scopes=SCOPES,
            redirect_uri=settings.AZURE_AD_REDIRECT_URI,
        )

        if 'error' in result:
            logger.error('Token acquisition failed: %s', result.get('error_description'))
            return HttpResponseBadRequest('Could not acquire token from Azure AD.')

        claims = result.get('id_token_claims', {})
        access_token = result['access_token']

        user = self._sync_user(claims, access_token)
        if user is None:
            return HttpResponseBadRequest('Could not resolve user from Azure AD claims.')

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('/')

    # ── helpers ──────────────────────────────────────────────────────────────

    def _graph_get(self, path: str, access_token: str):
        """Call Microsoft Graph API."""
        import json, urllib.request
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

    def _resolve_role(self, group_ids: list) -> str:
        """Map Azure AD group membership to a portal role."""
        role_map = getattr(settings, 'AZURE_AD_ROLE_MAP', {})
        for gid in group_ids:
            if gid in role_map:
                return role_map[gid]
        return User.ROLE_EMPLOYEE  # default

    def _sync_user(self, claims: dict, access_token: str):
        """Create or update the local User from Azure AD claims + Graph data."""
        oid        = claims.get('oid') or claims.get('sub')
        email      = claims.get('preferred_username') or claims.get('email', '')
        first_name = claims.get('given_name', '')
        last_name  = claims.get('family_name', '')

        if not oid:
            return None

        # Fetch group memberships for role mapping
        groups_data = self._graph_get('/me/memberOf?$select=id', access_token)
        group_ids   = [g.get('id') for g in groups_data.get('value', []) if g.get('id')]
        role        = self._resolve_role(group_ids)

        # Fetch manager for org hierarchy sync
        manager_data  = self._graph_get('/me/manager?$select=mail', access_token)
        manager_email = manager_data.get('mail', '')

        # Upsert user — use Azure OID as username for uniqueness
        username = f'azure_{oid}'
        user, _ = User.objects.get_or_create(username=username)
        user.first_name = first_name
        user.last_name  = last_name
        user.email      = email
        user.role       = role

        # Sync manager FK if we can find them locally
        if manager_email:
            mgr = User.objects.filter(email=manager_email).first()
            if mgr:
                user.manager = mgr

        user.save()
        return user
