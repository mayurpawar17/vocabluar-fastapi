from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from google.cloud import firestore
from google.cloud.firestore import Client, DocumentReference

from app.ai.gemini_provider import generate_tutor_reply
from app.core.config import get_settings
from app.schemas.conversation import (
    ConversationSummary,
    Correction,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
    TutorResponse,
    VocabularyTip,
)

MAX_CONTEXT_MESSAGES = 15


def _now() -> datetime:
    return datetime.now(UTC)


def _conversation_ref(db: Client, uid: str, conversation_id: str) -> DocumentReference:
    return (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document(conversation_id)
    )


def _message_response(
    *,
    message_id: str,
    role: str,
    text: str,
    tutor: TutorResponse | None = None,
) -> MessageResponse:
    return MessageResponse(
        id=message_id,
        role=role,
        text=text,
        correction=tutor.correction if tutor else None,
        vocabulary=tutor.vocabulary if tutor else None,
    )


def _reserve_daily_message(db: Client, uid: str) -> None:
    settings = get_settings()
    day_key = _now().date().isoformat()
    usage_ref = (
        db.collection("users").document(uid).collection("usage").document(day_key)
    )
    transaction = db.transaction()

    @firestore.transactional
    def reserve(transaction):
        snapshot = usage_ref.get(transaction=transaction)
        count = snapshot.get("messageCount") if snapshot.exists else 0
        if count >= settings.daily_message_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "USAGE_LIMIT_REACHED",
                    "message": "You have reached today's conversation limit.",
                    "retryable": False,
                },
            )
        transaction.set(
            usage_ref,
            {"messageCount": count + 1, "updatedAt": firestore.SERVER_TIMESTAMP},
            merge=True,
        )

    reserve(transaction)


def create_conversation(
    db: Client,
    uid: str,
    request: CreateConversationRequest,
) -> tuple[str, MessageResponse]:
    _reserve_daily_message(db, uid)
    conversation_id = uuid4().hex
    conversation_ref = _conversation_ref(db, uid, conversation_id)
    message_id = uuid4().hex
    topic_title = request.topic.replace("_", " ")
    tutor = generate_tutor_reply(
        topic=request.topic,
        level=request.level,
        history=[],
        message=(
            f"Start the conversation with one friendly, level-appropriate "
            f"opening question about {topic_title}."
        ),
    )
    created_at = firestore.SERVER_TIMESTAMP
    conversation_ref.set(
        {
            "topic": request.topic,
            "level": request.level,
            "status": "active",
            "createdAt": created_at,
            "updatedAt": created_at,
            "messageCount": 1,
        }
    )
    assistant_message = _message_response(
        message_id=message_id,
        role="assistant",
        text=tutor.reply,
        tutor=tutor,
    )
    conversation_ref.collection("messages").document(message_id).set(
        {
            **assistant_message.model_dump(exclude_none=True),
            "createdAt": created_at,
            "messageIndex": 0,
        }
    )
    return conversation_id, assistant_message


def send_message(
    db: Client,
    uid: str,
    conversation_id: str,
    request: SendMessageRequest,
) -> tuple[MessageResponse, MessageResponse]:
    text = request.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_REQUEST",
                "message": "Message text cannot be empty.",
            },
        )
    if len(text) > get_settings().max_message_length:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "MESSAGE_TOO_LONG",
                "message": "Messages must be 500 characters or fewer.",
            },
        )

    conversation_ref = _conversation_ref(db, uid, conversation_id)
    conversation_snapshot = conversation_ref.get()
    if not conversation_snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONVERSATION_NOT_FOUND",
                "message": "Conversation not found.",
            },
        )
    conversation = conversation_snapshot.to_dict() or {}
    if conversation.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONVERSATION_NOT_ACTIVE",
                "message": "This conversation has already ended.",
            },
        )

    _reserve_daily_message(db, uid)
    prior_messages = list(
        conversation_ref.collection("messages")
        .order_by("messageIndex", direction=firestore.Query.DESCENDING)
        .limit(MAX_CONTEXT_MESSAGES)
        .stream()
    )
    history = [
        {"role": item.get("role", "assistant"), "text": item.get("text", "")}
        for snapshot in reversed(prior_messages)
        if (item := snapshot.to_dict())
    ]
    tutor = generate_tutor_reply(
        topic=conversation["topic"],
        level=conversation["level"],
        history=history,
        message=text,
    )
    latest_snapshot = conversation_ref.get()
    if not latest_snapshot.exists or latest_snapshot.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONVERSATION_NOT_ACTIVE",
                "message": "This conversation has already ended.",
            },
        )

    user_message = _message_response(
        message_id=uuid4().hex,
        role="user",
        text=text,
    )
    assistant_message = _message_response(
        message_id=uuid4().hex,
        role="assistant",
        text=tutor.reply,
        tutor=tutor,
    )
    batch = db.batch()
    now = firestore.SERVER_TIMESTAMP
    batch.set(
        conversation_ref.collection("messages").document(user_message.id),
        {
            **user_message.model_dump(exclude_none=True),
            "createdAt": now,
            "messageIndex": conversation.get("messageCount", 1),
        },
    )
    batch.set(
        conversation_ref.collection("messages").document(assistant_message.id),
        {
            **assistant_message.model_dump(exclude_none=True),
            "createdAt": now,
            "messageIndex": conversation.get("messageCount", 1) + 1,
        },
    )
    batch.update(
        conversation_ref,
        {
            "updatedAt": now,
            "messageCount": firestore.Increment(2),
        },
    )
    batch.commit()
    return user_message, assistant_message


def end_conversation(
    db: Client,
    uid: str,
    conversation_id: str,
) -> ConversationSummary:
    conversation_ref = _conversation_ref(db, uid, conversation_id)
    snapshot = conversation_ref.get()
    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONVERSATION_NOT_FOUND",
                "message": "Conversation not found.",
            },
        )
    conversation = snapshot.to_dict() or {}
    existing_summary = conversation.get("summary")
    if conversation.get("status") == "completed" and existing_summary:
        return ConversationSummary.model_validate(existing_summary)

    messages = [
        item.to_dict()
        for item in conversation_ref.collection("messages")
        .order_by("messageIndex")
        .limit(200)
        .stream()
    ]
    corrections = [
        Correction.model_validate(item["correction"])
        for item in messages
        if item.get("correction")
    ][:3]
    vocabulary = [
        VocabularyTip.model_validate(item["vocabulary"])
        for item in messages
        if item.get("vocabulary")
    ][:5]
    created_at = conversation.get("createdAt")
    duration_seconds = (
        max(0, int((_now() - created_at.replace(tzinfo=UTC)).total_seconds()))
        if isinstance(created_at, datetime)
        else 0
    )
    summary = ConversationSummary(
        topic=conversation["topic"],
        durationSeconds=duration_seconds,
        messageCount=len(messages),
        corrections=corrections,
        vocabulary=vocabulary,
        suggestion="Keep practicing with complete sentences and try using a new phrase.",
    )
    conversation_ref.update(
        {
            "status": "completed",
            "endedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "summary": summary.model_dump(),
        }
    )
    return summary
