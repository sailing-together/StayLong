"""Authenticated FastAPI case-flow API with an injectable persistence boundary."""

import secrets
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from starlette.staticfiles import StaticFiles

from staylong.services.cases import CaseRepository, InMemoryCaseRepository


class ConcernRequest(BaseModel):
    """The non-clinical concern accepted by the case-flow API."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2_000)


class CaseResponse(BaseModel):
    case_id: str
    status: str = "open"


class ConcernResponse(BaseModel):
    concern_id: str
    case_id: str
    summary: str


def create_app(
    *,
    api_token: str,
    repository: CaseRepository | None = None,
) -> FastAPI:
    """Create the API with an explicit token and injectable case repository."""
    if not api_token:
        raise ValueError("api_token is required")

    app = FastAPI(title="StayLong case-flow API", version="0.1.0")
    cases = repository or InMemoryCaseRepository()
    bearer = HTTPBearer(auto_error=False)

    def require_auth(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer authentication is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not secrets.compare_digest(credentials.credentials, api_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
    def create_case(
        concern: ConcernRequest,
        _: Callable[[], None] = Depends(require_auth),
    ) -> CaseResponse:
        case_id = f"case-{uuid4().hex}"
        cases.create_concern(case_id=case_id, summary=concern.summary)
        return CaseResponse(case_id=case_id)

    @app.get("/v1/cases/{case_id}/concerns", response_model=list[ConcernResponse])
    def list_concerns(
        case_id: str,
        _: Callable[[], None] = Depends(require_auth),
    ) -> list[ConcernResponse]:
        return [
            ConcernResponse(
                concern_id=concern.concern_id,
                case_id=concern.case_id,
                summary=concern.summary,
            )
            for concern in cases.list_concerns(case_id=case_id)
        ]

    app.mount(
        "/",
        StaticFiles(directory=Path(__file__).parent / "static", html=True),
        name="family-ui",
    )

    return app
