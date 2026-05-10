"""
Workflow Definitions — maps each intent to an ordered sequence of steps.

Each workflow is a list of step dicts with:
  - action:      human-readable description
  - tool:        tool function name (from TOOL_REGISTRY) or None
  - args_map:    callable that builds tool kwargs from entities
  - condition:   optional callable for conditional execution
"""
from typing import Callable, Optional


def _workflow_step(
    action: str,
    tool: Optional[str] = None,
    args_map: Optional[Callable] = None,
    condition: Optional[Callable] = None,
) -> dict:
    return {
        "action": action,
        "tool": tool,
        "args_map": args_map or (lambda e: {}),
        "condition": condition,
    }


# ────────────────────────────────────────────────────────────
# 1. Employee Onboarding
# ────────────────────────────────────────────────────────────
ONBOARDING_WORKFLOW = [
    _workflow_step(
        "Identified onboarding request",
    ),
    _workflow_step(
        "Creating employee record",
        tool="create_employee_record",
        args_map=lambda e: {
            "name": e.get("name", "New Employee"),
            "role": e.get("role", "Associate"),
            "department": e.get("department", "General"),
        },
    ),
    _workflow_step(
        "Generating corporate email",
        tool="generate_employee_email",
        args_map=lambda e: {"name": e.get("name", "New Employee")},
    ),
    _workflow_step(
        "Assigning role and department",
        tool="assign_role",
        args_map=lambda e: {
            "name": e.get("name", "New Employee"),
            "role": e.get("role", "Associate"),
            "department": e.get("department", "General"),
        },
    ),
    _workflow_step(
        "Triggering IT provisioning",
        tool="provision_it_systems",
        args_map=lambda e: {"name": e.get("name", "New Employee")},
    ),
    _workflow_step(
        "Scheduling orientation session",
        tool="schedule_meeting",
        args_map=lambda e: {
            "title": "Orientation — " + e.get("name", "New Employee"),
            "organizer": "HR",
        },
    ),
    _workflow_step(
        "Sending welcome email",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": e.get("name", "employee").lower().replace(" ", ".") + "@enterprise.com",
            "subject": "Welcome to the team!",
            "body": f"Hi {e.get('name', 'there')}, welcome aboard! Your accounts have been set up.",
        },
    ),
    _workflow_step("Logging all onboarding actions"),
]


# ────────────────────────────────────────────────────────────
# 2. IT System Provisioning
# ────────────────────────────────────────────────────────────
IT_PROVISIONING_WORKFLOW = [
    _workflow_step("Identified IT provisioning request"),
    _workflow_step(
        "Verifying employee role",
        tool="get_employee_info",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1)},
    ),
    _workflow_step(
        "Creating email account",
        tool="generate_employee_email",
        args_map=lambda e: {"name": e.get("name", "Employee")},
    ),
    _workflow_step(
        "Adding to Slack workspace",
        tool="grant_system_access",
        args_map=lambda e: {
            "name": e.get("name", "Employee"),
            "system": "Slack",
        },
    ),
    _workflow_step(
        "Granting GitHub access",
        tool="grant_system_access",
        args_map=lambda e: {
            "name": e.get("name", "Employee"),
            "system": "GitHub",
        },
    ),
    _workflow_step(
        "Assigning default development tools",
        tool="grant_system_access",
        args_map=lambda e: {
            "name": e.get("name", "Employee"),
            "system": "Jira + Confluence",
        },
    ),
    _workflow_step("Logging provisioning actions"),
]


# ────────────────────────────────────────────────────────────
# 3. Access Management
# ────────────────────────────────────────────────────────────
ACCESS_MANAGEMENT_WORKFLOW = [
    _workflow_step("Identified access request"),
    _workflow_step(
        "Checking current permissions",
        tool="check_permissions",
        args_map=lambda e: {
            "name": e.get("name", "Employee"),
            "system": e.get("system", "Requested System"),
        },
    ),
    _workflow_step(
        "Validating eligibility",
        tool="validate_access_eligibility",
        args_map=lambda e: {
            "name": e.get("name", "Employee"),
            "system": e.get("system", "Requested System"),
        },
    ),
    _workflow_step(
        "Approving access request",
    ),
    _workflow_step(
        "Granting access",
        tool="grant_system_access",
        args_map=lambda e: {
            "name": e.get("name", "Employee"),
            "system": e.get("system", "Requested System"),
        },
    ),
    _workflow_step("Updating access audit logs"),
]


