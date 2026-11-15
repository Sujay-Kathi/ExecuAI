"""
Comprehensive Automation Test Suite for ExecuAI.

Tests all 10 automation workflows end-to-end through the agent pipeline:
  1. Employee Onboarding
  2. IT System Provisioning
  3. Access Management
  4. Leave Request
  5. Meeting Scheduling
  6. IT Ticket Creation
  7. Password Reset
  8. Attrition Prediction
  9. Notifications / Reminders
 10. System Health Check

Also tests:
  - Intent classification accuracy
  - Entity extraction
  - Real integration wrappers (Gmail, Slack, Calendar, GitHub) — graceful fallback
  - Tool registry completeness
  - Database operations
  - ML model loading
"""
import os
import sys
import json
import traceback

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Load .env BEFORE importing any project modules
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

# ── Imports (after path setup) ──────────────────────────────
from agent.intent import classify_intent, extract_entities
from agent.tools import TOOL_REGISTRY
from agent.workflows import WORKFLOW_MAP, CHAIN_RULES
from agent.agent import AgentController

# ── Test infrastructure ─────────────────────────────────────
PASSED = 0
FAILED = 0
ERRORS = []


def test(name: str, func):
    """Run a single test and track pass/fail."""
    global PASSED, FAILED
    try:
        func()
        PASSED += 1
        print(f"  [PASS] {name}")
    except AssertionError as e:
        FAILED += 1
        ERRORS.append((name, str(e)))
        print(f"  [FAIL] {name}: {e}")
    except Exception as e:
        FAILED += 1
        tb = traceback.format_exc()
        ERRORS.append((name, f"{e}\n{tb}"))
        print(f"  [ERROR] {name}: {e}")


# ============================================================
# 1. Intent Classification Tests
# ============================================================
def test_intents():
    print("-" * 30 + " 1. Intent Classification " + "-" * 30)

    cases = [
        ("Onboard John as Software Engineer in Engineering", "employee_onboarding"),
        ("I want to hire a new employee", "employee_onboarding"),
        ("Setup systems for Alice", "it_provisioning"),
        ("Provision IT for Bob", "it_provisioning"),
        ("Give access to Jira for John", "access_management"),
        ("Grant Alice access to GitHub", "access_management"),
        ("I need sick leave tomorrow", "leave_request"),
        ("Apply for vacation from May 12 to May 15", "leave_request"),
        ("Schedule meeting about sprint review", "meeting_scheduling"),
        ("Book a meeting with the team", "meeting_scheduling"),
        ("Slack is not working for me", "it_ticket"),
        ("My VPN connection keeps crashing", "it_ticket"),
        ("Reset password for John", "password_reset"),
        ("I forgot my password", "password_reset"),
        ("Predict attrition risk for employee", "attrition_prediction"),
        ("Is John a flight risk?", "attrition_prediction"),
        ("Remind me about upcoming events", "notification"),
        ("Set a reminder for tomorrow", "notification"),
        ("Check system health", "system_health"),
        ("Run diagnostics on the server", "system_health"),
        ("Hello, how are you?", "general"),
    ]

    for text, expected in cases:
        def check(t=text, e=expected):
            result = classify_intent(t)
            assert result == e, f"classify_intent('{t}') → '{result}', expected '{e}'"
        test(f"Intent: {expected} <- \"{text[:50]}\"", check)


# ============================================================
# 2. Entity Extraction Tests
# ============================================================
def test_entities():
    print("\n--- 2. Entity Extraction ---")

    def check_onboard_entities():
        entities = extract_entities("Onboard John as Software Engineer in Engineering", "employee_onboarding")
        assert "name" in entities, f"Missing 'name' in entities: {entities}"
        assert entities["name"] == "John", f"Expected name 'John', got '{entities.get('name')}'"

    def check_leave_entities():
        entities = extract_entities("I need sick leave from 2026-05-12 to 2026-05-15", "leave_request")
        assert entities.get("leave_type") == "sick", f"Expected leave_type 'sick', got '{entities.get('leave_type')}'"

    def check_system_entity():
        entities = extract_entities("Give access to jira for John", "access_management")
        assert entities.get("system") == "Jira", f"Expected system 'Jira', got '{entities.get('system')}'"

    def check_meeting_title():
        entities = extract_entities("Schedule meeting about sprint review", "meeting_scheduling")
        assert "title" in entities, f"Missing 'title' in entities: {entities}"

    test("Extract onboarding entities (name)", check_onboard_entities)
    test("Extract leave entities (type)", check_leave_entities)
    test("Extract system entity (Jira)", check_system_entity)
    test("Extract meeting title", check_meeting_title)


