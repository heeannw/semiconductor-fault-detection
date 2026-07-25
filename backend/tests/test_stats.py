def test_stats_summary_counts_increase_after_simulate(client):
    before = client.get("/api/stats/summary").json()["total_process_readings"]

    client.post("/api/process/simulate", json={"process": "oxidation"})

    after = client.get("/api/stats/summary").json()["total_process_readings"]
    assert after == before + 1


def test_stats_yield_is_between_0_and_1(client):
    client.post("/api/process/simulate", json={"process": "all"})
    res = client.get("/api/stats/yield")
    assert res.status_code == 200
    body = res.json()
    assert 0.0 <= body["overall_yield"] <= 1.0
    for rate in body["yield_by_process"].values():
        assert 0.0 <= rate <= 1.0
