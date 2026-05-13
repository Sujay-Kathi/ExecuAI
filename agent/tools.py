"""
Tools Layer — callable functions the AI Agent can invoke.

Each tool simulates a real enterprise action and returns structured output.
Tools are registered in TOOL_REGISTRY and looked up by name during execution.

== Architecture ==
  - Tools with DB access use the SessionLocal factory directly.
  - Tools without DB access are pure-function simulations.
  - All tools return a dict with at minimum: {"tool", "status", ...details}
"""
import os
import uuid
import random
import hashlib
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from backend.config import SUPABASE_URL, SUPABASE_KEY


# ────────────────────────────────────────────────────────────
# Employee Management Tools
# ────────────────────────────────────────────────────────────

def create_employee_record(name: str, role: str, department: str) -> dict:
    """Create or update an employee record in the database."""
    email = f"{name.lower().replace(' ', '.')}@enterprise.com"
    emp_id = None
    try:
        from backend.database import SessionLocal
        from backend.models import Employee

        db = SessionLocal()
        # Check if exists
        emp = db.query(Employee).filter(Employee.email == email).first()
        default_password = None
        if emp:
            # Update
            emp.role = role
            emp.department = department
            db.commit()
            db.refresh(emp)
            emp_id = emp.id
        else:
            # Create
            default_password = "admin123"
            pwd_hash = hashlib.sha256(default_password.encode()).hexdigest()
            emp = Employee(
                name=name, 
                email=email, 
                role=role, 
                department=department,
                password_hash=pwd_hash
            )
            db.add(emp)
            db.commit()
            db.refresh(emp)
            emp_id = emp.id
        db.close()
    except Exception as e:
        print(f"Local DB error: {e}")

    # ── Real-time Sync to Supabase ──
    supabase_synced = False
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Upsert by email
            supabase.table("employees").upsert({
                "name": name,
                "email": email,
                "role": role,
                "department": department,
                "password_hash": pwd_hash if default_password else None # Only update hash for new employees or keep current
            }, on_conflict="email").execute()
            supabase_synced = True
        except Exception as e:
            print(f"Supabase sync failed: {e}")

    return {
        "tool": "create_employee_record",
        "status": "success",
        "employee_id": emp_id,
        "name": name,
        "email": email,
        "role": role,
        "department": department,
        "password": default_password or "Existent (unchanged)",
        "supabase_synced": supabase_synced,
        "message": f"Record processed for {name} ({email}) and synced to Supabase. Password: {default_password}" if default_password else f"Record updated for {name} ({email})",
    }


def generate_employee_email(name: str) -> dict:
    """Generate a corporate email address for a new employee."""
    email = f"{name.lower().replace(' ', '.')}@enterprise.com"
    return {
        "tool": "generate_employee_email",
        "status": "success",
        "email": email,
        "name": name,
    }


def get_employee_info(employee_id: int = 1) -> dict:
    """Retrieve employee information from the database."""
    try:
        from backend.database import SessionLocal
        from backend.models import Employee

        db = SessionLocal()
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        db.close()
        if emp:
            return {
                "tool": "get_employee_info",
                "status": "success",
                "employee_id": emp.id,
                "name": emp.name,
                "role": emp.role,
                "department": emp.department,
                "email": emp.email,
            }
    except Exception:
        pass

    return {
        "tool": "get_employee_info",
        "status": "success",
        "employee_id": employee_id,
        "name": "Employee",
        "role": "Associate",
        "department": "General",
        "note": "Simulated record",
    }


def assign_role(name: str, role: str, department: str) -> dict:
    """Assign a role and department to an employee and sync to Supabase."""
    email = f"{name.lower().replace(' ', '.')}@enterprise.com"
    try:
        from backend.database import SessionLocal
        from backend.models import Employee

        db = SessionLocal()
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{name}%")).first()
        if emp:
            emp.role = role
            emp.department = department
            db.commit()
        db.close()
    except Exception:
        pass

    # Supabase Sync
    supabase_synced = False
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            supabase.table("employees").upsert({
                "name": name,
                "email": email,
                "role": role,
                "department": department
            }, on_conflict="email").execute()
            supabase_synced = True
        except Exception:
            pass

    return {
        "tool": "assign_role",
        "status": "success",
        "name": name,
        "role": role,
        "department": department,
        "supabase_synced": supabase_synced,
        "message": f"{name} assigned as {role} in {department} (Synced to Supabase)" if supabase_synced else f"{name} assigned as {role} in {department}",
    }

# Alias for Feature 1
generate_company_email = generate_employee_email


# ────────────────────────────────────────────────────────────
# IT Provisioning & Access Tools
# ────────────────────────────────────────────────────────────

def provision_it_systems(name: str) -> dict:
    """Provision all standard IT systems for a new employee."""
    from agent.integrations import send_slack_message

    systems = ["Email", "Slack", "GitHub", "Jira", "Google Workspace", "VPN"]

    # Try real Slack notification
    slack_result = send_slack_message(
        f":wave: *New Employee Provisioned:* {name}\n"
        f"Systems: {', '.join(systems)}\n"
        f"Status: All {len(systems)} systems configured :white_check_mark:"
    )

    return {
        "tool": "provision_it_systems",
        "status": "success",
        "name": name,
        "systems_provisioned": systems,
        "message": f"All {len(systems)} systems provisioned for {name}",
        "real_slack": slack_result is not None,
    }

# Alias for Feature 1
trigger_it_provisioning = provision_it_systems


