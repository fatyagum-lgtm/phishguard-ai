"""Local single-user API and optional same-origin compiled frontend."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from phishguard import __version__
from phishguard.model import load_model
from phishguard.service import analyze_email, analyze_url
from phishguard.urls import InputError

# Models, reports and compiled UI are repository assets, not Python package resources.
# Both editable and wheel installations are launched from the repository root.
ROOT = Path.cwd()
MAX_REQUEST = 1024 * 1024


class URLRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=4096)


class EmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=262144)

    @field_validator("content")
    @classmethod
    def valid_unicode(cls, value: str) -> str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("Invalid Unicode in email.") from exc
        return value


class URLReport(BaseModel):
    schema_version: int
    kind: Literal["url"]
    generated_utc: str
    input: dict[str, Any]
    input_sha256: str
    classification: Literal["review_required", "likely_phishing", "likely_legitimate"]
    binary_model_label: str | None
    score: float | None
    threshold: float | None
    score_meaning: str
    model_id: str | None
    model_version: str | None
    review_reasons: list[str]
    observed_features: dict[str, float]
    heuristics: list[dict[str, Any]]
    rule_index: float
    explanation: dict[str, Any] | None
    analysis_ms: float
    limitations: list[str]


class EmailReport(BaseModel):
    schema_version: int
    kind: Literal["email"]
    generated_utc: str
    subject: str
    from_: list[dict[str, str]] = Field(alias="from")
    reply_to: list[dict[str, str]]
    received: list[str]
    authentication: dict[str, Any]
    body_text: str
    body_truncated: bool
    attachments: list[dict[str, Any]]
    indicators: list[dict[str, Any]]
    defects: list[str]
    url_count: int
    urls_truncated: bool
    method: str
    bytes: int
    input_sha256: str
    url_reports: list[dict[str, Any]]
    classification: Literal["review_required", "no_indicators_detected"]
    limitations: list[str]


class RequestBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        if scope["method"] == "POST":
            origin = headers.get(b"origin", b"").decode("latin1")
            allowed = {f"http://{host}:5173" for host in ("localhost", "127.0.0.1")}
            # TrustedHostMiddleware checks this authority before the boundary runs.
            allowed.add("http://" + headers.get(b"host", b"").decode("latin1"))
            if origin and origin not in allowed:
                return await JSONResponse({"detail": "Cross-origin submission refused."}, 403)(
                    scope, receive, send
                )
            if headers.get(b"sec-fetch-site") == b"cross-site":
                return await JSONResponse({"detail": "Cross-site submission refused."}, 403)(
                    scope, receive, send
                )
            if headers.get(b"content-encoding", b"identity") != b"identity":
                return await JSONResponse(
                    {"detail": "Compressed request bodies are unsupported."}, 415
                )(scope, receive, send)
            buffer = bytearray()
            try:
                for _ in range(1024):
                    event = await asyncio.wait_for(receive(), timeout=10)
                    if event["type"] == "http.disconnect":
                        return
                    buffer.extend(event.get("body", b""))
                    if len(buffer) > MAX_REQUEST:
                        return await JSONResponse({"detail": "Request exceeds 1 MiB."}, 413)(
                            scope, receive, send
                        )
                    if not event.get("more_body", False):
                        break
                else:
                    return await JSONResponse({"detail": "Too many request chunks."}, 413)(
                        scope, receive, send
                    )
            except TimeoutError:
                return await JSONResponse({"detail": "Request body timeout."}, 408)(
                    scope, receive, send
                )

            async def replay():
                return {"type": "http.request", "body": bytes(buffer), "more_body": False}

            receive = replay

        async def secured_send(event):
            if event["type"] == "http.response.start":
                event.setdefault("headers", []).extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"cache-control", b"no-store"),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self'; "
                            b"style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                            b"connect-src 'self'; object-src 'none'; frame-ancestors 'none'; "
                            b"base-uri 'none'; form-action 'self'",
                        ),
                    ]
                )
            await send(event)

        await self.app(scope, receive, secured_send)


def create_app(
    model_path: Path | None = None, research_path: Path | None = None, frontend: Path | None = None
) -> FastAPI:
    app = FastAPI(
        title="PhishGuard AI",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    model_path = model_path or Path(os.environ.get("PHISHGUARD_MODEL", ROOT / "models/model.json"))
    research_path = research_path or ROOT / "reports/research.json"
    frontend = frontend or ROOT / "frontend/dist"
    model, model_error = None, None
    if model_path.exists():
        try:
            model = load_model(model_path)
        except (ValueError, OSError, KeyError, TypeError):
            model_error = (
                "Local model artifact is invalid; inference disabled. Reproduce "
                "or restore the model."
            )
    semaphore = asyncio.Semaphore(2)

    @app.exception_handler(InputError)
    async def input_error(request: Request, exc: InputError):
        return JSONResponse({"detail": str(exc)}, 422)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo submitted private content as FastAPI's default error does.
        return JSONResponse(
            {"detail": "Invalid request. Check required fields and input limits."}, 422
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return JSONResponse(
            {"detail": "Analysis failed safely. Check the local installation."}, 500
        )

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": __version__,
            "offline_analysis": True,
            "model_available": model is not None,
            "history_persisted": False,
        }

    @app.get("/api/model/info")
    def model_info():
        return {
            "available": model is not None,
            "error": model_error,
            "model_id": model.data.get("model_id") if model else None,
            "version": __version__,
            "protocol": "domain_disjoint" if model else None,
            "threshold": model.data["threshold"] if model else None,
            "dataset": model.data.get("dataset") if model else None,
            "score_note": "Dataset-calibrated estimate; not a definitive phishing verdict.",
            "limits": {
                "url_characters": 4096,
                "email_bytes": 262144,
                "mime_parts": 100,
                "mime_depth": 12,
                "email_urls_analyzed": 20,
            },
        }

    @app.post("/api/analyze/url", response_model=URLReport)
    async def url_analysis(payload: URLRequest):
        async with semaphore:
            return await run_in_threadpool(analyze_url, payload.url, model)

    @app.post("/api/analyze/email", response_model=EmailReport)
    async def email_analysis(payload: EmailRequest):
        async with semaphore:
            return await run_in_threadpool(analyze_email, payload.content.encode("utf-8"), model)

    @app.post("/api/analyze/email-file", response_model=EmailReport)
    async def email_upload(request: Request):
        filename = request.headers.get("x-filename", "")
        if (
            not filename.lower().endswith(".eml")
            or len(filename) > 256
            or any(c in filename for c in "/\\\r\n")
        ):
            return JSONResponse({"detail": "Supply a plain .eml filename in X-Filename."}, 415)
        if request.headers.get("content-type", "").split(";")[0] != "message/rfc822":
            return JSONResponse({"detail": "Expected message/rfc822 content type."}, 415)
        async with semaphore:
            return await run_in_threadpool(analyze_email, await request.body(), model)

    @app.get("/api/research/summary")
    def research_summary():
        if not research_path.exists():
            return JSONResponse(
                {"detail": "No experiment artifact installed. Run the research command."}, 404
            )
        return json.loads(research_path.read_text())

    @app.get("/api/research/experiments")
    def research_experiments():
        if not research_path.exists():
            return JSONResponse({"detail": "No experiment artifact installed."}, 404)
        data = json.loads(research_path.read_text())
        return {"robustness": data["robustness"], "models": data["models"]}

    if (frontend / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(frontend / "index.html")

    app.add_middleware(RequestBoundary)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    return app
