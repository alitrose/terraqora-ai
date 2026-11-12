import logging
import sys
import uuid
from collections.abc import Callable
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, _PROJECT_ROOT, get_settings
from app.models.farm import Farm
from app.models.modules import (
    ChatMessage,
    ChatSession,
    CropPrediction,
    CropRecommendation,
    FertilizerRecommendation,
)
from app.models.user import User
from app.schemas.chat import (
    ChatCitationOut,
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionUpdate,
    ChatTurnResponse,
)
from app.services.crop_rec_service import get_crop_rec_registry_status
from app.services.crop_yield_service import get_crop_yield_registry_status
from app.services.fertilizer_service import get_fertilizer_registry_status

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

from ai.chatbot.providers import (  # noqa: E402
    ChatTurn,
    LLMProvider,
    LLMProviderError,
    build_llm_provider,
)
from ai.prompts.agronomy_prompts import (  # noqa: E402
    build_prompt_injection_refusal,
    build_system_prompt,
    detect_language,
    detect_prompt_injection,
)
from ai.rag.knowledge_base import (  # noqa: E402
    format_rag_context,
    retrieve_agronomy_context,
)

logger = logging.getLogger("terraqora.chat")

_PROVIDER_FACTORY_OVERRIDE: Callable[[Settings], LLMProvider] | None = None

_DEFAULT_TITLE_PREFIXES = (
    "new farming consultation",
    "new agronomy consultation",
    "consultation (",
)


def set_provider_factory_for_testing(
    factory: Callable[[Settings], LLMProvider] | None,
) -> None:
    """Allow automated tests to inject a deterministic or failing LLMProvider."""
    global _PROVIDER_FACTORY_OVERRIDE
    _PROVIDER_FACTORY_OVERRIDE = factory


def _get_provider(settings: Settings) -> LLMProvider:
    if _PROVIDER_FACTORY_OVERRIDE is not None:
        return _PROVIDER_FACTORY_OVERRIDE(settings)
    return build_llm_provider(settings)


def _verify_farm_ownership(
    db: Session, farm_id: uuid.UUID, user: User
) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected farm plot was not found.",
        )
    if farm.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to link this farm plot.",
        )
    return farm


def get_owned_chat_session(
    db: Session, session_id: uuid.UUID, user: User
) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    if session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this chat session.",
        )
    return session


def _to_session_out(session: ChatSession, message_count: int) -> ChatSessionOut:
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        language=session.language,  # type: ignore[arg-type]
        farm_id=session.farm_id,
        message_count=int(message_count),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _to_message_out(
    msg: ChatMessage, *, detected_language: str | None = None
) -> ChatMessageOut:
    raw_citations = msg.citations_json or []
    citations = [
        ChatCitationOut(
            source_title=str(item.get("source_title", "TerraQora Agronomy Guide")),
            section=str(item.get("section", "Reference")),
        )
        for item in raw_citations
        if isinstance(item, dict)
    ]
    return ChatMessageOut(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,  # type: ignore[arg-type]
        content=msg.content,
        citations=citations,
        provider=msg.provider,
        model_name=msg.model_name,
        latency_ms=msg.latency_ms,
        detected_language=detected_language,  # type: ignore[arg-type]
        created_at=msg.created_at,
    )


