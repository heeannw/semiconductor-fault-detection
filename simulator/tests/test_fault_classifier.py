import pytest

from simulator.fault_classifier import fault_classifier_available, predict_fault

requires_fault_model = pytest.mark.skipif(
    not fault_classifier_available("etching"),
    reason="fault classifier not trained — run notebooks/12_fault_scenario_classification.ipynb first",
)


def test_fault_classifier_available_false_for_unknown_process():
    assert fault_classifier_available("not_a_process") is False


def test_predict_fault_returns_none_when_model_missing(monkeypatch):
    monkeypatch.setattr("simulator.fault_classifier.fault_classifier_available", lambda process: False)
    assert predict_fault("etching", {"pressure": 50, "gas_flow": 100, "power": 1000}) is None


@requires_fault_model
def test_predict_fault_returns_prediction_with_probabilities_summing_to_one():
    result = predict_fault("etching", {"pressure": 150, "gas_flow": 250, "power": 900})
    assert result is not None
    assert result.process == "etching"
    assert result.predicted_label_ko
    assert 0.0 <= result.confidence <= 1.0
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-6


@requires_fault_model
def test_predict_fault_normal_reading_predicts_normal_with_high_confidence():
    result = predict_fault("etching", {"pressure": 52, "gas_flow": 105, "power": 1000})
    assert result.predicted_label_ko == "정상"
