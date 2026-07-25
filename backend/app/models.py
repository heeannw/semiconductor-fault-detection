from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProcessLog(Base):
    """공정 시뮬레이터가 생성한 합성 센서 판독값. 정상/이상 여부는 시뮬레이터 자체 판정(정상 범위 이탈 여부)이며, SECOM 학습 모델과는 무관하다."""

    __tablename__ = "process_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process: Mapped[str] = mapped_column(String(50), index=True)
    process_name_ko: Mapped[str] = mapped_column(String(50))
    params_json: Mapped[str] = mapped_column(Text)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class FaultRecord(Base):
    """SECOM 학습 모델(Isolation Forest / XGBoost / 앙상블)의 이상 탐지 결과 기록."""

    __tablename__ = "fault_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String(30))
    if_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    xgb_proba: Mapped[float | None] = mapped_column(Float, nullable=True)
    ensemble_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ModelMetric(Base):
    """/api/model/retrain 실행 이력과 성능 지표."""

    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(30))
    precision: Mapped[float] = mapped_column(Float)
    recall: Mapped[float] = mapped_column(Float)
    f1: Mapped[float] = mapped_column(Float)
    auroc: Mapped[float] = mapped_column(Float)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
