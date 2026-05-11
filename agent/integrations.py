"""
Real-world API integrations for ExecuAI tools.

Each wrapper tries the real API first. If credentials are missing
or the call fails, it returns None so the caller can fall back to
simulation mode.  This keeps the app functional even without config.

Supported services:
  - Gmail  (SMTP via App Password)
  - Google Calendar (Service Account)
  - Slack  (Incoming Webhook)
  - GitHub (Personal Access Token)
"""
import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# Gmail SMTP Integration
# ────────────────────────────────────────────────────────────

def send_real_email(to: str, subject: str, body: str) -> dict | None:
    """
    Send an email via Gmail SMTP using an App Password.

    Required env vars:
        SMTP_EMAIL        – your Gmail address
        SMTP_APP_PASSWORD – 16-char App Password (not your login pw)

    Returns dict on success, None on failure/missing creds.
    """
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_APP_PASSWORD", "")

    if not smtp_email or not smtp_password:
        return None

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"ExecuAI <{smtp_email}>"
        msg["To"] = to
        msg["Subject"] = subject

        # Plain-text fallback
        msg.attach(MIMEText(body, "plain"))

        # Lean HTML version
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; color: #333; line-height: 1.6;">
            <h2 style="color: #0056b3; border-bottom: 1px solid #eee; padding-bottom: 10px;">{subject}</h2>
            <p>{body.replace(chr(10), '<br>')}</p>
            <p style="font-size: 12px; color: #777; border-top: 1px solid #eee; padding-top: 10px; margin-top: 20px;">
                Sent by ExecuAI Assistant.
            </p>
        </div>
        """
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to, msg.as_string())

        logger.info(f"✉️  Real email sent to {to}: {subject}")
        return {"sent": True, "to": to, "subject": subject, "method": "Gmail SMTP"}

    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return None


# ────────────────────────────────────────────────────────────
# Google Calendar Integration
# ────────────────────────────────────────────────────────────

def _get_calendar_service():
    """
    Build a Google Calendar v3 service.
    Supports both OAuth 2.0 user tokens and service-account JSON.
    Auto-detects the credential type from the file contents.
    """
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path or not os.path.exists(creds_path):
        return None

    try:
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/calendar"]

        # Read JSON to detect type
        with open(creds_path, "r") as f:
            cred_data = json.load(f)

        # OAuth 2.0 user token (from setup_google_auth.py)
        if "refresh_token" in cred_data or "token" in cred_data:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            creds = Credentials.from_authorized_user_file(creds_path, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                with open(creds_path, "w") as f:
                    f.write(creds.to_json())

        # Service account JSON
        elif "type" in cred_data and cred_data["type"] == "service_account":
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES
            )
        else:
            logger.warning("Unrecognized Google credentials format")
            return None

        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    except Exception as e:
        logger.warning(f"Google Calendar init failed: {e}")
        return None


def create_real_calendar_event(
    title: str,
    description: str = "",
    start_time: datetime | None = None,
    duration_minutes: int = 30,
    attendees: list[str] | None = None,
) -> dict | None:
    """
    Create a real Google Calendar event.

    Required env vars:
        GOOGLE_CREDENTIALS_PATH – path to service-account JSON
        GOOGLE_CALENDAR_ID      – calendar id (default: 'primary')
    """
    service = _get_calendar_service()
    if service is None:
        return None

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    if start_time is None:
        start_time = datetime.now(timezone.utc) + timedelta(days=1, hours=2)

    end_time = start_time + timedelta(minutes=duration_minutes)

    event_body = {
        "summary": title,
        "description": description or f"Scheduled by ExecuAI Agent",
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
    }

    if attendees:
        event_body["attendees"] = [{"email": e} for e in attendees]

    try:
        event = service.events().insert(
            calendarId=calendar_id, body=event_body, sendUpdates="all"
        ).execute()

        logger.info(f"📅 Real calendar event created: {event.get('htmlLink')}")
        return {
            "created": True,
            "event_id": event.get("id"),
            "link": event.get("htmlLink"),
            "title": title,
            "start": start_time.isoformat(),
            "method": "Google Calendar API",
        }
    except Exception as e:
        logger.warning(f"Calendar event creation failed: {e}")
        return None


def check_real_availability(
    time_min: datetime | None = None,
    time_max: datetime | None = None,
) -> dict | None:
    """
    Query Google Calendar freebusy to find open slots.
    """
    service = _get_calendar_service()
    if service is None:
        return None

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    if time_min is None:
        time_min = datetime.now(timezone.utc)
    if time_max is None:
        time_max = time_min + timedelta(days=3)

    try:
        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": calendar_id}],
        }
        result = service.freebusy().query(body=body).execute()
        busy = result["calendars"][calendar_id]["busy"]

        return {
            "checked": True,
            "busy_slots": len(busy),
            "busy": busy,
            "method": "Google Calendar freebusy API",
        }
    except Exception as e:
        logger.warning(f"Freebusy query failed: {e}")
        return None


# ────────────────────────────────────────────────────────────
# Slack Webhook Integration
# ────────────────────────────────────────────────────────────

def send_slack_message(text: str, channel_context: str = "") -> dict | None:
    """
    Post a message to Slack via an Incoming Webhook.

    Required env vars:
        SLACK_WEBHOOK_URL – full webhook URL
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return None

    try:
        import requests

        payload = {
            "text": text,
            "username": "ExecuAI Bot",
            "icon_emoji": ":zap:",
        }

        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200 and resp.text == "ok":
            logger.info(f"💬 Slack message sent: {text[:60]}...")
            return {
                "sent": True,
                "channel": channel_context or "webhook-default",
                "method": "Slack Incoming Webhook",
            }
        else:
            logger.warning(f"Slack returned {resp.status_code}: {resp.text}")
            return None

    except Exception as e:
        logger.warning(f"Slack message failed: {e}")
        return None


