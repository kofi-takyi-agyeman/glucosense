"""
GlucoSense — Kidney Disease Model Training Script
==================================================
Trains a Random Forest classifier to predict Chronic Kidney Disease (CKD).
Based on the UCI Chronic Kidney Disease dataset (400 samples).

Features used (15 total):
  Numerical : age, blood_pressure, blood_glucose_random, blood_urea,
              serum_creatinine, sodium, potassium, haemoglobin,
              packed_cell_volume, white_blood_cell_count, red_blood_cell_count
  Binary    : hypertension, diabetes_mellitus, pedal_edema, anemia

Run:  python train_kidney_model.py
Output: kidney_model.pkl (same directory)
"""

import os
import sys
import pickle
import numpy as np

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
    from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
except ImportError as e:
    print(f"[kidney-train] Missing dependency: {e}")
    print("[kidney-train] Run: pip install scikit-learn pandas numpy")
    sys.exit(1)

try:
    from urllib.request import urlretrieve
except ImportError:
    urlretrieve = None

MODEL_PATH = os.path.join(os.path.dirname(__file__), "kidney_model.pkl")

FEATURE_NAMES = [
    "age", "blood_pressure", "blood_glucose_random", "blood_urea",
    "serum_creatinine", "sodium", "potassium", "haemoglobin",
    "packed_cell_volume", "white_blood_cell_count", "red_blood_cell_count",
    "hypertension", "diabetes_mellitus", "pedal_edema", "anemia",
]

# ── Generate synthetic training data based on UCI CKD dataset statistics ──────
# CKD class  : ~250 samples  (label = 1)
# Non-CKD    : ~150 samples  (label = 0)
# Statistics sourced from:
#   Soundarapandian & Durai, "Chronic_Kidney_Disease Data Set", UCI ML Repo, 2015

