"""
ML Model Training Script — Employee Attrition Prediction.

== ASSIGNMENT: ML Engineer ==
  - Download the IBM HR Analytics Employee Attrition Dataset.
  - Place it as data/attrition_dataset.csv.
  - Train a Random Forest classifier.
  - Save the trained model as ml/model.pkl.

Run with:
    cd "agentic chatbot"
    .venv\Scripts\python -m ml.train_model
"""
import os
import pickle
import numpy as np

# Uncomment when dataset and dependencies are ready:
# import pandas as pd
# from sklearn.model_selection import train_test_split
# from sklearn.ensemble import RandomForestClassifier
# from sklearn.metrics import accuracy_score, classification_report

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "attrition_dataset.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")


def train():
    """
    Train the attrition prediction model.
    
    Expected columns in CSV (at minimum):
        Age, MonthlyIncome, YearsAtCompany, JobSatisfaction, OverTime, Attrition
    """

    # ── Step 1: Load dataset ─────────────────────────
    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] Dataset not found at {DATA_PATH}")
        print("        Download the IBM HR Analytics dataset and place it there.")
        print("        URL: https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset")
        return

    # TODO: ML Engineer — uncomment and complete the training pipeline below
    #
    # df = pd.read_csv(DATA_PATH)
    #
    # # ── Step 2: Preprocessing ────────────────────────
    # df["OverTime"] = df["OverTime"].map({"Yes": 1, "No": 0})
    # df["Attrition"] = df["Attrition"].map({"Yes": 1, "No": 0})
    #
    # features = ["Age", "MonthlyIncome", "YearsAtCompany", "JobSatisfaction", "OverTime"]
    # X = df[features]
    # y = df["Attrition"]
    #
    # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    #
    # # ── Step 3: Train ────────────────────────────────
    # model = RandomForestClassifier(n_estimators=100, random_state=42)
    # model.fit(X_train, y_train)
    #
    # # ── Step 4: Evaluate ─────────────────────────────
    # y_pred = model.predict(X_test)
    # print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    # print(classification_report(y_test, y_pred, target_names=["Stable", "Likely to Leave"]))
    #
    # # ── Step 5: Save model ───────────────────────────
    # with open(MODEL_PATH, "wb") as f:
    #     pickle.dump(model, f)
    # print(f"Model saved to {MODEL_PATH}")

    print("[INFO] Training pipeline stub executed. Uncomment code above to run real training.")


if __name__ == "__main__":
    train()
