"""숨은 원인(fault scenario)이 여러 파라미터에 상관된 패턴으로 나타나는 합성 데이터 생성기.

`simulator/diagnosis.py`의 규칙 기반 진단은 파라미터를 하나씩 독립적으로 검사한다 —
"압력이 규격을 벗어났다", "가스 유량이 규격을 벗어났다"를 따로 진단할 뿐, 그 둘이 사실
**같은 원인**(예: MFC 캘리브레이션 드리프트) 때문이라는 건 알지 못한다. 실제 설비 고장은
보통 여러 센서에 동시에 상관된 흔적을 남기므로, 이 모듈은 그 상관 패턴 자체를 학습 데이터로
만들어 분류 모델(`notebooks/12_fault_scenario_classification.ipynb`)이 "여러 파라미터가
동시에 이렇게 움직이면 원인은 이거다"를 직접 추론하게 한다 — 하드코딩된 규칙이 아니라
데이터에서 학습된 판단이라는 뜻이다.

각 시나리오가 어떤 파라미터를 어느 방향으로 움직이는지는 `simulator/diagnosis.py`의 원인
매핑과 마찬가지로 반도체 공정 도메인 지식에 기반한 예시(illustrative)다 — 실제 fab의 정밀한
인과관계를 그대로 재현한 건 아니다.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .process_simulator import PROCESS_SPECS

NORMAL_LABEL = "normal"


@dataclass(frozen=True)
class FaultScenario:
    name: str  # 클래스 레이블로 쓰이는 영문 식별자
    label_ko: str  # 사람이 읽는 한글 이름
    shifts: dict[str, float]  # 파라미터 이름 -> 이동 방향(+1 위로 / -1 아래로)


FAULT_SCENARIOS: dict[str, list[FaultScenario]] = {
    "wafer_fabrication": [
        FaultScenario("heater_drift", "히터 드리프트", {"temperature": 1, "resistivity": 1}),
        FaultScenario("chamber_leak", "챔버 시일 누설", {"oxygen_concentration": 1, "temperature": -1}),
    ],
    "oxidation": [
        FaultScenario("furnace_overshoot", "퍼니스 온도 오버슈트", {"temperature": 1, "oxide_thickness": 1}),
        FaultScenario("timer_malfunction", "레시피 타이머 오작동", {"time": -1, "oxide_thickness": -1}),
    ],
    "photolithography": [
        FaultScenario("light_source_drift", "광원 파워 드리프트", {"exposure_energy": 1, "temperature": 1}),
        FaultScenario("stage_leveling_error", "웨이퍼 스테이지 레벨링 오차", {"focus_distance": 1, "temperature": -1}),
    ],
    "etching": [
        FaultScenario("mfc_drift", "MFC 캘리브레이션 드리프트", {"pressure": 1, "gas_flow": 1}),
        FaultScenario("rf_generator_fault", "RF 제너레이터 이상", {"power": -1, "pressure": 1}),
    ],
    "deposition": [
        FaultScenario("heater_overshoot", "히터 오버슈트", {"temperature": 1, "deposition_rate": 1}),
        FaultScenario("precursor_supply_fault", "전구체 공급 이상", {"deposition_rate": -1, "pressure": -1}),
    ],
    "metallization": [
        FaultScenario("power_supply_drift", "파워 서플라이 드리프트", {"current_density": 1, "temperature": 1}),
        FaultScenario("bath_thermostat_fault", "항온조 이상", {"temperature": -1, "plating_time": 1}),
    ],
    "eds": [
        FaultScenario("tester_calibration_fault", "테스터 캘리브레이션 이상", {"test_voltage": 1, "test_current": 1}),
        FaultScenario("probe_contact_fault", "프로브 접촉 불량", {"test_voltage": -1, "test_current": -1}),
    ],
    "packaging": [
        FaultScenario("feed_rate_fault", "장비 이송 속도 이상", {"dicing_speed": 1, "bonding_strength": -1}),
        FaultScenario("bonding_heater_fault", "본딩 히터 이상", {"temperature": -1, "bonding_strength": -1}),
    ],
}


def generate_fault_sample(
    process: str, scenario: FaultScenario | None, rng: np.random.Generator,
) -> dict[str, float]:
    """`scenario=None`이면 정상 샘플, 아니면 해당 시나리오 방향으로 관련 파라미터들을
    상관되게 이동시킨 샘플을 만든다. 이동 폭을 규격 폭의 15~90%로 넓게 두어, 아직 규격
    안이지만 미세하게 흔들리는 조기 신호부터 뚜렷하게 벗어난 값까지 섞이게 한다."""
    values: dict[str, float] = {}
    for spec in PROCESS_SPECS[process]:
        center = (spec.low + spec.high) / 2
        half_width = (spec.high - spec.low) / 2
        base_spread = half_width / 3

        direction = scenario.shifts.get(spec.name) if scenario else None
        if direction is None:
            value = rng.normal(center, base_spread)
        else:
            magnitude = rng.uniform(0.15, 0.9) * half_width
            value = center + direction * magnitude + rng.normal(0, base_spread * 0.5)
        values[spec.name] = float(value)
    return values


def generate_dataset(process: str, n_per_class: int, seed: int = 42) -> pd.DataFrame:
    """공정 하나에 대해 정상 + 시나리오별 샘플을 균형 있게 생성한다.

    반환되는 `fault_label` 컬럼이 정답 레이블이다 — `simulator/diagnosis.py`와 달리 이 모듈은
    "레이블이 있는 데이터"를 만드는 게 목적이라, 여기서 나온 데이터로 분류 모델을 지도학습할
    수 있다.
    """
    if process not in PROCESS_SPECS:
        raise ValueError(f"Unknown process: {process}. Valid: {list(PROCESS_SPECS)}")

    rng = np.random.default_rng(seed)
    scenarios = FAULT_SCENARIOS.get(process, [])
    rows: list[dict] = []

    for _ in range(n_per_class):
        row = generate_fault_sample(process, None, rng)
        row["fault_label"] = NORMAL_LABEL
        rows.append(row)

    for scenario in scenarios:
        for _ in range(n_per_class):
            row = generate_fault_sample(process, scenario, rng)
            row["fault_label"] = scenario.name
            rows.append(row)

    return pd.DataFrame(rows)


def scenario_label_ko(process: str, scenario_name: str) -> str:
    if scenario_name == NORMAL_LABEL:
        return "정상"
    for scenario in FAULT_SCENARIOS.get(process, []):
        if scenario.name == scenario_name:
            return scenario.label_ko
    raise ValueError(f"Unknown scenario '{scenario_name}' for process '{process}'")
