"""
Chat / Agent routes — the main conversational endpoint.

== ASSIGNMENT: AI Engineer ==
  - Wire this to the AgentController in agent/agent.py.
  - Process user intent, call tools, return structured response.
"""
from fastapi import APIRouter
from backend.schemas import ChatRequest, ChatResponse
from agent.agent import AgentController

router = APIRouter(prefix="/api/chat", tags=["Chat"])

agent = AgentController()


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest):
    """
    Main chat endpoint.
    Receives a natural-language request and returns the agent's response
    along with an execution log.
    """
    result = agent.process_request(payload.message)
    return ChatResponse(
        reply=result["message"],
        execution_log=result["steps_executed"]
    )
