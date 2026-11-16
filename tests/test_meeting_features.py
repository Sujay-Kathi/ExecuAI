*** Begin Patch
*** Add File: tests/test_meeting_features.py
+"""Tests for the extended meeting‑scheduling features.
+
+The repository already contains ``test_meeting_scheduler.py`` which validates the
+core scheduling flow.  This file adds focused tests for:
+
+* ``MeetingScheduler.query_user_meetings`` – today, tomorrow and next‑meeting queries.
+* ``MeetingScheduler.cancel_meeting_by_title`` – CEO‑only enforcement and DB update.
+* ``MeetingScheduler.reschedule_meeting`` – CEO‑only enforcement, date‑time parsing,
+  and participant notification.
+
+All tests use the existing SQLite test database (``backend/database.py``) which is
+created fresh for each test run.  Helper functions populate minimal ``Employee``
+and ``Meeting`` records required for the assertions.
+"""
+
+import pytest
+from datetime import datetime, timedelta, timezone
+
+from agent.meeting_scheduler import MeetingScheduler
+from backend.models import Employee, Meeting
+from backend.database import SessionLocal, Base, engine
+
+
+# ---------------------------------------------------------------------------
+# Test fixtures – create a clean DB for each test
+# ---------------------------------------------------------------------------
+@pytest.fixture(autouse=True)
+def reset_db():
+    """Drop and recreate all tables before each test.
+
+    The production code uses the same SQLite file for tests, so we ensure a clean
+    state to avoid cross‑test contamination.
+    """
+    Base.metadata.drop_all(bind=engine)
+    Base.metadata.create_all(bind=engine)
+    yield
+    Base.metadata.drop_all(bind=engine)
+
+
+def _create_employee(email: str, role: str = "staff", department: str = "General") -> Employee:
+    db = SessionLocal()
+    emp = Employee(name=email.split("@")[0].title(), email=email, role=role, department=department)
+    db.add(emp)
+    db.commit()
+    db.refresh(emp)
+    db.close()
+    return emp
+
+
+def _create_meeting(title: str, organizer: Employee, participants: list[Employee], dt: datetime, duration: int = 30):
+    db = SessionLocal()
+    attendees = [{"id": p.id, "name": p.name, "email": p.email} for p in participants]
+    meeting = Meeting(
+        title=title,
+        organizer_id=organizer.id,
+        scheduled_at=dt,
+        duration_minutes=duration,
+        description="Test meeting",
+        attendees_json=str(attendees),
+        status="scheduled",
+    )
+    db.add(meeting)
+    db.commit()
+    db.refresh(meeting)
+    db.close()
+    return meeting
+
+
+# ---------------------------------------------------------------------------
+# Query tests
+# ---------------------------------------------------------------------------
+def test_query_meetings_today():
+    ceo = _create_employee("ceo@enterprise.com", role="CEO")
+    # Meeting scheduled for today
+    now = datetime.now(timezone.utc)
+    _create_meeting("Today Meeting", ceo, [], now + timedelta(hours=2))
+
+    res = MeetingScheduler.query_user_meetings(user_email=ceo.email, query_text="what are my meetings today")
+    assert res["status"] == "success"
+    assert "Today Meeting" in res["result"]
+
+
+def test_query_next_meeting():
+    ceo = _create_employee("ceo@enterprise.com", role="CEO")
+    # Two meetings in the future
+    now = datetime.now(timezone.utc)
+    _create_meeting("First", ceo, [], now + timedelta(days=1, hours=1))
+    _create_meeting("Second", ceo, [], now + timedelta(days=2))
+
+    res = MeetingScheduler.query_user_meetings(user_email=ceo.email, query_text="when is the next meeting")
+    assert res["status"] == "success"
+    # Should return the earliest future meeting ("First")
+    assert "First" in res["result"]
+
+
+# ---------------------------------------------------------------------------
+# Cancel tests – enforce CEO only
+# ---------------------------------------------------------------------------
+def test_cancel_meeting_by_ceo():
+    ceo = _create_employee("ceo@enterprise.com", role="CEO")
+    now = datetime.now(timezone.utc)
+    meeting = _create_meeting("CancelMe", ceo, [], now + timedelta(hours=1))
+
+    res = MeetingScheduler.cancel_meeting_by_title("CancelMe", user_email=ceo.email, user_role=ceo.role)
+    assert res["status"] == "success"
+    # Verify DB status
+    db = SessionLocal()
+    refreshed = db.query(Meeting).filter(Meeting.id == meeting.id).first()
+    assert refreshed.status == "cancelled"
+    db.close()
+
+
+def test_cancel_meeting_non_ceo_denied():
+    emp = _create_employee("emp@enterprise.com", role="engineer")
+    now = datetime.now(timezone.utc)
+    _create_meeting("NotAllowed", emp, [], now + timedelta(hours=1))
+
+    res = MeetingScheduler.cancel_meeting_by_title("NotAllowed", user_email=emp.email, user_role=emp.role)
+    assert res["status"] == "error"
+    assert MeetingScheduler.CEO_DENIAL_MESSAGE in res["result"]
+
+
+# ---------------------------------------------------------------------------
+# Reschedule tests – CEO only and date parsing
+# ---------------------------------------------------------------------------
+def test_reschedule_meeting_success():
+    ceo = _create_employee("ceo@enterprise.com", role="CEO")
+    now = datetime.now(timezone.utc)
+    meeting = _create_meeting("Resched", ceo, [], now + timedelta(days=1))
+
+    new_date = (now + timedelta(days=3)).strftime("%Y-%m-%d")
+    new_time = "10:30 AM"
+    res = MeetingScheduler.reschedule_meeting(
+        title_keyword="Resched",
+        new_date=new_date,
+        new_time=new_time,
+        user_email=ceo.email,
+        user_role=ceo.role,
+    )
+    assert res["status"] == "success"
+    db = SessionLocal()
+    refreshed = db.query(Meeting).filter(Meeting.id == meeting.id).first()
+    # New scheduled time should match the parsed datetime (UTC)
+    expected_dt = MeetingScheduler.parse_datetime(new_date, new_time)
+    assert refreshed.scheduled_at.replace(tzinfo=timezone.utc) == expected_dt
+    db.close()
+
+
+def test_reschedule_meeting_non_ceo_denied():
+    emp = _create_employee("emp@enterprise.com", role="engineer")
+    now = datetime.now(timezone.utc)
+    _create_meeting("ReschedFail", emp, [], now + timedelta(days=1))
+
+    res = MeetingScheduler.reschedule_meeting(
+        title_keyword="ReschedFail",
+        new_date="tomorrow",
+        new_time="9am",
+        user_email=emp.email,
+        user_role=emp.role,
+    )
+    assert res["status"] == "error"
+    assert MeetingScheduler.CEO_DENIAL_MESSAGE in res["result"]
+
*** End Patch
*** End Patch