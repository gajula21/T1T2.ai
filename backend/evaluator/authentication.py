"""
Supabase JWT authentication backend for Django REST Framework.
Validates Bearer tokens issued by Supabase Auth.
"""

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SupabaseUser:
    """Lightweight user object constructed from Supabase JWT claims."""

    def __init__(self, uid: str, email: str = "", role: str = "authenticated"):
        self.uid = uid
        self.email = email
        self.role = role
        self.is_authenticated = True
        self.is_active = True

    def __str__(self):
        return f"SupabaseUser({self.uid})"


class SupabaseJWTAuthentication(BaseAuthentication):
    """
    Authenticates requests using Supabase-issued JWT tokens.
    Token must be sent as: Authorization: Bearer <token>
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1].strip()
        try:
            # First, check if the token is valid by verifying it directly with the Supabase Gateway
            import requests
            verify_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
            resp = requests.get(
                verify_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_ANON_KEY,
                },
                timeout=10
            )

            if resp.status_code != 200:
                raise AuthenticationFailed(f"Token verification failed from Supabase: {resp.text}")

            # If Supabase Auth returns 200, the token is perfectly valid (unexpired and authentic).
            # We can now safely decode the payload locally without verifying the signature again.
            payload = jwt.decode(token, options={"verify_signature": False})

        except jwt.DecodeError as e:
            raise AuthenticationFailed(f"Invalid token format: {e}")
        except Exception as e:
            if isinstance(e, AuthenticationFailed):
                raise
            raise AuthenticationFailed(f"Authentication service error: {e}")

        uid = payload.get("sub")
        if not uid:
            raise AuthenticationFailed("Token missing 'sub' claim.")

        user = SupabaseUser(
            uid=uid,
            email=payload.get("email", ""),
            role=payload.get("role", "authenticated"),
        )
        return (user, token)

    def authenticate_header(self, request):
        return "Bearer"