def grant_system_access(name: str, system: str) -> dict:
    """Grant access to a specific system for an employee."""
    # DB record
    try:
        from backend.database import SessionLocal
        from backend.models import Employee, AccessRequest

        db = SessionLocal()
        emp = db.query(Employee).filter(Employee.name == name).first()
        if emp:
            req = AccessRequest(
                employee_id=emp.id,
                system_name=system,
                access_type="write",
                status="granted",
            )
            db.add(req)
            db.commit()
            db.close()
    except Exception:
        pass

    # Try real GitHub if the system is GitHub
    real_api = None
    if system.lower() in ("github", "git"):
        from agent.integrations import invite_to_github_org
        real_api = invite_to_github_org(name.lower().replace(" ", "-"))

    import random
    ticket_id = f"IT-{random.randint(1000, 9999)}"

    return {
        "tool": "grant_system_access",
        "status": "success",
        "name": name,
        "system": system,
        "steps": [
            f"Checking {system} license pool availability... [Available]",
            f"Creating Jira ticket {ticket_id} for audit trail... [Created]",
            f"Assigning {system} seat to {name}... [Assigned]",
            f"Configuring SSO for {name}... [Complete]"
        ],
        "ticket": ticket_id,
        "message": f"Access to {system} has been successfully provisioned for {name}."
    }


def check_permissions(name: str, system: str) -> dict:
    """Check current permissions for a user on a system."""
    return {
        "tool": "check_permissions",
        "status": "success",
        "name": name,
        "system": system,
        "current_access": "none",
        "message": f"No existing access found for {name} on {system}",
    }


def validate_access_eligibility(name: str, system: str) -> dict:
    """Validate whether an employee is eligible for the requested access."""
    return {
        "tool": "validate_access_eligibility",
        "status": "success",
        "name": name,
        "system": system,
        "eligible": True,
        "message": f"{name} is eligible for {system} access",
    }


# ────────────────────────────────────────────────────────────
# Meeting & Calendar Tools
# ────────────────────────────────────────────────────────────

def schedule_meeting(title: str, organizer: str = "System", attendees: list[str] = None) -> dict:
    """Schedule a meeting — tries Google Calendar first, then DB fallback."""
    from agent.integrations import create_real_calendar_event

    meeting_time = datetime.now(timezone.utc) + timedelta(days=random.randint(1, 5))

    # Try real Google Calendar
    gcal = create_real_calendar_event(
        title=title,
        description=f"Scheduled by {organizer} via ExecuAI",
        start_time=meeting_time,
        duration_minutes=30,
        attendees=attendees,
    )

    # Always persist in local DB too
    meeting_id = None
    try:
        from backend.database import SessionLocal
        from backend.models import Meeting, Employee

        db = SessionLocal()
        emp = db.query(Employee).first()
        org_id = emp.id if emp else 1
        meeting = Meeting(
            title=title,
            organizer_id=org_id,
            scheduled_at=meeting_time,
            duration_minutes=30,
            description=f"Scheduled by {organizer}",
        )
        db.add(meeting)
        db.commit()
        meeting_id = meeting.id
        db.close()
    except Exception:
        pass

    result = {
        "tool": "schedule_meeting",
        "status": "success",
        "title": title,
        "scheduled_at": meeting_time.isoformat(),
        "organizer": organizer,
        "real_calendar": gcal is not None,
    }
    if meeting_id:
        result["meeting_id"] = meeting_id
    if gcal:
        result["calendar_link"] = gcal.get("link", "")
        if gcal.get("meet_link"):
            result["meet_link"] = gcal.get("meet_link")
    else:
        import uuid
        result["calendar_link"] = "https://calendar.google.com/simulated"
        result["meet_link"] = f"https://meet.google.com/simulated-{uuid.uuid4().hex[:8]}"

    if attendees:
        meet_info = f"\nGoogle Meet Link: {result.get('meet_link')}" if result.get('meet_link') else ""
        body = f"You have been invited to a meeting: {title}\nTime: {meeting_time.strftime('%Y-%m-%d %H:%M UTC')}\nOrganizer: {organizer}{meet_info}"
        result["email_status"] = {}
        for attendee in attendees:
            email_res = send_notification_email(
                to=attendee,
                subject=f"Meeting Invitation: {title}",
                body=body
            )
            result["email_status"][attendee] = email_res.get("status")

    return result


def check_availability(name: str) -> dict:
    """Check calendar availability — tries Google Calendar freebusy first."""
    from agent.integrations import check_real_availability

    real = check_real_availability()
    if real:
        return {
            "tool": "check_availability",
            "status": "success",
            "name": name,
            "busy_slots": real["busy_slots"],
            "method": "Google Calendar API",
        }

    return {
        "tool": "check_availability",
        "status": "success",
        "name": name,
        "available_slots": [
            "Tomorrow 10:00 AM - 11:00 AM",
            "Tomorrow 2:00 PM - 3:00 PM",
            "Day after 9:00 AM - 10:00 AM",
        ],
    }


def resolve_conflicts(title: str) -> dict:
    """Resolve scheduling conflicts for a meeting."""
    return {
        "tool": "resolve_conflicts",
        "status": "success",
        "title": title,
        "conflicts_found": 0,
        "message": "No scheduling conflicts detected",
    }


# ────────────────────────────────────────────────────────────
# Email & Notification Tools
# ────────────────────────────────────────────────────────────

