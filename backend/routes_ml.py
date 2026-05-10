"""
ML prediction routes — employee attrition prediction.

== ASSIGNMENT: ML Engineer ==
  - Train the model (ml/train_model.py) and place model.pkl in ml/.
  - This route loads the model and serves predictions.
"""
from fastapi import APIRouter, HTTPException
from backend.schemas import AttritionInput, AttritionResult
from ml.predictor import AttritionPredictor

router = APIRouter(prefix="/api/ml", tags=["ML Predictions"])


@router.post("/predict-attrition", response_model=AttritionResult)
def predict_attrition(payload: AttritionInput):
    """
    Predict whether an employee is likely to leave.
    Uses the Random Forest model.
    """
    predictor = AttritionPredictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=503,
            detail="ML model not found. Run ml/train_model.py first."
        )

    result = predictor.predict(
        age=payload.age,
        monthly_income=payload.monthly_income,
        years_at_company=payload.years_at_company,
        job_satisfaction=payload.job_satisfaction,
        overtime=payload.overtime
    )

    return AttritionResult(
        prediction=result["prediction"],
        confidence=result["confidence"]
    )
