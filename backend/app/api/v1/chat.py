import uuid
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionUpdate,
    ChatTurnResponse,
)
from app.services import chat_service

settings = get_settings()
router = APIRouter(prefix="/chat", tags=["GenAI Farming Assistant"])


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSessionOut]:
    return chat_service.list_sessions(db, current_user)


@router.post(
    "/sessions",
    response_model=ChatSessionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionOut:
    return chat_service.create_session(db, current_user, payload)


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
def update_chat_session(
    session_id: uuid.UUID,
    payload: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionOut:
    return chat_service.update_session(db, current_user, session_id, payload)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_chat_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    chat_service.delete_session(db, current_user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageOut],
)
def get_chat_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatMessageOut]:
    return chat_service.list_messages(db, current_user, session_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatTurnResponse)
@limiter.limit(settings.RATE_LIMIT_AI)
def send_chat_message(
    request: Request,
    session_id: uuid.UUID,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatTurnResponse:
    _ = request
    return chat_service.send_message(db, current_user, session_id, payload)


@router.delete(
    "/sessions/{session_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def clear_chat_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    chat_service.clear_messages(db, current_user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