# ============================================================
# 3. Tool Registry Completeness
# ============================================================
def test_tool_registry():
    print("\n--- 3. Tool Registry ---")

    expected_tools = [
        "create_employee_record", "generate_employee_email", "get_employee_info",
        "assign_role", "provision_it_systems", "grant_system_access",
        "check_permissions", "validate_access_eligibility",
        "schedule_meeting", "check_availability", "resolve_conflicts",
        "send_notification_email",
        "check_leave_balance", "validate_leave_request", "apply_leave",
        "categorize_issue", "assign_priority", "create_it_ticket", "assign_it_team",
        "verify_identity", "generate_reset_link",
        "predict_attrition",
        "fetch_schedule", "identify_events",
        "check_db_health", "check_api_health", "check_ml_health", "detect_issues",
    ]

    def check_exists():
        missing = [t for t in expected_tools if t not in TOOL_REGISTRY]
        assert not missing, f"Missing tools: {missing}"

    def check_callable():
        non_callable = [t for t in expected_tools if not callable(TOOL_REGISTRY.get(t))]
        assert not non_callable, f"Non-callable tools: {non_callable}"

    def check_count():
        assert len(TOOL_REGISTRY) >= len(expected_tools), (
            f"Registry has {len(TOOL_REGISTRY)} tools, expected at least {len(expected_tools)}"
        )

    test("All expected tools registered", check_exists)
    test("All tools are callable", check_callable)
    test(f"Tool count >= {len(expected_tools)}", check_count)


# ============================================================
# 4. Workflow Map Completeness
# ============================================================
def test_workflows():
    print("\n--- 4. Workflow Map ---")

    expected_intents = [
        "employee_onboarding", "it_provisioning", "access_management",
        "leave_request", "meeting_scheduling", "it_ticket",
        "password_reset", "attrition_prediction", "notification", "system_health",
    ]

    def check_all_mapped():
        missing = [i for i in expected_intents if i not in WORKFLOW_MAP]
        assert not missing, f"Missing workflows: {missing}"

    def check_steps_structure():
        for intent, steps in WORKFLOW_MAP.items():
            assert isinstance(steps, list), f"Workflow '{intent}' is not a list"
            assert len(steps) > 0, f"Workflow '{intent}' has 0 steps"
            for step in steps:
                assert "action" in step, f"Step in '{intent}' missing 'action'"
                assert "args_map" in step, f"Step in '{intent}' missing 'args_map'"

    def check_chain_rules():
        assert "employee_onboarding" in CHAIN_RULES, "Onboarding should chain to IT provisioning"
        assert "it_provisioning" in CHAIN_RULES["employee_onboarding"]

    test("All intents have workflows", check_all_mapped)
    test("All steps have proper structure", check_steps_structure)
    test("Chain rules configured", check_chain_rules)


