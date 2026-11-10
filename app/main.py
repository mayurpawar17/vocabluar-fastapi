from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.conversations import router as conversations_router
from app.core.config import get_settings
from app.core.firebase import get_firebase_app


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Initialize Firebase on application startup
    get_firebase_app()
    yield


app = FastAPI(
    title="Vocabulary Conversation API",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(conversations_router)
cors_origins = [
    origin.strip()
    for origin in get_settings().cors_origins.split(",")
    if origin.strip()
]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.exception_handler(HTTPException)
async def handle_http_error(_: Request, exception: HTTPException) -> JSONResponse:
    detail = exception.detail
    error = (
        detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail
        else {"code": "REQUEST_FAILED", "message": "The request could not be completed."}
    )
    return JSONResponse(
        status_code=exception.status_code,
        content={"error": error},
        headers=exception.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Check the request fields and try again.",
                "retryable": False,
            },
        },
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
    )
