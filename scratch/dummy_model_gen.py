import os
import pickle
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# Generate dummy data
# Age, MonthlyIncome, YearsAtCompany, JobSatisfaction, OverTime
X_train = np.random.rand(100, 5)
X_train[:, 0] = X_train[:, 0] * 40 + 20 # Age
X_train[:, 1] = X_train[:, 1] * 10000 + 2000 # MonthlyIncome
X_train[:, 2] = X_train[:, 2] * 20 # YearsAtCompany
X_train[:, 3] = np.random.randint(1, 5, 100) # JobSatisfaction
X_train[:, 4] = np.random.randint(0, 2, 100) # Overtime
y_train = np.random.randint(0, 2, 100) # 0 or 1

# Train dummy model
model = RandomForestClassifier(n_estimators=10, random_state=42)
model.fit(X_train, y_train)

# Save
model_path = os.path.join(os.path.dirname(__file__), "..", "ml", "model.pkl")
with open(model_path, "wb") as f:
    pickle.dump(model, f)
print("Dummy model saved to", model_path)
