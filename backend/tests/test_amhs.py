def test_amhs_stations_returns_eight(client):
    res = client.get("/api/amhs/stations")
    assert res.status_code == 200
    stations = res.json()
    assert len(stations) == 8
    assert [s["index"] for s in stations] == list(range(8))


def test_amhs_simulate_nearest(client):
    res = client.post("/api/amhs/simulate", json={"n_vehicles": 4, "n_foups": 8, "n_laps": 1, "policy": "nearest"})
    assert res.status_code == 200
    body = res.json()
    assert body["completion_rate"] == 1.0
    assert body["avg_cycle_time_sec"] > 0
    assert body["max_queue_length"] >= 0
    assert body["avg_hot_lot_cycle_time_sec"] is None  # hot_lot_ratio 기본값 0


def test_amhs_simulate_with_hot_lots(client):
    res = client.post(
        "/api/amhs/simulate",
        json={"n_vehicles": 2, "n_foups": 8, "n_laps": 1, "foup_launch_interval_sec": 20.0, "hot_lot_ratio": 0.3},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["avg_hot_lot_cycle_time_sec"] is not None or body["avg_normal_lot_cycle_time_sec"] is not None


def test_amhs_simulate_rejects_out_of_range_hot_lot_ratio(client):
    res = client.post("/api/amhs/simulate", json={"hot_lot_ratio": 1.5})
    assert res.status_code == 400


def test_amhs_simulate_predictive_policy(client, requires_delay_model):
    res = client.post("/api/amhs/simulate", json={"n_vehicles": 4, "n_foups": 8, "n_laps": 1, "policy": "predictive"})
    assert res.status_code == 200
    assert res.json()["policy"] == "predictive"


def test_amhs_simulate_rejects_out_of_range_stocker_capacity(client):
    res = client.post("/api/amhs/simulate", json={"stocker_capacity": 0})
    assert res.status_code == 400


def test_amhs_simulate_all_policies(client):
    for policy in ("nearest", "fcfs", "zone"):
        res = client.post("/api/amhs/simulate", json={"n_vehicles": 3, "n_foups": 6, "n_laps": 1, "policy": policy})
        assert res.status_code == 200
        assert res.json()["policy"] == policy


def test_amhs_simulate_unknown_policy_returns_400(client):
    res = client.post("/api/amhs/simulate", json={"policy": "not_a_policy"})
    assert res.status_code == 400


def test_amhs_simulate_rejects_out_of_range_n_vehicles(client):
    res = client.post("/api/amhs/simulate", json={"n_vehicles": 0})
    assert res.status_code == 400
    res = client.post("/api/amhs/simulate", json={"n_vehicles": 21})
    assert res.status_code == 400


def test_amhs_simulate_replay_returns_stations_and_events(client):
    res = client.post(
        "/api/amhs/simulate/replay",
        json={"n_vehicles": 3, "n_foups": 6, "n_laps": 1, "policy": "nearest"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["n_stations"] == 8
    assert len(body["stations"]) == 8
    assert body["sim_duration_sec"] > 0
    assert len(body["events"]) > 0
    event = body["events"][0]
    assert event["from_station"] != event["to_station"]
    assert event["completed_at"] > event["requested_at"]
    assert isinstance(event["vehicle_id"], int)


def test_amhs_simulate_replay_rejects_unknown_policy(client):
    res = client.post("/api/amhs/simulate/replay", json={"policy": "not_a_policy"})
    assert res.status_code == 400
