"""
Custom exception handler for DRF.
Returns consistent JSON error responses.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return Response(
            {
                "error": True,
                "message": _flatten_errors(response.data),
                "status_code": response.status_code,
            },
            status=response.status_code,
        )

    return Response(
        {
            "error": True,
            "message": "An unexpected error occurred.",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _flatten_errors(data):
    if isinstance(data, list):
        return " ".join(str(item) for item in data)
    if isinstance(data, dict):
        parts = []
        for key, val in data.items():
            if isinstance(val, list):
                parts.append(f"{key}: {' '.join(str(v) for v in val)}")
            else:
                parts.append(f"{key}: {val}")
        return " | ".join(parts)
    return str(data)
