"""
GlucoSense — Model Training Script
===================================
Trains a Logistic Regression classifier on the Pima Indians Diabetes dataset.

Key design decisions:
  • Uses sklearn Pipeline (StandardScaler + LogisticRegression) so that the
    scaler is baked into the saved model. predict.py can then pass raw values
    directly — no manual scaling needed.
  • Replaces biologically impossible zeros (glucose, BP, skin, insulin, BMI)
    with column medians before scaling.
  • class_weight='balanced' corrects for the 65/35 non-diabetic/diabetic
    imbalance so the model doesn't always predict the majority class.

Run:  python train_model.py
Output: model.pkl (in the same directory)
"""

import os
import sys
import pickle
import numpy as np

# ── Try to import required packages ─────────────────────────────────────────
try:
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
    from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
except ImportError as e:
    print(f"[train] Missing dependency: {e}")
    print("[train] Run: pip install scikit-learn pandas numpy")
    sys.exit(1)

# ── Try to import urllib for data download ───────────────────────────────────
try:
    from urllib.request import urlretrieve
except ImportError:
    urlretrieve = None

# ── Dataset ──────────────────────────────────────────────────────────────────
DATASET_URL = (
    "https://raw.githubusercontent.com/jbrownlee/Datasets/master/"
    "pima-indians-diabetes.csv"
)
DATASET_PATH = os.path.join(os.path.dirname(__file__), "diabetes.csv")
MODEL_PATH   = os.path.join(os.path.dirname(__file__), "model.pkl")

COLUMNS = [
    "pregnancies", "glucose", "blood_pressure", "skin_thickness",
    "insulin", "bmi", "diabetes_pedigree", "age", "outcome"
]

# Columns where a value of 0 is physiologically impossible → treat as missing
ZERO_AS_NAN = ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"]

# ── Pima dataset embedded as fallback (first 50 rows × representative) ───────
# Full 768-row dataset downloaded from URL when possible; this small set is
# used only if the download fails and diabetes.csv doesn't exist.
EMBEDDED_DATA = """6,148,72,35,0,33.6,0.627,50,1
1,85,66,29,0,26.6,0.351,31,0
8,183,64,0,0,23.3,0.672,32,1
1,89,66,23,94,28.1,0.167,21,0
0,137,40,35,168,43.1,2.288,33,1
5,116,74,0,0,25.6,0.201,30,0
3,78,50,32,88,31,0.248,26,1
10,115,0,0,0,35.3,0.134,29,0
2,197,70,45,543,30.5,0.158,53,1
8,125,96,0,0,0,0.232,54,1
4,110,92,0,0,37.6,0.191,30,0
10,168,74,0,0,38,0.537,34,1
10,139,80,0,0,27.1,1.441,57,0
1,189,60,23,846,30.1,0.398,59,1
5,166,72,19,175,25.8,0.587,51,1
7,100,0,0,0,30,0.484,32,1
0,118,84,47,230,45.8,0.551,31,1
7,107,74,0,0,29.6,0.254,31,1
1,103,30,38,83,43.3,0.183,33,0
1,115,70,30,96,34.6,0.529,32,1
3,126,88,41,235,39.3,0.704,27,0
8,99,84,0,0,35.4,0.388,50,0
7,196,90,0,0,39.8,0.451,41,1
9,119,80,35,0,29,0.263,29,1
11,143,94,33,146,36.6,0.254,51,1
10,125,70,26,115,31.1,0.205,41,1
7,147,76,0,0,39.4,0.257,43,1
1,97,66,15,140,23.2,0.487,22,0
13,145,82,19,110,22.2,0.245,57,0
5,117,92,0,0,34.1,0.337,38,0
5,109,75,26,0,36,0.546,60,0
3,158,76,36,245,31.6,0.851,28,1
3,88,58,11,54,24.8,0.267,22,0
6,92,92,0,0,19.9,0.188,28,0
10,122,78,31,0,27.6,0.512,45,0
4,103,60,33,192,24,0.966,33,0
11,138,76,0,0,33.2,0.42,35,0
9,102,76,37,0,32.9,0.665,46,1
2,90,68,42,0,38.2,0.503,27,1
4,111,72,47,207,37.1,1.39,56,1
3,180,64,25,70,34,0.271,26,0
7,133,84,0,0,40.2,0.696,37,0
7,106,92,18,0,22.7,0.235,48,0
9,171,110,24,240,45.4,0.721,54,1
7,159,64,0,0,27.4,0.294,40,0
0,180,66,39,0,42,1.893,25,1
1,146,56,0,0,29.7,0.564,29,0
2,71,70,27,0,28,0.586,22,0
7,103,66,32,0,39.1,0.344,31,1
7,105,0,0,0,0,0.305,24,0
1,103,80,11,82,19.4,0.491,22,0
1,101,50,15,36,24.2,0.526,26,0
5,88,66,21,23,24.4,0.342,30,0
8,176,90,34,300,33.7,0.467,58,1
7,150,66,42,342,34.7,0.718,42,0
1,73,50,10,0,23,0.248,21,0
7,187,68,39,304,37.7,0.254,41,1
0,100,88,60,110,46.8,0.962,31,0
0,146,82,0,0,40.5,1.781,44,0
0,105,64,41,142,41.5,0.173,22,0
2,84,0,0,0,0,0.304,21,0
8,133,72,0,0,32.9,0.27,39,1
5,44,62,0,0,25,0.587,36,0
2,141,58,34,128,25.4,0.699,24,0
7,114,66,0,0,32.8,0.258,42,1
5,99,74,27,0,29,0.203,32,0
0,109,88,30,0,32.5,0.855,38,1
2,109,92,0,0,42.7,0.845,54,0
1,95,66,13,38,19.6,0.334,25,0
4,146,92,0,0,31.2,0.539,61,1
2,100,66,20,90,32.9,0.867,28,1
5,139,64,35,140,28.6,0.411,26,0
13,126,90,0,0,43.4,0.583,42,1
4,129,86,20,270,35.1,0.231,23,0
1,79,75,30,0,32,0.396,22,0
1,0,48,20,0,24.7,0.14,22,0
7,62,78,0,0,32.6,0.391,41,0
5,95,72,33,0,37.7,0.37,27,0
0,131,0,0,0,43.2,0.270,26,1
2,112,75,32,0,35.7,0.148,21,0
3,128,78,0,0,21.1,0.268,55,0
4,123,62,0,0,32,0.226,35,1
2,108,64,0,0,30.8,0.158,21,0
4,154,62,31,284,32.8,0.237,23,0
3,78,70,0,0,32.5,0.270,39,0
10,101,76,48,180,32.9,0.171,63,0
2,122,70,27,0,36.8,0.340,27,0
5,121,72,23,112,26.2,0.245,30,0
1,126,60,0,0,30.1,0.349,47,1
1,93,70,31,0,30.4,0.315,23,0"""


