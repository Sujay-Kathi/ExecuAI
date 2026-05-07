"""
Agent Controller — the "brain" of the agentic system.
Follows the  Understand → Plan → Execute → Respond  loop.

== ASSIGNMENT: AI Engineer ==
  - Replace the stub logic with actual LLM calls (OpenAI API).
  - Use the TOOL_REGISTRY from agent/tools.py to execute planned steps.
  - Log every step in the execution_log for UI transparency.
"""
from agent.tools import TOOL_REGISTRY


class AgentController:
    """
    Core agent that processes user requests through:
      1. Understand — parse user intent
      2. Plan     — break into ordered steps
      3. Execute  — call tools for each step
      4. Respond  — compile final answer + execution log
    """

    def __init__(self):
        self.tools = TOOL_REGISTRY

    # ── Public API ───────────────────────────────────

    def process_request(self, user_request: str) -> dict:
        """Entry-point called by the /api/chat route."""
        intent = self._understand(user_request)
        plan = self._plan(intent)
        results = self._execute(plan)
        return self._respond(results)

    # ── Private steps ────────────────────────────────

    def _understand(self, text: str) -> dict:
        """
        Step 1 — Understand user intent.
        TODO: AI Engineer — call OpenAI to classify intent & extract entities.
        """
        return {"raw_text": text, "intent": "general", "entities": {}}

    def _plan(self, intent: dict) -> list:
        """
        Step 2 — Break intent into ordered tool calls.
        TODO: AI Engineer — use LLM to generate a plan based on intent.
        """
        return [
            {"step": 1, "action": "Task identified", "tool": None},
            {"step": 2, "action": "Steps planned", "tool": None},
            {"step": 3, "action": "Actions executed", "tool": None},
            {"step": 4, "action": "Result generated", "tool": None},
        ]

    def _execute(self, plan: list) -> list:
        """
        Step 3 — Execute each step, calling tools where needed.
        TODO: AI Engineer — invoke tools from TOOL_REGISTRY per plan.
        """
        executed = []
        for step in plan:
            tool_name = step.get("tool")
            if tool_name and tool_name in self.tools:
                # result = self.tools[tool_name](**step.get("args", {}))
                pass
            executed.append(f"✔ {step['action']}")
        return executed

    def _respond(self, executed_steps: list) -> dict:
        """Step 4 — Compile final response."""
        return {
            "status": "success",
            "message": "Request processed successfully.",
            "steps_executed": executed_steps,
        }
