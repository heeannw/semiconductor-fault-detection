import numpy as np

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


def test_stocker_capacity_affects_observed_queue_length():
    """stocker_capacity를 바꾸면 관측되는 최대 큐 길이도 달라져야 한다(둘이 똑같으면 그 파라미터가
    사실상 아무 효과가 없다는 뜻이므로 회귀 감지용으로 충분한 약한 체크).

    참고로 "타이트한 버퍼일수록 큐가 더 짧다"는 직관과 반대로, 이 시뮬레이션에서는 타이트한
    버퍼가 back-pressure를 일찍 걸어 WIP 자체를 눌러버리는 반면 넉넉한 버퍼는 back-pressure가
    늦게 걸리는 대신 그 사이 대기열이 더 크게 쌓일 여유를 준다 — 절대적인 대소 관계를
    단정하지 않고 "capacity가 관측치에 실제로 영향을 준다"만 확인한다."""
    tight = run_simulation(n_vehicles=3, n_foups=15, n_laps=2, stocker_capacity=1, dispatch_policy=nearest_vehicle_dispatch, seed=11)
    loose = run_simulation(n_vehicles=3, n_foups=15, n_laps=2, stocker_capacity=5, dispatch_policy=nearest_vehicle_dispatch, seed=11)
    assert tight["max_queue_length"] != loose["max_queue_length"]
    assert tight["max_queue_length"] >= 0
    assert loose["max_queue_length"] >= 0


def test_transport_log_has_hot_lot_column():
    result = run_simulation(n_vehicles=3, n_foups=6, n_laps=1, hot_lot_ratio=0.3, dispatch_policy=nearest_vehicle_dispatch, seed=1)
    assert "is_hot_lot" in result["transport_log"].columns
    assert result["transport_log"]["is_hot_lot"].isin([True, False]).all()


def test_zero_hot_lot_ratio_produces_no_hot_lots():
    result = run_simulation(n_vehicles=3, n_foups=6, n_laps=1, hot_lot_ratio=0.0, dispatch_policy=nearest_vehicle_dispatch, seed=1)
    assert not result["transport_log"]["is_hot_lot"].any()
    assert np.isnan(result["avg_hot_lot_cycle_time_sec"])


def test_hot_lots_get_shorter_cycle_time_under_contention():
    """대기 경쟁이 없으면(차량 여유) hot lot이든 아니든 순서를 바꿀 게 없어 차이가 안 난다 —
    그래서 일부러 차량을 적게, 투입 간격을 짧게 줘서 여러 반송 요청이 동시에 대기하는
    상황을 만든다. 노이즈를 줄이려고 여러 시드에 걸쳐 평균낸다."""
    hot_means, normal_means = [], []
    for seed in range(15):
        result = run_simulation(
            n_vehicles=2, n_foups=20, n_laps=1, foup_launch_interval_sec=20.0,
            hot_lot_ratio=0.3, dispatch_policy=nearest_vehicle_dispatch, seed=seed,
        )
        if result["completion_rate"] == 1.0:
            hot_means.append(result["avg_hot_lot_cycle_time_sec"])
            normal_means.append(result["avg_normal_lot_cycle_time_sec"])

    assert len(hot_means) >= 5  # 완료율 1.0인 실행이 충분히 있어야 비교가 의미 있다
    assert np.nanmean(hot_means) < np.nanmean(normal_means)
