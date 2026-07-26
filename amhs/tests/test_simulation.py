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


def test_final_station_of_final_lap_creates_no_phantom_transport():
    """마지막 바퀴의 마지막 스테이션은 fab을 빠져나가는 지점이므로 반송이 생기면 안 된다."""
    result = run_simulation(n_vehicles=4, n_foups=6, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=1)
    assert result["expected_transports"] == 6 * (8 - 1)
    assert result["completed_transports"] == result["expected_transports"]


def test_small_stocker_capacity_still_completes_with_conwip_guard():
    """스토커를 작게 잡아도 CONWIP(max_wip 자동 설정)가 교착상태를 막아 완료율 1.0을 유지해야 한다."""
    result = run_simulation(
        n_vehicles=4, n_foups=10, n_laps=2, stocker_capacity=1,
        dispatch_policy=nearest_vehicle_dispatch, seed=9,
    )
    assert result["completion_rate"] == 1.0


def test_congestion_log_is_populated():
    result = run_simulation(n_vehicles=3, n_foups=8, n_laps=1, dispatch_policy=nearest_vehicle_dispatch, seed=5)
    congestion = result["congestion_log"]
    assert len(congestion) > 0
    assert set(congestion.columns) >= {"time", "station", "queue_length", "busy_vehicles"}
    assert (congestion["queue_length"] >= 0).all()
    assert result["max_queue_length"] >= 0


def test_tight_stocker_capacity_raises_max_queue_length_or_slows_flow():
    """스토커를 넉넉하게 주면 빡빡하게 줄 때보다 정체(최대 큐 길이 또는 평균 반송 시간)가 같거나 덜해야 한다."""
    tight = run_simulation(n_vehicles=3, n_foups=15, n_laps=2, stocker_capacity=1, dispatch_policy=nearest_vehicle_dispatch, seed=11)
    loose = run_simulation(n_vehicles=3, n_foups=15, n_laps=2, stocker_capacity=5, dispatch_policy=nearest_vehicle_dispatch, seed=11)
    assert loose["max_queue_length"] <= tight["max_queue_length"]
