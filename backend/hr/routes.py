from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Employee
from agent.agent import agent

router = APIRouter(prefix="/hr", tags=["HR Analytics"])

@router.get("/performance/{employee_id}")
def get_performance_summary(employee_id: int, db: Session = Depends(get_db)):
    """Fetch performance summary for a specific employee via the Agent."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Trigger the agentic workflow
    query = f"Show {emp.name}'s performance"
    result = agent.handle_query(query)
    return result

@router.get("/attrition-risk")
def get_attrition_risk():
    """Predict attrition risk for all employees using ML."""
    query = "Who might leave?"
    result = agent.handle_query(query)
    return result

@router.post("/notify")
def send_bulk_notification(message: str, group: str = "all"):
    """Send bulk notifications to employees."""
    query = f"Notify all employees: {message}"
    if group != "all":
        query = f"Notify group {group}: {message}"
        
    result = agent.handle_query(query)
    return result
