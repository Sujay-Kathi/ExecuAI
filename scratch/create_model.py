import pickle
import os

# Create a simple "model" which is just a coefficients dict for our simulation
model = {
    "salary_weight": -0.00001,  # higher salary = lower risk
    "satisfaction_weight": -0.2, # higher satisfaction = lower risk
    "workload_weight": 0.005,    # higher workload = higher risk
    "threshold": 0.5
}

# Ensure directory exists
model_dir = os.path.join(os.getcwd(), "models")
if not os.path.exists(model_dir):
    os.makedirs(model_dir)

model_path = os.path.join(model_dir, "attrition_model.pkl")
with open(model_path, "wb") as f:
    pickle.dump(model, f)

print(f"Model saved to {model_path}")
