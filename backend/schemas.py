"""
Pydantic schemas for request/response validation.

== ASSIGNMENT ==
  - Backend developer: keep these in sync with models.py.
  - Frontend developer: these define the API contract.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# ──────────────── Employee ────────────────

class EmployeeCreate(BaseModel):
    name: str
    email: str
    role: str
    department: Optional[str] = "General"


class EmployeeOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    department: str
    date_joined: datetime

    model_config = {"from_attributes": True}


# ──────────────── Leave ────────────────

class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type: str
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = ""


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type: str
    start_date: datetime
    end_date: datetime
    reason: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaveApproval(BaseModel):
    status: str       # "approved" or "rejected"


# ──────────────── Meeting ────────────────

class MeetingCreate(BaseModel):
    title: str
    organizer_id: int
    scheduled_at: datetime
    duration_minutes: Optional[int] = 30
    description: Optional[str] = ""


class MeetingOut(BaseModel):
    id: int
    title: str
    organizer_id: int
    scheduled_at: datetime
    duration_minutes: int
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────── Chat / Agent ────────────────

class ChatRequest(BaseModel):
    message: str
    user_role: Optional[str] = "employee"   # employee | hr | manager


class ChatResponse(BaseModel):
    reply: str
    execution_log: List[str]


# ──────────────── ML Prediction ────────────────

class AttritionInput(BaseModel):
    age: int
    monthly_income: float
    years_at_company: int
    job_satisfaction: int           # 1-4
    overtime: bool


class AttritionResult(BaseModel):
    prediction: str                 # "Likely to Leave" | "Stable"
    confidence: float


# ──────────────── Authentication ────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

