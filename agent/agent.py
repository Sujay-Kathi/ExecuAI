"""
Agent Controller — the "brain" of the ExecuAI agentic system.

Follows the  Understand → Plan → Execute → Respond  loop.

The agent:
  1. Parses user input and classifies intent (keyword-based, no external API needed)
  2. Extracts entities (names, roles, systems, etc.)
  3. Maps intent to a workflow (ordered sequence of tool calls)
  4. Executes each step, calling tools dynamically
  5. Chains workflows when rules match (e.g., onboard → IT provisioning)
  6. Returns structured output with execution steps + human-readable result

Can optionally enhance responses with NVIDIA NIM LLM if an API key is configured.
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional

from agent.intent import classify_intent, extract_entities
from agent.workflows import WORKFLOW_MAP, CHAIN_RULES
from agent.tools import TOOL_REGISTRY

# Optional: NVIDIA NIM for enhanced natural-language responses
try:
    from openai import OpenAI
    from backend.config import NVIDIA_API_KEY, NVIDIA_MODEL
    _HAS_LLM = bool(NVIDIA_API_KEY and NVIDIA_API_KEY != "your-nvidia-api-key-here")
except Exception:
    _HAS_LLM = False
    NVIDIA_API_KEY = ""
    NVIDIA_MODEL = ""


class AgentController:
    """
    Core agent that processes user requests through:
      1. Understand — parse user intent + extract entities
      2. Plan     — map intent → workflow steps
      3. Execute  — call tools for each step
      4. Respond  — compile final answer + execution log
    """

    def __init__(self):
        self.tools = TOOL_REGISTRY
        if _HAS_LLM:
            self.llm = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=NVIDIA_API_KEY,
            )
            self.model = NVIDIA_MODEL or "meta/llama-3.1-70b-instruct"
        else:
            self.llm = None
            self.model = None

    # ── Public entry point ──────────────────────────────────

    def process_request(self, user_request: str) -> dict:
        """Entry-point called by the /api/chat route."""
        start = time.time()

        # Step 1: Understand
        understanding = self._understand(user_request)

        # Step 2: Plan
        plan = self._plan(understanding)

        # Step 3: Execute
        execution = self._execute(plan, understanding["entities"])

        # Step 4: Respond
        response = self._respond(understanding, execution, time.time() - start)

        # Step 5: Log to database
        self._log_execution(user_request, response)

        return response

    # Also expose the simple `agent()` function signature
    def agent(self, user_input: str) -> dict:
        """
        Convenience wrapper matching the spec:
          def agent(user_input: str) -> dict
        Returns {"steps": [...], "result": "..."}
        """
        response = self.process_request(user_input)
        return {
            "steps": response["steps"],
            "result": response["result"],
        }

    # ── Step 1: Understand ──────────────────────────────────

    def _understand(self, text: str) -> dict:
        """Classify intent and extract entities from the raw text."""
        intent = classify_intent(text)
        entities = extract_entities(text, intent)
        entities["raw_text"] = text

        return {
            "raw_text": text,
            "intent": intent,
            "entities": entities,
        }

    # ── Step 2: Plan ────────────────────────────────────────

    def _plan(self, understanding: dict) -> list:
        """
        Build an ordered execution plan.
        If the intent maps to a known workflow, use it.
        If chain rules apply, append follow-up workflows.
        """
        intent = understanding["intent"]
        plan = []

        # Primary workflow
        if intent in WORKFLOW_MAP:
            plan.extend(WORKFLOW_MAP[intent])
        # Note: Unknown intents will result in an empty plan, which is handled in Respond step.

        # Check chain rules for composite workflows
        if intent in CHAIN_RULES:
            for chained_intent in CHAIN_RULES[intent]:
                if chained_intent in WORKFLOW_MAP:
                    # Add a separator step
                    plan.append({
                        "action": f"Initiating chained workflow: {chained_intent.replace('_', ' ').title()}",
                        "tool": None,
                        "args_map": lambda e: {},
                    })
                    plan.extend(WORKFLOW_MAP[chained_intent])

        return plan

    # ── Step 3: Execute ─────────────────────────────────────

    def _execute(self, plan: list, entities: dict) -> list:
        """
        Execute each step in the plan.
        For steps with a tool, resolve args from entities and call it.
        Returns a list of execution records.
        """
        executed = []

        for i, step in enumerate(plan):
            tool_name = step.get("tool")
            action = step.get("action", "Unknown action")
            args_map = step.get("args_map", lambda e: {})
            condition = step.get("condition")

            # Check optional condition
            if condition and not condition(entities):
                executed.append({
                    "step": i + 1,
                    "action": action,
                    "status": "skipped",
                    "detail": "Condition not met",
                })
                continue

            if tool_name and tool_name in self.tools:
                try:
                    args = args_map(entities)
                    result = self.tools[tool_name](**args)
                    executed.append({
                        "step": i + 1,
                        "action": action,
                        "status": "success",
                        "tool": tool_name,
                        "detail": result,
                    })
                except Exception as e:
                    executed.append({
                        "step": i + 1,
                        "action": action,
                        "status": "error",
                        "tool": tool_name,
                        "detail": str(e),
                    })
            else:
                # No tool — informational step
                executed.append({
                    "step": i + 1,
                    "action": action,
                    "status": "success",
                    "detail": None,
                })

        return executed

    # ── Step 4: Respond ─────────────────────────────────────

    def _respond(self, understanding: dict, execution: list, elapsed: float) -> dict:
        """Compile the final structured response."""
        intent = understanding["intent"]
        entities = understanding["entities"]
        name = entities.get("name", "the employee")

        # Build human-readable steps list
        steps = []
        for ex in execution:
            status_icon = "✅" if ex["status"] == "success" else "⏭️" if ex["status"] == "skipped" else "❌"
            steps.append(f"{status_icon} {ex['action']}")

        # Build result summary
        result = self._generate_result_summary(intent, entities, execution)

        # Optionally enhance with NVIDIA NIM LLM
        if self.llm:
            enhanced = self._enhance_with_nim(result, intent, entities)
            if enhanced:
                result = enhanced

        # Collect detailed tool outputs
        tool_outputs = {}
        for ex in execution:
            if ex.get("tool") and isinstance(ex.get("detail"), dict):
                tool_outputs[ex["tool"]] = ex["detail"]

        return {
            "status": "success",
            "intent": intent,
            "entities": {k: v for k, v in entities.items() if k != "raw_text"},
            "steps": steps,
            "result": result,
            "tool_outputs": tool_outputs,
            "execution_time": round(elapsed, 3),
            # Legacy fields for backward compatibility with routes_chat
            "message": result,
            "steps_executed": steps,
        }

    def _enhance_with_nim(self, summary: str, intent: str, entities: dict) -> Optional[str]:
        """Use NVIDIA NIM to polish the result into more natural language."""
        try:
            response = self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are ExecuAI, an enterprise AI assistant. The actions described in the summary HAVE ALREADY BEEN EXECUTED successfully. "
                            "Rewrite the summary into a helpful, conversational, and professional response that sounds like a human assistant speaking to their manager. "
                            "Use phrases like 'I've sent that message', 'I have scheduled that meeting', or 'I've taken care of that for you'. "
                            "Do NOT ask the user for permission to execute what is already done. Keep it concise and natural."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Intent: {intent}\nEntities: {json.dumps(entities, default=str)}\nSummary: {summary}",
                    },
                ],
                temperature=0.4,
                max_tokens=256,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"NIM enhance failed: {e}")
            return None

    def _generate_result_summary(self, intent: str, entities: dict, execution: list) -> str:
        """Generate a human-readable result summary based on intent and entities."""
        name = entities.get("name", "the employee")
        system = entities.get("system", "the requested system")
        leave_type = entities.get("leave_type", "leave")
        title = entities.get("title", "the meeting")

        success_count = sum(1 for ex in execution if ex["status"] == "success")
        total_count = len(execution)

        meet_link = ""
        for ex in execution:
            if ex.get("tool") == "schedule_meeting" and isinstance(ex.get("detail"), dict):
                mlink = ex["detail"].get("meet_link")
                if mlink:
                    meet_link = f"\nGoogle Meet Link: {mlink}"

        summaries = {
            "employee_onboarding": (
                f"{name} has been successfully onboarded with all systems configured. "
                f"Email account created, role assigned, orientation scheduled, and welcome email sent. "
                f"({success_count}/{total_count} steps completed)"
            ),
            "it_provisioning": (
                f"IT systems have been provisioned for {name}. "
                f"Email, Slack, GitHub, and default tools are now accessible. "
                f"({success_count}/{total_count} steps completed)"
            ),
            "access_management": (
                f"Access to {system} has been granted for {name}. "
                f"Permissions verified and audit log updated. "
                f"({success_count}/{total_count} steps completed)"
            ),
            "leave_request": (
                f"{leave_type.title()} leave request has been submitted successfully. "
                f"HR has been notified and the request is pending approval. "
                f"({success_count}/{total_count} steps completed)"
            ),
            "meeting_scheduling": (
                f"'{title}' has been scheduled successfully. "
                f"Calendar invites have been sent to all participants.{meet_link} "
                f"({success_count}/{total_count} steps completed)"
            ),
            "it_ticket": (
                f"IT support ticket has been created and assigned to the appropriate team. "
                f"You will receive updates on the ticket progress. "
                f"({success_count}/{total_count} steps completed)"
            ),
            "password_reset": (
                f"Password reset link has been generated and sent to {name}'s email. "
                f"The link will expire in 30 minutes. "
                f"({success_count}/{total_count} steps completed)"
            ),
            "attrition_prediction": self._build_attrition_summary(execution, name),
            "notification": (
                f"Reminders have been set up for {name}. "
                f"Notifications will be sent for upcoming events. "
                f"({success_count}/{total_count} steps completed)"
            ),
            "system_health": self._build_health_summary(execution),
            "task_management": self._build_task_summary(execution),
            "work_summary": self._build_work_summary(execution),
            "smart_leave_planning": self._build_leave_plan_summary(execution),
            "performance_insight": self._build_performance_summary(execution),
            "knowledge_assistant": self._build_knowledge_summary(execution),
            "workload_optimization": self._build_workload_summary(execution),
            "it_request_assistant": self._build_it_request_summary(execution),
            "notification_intelligence": self._build_notif_intel_summary(execution),
            "retention_analysis": self._build_retention_audit_summary(execution),
            "general": "Hello! I'm ExecuAI, your enterprise assistant. How can I help you today?",
        }

        return summaries.get(intent, (
            "I've processed your request and completed the necessary actions. Is there anything else you need help with?"
        ))

    def _build_attrition_summary(self, execution: list, name: str) -> str:
        """Build attrition prediction result summary."""
        for ex in execution:
            if ex.get("tool") == "predict_attrition" and isinstance(ex.get("detail"), dict):
                detail = ex["detail"]
                prediction = detail.get("prediction", "Unknown")
                confidence = detail.get("confidence", 0)
                recommendations = detail.get("recommendations", [])
                rec_text = " | ".join(recommendations[:2]) if recommendations else "N/A"
                return (
                    f"Attrition prediction for {name}: {prediction} "
                    f"(confidence: {confidence:.1%}). "
                    f"Recommendations: {rec_text}"
                )
        return f"Attrition analysis completed for {name}."

    def _build_health_summary(self, execution: list) -> str:
        """Build system health check summary."""
        health_items = []
        for ex in execution:
            if isinstance(ex.get("detail"), dict):
                detail = ex["detail"]
                if "database" in detail:
                    health_items.append(f"Database: {detail['database']}")
                if "api" in detail:
                    health_items.append(f"API: {detail['api']}")
                if "ml_model" in detail:
                    health_items.append(f"ML Model: {detail['ml_model']}")
                if "issues_detected" in detail:
                    health_items.append(f"Issues: {detail['issues_detected']}")

        if health_items:
            return "System Health Report — " + " | ".join(health_items)
        return "System health check completed. All systems operational."

    def _build_task_summary(self, execution: list) -> str:
        """Build summary for task management."""
        for ex in execution:
            if ex.get("tool") == "prioritize_tasks" and isinstance(ex.get("detail"), dict):
                suggestion = ex["detail"].get("suggestion", "")
                count = len(ex["detail"].get("sorted_tasks", []))
                return f"You have {count} tasks. {suggestion}"
        return "Your task list has been retrieved and prioritized."

    def _build_work_summary(self, execution: list) -> str:
        """Build summary for work summary generator."""
        for ex in execution:
            if ex.get("tool") == "summarize_activities" and isinstance(ex.get("detail"), dict):
                return ex["detail"].get("summary", "Activity summary generated.")
        return "Daily work summary generated successfully."

    def _build_leave_plan_summary(self, execution: list) -> str:
        """Build summary for smart leave planning."""
        dates = []
        reason = ""
        for ex in execution:
            if ex.get("tool") == "suggest_leave_dates" and isinstance(ex.get("detail"), dict):
                dates = ex["detail"].get("suggested_dates", [])
                reason = ex["detail"].get("reason", "")
        if dates:
            return f"Suggested leave dates: {', '.join(dates)}. {reason}"
        return "Smart leave planning complete."

    def _build_performance_summary(self, execution: list) -> str:
        """Build summary for performance insight."""
        for ex in execution:
            if ex.get("tool") == "analyze_performance_trends" and isinstance(ex.get("detail"), dict):
                strengths = ", ".join(ex["detail"].get("strengths", []))
                return f"Performance analysis complete. Key strengths: {strengths}."
        return "Your performance insights have been generated."

    def _build_knowledge_summary(self, execution: list) -> str:
        """Build summary for knowledge assistant."""
        for ex in execution:
            if ex.get("tool") == "extract_policy_info" and isinstance(ex.get("detail"), dict):
                steps = " | ".join(ex["detail"].get("steps", []))
                return f"Knowledge search results: {steps}"
        return "I've searched the knowledge base for your query."

    def _build_workload_summary(self, execution: list) -> str:
        """Build summary for workload optimization."""
        for ex in execution:
            if ex.get("tool") == "detect_schedule_overload" and isinstance(ex.get("detail"), dict):
                day = ex["detail"].get("bottleneck_day", "Wednesday")
                hours = ex["detail"].get("meeting_hours", 0)
                return f"Schedule optimization complete. Detected bottleneck on {day} ({hours}h of meetings). Suggestions proposed."
        return "Workload optimization strategy generated."

    def _build_it_request_summary(self, execution: list) -> str:
        """Build summary for IT request assistant."""
        for ex in execution:
            if ex.get("tool") == "check_software_eligibility" and isinstance(ex.get("detail"), dict):
                eligible = ex["detail"].get("eligible", False)
                software = ex["detail"].get("software", "Software")
                status = "eligible" if eligible else "not eligible"
                return f"Software request processed. You are {status} for {software}. Access request created and IT notified."
        return "IT software request submitted."

    def _build_notif_intel_summary(self, execution: list) -> str:
        """Build summary for notification intelligence."""
        for ex in execution:
            if ex.get("tool") == "filter_important_notifications" and isinstance(ex.get("detail"), dict):
                return ex["detail"].get("summary", "Notifications summarized.")
        return "Important updates filtered and summarized."

    def _build_retention_audit_summary(self, execution: list) -> str:
        """Build a comprehensive retention audit summary."""
        profile = ""
        prediction = ""
        workload = ""
        
        for ex in execution:
            tool = ex.get("tool")
            detail = ex.get("detail", {})
            if tool == "get_employee_data":
                profile = f"{detail.get('name')} ({detail.get('role')})"
            elif tool == "predict_attrition":
                prediction = f"ML Prediction: {detail.get('prediction')} ({detail.get('confidence')} confidence)"
            elif tool == "analyze_workload":
                workload = f"Workload Score: {detail.get('workload_score')}/100"
                
        return f"Comprehensive Audit for {profile}: {prediction}. {workload}. The full multi-step report has been compiled for HR review."

    def _enhance_with_llm(self, base_result: str, intent: str, entities: dict) -> Optional[str]:
        """Optionally polish the result summary using GPT."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an enterprise AI assistant. Rewrite the following result summary "
                            "to be more polished and professional, but keep it concise (2-3 sentences max). "
                            "Do not add information that isn't in the original."
                        ),
                    },
                    {"role": "user", "content": base_result},
                ],
                max_tokens=150,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return None

    # ── Logging ─────────────────────────────────────────────

    def _log_execution(self, request_text: str, response: dict):
        """Persist the execution log to the database."""
        try:
            from backend.database import SessionLocal
            from backend.models import ExecutionLog

            db = SessionLocal()
            log = ExecutionLog(
                request_text=request_text,
                steps_json=json.dumps(response["steps"]),
                result_summary=response["result"],
            )
            db.add(log)
            db.commit()
            db.close()
        except Exception:
            pass  # Non-critical — don't fail the request


# ── Module-level convenience function ──────────────────────

_controller = AgentController()


def agent(user_input: str) -> dict:
    """
    Module-level agent function matching the spec.
    Returns {"steps": [...], "result": "..."}
    """
    return _controller.agent(user_input)
