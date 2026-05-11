
import os
import sys
from datetime import datetime, timedelta, timezone

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.database import engine, SessionLocal, Base
from backend.models import Employee, LeaveRequest, Meeting, ITTicket

def seed_database():
    print("Initializing temporary database...")
    
    # Ensure data directory exists
    data_dir = os.path.join(ROOT, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    # Recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 1. Create Employees
        employees = [
            Employee(name="Sujay Kathi", email="sujay@enterprise.com", role="CEO & Lead Architect", department="Executive"),
            Employee(name="Rahul Kumar", email="rahul@enterprise.com", role="Senior Software Engineer", department="Engineering"),
            Employee(name="Sarah Jenkins", email="sarah@enterprise.com", role="Product Manager", department="Product"),
            Employee(name="John Doe", email="john.doe@enterprise.com", role="IT Administrator", department="IT Operations"),
            Employee(name="Alice Wang", email="alice.wang@enterprise.com", role="HR Specialist", department="Human Resources"),
            Employee(name="Bob Smith", email="bob.smith@enterprise.com", role="DevOps Engineer", department="Engineering"),
        ]
        db.add_all(employees)
        db.commit()
        print(f"Added {len(employees)} employees.")
        
        # 2. Add some Leave Requests
        leaves = [
            LeaveRequest(employee_id=1, leave_type="casual", start_date=datetime.now(timezone.utc), end_date=datetime.now(timezone.utc) + timedelta(days=2), reason="Short break", status="approved"),
            LeaveRequest(employee_id=2, leave_type="sick", start_date=datetime.now(timezone.utc) - timedelta(days=1), end_date=datetime.now(timezone.utc), reason="Flu", status="approved"),
        ]
        db.add_all(leaves)
        
        # 3. Add some IT Tickets
        tickets = [
            ITTicket(ticket_id="IT-1001", title="VPN Connection Issue", description="Unable to connect to US-East-1 region", priority="high", status="open", assigned_team="Networking"),
            ITTicket(ticket_id="IT-1002", title="New Laptop Request", description="M3 MacBook Pro for new hire", priority="medium", status="in_progress", assigned_team="Procurement"),
        ]
        db.add_all(tickets)
        
        # 4. Add some Meetings
        meetings = [
            Meeting(title="Project Sync", organizer_id=2, scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2), duration_minutes=60, description="Weekly project update"),
            Meeting(title="Sprint Planning", organizer_id=1, scheduled_at=datetime.now(timezone.utc) + timedelta(days=1), duration_minutes=90, description="Planning for Q3 Sprint 1"),
        ]
        db.add_all(meetings)
        
        db.commit()
        print("Database seeding completed successfully!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
