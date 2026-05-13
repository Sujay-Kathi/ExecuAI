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
        "Generating company email",
        tool="generate_company_email",
        args_map=lambda e: {"name": e.get("name", "New Employee")},
    ),
    _workflow_step(
        "Triggering IT provisioning",
        tool="trigger_it_provisioning",
        args_map=lambda e: {"name": e.get("name", "New Employee")},
    ),
    _workflow_step(
        "Scheduling orientation meeting",
        tool="schedule_meeting",
        args_map=lambda e: {
            "title": "Orientation — " + e.get("name", "New Employee"),
            "organizer": "HR",
        },
    ),
    _workflow_step(
        "Sending welcome email",
        tool="send_email",
        args_map=lambda e: {
            "to": e.get("name", "New Employee"),
            "subject": "Welcome to the team!",
            "body": (
                f"Hi {e.get('name', 'there')}, welcome aboard!\n\n"
                f"Your accounts have been set up as {e.get('role', 'an associate')}.\n"
                f"You can now access the portal at: http://localhost:3000\n"
                f"Your login email: {e.get('email', 'N/A')}\n"
                f"Your temporary password: {e.get('password', 'N/A')}\n\n"
                "Please change your password after your first login."
            ),
        },
        condition=lambda e: "role" in e and e["role"] != "Associate", # Check if a specific role was mentioned (Associate is the default)
    ),
    _workflow_step(
        "Notifying team",
        tool="send_notification",
        args_map=lambda e: {
            "text": f"🚀 New team member joining! Please welcome {e.get('name', 'a new colleague')} to the team.",
            "channel": "general"
        }
    ),
]


# ────────────────────────────────────────────────────────────
# 2. Leave Approval System
# ────────────────────────────────────────────────────────────
LEAVE_APPROVAL_WORKFLOW = [
    _workflow_step("Identified leave approval request"),
    _workflow_step(
        "Fetching leave request",
        tool="fetch_leave_request",
        args_map=lambda e: {"employee_name": e.get("name", "Employee")},
    ),
    _workflow_step(
        "Checking leave balance",
        tool="check_leave_balance",
        args_map=lambda e: {
            "employee_id": e.get("employee_id", 1),
            "leave_type": e.get("leave_type", "casual"),
        },
    ),
    _workflow_step(
        "Validating leave policy rules",
        tool="validate_leave_request",
        args_map=lambda e: {
            "employee_id": e.get("employee_id", 1),
            "dates": e.get("dates", []),
        },
    ),
    _workflow_step(
        "Approving leave status",
        tool="update_leave_status",
        args_map=lambda e: {
            "leave_id": 1, # Should be resolved from fetch_leave_request result in a real agent, but following workflow steps for now
            "status": "approved"
        },
    ),
    _workflow_step(
        "Sending confirmation email",
        tool="send_email",
        args_map=lambda e: {
            "to": e.get("name", "Employee"),
            "subject": "Leave Request Approved",
            "body": f"Hi {e.get('name', 'there')}, your leave request has been approved.",
        },
    ),
    _workflow_step(
        "Notifying employee via Slack",
        tool="send_notification",
        args_map=lambda e: {
            "text": f"✅ Your leave request has been approved, {e.get('name', 'there')}!",
            "channel": "direct-message"
        }
    ),
]


# ────────────────────────────────────────────────────────────
# 3. IT System Provisioning
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
# 4. Access Management
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
# 5. Leave Request
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
            "to": "Alice Wang", # Resolved to HR Specialist email
            "subject": "New Leave Request",
            "body": f"Employee #{e.get('employee_id', 1)} has requested {e.get('leave_type', 'casual')} leave.",
        },
    ),
    _workflow_step("Updating leave management system"),
]


# ────────────────────────────────────────────────────────────
# 6. Meeting Scheduling
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
            "attendees": [e.get("recipient", "Team")]
        },
    ),
    _workflow_step(
        "Sending meeting invites",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": e.get("recipient", "Team"),
            "subject": f"Meeting Invite: {e.get('title', 'Team Meeting')}",
            "body": f"Hi {e.get('recipient', 'Team')},\n\nYou are invited to '{e.get('title', 'Team Meeting')}'.",
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
            "to": e.get("name", "User"),
            "subject": "IT Ticket Created",
            "body": "Your IT support ticket has been created and assigned. We'll get back to you shortly.",
        },
    ),
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
            "to": e.get("name", "User"),
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


