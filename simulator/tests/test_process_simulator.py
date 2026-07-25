import pytest

from simulator import PROCESS_SPECS, ProcessSimulator


@pytest.fixture
def sim():
    return ProcessSimulator(seed=42)


@pytest.mark.parametrize("process", list(PROCESS_SPECS))
def test_generate_sample_has_expected_params(sim, process):
    sample = sim.generate_sample(process, anomaly=False)
    assert sample["process"] == process
    expected_params = {spec.name for spec in PROCESS_SPECS[process]}
    actual_params = set(sample) - {"process", "process_name_ko", "timestamp", "is_anomaly"}
    assert actual_params == expected_params


@pytest.mark.parametrize("process", list(PROCESS_SPECS))
def test_normal_sample_within_spec_range(sim, process):
    for _ in range(20):
        sample = sim.generate_sample(process, anomaly=False)
        for spec in PROCESS_SPECS[process]:
            assert spec.low <= sample[spec.name] <= spec.high
        assert sample["is_anomaly"] is False


@pytest.mark.parametrize("process", list(PROCESS_SPECS))
def test_anomaly_sample_outside_spec_range(sim, process):
    for _ in range(20):
        sample = sim.generate_sample(process, anomaly=True)
        for spec in PROCESS_SPECS[process]:
            value = sample[spec.name]
            assert value < spec.low or value > spec.high
        assert sample["is_anomaly"] is True


def test_unknown_process_raises(sim):
    with pytest.raises(ValueError):
        sim.generate_sample("not_a_process")


def test_generate_batch_row_count(sim):
    df = sim.generate_batch("etching", n_samples=15, anomaly_ratio=0.1)
    assert len(df) == 15
    assert set(df["process"]) == {"etching"}


def test_generate_all_covers_every_process(sim):
    df = sim.generate_all(n_samples_per_process=3, anomaly_ratio=0.1)
    assert len(df) == 3 * len(PROCESS_SPECS)
    assert set(df["process"]) == set(PROCESS_SPECS)


def test_anomaly_ratio_is_approximately_respected():
    sim = ProcessSimulator(seed=123)
    df = sim.generate_batch("packaging", n_samples=3000, anomaly_ratio=0.1)
    observed_ratio = df["is_anomaly"].mean()
    assert 0.07 <= observed_ratio <= 0.13