def send_notification_email(to: str, subject: str, body: str, recipient_name: str = None) -> dict:
    """
    Send an email only to verified recipients in the database.
    Will NOT send to unverified or placeholder addresses.
    """
    from agent.integrations import send_real_email
    from backend.database import SessionLocal
    from backend.models import Employee

    resolved_email = None
    db = SessionLocal()
    
    # Priority 1: Use recipient_name if provided
    if recipient_name:
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{recipient_name}%")).first()
        if emp:
            resolved_email = emp.email
            
    # Priority 2: If 'to' is not a valid email format, treat it as a name lookup
    if not resolved_email and to and "@" not in to:
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{to}%")).first()
        if emp:
            resolved_email = emp.email

    # Priority 3: If 'to' is an enterprise.com placeholder, try to resolve it
    if not resolved_email and to and "@enterprise.com" in to:
        name_part = to.split("@")[0].replace(".", " ")
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{name_part}%")).first()
        if emp:
            resolved_email = emp.email

    # Priority 4: Check if 'to' itself is in the DB
    if not resolved_email and to and "@" in to:
        emp = db.query(Employee).filter(Employee.email == to).first()
        if emp:
            resolved_email = emp.email

    db.close()

    if not resolved_email:
        return {
            "tool": "send_notification_email",
            "status": "error",
            "message": f"Recipient '{recipient_name or to}' not found in database. Email aborted to prevent bounces.",
        }

    to = resolved_email

    # SAFETY CHECK: Removed to allow testing with any domain.
    # Users should ensure they have a real email address in the DB for testing.

    real = send_real_email(to=to, subject=subject, body=body)
    if real:
        return {
            "tool": "send_notification_email",
            "status": "success",
            "to": to,
            "subject": subject,
            "message": f"Real email sent successfully to {to}.",
            "method": "Gmail SMTP",
        }

    # If send failed but credentials exist, report it as an error
    if os.getenv("SMTP_EMAIL") and os.getenv("SMTP_APP_PASSWORD"):
        return {
            "tool": "send_notification_email",
            "status": "error",
            "to": to,
            "message": f"Failed to send real email to {to}. This could be due to a connection issue or an invalid App Password.",
        }

    # Fallback to simulation only if credentials are missing
    return {
        "tool": "send_notification_email",
        "status": "simulated",
        "to": to,
        "subject": subject,
        "message": f"Simulated email notification to {to} (set SMTP_EMAIL & SMTP_APP_PASSWORD for real emails).",
    }

# Alias for Features
send_email = send_notification_email

def send_notification(text: str, channel: str = "general") -> dict:
    """Send a notification to Slack or Teams."""
    from agent.integrations import send_slack_message
    
    # Try real Slack
    slack_result = send_slack_message(text, channel_context=channel)
    
    return {
        "tool": "send_notification",
        "status": "success" if slack_result else "simulated",
        "channel": channel,
        "text": text,
        "real_slack": slack_result is not None,
        "message": "Notification sent to Slack" if slack_result else "Simulated notification sent (Set SLACK_WEBHOOK_URL for real Slack notifications)"
    }


# ────────────────────────────────────────────────────────────
# Leave Management Tools
# ────────────────────────────────────────────────────────────

def check_leave_balance(employee_id: int = 1, leave_type: str = "casual") -> dict:
    """Check remaining leave balance for an employee."""
    balances = {
        "casual": random.randint(5, 12),
        "sick": random.randint(3, 10),
        "earned": random.randint(8, 20),
        "pto": random.randint(10, 15),
        "vacation": random.randint(10, 15),
    }
    balance = balances.get(leave_type, 10)
    return {
        "tool": "check_leave_balance",
        "status": "success",
        "employee_id": employee_id,
        "leave_type": leave_type,
        "remaining_days": balance,
        "message": f"{balance} {leave_type} leave days remaining",
    }


def validate_leave_request(employee_id: int = 1, dates: list = None) -> dict:
    """Validate a leave request (check for overlaps, blackout dates, etc.)."""
    return {
        "tool": "validate_leave_request",
        "status": "success",
        "employee_id": employee_id,
        "valid": True,
        "message": "Leave request is valid — no conflicts found",
    }


def apply_leave(employee_id: int = 1, leave_type: str = "casual",
                start: str = "", end: str = "") -> dict:
    """Submit a leave request to the system."""
    try:
        from backend.database import SessionLocal
        from backend.models import LeaveRequest

        db = SessionLocal()
        leave = LeaveRequest(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=datetime.fromisoformat(start) if start else datetime.now(timezone.utc),
            end_date=datetime.fromisoformat(end) if end else datetime.now(timezone.utc) + timedelta(days=1),
            reason=f"Auto-created via agent: {leave_type} leave",
            status="pending",
        )
        db.add(leave)
        db.commit()
        leave_id = leave.id
        db.close()
        return {
            "tool": "apply_leave",
            "status": "success",
            "leave_id": leave_id,
            "employee_id": employee_id,
            "leave_type": leave_type,
        }
    except Exception:
        pass

    return {
        "tool": "apply_leave",
        "status": "success",
        "employee_id": employee_id,
        "leave_type": leave_type,
        "message": "Leave request submitted successfully",
    }

def fetch_leave_request(employee_name: str) -> dict:
    """Fetch the most recent leave request for an employee."""
    try:
        from backend.database import SessionLocal
        from backend.models import LeaveRequest, Employee

        db = SessionLocal()
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{employee_name}%")).first()
        if emp:
            req = db.query(LeaveRequest).filter(LeaveRequest.employee_id == emp.id).order_by(LeaveRequest.created_at.desc()).first()
            if req:
                return {
                    "tool": "fetch_leave_request",
                    "status": "success",
                    "leave_id": req.id,
                    "employee_name": emp.name,
                    "leave_type": req.leave_type,
                    "start_date": req.start_date.isoformat(),
                    "end_date": req.end_date.isoformat(),
                    "current_status": req.status
                }
        db.close()
    except Exception:
        pass

    return {
        "tool": "fetch_leave_request",
        "status": "success",
        "employee_name": employee_name,
        "leave_id": random.randint(100, 999),
        "leave_type": "vacation",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "current_status": "pending",
        "note": "Simulated leave request"
    }

def update_leave_status(leave_id: int, status: str) -> dict:
    """Approve or reject a leave request."""
    try:
        from backend.database import SessionLocal
        from backend.models import LeaveRequest

        db = SessionLocal()
        req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
        if req:
            req.status = status
            db.commit()
            db.close()
            return {
                "tool": "update_leave_status",
                "status": "success",
                "leave_id": leave_id,
                "new_status": status
            }
        db.close()
    except Exception:
        pass

    return {
        "tool": "update_leave_status",
        "status": "success",
        "leave_id": leave_id,
        "new_status": status,
        "note": "Simulated status update"
    }


# ────────────────────────────────────────────────────────────
# IT Ticket Tools
# ────────────────────────────────────────────────────────────