# ────────────────────────────────────────────────────────────
# 11. Task Management Assistant
# ────────────────────────────────────────────────────────────
TASK_MANAGEMENT_WORKFLOW = [
    _workflow_step("Identified task query"),
    _workflow_step(
        "Fetching employee task list",
        tool="fetch_employee_tasks",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1)},
    ),
    _workflow_step(
        "Analyzing task priorities",
        tool="prioritize_tasks",
        args_map=lambda e: {"tasks": [
            {"id": 101, "title": "Update API documentation", "priority": "high", "due": "Today"},
            {"id": 102, "title": "Review PR #452", "priority": "medium", "due": "Tomorrow"},
            {"id": 103, "title": "Fix bug in login flow", "priority": "high", "due": "Today"}
        ]},
    ),
    _workflow_step("Sorting tasks by urgency"),
    _workflow_step("Generating structured task list"),
]


# ────────────────────────────────────────────────────────────
# 12. Daily Work Summary Generator
# ────────────────────────────────────────────────────────────
WORK_SUMMARY_WORKFLOW = [
    _workflow_step("Identified request for work summary"),
    _workflow_step(
        "Fetching recent activity logs",
        tool="fetch_activity_logs",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1)},
    ),
    _workflow_step(
        "Summarizing completed tasks and contributions",
        tool="summarize_activities",
        args_map=lambda e: {"logs": [
            "Committed 3 changes to 'backend/auth.py'",
            "Closed 2 Jira tickets (IT-402, IT-405)",
            "Attended Sprint Standup"
        ]},
    ),
    _workflow_step("Generating professional daily report"),
]


# ────────────────────────────────────────────────────────────
# 13. Smart Leave Planning
# ────────────────────────────────────────────────────────────
SMART_LEAVE_PLANNING_WORKFLOW = [
    _workflow_step("Identified leave planning request"),
    _workflow_step(
        "Checking current leave balance",
        tool="check_leave_balance",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1), "leave_type": "earned"},
    ),
    _workflow_step(
        "Analyzing upcoming workload and milestones",
        tool="analyze_workload",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1)},
    ),
    _workflow_step(
        "Identifying low-density periods",
        tool="suggest_leave_dates",
        args_map=lambda e: {"balance": 15, "workload": {"status": "moderately busy"}},
    ),
    _workflow_step("Suggesting optimal leave schedule"),
]


# ────────────────────────────────────────────────────────────
# 14. Performance Insight
# ────────────────────────────────────────────────────────────
PERFORMANCE_INSIGHT_WORKFLOW = [
    _workflow_step("Identified request for performance data"),
    _workflow_step(
        "Fetching performance KPIs and metrics",
        tool="fetch_performance_data",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1)},
    ),
    _workflow_step(
        "Analyzing trends and growth areas",
        tool="analyze_performance_trends",
        args_map=lambda e: {"data": {"tasks_completed": 45, "code_quality": "92%"}},
    ),
    _workflow_step("Highlighting strengths and improvement points"),
]


# ────────────────────────────────────────────────────────────
# 15. Internal Knowledge Assistant
# ────────────────────────────────────────────────────────────
KNOWLEDGE_ASSISTANT_WORKFLOW = [
    _workflow_step("Identified knowledge base query"),
    _workflow_step(
        "Searching company policies and documentation",
        tool="search_knowledge_base",
        args_map=lambda e: {"query": e.get("raw_text", "reimbursement policy")},
    ),
    _workflow_step(
        "Extracting relevant procedural information",
        tool="extract_policy_info",
        args_map=lambda e: {"search_results": [{"title": "Policy", "snippet": "..."}]},
    ),
    _workflow_step("Summarizing steps for user"),
]


# ────────────────────────────────────────────────────────────
# 16. Workload Optimization
# ────────────────────────────────────────────────────────────
WORKLOAD_OPTIMIZATION_WORKFLOW = [
    _workflow_step("Identified schedule optimization request"),
    _workflow_step(
        "Analyzing calendar for meeting density",
        tool="detect_schedule_overload",
        args_map=lambda e: {"calendar_data": {}},
    ),
    _workflow_step(
        "Identifying rescheduling opportunities",
        tool="suggest_rescheduling",
        args_map=lambda e: {"overloaded_slots": ["Wednesday PM"]},
    ),
    _workflow_step("Proposing balanced daily schedule"),
]


