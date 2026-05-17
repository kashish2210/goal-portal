"""
Notification utilities for Email and Microsoft Teams (5.2).

Configure in settings.py:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS
    DEFAULT_FROM_EMAIL = 'goaltrack@yourorg.com'

    TEAMS_WEBHOOK_URL = 'https://outlook.office.com/webhook/...'  # optional
    SITE_BASE_URL     = 'https://your-domain.com'                 # for deep links
"""

import json
import logging
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _teams_webhook_url():
    return getattr(settings, 'TEAMS_WEBHOOK_URL', None)


def _base_url():
    return getattr(settings, 'SITE_BASE_URL', '').rstrip('/')


def send_email_notification(subject: str, body: str, recipient_email: str):
    """Send a plain-text email. Silently skips if no email configured."""
    if not recipient_email:
        return
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.warning('Email send failed to %s: %s', recipient_email, exc)


def send_teams_notification(title: str, body: str, deep_link_path: str = ''):
    """
    Post an Adaptive Card to a Teams channel via incoming webhook.
    Silently skips if TEAMS_WEBHOOK_URL is not configured.
    """
    webhook_url = _teams_webhook_url()
    if not webhook_url:
        return

    actions = []
    if deep_link_path:
        url = f'{_base_url()}{deep_link_path}'
        actions = [{
            'type': 'Action.OpenUrl',
            'title': 'Open in GoalTrack',
            'url': url,
        }]

    card = {
        'type': 'message',
        'attachments': [{
            'contentType': 'application/vnd.microsoft.card.adaptive',
            'content': {
                '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
                'type': 'AdaptiveCard',
                'version': '1.4',
                'body': [
                    {'type': 'TextBlock', 'size': 'Medium', 'weight': 'Bolder', 'text': title},
                    {'type': 'TextBlock', 'text': body, 'wrap': True},
                ],
                'actions': actions,
            },
        }],
    }

    try:
        data = json.dumps(card).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:
        logger.warning('Teams webhook failed: %s', exc)


def notify(subject: str, body: str, recipient_email: str,
           teams_title: str = '', deep_link_path: str = ''):
    """Send both email and Teams notification."""
    send_email_notification(subject, body, recipient_email)
    send_teams_notification(
        title=teams_title or subject,
        body=body,
        deep_link_path=deep_link_path,
    )
