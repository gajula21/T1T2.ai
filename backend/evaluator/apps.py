"""
AppConfig for the evaluator Django app.
"""

from django.apps import AppConfig


class EvaluatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "evaluator"
    verbose_name = "IELTS Evaluator"

    def ready(self):
        # Initialize Gemini key pool on startup
        from . import gemini_pool  # noqa: F401  (triggers singleton creation)
