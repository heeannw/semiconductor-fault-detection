import pytest

from simulator.diagnosis import DIAGNOSIS_TEMPLATES, diagnose
from simulator.process_simulator import PROCESS_SPECS


def test_every_parameter_has_both_directions_mapped():
    """diagnose()는 매핑이 없으면 조용히 건너뛴다 — 하나라도 빠지면 사용자에게 원인/조치 없이
    '이상'이라고만 뜨는 사각지대가 생기므로, 24개 파라미터 x 2방향 전체가 채워졌는지 검증한다."""
    missing = [
        (process, spec.name, direction)
        for process, specs in PROCESS_SPECS.items()
        for spec in specs
        for direction in ("high", "low")
        if (process, spec.name, direction) not in DIAGNOSIS_TEMPLATES
    ]
    assert missing == []


def test_in_spec_value_produces_no_diagnosis():
    result = diagnose("etching", {"pressure": 50, "gas_flow": 100, "power": 1000})
    assert result == []


def test_out_of_spec_high_produces_diagnosis_with_correct_direction():
    result = diagnose("etching", {"pressure": 150, "gas_flow": 100, "power": 1000})
    assert len(result) == 1
    d = result[0]
    assert d.parameter == "pressure"
    assert d.direction == "high"
    assert d.value == 150
    assert d.spec_low == 5 and d.spec_high == 100
    assert d.label and d.cause and d.impact and d.action


def test_out_of_spec_low_produces_diagnosis_with_correct_direction():
    result = diagnose("etching", {"pressure": -10, "gas_flow": 100, "power": 1000})
    assert len(result) == 1
    assert result[0].direction == "low"


def test_multiple_out_of_spec_params_produce_multiple_diagnoses():
    result = diagnose("etching", {"pressure": 150, "gas_flow": 5, "power": 1000})
    assert {d.parameter for d in result} == {"pressure", "gas_flow"}


def test_unknown_process_raises():
    with pytest.raises(ValueError):
        diagnose("not_a_process", {})


def test_missing_param_key_is_skipped_not_errored():
    result = diagnose("etching", {"pressure": 150})  # gas_flow/power 누락
    assert len(result) == 1
    assert result[0].parameter == "pressure"