def list_sessions(db: Session, user: User) -> list[ChatSessionOut]:
    counts_sq = (
        select(
            ChatMessage.session_id,
            func.count(ChatMessage.id).label("msg_count"),
        )
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    rows = db.execute(
        select(
            ChatSession,
            func.coalesce(counts_sq.c.msg_count, 0).label("msg_count"),
        )
        .outerjoin(counts_sq, ChatSession.id == counts_sq.c.session_id)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
    ).all()

    return [_to_session_out(sess, msg_count) for sess, msg_count in rows]


def create_session(
    db: Session, user: User, payload: ChatSessionCreate
) -> ChatSessionOut:
    if payload.farm_id is not None:
        _verify_farm_ownership(db, payload.farm_id, user)

    title = payload.title or f"Consultation ({payload.language.upper()})"
    session = ChatSession(
        user_id=user.id,
        farm_id=payload.farm_id,
        title=title,
        language=payload.language,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_session_out(session, 0)


def update_session(
    db: Session,
    user: User,
    session_id: uuid.UUID,
    payload: ChatSessionUpdate,
) -> ChatSessionOut:
    session = get_owned_chat_session(db, session_id, user)
    updates = payload.model_dump(exclude_unset=True)

    if "farm_id" in updates and updates["farm_id"] is not None:
        _verify_farm_ownership(db, updates["farm_id"], user)

    for field, value in updates.items():
        setattr(session, field, value)

    db.commit()
    db.refresh(session)

    msg_count = (
        db.scalar(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id == session.id
            )
        )
        or 0
    )
    return _to_session_out(session, msg_count)


def delete_session(
    db: Session, user: User, session_id: uuid.UUID
) -> None:
    session = get_owned_chat_session(db, session_id, user)
    db.delete(session)
    db.commit()


def list_messages(
    db: Session, user: User, session_id: uuid.UUID
) -> list[ChatMessageOut]:
    session = get_owned_chat_session(db, session_id, user)
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    ).all()
    return [_to_message_out(row) for row in rows]


def clear_messages(
    db: Session, user: User, session_id: uuid.UUID
) -> None:
    session = get_owned_chat_session(db, session_id, user)
    existing = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session.id)
    ).all()
    for msg in existing:
        db.delete(msg)
    db.commit()


