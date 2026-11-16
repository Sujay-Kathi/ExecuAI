"""
Focused Test Suite for Meeting Scheduling & Multi-Turn Chat Workflow.

Tests:
1. @mention resolution with actual user ID and verified email.
2. Missing details detection (title, date, start_time, duration, time_zone).
3. Conflict detection and honest reporting.
4. Cancellation flow.
5. Explicit confirmation step before event creation.
6. Calendar credentials missing and API error handling (no fake/simulated links).
7. Generic greeting fix for conversational and context queries.
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.database import init_db, SessionLocal
from backend.models import Employee, Meeting
from backend.auth.routes import list_employees_auth
from agent.agent import AgentController
from agent.meeting_scheduler import MeetingScheduler, get_or_create_session, clear_session

# Ensure DB initialized & seeded
init_db()
db = SessionLocal()
list_employees_auth(db)
db.close()


def test_mention_resolution():
    """Verify real user ID and email are passed through and used."""
    print("Testing @mention resolution...")
    agent = AgentController()
    session_id = "test_mention_res_1"
    clear_session(session_id)

    # 1. Structured mention from UI
    mentioned = [{
        "id": 5,
        "name": "Alice Wang",
        "email": "alice.wang@enterprise.com",
        "role": "HR Specialist"
    }]
    res = agent.process_request(
        user_request="Schedule a meeting tomorrow at 10:00 AM UTC",
        session_id=session_id,
        mentioned_users=mentioned
    )
    assert res["status"] == "success"
    session = get_or_create_session(session_id)
    assert len(session.participants) == 1
    assert session.participants[0]["id"] == 5
    assert session.participants[0]["email"] == "alice.wang@enterprise.com"
    assert session.participants[0]["name"] == "Alice Wang"

    # 2. Text mention matched in DB
    clear_session("test_mention_res_2")
    res2 = agent.process_request(
        user_request="Schedule a meeting with @Bob Smith tomorrow at 2:00 PM UTC",
        session_id="test_mention_res_2"
    )
    session2 = get_or_create_session("test_mention_res_2")
    assert len(session2.participants) == 1
    assert session2.participants[0]["email"] == "bob.smith@enterprise.com"

    # 3. Unmatched mention explains what happened
    clear_session("test_unmatched")
    res3 = agent.process_request(
        user_request="Schedule meeting with @NonExistentColleague",
        session_id="test_unmatched"
    )
    assert res3["status"] == "error"
    assert "Colleague Not Found" in res3["result"]
    assert "@NonExistentColleague" in res3["result"]
    print("  [PASS] @mention resolution")


def test_missing_details():
    """Verify detection and sequential prompting for missing meeting details."""
    print("Testing missing details detection...")
    agent = AgentController()
    session_id = "test_missing_seq"
    clear_session(session_id)

    # Step 1: Only participant provided
    r1 = agent.process_request(
        user_request="Schedule a meeting with @Alice Wang",
        session_id=session_id
    )
    assert r1["status"] == "success"
    missing1 = r1.get("missing_details", [])
    assert any("title" in m.lower() for m in missing1)
    assert any("date" in m.lower() for m in missing1)
    assert any("start time" in m.lower() for m in missing1)

    # Step 2: Supply title
    r2 = agent.process_request(
        user_request="Sprint Planning",
        session_id=session_id
    )
    assert r2["status"] == "success"
    missing2 = r2.get("missing_details", [])
    assert not any("title" in m.lower() for m in missing2)
    assert any("date" in m.lower() for m in missing2)
    assert any("start time" in m.lower() for m in missing2)

    # Step 3: Supply date and time
    r3 = agent.process_request(
        user_request="tomorrow at 10:00 AM UTC",
        session_id=session_id
    )
    assert r3.get("pending_confirmation") is True
    assert "Please Confirm Your Meeting Details" in r3["result"]
    print("  [PASS] Missing details detection")


def test_conflicts_detection():
    """Verify honest conflict detection and reporting."""
    print("Testing conflicts detection...")
    db = SessionLocal()
    conflict_time = datetime.now(timezone.utc) + timedelta(days=5, hours=3)
    existing_meeting = Meeting(
        title="Leadership Strategy Alignment",
        organizer_id=1,
        scheduled_at=conflict_time,
        duration_minutes=60,
        description="Pre-existing board meeting"
    )
    db.add(existing_meeting)
    db.commit()
    db.close()

    agent = AgentController()
    session_id = "test_conflict_check"
    clear_session(session_id)

    target_date = conflict_time.strftime("%Y-%m-%d")
    target_time = conflict_time.strftime("%I:%M %p")

    res = agent.process_request(
        user_request=f"Schedule meeting titled 'Team Review' with @Alice Wang on {target_date} at {target_time} UTC",
        session_id=session_id
    )
    assert res.get("pending_confirmation") is True
    assert "Conflicts Detected" in res["result"] or "conflict" in res["result"].lower()
    assert "Leadership Strategy Alignment" in res["result"]
    print("  [PASS] Conflicts detection and honest reporting")


def test_cancellation():
    """Verify meeting cancellation discards state."""
    print("Testing cancellation flow...")
    agent = AgentController()
    session_id = "test_cancel"
    clear_session(session_id)

    agent.process_request(
        user_request="Schedule meeting with @Alice Wang",
        session_id=session_id
    )
    session = get_or_create_session(session_id)
    assert session.state == "collecting_details"

    cancel_res = agent.process_request(
        user_request="Cancel",
        session_id=session_id,
        confirmation="cancel"
    )
    assert "Cancelled" in cancel_res["result"]
    session_after = get_or_create_session(session_id)
    assert session_after.state == "idle"
    print("  [PASS] Cancellation flow")


def test_confirmation_required():
    """Verify event is NOT created before user confirmation."""
    print("Testing confirmation requirement...")
    db = SessionLocal()
    db.query(Meeting).filter(Meeting.title == "Design Sync").delete()
    db.commit()
    db.close()

    agent = AgentController()
    session_id = "test_confirm_req"
    clear_session(session_id)

    # Initial request with all details
    res = agent.process_request(
        user_request="Schedule meeting titled 'Design Sync' with @Alice Wang tomorrow at 2:00 PM UTC",
        session_id=session_id
    )
    assert res.get("pending_confirmation") is True
    session = get_or_create_session(session_id)
    assert session.state == "awaiting_confirmation"

    # User has not confirmed yet: confirm state remains
    db = SessionLocal()
    created = db.query(Meeting).filter(Meeting.title == "Design Sync").first()
    assert created is None, "Meeting should not be created in DB before confirmation"
    db.close()

    # User confirms
    confirm_res = agent.process_request(
        user_request="Confirm",
        session_id=session_id,
        confirmation="confirm"
    )
    assert confirm_res["status"] in ("success", "calendar_unavailable")

    # Now recorded in DB
    db = SessionLocal()
    created = db.query(Meeting).filter(Meeting.title == "Design Sync").first()
    assert created is not None, "Meeting should be recorded in DB after confirmation"
    db.close()
    print("  [PASS] Confirmation required before creation")


def test_calendar_missing_credentials_and_success():
    """Verify honest reporting when Google Calendar credentials are missing vs present."""
    print("Testing Google Calendar integration handling...")
    agent = AgentController()

    # Case 1: Missing credentials (default when no token file)
    session_id_missing = "test_cal_missing"
    clear_session(session_id_missing)
    agent.process_request(
        user_request="Schedule meeting titled 'Q1 Review' with @Alice Wang tomorrow at 9:00 AM UTC",
        session_id=session_id_missing
    )
    with patch("agent.meeting_scheduler._get_calendar_service", return_value=None):
        res = agent.process_request(
            user_request="Confirm",
            session_id=session_id_missing,
            confirmation="confirm"
        )
        assert res["status"] == "calendar_unavailable"
        assert "Google Calendar credentials are not configured" in res["result"]
        assert "https://calendar.google.com/simulated" not in res["result"], "Must not fake simulated links"

    # Case 2: Calendar API success
    session_id_success = "test_cal_success"
    clear_session(session_id_success)
    agent.process_request(
        user_request="Schedule meeting titled 'Sync 2026' with @Alice Wang tomorrow at 4:00 PM UTC",
        session_id=session_id_success
    )
    mock_event = {
        "created": True,
        "event_id": "real_evt_123",
        "link": "https://calendar.google.com/event?eid=real123",
        "meet_link": "https://meet.google.com/real-abc-xyz",
        "title": "Sync 2026"
    }
    with patch("agent.meeting_scheduler._get_calendar_service", return_value=True):
        with patch("agent.meeting_scheduler.create_real_calendar_event", return_value=mock_event):
            res_success = agent.process_request(
                user_request="Confirm",
                session_id=session_id_success,
                confirmation="confirm"
            )
            assert res_success["status"] == "success"
            assert "Meeting Successfully Scheduled & Confirmed" in res_success["result"]
            assert res_success["event_link"] == "https://calendar.google.com/event?eid=real123"
            assert res_success["meet_link"] == "https://meet.google.com/real-abc-xyz"
    print("  [PASS] Calendar missing credentials and success handling")


def test_generic_greeting_fix():
    """Verify assistant does NOT repeat static greeting for general queries."""
    print("Testing generic greeting fix...")
    clear_session("default")
    clear_session("test_general_queries")
    agent = AgentController()

    # Query 1: capabilities
    r1 = agent.process_request("What can you do?", session_id="test_general_queries")
    assert "Hello! I'm ExecuAI, your enterprise assistant. How can I help you today?" not in r1["result"]
    assert "Meeting Scheduling" in r1["result"]

    # Query 2: how to schedule
    r2 = agent.process_request("How do I schedule a meeting?", session_id="test_general_queries")
    assert "Hello! I'm ExecuAI, your enterprise assistant. How can I help you today?" not in r2["result"]
    assert "@" in r2["result"]

    # Query 3: thanks
    r3 = agent.process_request("Thank you!", session_id="test_general_queries")
    assert "welcome" in r3["result"].lower()
    print("  [PASS] Generic greeting fix")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  ExecuAI Meeting Scheduler & Assistant Test Suite")
    print("=" * 60 + "\n")

    test_mention_resolution()
    test_missing_details()
    test_conflicts_detection()
    test_cancellation()
    test_confirmation_required()
    test_calendar_missing_credentials_and_success()
    test_generic_greeting_fix()

    print("\n" + "=" * 60)
    print("  ALL 7 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 60 + "\n")
