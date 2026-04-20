from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models.models import KidneyAssessment
import numpy as np
import pandas as pd
import os, pickle

kidney_bp = Blueprint("kidney", __name__)

# ── Load model ────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kidney_model.pkl")
kidney_model = None

if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, "rb") as f:
            kidney_model = pickle.load(f)
        print("[GlucoSense] ✓ Loaded kidney_model.pkl")
    except Exception as e:
        print(f"[GlucoSense] ✗ Could not load kidney_model.pkl: {e}")

# ── Feature definitions ───────────────────────────────────────────────────────
FEATURE_NAMES = [
    "age", "blood_pressure", "blood_glucose_random", "blood_urea",
    "serum_creatinine", "sodium", "potassium", "haemoglobin",
    "packed_cell_volume", "white_blood_cell_count", "red_blood_cell_count",
    "hypertension", "diabetes_mellitus", "pedal_edema", "anemia",
]

# ── Fallback: logistic regression on scaled features ─────────────────────────
# Derived from UCI CKD dataset statistics (used only when kidney_model.pkl is missing)
# Feature order matches FEATURE_NAMES above.

FEATURE_MEDIANS = {
    "age":                    49.0,
    "blood_pressure":         76.0,
    "blood_glucose_random":   121.0,
    "blood_urea":             44.0,
    "serum_creatinine":       1.1,
    "sodium":                 137.0,
    "potassium":              4.6,
    "haemoglobin":            12.5,
    "packed_cell_volume":     38.0,
    "white_blood_cell_count": 8000.0,
    "red_blood_cell_count":   4.5,
    "hypertension":           0.0,
    "diabetes_mellitus":      0.0,
    "pedal_edema":            0.0,
    "anemia":                 0.0,
}

FEATURE_MEANS = np.array([
    49.0,  76.2,  128.8,  58.0,   3.79,  136.2,
     4.70,  12.0,   35.6, 8700.0,   4.08,
     0.50,   0.32,   0.40,   0.35,
])

FEATURE_STDS = np.array([
    17.0,  17.0,   74.0,   55.0,   5.5,   12.0,
     1.7,   2.8,    9.0, 3000.0,    0.9,
     0.50,   0.47,   0.49,   0.48,
])

# Approximate LR coefficients on standardised features (CKD = 1)
FALLBACK_COEF = np.array([
    0.25,   # age
    0.15,   # blood_pressure
    0.25,   # blood_glucose_random
    0.55,   # blood_urea
    1.10,   # serum_creatinine  ← strongest predictor
   -0.25,   # sodium
    0.15,   # potassium
   -0.90,   # haemoglobin
   -0.70,   # packed_cell_volume
    0.12,   # white_blood_cell_count
   -0.55,   # red_blood_cell_count
    0.75,   # hypertension
    0.35,   # diabetes_mellitus
    0.90,   # pedal_edema
    0.65,   # anemia
])
FALLBACK_INTERCEPT = 0.30


def _impute_features(raw: dict) -> list:
    """Replace missing / zero numeric values with dataset medians."""
    result = []
    for name in FEATURE_NAMES:
        val = float(raw.get(name, 0))
        # For binary flags, keep as-is (0 = no, 1 = yes)
        if name in ("hypertension", "diabetes_mellitus", "pedal_edema", "anemia"):
            result.append(val)
        elif val == 0.0:
            result.append(FEATURE_MEDIANS[name])
        else:
            result.append(val)
    return result


def predict_ckd_probability(features: list) -> float:
    if kidney_model is not None:
        try:
            df = pd.DataFrame([features], columns=FEATURE_NAMES)
            return float(kidney_model.predict_proba(df)[0][1])
        except Exception as e:
            print(f"[GlucoSense] Kidney model prediction failed: {e} — using fallback")

    # Fallback: manual scale + sigmoid
    x = (np.array(features) - FEATURE_MEANS) / FEATURE_STDS
    z = float(np.dot(FALLBACK_COEF, x)) + FALLBACK_INTERCEPT
    return float(1 / (1 + np.exp(-z)))


