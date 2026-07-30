"""notebooks/12_fault_scenario_classification.ipynb에서 학습한 공정별 원인 분류 모델을
실시간 추론에 연결.

`simulator/diagnosis.py`가 파라미터 하나씩 독립적으로 검사하는 규칙 기반 진단이라면, 이
모듈은 여러 파라미터의 **동시 패턴**에서 XGBoost가 학습한 원인을 예측한다 — "이 파라미터가
규격을 벗어났다"가 아니라 "이런 패턴을 보이는 원인은 대체로 이거였다"를 데이터로부터 추론한
결과다. 노트북을 먼저 실행하지 않은 클론(모델 파일이 없는 상태)에서도 나머지 기능이 깨지지
않도록, `amhs/predictive.py`와 같은 패턴으로 모델 부재를 우아하게 처리한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from .fault_scenarios import scenario_label_ko
from .process_simulator import PROCESS_SPECS

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


@dataclass(frozen=True)
class FaultPrediction:
    process: str
    predicted_label: str  # "normal" 또는 시나리오 영문 식별자
    predicted_label_ko: str
    confidence: float
    probabilities: dict[str, float]  # 레이블(한글) -> 확률


def _model_paths(process: str) -> tuple[Path, Path, Path]:
    return (
        MODELS_DIR / f"fault_classifier_{process}.joblib",
        MODELS_DIR / f"fault_classifier_{process}_labels.joblib",
        MODELS_DIR / f"fault_classifier_{process}_features.joblib",
    )


def fault_classifier_available(process: str) -> bool:
    if process not in PROCESS_SPECS:
        return False
    return all(path.exists() for path in _model_paths(process))


def predict_fault(process: str, params: dict[str, float]) -> FaultPrediction | None:
    """모델이 없으면(노트북 12를 아직 안 돌린 클론) None을 반환한다 — 호출부가 이걸 보고
    "AI 예측 원인" 섹션을 그냥 생략하면 된다(다른 ML 의존 기능들과 동일한 관례)."""
    if not fault_classifier_available(process):
        return None

    model_path, labels_path, features_path = _model_paths(process)
    model = joblib.load(model_path)
    encoder = joblib.load(labels_path)
    feature_cols = joblib.load(features_path)

    row = pd.DataFrame([{col: params.get(col, 0.0) for col in feature_cols}])[feature_cols]
    proba = model.predict_proba(row)[0]
    predicted_idx = int(proba.argmax())
    predicted_label = str(encoder.classes_[predicted_idx])

    probabilities = {
        scenario_label_ko(process, str(label)): float(p)
        for label, p in zip(encoder.classes_, proba)
    }

    return FaultPrediction(
        process=process,
        predicted_label=predicted_label,
        predicted_label_ko=scenario_label_ko(process, predicted_label),
        confidence=float(proba[predicted_idx]),
        probabilities=probabilities,
    )
