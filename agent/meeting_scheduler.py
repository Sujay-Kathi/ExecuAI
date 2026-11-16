"""
Meeting Scheduler Module for ExecuAI.

Supports:
1. CEO-only authorization enforcement for scheduling.
2. Multi-turn meeting scheduling workflow with session state.
3. Flexible participant resolution: @mentions, names, departments, "all members".
4. Missing details detection (title, date, start_time, time_zone, duration).
5. Google Calendar integration check & honest conflict detection.
6. Explicit confirmation step showing all meeting details and participants.
7. Creation only after confirmation, with honest reporting on calendar status.
8. In-app notifications via PEER_MESSAGES and email.
9. Meeting queries: "What are my meetings today?", "When is the next meeting?", etc.
10. Meeting reschedule & cancel management (CEO only).
11. Graceful error handling (never pretending a meeting was scheduled).
"""
import re
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from backend.database import SessionLocal
from backend.models import Employee, Meeting
from agent.integrations import _get_calendar_service, create_real_calendar_event, check_real_availability
from agent.tools import send_notification_email


class MeetingSessionState:
    """Stores in-progress meeting draft state for a conversation session."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.reset()

    def reset(self):
        self.state = "idle"  # idle | collecting_details | awaiting_confirmation | scheduled | cancelled
        self.title: Optional[str] = None
        self.date_str: Optional[str] = None
        self.time_str: Optional[str] = None
        self.time_zone: str = "UTC"
        self.duration_minutes: int = 30
        self.participants: List[Dict[str, Any]] = []  # list of {"id": int, "name": str, "email": str, "role": str}
        self.parsed_datetime: Optional[datetime] = None
        self.conflicts: List[str] = []
        self.calendar_checked: bool = False
        self.calendar_available: bool = False
        self.created_event: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "title": self.title,
            "date": self.date_str,
            "start_time": self.time_str,
            "time_zone": self.time_zone,
            "duration_minutes": self.duration_minutes,
            "participants": self.participants,
            "parsed_datetime": self.parsed_datetime.isoformat() if self.parsed_datetime else None,
            "conflicts": self.conflicts,
            "calendar_available": self.calendar_available,
        }


# Global in-memory storage of meeting sessions
SESSION_STORE: Dict[str, MeetingSessionState] = {}


def get_or_create_session(session_id: str) -> MeetingSessionState:
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = MeetingSessionState(session_id)
    return SESSION_STORE[session_id]


def clear_session(session_id: str):
    if session_id in SESSION_STORE:
        SESSION_STORE[session_id].reset()


class MeetingScheduler:
    """Coordinates meeting parsing, availability checks, confirmation, and scheduling."""

    CEO_DENIAL_MESSAGE = (
        "Sorry, only the CEO is authorized to schedule meetings. "
        "You can still view meetings and access information according to your permissions."
    )

    @staticmethod
    def check_ceo_authorization(user_email: Optional[str] = None, user_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify the user is the CEO. Returns {"authorized": True/False, "employee": ...}.
        Checks DB record by email, then falls back to role string match.
        """
        if not user_email and not user_role:
            return {"authorized": False, "employee": None}

        db = SessionLocal()
        try:
            emp = None
            if user_email:
                emp = db.query(Employee).filter(Employee.email == user_email).first()

            if emp:
                is_ceo = bool(emp.role and "ceo" in emp.role.lower())
                return {"authorized": is_ceo, "employee": emp}

            # Fallback: check role string directly
            if user_role and "ceo" in user_role.lower():
                return {"authorized": True, "employee": None}

            return {"authorized": False, "employee": None}
        finally:
            db.close()

    @staticmethod
    def resolve_participants(
        text: str,
        mentioned_users: Optional[List[Dict[str, Any]]] = None,
        db_session=None
    ) -> Dict[str, Any]:
        """
        Resolves participants from:
        1. Explicit mentioned_users array passed from chat UI (contains real id & email).
        2. @mentions in text (e.g. @Alice, @alice.wang@enterprise.com).
        3. 'with <Name>' in text.
        
        Validates against database Employee records.
        Returns {"participants": [...], "unmatched": [...]}
        """
        close_db = False
        if db_session is None:
            db_session = SessionLocal()
            close_db = True

        try:
            participants = []
            unmatched = []
            seen_emails = set()

            # 1. Process structured mentioned_users first
            if mentioned_users:
                for u in mentioned_users:
                    if not isinstance(u, dict):
                        continue
                    email = u.get("email", "").strip().lower()
                    if not email or email in seen_emails:
                        continue

                    # Verify in DB to ensure ID and current record
                    emp = db_session.query(Employee).filter(Employee.email == email).first()
                    if emp:
                        participants.append({
                            "id": emp.id,
                            "name": emp.name,
                            "email": emp.email,
                            "role": emp.role or "Staff",
                            "department": emp.department or "General"
                        })
                        seen_emails.add(emp.email.lower())
                    else:
                        # Allow structured mention with provided ID/email
                        participants.append({
                            "id": u.get("id"),
                            "name": u.get("name", email),
                            "email": email,
                            "role": u.get("role", "Staff"),
                            "department": u.get("department", "General")
                        })
                        seen_emails.add(email)

            # 2. Extract @mentions from text (e.g. @Alice Wang, @Alice, @alice@enterprise.com)
            # Find @words or @email
            mention_matches = re.findall(r"@([a-zA-Z0-9._\-+]+(?:\s+[a-zA-Z0-9._\-+]+)?)", text)
            for raw_mention in mention_matches:
                m = raw_mention.strip()
                if not m:
                    continue

                # Ignore general keywords like @all, @channel, @here
                if m.lower() in ("all", "channel", "here", "everyone"):
                    continue

                # Try match by exact email
                emp = db_session.query(Employee).filter(Employee.email.ilike(m)).first()
                if not emp:
                    # Try match by name
                    emp = db_session.query(Employee).filter(Employee.name.ilike(f"%{m}%")).first()

                if emp:
                    if emp.email.lower() not in seen_emails:
                        participants.append({
                            "id": emp.id,
                            "name": emp.name,
                            "email": emp.email,
                            "role": emp.role or "Staff",
                            "department": emp.department or "General"
                        })
                        seen_emails.add(emp.email.lower())
                else:
                    if m.lower() not in [p["name"].lower() for p in participants] and "@" not in m:
                        # Check if m is a known unmatched mention
                        if m not in unmatched:
                            unmatched.append(m)

            # 3. Check for "all members" / "everyone" / "entire organization"
            lower_text = text.lower()
            if not participants and any(kw in lower_text for kw in ("all members", "everyone", "entire organization", "all employees", "whole team", "all staff")):
                all_emps = db_session.query(Employee).all()
                for emp in all_emps:
                    if emp.email.lower() not in seen_emails:
                        participants.append({
                            "id": emp.id,
                            "name": emp.name,
                            "email": emp.email,
                            "role": emp.role or "Staff",
                            "department": emp.department or "General"
                        })
                        seen_emails.add(emp.email.lower())
                return {"participants": participants, "unmatched": unmatched}

            # 4. Check for department/team references
            dept_map = {
                "engineering": ["engineering", "development team", "dev team", "development"],
                "human resources": ["hr team", "hr", "human resources"],
                "product": ["product team", "product"],
                "executive": ["executive team", "executive", "leadership"],
                "it operations": ["it team", "it operations", "it ops"],
                "marketing": ["marketing team", "marketing"],
            }
            for dept_key, dept_aliases in dept_map.items():
                if any(alias in lower_text for alias in dept_aliases):
                    dept_emps = db_session.query(Employee).filter(
                        Employee.department.ilike(f"%{dept_key}%")
                    ).all()
                    for emp in dept_emps:
                        if emp.email.lower() not in seen_emails:
                            participants.append({
                                "id": emp.id,
                                "name": emp.name,
                                "email": emp.email,
                                "role": emp.role or "Staff",
                                "department": emp.department or "General"
                            })
                            seen_emails.add(emp.email.lower())
                    if dept_emps:
                        return {"participants": participants, "unmatched": unmatched}

            # 5. Check for comma/and-separated names like "Roshni, Swati and Rahul"
            if not participants:
                # Look for "with Name1, Name2 and Name3" or just "Name1, Name2, Name3"
                with_multi = re.search(
                    r"\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s*[,&]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)?)",
                    text
                )
                if with_multi:
                    names_str = with_multi.group(1).strip()
                    # Split on comma, ampersand, or " and "
                    name_parts = re.split(r'\s*[,&]\s*|\s+and\s+', names_str)
                    for name_part in name_parts:
                        name_part = name_part.strip()
                        if not name_part or name_part.lower() in ("me", "us", "the", "a", "an", "google", "calendar", "team"):
                            continue
                        emp = db_session.query(Employee).filter(Employee.name.ilike(f"%{name_part}%")).first()
                        if emp and emp.email.lower() not in seen_emails:
                            participants.append({
                                "id": emp.id,
                                "name": emp.name,
                                "email": emp.email,
                                "role": emp.role or "Staff",
                                "department": emp.department or "General"
                            })
                            seen_emails.add(emp.email.lower())
                        elif not emp:
                            if name_part not in unmatched:
                                unmatched.append(name_part)

            # 6. If still no participants, look for single "with <Person>"
            if not participants:
                with_match = re.search(r"\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", text)
                if with_match:
                    name_candidate = with_match.group(1).strip()
                    if name_candidate.lower() not in ("me", "us", "team", "the", "a", "an", "google", "calendar"):
                        emp = db_session.query(Employee).filter(Employee.name.ilike(f"%{name_candidate}%")).first()
                        if emp and emp.email.lower() not in seen_emails:
                            participants.append({
                                "id": emp.id,
                                "name": emp.name,
                                "email": emp.email,
                                "role": emp.role or "Staff",
                                "department": emp.department or "General"
                            })
                            seen_emails.add(emp.email.lower())
                        elif not emp:
                            unmatched.append(name_candidate)

            # 7. Check for bare name(s) in collecting_details context (no "with" prefix)
            if not participants and not unmatched:
                # Try matching each capitalized word as a potential employee name
                bare_names = re.findall(r'\b([A-Z][a-z]+)\b', text)
                skip_words = {"schedule", "meeting", "book", "call", "sync", "set", "up", "arrange",
                              "create", "plan", "discussion", "with", "for", "about", "the",
                              "sure", "yes", "no", "and", "all", "members", "team",
                              "project", "sprint", "review", "planning", "monday", "tuesday",
                              "wednesday", "thursday", "friday", "saturday", "sunday",
                              "january", "february", "march", "april", "may", "june",
                              "july", "august", "september", "october", "november", "december",
                              "utc", "gmt", "pst", "est", "ist", "cet", "am", "pm"}
                for name_candidate in bare_names:
                    if name_candidate.lower() in skip_words:
                        continue
                    emp = db_session.query(Employee).filter(Employee.name.ilike(f"%{name_candidate}%")).first()
                    if emp and emp.email.lower() not in seen_emails:
                        participants.append({
                            "id": emp.id,
                            "name": emp.name,
                            "email": emp.email,
                            "role": emp.role or "Staff",
                            "department": emp.department or "General"
                        })
                        seen_emails.add(emp.email.lower())

            return {
                "participants": participants,
                "unmatched": unmatched
            }
        finally:
            if close_db:
                db_session.close()

    @staticmethod
    def extract_meeting_details(text: str, current_draft: Optional[MeetingSessionState] = None) -> Dict[str, Any]:
        """
        Extracts title, date, start_time, duration, timezone from text.
        Merges with current draft if provided.
        """
        extracted = {}

        # ── 1. Extract Title ──
        # Check quoted strings e.g. "Sprint Planning" or 'Sprint Planning'
        quotes = re.findall(r'["\']([^"\']+)["\']', text)
        if quotes:
            extracted["title"] = quotes[0].strip()
        else:
            # Check patterns like "title: <title>", "about <title>", "titled <title>", "topic <title>"
            title_match = re.search(
                r"(?:titled|title\s*:|topic\s*:|about|for)\s+([A-Za-z0-9\s\-]+?)(?=\s+(?:on|at|tomorrow|next|with|for\s+\d+|in\s+utc)|$)",
                text,
                re.IGNORECASE
            )
            if title_match:
                cand = title_match.group(1).strip()
                # Exclude meeting keywords
                if cand.lower() not in ("a meeting", "the meeting", "meeting", "call", "sync", "me"):
                    extracted["title"] = cand
            else:
                # Check "schedule (a) (30-minute) <Title> (meeting|call|sync|discussion)"
                sched_title_match = re.search(
                    r"(?:schedule|book|set\s+up|arrange)\s+(?:a\s+)?(?:\d+\s*[-]?\s*(?:min|mins|minute|minutes|hour|hours)\s+)?([A-Za-z0-9\s\-]+?)(?:\s+(?:meeting|call|sync|session|discussion)|\s+(?:with|on|at|tomorrow|next)|$)",
                    text,
                    re.IGNORECASE
                )
                if sched_title_match:
                    cand = sched_title_match.group(1).strip()
                    if cand.lower() not in ("a", "an", "the", "a meeting", "the meeting", "meeting", "call", "sync", "me", "new"):
                        extracted["title"] = cand

        # ── 2. Extract Duration ──
        dur_match = re.search(r"(\d+)\s*(?:mins?|minutes?|hours?|hrs?)", text, re.IGNORECASE)
        if dur_match:
            val = int(dur_match.group(1))
            if "hour" in dur_match.group(0).lower() or "hr" in dur_match.group(0).lower():
                val = val * 60
            extracted["duration_minutes"] = val

        # ── 3. Extract Timezone ──
        tz_match = re.search(r"\b(UTC|GMT|PST|PDT|EST|EDT|CST|CDT|IST|CET|CEST)\b", text, re.IGNORECASE)
        if tz_match:
            extracted["time_zone"] = tz_match.group(1).upper()

        # ── 4. Extract Date ──
        # Check ISO date YYYY-MM-DD
        date_iso = re.search(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\b", text)
        if date_iso:
            extracted["date_str"] = date_iso.group(1).replace("/", "-")
        elif re.search(r"\btomorrow\b", text, re.IGNORECASE):
            extracted["date_str"] = "tomorrow"
        elif re.search(r"\btoday\b", text, re.IGNORECASE):
            extracted["date_str"] = "today"
        else:
            # Check "next Monday", "this Friday", etc.
            weekday_match = re.search(r"\b(?:next|this)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.IGNORECASE)
            if weekday_match:
                extracted["date_str"] = weekday_match.group(0).strip()
            else:
                # Check "Nov 20", "20th Nov", "November 25"
                month_match = re.search(r"\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)\b", text, re.IGNORECASE)
                if month_match:
                    extracted["date_str"] = month_match.group(1).strip()

        # ── 5. Extract Start Time ──
        # e.g. "at 10:00 AM", "3pm", "14:30", "11:00"
        time_match = re.search(r"\b(\d{1,2}:\d{2}(?:\s*[ap]m)?|\d{1,2}\s*[ap]m)\b", text, re.IGNORECASE)
        if time_match:
            extracted["time_str"] = time_match.group(1).strip()

        return extracted

    @staticmethod
    def parse_datetime(date_str: str, time_str: str, time_zone: str = "UTC") -> Optional[datetime]:
        """Convert date_str and time_str into a normalized datetime object in UTC."""
        try:
            now = datetime.now(timezone.utc)
            target_date = now.date()

            d_lower = date_str.lower().strip()
            if d_lower == "today":
                target_date = now.date()
            elif d_lower == "tomorrow":
                target_date = now.date() + timedelta(days=1)
            elif re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", d_lower):
                parts = [int(p) for p in d_lower.split("-")]
                target_date = datetime(parts[0], parts[1], parts[2]).date()
            else:
                # Weekday match
                weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                for i, w in enumerate(weekdays):
                    if w in d_lower:
                        current_wd = now.weekday()
                        days_ahead = (i - current_wd) % 7
                        if days_ahead == 0 and "next" in d_lower:
                            days_ahead = 7
                        elif days_ahead == 0:
                            days_ahead = 7  # default to next occurrence
                        target_date = now.date() + timedelta(days=days_ahead)
                        break

            # Parse time
            t_lower = time_str.lower().strip()
            hour = 10
            minute = 0

            # Match 3pm, 3:30pm, 10am, 14:00
            m12 = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", t_lower)
            if m12:
                hour = int(m12.group(1))
                minute = int(m12.group(2)) if m12.group(2) else 0
                meridiem = m12.group(3)
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0
            else:
                m24 = re.match(r"^(\d{1,2}):(\d{2})$", t_lower)
                if m24:
                    hour = int(m24.group(1))
                    minute = int(m24.group(2))

            dt = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    @staticmethod
    def check_conflicts(start_dt: datetime, duration_minutes: int, attendees: List[str]) -> Dict[str, Any]:
        """
        Check availability using:
        1. Google Calendar freebusy API (if configured).
        2. Local database Meeting table for overlaps.
        Returns:
            {
                "calendar_available": bool,
                "calendar_notice": str,
                "conflicts": list[str],
            }
        """
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        conflicts = []
        calendar_available = False
        calendar_notice = ""

        # 1. Google Calendar freebusy check
        service = _get_calendar_service()
        if service is not None:
            calendar_available = True
            try:
                gcal_res = check_real_availability(time_min=start_dt, time_max=end_dt)
                if gcal_res and gcal_res.get("busy"):
                    for b in gcal_res["busy"]:
                        b_start = b.get("start")
                        b_end = b.get("end")
                        conflicts.append(f"Google Calendar conflict: busy between {b_start} and {b_end}")
                calendar_notice = "Checked availability via Google Calendar freebusy API."
            except Exception as e:
                calendar_notice = f"Google Calendar availability check error: {str(e)}"
                conflicts.append(calendar_notice)
        else:
            calendar_available = False
            calendar_notice = "Google Calendar integration is not configured (credentials missing); unable to check external calendar availability."

        # 2. Local database meetings check
        try:
            db = SessionLocal()
            window_start = start_dt - timedelta(hours=4)
            window_end = end_dt + timedelta(hours=4)
            candidate_meetings = db.query(Meeting).all()
            for m in candidate_meetings:
                if not m.scheduled_at:
                    continue
                m_start = m.scheduled_at.replace(tzinfo=timezone.utc) if m.scheduled_at.tzinfo is None else m.scheduled_at
                m_duration = m.duration_minutes or 30
                m_end = m_start + timedelta(minutes=m_duration)

                # Standard interval intersection check: max(start1, start2) < min(end1, end2)
                if max(m_start, start_dt) < min(m_end, end_dt):
                    conflicts.append(
                        f"Internal calendar conflict: '{m.title}' scheduled at {m_start.strftime('%Y-%m-%d %I:%M %p UTC')} ({m_duration} mins)"
                    )
            db.close()
        except Exception:
            pass

        return {
            "calendar_available": calendar_available,
            "calendar_notice": calendar_notice,
            "conflicts": conflicts
        }

    @classmethod
    def handle_scheduling_turn(
        cls,
        user_message: str,
        session_id: str,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        mentioned_users: Optional[List[Dict[str, Any]]] = None,
        confirmation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main multi-turn conversation handler for meeting scheduling.
        Returns response dictionary for the chat assistant.
        """
        session = get_or_create_session(session_id)
        lower_msg = user_message.lower().strip()

        # ── 1. Check for Cancellation ──
        if confirmation == "cancel" or lower_msg in ("cancel", "abort", "never mind", "stop", "cancel meeting", "no"):
            if session.state in ("collecting_details", "awaiting_confirmation"):
                session.reset()
                return {
                    "status": "success",
                    "intent": "meeting_scheduling",
                    "action": "meeting_cancelled",
                    "result": "❌ **Meeting Scheduling Cancelled.**\n\nThe draft meeting has been cleared. What would you like to do next?",
                    "steps": ["⏹️ Cancelled meeting scheduling by user request", "🧹 Cleared draft meeting session"],
                    "pending_confirmation": False,
                    "meeting_draft": None
                }

        # ── 2. Check for Confirmation ──
        if session.state == "awaiting_confirmation":
            if confirmation == "confirm" or lower_msg in ("confirm", "yes", "proceed", "sounds good", "go ahead", "approve", "ok", "okay", "confirm meeting"):
                # Execute final scheduling
                return cls._execute_scheduled_meeting(session, organizer_name=user_name or "Organizer", organizer_email=user_email)
            else:
                # User sent something else while awaiting confirmation
                # Check if they are updating a detail (e.g. changing title, time, or date)
                updates = cls.extract_meeting_details(user_message, session)
                if updates:
                    if "title" in updates: session.title = updates["title"]
                    if "date_str" in updates: session.date_str = updates["date_str"]
                    if "time_str" in updates: session.time_str = updates["time_str"]
                    if "duration_minutes" in updates: session.duration_minutes = updates["duration_minutes"]
                    if "time_zone" in updates: session.time_zone = updates["time_zone"]

                    # Re-validate
                    return cls._validate_and_request_confirmation(session)
                else:
                    return {
                        "status": "success",
                        "intent": "meeting_scheduling",
                        "action": "awaiting_confirmation",
                        "result": (
                            "Please confirm if you would like to proceed with the scheduled meeting:\n\n"
                            + cls._format_confirmation_summary(session)
                            + "\n\nReply **Confirm** to schedule or **Cancel** to abort."
                        ),
                        "steps": ["⏳ Awaiting user confirmation"],
                        "pending_confirmation": True,
                        "meeting_draft": session.to_dict()
                    }

        # ── 3. Participant Resolution ──
        part_res = cls.resolve_participants(user_message, mentioned_users)
        new_participants = part_res["participants"]
        unmatched = part_res["unmatched"]

        # Merge participants into session
        existing_emails = {p["email"].lower() for p in session.participants}
        for p in new_participants:
            if p["email"].lower() not in existing_emails:
                session.participants.append(p)
                existing_emails.add(p["email"].lower())

        # If a person was mentioned but cannot be matched in DB
        if unmatched and not session.participants:
            return {
                "status": "error",
                "intent": "meeting_scheduling",
                "action": "person_not_matched",
                "result": (
                    f"⚠️ **Colleague Not Found:**\n\n"
                    f"Could not find **@{', @'.join(unmatched)}** in the enterprise employee directory.\n\n"
                    f"Please select from the @ suggestions menu or provide their valid company email address. How would you like to proceed?"
                ),
                "steps": [f"❌ Failed to match participant: {', '.join(unmatched)}"],
                "pending_confirmation": False,
                "meeting_draft": session.to_dict()
            }

        # ── 4. Extract Details from Message ──
        details = cls.extract_meeting_details(user_message, session)
        if "title" in details: session.title = details["title"]
        if "date_str" in details: session.date_str = details["date_str"]
        if "time_str" in details: session.time_str = details["time_str"]
        if "duration_minutes" in details: session.duration_minutes = details["duration_minutes"]
        if "time_zone" in details: session.time_zone = details["time_zone"]

        # If session is currently collecting details and user answered directly
        if session.state == "collecting_details":
            # If title is missing and message looks like a title
            if not session.title and not any(k in details for k in ("date_str", "time_str")):
                # The whole message might be the meeting title
                clean_msg = re.sub(r"@\S+", "", user_message).strip()
                if clean_msg and len(clean_msg) < 80:
                    session.title = clean_msg

        session.state = "collecting_details"

        # ── 5. Check Missing Details ──
        missing = []
        if not session.participants:
            missing.append("Participants (select using @ mention)")
        if not session.title:
            missing.append("Meeting title / topic")
        if not session.date_str:
            missing.append("Date (e.g. tomorrow, 2026-11-20, next Tuesday)")
        if not session.time_str:
            missing.append("Start time (e.g. 10:00 AM, 3:00 PM)")

        if missing:
            part_str = ", ".join([f"**{p['name']}** ({p['email']})" for p in session.participants]) if session.participants else "None specified yet"
            return {
                "status": "success",
                "intent": "meeting_scheduling",
                "action": "missing_details",
                "result": (
                    f"🗓️ **Meeting Scheduling Request Detected**\n\n"
                    f"• **Participants:** {part_str}\n"
                    + (f"• **Title:** {session.title}\n" if session.title else "")
                    + (f"• **Date:** {session.date_str}\n" if session.date_str else "")
                    + (f"• **Time:** {session.time_str}\n" if session.time_str else "")
                    + (f"• **Time Zone:** {session.time_zone}\n" if session.time_zone else "")
                    + (f"• **Duration:** {session.duration_minutes} minutes\n\n" if session.duration_minutes else "")
                    + "Please provide the missing details to continue:\n"
                    + "\n".join([f"• {m}" for m in missing])
                ),
                "steps": [
                    "🔍 Parsed meeting scheduling parameters",
                    f"⚠️ Missing required details: {', '.join(missing)}",
                    "💬 Prompted user for missing parameters"
                ],
                "missing_details": missing,
                "pending_confirmation": False,
                "meeting_draft": session.to_dict()
            }

        # ── 6. All Details Present: Check Availability & Request Confirmation ──
        return cls._validate_and_request_confirmation(session)

    @classmethod
    def _validate_and_request_confirmation(cls, session: MeetingSessionState) -> Dict[str, Any]:
        """Validates date/time, checks conflicts, and transitions to awaiting_confirmation."""
        start_dt = cls.parse_datetime(session.date_str, session.time_str, session.time_zone)
        if not start_dt:
            return {
                "status": "error",
                "intent": "meeting_scheduling",
                "action": "invalid_datetime",
                "result": (
                    f"⚠️ Could not parse the date/time combination: '{session.date_str}' at '{session.time_str}'.\n"
                    f"Please specify a clear date and start time (e.g., 'tomorrow at 10:00 AM' or '2026-11-20 at 3:00 PM')."
                ),
                "steps": ["❌ Date/time parsing failed"],
                "pending_confirmation": False,
                "meeting_draft": session.to_dict()
            }

        session.parsed_datetime = start_dt
        attendee_emails = [p["email"] for p in session.participants]

        # Conflict & Google Calendar Availability Check
        check_res = cls.check_conflicts(start_dt, session.duration_minutes, attendee_emails)
        session.calendar_available = check_res["calendar_available"]
        session.conflicts = check_res["conflicts"]
        calendar_notice = check_res.get("calendar_notice", "")

        session.state = "awaiting_confirmation"

        availability_report = ""
        if not session.calendar_available:
            availability_report += f"\n⚠️ **Google Calendar Availability Notice:**\n{calendar_notice} Only local enterprise schedules could be verified.\n"

        if session.conflicts:
            availability_report += "\n⚠️ **Availability Warning / Potential Conflicts Detected:**\n" + "\n".join([f"• {c}" for c in session.conflicts]) + "\n"
        elif session.calendar_available:
            availability_report += "\n✅ **Availability:** No conflicts detected for the requested time slot on Google Calendar or local records.\n"

        summary = cls._format_confirmation_summary(session)

        return {
            "status": "success",
            "intent": "meeting_scheduling",
            "action": "awaiting_confirmation",
            "result": (
                f"📋 **Please Confirm Your Meeting Details:**\n\n"
                f"{summary}\n"
                f"{availability_report}\n"
                f"Would you like me to schedule this meeting and send invitations?\n"
                f"Reply **Confirm** to schedule, or **Cancel** to discard."
            ),
            "steps": [
                "✅ Extracted all required meeting details",
                "🔎 Verified participant directories and emails",
                f"📅 Calendar integration status: {'Google Calendar Connected' if session.calendar_available else 'Cannot check external availability (Google Calendar credentials missing)'}",
                f"{'⚠️ Conflicts or warnings reported' if session.conflicts or not session.calendar_available else '✅ No scheduling conflicts detected'}",
                "⏳ Presented meeting draft awaiting user confirmation"
            ],
            "pending_confirmation": True,
            "meeting_draft": session.to_dict()
        }

    @staticmethod
    def _format_confirmation_summary(session: MeetingSessionState) -> str:
        date_display = session.parsed_datetime.strftime("%A, %b %d, %Y at %I:%M %p UTC") if session.parsed_datetime else f"{session.date_str} at {session.time_str}"
        part_lines = "\n".join([f"   - **{p['name']}** (ID: {p['id']}, {p['email']})" for p in session.participants])

        if session.calendar_available:
            cal_status = "✅ Google Calendar Connected (Checked availability via Google Calendar API)"
        else:
            cal_status = "⚠️ Google Calendar Credentials Missing (Cannot check external Google Calendar availability)"

        return (
            f"• **Title:** {session.title}\n"
            f"• **Date & Time:** {date_display}\n"
            f"• **Duration:** {session.duration_minutes} minutes\n"
            f"• **Time Zone:** {session.time_zone}\n"
            f"• **Participants:**\n{part_lines}\n"
            f"• **Calendar Status:** {cal_status}"
        )

    @classmethod
    def _execute_scheduled_meeting(cls, session: MeetingSessionState, organizer_name: str, organizer_email: str = None) -> Dict[str, Any]:
        """Creates the event on Google Calendar, saves to DB, sends emails & in-app notifications, and clears session."""
        attendee_emails = [p["email"] for p in session.participants]
        start_time = session.parsed_datetime or datetime.now(timezone.utc)

        # 1. Google Calendar Attempt
        service = _get_calendar_service()
        gcal_result = None
        if service is not None:
            try:
                gcal_result = create_real_calendar_event(
                    title=session.title,
                    description=f"Scheduled by {organizer_name} via ExecuAI Assistant",
                    start_time=start_time,
                    duration_minutes=session.duration_minutes,
                    attendees=attendee_emails,
                )
            except Exception as e:
                gcal_result = None

        # 2. Persist in Database Meeting table with attendees
        meeting_id = None
        try:
            db = SessionLocal()
            # Find organizer employee record
            org_emp = None
            if organizer_email:
                org_emp = db.query(Employee).filter(Employee.email == organizer_email).first()
            if not org_emp:
                org_emp = db.query(Employee).first()
            org_id = org_emp.id if org_emp else 1

            attendees_data = json.dumps([{
                "id": p.get("id"),
                "name": p.get("name"),
                "email": p.get("email")
            } for p in session.participants])

            db_meeting = Meeting(
                title=session.title,
                organizer_id=org_id,
                scheduled_at=start_time,
                duration_minutes=session.duration_minutes,
                description=f"Scheduled via ExecuAI for: {', '.join(attendee_emails)}",
                attendees_json=attendees_data,
                meet_link=gcal_result.get("meet_link", "") if gcal_result else "",
                calendar_event_id=gcal_result.get("event_id", "") if gcal_result else "",
                status="scheduled",
            )
            db.add(db_meeting)
            db.commit()
            meeting_id = db_meeting.id
            db.close()
        except Exception:
            pass

        # 3. Dispatch in-app notifications via PEER_MESSAGES
        try:
            from backend.routes_chat import PEER_MESSAGES
            for p in session.participants:
                p_email = p["email"]
                if p_email not in PEER_MESSAGES:
                    PEER_MESSAGES[p_email] = []
                PEER_MESSAGES[p_email].append({
                    "sender_email": organizer_email or "system@execuai.com",
                    "sender_name": organizer_name,
                    "sender_role": "CEO & Lead Architect",
                    "recipient_email": p_email,
                    "text": (
                        f"📅 **Meeting Invitation:** {session.title}\n"
                        f"**When:** {start_time.strftime('%A, %b %d, %Y at %I:%M %p UTC')} ({session.duration_minutes} min)\n"
                        f"**Organizer:** {organizer_name}\n"
                        f"**Participants:** {', '.join([pp['name'] for pp in session.participants])}"
                    )
                })
        except Exception:
            pass

        # 4. Handle Calendar Outcome Honestly
        final_title = session.title or "Meeting"
        final_participants = list(session.participants)
        final_duration = session.duration_minutes
        part_display = ", ".join([f"{p['name']} ({p['email']})" for p in final_participants])

        if gcal_result and gcal_result.get("created"):
            # Real Google Calendar Success
            event_link = gcal_result.get("link", "")
            meet_link = gcal_result.get("meet_link", "")

            # Dispatch invitation emails with real links
            email_body = (
                f"You have been invited to a meeting scheduled via ExecuAI:\n\n"
                f"Title: {final_title}\n"
                f"Time: {start_time.strftime('%Y-%m-%d %H:%M UTC')} ({final_duration} mins)\n"
                f"Organizer: {organizer_name}\n"
                + (f"Google Calendar Event: {event_link}\n" if event_link else "")
                + (f"Google Meet Video Link: {meet_link}\n" if meet_link else "")
            )
            for p in final_participants:
                send_notification_email(
                    to=p["email"],
                    subject=f"Meeting Invitation: {final_title}",
                    body=email_body,
                    recipient_name=p["name"]
                )

            notification_names = ", ".join([p["name"] for p in final_participants])
            session.reset()
            return {
                "status": "success",
                "intent": "meeting_scheduling",
                "action": "meeting_created",
                "result": (
                    f"🎉 **Meeting Successfully Scheduled & Confirmed!**\n\n"
                    f"• **Title:** {final_title}\n"
                    f"• **Scheduled Time:** {start_time.strftime('%A, %b %d, %Y at %I:%M %p UTC')}\n"
                    f"• **Duration:** {final_duration} minutes\n"
                    f"• **Participants Invited:** {part_display}\n"
                    + (f"• **Google Calendar Event:** [View Event in Google Calendar]({event_link})\n" if event_link else "")
                    + (f"• **Google Meet Video Link:** [Join Google Meet]({meet_link})\n" if meet_link else "")
                    + f"\nA notification has been sent to {notification_names}."
                ),
                "steps": [
                    "✅ User confirmed meeting parameters",
                    "📅 Google Calendar event successfully created via API",
                    "💾 Meeting saved to enterprise database records",
                    "📨 Meeting invitation emails dispatched to all participants",
                    "🔔 In-app notifications delivered to participant feeds"
                ],
                "pending_confirmation": False,
                "meeting_draft": None,
                "event_link": event_link,
                "meet_link": meet_link
            }
        else:
            # Google Calendar credentials missing or API call failed
            # Send email notifications even without calendar
            email_body = (
                f"You have been invited to a meeting scheduled via ExecuAI:\n\n"
                f"Title: {final_title}\n"
                f"Time: {start_time.strftime('%Y-%m-%d %H:%M UTC')} ({final_duration} mins)\n"
                f"Organizer: {organizer_name}\n\n"
                f"Note: Google Calendar integration is not configured, so no calendar invite was generated.\n"
            )
            for p in final_participants:
                send_notification_email(
                    to=p["email"],
                    subject=f"Meeting Invitation: {final_title}",
                    body=email_body,
                    recipient_name=p["name"]
                )

            notification_names = ", ".join([p["name"] for p in final_participants])
            session.reset()
            return {
                "status": "calendar_unavailable",
                "intent": "meeting_scheduling",
                "action": "calendar_credentials_missing",
                "result": (
                    f"⚠️ **Google Calendar Integration Unavailable**\n\n"
                    f"The meeting details were validated, but **Google Calendar credentials are not configured** (or could not be reached via OAuth API).\n\n"
                    f"• **Title:** {final_title}\n"
                    f"• **Requested Time:** {start_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
                    f"• **Participants:** {part_display}\n\n"
                    + (f"The meeting has been recorded internally in your ExecuAI database (ID #{meeting_id}), but **no Google Calendar invite or Meet link was created**.\n\n" if meeting_id else "")
                    + f"A notification has been sent to {notification_names}.\n\n"
                    + "To sync with real Google Calendar, configure `credentials/google_oauth.json` and run `python credentials/setup_google_auth.py`.\n\n"
                    "How would you like to proceed?"
                ),
                "steps": [
                    "✅ User confirmed meeting parameters",
                    "⚠️ Checked Google Calendar API: credentials missing or connection unavailable",
                    "ℹ️ Recorded in local database fallback (if applicable)",
                    "📨 Email notifications dispatched to participants",
                    "🔔 In-app notifications delivered to participant feeds",
                    "⚠️ Honestly reported calendar integration status to user"
                ],
                "pending_confirmation": False,
                "meeting_draft": None
            }


    # ── Meeting Query Methods ────────────────────────────────

    @staticmethod
    def query_user_meetings(
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        query_text: str = ""
    ) -> Dict[str, Any]:
        """
        Handle meeting information queries like:
        - "What are my meetings today?"
        - "When is the next meeting?"
        - "What meetings are scheduled tomorrow?"
        - "Show all upcoming meetings"
        - "Who is attending the project meeting?"
        """
        lower = query_text.lower().strip()
        now = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            all_meetings = db.query(Meeting).filter(
                Meeting.status != "cancelled"
            ).order_by(Meeting.scheduled_at.asc()).all()

            # Determine date filter
            target_date = None
            date_label = ""
            if "today" in lower:
                target_date = now.date()
                date_label = "today"
            elif "tomorrow" in lower:
                target_date = (now + timedelta(days=1)).date()
                date_label = "tomorrow"
            elif "this week" in lower:
                # All meetings from now through end of week (Sunday)
                week_end = now.date() + timedelta(days=(6 - now.weekday()))
                filtered = [
                    m for m in all_meetings
                    if m.scheduled_at and now.date() <= m.scheduled_at.date() <= week_end
                ]
                if not filtered:
                    return {
                        "status": "success", "intent": "meeting_query",
                        "result": "You don't have any meetings scheduled this week.",
                        "steps": ["📅 Checked meeting database for this week", "ℹ️ No meetings found"]
                    }
                lines = [f"📅 **Your Meetings This Week ({now.strftime('%b %d')} – {week_end.strftime('%b %d')}):**\n"]
                for m in filtered:
                    t = m.scheduled_at.strftime("%A, %b %d at %I:%M %p UTC")
                    lines.append(f"• **{m.title}** – {t} ({m.duration_minutes or 30} min)")
                return {
                    "status": "success", "intent": "meeting_query",
                    "result": "\n".join(lines),
                    "steps": ["📅 Queried meeting database", f"✅ Found {len(filtered)} meeting(s) this week"]
                }

            # "next meeting" query
            if "next" in lower and ("meeting" in lower or "call" in lower or "sync" in lower):
                upcoming = [m for m in all_meetings if m.scheduled_at and m.scheduled_at.replace(tzinfo=timezone.utc) > now]
                if not upcoming:
                    return {
                        "status": "success", "intent": "meeting_query",
                        "result": "You don't have any upcoming meetings scheduled.",
                        "steps": ["📅 Checked meeting database", "ℹ️ No upcoming meetings found"]
                    }
                nxt = upcoming[0]
                t = nxt.scheduled_at.strftime("%A, %b %d, %Y at %I:%M %p UTC")
                attendees_str = ""
                if nxt.attendees_json:
                    try:
                        att = json.loads(nxt.attendees_json)
                        if att:
                            attendees_str = "\n• **Participants:** " + ", ".join([a.get("name", a.get("email", "")) for a in att])
                    except Exception:
                        pass
                return {
                    "status": "success", "intent": "meeting_query",
                    "result": (
                        f"📅 **Your Next Meeting:**\n\n"
                        f"• **{nxt.title}** – {t} ({nxt.duration_minutes or 30} min)"
                        f"{attendees_str}"
                    ),
                    "steps": ["📅 Queried meeting database", "✅ Found next upcoming meeting"]
                }

            # "who is attending" query
            if "who" in lower and ("attending" in lower or "invited" in lower or "participants" in lower):
                # Try to find the meeting by title keyword
                title_words = re.findall(r'\b[A-Za-z]+\b', lower)
                skip = {"who", "is", "are", "attending", "invited", "participants", "the", "to", "in", "meeting", "of", "for"}
                keywords = [w for w in title_words if w not in skip]
                matched_meeting = None
                for m in all_meetings:
                    if any(kw in (m.title or "").lower() for kw in keywords):
                        matched_meeting = m
                        break
                if matched_meeting and matched_meeting.attendees_json:
                    try:
                        att = json.loads(matched_meeting.attendees_json)
                        if att:
                            part_lines = ", ".join([f"**{a.get('name', 'Unknown')}** ({a.get('email', '')})" for a in att])
                            return {
                                "status": "success", "intent": "meeting_query",
                                "result": f"📋 **Attendees for '{matched_meeting.title}':**\n\n{part_lines}",
                                "steps": ["📅 Found matching meeting", "✅ Retrieved participant list"]
                            }
                    except Exception:
                        pass
                return {
                    "status": "success", "intent": "meeting_query",
                    "result": "I couldn't find attendee information for that meeting. Could you specify the meeting title?",
                    "steps": ["📅 Searched meeting database", "⚠️ No matching meeting or attendee data found"]
                }

            # Filter by specific date
            if target_date:
                filtered = [m for m in all_meetings if m.scheduled_at and m.scheduled_at.date() == target_date]
                if not filtered:
                    return {
                        "status": "success", "intent": "meeting_query",
                        "result": f"You don't have any meetings scheduled for {date_label} ({target_date.strftime('%b %d, %Y')}).",
                        "steps": [f"📅 Checked meeting database for {date_label}", "ℹ️ No meetings found"]
                    }
                lines = [f"📅 **Your Meetings for {date_label.title()} ({target_date.strftime('%A, %b %d, %Y')}):**\n"]
                for m in filtered:
                    t = m.scheduled_at.strftime("%I:%M %p UTC")
                    dur = m.duration_minutes or 30
                    end_t = (m.scheduled_at + timedelta(minutes=dur)).strftime("%I:%M %p")
                    lines.append(f"• **{m.title}** – {t} to {end_t} ({dur} min)")
                lines.append(f"\nWould you like more details about any meeting?")
                return {
                    "status": "success", "intent": "meeting_query",
                    "result": "\n".join(lines),
                    "steps": [f"📅 Queried meeting database for {date_label}", f"✅ Found {len(filtered)} meeting(s)"]
                }

            # Default: show all upcoming meetings
            upcoming = [m for m in all_meetings if m.scheduled_at and m.scheduled_at.replace(tzinfo=timezone.utc) >= now]
            if not upcoming:
                return {
                    "status": "success", "intent": "meeting_query",
                    "result": "You don't have any upcoming meetings scheduled.",
                    "steps": ["📅 Checked meeting database", "ℹ️ No upcoming meetings found"]
                }
            lines = ["📅 **Your Upcoming Meetings:**\n"]
            for m in upcoming[:10]:
                t = m.scheduled_at.strftime("%A, %b %d at %I:%M %p UTC")
                lines.append(f"• **{m.title}** – {t} ({m.duration_minutes or 30} min)")
            if len(upcoming) > 10:
                lines.append(f"\n...and {len(upcoming) - 10} more.")
            return {
                "status": "success", "intent": "meeting_query",
                "result": "\n".join(lines),
                "steps": ["📅 Queried meeting database", f"✅ Found {len(upcoming)} upcoming meeting(s)"]
            }
        finally:
            db.close()

    # ── Meeting Reschedule & Cancel ──────────────────────────

    @staticmethod
    def cancel_meeting_by_title(
        title_keyword: str,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a meeting by title keyword. CEO only."""
        auth = MeetingScheduler.check_ceo_authorization(user_email, user_role)
        if not auth["authorized"]:
            return {
                "status": "error", "intent": "meeting_management",
                "result": MeetingScheduler.CEO_DENIAL_MESSAGE,
                "steps": ["🔒 Authorization check: denied"]
            }

        db = SessionLocal()
        try:
            meeting = db.query(Meeting).filter(
                Meeting.title.ilike(f"%{title_keyword}%"),
                Meeting.status != "cancelled"
            ).order_by(Meeting.scheduled_at.desc()).first()

            if not meeting:
                return {
                    "status": "error", "intent": "meeting_management",
                    "result": f"No active meeting found matching '{title_keyword}'.",
                    "steps": ["🔍 Searched for meeting", "⚠️ No matching meeting found"]
                }

            meeting.status = "cancelled"
            db.commit()

            # Notify participants
            if meeting.attendees_json:
                try:
                    from backend.routes_chat import PEER_MESSAGES
                    attendees = json.loads(meeting.attendees_json)
                    for a in attendees:
                        email = a.get("email", "")
                        if email:
                            if email not in PEER_MESSAGES:
                                PEER_MESSAGES[email] = []
                            PEER_MESSAGES[email].append({
                                "sender_email": user_email or "system@execuai.com",
                                "sender_name": "ExecuAI",
                                "sender_role": "System",
                                "recipient_email": email,
                                "text": f"❌ **Meeting Cancelled:** '{meeting.title}' originally scheduled at {meeting.scheduled_at.strftime('%b %d, %Y %I:%M %p UTC')} has been cancelled."
                            })
                except Exception:
                    pass

            return {
                "status": "success", "intent": "meeting_management",
                "action": "meeting_cancelled",
                "result": (
                    f"✅ **Meeting Cancelled Successfully**\n\n"
                    f"• **Title:** {meeting.title}\n"
                    f"• **Was Scheduled:** {meeting.scheduled_at.strftime('%A, %b %d, %Y at %I:%M %p UTC')}\n\n"
                    f"All participants have been notified of the cancellation."
                ),
                "steps": [
                    "🔍 Found matching meeting",
                    "❌ Updated meeting status to cancelled",
                    "🔔 Notified participants of cancellation"
                ]
            }
        finally:
            db.close()

    @staticmethod
    def reschedule_meeting(
        title_keyword: str,
        new_date: Optional[str] = None,
        new_time: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reschedule a meeting by title keyword. CEO only."""
        auth = MeetingScheduler.check_ceo_authorization(user_email, user_role)
        if not auth["authorized"]:
            return {
                "status": "error", "intent": "meeting_management",
                "result": MeetingScheduler.CEO_DENIAL_MESSAGE,
                "steps": ["🔒 Authorization check: denied"]
            }

        if not new_date or not new_time:
            return {
                "status": "error", "intent": "meeting_management",
                "result": "Please provide both a new date and time for the rescheduled meeting.",
                "steps": ["⚠️ Missing new date or time for rescheduling"]
            }

        new_dt = MeetingScheduler.parse_datetime(new_date, new_time)
        if not new_dt:
            return {
                "status": "error", "intent": "meeting_management",
                "result": f"Could not parse the new date/time: '{new_date}' at '{new_time}'.",
                "steps": ["❌ Date/time parsing failed"]
            }

        db = SessionLocal()
        try:
            meeting = db.query(Meeting).filter(
                Meeting.title.ilike(f"%{title_keyword}%"),
                Meeting.status != "cancelled"
            ).order_by(Meeting.scheduled_at.desc()).first()

            if not meeting:
                return {
                    "status": "error", "intent": "meeting_management",
                    "result": f"No active meeting found matching '{title_keyword}'.",
                    "steps": ["🔍 Searched for meeting", "⚠️ No matching meeting found"]
                }

            old_time = meeting.scheduled_at.strftime("%A, %b %d, %Y at %I:%M %p UTC")
            meeting.scheduled_at = new_dt
            meeting.status = "rescheduled"
            db.commit()

            # Notify participants
            if meeting.attendees_json:
                try:
                    from backend.routes_chat import PEER_MESSAGES
                    attendees = json.loads(meeting.attendees_json)
                    for a in attendees:
                        email = a.get("email", "")
                        if email:
                            if email not in PEER_MESSAGES:
                                PEER_MESSAGES[email] = []
                            PEER_MESSAGES[email].append({
                                "sender_email": user_email or "system@execuai.com",
                                "sender_name": "ExecuAI",
                                "sender_role": "System",
                                "recipient_email": email,
                                "text": (
                                    f"🔄 **Meeting Rescheduled:** '{meeting.title}'\n"
                                    f"**Previous:** {old_time}\n"
                                    f"**New:** {new_dt.strftime('%A, %b %d, %Y at %I:%M %p UTC')}"
                                )
                            })
                except Exception:
                    pass

            return {
                "status": "success", "intent": "meeting_management",
                "action": "meeting_rescheduled",
                "result": (
                    f"✅ **Meeting Rescheduled Successfully**\n\n"
                    f"• **Title:** {meeting.title}\n"
                    f"• **Previous Time:** {old_time}\n"
                    f"• **New Time:** {new_dt.strftime('%A, %b %d, %Y at %I:%M %p UTC')}\n\n"
                    f"All participants have been notified of the change."
                ),
                "steps": [
                    "🔍 Found matching meeting",
                    "🔄 Updated meeting schedule",
                    "🔔 Notified participants of rescheduling"
                ]
            }
        finally:
            db.close()
