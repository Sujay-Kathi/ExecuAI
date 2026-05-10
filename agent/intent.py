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
        "reset password", "forgot password", "change password",
        "password expired", "unlock account", "locked out",
    ]),
    ("attrition_prediction", [
        "likely to leave", "attrition", "churn", "flight risk",
        "retention risk", "will resign", "predict leave",
        "attrition risk",
    ]),
    ("notification",         [
        "remind", "reminder", "notify", "notification",
        "alert me", "send alert", "upcoming events",
    ]),
    ("system_health",        [
        "system status", "health check", "system health",
        "server status", "api status", "is the system up",
        "diagnostics",
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

    # ── Meeting title ──
    if intent == "meeting_scheduling":
        entities["title"] = _extract_meeting_title(text)

    # ── Employee ID ──
    eid = _extract_employee_id(lower)
    if eid:
        entities["employee_id"] = eid

    # ── Attrition-specific fields ──
    if intent == "attrition_prediction":
        entities.update(_extract_attrition_fields(lower))

    return entities


# ── Private helpers ──────────────────────────────────────────

def _extract_name(text: str, intent: str) -> Optional[str]:
    """Extract a person name from the request."""
    lower = text.lower()

    # Pattern: "onboard <Name>", "provision <Name>", etc.
    for keyword in ("onboard", "provision", "hire", "setup system for",
                    "give access to", "grant access to", "remind",
                    "reset password for", "employee"):
        pattern = rf"(?i){keyword}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            # Filter out known non-name words
            if name.lower() not in ("as", "in", "to", "for", "the", "a"):
                return name

    # Fallback: look for capitalized words that aren't at sentence start
    words = text.split()
    for i, word in enumerate(words):
        if i > 0 and word[0].isupper() and word.lower() not in (
            "software", "engineer", "manager", "admin", "hr", "it",
            "senior", "junior", "lead", "director", "vp",
            "monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday", "january", "february", "march",
            "april", "may", "june", "july", "august", "september",
            "october", "november", "december",
        ):
            return word

    return None


def _extract_after_keyword(text: str, keywords: list[str]) -> Optional[str]:
    """Extract the word/phrase immediately after any of the given keywords."""
    for kw in keywords:
        pattern = rf"\b{kw}\s+([\w\s]+)"
        match = re.search(pattern, text)
        if match:
            # Take first 1-3 words
            phrase = match.group(1).strip().split()
            return " ".join(phrase[:3])
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