def load_dataset():
    """Load the Pima dataset — download if not present, fall back to embedded."""

    # 1. Try to use existing diabetes.csv
    if os.path.exists(DATASET_PATH):
        print(f"[train] Loading dataset from {DATASET_PATH}")
        df = pd.read_csv(DATASET_PATH, header=None, names=COLUMNS)
        return df

    # 2. Try to download
    if urlretrieve is not None:
        try:
            print(f"[train] Downloading dataset from {DATASET_URL} ...")
            urlretrieve(DATASET_URL, DATASET_PATH)
            print(f"[train] Saved to {DATASET_PATH}")
            df = pd.read_csv(DATASET_PATH, header=None, names=COLUMNS)
            return df
        except Exception as e:
            print(f"[train] Download failed ({e}), using embedded data")

    # 3. Fall back to embedded rows
    print("[train] Using embedded dataset (90 representative samples)")
    from io import StringIO
    df = pd.read_csv(StringIO(EMBEDDED_DATA), header=None, names=COLUMNS)
    return df


def train():
    print("\n╔══════════════════════════════════════╗")
    print("║  GlucoSense — Training ML Model      ║")
    print("╚══════════════════════════════════════╝\n")

    # ── Load data ────────────────────────────────────────────────────────────
    df = load_dataset()
    print(f"[train] Dataset shape: {df.shape}")
    print(f"[train] Class distribution:\n{df['outcome'].value_counts().to_string()}\n")

    # ── Feature matrix & target ───────────────────────────────────────────────
    X = df[COLUMNS[:-1]].copy()
    y = df["outcome"].values

    # Replace physiologically impossible zeros with NaN
    for col in ZERO_AS_NAN:
        if col in X.columns:
            X[col] = X[col].replace(0, np.nan)

    # ── Build Pipeline ────────────────────────────────────────────────────────
    #   SimpleImputer  → fills NaN with median (robust to outliers)
    #   StandardScaler → zero-mean, unit-variance normalisation
    #   LogisticRegression → class_weight='balanced' corrects class imbalance
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("clf",     LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
            C=0.8,              # slight L2 regularisation
            solver="lbfgs",
        )),
    ])

    # ── Train / evaluate ──────────────────────────────────────────────────────
    if len(df) >= 100:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        pipeline.fit(X_train, y_train)

        y_pred  = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)[:, 1]

        print("[train] ── Evaluation on held-out test set (20%) ──")
        print(classification_report(y_test, y_pred, target_names=["Non-Diabetic", "Diabetic"]))

        cm = confusion_matrix(y_test, y_pred)
        print(f"[train] Confusion matrix:\n  TN={cm[0,0]}  FP={cm[0,1]}\n  FN={cm[1,0]}  TP={cm[1,1]}\n")

        roc = roc_auc_score(y_test, y_proba)
        print(f"[train] ROC-AUC: {roc:.4f}\n")

        # Cross-validation on full set for stability estimate
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="roc_auc")
        print(f"[train] 5-fold CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}\n")

        # Retrain on full dataset before saving
        pipeline.fit(X, y)
    else:
        # Small embedded fallback — just train on everything
        print("[train] Small dataset — training on all samples (no test split)")
        pipeline.fit(X, y)

    # ── Save pipeline ─────────────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"[train] ✓ Pipeline saved to {MODEL_PATH}")
    print("[train] ✓ Model includes: Imputer → Scaler → LogisticRegression")
    print("[train]   Raw inputs can now be passed directly — no manual scaling needed.\n")

    # ── Quick sanity check ────────────────────────────────────────────────────
    print("[train] ── Sanity check predictions ──")
    sanity = [
        ("Healthy 25-yr-old woman",  [0, 85,  70, 20,  80, 24.0, 0.200, 25]),
        ("Borderline (moderate)",    [2, 120, 75, 28, 120, 30.0, 0.350, 35]),
        ("High-risk 50-yr-old",      [8, 180, 90, 40, 300, 38.0, 0.800, 50]),
    ]
    for label, vals in sanity:
        sample = pd.DataFrame([vals], columns=COLUMNS[:-1])
        prob = pipeline.predict_proba(sample)[0][1] * 100
        risk = "Low" if prob < 30 else "Moderate" if prob < 60 else "High"
        print(f"  {label:<35} → {prob:5.1f}%  [{risk}]")

    print("\n[train] Done. Restart the Flask server to load the new model.\n")


if __name__ == "__main__":
    train()
