import numpy as np
import pytest

from simulator.fault_scenarios import (
    FAULT_SCENARIOS,
    NORMAL_LABEL,
    generate_dataset,
    generate_fault_sample,
    scenario_label_ko,
)
from simulator.process_simulator import PROCESS_SPECS


def test_every_process_has_at_least_one_scenario():
    assert set(FAULT_SCENARIOS) == set(PROCESS_SPECS)
    for process, scenarios in FAULT_SCENARIOS.items():
        assert len(scenarios) >= 1


def test_scenario_shift_keys_reference_real_parameters():
    for process, scenarios in FAULT_SCENARIOS.items():
        valid_params = {spec.name for spec in PROCESS_SPECS[process]}
        for scenario in scenarios:
            assert set(scenario.shifts) <= valid_params
            assert set(scenario.shifts.values()) <= {1, -1}


def test_generate_dataset_is_balanced_across_classes():
    df = generate_dataset("etching", n_per_class=20, seed=0)
    counts = df["fault_label"].value_counts()
    assert len(counts) == 3  # normal + 2 scenarios
    assert (counts == 20).all()


def test_generate_dataset_columns_match_process_params_plus_label():
    df = generate_dataset("etching", n_per_class=5, seed=0)
    expected = {spec.name for spec in PROCESS_SPECS["etching"]} | {"fault_label"}
    assert set(df.columns) == expected


def test_fault_sample_shifts_in_the_declared_direction_on_average():
    rng = np.random.default_rng(1)
    scenario = FAULT_SCENARIOS["etching"][0]  # mfc_drift: pressure+, gas_flow+
    normal_vals = [generate_fault_sample("etching", None, rng)["pressure"] for _ in range(500)]
    fault_vals = [generate_fault_sample("etching", scenario, rng)["pressure"] for _ in range(500)]
    assert np.mean(fault_vals) > np.mean(normal_vals)


def test_generate_dataset_unknown_process_raises():
    with pytest.raises(ValueError):
        generate_dataset("not_a_process", n_per_class=5)


def test_scenario_label_ko_normal_and_known_scenario():
    assert scenario_label_ko("etching", NORMAL_LABEL) == "정상"
    assert scenario_label_ko("etching", "mfc_drift") == "MFC 캘리브레이션 드리프트"


def test_scenario_label_ko_unknown_scenario_raises():
    with pytest.raises(ValueError):
        scenario_label_ko("etching", "not_a_scenario")
