"""
Choices for the Django Audit Logger package.
"""
from django.db import models


AGENT_STRING_MAX_LENGTH = 255


class UsageLogMethodChoices(models.TextChoices):
    """
    HTTP method choices for usage logs.
    """
    HTTP_GET = 'GET', 'GET'
    HTTP_POST = 'POST', 'POST'
    HTTP_PUT = 'PUT', 'PUT'
    HTTP_DELETE = 'DELETE', 'DELETE'
    HTTP_PATCH = 'PATCH', 'PATCH'
    HTTP_OPTIONS = 'OPTIONS', 'OPTIONS'
    HTTP_HEAD = 'HEAD', 'HEAD'
