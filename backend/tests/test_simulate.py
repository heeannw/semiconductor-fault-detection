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


def test_simulate_anomaly_includes_root_cause_diagnosis(client):
    res = client.post("/api/process/simulate", json={"process": "etching", "anomaly_ratio": 1.0})
    assert res.status_code == 200
    log = res.json()[0]
    assert log["is_anomaly"] is True
    assert len(log["diagnoses"]) > 0
    d = log["diagnoses"][0]
    assert d["direction"] in ("high", "low")
    assert d["label"] and d["cause"] and d["impact"] and d["action"]


def test_simulate_normal_has_no_diagnosis(client):
    res = client.post("/api/process/simulate", json={"process": "etching", "anomaly_ratio": 0.0})
    assert res.status_code == 200
    log = res.json()[0]
    assert log["is_anomaly"] is False
    assert log["diagnoses"] == []


def test_simulate_includes_predicted_fault_field(client):
    res = client.post("/api/process/simulate", json={"process": "etching"})
    assert res.status_code == 200
    log = res.json()[0]
    assert "predicted_fault" in log  # 모델이 없는 클론에서는 None이어야 하고, 필드 자체는 항상 있어야 함


def test_simulate_predicted_fault_shape_when_model_available(client, requires_fault_classifier):
    res = client.post("/api/process/simulate", json={"process": "etching", "anomaly_ratio": 1.0})
    assert res.status_code == 200
    log = res.json()[0]
    pf = log["predicted_fault"]
    assert pf is not None
    assert pf["predicted_label_ko"]
    assert 0.0 <= pf["confidence"] <= 1.0
    assert abs(sum(pf["probabilities"].values()) - 1.0) < 1e-6


def test_fault_demo_unknown_process_returns_400(client):
    res = client.post("/api/process/fault-demo", json={"process": "not_a_process"})
    assert res.status_code == 400


def test_fault_demo_returns_injected_truth_and_prediction(client, requires_fault_classifier):
    res = client.post("/api/process/fault-demo", json={"process": "etching"})
    assert res.status_code == 200
    body = res.json()
    assert body["process"] == "etching"
    assert body["injected_label_ko"]
    assert set(body["params"]) == {"pressure", "gas_flow", "power"}
    assert body["predicted_fault"]["predicted_label_ko"]


def test_fault_demo_correctly_identifies_injected_fault_most_of_the_time(client, requires_fault_classifier):
    """실제로 학습된 상관 패턴(fault_scenarios.py)을 주입하면, 독립 무작위 이탈과 달리
    분류기가 대부분 정답을 맞혀야 한다 — AI 예측 기능이 실제로 동작한다는 걸 확인한다.

    n=150, 임계값 0.65: 노트북 12의 held-out 정확도(etching 0.8133)를 기준으로 이항분포
    표준편차를 계산하면(np≈122, sd≈4.6) 0.65는 참 정확도보다 약 5.9 표준편차 아래라
    우연히 실패할 확률이 사실상 0에 가깝다 — 처음엔 n=30/임계값 0.7로 뒀다가 실제로
    60%(18/30)가 나와서 실패하는 걸 겪었고(모델은 200개 샘플 재검증에서 83.5%로 정상이었다),
    작은 표본으로 인한 우연한 실패였다는 걸 확인한 뒤 이렇게 고쳤다."""
    matches = 0
    n = 150
    for _ in range(n):
        res = client.post("/api/process/fault-demo", json={"process": "etching"})
        body = res.json()
        if body["predicted_fault"]["predicted_label"] == body["injected_label"]:
            matches += 1
    assert matches / n >= 0.65
