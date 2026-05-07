"""
Employee routes — CRUD operations on employee records.

== ASSIGNMENT: Backend Developer + Feature Devs (HR module) ==
  - Implement employee creation, listing, updating, deletion.
  - Wire up the onboarding workflow (create record → generate email → schedule meeting).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models import Employee
from backend.schemas import EmployeeCreate, EmployeeOut

router = APIRouter(prefix="/api/employees", tags=["Employees"])


@router.post("/", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    """Create a new employee record (part of onboarding flow)."""
    # TODO: Feature Dev — add email generation & calendar scheduling logic
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    """List all employees."""
    return db.query(Employee).all()


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get a single employee by ID."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp
