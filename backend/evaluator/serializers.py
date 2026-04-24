"""
DRF serializers for the evaluator app.
"""

from rest_framework import serializers
from .models import Evaluation, QuotaLog


class EvaluationCreateTask1Serializer(serializers.Serializer):
    """Validates POST /api/evaluate/task1 request body."""

    essay_text = serializers.CharField(
        min_length=50,
        max_length=10000,
        error_messages={
            "min_length": "Essay must be at least 50 characters.",
            "max_length": "Essay exceeds 10,000 character limit.",
        },
    )
    image_url = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="URL of the uploaded chart image in DO Spaces.",
    )
    task_question = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=2000,
        help_text="The prompt/question given for the task.",
    )

    def validate_essay_text(self, value):
        word_count = len(value.split())
        if word_count < 20:
            raise serializers.ValidationError(
                "Essay must contain at least 20 words."
            )
        return value.strip()


class EvaluationCreateTask2Serializer(serializers.Serializer):
    """Validates POST /api/evaluate/task2 request body."""

    essay_text = serializers.CharField(
        min_length=50,
        max_length=15000,
        error_messages={
            "min_length": "Essay must be at least 50 characters.",
            "max_length": "Essay exceeds 15,000 character limit.",
        },
    )
    task_question = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        min_length=20,
        max_length=2000,
        error_messages={
            "min_length": "Task question must be at least 20 characters.",
        },
        help_text="The prompt/question given for the task.",
    )

    def validate_essay_text(self, value):
        word_count = len(value.split())
        if word_count < 20:
            raise serializers.ValidationError(
                "Essay must contain at least 20 words."
            )
        return value.strip()


class EvaluationListSerializer(serializers.ModelSerializer):
    """Compact serializer for history list view."""

    overall_band = serializers.ReadOnlyField()
    essay_excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "task_type",
            "status",
            "word_count",
            "overall_band",
            "essay_excerpt",
            "created_at",
        ]

    def get_essay_excerpt(self, obj):
        return obj.essay_text[:80] + "..." if len(obj.essay_text) > 80 else obj.essay_text


class EvaluationDetailSerializer(serializers.ModelSerializer):
    """Full serializer for individual evaluation result."""

    overall_band = serializers.ReadOnlyField()

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "task_type",
            "status",
            "image_url",
            "task_question",
            "essay_text",
            "word_count",
            "scores",
            "feedback",
            "model_used",
            "cache_hit",
            "overall_band",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class QuotaStatusSerializer(serializers.Serializer):
    """Response shape for /api/quota."""

    limit = serializers.IntegerField()
    used = serializers.IntegerField()
    remaining = serializers.IntegerField()
    resets_in_seconds = serializers.IntegerField()
    resets_at_ist_midnight = serializers.BooleanField()


class AdminQuotaSerializer(serializers.ModelSerializer):
    """Admin view of per-model quota logs."""

    class Meta:
        model = QuotaLog
        fields = "__all__"
