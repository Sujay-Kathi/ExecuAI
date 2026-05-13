"""
Chat / Agent routes — the main conversational endpoint.

Exposes the AI agent via /api/chat for the frontend to consume.
Returns both the human-readable result and the full execution log.
Also handles real-time inter-employee live peer-to-peer messaging.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import datetime
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import LeaveRequest, Employee
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


# ── Leave Management Endpoints for Frontend Integration ──

class LeaveApplyPayload(BaseModel):
    email: str
    leave_type: str
    reason: str


class LeaveClosePayload(BaseModel):
    leave_id: int
    status: str


@router.post("/leave/apply")
def apply_leave_api(payload: LeaveApplyPayload, db: Session = Depends(get_db)):
    """Persist a newly applied leave request from the frontend form into the database."""
    emp = db.query(Employee).filter(Employee.email == payload.email.strip()).first()
    emp_id = emp.id if emp else 1
    
    now = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = now + datetime.timedelta(days=1)
    
    leave_rec = LeaveRequest(
        employee_id=emp_id,
        leave_type=payload.leave_type or "casual",
        start_date=tomorrow,
        end_date=tomorrow,
        reason=payload.reason,
        status="pending"
    )
    db.add(leave_rec)
    db.commit()
    db.refresh(leave_rec)
    
    return {
        "status": "success",
        "leave_id": leave_rec.id,
        "employee_name": emp.name if emp else "Employee",
        "employee_role": emp.role if emp else "Staff",
        "remaining_balance": 12
    }


@router.get("/leave/list")
def list_pending_leaves(db: Session = Depends(get_db)):
    """Fetch all pending leave applications for display in the HR review dashboard."""
    leaves = db.query(LeaveRequest).filter(LeaveRequest.status == "pending").all()
    results = []
    for l in leaves:
        emp = db.query(Employee).filter(Employee.id == l.employee_id).first()
        results.append({
            "id": l.id,
            "employee_name": emp.name if emp else f"User #{l.employee_id}",
            "employee_role": emp.role if emp else "Staff",
            "leave_type": l.leave_type,
            "reason": l.reason,
            "created_at": l.created_at.isoformat() if hasattr(l.created_at, 'isoformat') else str(l.created_at)
        })
    return results


@router.post("/leave/close")
def close_leave_api(payload: LeaveClosePayload, db: Session = Depends(get_db)):
    """Approve or reject a leave application, updating its status to closed."""
    leave_rec = db.query(LeaveRequest).filter(LeaveRequest.id == payload.leave_id).first()
    if leave_rec:
        leave_rec.status = payload.status
        db.commit()
        return {"status": "closed", "id": payload.leave_id, "final_status": payload.status}
    return {"status": "not_found"}

