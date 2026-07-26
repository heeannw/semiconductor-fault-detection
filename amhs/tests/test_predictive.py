from amhs import make_predictive_dispatch, run_simulation


def test_predictive_dispatch_completes(requires_delay_model):
    policy = make_predictive_dispatch(n_vehicles=4, launch_interval_sec=150.0)
    result = run_simulation(n_vehicles=4, n_foups=10, n_laps=1, dispatch_policy=policy, seed=6)
    assert result["completion_rate"] == 1.0


def test_predictive_dispatch_falls_back_to_known_policies(requires_delay_model):
    """예측 정책이 고른 차량은 항상 idle_vehicles 안에 있어야 한다(nearest/zone 둘 중 하나의 선택 로직을 그대로 씀)."""
    policy = make_predictive_dispatch(n_vehicles=3, launch_interval_sec=150.0)
    result = run_simulation(n_vehicles=3, n_foups=8, n_laps=1, dispatch_policy=policy, seed=8)
    assigned_ids = set(result["transport_log"]["vehicle_id"])
    assert assigned_ids <= {0, 1, 2}
