"""POST /api/process/explain 테스트.

실제 Gemini API를 호출하지 않는다 — 무료 등급이라도 자동화 테스트에서 외부 네트워크
호출을 하는 건 느리고 불안정하고 (테스트를 자주 돌리면) 쿼터를 갉아먹는다. 대신
`backend.app.llm_explain`의 `gemini_available`/`explain`을 monkeypatch로 가짜 함수로
바꿔서, "그 함수들이 올바른 근거(diagnoses/prediction)와 함께 호출되는지"와 "그 결과가
API 응답으로 올바르게 나오는지"만 검증한다.
"""


def test_process_explain_unknown_process_returns_400(client):
    res = client.post(
        "/api/process/explain",
        json={"process": "not_a_process", "params": {}, "question": "왜 이상이야?"},
    )
    assert res.status_code == 400


def test_process_explain_without_key_returns_503(client, monkeypatch):
    monkeypatch.setattr("backend.app.llm_explain.gemini_available", lambda: False)
    res = client.post(
        "/api/process/explain",
        json={"process": "etching", "params": {"pressure": 150, "gas_flow": 100, "power": 1000}, "question": "왜?"},
    )
    assert res.status_code == 503


def test_process_explain_returns_grounded_answer(client, monkeypatch):
    captured = {}

    def fake_explain(process_name_ko, params, diagnoses, prediction, question):
        captured["process_name_ko"] = process_name_ko
        captured["params"] = params
        captured["diagnoses"] = diagnoses
        captured["question"] = question
        return "압력이 규격 상한을 넘었습니다."

    monkeypatch.setattr("backend.app.llm_explain.gemini_available", lambda: True)
    monkeypatch.setattr("backend.app.llm_explain.explain", fake_explain)

    res = client.post(
        "/api/process/explain",
        json={
            "process": "etching",
            "params": {"pressure": 150, "gas_flow": 100, "power": 1000},
            "question": "이 상황 좀 설명해줘",
        },
    )
    assert res.status_code == 200
    assert res.json()["answer"] == "압력이 규격 상한을 넘었습니다."

    # main.py가 클라이언트 입력을 그대로 믿지 않고 서버에서 diagnose()를 다시 계산해
    # 근거로 넘겼는지 확인 — pressure=150은 규격(5~100)을 벗어나므로 진단이 비어있으면 안 됨
    assert captured["process_name_ko"] == "식각"
    assert len(captured["diagnoses"]) > 0
    assert captured["question"] == "이 상황 좀 설명해줘"


def test_process_explain_gemini_failure_returns_502(client, monkeypatch):
    def failing_explain(*args, **kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr("backend.app.llm_explain.gemini_available", lambda: True)
    monkeypatch.setattr("backend.app.llm_explain.explain", failing_explain)

    res = client.post(
        "/api/process/explain",
        json={"process": "etching", "params": {"pressure": 150, "gas_flow": 100, "power": 1000}, "question": "왜?"},
    )
    assert res.status_code == 502
