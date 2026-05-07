# 🏢 Intelligent Enterprise Assistant

> An Agentic AI System for Autonomous Workflow Automation

---

## 📁 Project Structure

```
agentic-chatbot/
├── backend/                       # FastAPI backend
│   ├── main.py                    # App entry-point — integrates all modules
│   ├── config.py                  # Env vars & app settings
│   ├── database.py                # SQLAlchemy engine & session
│   ├── models.py                  # All ORM models (shared)
│   ├── schemas.py                 # Pydantic schemas (shared)
│   │
│   ├── employee/                  # 👨‍💻 Employee module
│   │   ├── __init__.py
│   │   ├── routes.py              # /api/employee/* endpoints
│   │   └── schemas.py             # Employee-specific schemas
│   │
│   ├── hr/                        # 👩‍💼 HR module
│   │   ├── __init__.py
│   │   ├── routes.py              # /api/hr/* endpoints
│   │   └── schemas.py             # HR-specific schemas
│   │
│   ├── it_admin/                  # 🛠️ IT Admin module
│   │   ├── __init__.py
│   │   ├── routes.py              # /api/it/* endpoints
│   │   └── schemas.py             # IT-specific schemas
│   │
│   ├── routes_chat.py             # /api/chat/* (shared — agent)
│   ├── routes_ml.py               # /api/ml/*   (shared — predictions)
│   ├── routes_employees.py        # Legacy CRUD (backward compat)
│   ├── routes_leaves.py           # Legacy CRUD (backward compat)
│   └── routes_meetings.py         # Legacy CRUD (backward compat)
│
├── agent/                         # 🤖 AI Agent logic
│   ├── agent.py                   # AgentController — Understand→Plan→Execute→Respond
│   └── tools.py                   # Tool registry (callable functions)
│
├── ml/                            # 📊 Machine Learning
│   ├── train_model.py             # Training script (Random Forest)
│   ├── predictor.py               # Prediction utility class
│   └── model.pkl                  # Trained model (generated, not committed)
│
├── data/                          # Datasets & database
│   ├── README.md                  # Dataset download instructions
│   ├── attrition_dataset.csv      # IBM HR dataset (download separately)
│   └── enterprise.db              # SQLite DB (auto-created on startup)
│
├── frontend/                      # 🎨 React + Vite frontend
│   ├── src/                       # React source code
│   ├── public/                    # Static assets
│   ├── package.json               # Node dependencies
│   └── vite.config.js             # Vite configuration
│
├── .env.example                   # Environment variable template
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
└── context.txt                    # Project specification document
```

---

## 🚀 Quick Start

### 1. Clone & activate virtual environment

```bash
git clone <repo-url>
cd "agentic chatbot"

# Activate existing venv (Windows):
.venv\Scripts\activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env
# Edit .env → add your OPENAI_API_KEY
```

### 4. Start the backend

```bash
# From project root:
uvicorn backend.main:app --reload
# API runs at http://127.0.0.1:8000
# Docs at    http://127.0.0.1:8000/docs
```

### 5. Start the frontend

```bash
cd frontend
npm install   # (already done)
npm run dev
# UI runs at http://localhost:5173
```

---

## 👥 Team Roles & Assignments

### 🤖 AI Engineer — `agent/`
| File | Task |
|------|------|
| `agent/agent.py` | Implement LLM calls in `_understand()` and `_plan()` using OpenAI API |
| `agent/tools.py` | Wire tool functions to actual backend endpoints / external APIs |
| **Branch:** `feature/agent-logic` | |

---

### 🔧 Backend Developer — `backend/` (core)
| File | Task |
|------|------|
| `backend/models.py` | Extend DB models if needed |
| `backend/schemas.py` | Keep schemas in sync with models |
| `backend/database.py` | Optimise DB queries if needed |
| `backend/main.py` | Integrate new routers as modules grow |
| **Branch:** `feature/backend-api` | |

---

