from django.urls import path
from . import views
from .azure_views import AzureLoginView, AzureCallbackView

app_name = 'integrations'

urlpatterns = [
    # 5.1 — Azure AD SSO
    path('azure/login/',    AzureLoginView.as_view(),    name='azure_login'),
    path('azure/callback/', AzureCallbackView.as_view(), name='azure_callback'),

    # 5.3 — Escalation rules (Admin)
    path('escalations/',                      views.EscalationRuleListView.as_view(),  name='escalation_rules'),
    path('escalations/<int:pk>/toggle/',      views.EscalationRuleToggleView.as_view(), name='escalation_toggle'),

    # 5.3 — Escalation log (Admin)
    path('escalations/log/',                  views.EscalationLogView.as_view(),       name='escalation_log'),
    path('escalations/log/<int:pk>/resolve/', views.EscalationResolveView.as_view(),   name='escalation_resolve'),
]
