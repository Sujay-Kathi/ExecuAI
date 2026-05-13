"""
Authentication routes for handling role-based access.
Tracks runtime online presence for peer chat integration.
"""
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Employee
from backend.schemas import LoginRequest, EmployeeOut

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Track live online presence by employee email
ONLINE_USERS = set()


@router.post("/login", response_model=EmployeeOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate an employee via email and password.
    Returns the employee details and role to govern UI access.
    """
    employee = db.query(Employee).filter(Employee.email == payload.email.strip()).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Compute hash of incoming password
    pwd_hash = hashlib.sha256(payload.password.encode()).hexdigest()

    # Compare hash, or allow fallback plain check if someone seeded raw passwords
    if employee.password_hash != pwd_hash and employee.password_hash != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Mark user as online
    ONLINE_USERS.add(employee.email)

    out = EmployeeOut.model_validate(employee)
    out.is_online = True
    return out


@router.post("/logout")
def logout(payload: dict):
    """Mark user as offline."""
    email = payload.get("email")
    if email and email in ONLINE_USERS:
        ONLINE_USERS.remove(email)
    return {"status": "ok"}


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees_auth(db: Session = Depends(get_db)):
    """Convenience endpoint to fetch all active accounts with current online presence status."""
    employees = db.query(Employee).all()
    results = []
    for emp in employees:
        out = EmployeeOut.model_validate(emp)
        out.is_online = (emp.email in ONLINE_USERS)
        results.append(out)
    return results
