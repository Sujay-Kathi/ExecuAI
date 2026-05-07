"""
IT Admin routes — endpoints accessible by the IT / Admin role.

== ASSIGNMENT: Feature Dev (IT module) ==
  - Manage user access (grant / revoke system permissions)
  - Handle system requests (password resets, software installs)
  - View system health / audit logs

Branch: feature/it-module
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models import Employee, AccessRequest

router = APIRouter(prefix="/api/it", tags=["IT Admin"])


# ── Access Management ────────────────────────────────

@router.post("/access", status_code=201)
def create_access_request(
    employee_id: int,
    system_name: str,
    access_type: str = "read",
    db: Session = Depends(get_db),
):
    """
    Employee or HR requests system access for someone.
    IT Admin reviews and grants/revokes.
    """
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    req = AccessRequest(
        employee_id=employee_id,
        system_name=system_name,
        access_type=access_type,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status, "system": req.system_name}


@router.get("/access", response_model=list)
def list_access_requests(db: Session = Depends(get_db)):
    """List all pending access requests."""
    requests = db.query(AccessRequest).all()
    return [
        {
            "id": r.id,
            "employee_id": r.employee_id,
            "system_name": r.system_name,
            "access_type": r.access_type,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in requests
    ]


@router.patch("/access/{request_id}")
def resolve_access_request(
    request_id: int, action: str, db: Session = Depends(get_db)
):
    """
    IT Admin grants or denies an access request.
    action: 'granted' or 'denied'
    """
    req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found")
    if action not in ("granted", "denied"):
        raise HTTPException(
            status_code=400, detail="Action must be 'granted' or 'denied'"
        )
    req.status = action
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status}


# ── System Requests ──────────────────────────────────

@router.post("/system-request")
def create_system_request(
    employee_id: int,
    request_type: str,
    description: str = "",
    db: Session = Depends(get_db),
):
    """
    Handle IT system requests (password reset, software install, etc.).
    TODO: Feature Dev — create a SystemRequest model and persist.
    """
    return {
        "status": "received",
        "employee_id": employee_id,
        "request_type": request_type,
        "description": description,
        "message": "IT team has been notified.",
    }


# ── System Health ────────────────────────────────────

@router.get("/health")
def system_health():
    """
    Return system health status.
    TODO: Feature Dev — check DB connectivity, API health, etc.
    """
    return {
        "database": "ok",
        "api": "ok",
        "agent": "ok",
        "ml_model_loaded": False,   # TODO: check if model.pkl exists
    }
