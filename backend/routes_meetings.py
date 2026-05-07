"""
Meeting / smart scheduling routes.

== ASSIGNMENT: Feature Devs ==
  - Auto-create meetings.
  - Check availability (future: Google Calendar integration).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models import Meeting
from backend.schemas import MeetingCreate, MeetingOut

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])


@router.post("/", response_model=MeetingOut, status_code=201)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    """Schedule a new meeting."""
    meeting = Meeting(**payload.model_dump())
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/", response_model=List[MeetingOut])
def list_meetings(db: Session = Depends(get_db)):
    """List all scheduled meetings."""
    return db.query(Meeting).all()
