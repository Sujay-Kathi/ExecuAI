"""
HR routes — endpoints accessible by the HR role.

== ASSIGNMENT: Feature Dev (HR module) ==
  - Onboard new employees (create profile → generate email → schedule orientation → send notification)
  - Approve / reject leave requests
  - View workforce insights (headcount, attrition risk)

Branch: feature/hr-module
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models import Employee, LeaveRequest
from backend.schemas import (
    EmployeeCreate, EmployeeOut,
    LeaveRequestOut, LeaveApproval,
)

router = APIRouter(prefix="/api/hr", tags=["HR"])


# ── Onboarding ───────────────────────────────────────

@router.post("/onboard", response_model=EmployeeOut, status_code=201)
def onboard_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    """
    Full onboarding workflow:
      1. Create employee record
      2. Generate corporate email
      3. Schedule orientation meeting (Google Calendar)
      4. Send welcome email (Gmail API)

    TODO: Feature Dev — wire steps 2-4 via agent/tools.py or directly.
    """
    # Step 1: Create record
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)

    # TODO: Step 2 — generate_employee_email(employee.name)
    # TODO: Step 3 — schedule_meeting("Orientation", employee.id, ...)
    # TODO: Step 4 — send_notification_email(employee.email, ...)

    return employee


@router.get("/employees", response_model=List[EmployeeOut])
def list_all_employees(db: Session = Depends(get_db)):
    """View all employees (HR dashboard)."""
    return db.query(Employee).all()


# ── Leave Approval ───────────────────────────────────

@router.get("/leaves", response_model=List[LeaveRequestOut])
def list_pending_leaves(db: Session = Depends(get_db)):
    """View all leave requests (filterable by status)."""
    return db.query(LeaveRequest).all()


@router.patch("/leaves/{leave_id}", response_model=LeaveRequestOut)
def approve_or_reject_leave(
    leave_id: int, body: LeaveApproval, db: Session = Depends(get_db)
):
    """HR approves or rejects a leave request."""
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400, detail="Status must be 'approved' or 'rejected'"
        )
    leave.status = body.status
    db.commit()
    db.refresh(leave)
    return leave


# ── Workforce Insights ──────────────────────────────

@router.get("/insights")
def workforce_insights(db: Session = Depends(get_db)):
    """
    Return workforce analytics: headcount, department breakdown, etc.
    TODO: Feature Dev — add attrition risk summary from ML model.
    """
    total = db.query(Employee).count()
    departments = {}
    for emp in db.query(Employee).all():
        departments[emp.department] = departments.get(emp.department, 0) + 1

    pending_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.status == "pending"
    ).count()

    return {
        "total_employees": total,
        "department_breakdown": departments,
        "pending_leave_requests": pending_leaves,
    }
