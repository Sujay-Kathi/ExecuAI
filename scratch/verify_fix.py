
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.intent import extract_entities

texts = [
    "Schedule a meeting with Rahul about the project",
    "Invite Rahul to a meeting regarding the roadmap",
    "Book a meeting for Sarah on Friday",
    "Meeting with John regarding the budget"
]

for t in texts:
    ents = extract_entities(t, "meeting_scheduling")
    print(f"Text: {t}")
    print(f"Entities: {ents}")
    print("-" * 20)
