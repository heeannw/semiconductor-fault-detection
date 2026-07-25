"""SECOM으로 학습된 Isolation Forest / XGBoost 앙상블 로드 및 추론.

공정 시뮬레이터의 물리 파라미터(온도, 압력 등)와는 피처 공간이 다르므로,
이 모듈은 SECOM과 동일한 피처 형식(models/feature_columns.joblib 기준)의
입력만 받는다. 시뮬레이터 데이터의 정상/이상 판정은 시뮬레이터 자체 로직을
사용하며 이 모델과는 별개다.
"""
from pathlib import Path

import joblib
import numpy as np

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
REQUIRED_FILES = [
    "isolation_forest.joblib",
    "xgboost.joblib",
    "feature_columns.joblib",
    "xgboost_threshold.joblib",
]

_cache: dict = {}


def models_available() -> bool:
    return all((MODELS_DIR / name).exists() for name in REQUIRED_FILES)


def _load():
    if not _cache:
        if not models_available():
            raise FileNotFoundError(
                f"모델 파일이 없습니다. notebooks/03_modeling.ipynb를 먼저 실행하세요 ({MODELS_DIR})"
            )
        _cache["if_model"] = joblib.load(MODELS_DIR / "isolation_forest.joblib")
        _cache["xgb_model"] = joblib.load(MODELS_DIR / "xgboost.joblib")
        _cache["feature_columns"] = joblib.load(MODELS_DIR / "feature_columns.joblib")
        _cache["threshold"] = joblib.load(MODELS_DIR / "xgboost_threshold.joblib")
    return _cache["if_model"], _cache["xgb_model"], _cache["feature_columns"], _cache["threshold"]


def reload_models() -> None:
    """retrain 등으로 joblib 파일이 갱신된 뒤 캐시를 비운다."""
    _cache.clear()


def get_feature_columns() -> list[str]:
    _, _, feature_columns, _ = _load()
    return list(feature_columns)


def top_feature_importance(top_n: int = 20) -> dict:
    _, xgb_model, feature_columns, _ = _load()
    pairs = sorted(zip(feature_columns, xgb_model.feature_importances_), key=lambda p: p[1], reverse=True)[:top_n]
    return {
        "features": [name for name, _ in pairs],
        "importances": [float(score) for _, score in pairs],
    }


def predict(features: dict[str, float]) -> dict:
    if_model, xgb_model, feature_columns, threshold = _load()

    missing = [c for c in feature_columns if c not in features]
    if missing:
        raise ValueError(f"{len(missing)}개 피처 누락 (예: {missing[:5]})")

    row = np.array([[features[c] for c in feature_columns]])

    if_is_anomaly = bool(if_model.predict(row)[0] == -1)
    if_score = float(-if_model.decision_function(row)[0])

    xgb_proba = float(xgb_model.predict_proba(row)[0, 1])
    xgb_is_anomaly = bool(xgb_proba >= threshold)

    ensemble_is_anomaly = if_is_anomaly or xgb_is_anomaly
    # 단일 샘플이라 배치 정규화가 불가능하므로 IF 점수는 0~1로 클리핑해 근사치로 사용
    ensemble_score = 0.5 * min(max(if_score, 0.0), 1.0) + 0.5 * xgb_proba

    return {
        "is_anomaly_isolation_forest": if_is_anomaly,
        "is_anomaly_xgboost": xgb_is_anomaly,
        "is_anomaly_ensemble": ensemble_is_anomaly,
        "if_score": if_score,
        "xgb_proba": xgb_proba,
        "ensemble_score": ensemble_score,
    }