### 👨‍💻 Feature Dev — Employee Module (`backend/employee/`)
| File | Task |
|------|------|
| `backend/employee/routes.py` | Apply leave, schedule meetings, view profile, request access |
| `backend/employee/schemas.py` | Add employee-specific request/response models |
| **Branch:** `feature/employee-module` | |

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/employee/profile/{id}` | View own profile |
| `POST` | `/api/employee/leave` | Apply for leave |
| `GET` | `/api/employee/leave/{id}` | View own leave history |
| `POST` | `/api/employee/meeting` | Schedule a meeting |
| `GET` | `/api/employee/meetings/{id}` | View own meetings |
| `GET` | `/api/employee/info/{id}` | Get salary, role, policies |

---

### 👩‍💼 Feature Dev — HR Module (`backend/hr/`)
| File | Task |
|------|------|
| `backend/hr/routes.py` | Onboard employees, approve leave, workforce insights |
| `backend/hr/schemas.py` | Add HR-specific request/response models |
| **Branch:** `feature/hr-module` | |

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/hr/onboard` | Full onboarding workflow |
| `GET` | `/api/hr/employees` | List all employees |
| `GET` | `/api/hr/leaves` | List all leave requests |
| `PATCH` | `/api/hr/leaves/{id}` | Approve / reject leave |
| `GET` | `/api/hr/insights` | Workforce analytics |

---

### 🛠️ Feature Dev — IT Admin Module (`backend/it_admin/`)
| File | Task |
|------|------|
| `backend/it_admin/routes.py` | Manage access, handle system requests, monitor health |
| `backend/it_admin/schemas.py` | Add IT-specific request/response models |
| **Branch:** `feature/it-module` | |

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/it/access` | Request system access |
| `GET` | `/api/it/access` | List access requests |
| `PATCH` | `/api/it/access/{id}` | Grant / deny access |
| `POST` | `/api/it/system-request` | Submit IT request |
| `GET` | `/api/it/health` | System health status |

---

### 🎨 Frontend Developer — `frontend/`
| File | Task |
|------|------|
| `frontend/src/` | Build Chat Panel, Execution Log Panel, Dashboard |
| Connect to API | Use `http://127.0.0.1:8000/api/` endpoints |
| **Branch:** `feature/frontend-ui` | |

---

### 📊 ML Engineer — `ml/`
| File | Task |
|------|------|
| `data/` | Download IBM HR Attrition dataset → `data/attrition_dataset.csv` |
| `ml/train_model.py` | Uncomment training pipeline, train model, save `model.pkl` |
| `ml/predictor.py` | Verify feature order matches training |
| `backend/routes_ml.py` | Replace stub with real `predictor.predict()` call |
| **Branch:** `feature/ml-model` | |

---

### 🔗 Integration Lead
| Task |
|------|
| Merge all feature branches into `dev` |
| End-to-end testing of the full workflow |
| Wire agent tools to real external APIs |
| **Branch:** `dev` → `main` |

---

## 🌿 Git Workflow

```
main              ← final, stable code
  └── dev         ← integration branch
       ├── feature/agent-logic
       ├── feature/backend-api
       ├── feature/employee-module
       ├── feature/hr-module
       ├── feature/it-module
       ├── feature/frontend-ui
       └── feature/ml-model
```

**Rules:**
1. Never push directly to `main`.
2. Create your feature branch from `main`.
3. Open a PR to `dev` when your feature is ready.
4. Integration Lead merges `dev` → `main` after testing.

---

## 📡 Full API Reference

### Shared Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/chat/` | Send message to agent |
| `POST` | `/api/ml/predict-attrition` | Predict employee attrition |

### Employee Endpoints (`/api/employee/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/employee/profile/{id}` | View profile |
| `POST` | `/api/employee/leave` | Apply for leave |
| `GET` | `/api/employee/leave/{id}` | View leave history |
| `POST` | `/api/employee/meeting` | Schedule meeting |
| `GET` | `/api/employee/meetings/{id}` | View meetings |
| `GET` | `/api/employee/info/{id}` | Get info |

### HR Endpoints (`/api/hr/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/hr/onboard` | Onboard employee |
| `GET` | `/api/hr/employees` | List all employees |
| `GET` | `/api/hr/leaves` | List leave requests |
| `PATCH` | `/api/hr/leaves/{id}` | Approve/reject leave |
| `GET` | `/api/hr/insights` | Workforce analytics |

### IT Admin Endpoints (`/api/it/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/it/access` | Request access |
| `GET` | `/api/it/access` | List requests |
| `PATCH` | `/api/it/access/{id}` | Grant/deny access |
| `POST` | `/api/it/system-request` | Submit IT request |
| `GET` | `/api/it/health` | System health |

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenAI API |
| Backend | Python, FastAPI, SQLAlchemy |
| Frontend | React, Vite |
| Database | SQLite |
| ML | scikit-learn (Random Forest) |
| Version Control | GitHub |

---
#   E x e c u A I  
 