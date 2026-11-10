from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["beginner", "intermediate", "advanced"]
Topic = Literal[
    "daily_life",
    "work",
    "travel",
    "shopping",
    "interview",
    "free_conversation",
]


class CreateConversationRequest(BaseModel):
    topic: Topic
    level: Level


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class Correction(BaseModel):
    original: str
    corrected: str
    explanation: str


class VocabularyTip(BaseModel):
    term: str
    meaning: str
    example: str


class TutorResponse(BaseModel):
    reply: str = Field(min_length=1, max_length=2000)
    correction: Correction | None = None
    vocabulary: VocabularyTip | None = None


class MessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    correction: Correction | None = None
    vocabulary: VocabularyTip | None = None


class CreateConversationResponse(BaseModel):
    conversationId: str
    assistantMessage: MessageResponse


class SendMessageResponse(BaseModel):
    userMessage: MessageResponse
    assistantMessage: MessageResponse


class ConversationSummary(BaseModel):
    topic: Topic
    durationSeconds: int
    messageCount: int
    corrections: list[Correction]
    vocabulary: list[VocabularyTip]
    suggestion: str


class EndConversationResponse(BaseModel):
    conversationId: str
    summary: ConversationSummary
