"""
Leave management routes.

== ASSIGNMENT: Feature Devs (Employee module) ==
  - Employees apply for leave.
  - HR approves/rejects.
  - System updates status automatically.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models import LeaveRequest
from backend.schemas import LeaveRequestCreate, LeaveRequestOut, LeaveApproval

router = APIRouter(prefix="/api/leaves", tags=["Leave Management"])


@router.post("/", response_model=LeaveRequestOut, status_code=201)
def apply_leave(payload: LeaveRequestCreate, db: Session = Depends(get_db)):
    """Employee submits a leave request."""
    leave = LeaveRequest(**payload.model_dump())
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/", response_model=List[LeaveRequestOut])
def list_leaves(db: Session = Depends(get_db)):
    """List all leave requests (HR view)."""
    return db.query(LeaveRequest).all()


@router.patch("/{leave_id}/approve", response_model=LeaveRequestOut)
def approve_leave(leave_id: int, body: LeaveApproval, db: Session = Depends(get_db)):
    """HR approves or rejects a leave request."""
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    leave.status = body.status
    db.commit()
    db.refresh(leave)
    return leave
