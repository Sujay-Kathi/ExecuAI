"""
Intent Classifier — keyword-based + entity extraction.

Maps natural language input to a canonical intent and extracts
relevant entities (names, dates, systems, etc.).

No external API dependency — works fully offline.
"""
import re
from typing import Optional


# ── Intent keyword map ──────────────────────────────────────
# Order matters: more-specific triggers should come first.
INTENT_TRIGGERS = [
    # Composite / specific first
    ("employee_onboarding",  [
        "onboard", "new hire", "new employee", "new joiner",
        "hiring", "bring on", "add employee",
    ]),
    ("it_provisioning",      [
        "setup system", "provision", "system setup", "it setup",
        "configure workstation", "setup laptop", "setup account",
    ]),
    ("access_management",    [
        "give access", "grant access", "revoke access", "remove access",
        "access request", "permission", "add to",
        "grant",  # "Grant Alice access to GitHub" — "grant" alone is specific enough
    ]),
    ("leave_approval",      [
        "approve leave", "reject leave", "authorize leave",
        "deny leave", "grant leave request",
    ]),
    ("leave_request",        [
        "leave", "day off", "time off", "vacation", "sick leave",
        "casual leave", "earned leave", "pto",
    ]),
    ("meeting_scheduling",   [
        "schedule meeting", "book meeting", "set up meeting",
        "arrange meeting", "create meeting", "meeting with",
        "schedule call", "book call",
    ]),
    ("it_ticket",            [
        "not working", "broken", "issue", "bug", "ticket",
        "problem with", "cannot access", "error", "crash",
        "outage", "down", "malfunction",
    ]),
    ("password_reset",       [
        "reset password", "forgot password", "forgot my password",
        "change password", "password expired", "unlock account",
        "locked out", "forgot",
    ]),
    ("attrition_prediction", [
        "likely to leave", "attrition", "churn", "flight risk",
        "retention risk", "will resign", "predict leave",
        "attrition risk",
    ]),
    ("send_message",         [
        "tell", "remind", "send a message to", "message to",
        "inform", "notify", "ping",
    ]),
    ("notification",         [
        "reminder for me", "alert me", "upcoming events",
        "my notifications",
    ]),
    ("system_health",        [
        "system status", "health check", "system health",
        "server status", "api status", "is the system up",
        "diagnostics",
    ]),
    ("task_management",      [
        "what are my tasks", "show my tasks", "task list", "my to-do",
        "pending work", "assigned tasks", "current tasks",
    ]),
    ("work_summary",         [
        "what did i do today", "daily summary", "my activity today",
        "work log", "accomplishments today", "daily report",
    ]),
    ("smart_leave_planning", [
        "plan my leave", "best dates for leave", "suggest leave",
        "when should i take leave", "leave recommendations",
    ]),
    ("performance_insight",  [
        "my performance", "performance review", "how am i doing",
        "performance trends", "growth metrics", "feedback summary",
    ]),
    ("knowledge_assistant",  [
        "how to", "procedure for", "company policy", "where can i find",
        "manual", "guidelines", "reimbursement", "benefits",
    ]),
    ("workload_optimization", [
        "optimize my schedule", "optimize workload", "too many meetings",
        "balance my day", "schedule optimization",
    ]),
    ("it_request_assistant", [
        "i need software", "request software", "software access",
        "install software", "need tools", "request license",
    ]),
    ("notification_intelligence", [
        "important updates", "summarize notifications", "what missed",
        "urgent alerts", "notification summary",
    ]),
    ("retention_analysis",   [
        "deep audit", "retention analysis", "comprehensive report",
        "full insight", "deep dive on employee",
    ]),
    # IT/Admin Master Features (requested by user)
    ("system_provisioning",  [
        "setup system for", "provision system", "full setup",
    ]),
    ("security_management",  [
        "reset my password", "security reset", "account security",
    ]),
    ("integration_management", [
        "connect hr", "integrate system", "sync data between", "link systems",
        "connect services",
    ]),
]


def classify_intent(text: str) -> str:
    """
    Return the best-matching intent string, or 'general' if no match.
    """
    lower = text.lower().strip()
    for intent, triggers in INTENT_TRIGGERS:
        for trigger in triggers:
            if trigger in lower:
                return intent
    return "general"


def extract_entities(text: str, intent: str) -> dict:
    """
    Pull structured entities out of the raw text based on the intent.
    Returns a dict of key→value pairs.
    """
    entities: dict = {}
    lower = text.lower().strip()

    # ── Name extraction (used by onboarding, provisioning, etc.) ──
    name = _extract_name(text, intent)
    if name:
        entities["name"] = name

    # ── Role / department ──
    role = _extract_after_keyword(lower, ["as", "role"])
    if role:
        entities["role"] = role.title()

    dept = _extract_after_keyword(lower, ["in", "department", "dept"])
    if dept and dept.lower() not in ("the", "a", "an"):
        entities["department"] = dept.title()

    # ── System / tool name (for access mgmt, IT tickets) ──
    system = _extract_system(lower)
    if system:
        entities["system"] = system

    # ── Leave type ──
    if intent == "leave_request":
        for lt in ("sick", "casual", "earned", "pto", "vacation"):
            if lt in lower:
                entities["leave_type"] = lt
                break
        dates = _extract_dates(text)
        if dates:
            entities["dates"] = dates

    # ── Meeting title & Recipient ──
    if intent == "meeting_scheduling":
        entities["title"] = _extract_meeting_title(text)
        recipient = _extract_after_keyword(lower, ["with", "invite", "to", "for"])
        if recipient and recipient.lower() not in ("me", "my", "the", "a", "an"):
             # Clean up common possessives
             recipient = recipient.replace("my ", "").replace("your ", "")
             entities["recipient"] = recipient.title()

    # ── Employee ID ──
    eid = _extract_employee_id(lower)
    if eid:
        entities["employee_id"] = eid

    # ── Attrition-specific fields ──
    if intent == "attrition_prediction":
        entities.update(_extract_attrition_fields(lower))

    # ── Message extraction (for reminders/direct pings) ──
    message = _extract_message(text, intent)
    if message:
        entities["message"] = message

    return entities


