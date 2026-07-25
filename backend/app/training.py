"""POST /api/model/retrain에서 쓰는 재학습 루틴.

notebooks/03_modeling.ipynb의 5-fold OOF 임계값 튜닝은 오프라인 실험 단계에서
이미 확정된 값(models/xgboost_threshold.joblib)을 그대로 재사용하고,
여기서는 최신 data/processed 데이터로 두 모델만 다시 학습해 저장한다.
"""
from pathlib import Path

import joblib
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"
RANDOM_STATE = 42

XGB_PARAMS = dict(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="logloss",
    random_state=RANDOM_STATE,
    n_jobs=-1,
)


def retrain_and_evaluate() -> dict:
    required = ["X_train_raw.csv", "y_train_raw.csv", "X_val.csv", "y_val.csv", "X_test.csv", "y_test.csv"]
    missing = [f for f in required if not (DATA_DIR / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"전처리 데이터가 없습니다: {missing}. notebooks/02_preprocessing.ipynb를 먼저 실행하세요."
        )

    X_train_raw = pd.read_csv(DATA_DIR / "X_train_raw.csv")
    y_train_raw = pd.read_csv(DATA_DIR / "y_train_raw.csv").squeeze("columns")
    X_val = pd.read_csv(DATA_DIR / "X_val.csv")
    y_val = pd.read_csv(DATA_DIR / "y_val.csv").squeeze("columns")
    X_test = pd.read_csv(DATA_DIR / "X_test.csv")
    y_test = pd.read_csv(DATA_DIR / "y_test.csv").squeeze("columns")

    X_dev = pd.concat([X_train_raw, X_val], ignore_index=True)
    y_dev = pd.concat([y_train_raw, y_val], ignore_index=True)

    if_model = IsolationForest(n_estimators=200, contamination=0.07, random_state=RANDOM_STATE, n_jobs=-1)
    if_model.fit(X_dev)

    X_dev_res, y_dev_res = SMOTE(random_state=RANDOM_STATE).fit_resample(X_dev, y_dev)
    xgb_model = XGBClassifier(**XGB_PARAMS)
    xgb_model.fit(X_dev_res, y_dev_res)

    threshold = joblib.load(MODELS_DIR / "xgboost_threshold.joblib")
    xgb_proba_test = xgb_model.predict_proba(X_test)[:, 1]
    xgb_pred_test = (xgb_proba_test >= threshold).astype(int)

    metrics = {
        "model_name": "xgboost",
        "precision": float(precision_score(y_test, xgb_pred_test, zero_division=0)),
        "recall": float(recall_score(y_test, xgb_pred_test, zero_division=0)),
        "f1": float(f1_score(y_test, xgb_pred_test, zero_division=0)),
        "auroc": float(roc_auc_score(y_test, xgb_proba_test)),
    }

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(if_model, MODELS_DIR / "isolation_forest.joblib")
    joblib.dump(xgb_model, MODELS_DIR / "xgboost.joblib")
    joblib.dump(list(X_dev.columns), MODELS_DIR / "feature_columns.joblib")

    return metrics
