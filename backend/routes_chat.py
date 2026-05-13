"""
Chat / Agent routes — the main conversational endpoint.

Exposes the AI agent via /api/chat for the frontend to consume.
Returns both the human-readable result and the full execution log.
Also handles real-time inter-employee live peer-to-peer messaging.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from agent.agent import AgentController

router = APIRouter(prefix="/api/chat", tags=["Chat"])

agent = AgentController()


class ChatRequest(BaseModel):
    message: str
    user_role: Optional[str] = "employee"


class ChatResponse(BaseModel):
    reply: str
    execution_log: List[str]
    intent: str = "general"
    entities: dict = {}
    tool_outputs: dict = {}
    execution_time: float = 0.0


class PeerMessagePayload(BaseModel):
    sender_email: str
    sender_name: str
    sender_role: str
    recipient_email: str
    text: str


# In-memory storage mapping recipient_email -> list of pending messages dicts
PEER_MESSAGES: Dict[str, List[Dict]] = {}


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest):
    """
    Main chat endpoint.
    Receives a natural-language request and returns the agent's response
    along with a detailed execution log.
    """
    result = agent.process_request(payload.message)

    return ChatResponse(
        reply=result.get("result", result.get("message", "Request processed.")),
        execution_log=result.get("steps", result.get("steps_executed", [])),
        intent=result.get("intent", "general"),
        entities=result.get("entities", {}),
        tool_outputs=result.get("tool_outputs", {}),
        execution_time=result.get("execution_time", 0.0),
    )


@router.post("/peer/send")
def send_peer_message(payload: PeerMessagePayload):
    """Broadcast a real-time message to a specific active employee terminal feed."""
    rec = payload.recipient_email.strip()
    if rec not in PEER_MESSAGES:
        PEER_MESSAGES[rec] = []
    PEER_MESSAGES[rec].append(payload.model_dump())
    return {"status": "sent"}


@router.get("/peer/poll")
def poll_peer_messages(email: str):
    """Poll for live incoming direct communications directed to this employee."""
    rec = email.strip()
    msgs = PEER_MESSAGES.get(rec, [])
    if msgs:
        PEER_MESSAGES[rec] = []
    return msgs
