from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from .firebase import get_firebase_app

bearer_scheme = HTTPBearer(auto_error=False)


def authenticated_uid(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHENTICATED",
                "message": "Sign in to use conversation practice.",
            },
        )

    try:
        claims = auth.verify_id_token(
            credentials.credentials,
            app=get_firebase_app(),
            check_revoked=True,
        )
    except (
        ValueError,
        auth.InvalidIdTokenError,
        auth.UserDisabledError,
        auth.UserNotFoundError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHENTICATED",
                "message": "Your session is invalid. Sign in again.",
            },
        ) from None
    except auth.CertificateFetchError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AUTH_TEMPORARILY_UNAVAILABLE",
                "message": "Could not verify your account right now. Please try again.",
                "retryable": True,
            },
        ) from None

    uid = claims.get("uid")
    if not isinstance(uid, str) or not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "Invalid user token."},
        )
    return uid


CurrentUser = Annotated[str, Depends(authenticated_uid)]