# ============================================================
# 5. Individual Tool Tests
# ============================================================
def test_individual_tools():
    print("\n--- 5. Individual Tool Execution ---")

    def _run_tool(tool_name, **kwargs):
        tool_fn = TOOL_REGISTRY[tool_name]
        result = tool_fn(**kwargs)
        assert isinstance(result, dict), f"{tool_name} returned {type(result)}, expected dict"
        assert result.get("status") == "success", f"{tool_name} status: {result.get('status')}"
        return result

    tool_tests = [
        ("create_employee_record", {"name": "Test User", "role": "Tester", "department": "QA"}),
        ("generate_employee_email", {"name": "Test User"}),
        ("get_employee_info", {"employee_id": 1}),
        ("assign_role", {"name": "Test User", "role": "Dev", "department": "Eng"}),
        ("provision_it_systems", {"name": "Test User"}),
        ("grant_system_access", {"name": "Test User", "system": "Jira"}),
        ("check_permissions", {"name": "Test User", "system": "GitHub"}),
        ("validate_access_eligibility", {"name": "Test User", "system": "AWS"}),
        ("schedule_meeting", {"title": "Test Meeting", "organizer": "Test"}),
        ("check_availability", {"name": "Test User"}),
        ("resolve_conflicts", {"title": "Test Meeting"}),
        ("send_notification_email", {"to": "test@example.com", "subject": "Test", "body": "Test body"}),
        ("check_leave_balance", {"employee_id": 1, "leave_type": "casual"}),
        ("validate_leave_request", {"employee_id": 1}),
        ("apply_leave", {"employee_id": 1, "leave_type": "casual"}),
        ("categorize_issue", {"description": "email not working"}),
        ("assign_priority", {"description": "server crash critical outage"}),
        ("create_it_ticket", {"title": "Test Ticket", "description": "Testing", "priority": "low"}),
        ("assign_it_team", {"system": "GitHub"}),
        ("verify_identity", {"name": "Test User"}),
        ("generate_reset_link", {"name": "Test User"}),
        ("predict_attrition", {}),
        ("fetch_schedule", {"name": "Test User"}),
        ("identify_events", {"name": "Test User"}),
        ("check_db_health", {}),
        ("check_api_health", {}),
        ("check_ml_health", {}),
        ("detect_issues", {}),
    ]

    for tool_name, kwargs in tool_tests:
        def check(tn=tool_name, kw=kwargs):
            result = _run_tool(tn, **kw)
            assert result["tool"] == tn, f"Tool name mismatch: {result['tool']} != {tn}"
        test(f"Tool: {tool_name}", check)


# ============================================================
# 6. End-to-End Agent Workflow Tests
# ============================================================
def test_agent_e2e():
    print("\n--- 6. End-to-End Agent Workflows ---")

    controller = AgentController()

    scenarios = [
        ("Onboard Alice as Software Engineer in Engineering", "employee_onboarding"),
        ("Setup systems for Bob", "it_provisioning"),
        ("Grant John access to GitHub", "access_management"),
        ("I need casual leave from 2026-05-15 to 2026-05-16", "leave_request"),
        ("Schedule meeting about sprint planning", "meeting_scheduling"),
        ("My VPN is not working, keeps disconnecting", "it_ticket"),
        ("Reset password for Sarah", "password_reset"),
        ("Predict attrition for employee #3", "attrition_prediction"),
        ("Remind me about upcoming events", "notification"),
        ("Check system health", "system_health"),
    ]

    for user_input, expected_intent in scenarios:
        def check(ui=user_input, ei=expected_intent):
            result = controller.process_request(ui)

            # Verify structure
            assert isinstance(result, dict), f"Result is not a dict: {type(result)}"
            assert "status" in result, f"Missing 'status' in result"
            assert result["status"] == "success", f"Status: {result['status']}"
            assert "intent" in result, f"Missing 'intent' in result"
            assert result["intent"] == ei, f"Intent mismatch: {result['intent']} != {ei}"
            assert "steps" in result, f"Missing 'steps' in result"
            assert len(result["steps"]) > 0, f"No steps executed for {ei}"
            assert "result" in result, f"Missing 'result' in result"
            assert len(result["result"]) > 0, f"Empty result for {ei}"

        test(f"E2E: {expected_intent}", check)


# ============================================================
# 7. Integration Wrappers (graceful fallback)
# ============================================================
def test_integrations():
    print("\n--- 7. Integration Wrappers ---")

    def check_email_integration():
        from agent.integrations import send_real_email
        # Should return dict on success, None if creds missing/invalid
        result = send_real_email("test@example.com", "Test Subject", "Test Body")
        # Result is either a dict (real email sent) or None (fallback)
        assert result is None or isinstance(result, dict), f"Unexpected email result: {result}"

    def check_slack_integration():
        from agent.integrations import send_slack_message
        result = send_slack_message("Test message from ExecuAI automation test")
        assert result is None or isinstance(result, dict), f"Unexpected slack result: {result}"

    def check_calendar_integration():
        from agent.integrations import create_real_calendar_event
        result = create_real_calendar_event(title="Test Event")
        assert result is None or isinstance(result, dict), f"Unexpected calendar result: {result}"

    def check_github_integration():
        from agent.integrations import invite_to_github_org
        result = invite_to_github_org("test-user-nonexistent")
        assert result is None or isinstance(result, dict), f"Unexpected github result: {result}"

    test("Email integration (graceful)", check_email_integration)
    test("Slack integration (graceful)", check_slack_integration)
    test("Calendar integration (graceful)", check_calendar_integration)
    test("GitHub integration (graceful)", check_github_integration)


