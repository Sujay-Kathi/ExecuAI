"""
Agent Controller — the "brain" of the agentic system.
Follows the  Understand → Plan → Execute → Respond  loop.
"""
import json
from openai import OpenAI
from backend.config import OPENAI_API_KEY
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
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY and OPENAI_API_KEY != "your-openai-api-key-here" else None

    def process_request(self, user_request: str) -> dict:
        """Entry-point called by the /api/chat route."""
        intent = self._understand(user_request)
        plan = self._plan(intent)
        results = self._execute(plan)
        return self._respond(results)

    def _understand(self, text: str) -> dict:
        """Step 1 — Understand user intent."""
        if not self.client:
            return {"raw_text": text, "intent": "mock_intent (no API key)", "entities": {}}
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an enterprise AI assistant intent classifier. Classify the user's intent based on their request. Output JSON with 'intent' and 'entities' (key-value pairs)."
                    },
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return {
                "raw_text": text,
                "intent": data.get("intent", "general"),
                "entities": data.get("entities", {})
            }
        except Exception as e:
            return {"raw_text": text, "intent": "error", "entities": {}, "error": str(e)}

    def _plan(self, intent: dict) -> list:
        """Step 2 — Break intent into ordered tool calls."""
        if not self.client or "mock_intent" in intent.get("intent", "") or intent.get("intent") == "error":
            return [
                {"step": 1, "action": "Task identified", "tool": None, "args": {}},
                {"step": 2, "action": "Steps planned", "tool": None, "args": {}},
                {"step": 3, "action": "Actions executed", "tool": None, "args": {}},
                {"step": 4, "action": "Result generated", "tool": None, "args": {}},
            ]
        
        try:
            prompt = f"Given the intent '{intent['intent']}' and entities {intent['entities']}, generate an execution plan using available tools: {list(self.tools.keys())}. Output JSON with a 'plan' array, where each item has 'step', 'action' (description), 'tool' (tool name or null), and 'args' (dictionary of args mapping to tool parameters)."
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a planning AI. Always output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("plan", [])
        except Exception as e:
            return [{"step": 1, "action": f"Error planning: {str(e)}", "tool": None, "args": {}}]

    def _execute(self, plan: list) -> list:
        """Step 3 — Execute each step, calling tools where needed."""
        executed = []
        for step in plan:
            tool_name = step.get("tool")
            args = step.get("args", {})
            if tool_name and tool_name in self.tools:
                try:
                    result = self.tools[tool_name](**args)
                    executed.append(f"✔ Executed {tool_name}: {result}")
                except Exception as e:
                    executed.append(f"❌ Failed {tool_name}: {str(e)}")
            else:
                executed.append(f"✔ {step.get('action', 'Unknown action')}")
        return executed

    def _respond(self, executed_steps: list) -> dict:
        """Step 4 — Compile final response."""
        return {
            "status": "success",
            "message": "Request processed successfully.",
            "steps_executed": executed_steps,
        }
