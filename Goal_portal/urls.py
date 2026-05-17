"""
URL configuration for Goal_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin (keep separate from custom admin portal)
    path('django-admin/', admin.site.urls),

    # Auth (login / logout / register)
    path('auth/', include('accounts.urls', namespace='accounts')),

    # Employee goal management
    path('goals/', include('goals.urls', namespace='goals')),

    # Manager workspace
    path('manager/', include('manager.urls', namespace='manager')),

    # Admin / HR portal
    path('portal/', include('portal.urls', namespace='portal')),

    # Reports
    path('reports/', include('reports.urls', namespace='reports')),

    # Dashboard (role-based redirect lives here)
    path('', include('dashboards.urls', namespace='dashboards')),

    # Bonus features: Azure SSO, Teams/Email notifications, Escalations
    path('integrations/', include('integrations.urls', namespace='integrations')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
