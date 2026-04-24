"""
Database models for BandBoost IELTS AI Evaluator.
"""

from django.db import models


class Evaluation(models.Model):
    """Represents a single IELTS Task 1 or Task 2 evaluation request."""

    TASK_CHOICES = [
        ("task1", "Task 1"),
        ("task2", "Task 2"),
    ]
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    supabase_uid = models.CharField(max_length=255, db_index=True)
    task_type = models.CharField(max_length=5, choices=TASK_CHOICES)
    image_url = models.URLField(null=True, blank=True)  # Task 1 only
    task_question = models.TextField(null=True, blank=True)  # Task prompt/question
    essay_text = models.TextField()
    word_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default="queued", db_index=True
    )

    # Results — stored as JSON after evaluation completes
    scores = models.JSONField(null=True, blank=True)
    # Expected format:
    # {
    #   "task_response": 7.0,      # Task Achievement / Task Response
    #   "coherence": 6.5,          # Coherence and Cohesion
    #   "lexical": 6.0,            # Lexical Resource
    #   "grammar": 6.5,            # Grammatical Range and Accuracy
    #   "overall": 6.5             # Overall band score
    # }

    feedback = models.JSONField(null=True, blank=True)
    # Expected format:
    # {
    #   "task_response": "Your response addresses...",
    #   "coherence": "The essay is generally well-organised...",
    #   "lexical": "You use a good range of vocabulary...",
    #   "grammar": "There are some grammatical errors...",
    #   "improvements": [
    #     "Use more precise data references",
    #     "Vary sentence structure more",
    #     "Expand vocabulary range"
    #   ]
    # }

    model_used = models.CharField(max_length=60, blank=True, default="")
    cache_hit = models.BooleanField(default=False)
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["supabase_uid", "created_at"]),
            models.Index(fields=["supabase_uid", "status"]),
        ]

    def __str__(self):
        return f"Evaluation({self.id}) — {self.task_type} — {self.status}"

    @property
    def overall_band(self):
        """Returns the overall band score if evaluation is complete."""
        if self.scores and "overall" in self.scores:
            return self.scores["overall"]
        return None


class QuotaLog(models.Model):
    """Daily API usage log per model key for admin monitoring."""

    date = models.DateField(auto_now_add=True, db_index=True)
    model = models.CharField(max_length=60)
    api_key_index = models.IntegerField(default=0)  # which key in the pool
    calls_made = models.IntegerField(default=0)
    cache_hits = models.IntegerField(default=0)
    tokens_used = models.IntegerField(default=0)

    class Meta:
        unique_together = [["date", "model", "api_key_index"]]
        ordering = ["-date", "model"]

    def __str__(self):
        return f"QuotaLog({self.date}) — {self.model}[{self.api_key_index}] — {self.calls_made} calls"
