"""
ML Prediction utility — loads the trained model and predicts.

== ASSIGNMENT: ML Engineer ==
  - This module is imported by backend/routes_ml.py.
  - Ensure feature order matches training.
"""
import os
import pickle
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")


class AttritionPredictor:
    def __init__(self):
        self.model = None
        self._load()

    def _load(self):
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)

    def predict(self, age: int, monthly_income: float, years_at_company: int,
                job_satisfaction: int, overtime: bool) -> dict:
        """
        Returns dict with 'prediction' and 'confidence'.
        """
        if self.model is None:
            return {"prediction": "Model not loaded", "confidence": 0.0}

        features = np.array([[age, monthly_income, years_at_company,
                               job_satisfaction, int(overtime)]])

        pred = self.model.predict(features)[0]
        proba = self.model.predict_proba(features)[0]

        return {
            "prediction": "Likely to Leave" if pred == 1 else "Stable",
            "confidence": round(float(max(proba)), 4),
        }
