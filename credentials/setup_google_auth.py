"""
One-time OAuth 2.0 setup for Google Calendar.

Run this script ONCE after downloading your OAuth client JSON:
    python credentials/setup_google_auth.py

It will:
  1. Open your browser for Google sign-in
  2. Ask you to grant Calendar access
  3. Save a token.json that the app uses automatically

You will NOT need to run this again unless the token expires.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDS_DIR = os.path.dirname(os.path.abspath(__file__))
OAUTH_FILE = os.path.join(CREDS_DIR, "google_oauth.json")
TOKEN_FILE = os.path.join(CREDS_DIR, "google_token.json")


def main():
    print("=" * 50)
    print("  ExecuAI — Google Calendar Setup")
    print("=" * 50)

    if not os.path.exists(OAUTH_FILE):
        print(f"\n❌ OAuth client file not found!")
        print(f"   Expected: {OAUTH_FILE}")
        print(f"\n📋 Steps:")
        print(f"   1. Go to https://console.cloud.google.com/")
        print(f"   2. APIs & Services → Credentials")
        print(f"   3. Create OAuth client ID (Desktop app)")
        print(f"   4. Download the JSON")
        print(f"   5. Save it as: {OAUTH_FILE}")
        return

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ Missing packages. Run:")
        print("   pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return

    creds = None

    # Check for existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh or create new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("\n🌐 Opening browser for Google sign-in...")
            print("   Grant access to Google Calendar when prompted.\n")
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the token
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"\n✅ Token saved to: {TOKEN_FILE}")

    # Verify by listing next 3 events
    try:
        from googleapiclient.discovery import build
        from datetime import datetime, timezone

        service = build("calendar", "v3", credentials=creds)
        now = datetime.now(timezone.utc).isoformat()
        result = service.events().list(
            calendarId="primary", timeMin=now,
            maxResults=3, singleEvents=True, orderBy="startTime"
        ).execute()

        events = result.get("items", [])
        print(f"\n📅 Connection verified! Found {len(events)} upcoming event(s):")
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            print(f"   • {start} — {e['summary']}")

        if not events:
            print("   (No upcoming events)")

    except Exception as e:
        print(f"⚠️  Token saved but calendar test failed: {e}")

    print(f"\n🎉 Setup complete! Update your .env:")
    print(f"   GOOGLE_CREDENTIALS_PATH={TOKEN_FILE}")
    print(f"   GOOGLE_CALENDAR_ID=primary")


if __name__ == "__main__":
    main()