# ────────────────────────────────────────────────────────────
# 4. Leave Request
# ────────────────────────────────────────────────────────────
LEAVE_REQUEST_WORKFLOW = [
    _workflow_step("Identified leave request"),
    _workflow_step(
        "Checking leave balance",
        tool="check_leave_balance",
        args_map=lambda e: {
            "employee_id": e.get("employee_id", 1),
            "leave_type": e.get("leave_type", "casual"),
        },
    ),
    _workflow_step(
        "Validating leave request dates",
        tool="validate_leave_request",
        args_map=lambda e: {
            "employee_id": e.get("employee_id", 1),
            "dates": e.get("dates", []),
        },
    ),
    _workflow_step(
        "Creating leave entry",
        tool="apply_leave",
        args_map=lambda e: {
            "employee_id": e.get("employee_id", 1),
            "leave_type": e.get("leave_type", "casual"),
            "start": e.get("dates", ["2026-05-12"])[0] if e.get("dates") else "2026-05-12",
            "end": e.get("dates", ["", "2026-05-12"])[1] if len(e.get("dates", [])) > 1 else "2026-05-12",
        },
    ),
    _workflow_step(
        "Notifying HR manager",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": "hr@enterprise.com",
            "subject": "New Leave Request",
            "body": f"Employee #{e.get('employee_id', 1)} has requested {e.get('leave_type', 'casual')} leave.",
        },
    ),
    _workflow_step("Updating leave management system"),
]


# ────────────────────────────────────────────────────────────
# 5. Meeting Scheduling
# ────────────────────────────────────────────────────────────
MEETING_SCHEDULING_WORKFLOW = [
    _workflow_step("Identified meeting request"),
    _workflow_step(
        "Checking participant availability",
        tool="check_availability",
        args_map=lambda e: {"name": e.get("name", "Organizer")},
    ),
    _workflow_step(
        "Resolving scheduling conflicts",
        tool="resolve_conflicts",
        args_map=lambda e: {"title": e.get("title", "Meeting")},
    ),
    _workflow_step(
        "Creating calendar event",
        tool="schedule_meeting",
        args_map=lambda e: {
            "title": e.get("title", "Team Meeting"),
            "organizer": e.get("name", "Organizer"),
        },
    ),
    _workflow_step(
        "Sending meeting invites",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": "team@enterprise.com",
            "subject": f"Meeting Invite: {e.get('title', 'Team Meeting')}",
            "body": f"You are invited to '{e.get('title', 'Team Meeting')}'.",
        },
    ),
    _workflow_step("Logging calendar event"),
]


# ────────────────────────────────────────────────────────────
# 6. IT Ticket Creation
# ────────────────────────────────────────────────────────────
IT_TICKET_WORKFLOW = [
    _workflow_step("Identified IT issue report"),
    _workflow_step(
        "Categorizing issue",
        tool="categorize_issue",
        args_map=lambda e: {"description": e.get("raw_text", "IT issue")},
    ),
    _workflow_step(
        "Assigning priority level",
        tool="assign_priority",
        args_map=lambda e: {"description": e.get("raw_text", "IT issue")},
    ),
    _workflow_step(
        "Creating support ticket",
        tool="create_it_ticket",
        args_map=lambda e: {
            "title": e.get("system", "System") + " issue",
            "description": e.get("raw_text", "IT issue reported"),
            "priority": "medium",
        },
    ),
    _workflow_step(
        "Assigning to IT support team",
        tool="assign_it_team",
        args_map=lambda e: {"system": e.get("system", "General")},
    ),
    _workflow_step(
        "Notifying user of ticket creation",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": e.get("name", "user").lower() + "@enterprise.com",
            "subject": "IT Ticket Created",
            "body": "Your IT support ticket has been created and assigned. We'll get back to you shortly.",
        },
    ),
]


