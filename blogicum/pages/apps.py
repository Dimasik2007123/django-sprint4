"""Конфигурация информационных страниц."""

from django.apps import AppConfig


class PagesConfig(AppConfig):
    """Зарегистрировать приложение pages."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'
