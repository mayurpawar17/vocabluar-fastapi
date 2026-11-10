from typing import Annotated

from fastapi import APIRouter, Depends
from google.cloud.firestore import Client

from app.core.firebase import get_firestore_client
from app.core.security import CurrentUser
from app.schemas.conversation import (
    CreateConversationRequest,
    CreateConversationResponse,
    EndConversationResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.conversation_service import (
    create_conversation,
    end_conversation,
    send_message,
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])
FirestoreClient = Annotated[Client, Depends(get_firestore_client)]


@router.post("", response_model=CreateConversationResponse)
def create(request: CreateConversationRequest, uid: CurrentUser, db: FirestoreClient):
    conversation_id, assistant_message = create_conversation(db, uid, request)
    return CreateConversationResponse(
        conversationId=conversation_id,
        assistantMessage=assistant_message,
    )


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def message(
    conversation_id: str,
    request: SendMessageRequest,
    uid: CurrentUser,
    db: FirestoreClient,
):
    user_message, assistant_message = send_message(
        db,
        uid,
        conversation_id,
        request,
    )
    return SendMessageResponse(
        userMessage=user_message,
        assistantMessage=assistant_message,
    )


@router.post("/{conversation_id}/end", response_model=EndConversationResponse)
def end(conversation_id: str, uid: CurrentUser, db: FirestoreClient):
    summary = end_conversation(db, uid, conversation_id)
    return EndConversationResponse(
        conversationId=conversation_id,
        summary=summary,
    )
