from amhs import fcfs_dispatch, nearest_vehicle_dispatch, run_simulation, zone_based_dispatch


def test_run_simulation_completes_all_transports():
    result = run_simulation(n_vehicles=4, n_foups=6, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=1)
    assert result["completion_rate"] == 1.0
    assert result["completed_transports"] == result["expected_transports"]


def test_transport_log_has_expected_columns():
    result = run_simulation(n_vehicles=3, n_foups=4, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=2)
    log = result["transport_log"]
    assert set(log.columns) >= {"foup_id", "from", "to", "cycle_time_sec", "vehicle_id"}
    assert (log["cycle_time_sec"] > 0).all()


def test_more_vehicles_do_not_increase_cycle_time():
    """차량을 늘리면(다른 조건 동일) 평균 반송 시간이 늘어나지는 않아야 한다."""
    few = run_simulation(n_vehicles=2, n_foups=10, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=3)
    many = run_simulation(n_vehicles=8, n_foups=10, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=3)
    assert many["avg_cycle_time_sec"] <= few["avg_cycle_time_sec"]


def test_all_dispatch_policies_run_without_error():
    for policy in (nearest_vehicle_dispatch, fcfs_dispatch, zone_based_dispatch):
        result = run_simulation(n_vehicles=4, n_foups=5, n_laps=1, dispatch_policy=policy, seed=4)
        assert result["completion_rate"] == 1.0


def test_seed_is_reproducible():
    a = run_simulation(n_vehicles=3, n_foups=5, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=7)
    b = run_simulation(n_vehicles=3, n_foups=5, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=7)
    assert a["avg_cycle_time_sec"] == b["avg_cycle_time_sec"]
