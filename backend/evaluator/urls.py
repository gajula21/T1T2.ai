"""
URL routing for the evaluator app.
All routes are prefixed with /api/ from the root urls.py.
"""

from django.urls import path
from .views import (
    EvaluateTask1View,
    EvaluateTask2View,
    EvaluationDetailView,
    EvaluationListView,
    EvaluationExportView,
    QuotaView,
    AdminQuotaView,
)

urlpatterns = [
    # Evaluation endpoints
    path("evaluate/task1", EvaluateTask1View.as_view(), name="evaluate-task1"),
    path("evaluate/task2", EvaluateTask2View.as_view(), name="evaluate-task2"),
    path("evaluate/<int:pk>", EvaluationDetailView.as_view(), name="evaluate-detail"),

    # History
    path("evaluations", EvaluationListView.as_view(), name="evaluation-list"),
    path("evaluations/<int:pk>/export", EvaluationExportView.as_view(), name="evaluation-export"),

    # Quota
    path("quota", QuotaView.as_view(), name="quota"),
    path("admin/quota", AdminQuotaView.as_view(), name="admin-quota"),
]
