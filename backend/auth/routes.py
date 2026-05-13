"""
Authentication routes for handling role-based access.
"""
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Employee
from backend.schemas import LoginRequest, EmployeeOut

router = APIRouter(prefix="/api/auth", tags=["Auth"])


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

    return employee


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees_auth(db: Session = Depends(get_db)):
    """Convenience endpoint to fetch all active accounts for login dropdowns/testing."""
    return db.query(Employee).all()