# ============================================================
# 8. ML Model Tests
# ============================================================
def test_ml_model():
    print("\n--- 8. ML Attrition Model ---")

    def check_model_loads():
        from ml.predictor import AttritionPredictor
        p = AttritionPredictor()
        assert p.model is not None, "Model failed to load (model.pkl missing?)"

    def check_model_predicts():
        from ml.predictor import AttritionPredictor
        p = AttritionPredictor()
        if p.model is None:
            raise AssertionError("Model not loaded — skipping prediction test")
        result = p.predict(age=30, monthly_income=60000, years_at_company=3,
                           job_satisfaction=2, overtime=True)
        assert "prediction" in result, f"Missing 'prediction': {result}"
        assert result["prediction"] in ("Likely to Leave", "Stable"), f"Bad prediction: {result['prediction']}"
        assert 0 <= result["confidence"] <= 1, f"Confidence out of range: {result['confidence']}"

    test("ML model loads successfully", check_model_loads)
    test("ML model produces valid prediction", check_model_predicts)


# ============================================================
# 9. Database Operations Tests
# ============================================================
def test_database():
    print("\n--- 9. Database Operations ---")

    def check_db_init():
        from backend.database import init_db, SessionLocal
        init_db()  # Should not raise
        db = SessionLocal()
        db.close()

    def check_employee_crud():
        from backend.database import SessionLocal
        from backend.models import Employee
        db = SessionLocal()
        # Create
        emp = Employee(name="TestBot", email="testbot@enterprise.com",
                       role="Tester", department="QA")
        db.add(emp)
        db.commit()
        db.refresh(emp)
        eid = emp.id
        assert eid is not None, "Employee ID is None after commit"
        # Read
        fetched = db.query(Employee).filter(Employee.id == eid).first()
        assert fetched is not None, f"Employee {eid} not found"
        assert fetched.name == "TestBot"
        # Cleanup
        db.delete(fetched)
        db.commit()
        db.close()

    def check_execution_log():
        from backend.database import SessionLocal
        from backend.models import ExecutionLog
        db = SessionLocal()
        log = ExecutionLog(
            request_text="test request",
            steps_json=json.dumps(["step1", "step2"]),
            result_summary="test result",
        )
        db.add(log)
        db.commit()
        log_id = log.id
        assert log_id is not None
        # Cleanup
        db.delete(log)
        db.commit()
        db.close()

    test("Database initializes", check_db_init)
    test("Employee CRUD operations", check_employee_crud)
    test("Execution log persistence", check_execution_log)


# ============================================================
# 10. check_db_health — SQL text issue
# ============================================================
def test_db_health_tool():
    print("\n--- 10. DB Health Tool (SQLAlchemy text) ---")

    def check_db_health_executes():
        result = TOOL_REGISTRY["check_db_health"]()
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["database"] == "healthy"

    test("check_db_health returns healthy", check_db_health_executes)


# ============================================================
# Main runner
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  ExecuAI — Comprehensive Automation Test Suite")
    print("=" * 60)

    test_intents()
    test_entities()
    test_tool_registry()
    test_workflows()
    test_individual_tools()
    test_agent_e2e()
    test_integrations()
    test_ml_model()
    test_database()
    test_db_health_tool()

    print("\n" + "=" * 60)
    total = PASSED + FAILED
    print(f"  Results: {PASSED}/{total} passed, {FAILED} failed")
    if ERRORS:
        print(f"\n  Failed tests:")
        for name, err in ERRORS:
            print(f"    [FAIL] {name}")
            for line in err.split("\n")[:3]:
                print(f"       {line}")
    print("=" * 60)

    sys.exit(0 if FAILED == 0 else 1)
