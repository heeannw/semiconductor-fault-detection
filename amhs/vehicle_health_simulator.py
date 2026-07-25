"""OHT 차량 상태 센서 합성 데이터 생성기.

`simulator/process_simulator.py`(8대 공정 시뮬레이터)와 동일한 설계를 그대로 재사용한다 —
파라미터별 정상 범위를 정의하고, 정상 분포 내 값 또는 범위를 벗어난 이상값을 생성한다.
대상만 "공정 파라미터"에서 "OHT 차량 센서"로 바뀌었을 뿐이다.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ParamSpec:
    name: str
    low: float
    high: float
    unit: str


# OHT 차량 상태 센서 정상 범위. 실제 값은 공개 스펙이 아니라 업계 자료(OHT 유지보수 가이드,
# 산업용 모터/베어링 진동 기준 ISO 10816 등)를 참고해 그럴듯한 범위로 잡은 것 — SECOM처럼
# 실측 데이터는 아니고, 시뮬레이터 데이터라는 점을 노트북에도 명시한다.
VEHICLE_HEALTH_SPECS: list[ParamSpec] = [
    ParamSpec("motor_current", 2.0, 5.0, "A"),
    ParamSpec("hoist_vibration", 0.5, 3.0, "mm/s RMS"),
    ParamSpec("hoist_motor_temp", 30.0, 60.0, "°C"),
    ParamSpec("brake_response_time", 50.0, 150.0, "ms"),
    ParamSpec("wheel_bearing_temp", 25.0, 55.0, "°C"),
]


class VehicleHealthSimulator:
    """`simulator.ProcessSimulator`와 동일한 인터페이스(generate_sample/generate_batch)."""

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def _sample_param(self, spec: ParamSpec, anomaly: bool) -> float:
        if not anomaly:
            center = (spec.low + spec.high) / 2
            spread = (spec.high - spec.low) / 6
            value = self.rng.normal(center, spread)
            return float(np.clip(value, spec.low, spec.high))

        margin = (spec.high - spec.low) * self.rng.uniform(0.1, 0.5)
        if self.rng.random() < 0.5:
            return float(spec.low - margin)
        return float(spec.high + margin)

    def generate_sample(
        self,
        vehicle_id: int,
        anomaly: bool | None = None,
        anomaly_ratio: float = 0.1,
    ) -> dict:
        if anomaly is None:
            anomaly = bool(self.rng.random() < anomaly_ratio)

        params = {
            spec.name: round(self._sample_param(spec, anomaly), 4)
            for spec in VEHICLE_HEALTH_SPECS
        }
        return {
            "vehicle_id": vehicle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **params,
            "is_anomaly": anomaly,
        }

    def generate_batch(self, vehicle_id: int, n_samples: int, anomaly_ratio: float = 0.1) -> pd.DataFrame:
        rows = [self.generate_sample(vehicle_id, anomaly_ratio=anomaly_ratio) for _ in range(n_samples)]
        return pd.DataFrame(rows)

    def generate_fleet(self, n_vehicles: int, n_samples_per_vehicle: int, anomaly_ratio: float = 0.1) -> pd.DataFrame:
        frames = [
            self.generate_batch(vid, n_samples_per_vehicle, anomaly_ratio)
            for vid in range(n_vehicles)
        ]
        return pd.concat(frames, ignore_index=True)
