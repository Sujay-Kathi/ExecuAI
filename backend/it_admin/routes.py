from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.models import Employee, SystemRequest, ToolAssigned, AccessLog, IntegrationLog
from agent.tools import (
    fetch_employee_data, 
    create_system_request, 
    assign_tools_access, 
    store_access_log, 
    update_request_status,
    send_email,
    send_notification,
    check_existing_integrations,
    connect_service,
    sync_data,
    store_integration_log
)

router = APIRouter(prefix="/api/it", tags=["IT Admin"])

class ProvisionRequest(BaseModel):
    name: str

class AccessControlRequest(BaseModel):
    name: str
    system: str

class IntegrationRequest(BaseModel):
    name: str
    services: List[str]

# ── Feature 1: System Provisioning ──────────────────

@router.post("/system-provision")
def system_provision(req: ProvisionRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Setup system for an employee."""
    # 1. Fetch employee
    emp_data = fetch_employee_data(req.name)
    if emp_data["status"] == "error":
        raise HTTPException(status_code=404, detail=emp_data["message"])
    
    emp = emp_data["employee"]
    
    # 2. Create system request
    s_req = create_system_request(emp["id"], "provisioning", f"Full setup for {emp['name']}")
    req_id = s_req["request_id"]
    
    # 3. Assign tools
    tools = ["GitHub", "Slack", "Internal Dashboard"]
    for tool in tools:
        assign_tools_access(emp["name"], tool)
        # Store in tools_assigned
        t_assigned = ToolAssigned(employee_id=emp["id"], tool_name=tool)
        db.add(t_assigned)
    
    # 4. Log actions
    store_access_log(emp["id"], f"Provisioned tools: {', '.join(tools)}", "Multiple Systems")
    
    # 5. Update status
    update_request_status(req_id, "completed")
    
    # 6. Send email
    email_body = f"Hello {emp['name']},\n\nYour system setup is complete. You now have access to: {', '.join(tools)}."
    send_email(emp["name"], "System Setup Completed", email_body)
    
    # 7. Notify
    send_notification(emp["name"], "Your IT provisioning is complete.")
    
    db.commit()
    return {"steps": ["Identified provisioning request", "Fetching employee data", "Creating system request", "Assigning tools", "Logging actions", "Sending email notification"], "result": "System setup completed. All tools and access have been assigned and details sent to your email."}

# ── Feature 3: Integration Management ──────────────

@router.post("/integration")
def integration(req: IntegrationRequest, db: Session = Depends(get_db)):
    """Connect systems and sync data."""
    # 1. Check existing
    existing = check_existing_integrations()
    
    # 2. Connect service
    conn = connect_service(req.name, req.services)
    
    # 3. Sync data
    sync_data(req.name)
    
    # 4. Store log
    store_integration_log(req.name, req.services)
    
    # 5. Fetch employee data for the email
    emp_data = fetch_employee_data(req.name)
    if emp_data["status"] == "success":
        emp = emp_data["employee"]
        # 6. Fetch schedule
        from agent.tools import fetch_employee_schedule
        sched = fetch_employee_schedule(emp["name"])
        
        # 7. Send email with schedule
        email_body = (
            f"Hello {emp['name']},\n\n"
            f"The HR system has been successfully connected with your email and calendar.\n\n"
            f"YOUR UPCOMING WORK & MEETING DATES:\n"
            f"{sched.get('schedule', 'No upcoming events found.')}\n\n"
            f"Best regards,\nExecuAI IT Team"
        )
        send_email(emp["name"], "Integration Successful - Your Upcoming Schedule", email_body)
        
        # 8. Notify
        send_notification(emp["name"], f"Integration {req.name} complete. Your schedule has been sent to your email.")
    else:
        # Fallback for Admin
        send_email("Admin", "Integration Successful", f"Integration '{req.name}' with services {req.services} completed.")
        send_notification("Admin", f"Integration {req.name} is now active.")
    
    return {"steps": ["Identify integration request", "Check existing connections", "Connect services", "Sync data", "Store integration details", "Fetch employee schedule", "Send confirmation email with dates"], "result": "Systems successfully integrated and data synchronization completed. Schedule sent to employee email."}
