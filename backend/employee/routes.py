"""
Employee routes — endpoints accessible by the Employee role.

== ASSIGNMENT: Feature Dev (Employee module) ==
  - Apply for leave
  - Schedule meetings
  - View personal data (profile, salary, policies)
  - Request IT access

Branch: feature/employee-module
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models import Employee, LeaveRequest, Meeting
from backend.schemas import (
    EmployeeOut,
    LeaveRequestCreate, LeaveRequestOut,
    MeetingCreate, MeetingOut,
)

router = APIRouter(prefix="/api/employee", tags=["Employee"])


# ── Profile ──────────────────────────────────────────

@router.get("/profile/{employee_id}", response_model=EmployeeOut)
def get_my_profile(employee_id: int, db: Session = Depends(get_db)):
    """View own profile (name, role, department, date joined)."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


# ── Leave ────────────────────────────────────────────

@router.post("/leave", response_model=LeaveRequestOut, status_code=201)
def apply_for_leave(payload: LeaveRequestCreate, db: Session = Depends(get_db)):
    """Employee submits a leave request."""
    # TODO: add leave-balance check before creating
    leave = LeaveRequest(**payload.model_dump())
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/leave/{employee_id}", response_model=List[LeaveRequestOut])
def my_leave_requests(employee_id: int, db: Session = Depends(get_db)):
    """View own leave history."""
    return db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id
    ).all()


# ── Meetings ─────────────────────────────────────────

@router.post("/meeting", response_model=MeetingOut, status_code=201)
def schedule_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    """Schedule a new meeting."""
    meeting = Meeting(**payload.model_dump())
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/meetings/{employee_id}", response_model=List[MeetingOut])
def my_meetings(employee_id: int, db: Session = Depends(get_db)):
    """View meetings I organised."""
    return db.query(Meeting).filter(
        Meeting.organizer_id == employee_id
    ).all()


# ── Information Retrieval ────────────────────────────

@router.get("/info/{employee_id}")
def get_employee_info(employee_id: int, db: Session = Depends(get_db)):
    """
    Retrieve salary, role, policies for the employee.
    TODO: Feature Dev — add salary & policies tables/logic.
    """
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {
        "name": emp.name,
        "role": emp.role,
        "department": emp.department,
        "policies": "TODO: link to policy documents",
    }