# ────────────────────────────────────────────────────────────
# 17. Smart IT Request Assistant
# ────────────────────────────────────────────────────────────
IT_REQUEST_ASSISTANT_WORKFLOW = [
    _workflow_step("Identified software request"),
    _workflow_step(
        "Checking role-based software eligibility",
        tool="check_software_eligibility",
        args_map=lambda e: {"role": e.get("role", "Software Engineer"), "software": e.get("system", "IntelliJ")},
    ),
    _workflow_step(
        "Creating automated access request",
        tool="grant_system_access",
        args_map=lambda e: {"name": e.get("name", "Employee"), "system": e.get("system", "Software")},
    ),
    _workflow_step(
        "Notifying IT administration team",
        tool="send_notification_email",
        args_map=lambda e: {"to": "John Doe", "subject": "Software Request", "body": "License requested."},
    ),
]


# ────────────────────────────────────────────────────────────
# 18. Notification Intelligence
# ────────────────────────────────────────────────────────────
NOTIFICATION_INTELLIGENCE_WORKFLOW = [
    _workflow_step("Identified request for important updates"),
    _workflow_step(
        "Fetching all unread unread notifications",
        tool="fetch_notifications",
        args_map=lambda e: {"employee_id": e.get("employee_id", 1)},
    ),
    _workflow_step(
        "Prioritizing urgent alerts and mentions",
        tool="filter_important_notifications",
        args_map=lambda e: {"notifications": []},
    ),
    _workflow_step("Summarizing critical updates"),
]


# ────────────────────────────────────────────────────────────
# 19. Comprehensive Retention Analysis (Master Demo)
# ────────────────────────────────────────────────────────────
RETENTION_ANALYSIS_WORKFLOW = [
    _workflow_step("Initializing deep retention audit"),
    _workflow_step(
        "Fetching employee profile",
        tool="get_employee_data",
        args_map=lambda e: {"name": e.get("name", "Rahul")},
    ),
    _workflow_step(
        "Running ML Attrition Prediction (Random Forest)",
        tool="predict_attrition",
        args_map=lambda e: {"name": e.get("name", "Rahul")},
    ),
    _workflow_step(
        "Auditing current task load",
        tool="fetch_employee_tasks",
        args_map=lambda e: {"employee_id": 1},
    ),
    _workflow_step(
        "Analyzing burnout risk vs productivity",
        tool="analyze_workload",
        args_map=lambda e: {"employee_id": 1},
    ),
    _workflow_step("Compiling multi-dimensional HR insight report"),
]
 
 
# ────────────────────────────────────────────────────────────
# 21. FEATURE 1: System Provisioning
# ────────────────────────────────────────────────────────────
SYSTEM_PROVISIONING_WORKFLOW = [
    _workflow_step("Identifying provisioning request"),
    _workflow_step("Fetching employee details"),
    _workflow_step(
        "Creating company email",
        tool="create_company_email",
        args_map=lambda e: {"name": e.get("name", "Rahul")},
    ),
    _workflow_step(
        "Creating internal account",
        tool="create_user_account",
        args_map=lambda e: {"name": e.get("name", "Rahul")},
    ),
    _workflow_step(
        "Assigning tool access (GitHub, Slack)",
        tool="assign_tools_access",
        args_map=lambda e: {
            "name": e.get("name", "Rahul"),
            "tools": ["GitHub", "Slack", "Jira"]
        },
    ),
    _workflow_step(
        "Sending credentials via email",
        tool="send_email",
        args_map=lambda e: {
            "to": e.get("name", "Rahul"),
            "subject": "System Access Provisioned",
            "body": (
                f"Your corporate systems are ready.\n\n"
                f"LOGIN CREDENTIALS:\n"
                f"Email/Login ID: {e.get('email', 'Pending')}\n"
                f"Temporary Password: {e.get('temporary_password', 'Sent separately')}\n\n"
                f"EXTERNAL TOOL ACCESS:\n"
                f"Slack Workspace: {e.get('slack_workspace', 'ExecuAI-HQ')}\n"
                f"Slack ID: {e.get('slack_id', 'Assigned')}\n"
                f"GitHub Username: {e.get('github_username', 'Pending')}\n\n"
                f"Please login and change your password immediately."
            )
        },
    ),
    _workflow_step(
        "Notifying team of new setup",
        tool="send_notification",
        args_map=lambda e: {
            "text": f"System setup completed for {e.get('name', 'Rahul')}. Access to Slack and GitHub granted.",
            "channel": "general"
        }
    ),
]




