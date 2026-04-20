from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models.models import Assessment
import numpy as np
import pandas as pd
import os, pickle

predict_bp = Blueprint("predict", __name__)

# ── Load model ────────────────────────────────────────────────────────────────
# Prefer the newer, sex-agnostic "diabetes_model.pkl" (7 features, no pregnancies).
# Fall back to the legacy "model.pkl" (8 features) if the new one isn't present.
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
MODEL_CANDIDATES = [
    os.path.join(BACKEND_DIR, "diabetes_model.pkl"),
    os.path.join(BACKEND_DIR, "model.pkl"),
]

model = None
MODEL_PATH_LOADED = None
MODEL_USES_PREGNANCIES = True   # auto-detected below


def _detect_n_features(pipe):
    """Return how many input features the estimator / Pipeline expects."""
    n = getattr(pipe, "n_features_in_", None)
    if n is not None:
        return int(n)
    if hasattr(pipe, "named_steps"):
        for step in pipe.named_steps.values():
            n = getattr(step, "n_features_in_", None)
            if n is not None:
                return int(n)
    if hasattr(pipe, "steps") and pipe.steps:
        n = getattr(pipe.steps[0][1], "n_features_in_", None)
        if n is not None:
            return int(n)
    return None


for candidate in MODEL_CANDIDATES:
    if os.path.exists(candidate):
        try:
            with open(candidate, "rb") as f:
                model = pickle.load(f)
            MODEL_PATH_LOADED = candidate

            n_features = _detect_n_features(model)
            if n_features is not None:
                MODEL_USES_PREGNANCIES = (n_features == 8)
            else:
                MODEL_USES_PREGNANCIES = "diabetes_model" not in os.path.basename(candidate)

            fmt = "8-feature (with pregnancies)" if MODEL_USES_PREGNANCIES \
                  else "7-feature (sex-agnostic, no pregnancies)"
            print(f"[GlucoSense] ✓ Loaded {os.path.basename(candidate)}  — {fmt}")
            break
        except Exception as e:
            print(f"[GlucoSense] ✗ Could not load {candidate}: {e}")


# ── Feature definitions ──────────────────────────────────────────────────────
FEATURE_NAMES_FULL = [
    "pregnancies", "glucose", "blood_pressure", "skin_thickness",
    "insulin", "bmi", "diabetes_pedigree", "age",
]
FEATURE_NAMES_NO_PREG = [
    "glucose", "blood_pressure", "skin_thickness", "insulin",
    "bmi", "diabetes_pedigree", "age",
]

FEATURE_MEDIANS = {
    "pregnancies":       3.0,
    "glucose":         117.0,
    "blood_pressure":   72.0,
    "skin_thickness":   23.0,
    "insulin":          30.5,
    "bmi":              32.0,
    "diabetes_pedigree": 0.3725,
    "age":              29.0,
}

# ── Fallback (used ONLY when no .pkl is present) ─────────────────────────────
FEATURE_MEANS_FULL      = np.array([3.845, 121.69, 72.41, 29.15, 140.67, 32.46, 0.4719, 33.24])
FEATURE_STDS_FULL       = np.array([3.370,  30.44, 12.10,  9.94,  86.38,  6.92, 0.3313, 11.76])
FALLBACK_COEF_FULL      = np.array([0.125,  1.083, -0.089, 0.052, 0.168, 0.446, 0.403, 0.334])
FALLBACK_INTERCEPT_FULL = -0.547

FEATURE_MEANS_NO_PREG      = FEATURE_MEANS_FULL[1:]
FEATURE_STDS_NO_PREG       = FEATURE_STDS_FULL[1:]
FALLBACK_COEF_NO_PREG      = FALLBACK_COEF_FULL[1:]
FALLBACK_INTERCEPT_NO_PREG = -0.42


def _impute(values, names):
    """Replace physiologically impossible zero values with dataset medians."""
    zero_cols = {"glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"}
    out = list(values)
    for i, name in enumerate(names):
        if name in zero_cols and out[i] == 0.0:
            out[i] = FEATURE_MEDIANS[name]
    return out


def predict_probability(features_dict):
    names  = FEATURE_NAMES_FULL if MODEL_USES_PREGNANCIES else FEATURE_NAMES_NO_PREG
    values = [float(features_dict.get(n, 0)) for n in names]
    values = _impute(values, names)

    if model is not None:
        try:
            df = pd.DataFrame([values], columns=names)
            return float(model.predict_proba(df)[0][1])
        except Exception:
            try:
                arr = np.array(values).reshape(1, -1)
                return float(model.predict_proba(arr)[0][1])
            except Exception as e:
                print(f"[GlucoSense] Model prediction failed: {e} — using fallback")

    if MODEL_USES_PREGNANCIES:
        x = (np.array(values) - FEATURE_MEANS_FULL) / FEATURE_STDS_FULL
        z = float(np.dot(FALLBACK_COEF_FULL, x)) + FALLBACK_INTERCEPT_FULL
    else:
        x = (np.array(values) - FEATURE_MEANS_NO_PREG) / FEATURE_STDS_NO_PREG
        z = float(np.dot(FALLBACK_COEF_NO_PREG, x)) + FALLBACK_INTERCEPT_NO_PREG
    return float(1 / (1 + np.exp(-z)))


def risk_label(prob):
    if prob < 0.30:
        return "Low"
    elif prob < 0.60:
        return "Moderate"
    return "High"


@predict_bp.route("/", methods=["POST"])
@jwt_required()
def predict():
    data = request.get_json() or {}

    # The 7 biomarkers are ALWAYS required.
    for f in FEATURE_NAMES_NO_PREG:
        if data.get(f) is None:
            return jsonify({"error": f"{f} is required"}), 400

    gender = data.get("gender")

    # Pregnancies: optional. For males (or if omitted) default to 0.
    raw_preg = data.get("pregnancies")
    if gender == "Male" or raw_preg is None or raw_preg == "":
        pregnancies = 0.0
    else:
        try:
            pregnancies = float(raw_preg)
        except (TypeError, ValueError):
            pregnancies = 0.0

    features_dict = {
        "pregnancies":       pregnancies,
        "glucose":           float(data["glucose"]),
        "blood_pressure":    float(data["blood_pressure"]),
        "skin_thickness":    float(data["skin_thickness"]),
        "insulin":           float(data["insulin"]),
        "bmi":               float(data["bmi"]),
        "diabetes_pedigree": float(data["diabetes_pedigree"]),
        "age":               float(data["age"]),
    }

    prob = predict_probability(features_dict)
    risk = risk_label(prob)

    assessment = Assessment(
        user_id            = int(get_jwt_identity()),
        pregnancies        = features_dict["pregnancies"],
        glucose            = features_dict["glucose"],
        blood_pressure     = features_dict["blood_pressure"],
        skin_thickness     = features_dict["skin_thickness"],
        insulin            = features_dict["insulin"],
        bmi                = features_dict["bmi"],
        diabetes_pedigree  = features_dict["diabetes_pedigree"],
        age_input          = features_dict["age"],
        probability        = round(prob, 4),
        risk_level         = risk,
    )
    db.session.add(assessment)
    db.session.commit()

    return jsonify({
        "probability":   round(prob * 100, 1),
        "risk_level":    risk,
        "assessment_id": assessment.id,
        "factors": {
            "glucose":           features_dict["glucose"],
            "bmi":               features_dict["bmi"],
            "age":               features_dict["age"],
            "blood_pressure":    features_dict["blood_pressure"],
            "insulin":           features_dict["insulin"],
            "diabetes_pedigree": features_dict["diabetes_pedigree"],
        },
    }), 200