def risk_label(prob: float) -> str:
    if prob < 0.30:
        return "Low"
    elif prob < 0.60:
        return "Moderate"
    return "High"


# ── Prediction endpoint ───────────────────────────────────────────────────────
@kidney_bp.route("/predict", methods=["POST"])
@jwt_required()
def predict():
    data = request.get_json()
    required = FEATURE_NAMES
    for f in required:
        if data.get(f) is None:
            return jsonify({"error": f"{f} is required"}), 400

    raw_features = {name: float(data[name]) for name in FEATURE_NAMES}
    features = _impute_features(raw_features)

    prob = predict_ckd_probability(features)
    risk = risk_label(prob)

    assessment = KidneyAssessment(
        user_id               = int(get_jwt_identity()),
        age_input             = features[0],
        blood_pressure        = features[1],
        blood_glucose_random  = features[2],
        blood_urea            = features[3],
        serum_creatinine      = features[4],
        sodium                = features[5],
        potassium             = features[6],
        haemoglobin           = features[7],
        packed_cell_volume    = features[8],
        white_blood_cell_count= features[9],
        red_blood_cell_count  = features[10],
        hypertension          = int(features[11]),
        diabetes_mellitus     = int(features[12]),
        pedal_edema           = int(features[13]),
        anemia                = int(features[14]),
        probability           = round(prob, 4),
        risk_level            = risk,
    )
    db.session.add(assessment)
    db.session.commit()

    return jsonify({
        "probability":   round(prob * 100, 1),
        "risk_level":    risk,
        "assessment_id": assessment.id,
        "factors": {
            "serum_creatinine":      features[4],
            "blood_urea":            features[3],
            "haemoglobin":           features[7],
            "packed_cell_volume":    features[8],
            "blood_glucose_random":  features[2],
            "red_blood_cell_count":  features[10],
        },
    }), 200


# ── Records endpoints ─────────────────────────────────────────────────────────
@kidney_bp.route("/records", methods=["GET"])
@jwt_required()
def records():
    user_id = int(get_jwt_identity())
    page    = int(request.args.get("page", 1))
    per     = int(request.args.get("per_page", 10))

    pagination = (
        KidneyAssessment.query
        .filter_by(user_id=user_id)
        .order_by(KidneyAssessment.created_at.desc())
        .paginate(page=page, per_page=per, error_out=False)
    )
    return jsonify({
        "records":    [r.to_dict() for r in pagination.items],
        "total":      pagination.total,
        "pages":      pagination.pages,
        "current_page": page,
    }), 200


@kidney_bp.route("/records/stats", methods=["GET"])
@jwt_required()
def stats():
    user_id = int(get_jwt_identity())
    all_recs = KidneyAssessment.query.filter_by(user_id=user_id).all()

    if not all_recs:
        return jsonify({"total": 0, "avg_risk": 0, "latest_risk": "N/A", "high_risk_count": 0}), 200

    probs  = [r.probability for r in all_recs]
    latest = max(all_recs, key=lambda r: r.created_at)
    high   = sum(1 for r in all_recs if r.risk_level == "High")

    return jsonify({
        "total":           len(all_recs),
        "avg_risk":        round(sum(probs) / len(probs) * 100, 1),
        "latest_risk":     latest.risk_level,
        "high_risk_count": high,
    }), 200


@kidney_bp.route("/records/<int:record_id>", methods=["DELETE"])
@jwt_required()
def delete_record(record_id):
    user_id = int(get_jwt_identity())
    rec = KidneyAssessment.query.filter_by(id=record_id, user_id=user_id).first()
    if not rec:
        return jsonify({"error": "Record not found"}), 404
    db.session.delete(rec)
    db.session.commit()
    return jsonify({"message": "Record deleted"}), 200
