import pytest

from amhs.predictive import delay_model_available
from amhs.maintenance import pm_model_available


@pytest.fixture
def requires_delay_model():
    if not delay_model_available():
        pytest.skip("지연 예측 모델이 없습니다. notebooks/08_amhs_delay_prediction.ipynb를 먼저 실행하세요.")


@pytest.fixture
def requires_pm_model():
    if not pm_model_available():
        pytest.skip("예지보전 모델이 없습니다. notebooks/09_amhs_predictive_maintenance.ipynb를 먼저 실행하세요.")
