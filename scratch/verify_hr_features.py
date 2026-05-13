import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from agent.agent import agent

def test_feature(trigger):
    print(f"--- Trigger: {trigger} ---")
    response = agent(trigger)
    print(json.dumps(response, indent=2))
    print("\n")

if __name__ == "__main__":
    test_feature("Onboard Rahul") # Should skip welcome email (no role)
    test_feature("Onboard Rahul as Senior Engineer") # Should send welcome email
    test_feature("Approve leave for Rahul")
