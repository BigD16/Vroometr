from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, get_db
from app.errors import AppError
from app.models.user import User
from app.repositories.bikes import BikeRepository
from app.repositories.retrieval import RetrievalRepository
from app.retrieval.ranking import Match
from app.services.bikes import BikeNotFound
from app.services.retrieval import InvalidSearch, RetrievalService
from vroometr.ai.embeddings import EmbeddingFailed
from vroometr.ai.factory import get_embedding_model, get_reranker
from vroometr.ai.reranking import RerankingFailed
from vroometr.ai.unconfigured import UnconfiguredError

router = APIRouter(prefix="/v1/retrieval", tags=["retrieval"])


def get_retrieval_service(session: Session = Depends(get_db)):
    return RetrievalService(
        BikeRepository(session),
        RetrievalRepository(session, settings.embedding_model, settings.embedding_version),
        get_embedding_model(),
        get_reranker(),
        reranker_model=settings.reranker_model,
    )


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bike_id: UUID
    query: str = Field(min_length=1, max_length=1200)
    include_reference_editions: StrictBool = False


class SearchDiagnostics(BaseModel):
    vector_candidates: int
    keyword_candidates: int
    reranker_candidates: int
    retrieval_version: str
    reranker_version: str
    reranker_model: str
    embedding_model: str
    embedding_version: str
    elapsed_ms: int
    context_chars: int
    confidence: float
    confidence_is_calibrated: Literal[False]


class SearchResponse(BaseModel):
    status: Literal["ready", "no_indexed_sources", "no_relevant_evidence", "sources_changed"]
    passages: list[Match]
    include_reference_editions: bool
    diagnostics: SearchDiagnostics


@router.post("", response_model=SearchResponse)
def search(
    body: SearchRequest,
    user: Annotated[User, Depends(get_current_user)],
    response: Response,
    service=Depends(get_retrieval_service),
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.search(user.id, body.bike_id, body.query, body.include_reference_editions)
    except BikeNotFound as exc:
        raise AppError("bike_not_found", "Bike not found", status_code=404) from exc
    except InvalidSearch as exc:
        raise AppError("invalid_search", str(exc), status_code=422) from exc
    except UnconfiguredError as exc:
        raise AppError(
            "search_unconfigured",
            "Document search needs embedding and reranker configuration.",
            status_code=503,
        ) from exc
    except (EmbeddingFailed, RerankingFailed) as exc:
        raise AppError(
            "search_unavailable", "Document search could not finish. Please retry.", status_code=503
        ) from exc