# ── Private helpers ──────────────────────────────────────────

def _extract_name(text: str, intent: str) -> Optional[str]:
    """Extract a person name from the request."""
    lower = text.lower()

    # Words that signal the name has ended (role / dept / preposition context)
    STOP_WORDS = {
        "as", "in", "to", "for", "the", "a", "an", "from", "with", "on",
        "software", "engineer", "manager", "admin", "administrator",
        "senior", "junior", "lead", "director", "vp", "associate",
        "developer", "analyst", "consultant", "intern", "designer",
        "specialist", "coordinator", "executive", "officer", "architect",
        "hr", "it", "department", "dept", "team", "engineering",
        "marketing", "sales", "finance", "operations", "support",
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday", "january", "february", "march",
        "april", "may", "june", "july", "august", "september",
        "october", "november", "december",
        "access", "system", "account", "password", "email",
    }

    # Pattern: "onboard <Name>", "provision <Name>", etc.
    # Capture one or more capitalized words, but stop at stop-words.
    for keyword in ("onboard", "provision", "hire", "setup system for",
                    "give access to", "grant access to", "grant", "remind", "tell",
                    "to", "with", "for", "message",
                    "reset password for", "employee"):
        # Match words following the keyword
        pattern = rf"(?i){keyword}\s+([\w\s]+)"
        match = re.search(pattern, text)
        if match:
            captured = match.group(1).strip()
            words = captured.split()
            name_parts = []
            for w in words:
                if w.lower() in STOP_WORDS:
                    break
                name_parts.append(w)
            
            if name_parts:
                return " ".join(name_parts).title()

    # Fallback: look for capitalized words that aren't at sentence start
    words = text.split()
    for i, word in enumerate(words):
        if i > 0 and word[0].isupper() and word.lower() not in STOP_WORDS:
            return word

    return None


def _extract_after_keyword(text: str, keywords: list[str]) -> Optional[str]:
    """Extract the word/phrase immediately after any of the given keywords, stopping at prepositions."""
    STOP_WORDS = {"about", "for", "regarding", "on", "at", "titled", "in", "to", "me", "my"}
    for kw in keywords:
        pattern = rf"\b{kw}\s+([\w\s]+)"
        match = re.search(pattern, text)
        if match:
            # Take first 1-3 words but stop at prepositions (that aren't the keyword itself)
            words = match.group(1).strip().split()
            result = []
            for w in words[:3]:
                if w.lower() in STOP_WORDS and w.lower() != kw:
                    break
                result.append(w)
            if result:
                return " ".join(result)
    return None


def _extract_system(text: str) -> Optional[str]:
    """Identify known system names in the text."""
    known = [
        "jira", "github", "slack", "aws", "azure", "google workspace",
        "confluence", "bitbucket", "jenkins", "datadog", "grafana",
        "salesforce", "notion", "figma", "trello", "asana",
        "email", "vpn", "wifi",
    ]
    for system in known:
        if system in text:
            return system.title()
    return None


def _extract_dates(text: str) -> list[str]:
    """Extract date-like strings from the text."""
    patterns = [
        r"\d{4}-\d{2}-\d{2}",           # 2026-05-10
        r"\d{1,2}/\d{1,2}/\d{2,4}",     # 5/10/2026
        r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}",
    ]
    dates = []
    for pat in patterns:
        dates.extend(re.findall(pat, text, re.IGNORECASE))
    return dates


def _extract_meeting_title(text: str) -> str:
    """Extract or generate a meeting title."""
    # Pattern: "schedule meeting about <title>"
    match = re.search(r"(?i)(?:about|for|regarding|on|titled?)\s+(.+)", text)
    if match:
        return match.group(1).strip().rstrip(".")
    return "Team Meeting"


def _extract_employee_id(text: str) -> Optional[int]:
    """Extract an employee ID from the text."""
    match = re.search(r"(?:employee|emp|id)\s*#?\s*(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def _extract_attrition_fields(text: str) -> dict:
    """Extract ML-relevant fields for attrition prediction."""
    fields = {}
    age_match = re.search(r"age\s*[:=]?\s*(\d+)", text)
    if age_match:
        fields["age"] = int(age_match.group(1))
    income_match = re.search(r"(?:salary|income)\s*[:=]?\s*(\d+)", text)
    if income_match:
        fields["monthly_income"] = float(income_match.group(1))
    years_match = re.search(r"(\d+)\s*(?:years?|yrs?)", text)
    if years_match:
        fields["years_at_company"] = int(years_match.group(1))
    return fields
def _extract_message(text: str, intent: str) -> Optional[str]:
    """Capture the actual message content for pings/reminders."""
    if intent != "send_message":
        return None

    lower = text.lower()
    # Patterns for: "Remind Rahul to [message]", "Tell Sarah [message]", etc.
    patterns = [
        r"remind\s+[\w\s]+\s+(?:to|that|about)\s+(.*)",
        r"tell\s+[\w\s]+\s+(.*)",
        r"inform\s+[\w\s]+\s+(?:that|about)\s+(.*)",
        r"send\s+a\s+message\s+to\s+[\w\s]+\s+(?:saying|that|about)?\s*(.*)",
        r"message\s+to\s+[\w\s]+\s+(.*)",
    ]
    for p in patterns:
        match = re.search(p, lower)
        if match:
            return match.group(1).strip()
    return None
