"""
Tools layer — callable functions the AI Agent can invoke.

== ASSIGNMENT: AI Engineer ==
  - Each tool is a function the agent planner can call.
  - Add new tools as features expand (email, calendar, etc.).

== ASSIGNMENT: Integration Lead ==
  - Wire these tools to actual external APIs for production.
"""


def create_employee_record(name: str, role: str, department: str) -> dict:
    """Tool: create an employee record in the database."""
    # TODO: call the /api/employees POST endpoint or DB directly
    return {"tool": "create_employee_record", "status": "success", "name": name}


def generate_employee_email(name: str) -> dict:
    """Tool: generate a corporate email for a new employee."""
    email = f"{name.lower().replace(' ', '.')}@enterprise.com"
    return {"tool": "generate_employee_email", "status": "success", "email": email}


def schedule_meeting(title: str, organizer_id: int, datetime_str: str) -> dict:
    """Tool: schedule a meeting / orientation session."""
    # TODO: call Google Calendar API or internal meeting endpoint
    return {"tool": "schedule_meeting", "status": "success", "title": title}


def send_notification_email(to: str, subject: str, body: str) -> dict:
    """Tool: send an email notification (Gmail API or SMTP)."""
    # TODO: implement Gmail API integration
    return {"tool": "send_notification_email", "status": "success", "to": to}


def apply_leave(employee_id: int, leave_type: str, start: str, end: str) -> dict:
    """Tool: submit a leave request."""
    # TODO: call /api/leaves POST
    return {"tool": "apply_leave", "status": "success", "employee_id": employee_id}


def predict_attrition(employee_data: dict) -> dict:
    """Tool: call the ML model to predict employee attrition."""
    # TODO: call /api/ml/predict-attrition
    return {"tool": "predict_attrition", "status": "success", "prediction": "Stable"}


def get_employee_info(employee_id: int) -> dict:
    """Tool: retrieve salary, role, policies for an employee."""
    # TODO: call /api/employees/{id}
    return {"tool": "get_employee_info", "status": "success", "employee_id": employee_id}


# ── Tool registry (used by the agent planner) ───────
TOOL_REGISTRY = {
    "create_employee_record": create_employee_record,
    "generate_employee_email": generate_employee_email,
    "schedule_meeting": schedule_meeting,
    "send_notification_email": send_notification_email,
    "apply_leave": apply_leave,
    "predict_attrition": predict_attrition,
    "get_employee_info": get_employee_info,
}
