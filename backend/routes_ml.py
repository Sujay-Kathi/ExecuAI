"""
ML prediction routes — employee attrition prediction.

== ASSIGNMENT: ML Engineer ==
  - Train the model (ml/train_model.py) and place model.pkl in ml/.
  - This route loads the model and serves predictions.
"""
from fastapi import APIRouter, HTTPException
from backend.schemas import AttritionInput, AttritionResult
import pickle
import os
import numpy as np

router = APIRouter(prefix="/api/ml", tags=["ML Predictions"])

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "model.pkl")


def load_model():
    """Load the trained .pkl model. Returns None if not found."""
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


@router.post("/predict-attrition", response_model=AttritionResult)
def predict_attrition(payload: AttritionInput):
    """
    Predict whether an employee is likely to leave.
    Uses the Random Forest model trained by the ML Engineer.
    """
    model = load_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="ML model not found. Run ml/train_model.py first."
        )

    # TODO: ML Engineer — replace this stub with actual model.predict() call
    # Example feature vector (must match training order):
    # features = np.array([[payload.age, payload.monthly_income,
    #                        payload.years_at_company, payload.job_satisfaction,
    #                        int(payload.overtime)]])
    # prediction = model.predict(features)
    # proba = model.predict_proba(features)

    return AttritionResult(
        prediction="Stable",
        confidence=0.0
    )
