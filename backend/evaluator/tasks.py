"""
Celery async tasks for BandBoost IELTS evaluator.
Tasks are queued by views.py and polled via GET /api/evaluate/{id}.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def evaluate_task1_async(self, evaluation_id: int):
    """
    Async Celery task for IELTS Task 1 evaluation.
    Downloads image, calls Gemini Flash, saves results.
    """
    from .models import Evaluation
    from .task1 import evaluate_task1

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
    except Evaluation.DoesNotExist:
        logger.error("Evaluation %d not found.", evaluation_id)
        return

    evaluation.status = "processing"
    evaluation.save(update_fields=["status", "updated_at"])
    logger.info("Starting Task 1 evaluation: id=%d", evaluation_id)

    try:
        image_data = None

        if evaluation.image_url:
            url = evaluation.image_url
            if url.startswith("http://") or url.startswith("https://"):
                # Remote URL (DO Spaces) — download via HTTP
                import requests as req
                try:
                    resp = req.get(url, timeout=15)
                    resp.raise_for_status()
                    image_data = resp.content
                except Exception as e:
                    logger.warning("Could not download image from URL: %s", e)
            else:
                # Local filesystem path — read directly
                import os
                try:
                    with open(url, "rb") as f:
                        image_data = f.read()
                except Exception as e:
                    logger.warning("Could not read local image file: %s", e)

        result = evaluate_task1(
            image_url=evaluation.image_url or "",
            essay_text=evaluation.essay_text,
            task_question=evaluation.task_question,
            image_data=image_data,
        )

        evaluation.scores = result["scores"]
        evaluation.feedback = result["feedback"]
        evaluation.model_used = result.get("model_used", "")
        evaluation.cache_hit = result.get("cache_hit", False)
        evaluation.status = "completed"
        evaluation.save(
            update_fields=["scores", "feedback", "model_used", "cache_hit", "status", "updated_at"]
        )
        logger.info(
            "Task 1 evaluation completed: id=%d, overall=%s",
            evaluation_id,
            evaluation.scores.get("overall"),
        )

    except Exception as exc:
        logger.exception("Task 1 evaluation failed: id=%d, error=%s", evaluation_id, exc)

        if self.request.retries < self.max_retries:
            evaluation.status = "queued"
            evaluation.save(update_fields=["status", "updated_at"])
            raise self.retry(exc=exc)

        evaluation.status = "failed"
        evaluation.error_message = str(exc)[:1000]
        evaluation.save(update_fields=["status", "error_message", "updated_at"])


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def evaluate_task2_async(self, evaluation_id: int):
    """
    Async Celery task for IELTS Task 2 evaluation.
    Calls HF scorer + Gemini Flash-Lite feedback pipeline.
    """
    from .models import Evaluation
    from .task2 import evaluate_task2

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
    except Evaluation.DoesNotExist:
        logger.error("Evaluation %d not found.", evaluation_id)
        return

    evaluation.status = "processing"
    evaluation.save(update_fields=["status", "updated_at"])
    logger.info("Starting Task 2 evaluation: id=%d", evaluation_id)

    try:
        result = evaluate_task2(
            essay_text=evaluation.essay_text,
            task_question=evaluation.task_question
        )

        evaluation.scores = result["scores"]
        evaluation.feedback = result["feedback"]
        evaluation.model_used = result.get("model_used", "")
        evaluation.cache_hit = result.get("cache_hit", False)
        evaluation.status = "completed"
        evaluation.save(
            update_fields=["scores", "feedback", "model_used", "cache_hit", "status", "updated_at"]
        )
        logger.info(
            "Task 2 evaluation completed: id=%d, overall=%s",
            evaluation_id,
            evaluation.scores.get("overall"),
        )

    except Exception as exc:
        logger.exception("Task 2 evaluation failed: id=%d, error=%s", evaluation_id, exc)

        if self.request.retries < self.max_retries:
            evaluation.status = "queued"
            evaluation.save(update_fields=["status", "updated_at"])
            raise self.retry(exc=exc)

        evaluation.status = "failed"
        evaluation.error_message = str(exc)[:1000]
        evaluation.save(update_fields=["status", "error_message", "updated_at"])
