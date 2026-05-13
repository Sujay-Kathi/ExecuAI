from backend.database import SessionLocal
from backend.models import Employee

def check_db():
    db = SessionLocal()
    employees = db.query(Employee).all()
    print(f"Found {len(employees)} employees in database:")
    for emp in employees:
        print(f"ID: {emp.id}, Name: '{emp.name}', Email: '{emp.email}'")
    db.close()

if __name__ == "__main__":
    check_db()
