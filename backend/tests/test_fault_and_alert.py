def test_fault_detail_404_for_unknown_id(client):
    res = client.get("/api/fault/999999")
    assert res.status_code == 404


def test_alert_send_404_for_unknown_fault(client):
    res = client.post("/api/alert/send", json={"fault_id": 999999})
    assert res.status_code == 404


def test_alert_send_marks_fault_as_sent(client, requires_models, secom_sample):
    fault_id = client.post("/api/ai/detect", json={"features": secom_sample}).json()["fault_id"]

    before = client.get(f"/api/fault/{fault_id}").json()
    assert before["alert_sent"] is False

    send_res = client.post("/api/alert/send", json={"fault_id": fault_id})
    assert send_res.status_code == 200
    assert send_res.json() == {"fault_id": fault_id, "alert_sent": True}

    after = client.get(f"/api/fault/{fault_id}").json()
    assert after["alert_sent"] is True


def test_fault_list_supports_is_anomaly_filter(client):
    res = client.get("/api/fault/list", params={"is_anomaly": True, "limit": 100})
    assert res.status_code == 200
    assert all(f["is_anomaly"] is True for f in res.json())