def _build_farm_and_ml_context(
    db: Session,
    user: User,
    session: ChatSession,
    *,
    include_farm_context: bool,
) -> tuple[str, str, Farm | None]:
    if not include_farm_context:
        return (
            "User chose not to attach saved farm plot details to this turn.",
            "ML history context skipped for this turn per user preference.",
            None,
        )

    linked_farm: Farm | None = None
    farm_lines: list[str] = []

    if session.farm_id is not None:
        candidate = db.get(Farm, session.farm_id)
        if candidate is not None and candidate.user_id == user.id:
            linked_farm = candidate
            farm_lines.append(
                f"- Linked Farm Plot: {candidate.name} | {candidate.district}, {candidate.state} | "
                f"Area: {candidate.area_hectares:.2f} ha | Soil: {candidate.soil_type}"
                + (f", pH {candidate.soil_ph:.1f}" if candidate.soil_ph is not None else "")
                + f" | Irrigation: {candidate.irrigation_type}"
                + (f" | Primary Crop: {candidate.primary_crop}" if candidate.primary_crop else "")
            )

    if not farm_lines:
        user_farms = db.scalars(
            select(Farm)
            .where(Farm.user_id == user.id)
            .order_by(Farm.updated_at.desc())
            .limit(3)
        ).all()
        for f in user_farms:
            if linked_farm is None:
                linked_farm = f
            farm_lines.append(
                f"- Saved Plot: {f.name} ({f.district}, {f.state}, {f.area_hectares:.2f} ha, "
                f"{f.soil_type}"
                + (f", pH {f.soil_ph:.1f}" if f.soil_ph is not None else "")
                + f", {f.irrigation_type}"
                + (f", crop: {f.primary_crop}" if f.primary_crop else "")
                + ")"
            )

    farm_summary = "\n".join(farm_lines) if farm_lines else ""

    # Read latest saved Phase 5 / 5B ML runs owned by this user (never mutates records)
    ml_lines: list[str] = []

    yield_stmt = (
        select(CropPrediction)
        .where(CropPrediction.user_id == user.id)
        .order_by(CropPrediction.created_at.desc())
        .limit(1)
    )
    if session.farm_id is not None:
        farm_yield = db.scalar(
            select(CropPrediction)
            .where(
                CropPrediction.user_id == user.id,
                CropPrediction.farm_id == session.farm_id,
            )
            .order_by(CropPrediction.created_at.desc())
            .limit(1)
        )
        latest_yield = farm_yield or db.scalar(yield_stmt)
    else:
        latest_yield = db.scalar(yield_stmt)

    if latest_yield is not None:
        ml_lines.append(
            f"- Saved Crop Yield Prediction: {latest_yield.crop} ({latest_yield.season}, "
            f"{latest_yield.state}, {latest_yield.area_hectares:.2f} ha) -> "
            f"{latest_yield.predicted_yield:.2f} {latest_yield.yield_unit} "
            f"(model: {latest_yield.model_name}, v{latest_yield.model_version})"
        )

    crop_rec_stmt = (
        select(CropRecommendation)
        .where(CropRecommendation.user_id == user.id)
        .order_by(CropRecommendation.created_at.desc())
        .limit(1)
    )
    if session.farm_id is not None:
        farm_crop_rec = db.scalar(
            select(CropRecommendation)
            .where(
                CropRecommendation.user_id == user.id,
                CropRecommendation.farm_id == session.farm_id,
            )
            .order_by(CropRecommendation.created_at.desc())
            .limit(1)
        )
        latest_crop_rec = farm_crop_rec or db.scalar(crop_rec_stmt)
    else:
        latest_crop_rec = db.scalar(crop_rec_stmt)

    if latest_crop_rec is not None:
        ml_lines.append(
            f"- Saved Crop Suitability Recommendation: Top match '{latest_crop_rec.recommended_crop}' "
            f"(NPK {latest_crop_rec.nitrogen:.0f}-{latest_crop_rec.phosphorus:.0f}-{latest_crop_rec.potassium:.0f}, "
            f"pH {latest_crop_rec.soil_ph:.1f}, rainfall {latest_crop_rec.rainfall_mm:.0f} mm, "
            f"temp {latest_crop_rec.temperature_c:.1f} C, model {latest_crop_rec.model_version})"
        )

    fert_stmt = (
        select(FertilizerRecommendation)
        .where(FertilizerRecommendation.user_id == user.id)
        .order_by(FertilizerRecommendation.created_at.desc())
        .limit(1)
    )
    if session.farm_id is not None:
        farm_fert = db.scalar(
            select(FertilizerRecommendation)
            .where(
                FertilizerRecommendation.user_id == user.id,
                FertilizerRecommendation.farm_id == session.farm_id,
            )
            .order_by(FertilizerRecommendation.created_at.desc())
            .limit(1)
        )
        latest_fert = farm_fert or db.scalar(fert_stmt)
    else:
        latest_fert = db.scalar(fert_stmt)

    if latest_fert is not None:
        ml_lines.append(
            f"- Saved Fertilizer Advisory: '{latest_fert.recommended_fertilizer}' for "
            f"{latest_fert.crop_type} on {latest_fert.soil_type} soil "
            f"(NPK {latest_fert.nitrogen:.0f}-{latest_fert.phosphorus:.0f}-{latest_fert.potassium:.0f}, "
            f"pH {latest_fert.soil_ph:.1f}, qualitative guidance only)"
        )

    # Check live ML artifact readiness transparently (missing .joblib never breaks chat)
    try:
        registry_notes = []
        for fn in (
            get_crop_yield_registry_status,
            get_crop_rec_registry_status,
            get_fertilizer_registry_status,
        ):
            item = fn()
            registry_notes.append(f"{item.module}: {item.status}")
        ml_lines.append(
            "- Available TerraQora ML Modules Status: " + "; ".join(registry_notes)
        )
    except Exception:
        logger.warning("Could not query ML registry status cleanly for chat context.")

    return farm_summary, "\n".join(ml_lines), linked_farm


def _auto_title_from_prompt(prompt: str) -> str:
    single_line = " ".join(prompt.split())
    if len(single_line) <= 58:
        return single_line
    return single_line[:55].rstrip() + "..."


