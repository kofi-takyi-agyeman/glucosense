"""
GlucoSense — Diabetes Model Training (sex-agnostic, tuned)
==========================================================
Retrains the diabetes classifier with the 'Pregnancies' feature removed
and a more thorough pipeline aimed at squeezing out extra accuracy:

  • Impossible-zero handling   →  NaN, then KNN imputation
  • Feature engineering        →  log-transforms, ratios, interactions
  • Model shortlist            →  Logistic Regression, Random Forest,
                                  Gradient Boosting, HistGradientBoosting
  • Hyperparameter search      →  GridSearchCV, 5-fold stratified ROC-AUC
  • Final selection            →  best CV ROC-AUC wins
  • Held-out evaluation        →  20 % test split  (accuracy, ROC-AUC, report)

Run:     python train_model_no_preg.py
Output:  diabetes_model.pkl  (written next to this script)
"""

import io
import os
import sys
import pickle
import warnings

try:
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler, FunctionTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.impute import KNNImputer
    from sklearn.model_selection import (
        train_test_split, cross_val_score, StratifiedKFold, GridSearchCV,
    )
    from sklearn.metrics import (
        classification_report, roc_auc_score, confusion_matrix, accuracy_score,
    )
except ImportError as e:
    print(f"[diabetes-train] Missing dependency: {e}")
    print("[diabetes-train] Run: pip install scikit-learn pandas numpy")
    sys.exit(1)

from urllib.request import urlopen
from urllib.error import URLError

warnings.filterwarnings("ignore", category=UserWarning)

# ── Paths & dataset ──────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "diabetes_model.pkl")

DATASET_URLS = [
    "https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.data.csv",
    "https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.csv",
]

ALL_COLUMNS = [
    "pregnancies", "glucose", "blood_pressure", "skin_thickness",
    "insulin", "bmi", "diabetes_pedigree", "age", "outcome",
]

# Raw features kept (pregnancies dropped).
BASE_FEATURES = [
    "glucose", "blood_pressure", "skin_thickness", "insulin",
    "bmi", "diabetes_pedigree", "age",
]

# Zero is physiologically impossible → treat as NaN so the imputer can fill it.
ZERO_AS_MISSING = ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"]


# ── Data loading ─────────────────────────────────────────────────────────────
def load_dataset() -> pd.DataFrame:
    last_err = None
    for url in DATASET_URLS:
        try:
            print(f"[diabetes-train] Downloading dataset: {url}")
            with urlopen(url, timeout=30) as resp:
                raw = resp.read()
            df = pd.read_csv(io.BytesIO(raw), header=None, names=ALL_COLUMNS)
            print(f"[diabetes-train] Loaded {len(df)} rows, {df.shape[1]} columns")
            break
        except (URLError, Exception) as err:
            last_err = err
            print(f"[diabetes-train]   ✗ failed ({err}); trying next mirror…")
    else:
        raise RuntimeError(f"Could not download the dataset: {last_err}")

    df = df.drop(columns=["pregnancies"])
    print("[diabetes-train] Dropped column: pregnancies")

    for col in ZERO_AS_MISSING:
        n_zeros = int((df[col] == 0).sum())
        if n_zeros:
            df.loc[df[col] == 0, col] = np.nan
            print(f"[diabetes-train]   {col}: replaced {n_zeros} zero(s) with NaN")

    return df


# ── Feature engineering ──────────────────────────────────────────────────────
def engineer_features(X: pd.DataFrame) -> pd.DataFrame:
    """Add log-transforms, ratios, and clinically motivated interactions.

    NOTE: called *after* imputation, so there are no NaNs at this point.
    """
    X = X.copy()
    # Log-transform highly skewed features.
    for col in ["insulin", "skin_thickness", "diabetes_pedigree"]:
        X[f"log_{col}"] = np.log1p(X[col].clip(lower=0))

    # Clinically meaningful ratios / interactions.
    X["glucose_bmi"]     = X["glucose"] * X["bmi"] / 100.0
    X["insulin_glucose"] = X["insulin"] / (X["glucose"] + 1e-6)
    X["age_bmi"]         = X["age"] * X["bmi"] / 100.0
    X["glucose_age"]     = X["glucose"] * X["age"] / 100.0

    # Binary clinical flags — these often help tree models.
    X["flag_hyperglycaemic"] = (X["glucose"] >= 140).astype(float)
    X["flag_obese"]          = (X["bmi"]     >= 30 ).astype(float)
    X["flag_hypertensive"]   = (X["blood_pressure"] >= 90).astype(float)

    return X


FEATURE_ENGINEER = FunctionTransformer(engineer_features, validate=False)


# ── Pipeline factory ─────────────────────────────────────────────────────────
def make_pipeline(clf) -> Pipeline:
    return Pipeline([
        ("imputer", KNNImputer(n_neighbors=5, weights="distance")),
        # KNNImputer returns a numpy array → wrap back into a DataFrame so
        # engineer_features() can use column names.
        ("to_df",   FunctionTransformer(
            lambda arr: pd.DataFrame(arr, columns=BASE_FEATURES),
            validate=False,
        )),
        ("engineer", FEATURE_ENGINEER),
        ("scaler",   StandardScaler()),
        ("clf",      clf),
    ])


