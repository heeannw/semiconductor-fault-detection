def test_simulate_all_returns_eight_processes(client):
    res = client.post("/api/process/simulate", json={"process": "all"})
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) == 8
    processes = {log["process"] for log in logs}
    assert processes == {
        "wafer_fabrication", "oxidation", "photolithography", "etching",
        "deposition", "metallization", "eds", "packaging",
    }
    for log in logs:
        assert isinstance(log["is_anomaly"], bool)
        assert len(log["params"]) > 0


def test_simulate_single_process(client):
    res = client.post("/api/process/simulate", json={"process": "etching"})
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) == 1
    assert logs[0]["process"] == "etching"
    assert set(logs[0]["params"]) == {"pressure", "gas_flow", "power"}


def test_simulate_unknown_process_returns_400(client):
    res = client.post("/api/process/simulate", json={"process": "not_a_process"})
    assert res.status_code == 400


def test_process_status_reflects_latest_reading(client):
    client.post("/api/process/simulate", json={"process": "eds"})
    res = client.get("/api/process/status")
    assert res.status_code == 200
    eds_entries = [log for log in res.json() if log["process"] == "eds"]
    assert len(eds_entries) == 1


def test_process_history_filters_by_process(client):
    client.post("/api/process/simulate", json={"process": "packaging"})
    res = client.get("/api/process/history", params={"process": "packaging", "limit": 5})
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) >= 1
    assert all(log["process"] == "packaging" for log in logs)
