"""
SQLAlchemy ORM models for the enterprise assistant.

== ASSIGNMENT ==
  - Backend developer: add/modify columns as needed.
  - Feature devs (HR / Employee modules): extend with new tables if required.
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.database import Base


class Employee(Base):
    """Core employee record."""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(100), nullable=False)
    department = Column(String(100), default="General")
    password_hash = Column(String(255), nullable=True)
    temp_password = Column(String(50), nullable=True)
    slack_id = Column(String(50), nullable=True)
    github_username = Column(String(100), nullable=True)
    date_joined = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    leave_requests = relationship("LeaveRequest", back_populates="employee")

    def __repr__(self):
        return f"<Employee {self.name} ({self.role})>"


class LeaveRequest(Base):
    """Leave management records."""
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type = Column(String(50), nullable=False)           # sick, casual, earned
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(Text, default="")
    status = Column(
        String(20),
        default="pending"       # pending | approved | rejected
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    employee = relationship("Employee", back_populates="leave_requests")


class Meeting(Base):
    """Meeting / calendar entries."""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    organizer_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ExecutionLog(Base):
    """Stores the step-by-step execution logs shown in the UI."""
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_text = Column(Text, nullable=False)
    steps_json = Column(Text, nullable=False)       # JSON array of step dicts
    result_summary = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AccessRequest(Base):
    """IT Admin — tracks system access requests (grant / revoke)."""
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    system_name = Column(String(100), nullable=False)     # e.g. "Jira", "AWS Console"
    access_type = Column(String(50), default="read")      # read | write | admin
    status = Column(String(20), default="pending")        # pending | granted | denied
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ITTicket(Base):
    """IT support tickets created by users or the agent."""
    __tablename__ = "it_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(20), unique=True, nullable=False)   # e.g. "IT-4821"
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category = Column(String(100), default="General IT")
    priority = Column(String(20), default="medium")               # low | medium | high | critical
    status = Column(String(20), default="open")                   # open | in_progress | resolved | closed
    assigned_team = Column(String(100), default="General IT Support")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


class Candidate(Base):
    """Recruitment candidate records."""
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(100), nullable=False)
    status = Column(String(50), default="new")  # new | interview_scheduled | offered | hired
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Feature 1, 2, 3: IT/Admin Tables ──────────────────────────

class SystemRequest(Base):
    """Master IT — tracks system provisioning and access requests."""
    __tablename__ = "system_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    request_type = Column(String(100), nullable=False)  # provisioning | access_control | integration
    details = Column(Text, default="")
    status = Column(String(50), default="pending")      # pending | completed | failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AccessLog(Base):
    """Audit trail for all access-related actions."""
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    action = Column(String(255), nullable=False)        # e.g. "Granted access to AWS"
    system = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ToolAssigned(Base):
    """Inventory of tools assigned to employees."""
    __tablename__ = "tools_assigned"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)     # e.g. "Slack", "GitHub"
    access_level = Column(String(50), default="user")
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IntegrationLog(Base):
    """Registry of system integrations and their status."""
    __tablename__ = "integration_logs"

    id = Column(Integer, primary_key=True, index=True)
    integration_name = Column(String(200), nullable=False)
    services = Column(String(255), nullable=False)       # comma-separated services
    status = Column(String(50), default="active")
    last_sync = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
