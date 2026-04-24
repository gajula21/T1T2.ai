"""
API views for BandBoost IELTS Evaluator.

All endpoints require Supabase JWT authentication.
Both rate limiting layers are applied to evaluate endpoints.
"""

import logging
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .authentication import SupabaseJWTAuthentication
from .models import Evaluation, QuotaLog
from .rate_limit import (
    check_rpm,
    check_daily_quota,
    consume_daily_quota,
    get_quota_status,
    RPMLimitError,
    DailyQuotaError,
)
from .serializers import (
    EvaluationCreateTask1Serializer,
    EvaluationCreateTask2Serializer,
    EvaluationDetailSerializer,
    EvaluationListSerializer,
    QuotaStatusSerializer,
    AdminQuotaSerializer,
)
from .tasks import evaluate_task1_async, evaluate_task2_async
from .pdf_export import generate_evaluation_pdf

logger = logging.getLogger(__name__)


def _quota_headers(user_id: str) -> dict:
    """Returns quota status headers to attach to any evaluate response."""
    quota = get_quota_status(user_id)
    return {
        "X-Quota-Limit": str(quota["limit"]),
        "X-Quota-Used": str(quota["used"]),
        "X-Quota-Remaining": str(quota["remaining"]),
        "X-Quota-Resets-In": str(quota["resets_in_seconds"]),
    }


def _apply_rate_limits(user_id: str):
    """
    Run both rate limit checks. Returns (ok, error_response) tuple.
    ok=True means both checks passed.
    """
    try:
        check_rpm(user_id)
    except RPMLimitError as e:
        return False, Response(
            {"error": True, "message": e.message, "retry_after": e.retry_after},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(e.retry_after)},
        )

    try:
        check_daily_quota(user_id)
    except DailyQuotaError as e:
        return False, Response(
            {
                "error": True,
                "message": e.message,
                "retry_after": e.retry_after,
                "quota_remaining": 0,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(e.retry_after)},
        )

    return True, None


# ─────────────────────────────────────────────
# POST /api/evaluate/task1
# ─────────────────────────────────────────────
class EvaluateTask1View(APIView):
    """Submit a Task 1 chart image + essay for evaluation."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        user_id = request.user.uid

        # Rate limiting
        ok, err = _apply_rate_limits(user_id)
        if not ok:
            return err

        # Validate input
        serializer = EvaluationCreateTask1Serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        essay_text = serializer.validated_data["essay_text"]
        image_url = serializer.validated_data.get("image_url", "")
        task_question = serializer.validated_data.get("task_question", "")
        word_count = len(essay_text.split())
        
        # Handle file upload — save to DO Spaces if configured, else save locally
        uploaded_image_url = image_url
        image_file = request.FILES.get("image")
        if image_file:
            try:
                from django.conf import settings as djsettings
                use_s3 = getattr(djsettings, "_DO_SPACES_CONFIGURED", False)
                if use_s3:
                    from django.core.files.storage import default_storage
                    filename = f"task1/{user_id}/{uuid.uuid4()}{_ext(image_file.name)}"
                    path = default_storage.save(filename, image_file)
                    uploaded_image_url = default_storage.url(path)
                else:
                    # Local dev: save to MEDIA_ROOT and store the file system path
                    import os
                    from django.core.files.storage import FileSystemStorage
                    local_storage = FileSystemStorage(location=djsettings.MEDIA_ROOT)
                    filename = f"task1/{user_id}/{uuid.uuid4()}{_ext(image_file.name)}"
                    saved_name = local_storage.save(filename, image_file)
                    # Store as absolute path so Celery task can read bytes directly
                    uploaded_image_url = os.path.join(djsettings.MEDIA_ROOT, saved_name)
            except Exception as e:
                logger.error("Image save failed: %s", e)
                return Response(
                    {"error": True, "message": "Image could not be saved. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Create evaluation record
        evaluation = Evaluation.objects.create(
            supabase_uid=user_id,
            task_type="task1",
            image_url=uploaded_image_url or None,
            task_question=task_question or None,
            essay_text=essay_text,
            word_count=word_count,
            status="queued",
        )

        # Queue async Celery task
        task = evaluate_task1_async.delay(evaluation.id)
        evaluation.celery_task_id = task.id
        evaluation.save(update_fields=["celery_task_id"])

        # Consume daily quota
        remaining = consume_daily_quota(user_id)

        logger.info(
            "Task 1 queued: evaluation_id=%d, user=%s, words=%d",
            evaluation.id, user_id, word_count,
        )

        headers = _quota_headers(user_id)
        return Response(
            {"id": evaluation.id, "status": "queued", "quota_remaining": remaining},
            status=status.HTTP_202_ACCEPTED,
            headers=headers,
        )


def _ext(filename: str) -> str:
    import os
    return os.path.splitext(filename)[1].lower() or ".jpg"


# ─────────────────────────────────────────────
# POST /api/evaluate/task2
# ─────────────────────────────────────────────
class EvaluateTask2View(APIView):
    """Submit a Task 2 essay for evaluation."""

    def post(self, request):
        user_id = request.user.uid

        ok, err = _apply_rate_limits(user_id)
        if not ok:
            return err

        serializer = EvaluationCreateTask2Serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        essay_text = serializer.validated_data["essay_text"]
        task_question = serializer.validated_data.get("task_question", "")
        word_count = len(essay_text.split())

        evaluation = Evaluation.objects.create(
            supabase_uid=user_id,
            task_type="task2",
            task_question=task_question or None,
            essay_text=essay_text,
            word_count=word_count,
            status="queued",
        )

        task = evaluate_task2_async.delay(evaluation.id)
        evaluation.celery_task_id = task.id
        evaluation.save(update_fields=["celery_task_id"])

        remaining = consume_daily_quota(user_id)

        logger.info(
            "Task 2 queued: evaluation_id=%d, user=%s, words=%d",
            evaluation.id, user_id, word_count,
        )

        headers = _quota_headers(user_id)
        return Response(
            {"id": evaluation.id, "status": "queued", "quota_remaining": remaining},
            status=status.HTTP_202_ACCEPTED,
            headers=headers,
        )


# ─────────────────────────────────────────────
# GET /api/evaluate/{id}  — poll for result
# ─────────────────────────────────────────────
class EvaluationDetailView(APIView):
    """Poll for evaluation result by ID."""

    def get(self, request, pk):
        user_id = request.user.uid

        try:
            evaluation = Evaluation.objects.get(id=pk, supabase_uid=user_id)
        except Evaluation.DoesNotExist:
            return Response(
                {"error": True, "message": "Evaluation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EvaluationDetailSerializer(evaluation)
        return Response(serializer.data)


# ─────────────────────────────────────────────
# GET /api/evaluations  — paginated history
# ─────────────────────────────────────────────
class EvaluationListView(APIView):
    """Return paginated list of user's evaluations."""

    def get(self, request):
        user_id = request.user.uid
        page = int(request.query_params.get("page", 1))
        page_size = 10

        qs = Evaluation.objects.filter(supabase_uid=user_id).order_by("-created_at")
        total = qs.count()
        start = (page - 1) * page_size
        evaluations = qs[start: start + page_size]

        serializer = EvaluationListSerializer(evaluations, many=True)

        # Summary stats
        completed = Evaluation.objects.filter(
            supabase_uid=user_id, status="completed"
        )
        bands = [
            e.overall_band for e in completed if e.overall_band is not None
        ]
        avg_band = round(sum(bands) / len(bands), 1) if bands else None
        best_band = max(bands) if bands else None

        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
                "stats": {
                    "total_evaluations": total,
                    "average_band": avg_band,
                    "best_band": best_band,
                },
            }
        )