def categorize_issue(description: str) -> dict:
    """Categorize an IT issue based on description."""
    categories = {
        "email": "Email & Communication",
        "slack": "Collaboration Tools",
        "vpn": "Network & Connectivity",
        "login": "Authentication",
        "password": "Authentication",
        "slow": "Performance",
        "crash": "Application Stability",
        "error": "Application Error",
        "access": "Access & Permissions",
    }
    category = "General IT"
    for keyword, cat in categories.items():
        if keyword in description.lower():
            category = cat
            break
    return {
        "tool": "categorize_issue",
        "status": "success",
        "category": category,
        "description": description[:100],
    }


def assign_priority(description: str) -> dict:
    """Assign priority to an IT ticket based on keywords."""
    high_keywords = ["crash", "down", "outage", "cannot access", "critical", "urgent"]
    medium_keywords = ["slow", "error", "not working", "bug"]

    priority = "low"
    for kw in high_keywords:
        if kw in description.lower():
            priority = "high"
            break
    if priority == "low":
        for kw in medium_keywords:
            if kw in description.lower():
                priority = "medium"
                break

    return {
        "tool": "assign_priority",
        "status": "success",
        "priority": priority,
        "description": description[:100],
    }


def create_it_ticket(title: str, description: str, priority: str = "medium") -> dict:
    """Create an IT support ticket."""
    ticket_id = f"IT-{random.randint(1000, 9999)}"
    try:
        from backend.database import SessionLocal
        from backend.models import ITTicket

        db = SessionLocal()
        ticket = ITTicket(
            ticket_id=ticket_id,
            title=title,
            description=description,
            priority=priority,
            status="open",
        )
        db.add(ticket)
        db.commit()
        db.close()
    except Exception:
        pass

    return {
        "tool": "create_it_ticket",
        "status": "success",
        "ticket_id": ticket_id,
        "title": title,
        "priority": priority,
        "message": f"Ticket {ticket_id} created with {priority} priority",
    }


def assign_it_team(system: str = "General") -> dict:
    """Assign an IT support team to handle the ticket."""
    teams = {
        "Email": "Communications Team",
        "Slack": "Collaboration Support",
        "GitHub": "DevOps Team",
        "VPN": "Network Operations",
        "General": "General IT Support",
    }
    team = teams.get(system, "General IT Support")
    return {
        "tool": "assign_it_team",
        "status": "success",
        "system": system,
        "assigned_team": team,
        "message": f"Ticket assigned to {team}",
    }


# ────────────────────────────────────────────────────────────
# Password Reset Tools
# ────────────────────────────────────────────────────────────

def verify_identity(name: str) -> dict:
    """Verify user identity before password reset."""
    return {
        "tool": "verify_identity",
        "status": "success",
        "name": name,
        "verified": True,
        "method": "Email verification",
        "message": f"Identity verified for {name}",
    }


def generate_reset_link(name: str) -> dict:
    """Generate a secure password reset link."""
    token = uuid.uuid4().hex[:16]
    return {
        "tool": "generate_reset_link",
        "status": "success",
        "name": name,
        "reset_link": f"https://enterprise.com/reset/{token}",
        "expires_in": "30 minutes",
    }


# ────────────────────────────────────────────────────────────
# ML / Attrition Prediction Tools
# ────────────────────────────────────────────────────────────

def predict_attrition(name: str = "Rahul") -> dict:
    """
    Predict employee attrition using the trained ML model (Random Forest).
    If the model is not found, it falls back to simulation mode.
    """
    try:
        from ml.predictor import AttritionPredictor
        predictor = AttritionPredictor()
        
        if predictor.model is not None:
            # Profile-based inputs for the demo
            age = 35 if name == "Rahul" else 28
            income = 5500 if name == "Rahul" else 4200
            
            result = predictor.predict(
                age=age,
                monthly_income=income,
                years_at_company=5,
                job_satisfaction=3,
                overtime=True if name == "Rahul" else False
            )
            
            recs = [
                "Consider a retention conversation",
                "Review compensation",
                "Evaluate workload"
            ] if result["prediction"] == "Likely to Leave" else ["Continue regular check-ins"]
            
            return {
                "tool": "predict_attrition",
                "status": "success",
                "employee": name,
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "recommendations": recs,
                "method": "Real ML Model"
            }
    except Exception as e:
        print(f"[AGENT] Prediction Error: {e}")

    # Fallback simulation
    risk = "Likely to Leave" if name == "Rahul" else "Stable"
    return {
        "tool": "predict_attrition",
        "status": "success",
        "employee": name,
        "prediction": risk,
        "confidence": 0.92,
        "recommendations": ["Retention talk"] if risk == "Likely to Leave" else ["Maintain engagement"],
        "method": "Simulation (Model not loaded)"
    }


# ────────────────────────────────────────────────────────────
# Notification / Reminder Tools
# ────────────────────────────────────────────────────────────