def generate_ckd_data(n_ckd=250, n_notckd=150, seed=42):
    rng = np.random.default_rng(seed)

    # ── CKD patients (class = 1) ──────────────────────────────────────────────
    ckd = {
        "age":                    rng.normal(51,  17,  n_ckd).clip(2, 90),
        "blood_pressure":         rng.normal(79,  18,  n_ckd).clip(50, 180),
        "blood_glucose_random":   rng.normal(146, 74,  n_ckd).clip(70, 490),
        "blood_urea":             rng.normal(78,  55,  n_ckd).clip(10, 391),
        "serum_creatinine":       rng.normal(5.7,  5.8, n_ckd).clip(0.5, 47.0),
        "sodium":                 rng.normal(133, 14,  n_ckd).clip(111, 163),
        "potassium":              rng.normal(4.9,  1.9, n_ckd).clip(2.5, 47.0),
        "haemoglobin":            rng.normal(10.0, 2.4, n_ckd).clip(3.1, 17.8),
        "packed_cell_volume":     rng.normal(30,   8,   n_ckd).clip(9,  54),
        "white_blood_cell_count": rng.normal(9300, 3500,n_ckd).clip(3800, 26400),
        "red_blood_cell_count":   rng.normal(3.4,  0.9, n_ckd).clip(1.5, 6.1),
        "hypertension":           rng.binomial(1, 0.72, n_ckd).astype(float),
        "diabetes_mellitus":      rng.binomial(1, 0.44, n_ckd).astype(float),
        "pedal_edema":            rng.binomial(1, 0.67, n_ckd).astype(float),
        "anemia":                 rng.binomial(1, 0.53, n_ckd).astype(float),
    }

    # ── Non-CKD patients (class = 0) ─────────────────────────────────────────
    notckd = {
        "age":                    rng.normal(46,  15,  n_notckd).clip(2, 90),
        "blood_pressure":         rng.normal(72,  12,  n_notckd).clip(50, 120),
        "blood_glucose_random":   rng.normal(103, 39,  n_notckd).clip(70, 300),
        "blood_urea":             rng.normal(28,  10,  n_notckd).clip(10, 80),
        "serum_creatinine":       rng.normal(0.92, 0.25,n_notckd).clip(0.5, 2.0),
        "sodium":                 rng.normal(141,  3,  n_notckd).clip(130, 163),
        "potassium":              rng.normal(4.4,  0.6, n_notckd).clip(2.5, 6.5),
        "haemoglobin":            rng.normal(15.0, 1.3, n_notckd).clip(10, 17.8),
        "packed_cell_volume":     rng.normal(44,   4,   n_notckd).clip(30, 54),
        "white_blood_cell_count": rng.normal(7800, 2000,n_notckd).clip(3800, 15000),
        "red_blood_cell_count":   rng.normal(5.1,  0.5, n_notckd).clip(3.5, 6.5),
        "hypertension":           rng.binomial(1, 0.18, n_notckd).astype(float),
        "diabetes_mellitus":      rng.binomial(1, 0.14, n_notckd).astype(float),
        "pedal_edema":            rng.binomial(1, 0.03, n_notckd).astype(float),
        "anemia":                 rng.binomial(1, 0.08, n_notckd).astype(float),
    }

    df_ckd    = pd.DataFrame(ckd);    df_ckd["outcome"]    = 1
    df_notckd = pd.DataFrame(notckd); df_notckd["outcome"] = 0

    df = pd.concat([df_ckd, df_notckd], ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def train():
    print("\n╔══════════════════════════════════════════╗")
    print("║  GlucoSense — Kidney Disease ML Model   ║")
    print("╚══════════════════════════════════════════╝\n")

    df = generate_ckd_data()
    print(f"[kidney-train] Dataset shape: {df.shape}")
    print(f"[kidney-train] Class distribution:\n{df['outcome'].value_counts().to_string()}\n")

    X = df[FEATURE_NAMES].copy()
    y = df["outcome"].values

    # ── Pipeline ──────────────────────────────────────────────────────────────
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("clf",     RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])

    # ── Train / evaluate ──────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    pipeline.fit(X_train, y_train)

    y_pred  = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    print("[kidney-train] ── Evaluation on held-out test set (20%) ──")
    print(classification_report(y_test, y_pred, target_names=["No CKD", "CKD"]))

    cm = confusion_matrix(y_test, y_pred)
    print(f"[kidney-train] Confusion matrix:\n  TN={cm[0,0]}  FP={cm[0,1]}\n  FN={cm[1,0]}  TP={cm[1,1]}\n")

    roc = roc_auc_score(y_test, y_proba)
    print(f"[kidney-train] ROC-AUC: {roc:.4f}\n")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="roc_auc")
    print(f"[kidney-train] 5-fold CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}\n")

    # Retrain on full dataset
    pipeline.fit(X, y)

    # ── Save ──────────────────────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"[kidney-train] ✓ Pipeline saved to {MODEL_PATH}")
    print("[kidney-train] ✓ Model: Imputer → Scaler → RandomForest\n")

    # ── Sanity check ──────────────────────────────────────────────────────────
    print("[kidney-train] ── Sanity check predictions ──")
    sanity = [
        ("Healthy young person",     [28, 70, 100, 20, 0.8, 142, 4.3, 15.0, 45, 7500, 5.2, 0, 0, 0, 0]),
        ("Borderline moderate risk", [50, 80, 130, 55, 3.0, 136, 4.8, 11.5, 33, 9000, 3.8, 1, 0, 1, 0]),
        ("Severe CKD indicators",   [65, 95, 170, 110, 9.5, 128, 5.5, 8.2,  24, 11000,2.8, 1, 1, 1, 1]),
    ]
    for label, vals in sanity:
        sample = pd.DataFrame([vals], columns=FEATURE_NAMES)
        prob = pipeline.predict_proba(sample)[0][1] * 100
        risk = "Low" if prob < 30 else "Moderate" if prob < 60 else "High"
        print(f"  {label:<35} → {prob:5.1f}%  [{risk}]")

    print("\n[kidney-train] Done. Restart Flask to load the new model.\n")


if __name__ == "__main__":
    train()