# ────────────────────────────────────────────────────────────
# 23. FEATURE 3: Integration Management
# ────────────────────────────────────────────────────────────
INTEGRATION_MANAGEMENT_WORKFLOW = [
    _workflow_step("Identifying integration request"),
    _workflow_step(
        "Checking existing system connections",
        tool="check_system_connections",
    ),
    _workflow_step(
        "Connecting services via API",
        tool="connect_service_api",
        args_map=lambda e: {"service": e.get("system", "HR System")},
    ),
    _workflow_step(
        "Synchronizing data across systems",
        tool="sync_data_between_systems",
        args_map=lambda e: {
            "source": e.get("system", "HR"),
            "target": "Email/Calendar"
        },
    ),
    _workflow_step("Validating integration success"),
    _workflow_step(
        "Notifying administrator",
        tool="send_notification",
        args_map=lambda e: {
            "text": f"Integration successful: {e.get('system', 'HR')} system now synced with Email and Calendar.",
            "channel": "admin"
        }
    ),
]
SEND_MESSAGE_WORKFLOW = [
    _workflow_step("Identified message request for a colleague"),
    _workflow_step(
        "Conveying message via agent",
        tool="send_notification_email",
        args_map=lambda e: {
            "to": e.get("name", "Colleague"),
            "subject": "Message from Colleague (via ExecuAI)",
            "body": (
                f"Hi {e.get('name', 'there')},\n\n"
                f"I'm ExecuAI, your enterprise assistant. Your colleague asked me to reach out and remind you about the following:\n\n"
                f"\"{e.get('message', '...')}\"\n\n"
                f"Is there anything I can help you with regarding this?\n\n"
                f"Best regards,\n"
                f"ExecuAI"
            ),
        },
    ),
]


# ────────────────────────────────────────────────────────────
# 21. Workforce Insights Dashboard
# ────────────────────────────────────────────────────────────
WORKFORCE_INSIGHTS_WORKFLOW = [
    _workflow_step("Identified analytics request"),
    _workflow_step(
        "Fetching employee data",
        tool="fetch_employee_data",
    ),
    _workflow_step(
        "Fetching leave records",
        tool="fetch_leave_records",
    ),
    _workflow_step(
        "Calculating workforce metrics",
        tool="calculate_metrics",
        args_map=lambda e: {
            "employees": e.get("employees", []),
            "leaves": e.get("leaves", []),
        },
    ),
    _workflow_step(
        "Running attrition prediction model",
        tool="predict_attrition",
        args_map=lambda e: {"name": "Workforce Analytics"},
    ),
    _workflow_step(
        "Generating insights report",
        tool="generate_report",
        args_map=lambda e: {
            "metrics": e.get("metrics", {}),
            "attrition": e.get("detail", {}), # result from previous step
        },
    ),
]


# ────────────────────────────────────────────────────────────
# 22. Recruitment Assistant
# ────────────────────────────────────────────────────────────
RECRUITMENT_WORKFLOW = [
    _workflow_step("Identified recruitment request"),
    _workflow_step(
        "Capturing candidate details",
    ),
    _workflow_step(
        "Creating candidate record",
        tool="add_candidate_record",
        args_map=lambda e: {
            "name": e.get("name", "Candidate"),
            "role": e.get("role", "Applicant"),
            "email": e.get("email", "candidate@example.com"),
        },
    ),
    _workflow_step(
        "Scheduling interview",
        tool="schedule_interview",
        args_map=lambda e: {
            "title": f"Interview: {e.get('name', 'Candidate')} for {e.get('role', 'Applicant')}",
            "attendees": [e.get("email", "candidate@example.com")],
        },
    ),
    _workflow_step(
        "Sending interview invitation",
        tool="send_email",
        args_map=lambda e: {
            "to": e.get("email", "candidate@example.com"),
            "subject": "Interview Invitation",
            "body": f"Hi {e.get('name', 'there')}, you are invited for an interview for the {e.get('role', 'position')} role.",
        },
    ),
    _workflow_step(
        "Updating candidate status",
        tool="update_candidate_status",
        args_map=lambda e: {
            "candidate_id": e.get("candidate_id", 0),
            "status": "interview_scheduled",
        },
    ),
    _workflow_step(
        "Notifying HR team",
        tool="send_notification",
        args_map=lambda e: {
            "text": f"New candidate {e.get('name', 'Candidate')} added and interview scheduled.",
            "channel": "hr-recruitment",
        },
    ),
]