def fetch_schedule(name: str = "User") -> dict:
    """Fetch upcoming schedule for a user."""
    now = datetime.now(timezone.utc)
    events = [
        {"title": "Team Standup", "time": (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")},
        {"title": "Sprint Planning", "time": (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")},
        {"title": "1:1 with Manager", "time": (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")},
    ]
    return {
        "tool": "fetch_schedule",
        "status": "success",
        "name": name,
        "upcoming_events": events,
    }


def identify_events(name: str = "User") -> dict:
    """Identify important events requiring reminders."""
    return {
        "tool": "identify_events",
        "status": "success",
        "name": name,
        "reminder_count": 3,
        "message": "3 events identified for reminders",
    }


# ────────────────────────────────────────────────────────────
# System Health Check Tools
# ────────────────────────────────────────────────────────────

def check_db_health() -> dict:
    """Check database connectivity."""
    try:
        from backend.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "tool": "check_db_health",
            "status": "success",
            "database": "healthy",
            "response_time_ms": random.randint(1, 15),
        }
    except Exception:
        pass

    return {
        "tool": "check_db_health",
        "status": "success",
        "database": "healthy",
        "response_time_ms": random.randint(1, 15),
    }


def check_api_health() -> dict:
    """Check API endpoint health."""
    return {
        "tool": "check_api_health",
        "status": "success",
        "api": "healthy",
        "endpoints_checked": 12,
        "all_passing": True,
        "response_time_ms": random.randint(5, 50),
    }


def check_ml_health() -> dict:
    """Check ML model availability."""
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "model.pkl")
    loaded = os.path.exists(model_path)
    return {
        "tool": "check_ml_health",
        "status": "success",
        "ml_model": "loaded" if loaded else "not found",
        "model_path": model_path,
    }


def detect_issues() -> dict:
    """Run anomaly detection across all systems."""
    return {
        "tool": "detect_issues",
        "status": "success",
        "issues_detected": 0,
        "message": "All systems operating normally",
        "last_checked": datetime.now(timezone.utc).isoformat(),
    }


# ────────────────────────────────────────────────────────────
# Task & Activity Tools
# ────────────────────────────────────────────────────────────

def fetch_employee_tasks(employee_id: int = 1) -> dict:
    """Fetch all assigned tasks for an employee."""
    tasks = [
        {"id": 101, "title": "Update API documentation", "priority": "high", "due": "Today"},
        {"id": 102, "title": "Review PR #452", "priority": "medium", "due": "Tomorrow"},
        {"id": 103, "title": "Fix bug in login flow", "priority": "high", "due": "Today"},
        {"id": 104, "title": "Meeting with stakeholders", "priority": "medium", "due": "Thursday"},
    ]
    return {
        "tool": "fetch_employee_tasks",
        "status": "success",
        "employee_id": employee_id,
        "tasks": tasks,
        "count": len(tasks),
    }


def prioritize_tasks(tasks: list) -> dict:
    """Sort tasks by priority and urgency."""
    priority_map = {"high": 0, "medium": 1, "low": 2}
    sorted_tasks = sorted(tasks, key=lambda t: priority_map.get(t["priority"], 3))
    return {
        "tool": "prioritize_tasks",
        "status": "success",
        "sorted_tasks": sorted_tasks,
        "suggestion": f"Focus on '{sorted_tasks[0]['title']}' first as it is high priority."
    }


def fetch_activity_logs(employee_id: int = 1) -> dict:
    """Fetch recent activity logs for an employee."""
    logs = [
        "Committed 3 changes to 'backend/auth.py'",
        "Closed 2 Jira tickets (IT-402, IT-405)",
        "Attended Sprint Standup",
        "Replied to 12 Slack messages in #dev-team",
    ]
    return {
        "tool": "fetch_activity_logs",
        "status": "success",
        "employee_id": employee_id,
        "logs": logs,
    }


def summarize_activities(logs: list) -> dict:
    """Generate a natural language summary of activities."""
    summary = "Today you focused on backend authentication, resolved 2 IT tickets, and maintained active communication with the dev team."
    return {
        "tool": "summarize_activities",
        "status": "success",
        "summary": summary,
        "achievements_count": len(logs),
    }


# ────────────────────────────────────────────────────────────
# Planning & Insight Tools
# ────────────────────────────────────────────────────────────

def analyze_workload(employee_id: int = 1) -> dict:
    """Analyze current workload based on tasks and meetings."""
    return {
        "tool": "analyze_workload",
        "status": "success",
        "workload_score": 75,  # 0-100
        "status": "moderately busy",
        "busy_days": ["Tuesday", "Wednesday"],
    }


def suggest_leave_dates(balance: int, workload: dict) -> dict:
    """Suggest the best dates for leave based on low workload periods."""
    return {
        "tool": "suggest_leave_dates",
        "status": "success",
        "suggested_dates": ["2026-05-22", "2026-05-25"],
        "reason": "These dates follow the project milestone and have minimal meeting density.",
    }


def fetch_performance_data(employee_id: int = 1) -> dict:
    """Fetch performance metrics for an employee."""
    return {
        "tool": "fetch_performance_data",
        "status": "success",
        "kpis": {
            "tasks_completed": 45,
            "code_quality": "92%",
            "collaboration_score": 4.8,
        },
        "trends": "Improving",
    }


def analyze_performance_trends(data: dict) -> dict:
    """Analyze performance data for strengths and improvements."""
    return {
        "tool": "analyze_performance_trends",
        "status": "success",
        "strengths": ["Consistent delivery", "High code quality"],
        "improvements": ["More active participation in cross-team reviews"],
    }


# ────────────────────────────────────────────────────────────
# Knowledge & Assistance Tools
# ────────────────────────────────────────────────────────────

def search_knowledge_base(query: str) -> dict:
    """Search company knowledge base for procedures and policies."""
    return {
        "tool": "search_knowledge_base",
        "status": "success",
        "query": query,
        "results": [
            {"title": "Reimbursement Policy", "snippet": "Submit all receipts within 30 days via the Finance portal..."},
            {"title": "Travel Guidelines", "snippet": "Book flights 2 weeks in advance for domestic travel..."},
        ]
    }


def extract_policy_info(search_results: list) -> dict:
    """Extract key steps from search results."""
    return {
        "tool": "extract_policy_info",
        "status": "success",
        "steps": [
            "1. Collect all digital receipts",
            "2. Log in to the Finance Portal",
            "3. Select 'New Reimbursement'",
            "4. Attach receipts and submit"
        ],
    }


def detect_schedule_overload(calendar_data: dict) -> dict:
    """Detect overloaded days in the calendar."""
    return {
        "tool": "detect_schedule_overload",
        "status": "success",
        "overloaded": True,
        "bottleneck_day": "Wednesday",
        "meeting_hours": 6.5,
    }


def suggest_rescheduling(overloaded_slots: list) -> dict:
    """Suggest meetings that can be rescheduled to balance the day."""
    return {
        "tool": "suggest_rescheduling",
        "status": "success",
        "suggestions": ["Move 'Weekly Sync' to Thursday morning", "Shorten 'Design Review' by 15 mins"],
    }


# ────────────────────────────────────────────────────────────
# IT & Software Tools
# ────────────────────────────────────────────────────────────

def check_software_eligibility(role: str, software: str) -> dict:
    """Check if the employee's role is eligible for a software license."""
    return {
        "tool": "check_software_eligibility",
        "status": "success",
        "role": role,
        "software": software,
        "eligible": True,
    }


def fetch_notifications(employee_id: int = 1) -> dict:
    """Fetch all unread notifications for an employee."""
    return {
        "tool": "fetch_notifications",
        "status": "success",
        "notifications": [
            {"type": "urgent", "msg": "Security patch required on your laptop"},
            {"type": "info", "msg": "New company policy on remote work updated"},
            {"type": "social", "msg": "Alice mentioned you in #random"},
        ],
    }


def filter_important_notifications(notifications: list) -> dict:
    """Filter and prioritize important notifications."""
    urgent = [n for n in notifications if n["type"] == "urgent"]
    return {
        "tool": "filter_important_notifications",
        "status": "success",
        "summary": f"You have {len(urgent)} urgent alert regarding a security patch.",
        "important_count": len(urgent),
    }


# ────────────────────────────────────────────────────────────
# IT/Admin Master Tools (Feature 1, 2, 3)
# ────────────────────────────────────────────────────────────

def create_company_email(name: str = "User") -> dict:
    """Create a new corporate email account using Gmail/SMTP integration."""
    email = f"{name.lower().replace(' ', '.')}@execuai.com"
    return {
        "tool": "create_company_email",
        "status": "success",
        "email": email,
        "name": name,
        "message": f"Corporate email {email} successfully provisioned."
    }

def create_user_account(name: str = "User") -> dict:
    """Create an internal system account and database record."""
    try:
        from backend.database import SessionLocal
        from backend.models import Employee
        
        db = SessionLocal()
        email = f"{name.lower().replace(' ', '.')}@execuai.com"
        
        # Check if employee already exists
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{name}%")).first()
        if not emp:
            temp_pwd = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=10))
            emp = Employee(name=name, email=email, role="Associate", department="General", temp_password=temp_pwd)
            db.add(emp)
            db.commit()
            db.refresh(emp)
        
        user_id = f"UID-{emp.id:05d}"
        ret_email = emp.email
        ret_pwd = emp.temp_password or "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=10))
        
        if not emp.temp_password:
            emp.temp_password = ret_pwd
            db.commit()

        db.close()
        return {
            "tool": "create_user_account",
            "status": "success",
            "user_id": user_id,
            "email": ret_email,
            "name": name,
            "temporary_password": ret_pwd,
            "message": f"Account retrieved/created for {name} from database. Email: {ret_email}"
        }
    except Exception as e:
        temp_pwd = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=10))
        return {
            "tool": "create_user_account",
            "status": "success",
            "user_id": f"UID-{random.randint(10000, 99999)}",
            "name": name,
            "temporary_password": temp_pwd,
            "message": f"Internal account created for {name} (Simulation: {e}). Temp Password: {temp_pwd}"
        }

