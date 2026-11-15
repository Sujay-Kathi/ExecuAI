import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def test_email():
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    to = "sujaykathi25csds@rnsit.ac.in"
    
    print(f"Attempting to send email from {smtp_email} to {to}...")
    
    try:
        msg = MIMEText("Test email from ExecuAI")
        msg["Subject"] = "ExecuAI SMTP Test"
        msg["From"] = smtp_email
        msg["To"] = to
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.set_debuglevel(1)
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to, msg.as_string())
        print("SUCCESS: Email sent!")
    except Exception as e:
        print(f"FAILURE: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    test_email()
