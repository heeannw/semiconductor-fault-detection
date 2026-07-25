import json
import os
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]

# 앱을 import하기 전에 테스트 전용 SQLite 파일을 가리키도록 설정 (실 서비스 DB를 건드리지 않음)
_tmp_dir = tempfile.mkdtemp(prefix="semisense_test_")
os.environ["SEMISENSE_DATABASE_URL"] = f"sqlite:///{Path(_tmp_dir) / 'test.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402

DATA_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _models_ready() -> bool:
    required = ["isolation_forest.joblib", "xgboost.joblib", "feature_columns.joblib", "xgboost_threshold.joblib"]
    return all((MODELS_DIR / f).exists() for f in required)


@pytest.fixture(scope="session")
def secom_sample():
    """X_test.csv에서 뽑은 실제 SECOM 피처 벡터 1건. 전처리 데이터가 없으면 스킵."""
    csv_path = DATA_DIR / "X_test.csv"
    if not csv_path.exists():
        pytest.skip("data/processed/X_test.csv가 없습니다. notebooks/02_preprocessing.ipynb를 먼저 실행하세요.")

    import pandas as pd

    row = pd.read_csv(csv_path).iloc[0]
    return row.to_dict()


@pytest.fixture
def requires_models():
    """모델 아티팩트가 필요한 테스트에서 명시적으로 요청하는 스킵 가드."""
    if not _models_ready():
        pytest.skip("모델 아티팩트(models/*.joblib)가 없습니다. notebooks/03_modeling.ipynb를 먼저 실행하세요.")
