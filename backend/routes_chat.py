"""
Chat / Agent routes — the main conversational endpoint.

Exposes the AI agent via /api/chat for the frontend to consume.
Returns both the human-readable result and the full execution log.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Any
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


@router.post("/", response_model=ChatResponse)
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