# ────────────────────────────────────────────────────────────
# 23. Policy Assistant
# ────────────────────────────────────────────────────────────
POLICY_ASSISTANT_WORKFLOW = [
    _workflow_step("Identified policy query intent"),
    _workflow_step(
        "Fetching HR policy documents",
        tool="fetch_policy_documents",
    ),
    _workflow_step(
        "Searching relevant content",
        tool="search_policy_content",
        args_map=lambda e: {
            "documents": e.get("documents", []),
            "query": e.get("query", "leave policy")
        },
    ),
    _workflow_step(
        "Summarizing policy details",
        tool="summarize_text",
        args_map=lambda e: {
            "text": str(e.get("matches", [{}])[0].get("snippet", "")) if e.get("matches") else "No relevant policy found."
        },
    ),
]


# ────────────────────────────────────────────────────────────
# 24. Performance Summary
# ────────────────────────────────────────────────────────────
PERFORMANCE_SUMMARY_WORKFLOW = [
    _workflow_step("Identified performance query"),
    _workflow_step(
        "Fetching employee data",
        tool="fetch_employee_data",
        args_map=lambda e: {"name": e.get("name", "Rahul")},
    ),
    _workflow_step(
        "Retrieving performance metrics",
        tool="fetch_performance_metrics",
        args_map=lambda e: {"name": e.get("name", "Rahul")},
    ),
    _workflow_step(
        "Analyzing performance trends",
        tool="analyze_performance",
        args_map=lambda e: {"metrics": e.get("metrics", {})},
    ),
    _workflow_step(
        "Generating performance report",
        tool="generate_report",
        args_map=lambda e: {
            "metrics": e.get("metrics", {}),
            "performance": {
                "strengths": e.get("strengths", []),
                "improvements": e.get("improvement_areas", []),
                "score": e.get("overall_score", 0)
            }
        },
    ),
    _workflow_step(
        "Notifying management",
        tool="send_notification",
        args_map=lambda e: {
            "text": f"Performance summary generated for {e.get('name', 'Rahul')}. Overall score: {e.get('overall_score', 0):.1f}%",
            "channel": "hr-reviews"
        },
    ),
]


# ── Master mapping: intent → workflow ────────────────────────
WORKFLOW_MAP = {
    "employee_onboarding":  ONBOARDING_WORKFLOW,
    "leave_approval":       LEAVE_APPROVAL_WORKFLOW,
    "leave_request":        LEAVE_REQUEST_WORKFLOW,
    "meeting_scheduling":   MEETING_SCHEDULING_WORKFLOW,
    "it_ticket":            IT_TICKET_WORKFLOW,
    "attrition_prediction": ATTRITION_PREDICTION_WORKFLOW,
    "notification":         NOTIFICATION_WORKFLOW,
    "system_health":        SYSTEM_HEALTH_WORKFLOW,
    "workforce_insights":   WORKFORCE_INSIGHTS_WORKFLOW,
    "recruitment":          RECRUITMENT_WORKFLOW,
    "policy_assistant":     POLICY_ASSISTANT_WORKFLOW,
    "performance_summary":  PERFORMANCE_SUMMARY_WORKFLOW,

    # New Features
    "task_management":      TASK_MANAGEMENT_WORKFLOW,
    "work_summary":         WORK_SUMMARY_WORKFLOW,
    "smart_leave_planning": SMART_LEAVE_PLANNING_WORKFLOW,
    "performance_insight":  PERFORMANCE_INSIGHT_WORKFLOW,
    "knowledge_assistant":  KNOWLEDGE_ASSISTANT_WORKFLOW,
    "workload_optimization": WORKLOAD_OPTIMIZATION_WORKFLOW,
    "it_request_assistant": IT_REQUEST_ASSISTANT_WORKFLOW,
    "notification_intelligence": NOTIFICATION_INTELLIGENCE_WORKFLOW,
    "retention_analysis":   RETENTION_ANALYSIS_WORKFLOW,
    "send_message":         SEND_MESSAGE_WORKFLOW,

    # Master IT/Admin Workflows
    "system_provisioning":  SYSTEM_PROVISIONING_WORKFLOW,
    "integration_management": INTEGRATION_MANAGEMENT_WORKFLOW,
}

# ── Chaining rules: intent → list of follow-up intents ──────
# When a primary intent completes, automatically trigger these.
CHAIN_RULES = {
}