# ─────────────────────────────────────────────
# GET /api/evaluations/{id}/export  — PDF
# ─────────────────────────────────────────────
class EvaluationExportView(APIView):
    """Download evaluation result as a formatted PDF."""

    def get(self, request, pk):
        user_id = request.user.uid

        try:
            evaluation = Evaluation.objects.get(
                id=pk, supabase_uid=user_id, status="completed"
            )
        except Evaluation.DoesNotExist:
            return Response(
                {"error": True, "message": "Completed evaluation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            pdf_bytes = generate_evaluation_pdf(evaluation)
        except Exception as e:
            logger.error("PDF generation failed for evaluation %d: %s", pk, e)
            return Response(
                {"error": True, "message": "PDF generation failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        from django.http import HttpResponse
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="bandboost-evaluation-{pk}.pdf"'
        )
        return response


# ─────────────────────────────────────────────
# GET /api/quota  — user's daily usage
# ─────────────────────────────────────────────
class QuotaView(APIView):
    """Return current user's daily evaluation quota status."""

    def get(self, request):
        quota = get_quota_status(request.user.uid)
        serializer = QuotaStatusSerializer(quota)
        return Response(serializer.data)


# ─────────────────────────────────────────────
# GET /api/admin/quota  — admin view of all key usage
# ─────────────────────────────────────────────
class AdminQuotaView(APIView):
    """Admin endpoint: view API key usage across all models."""

    # Override to require Django staff status for this one endpoint
    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        # Simple role check: allow if supabase role is 'service_role' or is admin
        if not (
            getattr(request.user, "role", "") in ("service_role", "admin")
            or getattr(request.user, "is_staff", False)
        ):
            return Response(
                {"error": True, "message": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        today_logs = QuotaLog.objects.filter().order_by("-date", "model")[:50]
        serializer = AdminQuotaSerializer(today_logs, many=True)

        # Also include pool availability info
        from .gemini_pool import get_flash_pool, get_lite_pool
        try:
            fp = get_flash_pool()
            lp = get_lite_pool()
            pool_status = {
                "flash": {"available": fp.available_count, "total": fp.total_count},
                "lite": {"available": lp.available_count, "total": lp.total_count},
            }
        except Exception:
            pool_status = {}

        return Response({
            "quota_logs": serializer.data,
            "pool_status": pool_status,
        })
