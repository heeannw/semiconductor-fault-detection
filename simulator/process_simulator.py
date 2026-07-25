"""8대 반도체 공정 파라미터 기반 합성 데이터 생성기.

SECOM 데이터셋과는 독립적인 모듈이며, 학습된 이상 탐지 모델에
실시간 추론용 입력을 공급하는 역할을 한다.
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


PROCESS_SPECS: dict[str, list[ParamSpec]] = {
    "wafer_fabrication": [
        ParamSpec("temperature", 1400, 1500, "°C"),
        ParamSpec("oxygen_concentration", 0, 10, "ppb"),
        ParamSpec("resistivity", 1, 100, "Ω·cm"),
    ],
    "oxidation": [
        ParamSpec("temperature", 900, 1200, "°C"),
        ParamSpec("time", 10, 120, "min"),
        ParamSpec("oxide_thickness", 10, 1000, "nm"),
    ],
    "photolithography": [
        ParamSpec("exposure_energy", 10, 50, "mJ/cm²"),
        ParamSpec("focus_distance", -0.1, 0.1, "μm"),
        ParamSpec("temperature", 90, 130, "°C"),
    ],
    "etching": [
        ParamSpec("pressure", 5, 100, "mTorr"),
        ParamSpec("gas_flow", 10, 200, "sccm"),
        ParamSpec("power", 100, 2000, "W"),
    ],
    "deposition": [
        ParamSpec("temperature", 300, 900, "°C"),
        ParamSpec("pressure", 0.1, 10, "Torr"),
        ParamSpec("deposition_rate", 1, 100, "nm/min"),
    ],
    "metallization": [
        ParamSpec("current_density", 1, 10, "mA/cm²"),
        ParamSpec("temperature", 20, 80, "°C"),
        ParamSpec("plating_time", 1, 30, "min"),
    ],
    "eds": [
        ParamSpec("test_voltage", 1, 5, "V"),
        ParamSpec("test_current", 1, 100, "μA"),
    ],
    "packaging": [
        ParamSpec("dicing_speed", 10, 100, "mm/s"),
        ParamSpec("bonding_strength", 5, 15, "g"),
        ParamSpec("temperature", 150, 180, "°C"),
    ],
}

PROCESS_NAMES_KO: dict[str, str] = {
    "wafer_fabrication": "웨이퍼 제조",
    "oxidation": "산화",
    "photolithography": "포토",
    "etching": "식각",
    "deposition": "증착",
    "metallization": "금속 배선",
    "eds": "EDS",
    "packaging": "패키징",
}


class ProcessSimulator:
    """정상 범위 내/외 값을 생성해 8대 공정의 합성 센서 데이터를 만든다."""

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def _sample_param(self, spec: ParamSpec, anomaly: bool) -> float:
        if not anomaly:
            center = (spec.low + spec.high) / 2
            spread = (spec.high - spec.low) / 6  # 값의 대부분이 정상 범위 안에 들어오도록
            value = self.rng.normal(center, spread)
            return float(np.clip(value, spec.low, spec.high))

        # 이상치: 정상 범위 밖으로 벗어난 값을 좌/우 무작위로 생성
        margin = (spec.high - spec.low) * self.rng.uniform(0.1, 0.5)
        if self.rng.random() < 0.5:
            return float(spec.low - margin)
        return float(spec.high + margin)

    def generate_sample(
        self,
        process: str,
        anomaly: bool | None = None,
        anomaly_ratio: float = 0.1,
    ) -> dict:
        if process not in PROCESS_SPECS:
            raise ValueError(f"Unknown process: {process}. Valid: {list(PROCESS_SPECS)}")

        if anomaly is None:
            anomaly = bool(self.rng.random() < anomaly_ratio)

        params = {
            spec.name: round(self._sample_param(spec, anomaly), 4)
            for spec in PROCESS_SPECS[process]
        }
        return {
            "process": process,
            "process_name_ko": PROCESS_NAMES_KO[process],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **params,
            "is_anomaly": anomaly,
        }

    def generate_batch(
        self,
        process: str,
        n_samples: int,
        anomaly_ratio: float = 0.1,
    ) -> pd.DataFrame:
        rows = [self.generate_sample(process, anomaly_ratio=anomaly_ratio) for _ in range(n_samples)]
        return pd.DataFrame(rows)

    def generate_all(
        self,
        n_samples_per_process: int = 200,
        anomaly_ratio: float = 0.1,
    ) -> pd.DataFrame:
        frames = [
            self.generate_batch(process, n_samples_per_process, anomaly_ratio)
            for process in PROCESS_SPECS
        ]
        return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    sim = ProcessSimulator(seed=42)
    df = sim.generate_all(n_samples_per_process=5, anomaly_ratio=0.1)
    print(df.head(20).to_string())
    print("\nprocess counts:\n", df["process"].value_counts())
    print("\nanomaly ratio:\n", df["is_anomaly"].mean())