# ── Model shortlist & hyperparameter grids ───────────────────────────────────
def candidate_models():
    return {
        "LogisticRegression": (
            LogisticRegression(max_iter=5000, solver="lbfgs",
                               class_weight="balanced", random_state=42),
            {
                "clf__C":       [0.05, 0.1, 0.3, 1.0, 3.0, 10.0],
                "clf__penalty": ["l2"],
            },
        ),
        "RandomForest": (
            RandomForestClassifier(random_state=42, n_jobs=-1,
                                   class_weight="balanced"),
            {
                "clf__n_estimators":      [200, 400],
                "clf__max_depth":         [None, 6, 10],
                "clf__min_samples_leaf":  [1, 2, 4],
            },
        ),
        "GradientBoosting": (
            GradientBoostingClassifier(random_state=42),
            {
                "clf__n_estimators":  [150, 300],
                "clf__learning_rate": [0.03, 0.08],
                "clf__max_depth":     [2, 3],
            },
        ),
        "HistGradientBoosting": (
            HistGradientBoostingClassifier(random_state=42),
            {
                "clf__learning_rate": [0.03, 0.08, 0.15],
                "clf__max_depth":     [None, 4, 8],
                "clf__max_iter":      [200, 400],
            },
        ),
    }


# ── Training & evaluation ────────────────────────────────────────────────────
def train() -> None:
    print("\n╔════════════════════════════════════════════════╗")
    print("║  GlucoSense — Diabetes Model (tuned, no preg) ║")
    print("╚════════════════════════════════════════════════╝\n")

    df = load_dataset()
    print(f"[diabetes-train] Final dataset shape: {df.shape}")
    print(f"[diabetes-train] Class distribution:\n{df['outcome'].value_counts().to_string()}\n")

    X = df[BASE_FEATURES].copy()
    y = df["outcome"].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    print("[diabetes-train] ── Searching for the best model ──")
    leaderboard = []
    best_overall = None  # (name, estimator, cv_score)

    for name, (estimator, grid) in candidate_models().items():
        pipe = make_pipeline(estimator)
        search = GridSearchCV(
            pipe, grid, cv=cv, scoring="roc_auc",
            n_jobs=-1, refit=True, verbose=0,
        )
        search.fit(X_train, y_train)
        leaderboard.append((name, search.best_score_, search.best_params_))
        print(f"  {name:<22}  CV ROC-AUC = {search.best_score_:.4f}   "
              f"best = {search.best_params_}")
        if best_overall is None or search.best_score_ > best_overall[2]:
            best_overall = (name, search.best_estimator_, search.best_score_)

    print()
    print("[diabetes-train] Leaderboard (5-fold CV ROC-AUC on training split):")
    for name, score, params in sorted(leaderboard, key=lambda r: -r[1]):
        print(f"    {name:<22}  {score:.4f}")

    best_name, best_pipe, best_cv = best_overall
    print(f"\n[diabetes-train] ✓ Winner: {best_name}  (CV ROC-AUC = {best_cv:.4f})\n")

    # ── Held-out evaluation ──────────────────────────────────────────────────
    y_pred  = best_pipe.predict(X_test)
    y_proba = best_pipe.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    roc = roc_auc_score(y_test, y_proba)
    cm  = confusion_matrix(y_test, y_pred)

    print("[diabetes-train] ── Held-out test set (20%) ──")
    print(classification_report(y_test, y_pred, target_names=["No Diabetes", "Diabetes"]))
    print(f"[diabetes-train] Confusion matrix:")
    print(f"  TN={cm[0,0]}  FP={cm[0,1]}\n  FN={cm[1,0]}  TP={cm[1,1]}")
    print(f"[diabetes-train] Test accuracy : {acc:.4f}")
    print(f"[diabetes-train] Test ROC-AUC  : {roc:.4f}\n")

    # Full cross-validation sanity check on the whole dataset.
    full_cv = cross_val_score(best_pipe, X, y, cv=cv, scoring="roc_auc")
    print(f"[diabetes-train] 5-fold CV on full data: "
          f"{full_cv.mean():.4f} ± {full_cv.std():.4f}\n")

    # Refit on the entire dataset before saving.
    best_pipe.fit(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(best_pipe, f)

    print(f"[diabetes-train] ✓ Pipeline saved to {MODEL_PATH}")
    print(f"[diabetes-train] ✓ Stages: KNNImputer → FeatureEngineer → "
          f"StandardScaler → {best_name}\n")

    # ── Sanity check predictions ─────────────────────────────────────────────
    print("[diabetes-train] ── Sanity check predictions ──")
    sanity = [
        ("Healthy young adult",     [ 90, 70, 20,  80, 22.0, 0.25, 25]),
        ("Borderline middle-aged",  [130, 82, 28, 110, 29.5, 0.55, 48]),
        ("High-risk older adult",   [185, 92, 45, 220, 36.0, 1.20, 62]),
    ]
    for label, vals in sanity:
        sample = pd.DataFrame([vals], columns=BASE_FEATURES)
        prob = best_pipe.predict_proba(sample)[0][1] * 100
        risk = "Low" if prob < 30 else "Moderate" if prob < 60 else "High"
        print(f"  {label:<28} → {prob:5.1f}%  [{risk}]")

    print("\n[diabetes-train] Done.")
    print("[diabetes-train] Next steps:")
    print("  1. In backend/routes/predict.py, stop reading 'pregnancies' and build")
    print("     the feature vector in this exact order:")
    print("       " + ", ".join(BASE_FEATURES))
    print("     (The saved Pipeline handles imputation, engineering, and scaling.)")
    print("  2. Remove / hide the Pregnancies input on the frontend assessment.")
    print("  3. Restart Flask so it reloads diabetes_model.pkl.\n")


if __name__ == "__main__":
    train()
