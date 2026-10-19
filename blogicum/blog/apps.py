"""Конфигурация приложения публикаций."""

from django.apps import AppConfig


class BlogConfig(AppConfig):
    """Зарегистрировать приложение blog."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'
    verbose_name = 'Блог'
