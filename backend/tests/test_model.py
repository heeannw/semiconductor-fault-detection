def test_feature_importance_returns_top_n(client, requires_models):
    res = client.get("/api/model/feature-importance", params={"top_n": 5})
    assert res.status_code == 200
    body = res.json()
    assert len(body["features"]) == 5
    assert len(body["importances"]) == 5
    # gain 기반 중요도는 내림차순이어야 한다
    assert body["importances"] == sorted(body["importances"], reverse=True)


def test_model_metrics_empty_list_before_any_retrain(client):
    res = client.get("/api/model/metrics")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_retrain_records_new_metric(client, requires_models):
    before = len(client.get("/api/model/metrics").json())

    res = client.post("/api/model/retrain")
    assert res.status_code == 200
    body = res.json()
    assert body["model_name"] == "xgboost"
    assert 0.0 <= body["f1"] <= 1.0
    assert 0.0 <= body["auroc"] <= 1.0

    after = client.get("/api/model/metrics").json()
    assert len(after) == before + 1
