"""
Django admin registration for BandBoost evaluator models.
"""

from django.contrib import admin
from .models import Evaluation, QuotaLog


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "id", "supabase_uid", "task_type", "status",
        "word_count", "overall_band", "model_used", "cache_hit", "created_at"
    ]
    list_filter = ["task_type", "status", "cache_hit", "model_used"]
    search_fields = ["supabase_uid", "essay_text"]
    readonly_fields = [
        "supabase_uid", "task_type", "image_url", "essay_text", "word_count",
        "scores", "feedback", "model_used", "cache_hit", "celery_task_id",
        "error_message", "created_at", "updated_at"
    ]
    ordering = ["-created_at"]

    def overall_band(self, obj):
        return obj.overall_band
    overall_band.short_description = "Band"


@admin.register(QuotaLog)
class QuotaLogAdmin(admin.ModelAdmin):
    list_display = [
        "date", "model", "api_key_index", "calls_made", "cache_hits", "tokens_used"
    ]
    list_filter = ["model", "date"]
    ordering = ["-date", "model"]
