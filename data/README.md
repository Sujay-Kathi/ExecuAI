# Data Directory

Place datasets here.

## Required Files

- **attrition_dataset.csv** — IBM HR Analytics Employee Attrition Dataset
  - Download from: https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset
  - Used by: `ml/train_model.py`

## Notes
- The SQLite database (`enterprise.db`) will be auto-created here on first backend startup.
- Do NOT commit large CSVs to Git — add them to `.gitignore`.
