"""
Authentication routes for handling role-based access.
Tracks runtime online presence for peer chat integration.
"""
import hashlib
from pydantic import BaseModel
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
    
    # Auto-seed baseline employees if table is empty to guarantee records are always fetched
    if not employees:
        default_pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
        initials = [
            Employee(name="Sujay Kathi", email="sujaykathi25csds@rnsit.ac.in", role="CEO & Lead Architect", department="Executive", password_hash=default_pwd_hash),
            Employee(name="Rahul Kumar", email="rahul@enterprise.com", role="Senior Software Engineer", department="Engineering", password_hash=default_pwd_hash),
            Employee(name="Roshni", email="br.roshni0031@gmail.com", role="Product Manager", department="Product", password_hash=default_pwd_hash),
            Employee(name="John Doe", email="john.doe@enterprise.com", role="IT Administrator", department="IT Operations", password_hash=default_pwd_hash),
            Employee(name="Alice Wang", email="alice.wang@enterprise.com", role="HR Specialist", department="Human Resources", password_hash=default_pwd_hash),
            Employee(name="Bob Smith", email="bob.smith@enterprise.com", role="DevOps Engineer", department="Engineering", password_hash=default_pwd_hash),
        ]
        db.add_all(initials)
        db.commit()
        employees = db.query(Employee).all()

    results = []
    for emp in employees:
        out = EmployeeOut.model_validate(emp)
        out.is_online = (emp.email in ONLINE_USERS)
        results.append(out)
    return results


class ResetPasswordPayload(BaseModel):
    email: str
    new_password: str


@router.post("/reset-password")
def reset_password_api(payload: ResetPasswordPayload, db: Session = Depends(get_db)):
    """Reset password for an authenticated employee and save permanently in database."""
    emp = db.query(Employee).filter(Employee.email == payload.email.strip()).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee record not found in database")
    
    pwd_hash = hashlib.sha256(payload.new_password.encode()).hexdigest()
    emp.password_hash = pwd_hash
    db.commit()
    
    # Try syncing to Supabase if configured to be absolutely robust
    try:
        from backend.config import SUPABASE_URL, SUPABASE_KEY
        if SUPABASE_URL and SUPABASE_KEY:
            from supabase import create_client
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            supabase.table("employees").update({"password_hash": pwd_hash}).eq("email", emp.email).execute()
    except Exception as e:
        print("Supabase password reset sync skipped:", e)
        
    return {"status": "success", "message": "Password saved permanently in database."}
