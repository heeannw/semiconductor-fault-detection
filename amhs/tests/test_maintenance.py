from amhs import make_maintenance_process, nearest_vehicle_dispatch, run_simulation


def test_maintenance_process_completes_simulation(requires_pm_model):
    log = []
    maint = make_maintenance_process(check_interval_sec=300.0, downtime_sec=600.0, anomaly_ratio=0.3, maintenance_log=log)
    result = run_simulation(
        n_vehicles=5, n_foups=10, n_laps=1,
        dispatch_policy=nearest_vehicle_dispatch, maintenance_process=maint, seed=42,
    )
    assert result["completion_rate"] == 1.0


def test_maintenance_events_recorded_with_high_anomaly_ratio(requires_pm_model):
    log = []
    maint = make_maintenance_process(check_interval_sec=300.0, downtime_sec=600.0, anomaly_ratio=0.5, maintenance_log=log)
    run_simulation(
        n_vehicles=5, n_foups=15, n_laps=2,
        dispatch_policy=nearest_vehicle_dispatch, maintenance_process=maint, seed=1,
    )
    assert len(log) > 0
    assert {e["event"] for e in log} <= {"down", "restored"}


def test_low_anomaly_ratio_triggers_fewer_events_than_high(requires_pm_model):
    """anomaly_ratio=0이어도 IsolationForest는 contamination(0.08)만큼 정상 샘플을 오탐하도록
    설계돼 있어 이벤트가 0건이라고 단정할 수 없다 — 대신 낮은 비율이 높은 비율보다
    적게 발동하는지를 비교한다."""
    low_log, high_log = [], []
    low = make_maintenance_process(check_interval_sec=300.0, downtime_sec=600.0, anomaly_ratio=0.0, maintenance_log=low_log)
    high = make_maintenance_process(check_interval_sec=300.0, downtime_sec=600.0, anomaly_ratio=0.6, maintenance_log=high_log)

    run_simulation(n_vehicles=4, n_foups=15, n_laps=2, dispatch_policy=nearest_vehicle_dispatch, maintenance_process=low, seed=2)
    run_simulation(n_vehicles=4, n_foups=15, n_laps=2, dispatch_policy=nearest_vehicle_dispatch, maintenance_process=high, seed=2)

    assert len(low_log) <= len(high_log)


def test_maintenance_reduces_effective_capacity_increases_cycle_time(requires_pm_model):
    """차량이 자주 고장 나면(다운타임이 늘면) 평균 반송 시간이 더 나빠지거나 같아야 한다."""
    no_maint = run_simulation(n_vehicles=5, n_foups=15, n_laps=2, dispatch_policy=nearest_vehicle_dispatch, seed=3)

    log = []
    heavy_maint = make_maintenance_process(check_interval_sec=200.0, downtime_sec=1500.0, anomaly_ratio=0.6, maintenance_log=log)
    with_maint = run_simulation(
        n_vehicles=5, n_foups=15, n_laps=2,
        dispatch_policy=nearest_vehicle_dispatch, maintenance_process=heavy_maint, seed=3,
    )
    assert with_maint["avg_cycle_time_sec"] >= no_maint["avg_cycle_time_sec"]