# ────────────────────────────────────────────────────────────
# GitHub API Integration
# ────────────────────────────────────────────────────────────

def invite_to_github_org(username: str) -> dict | None:
    """
    Invite a user to a GitHub organisation.

    Required env vars:
        GITHUB_TOKEN – PAT with admin:org scope
        GITHUB_ORG   – organisation name
    """
    token = os.getenv("GITHUB_TOKEN", "")
    org = os.getenv("GITHUB_ORG", "")

    if not token or not org:
        return None

    try:
        import requests

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # First resolve username to user ID
        user_resp = requests.get(
            f"https://api.github.com/users/{username}",
            headers=headers, timeout=10,
        )

        if user_resp.status_code != 200:
            logger.warning(f"GitHub user lookup failed for '{username}'")
            return None

        user_id = user_resp.json().get("id")

        # Send org invitation
        invite_resp = requests.post(
            f"https://api.github.com/orgs/{org}/invitations",
            headers=headers,
            json={"invitee_id": user_id, "role": "direct_member"},
            timeout=10,
        )

        if invite_resp.status_code in (201, 422):  # 422 = already invited/member
            logger.info(f"🐙 GitHub invite sent to {username} for org {org}")
            return {
                "invited": True,
                "username": username,
                "org": org,
                "method": "GitHub REST API",
            }
        else:
            logger.warning(f"GitHub invite failed: {invite_resp.status_code}")
            return None

    except Exception as e:
        logger.warning(f"GitHub integration error: {e}")
        return None


def add_github_collaborator(username: str, repo: str) -> dict | None:
    """
    Add a user as a collaborator to a specific GitHub repository.

    Required env vars:
        GITHUB_TOKEN – PAT with repo scope
        GITHUB_ORG   – owner/org name
    """
    token = os.getenv("GITHUB_TOKEN", "")
    org = os.getenv("GITHUB_ORG", "")

    if not token or not org:
        return None

    try:
        import requests

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        resp = requests.put(
            f"https://api.github.com/repos/{org}/{repo}/collaborators/{username}",
            headers=headers,
            json={"permission": "push"},
            timeout=10,
        )

        if resp.status_code in (201, 204):
            logger.info(f"🐙 {username} added to {org}/{repo}")
            return {
                "added": True,
                "username": username,
                "repo": f"{org}/{repo}",
                "permission": "push",
                "method": "GitHub REST API",
            }
        else:
            logger.warning(f"GitHub collab add failed: {resp.status_code}")
            return None

    except Exception as e:
        logger.warning(f"GitHub collaborator error: {e}")
        return None
