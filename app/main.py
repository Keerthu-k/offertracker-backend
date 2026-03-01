"""OfferTracker API — application entry-point with global error handling."""

import traceback
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.api.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================
# Global Exception Handlers
# ======================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return clean validation errors instead of the default 422 body."""
    errors = []
    for err in exc.errors():
        field = " → ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg", "Invalid value")})
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Log HTTP exceptions for visibility and return a clean JSON body."""
    if exc.status_code >= 500:
        logger.error(
            "HTTP %s on %s %s: %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    else:
        logger.info(
            "HTTP %s on %s %s: %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled errors — log the full traceback but return a
    safe JSON response with an error_id the user can report."""
    error_id = str(uuid.uuid4())[:8]
    logger.error(
        "Unhandled exception [%s] on %s %s:\n%s",
        error_id,
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "error_id": error_id,
        },
    )


# ======================================================================
# Routes
# ======================================================================


@app.get("/")
def read_root():
    return {"message": "Welcome to OfferTracker API"}


app.include_router(api_router, prefix=settings.API_V1_STR)
