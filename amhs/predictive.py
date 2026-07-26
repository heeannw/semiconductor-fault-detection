"""notebooks/08_amhs_delay_prediction.ipynb에서 학습한 지연 예측 모델을 실시간 디스패칭에 연결.

그 노트북의 핵심 발견은 "반송 지연은 정적 거리가 아니라 요청 시점의 실시간 시스템 부하
(concurrent_requests)가 거의 다 설명한다"는 것이었다(피처 중요도 0.726). 이 모듈은 그 모델을
그대로 불러와, 지금 이 순간 예측 지연이 임계값을 넘으면 — 07 노트북 비교에서 혼잡 상황에
더 유리했던 — 구역기반 디스패칭으로, 아니면 단순한 최근접 배정으로 전환하는 적응형
디스패처를 만든다.
"""
from pathlib import Path

import joblib
import pandas as pd

from .layout import STATIONS, travel_time_seconds
from .simulation import DispatchPolicy, TransportRequest, Vehicle, nearest_vehicle_dispatch, zone_based_dispatch

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# notebooks/08_amhs_delay_prediction.ipynb test set 평균 cycle time 근사값(mae_sec / mae_pct_of_mean).
# 이보다 예측치가 높으면 "평소보다 붐빈다"로 판단한다.
DEFAULT_CONGESTION_THRESHOLD_SEC = 307.0

REQUIRED_FILES = ["amhs_delay_regressor.joblib", "amhs_delay_features.joblib"]


def delay_model_available() -> bool:
    return all((MODELS_DIR / name).exists() for name in REQUIRED_FILES)


def load_delay_regressor():
    if not delay_model_available():
        raise FileNotFoundError(
            f"지연 예측 모델이 없습니다. notebooks/08_amhs_delay_prediction.ipynb를 먼저 실행하세요 ({MODELS_DIR})"
        )
    regressor = joblib.load(MODELS_DIR / "amhs_delay_regressor.joblib")
    feature_cols = joblib.load(MODELS_DIR / "amhs_delay_features.joblib")
    return regressor, feature_cols


def make_predictive_dispatch(
    n_vehicles: int,
    launch_interval_sec: float,
    congestion_threshold_sec: float = DEFAULT_CONGESTION_THRESHOLD_SEC,
) -> DispatchPolicy:
    """지연 예측이 임계값을 넘으면 구역기반, 아니면 최근접으로 전환하는 적응형 정책."""
    regressor, feature_cols = load_delay_regressor()

    def policy(request: TransportRequest, idle_vehicles: list[Vehicle], all_vehicles: list[Vehicle] | None) -> Vehicle:
        concurrent = sum(1 for v in (all_vehicles or idle_vehicles) if v.busy)
        row = pd.DataFrame([{
            "from_idx": STATIONS[request.from_station].index,
            "to_idx": STATIONS[request.to_station].index,
            "direct_travel_time": travel_time_seconds(request.from_station, request.to_station),
            "concurrent_requests": concurrent,
            "n_vehicles": n_vehicles,
            "launch_interval_sec": launch_interval_sec,
        }])[feature_cols]
        predicted_cycle_time = float(regressor.predict(row)[0])

        if predicted_cycle_time > congestion_threshold_sec:
            return zone_based_dispatch(request, idle_vehicles, all_vehicles)
        return nearest_vehicle_dispatch(request, idle_vehicles, all_vehicles)

    return policy