def send_message(
    db: Session,
    user: User,
    session_id: uuid.UUID,
    payload: ChatMessageCreate,
) -> ChatTurnResponse:
    settings = get_settings()
    if len(payload.content) > settings.CHAT_MAX_MESSAGE_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Message exceeds maximum allowed length of {settings.CHAT_MAX_MESSAGE_CHARS} characters.",
        )

    session = get_owned_chat_session(db, session_id, user)

    # Language selection + optional automatic script detection
    if payload.language == "auto":
        resolved_lang, auto_detected = detect_language(
            payload.content, fallback=session.language
        )
    else:
        resolved_lang = payload.language
        auto_detected = False

    # Load bounded conversation history before this turn
    max_msgs = max(2, settings.CHAT_MAX_HISTORY_TURNS * 2)
    prior_msgs = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(max_msgs)
    ).all()
    prior_msgs.reverse()

    history = [
        ChatTurn(
            role="assistant" if m.role == "assistant" else "user",
            content=m.content,
        )
        for m in prior_msgs
        if m.role in ("user", "assistant")
    ]

    # Prompt-injection & secret-exfiltration protection
    injection_category = detect_prompt_injection(payload.content)
    if injection_category is not None:
        logger.warning(
            "Blocked suspicious prompt pattern (%s) for user_id=%s session_id=%s",
            injection_category,
            user.id,
            session.id,
        )
        assistant_text = build_prompt_injection_refusal(resolved_lang)
        provider_name = "terraqora_guardrail"
        model_name = "safety-policy"
        latency_ms = 0
        citations_dicts: list[dict[str, str]] = []
    else:
        farm_context, ml_context, linked_farm = _build_farm_and_ml_context(
            db,
            user,
            session,
            include_farm_context=payload.include_farm_context,
        )
        rag_chunks = retrieve_agronomy_context(
            payload.content,
            farm_crop=linked_farm.primary_crop if linked_farm else None,
            farm_soil_type=linked_farm.soil_type if linked_farm else None,
            top_k=3,
        )
        rag_context = format_rag_context(rag_chunks)
        citations_dicts = [
            {"source_title": chunk.source_title, "section": chunk.section}
            for chunk in rag_chunks
        ]

        system_prompt = build_system_prompt(
            target_language=resolved_lang,
            rag_context=rag_context,
            farm_context=farm_context,
            ml_context=ml_context,
        )

        provider = _get_provider(settings)
        try:
            llm_reply = provider.generate(
                system_prompt=system_prompt,
                history=history,
                user_message=payload.content,
            )
        except LLMProviderError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
            ) from exc

        assistant_text = llm_reply.text
        provider_name = llm_reply.provider
        model_name = llm_reply.model_name
        latency_ms = llm_reply.latency_ms

    # Persist both turns cleanly after valid response
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.content,
        citations_json=[],
        provider=None,
        model_name=None,
        latency_ms=None,
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=assistant_text,
        citations_json=citations_dicts,
        provider=provider_name,
        model_name=model_name,
        latency_ms=latency_ms,
    )

    session.language = resolved_lang
    if len(prior_msgs) == 0 and session.title.lower().startswith(_DEFAULT_TITLE_PREFIXES):
        session.title = _auto_title_from_prompt(payload.content)

    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(session)
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    msg_count = (
        db.scalar(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id == session.id
            )
        )
        or 0
    )

    logger.info(
        "Completed GenAI turn user_id=%s session_id=%s lang=%s provider=%s latency_ms=%s",
        user.id,
        session.id,
        resolved_lang,
        provider_name,
        latency_ms,
    )

    return ChatTurnResponse(
        session=_to_session_out(session, msg_count),
        user_message=_to_message_out(user_msg),
        assistant_message=_to_message_out(
            assistant_msg, detected_language=resolved_lang  # type: ignore[arg-type]
        ),
        resolved_language=resolved_lang,  # type: ignore[arg-type]
        language_auto_detected=auto_detected,
        source_mode="live_api",
    )