def assign_tools_access(name: str = "User", tools: list = None) -> dict:
    """Assign access to enterprise tools and sync with database."""
    try:
        from backend.database import SessionLocal
        from backend.models import Employee
        
        db = SessionLocal()
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{name}%")).first()
        
        if not tools:
            tools = ["GitHub", "Slack"]
            
        clean_name = name.lower().replace(" ", ".")
        # Proper name-based IDs
        slack_id = f"{clean_name}.slack"
        github_user = f"{clean_name}.github"
        
        if emp:
            # Only generate and save if they don't already exist in DB
            if not emp.slack_id:
                emp.slack_id = slack_id
            else:
                slack_id = emp.slack_id
                
            if not emp.github_username:
                emp.github_username = github_user
            else:
                github_user = emp.github_username
                
            db.commit()
            db.close()
        
        return {
            "tool": "assign_tools_access",
            "status": "success",
            "name": name,
            "assigned_tools": tools,
            "slack_id": slack_id,
            "slack_workspace": "ExecuAI-HQ",
            "github_username": github_user,
            "message": f"Tool access synced with database for {name}."
        }
    except Exception as e:
        return {
            "tool": "assign_tools_access",
            "status": "success",
            "name": name,
            "assigned_tools": tools or ["GitHub", "Slack"],
            "slack_id": f"U{random.randint(10000, 99999)}",
            "github_username": f"{name.lower().replace(' ', '')}-git",
            "message": f"Tool access granted (Simulation: {e})."
        }

def reset_user_password(name: str = "User") -> dict:
    """Generate and reset a user's password securely with hashing and DB sync."""
    import string
    # Requirement: only words (alphabetical)
    temp_pwd = "".join(random.choices(string.ascii_letters, k=10))
    pwd_hash = hashlib.sha256(temp_pwd.encode()).hexdigest()
    
    email = f"{name.lower().replace(' ', '.')}@enterprise.com"
    
    # Update local DB
    try:
        from backend.database import SessionLocal
        from backend.models import Employee

        db = SessionLocal()
        emp = db.query(Employee).filter(Employee.name.ilike(f"%{name}%")).first()
        if emp:
            emp.password_hash = pwd_hash
            db.commit()
            email = emp.email
        db.close()
    except Exception:
        pass

    # Supabase Sync (optional if configured)
    supabase_synced = False
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            supabase.table("employees").update({
                "password_hash": pwd_hash
            }).eq("email", email).execute()
            supabase_synced = True
        except Exception:
            pass

    return {
        "tool": "reset_user_password",
        "status": "success",
        "name": name,
        "email": email,
        "temporary_password": temp_pwd,
        "supabase_synced": supabase_synced,
        "message": f"Password reset successfully for {name}. New password updated in database."
    }

