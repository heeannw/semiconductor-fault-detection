import pytest

from amhs import VEHICLE_HEALTH_SPECS, VehicleHealthSimulator


@pytest.fixture
def sim():
    return VehicleHealthSimulator(seed=42)


def test_normal_sample_within_spec_range(sim):
    for _ in range(30):
        sample = sim.generate_sample(vehicle_id=0, anomaly=False)
        for spec in VEHICLE_HEALTH_SPECS:
            assert spec.low <= sample[spec.name] <= spec.high
        assert sample["is_anomaly"] is False


def test_anomaly_sample_outside_spec_range(sim):
    for _ in range(30):
        sample = sim.generate_sample(vehicle_id=0, anomaly=True)
        for spec in VEHICLE_HEALTH_SPECS:
            value = sample[spec.name]
            assert value < spec.low or value > spec.high
        assert sample["is_anomaly"] is True


def test_generate_fleet_shape(sim):
    df = sim.generate_fleet(n_vehicles=4, n_samples_per_vehicle=10, anomaly_ratio=0.1)
    assert len(df) == 40
    assert set(df["vehicle_id"]) == {0, 1, 2, 3}


def test_anomaly_ratio_is_approximately_respected():
    sim = VehicleHealthSimulator(seed=123)
    df = sim.generate_batch(vehicle_id=0, n_samples=3000, anomaly_ratio=0.1)
    observed_ratio = df["is_anomaly"].mean()
    assert 0.07 <= observed_ratio <= 0.13