# ────────────────────────────────────────────────────────────
# 7. Password Reset
# ────────────────────────────────────────────────────────────
PASSWORD_RESET_WORKFLOW = [
    _workflow_step("Identified password reset request"),
    _workflow_step(
        "Verifying user identity",
        tool="verify_identity",
        args_map=lambda e: {"name": e.get("name", "User")},
    ),
    _workflow_step(
        "Generating secure reset link",
        tool="generate_reset_link",
        args_map=lambda e: {"name": e.get("name", "User")},
    ),
    _workflow_step(
        "Sending reset link via email",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": e.get("name", "user").lower().replace(" ", ".") + "@enterprise.com",
            "subject": "Password Reset Link",
            "body": "Click here to reset your password: https://enterprise.com/reset/abc123",
        },
    ),
    _workflow_step("Logging password reset action"),
]


# ────────────────────────────────────────────────────────────
# 8. Attrition Prediction
# ────────────────────────────────────────────────────────────
ATTRITION_PREDICTION_WORKFLOW = [
    _workflow_step("Identified attrition prediction request"),
    _workflow_step(
        "Fetching employee data",
        tool="get_employee_info",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1)},
    ),
    _workflow_step(
        "Running ML attrition model",
        tool="predict_attrition",
        args_map=lambda e: {
            "employee_data": {
                "age": e.get("age", 35),
                "monthly_income": e.get("monthly_income", 50000),
                "years_at_company": e.get("years_at_company", 5),
                "job_satisfaction": e.get("job_satisfaction", 3),
                "overtime": e.get("overtime", False),
            }
        },
    ),
    _workflow_step("Interpreting prediction results"),
    _workflow_step("Generating retention recommendations"),
]


# ────────────────────────────────────────────────────────────
# 9. Notifications / Reminders
# ────────────────────────────────────────────────────────────
NOTIFICATION_WORKFLOW = [
    _workflow_step("Identified reminder request"),
    _workflow_step(
        "Fetching upcoming schedule",
        tool="fetch_schedule",
        args_map=lambda e: {"name": e.get("name", "User")},
    ),
    _workflow_step(
        "Identifying relevant events",
        tool="identify_events",
        args_map=lambda e: {"name": e.get("name", "User")},
    ),
    _workflow_step(
        "Generating reminder notifications",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": e.get("name", "user").lower().replace(" ", ".") + "@enterprise.com",
            "subject": "Upcoming Reminders",
            "body": "Here are your upcoming events and tasks.",
        },
    ),
]


# ────────────────────────────────────────────────────────────
# 10. System Health Check
# ────────────────────────────────────────────────────────────
SYSTEM_HEALTH_WORKFLOW = [
    _workflow_step("Identified system health check request"),
    _workflow_step(
        "Checking database connection",
        tool="check_db_health",
    ),
    _workflow_step(
        "Checking API endpoint health",
        tool="check_api_health",
    ),
    _workflow_step(
        "Checking ML model status",
        tool="check_ml_health",
    ),
    _workflow_step(
        "Detecting anomalies and issues",
        tool="detect_issues",
    ),
    _workflow_step("Compiling health report"),
]


# ── Master mapping: intent → workflow ────────────────────────
WORKFLOW_MAP = {
    "employee_onboarding":  ONBOARDING_WORKFLOW,
    "it_provisioning":      IT_PROVISIONING_WORKFLOW,
    "access_management":    ACCESS_MANAGEMENT_WORKFLOW,
    "leave_request":        LEAVE_REQUEST_WORKFLOW,
    "meeting_scheduling":   MEETING_SCHEDULING_WORKFLOW,
    "it_ticket":            IT_TICKET_WORKFLOW,
    "password_reset":       PASSWORD_RESET_WORKFLOW,
    "attrition_prediction": ATTRITION_PREDICTION_WORKFLOW,
    "notification":         NOTIFICATION_WORKFLOW,
    "system_health":        SYSTEM_HEALTH_WORKFLOW,
}

# ── Chaining rules: intent → list of follow-up intents ──────
# When a primary intent completes, automatically trigger these.
CHAIN_RULES = {
    "employee_onboarding": ["it_provisioning"],
}