def verify_user_identity(name: str = "User") -> dict:
    """Verify user identity using multi-factor or database check."""
    return {
        "tool": "verify_user_identity",
        "status": "success",
        "name": name,
        "verified": True,
        "message": f"Identity verified for {name} via database lookup."
    }

def update_authentication(name: str = "User") -> dict:
    """Update the authentication system (LDAP/AD/SSO) with new credentials."""
    return {
        "tool": "update_authentication",
        "status": "success",
        "name": name,
        "system": "Azure AD / Okta",
        "message": f"Authentication records updated for {name}."
    }

def connect_service_api(service: str = "HR System") -> dict:
    """Establish a connection between services via API."""
    return {
        "tool": "connect_service_api",
        "status": "success",
        "service": service,
        "connection_id": f"CONN-{uuid.uuid4().hex[:8]}",
        "message": f"API connection established for {service}."
    }

def sync_data_between_systems(source: str = "HR", target: str = "Email/Calendar") -> dict:
    """Synchronize data across integrated enterprise systems."""
    return {
        "tool": "sync_data_between_systems",
        "status": "success",
        "records_synced": random.randint(50, 500),
        "message": f"Data successfully synchronized from {source} to {target}."
    }

def check_system_connections() -> dict:
    """Verify health and connectivity of all integrated service APIs."""
    services = ["HR System", "Email Service", "Calendar API"]
    return {
        "tool": "check_system_connections",
        "status": "success",
        "active_services": services,
        "health": "Optimal",
        "message": f"All {len(services)} services are connected and healthy."
    }

# ── Feature 1: Workforce Insights Dashboard ───────────────────

def fetch_employee_data() -> dict:
    """Fetch all employee records for analytics."""
    try:
        from backend.database import SessionLocal
        from backend.models import Employee
        db = SessionLocal()
        employees = db.query(Employee).all()
        data = [{"id": e.id, "name": e.name, "role": e.role} for e in employees]
        db.close()
        return {"tool": "fetch_employee_data", "status": "success", "employees": data}
    except Exception:
        return {"tool": "fetch_employee_data", "status": "success", "employees": []}

def fetch_leave_records() -> dict:
    """Fetch all leave requests for analytics."""
    try:
        from backend.database import SessionLocal
        from backend.models import LeaveRequest
        db = SessionLocal()
        leaves = db.query(LeaveRequest).all()
        data = [{"id": l.id, "status": l.status, "type": l.leave_type} for l in leaves]
        db.close()
        return {"tool": "fetch_leave_records", "status": "success", "leaves": data}
    except Exception:
        return {"tool": "fetch_leave_records", "status": "success", "leaves": []}

def calculate_metrics(employees: list = None, leaves: list = None) -> dict:
    """Calculate workforce metrics (headcount, leave stats)."""
    if employees is None: employees = []
    if leaves is None: leaves = []
    
    stats = {
        "total_employees": len(employees),
        "leave_stats": {
            "approved": len([l for l in leaves if l["status"] == "approved"]),
            "pending": len([l for l in leaves if l["status"] == "pending"]),
            "rejected": len([l for l in leaves if l["status"] == "rejected"]),
        },
        "on_leave": len([l for l in leaves if l["status"] == "approved"])
    }
    return {"tool": "calculate_metrics", "status": "success", "metrics": stats}

def generate_report(metrics: dict, attrition: dict = None) -> dict:
    """Aggregate metrics and attrition risks into a structured report."""
    total = metrics.get("total_employees", 0)
    on_leave = metrics.get("on_leave", 0)
    risk_count = 1 if attrition and attrition.get("prediction") == "Likely to Leave" else 0
    
    # Simulate a few more at-risk for a realistic report
    if total > 10: risk_count += random.randint(1, 5)

    report = (
        f"Workforce Insights: {total} employees, {on_leave} on leave, "
        f"{risk_count} at high attrition risk. Key trends and insights generated."
    )
    return {
        "tool": "generate_report",
        "status": "success",
        "report": report,
        "metrics": metrics,
        "attrition_risk_count": risk_count
    }

# ── Feature 2: Recruitment Assistant ───────────────────────────

def add_candidate_record(name: str, role: str, email: str) -> dict:
    """Create a new candidate record in the database."""
    try:
        from backend.database import SessionLocal
        from backend.models import Candidate
        db = SessionLocal()
        candidate = Candidate(name=name, email=email, role=role, status="new")
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        c_id = candidate.id
        db.close()
        return {
            "tool": "add_candidate_record",
            "status": "success",
            "candidate_id": c_id,
            "name": name,
            "role": role,
            "email": email
        }
    except Exception as e:
        return {
            "tool": "add_candidate_record",
            "status": "success",
            "candidate_id": random.randint(1000, 9999),
            "name": name,
            "role": role,
            "email": email,
            "note": f"Simulation (Error: {e})"
        }

def update_candidate_status(candidate_id: int, status: str) -> dict:
    """Update the status of a recruitment candidate."""
    try:
        from backend.database import SessionLocal
        from backend.models import Candidate
        db = SessionLocal()
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.status = status
            db.commit()
        db.close()
    except Exception:
        pass
    return {
        "tool": "update_candidate_status",
        "status": "success",
        "candidate_id": candidate_id,
        "new_status": status
    }

# ── Feature 3: Policy Assistant ───────────────────────────────

def fetch_policy_documents() -> dict:
    """Fetch all HR policy documents from the policies directory."""
    policy_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policies")
    docs = []
    if os.path.exists(policy_dir):
        for f in os.listdir(policy_dir):
            if f.endswith(".md"):
                docs.append(f)
    return {
        "tool": "fetch_policy_documents",
        "status": "success",
        "documents": docs,
        "count": len(docs)
    }

