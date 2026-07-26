"""notebooks/09_amhs_predictive_maintenance.ipynb에서 학습한 예지보전 모델을 시뮬레이션에 피드백.

주기적으로 각 유휴 차량의 상태 센서를 합성 생성해 IF+XGBoost 앙상블로 이상 여부를 판정하고,
이상으로 판정된 차량을 일정 시간 운행 중단시킨다. 차량이 줄면 디스패칭 대기가 늘고 반송이
느려지는 것을 시뮬레이션에서 직접 관찰할 수 있다 — `docs/AMHS.md`가 말하는
"차량 고장 -> 정체 도미노"를 코드로 보여주는 부분이다.

바쁜(반송 중인) 차량은 점검하지 않는다 — 이동 중에 갑자기 멈추게 하면 FOUP이 허공에 남는
비현실적인 상태가 되므로, 점검은 항상 유휴 상태인 차량에만 적용한다.
"""
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
import pandas as pd
import simpy

from .vehicle_health_simulator import VEHICLE_HEALTH_SPECS, VehicleHealthSimulator

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

REQUIRED_FILES = [
    "amhs_vehicle_isolation_forest.joblib",
    "amhs_vehicle_xgboost.joblib",
    "amhs_vehicle_scaler.joblib",
    "amhs_vehicle_feature_columns.joblib",
    "amhs_vehicle_threshold.joblib",
]

DEFAULT_CHECK_INTERVAL_SEC = 1800.0
DEFAULT_DOWNTIME_SEC = 1200.0
DEFAULT_ANOMALY_RATIO = 0.03


def pm_model_available() -> bool:
    return all((MODELS_DIR / name).exists() for name in REQUIRED_FILES)


def load_pm_models() -> dict:
    if not pm_model_available():
        raise FileNotFoundError(
            f"예지보전 모델이 없습니다. notebooks/09_amhs_predictive_maintenance.ipynb를 먼저 실행하세요 ({MODELS_DIR})"
        )
    return {
        "if_model": joblib.load(MODELS_DIR / "amhs_vehicle_isolation_forest.joblib"),
        "xgb_model": joblib.load(MODELS_DIR / "amhs_vehicle_xgboost.joblib"),
        "scaler": joblib.load(MODELS_DIR / "amhs_vehicle_scaler.joblib"),
        "feature_cols": joblib.load(MODELS_DIR / "amhs_vehicle_feature_columns.joblib"),
        "threshold": joblib.load(MODELS_DIR / "amhs_vehicle_threshold.joblib"),
    }


def _is_anomalous(models: dict, features: dict) -> bool:
    row = pd.DataFrame([[features[c] for c in models["feature_cols"]]], columns=models["feature_cols"])
    scaled = pd.DataFrame(models["scaler"].transform(row), columns=models["feature_cols"])
    if_flag = models["if_model"].predict(scaled)[0] == -1
    xgb_proba = models["xgb_model"].predict_proba(scaled)[0, 1]
    xgb_flag = xgb_proba >= models["threshold"]
    return bool(if_flag or xgb_flag)


def _restore_after(env: simpy.Environment, vehicle, downtime_sec: float, maintenance_log: list | None):
    yield env.timeout(downtime_sec)
    vehicle.under_maintenance = False
    if maintenance_log is not None:
        maintenance_log.append({"time": env.now, "vehicle_id": vehicle.id, "event": "restored"})


def make_maintenance_process(
    check_interval_sec: float = DEFAULT_CHECK_INTERVAL_SEC,
    downtime_sec: float = DEFAULT_DOWNTIME_SEC,
    anomaly_ratio: float = DEFAULT_ANOMALY_RATIO,
    maintenance_log: list | None = None,
) -> Callable:
    """`run_simulation(maintenance_process=...)`에 넘길 SimPy 프로세스 팩토리."""
    models = load_pm_models()

    def process(env: simpy.Environment, vehicles, rng: np.random.Generator):
        health_sim = VehicleHealthSimulator(seed=int(rng.integers(0, 1_000_000)))
        while True:
            yield env.timeout(check_interval_sec)
            for vehicle in vehicles:
                if vehicle.busy or vehicle.under_maintenance:
                    continue
                sample = health_sim.generate_sample(vehicle.id, anomaly_ratio=anomaly_ratio)
                features = {spec.name: sample[spec.name] for spec in VEHICLE_HEALTH_SPECS}
                if _is_anomalous(models, features):
                    vehicle.under_maintenance = True
                    vehicle.downtime_seconds += downtime_sec
                    if maintenance_log is not None:
                        maintenance_log.append({"time": env.now, "vehicle_id": vehicle.id, "event": "down"})
                    env.process(_restore_after(env, vehicle, downtime_sec, maintenance_log))

    return process
