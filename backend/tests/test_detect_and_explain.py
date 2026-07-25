def test_detect_returns_all_three_verdicts(client, requires_models, secom_sample):
    res = client.post("/api/ai/detect", json={"features": secom_sample})
    assert res.status_code == 200
    body = res.json()
    for key in (
        "is_anomaly_isolation_forest", "is_anomaly_xgboost", "is_anomaly_ensemble",
        "if_score", "xgb_proba", "ensemble_score", "fault_id",
    ):
        assert key in body
    # 앙상블은 IF 또는 XGBoost 둘 중 하나라도 True면 True (투표 방식)
    assert body["is_anomaly_ensemble"] == (body["is_anomaly_isolation_forest"] or body["is_anomaly_xgboost"])


def test_detect_missing_features_returns_400(client, requires_models):
    res = client.post("/api/ai/detect", json={"features": {"feature_1": 0.0}})
    assert res.status_code == 400


def test_detect_creates_fault_record(client, requires_models, secom_sample):
    res = client.post("/api/ai/detect", json={"features": secom_sample})
    fault_id = res.json()["fault_id"]

    detail = client.get(f"/api/fault/{fault_id}")
    assert detail.status_code == 200
    assert detail.json()["model"] == "ensemble"


def test_explain_returns_signed_contributors(client, requires_models, secom_sample):
    res = client.post("/api/ai/explain", json={"features": secom_sample})
    assert res.status_code == 200
    body = res.json()
    assert "base_value" in body
    assert len(body["top_contributors"]) == 10
    for c in body["top_contributors"]:
        assert {"feature", "shap_value", "feature_value"} <= set(c)

    # 절대값 기준 내림차순 정렬이어야 한다
    abs_values = [abs(c["shap_value"]) for c in body["top_contributors"]]
    assert abs_values == sorted(abs_values, reverse=True)


def test_explain_features_are_valid_secom_features(client, requires_models, secom_sample):
    """explain이 반환하는 피처 이름은 실제 학습에 쓰인 피처 공간(feature-importance와 동일 출처)에 속해야 한다."""
    importance_res = client.get("/api/model/feature-importance", params={"top_n": 1000}).json()
    known_features = set(importance_res["features"])

    explain_res = client.post("/api/ai/explain", json={"features": secom_sample}).json()
    for c in explain_res["top_contributors"]:
        assert c["feature"] in known_features