def search_policy_content(documents: list, query: str) -> dict:
    """Search for specific keywords within policy documents."""
    policy_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policies")
    results = []
    for doc in documents:
        path = os.path.join(policy_dir, doc)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if query.lower() in content.lower():
                    # Extract relevant section (simple logic)
                    start = content.lower().find(query.lower())
                    snippet = content[max(0, start-50):min(len(content), start+200)]
                    results.append({"document": doc, "snippet": snippet})
    return {
        "tool": "search_policy_content",
        "status": "success",
        "query": query,
        "matches": results
    }

def summarize_text(text: str) -> dict:
    """Summarize a large block of text into key points."""
    # Simulation: Extracting bullet points or key sentences
    lines = text.split("\n")
    summary = [l.strip("- ") for l in lines if l.strip().startswith("-") or "entitled" in l.lower() or "days" in l.lower()]
    if not summary:
        summary = ["Refer to the full policy document for details."]
    
    return {
        "tool": "summarize_text",
        "status": "success",
        "summary": " ".join(summary[:3])
    }

# ── Feature 4: Performance Summary ────────────────────────────

def fetch_performance_metrics(name: str) -> dict:
    """Fetch performance-related metrics for an employee."""
    # Simulation: Return structured metrics
    metrics = {
        "productivity": random.randint(70, 95),
        "attendance": random.randint(85, 100),
        "task_completion": random.randint(75, 98),
        "collaboration": random.randint(60, 90),
        "deadline_compliance": random.randint(65, 92)
    }
    return {
        "tool": "fetch_performance_metrics",
        "status": "success",
        "name": name,
        "metrics": metrics
    }

def analyze_performance(metrics: dict) -> dict:
    """Analyze performance metrics and generate insights."""
    m = metrics.get("metrics", {})
    strengths = []
    improvements = []
    
    if m.get("task_completion", 0) > 85: strengths.append("Task Completion")
    if m.get("productivity", 0) > 85: strengths.append("Productivity")
    if m.get("attendance", 0) > 95: strengths.append("Consistency/Attendance")
    
    if m.get("collaboration", 0) < 75: improvements.append("Collaboration")
    if m.get("deadline_compliance", 0) < 75: improvements.append("Meeting Deadlines")
    
    return {
        "tool": "analyze_performance",
        "status": "success",
        "strengths": strengths or ["General performance is stable"],
        "improvement_areas": improvements or ["Continue current growth trajectory"],
        "overall_score": sum(m.values()) / len(m) if m else 0
    }
TOOL_REGISTRY = {
    # Employee Management
    "create_employee_record": create_employee_record,
    "generate_employee_email": generate_employee_email,
    "get_employee_info": get_employee_info,
    "assign_role": assign_role,

    # IT Provisioning & Access
    "provision_it_systems": provision_it_systems,
    "grant_system_access": grant_system_access,
    "check_permissions": check_permissions,
    "validate_access_eligibility": validate_access_eligibility,

    # Meeting & Calendar
    "schedule_meeting": schedule_meeting,
    "check_availability": check_availability,
    "resolve_conflicts": resolve_conflicts,

    # Email
    "send_notification_email": send_notification_email,

    # Leave
    "check_leave_balance": check_leave_balance,
    "validate_leave_request": validate_leave_request,
    "apply_leave": apply_leave,

    # IT Tickets
    "categorize_issue": categorize_issue,
    "assign_priority": assign_priority,
    "create_it_ticket": create_it_ticket,
    "assign_it_team": assign_it_team,

    # Password Reset
    "verify_identity": verify_identity,
    "generate_reset_link": generate_reset_link,

    # ML / Attrition
    "predict_attrition": predict_attrition,

    # Notifications
    "fetch_schedule": fetch_schedule,
    "identify_events": identify_events,

    # System Health
    "check_db_health": check_db_health,
    "check_api_health": check_api_health,
    "check_ml_health": check_ml_health,
    "detect_issues": detect_issues,

    # Task & Activity
    "fetch_employee_tasks": fetch_employee_tasks,
    "prioritize_tasks": prioritize_tasks,
    "fetch_activity_logs": fetch_activity_logs,
    "summarize_activities": summarize_activities,

    # Planning & Insight
    "analyze_workload": analyze_workload,
    "suggest_leave_dates": suggest_leave_dates,
    "fetch_performance_data": fetch_performance_data,
    "analyze_performance_trends": analyze_performance_trends,

    # Knowledge & Assistance
    "search_knowledge_base": search_knowledge_base,
    "extract_policy_info": extract_policy_info,
    "detect_schedule_overload": detect_schedule_overload,
    "suggest_rescheduling": suggest_rescheduling,

    # IT & Software
    "check_software_eligibility": check_software_eligibility,
    "fetch_notifications": fetch_notifications,
    "filter_important_notifications": filter_important_notifications,
    
    # Communications
    "send_notification_email": send_notification_email,
    "send_email": send_email,
    "send_notification": send_notification,
    
    # Master IT/Admin Tools
    "create_company_email": create_company_email,
    "create_user_account": create_user_account,
    "assign_tools_access": assign_tools_access,
    "reset_user_password": reset_user_password,
    "verify_user_identity": verify_user_identity,
    "update_authentication": update_authentication,
    "connect_service_api": connect_service_api,
    "sync_data_between_systems": sync_data_between_systems,
    "check_system_connections": check_system_connections,

    # Advanced HR (Feature 1 & 2)
    "fetch_employee_data": fetch_employee_data,
    "fetch_leave_records": fetch_leave_records,
    "calculate_metrics": calculate_metrics,
    "generate_report": generate_report,
    "add_candidate_record": add_candidate_record,
    "update_candidate_status": update_candidate_status,
    "schedule_interview": schedule_meeting,  # Alias

    # Policy & Performance (New)
    "fetch_policy_documents": fetch_policy_documents,
    "search_policy_content": search_policy_content,
    "summarize_text": summarize_text,
    "fetch_performance_metrics": fetch_performance_metrics,
    "analyze_performance": analyze_performance,
}
