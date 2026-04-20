# 🩺 GlucoSense — AI Diabetes Intelligence Platform

A full-stack diabetes risk prediction web application built with:
- **Backend**: Python / Flask REST API with JWT authentication
- **Frontend**: Vanilla HTML/CSS/JS (no framework — runs in any browser)
- **AI Model**: Scikit-learn Logistic Regression trained on the Pima Indians Diabetes Dataset

---

## 📁 Project Structure

```
glucosense/
├── backend/
│   ├── app.py                  # Flask app factory
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variables template
│   ├── model.pkl               # ← Place your model here
│   ├── models/
│   │   └── models.py           # SQLAlchemy DB models (User, Assessment, Report)
│   └── routes/
│       ├── auth.py             # Register, Login, Profile, Change Password
│       ├── predict.py          # Risk prediction + history
│       ├── records.py          # Assessment records + stats
│       └── reports.py          # File upload / download / delete
│
└── frontend/
    ├── assets/
    │   └── css/
    │       └── global.css      # Full design system (Navy/Gold luxury aesthetic)
    ├── components/
    │   └── api.js              # API wrapper, Auth helpers, Toast, Sidebar renderer
    └── pages/
        ├── index.html          # Animated splash screen
        ├── login.html          # Login + Register (two-tab layout)
        ├── dashboard.html      # Overview stats, gauge, trend chart, activity feed
        ├── assessment.html     # Multi-step risk assessment form + results
        ├── records.html        # Full assessment history with filters + pagination
        ├── reports.html        # Upload / download medical documents
        ├── tips.html           # Health tips + biomarker reference table
        └── profile.html        # Account settings + change password
```

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd glucosense/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your own SECRET_KEY values

# Place your model.pkl in the backend/ directory
# (The app falls back to embedded coefficients if no model.pkl is found)

# Run the server
python app.py
# → Flask API running on http://localhost:5000
```

### 2. Frontend Setup

No build step required — open directly in a browser:

```bash
# Option A: VS Code Live Server (recommended)
# Right-click frontend/pages/index.html → "Open with Live Server"

# Option B: Python simple server
cd glucosense/frontend
python -m http.server 3000
# → Open http://localhost:3000/pages/index.html
```

### 3. Ensure CORS is configured

The backend allows requests from `http://localhost:3000` and `http://127.0.0.1:5500` by default.
Edit the `CORS(...)` call in `app.py` to add your own origin if needed.

---

## 🔑 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Sign in, returns JWT |
| GET  | `/api/auth/me` | Get current user (JWT required) |
| PUT  | `/api/auth/profile` | Update profile |
| POST | `/api/auth/change-password` | Change password |

### Prediction
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict/` | Run assessment, save to DB |
| GET  | `/api/predict/history` | Paginated assessment history |
| GET  | `/api/predict/:id` | Single assessment detail |
| DELETE | `/api/predict/:id` | Delete assessment |

### Records & Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/records/` | All records (paginated) |
| GET  | `/api/records/stats` | Aggregate statistics |
| POST | `/api/reports/upload` | Upload a file (multipart) |
| GET  | `/api/reports/` | List all uploaded files |
| GET  | `/api/reports/download/:id` | Download a file |
| DELETE | `/api/reports/:id` | Delete a file |

---

## 🎨 Design System

- **Aesthetic**: Refined Medical Luxury — Deep Navy + Champagne Gold
- **Display font**: Cormorant Garamond (elegant, editorial)
- **Body font**: DM Sans (clean, modern, readable)
- **Theme tokens**: All in `global.css` as CSS custom properties
- **Components**: Cards, buttons, form inputs, badges, toasts, modals, tables — all pre-styled

---

## 🧠 AI Model

The prediction engine loads `model.pkl` (scikit-learn LogisticRegression) from the backend directory.

**Input features (in order):**
1. Pregnancies
2. Plasma Glucose Concentration (mg/dL)
3. Diastolic Blood Pressure (mmHg)
4. Triceps Skin Fold Thickness (mm)
5. 2-Hour Serum Insulin (μU/mL)
6. BMI (kg/m²)
7. Diabetes Pedigree Function
8. Age (years)

**Output:**
- `risk_score`: 0–100 probability
- `risk_level`: Low / Moderate / High
- `prediction`: 0 (no diabetes) or 1 (diabetes risk)
- `recommendations`: personalised clinical advice list

---

## 🛡️ Security Notes

- JWT tokens expire after 7 days
- Passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2-SHA256)
- File uploads are restricted to safe extensions and 16MB max
- All prediction and file endpoints require a valid JWT

---

## 📄 License

For educational and personal use. Always consult a qualified healthcare professional — this app does not provide medical advice.
