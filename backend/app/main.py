import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from simulator import PROCESS_SPECS, ProcessSimulator  # noqa: E402

from . import ml, training  # noqa: E402
from .database import Base, SessionLocal, engine, get_db  # noqa: E402
from .models import FaultRecord, ModelMetric, ProcessLog  # noqa: E402
from .schemas import (  # noqa: E402
    AlertSendRequest,
    AlertSendResponse,
    DetectResponse,
    FaultRecordOut,
    FeatureImportanceOut,
    HealthResponse,
    ModelMetricOut,
    ProcessLogOut,
    RetrainResponse,
    SecomDetectRequest,
    SimulateRequest,
    StatsSummary,
    YieldStats,
)

simulator = ProcessSimulator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SemiSense API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",  # CRA 기본 포트 (설계 문서 기준)
        "http://localhost:5173", "http://127.0.0.1:5173",  # Vite 기본 포트 (실제 사용 중인 프론트엔드 dev 서버)
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _process_log_to_out(log: ProcessLog) -> ProcessLogOut:
    return ProcessLogOut(
        id=log.id,
        process=log.process,
        process_name_ko=log.process_name_ko,
        params=json.loads(log.params_json),
        is_anomaly=log.is_anomaly,
        created_at=log.created_at,
    )


@app.post("/api/process/simulate", response_model=list[ProcessLogOut])
def simulate_process(req: SimulateRequest, db: Session = Depends(get_db)):
    if req.process != "all" and req.process not in PROCESS_SPECS:
        raise HTTPException(status_code=400, detail=f"Unknown process: {req.process}. Valid: {list(PROCESS_SPECS)} or 'all'")

    processes = list(PROCESS_SPECS) if req.process == "all" else [req.process]
    logs: list[ProcessLog] = []
    for process in processes:
        sample = simulator.generate_sample(process, anomaly_ratio=req.anomaly_ratio)
        params = {
            k: v for k, v in sample.items()
            if k not in ("process", "process_name_ko", "timestamp", "is_anomaly")
        }
        log = ProcessLog(
            process=sample["process"],
            process_name_ko=sample["process_name_ko"],
            params_json=json.dumps(params),
            is_anomaly=sample["is_anomaly"],
        )
        db.add(log)
        logs.append(log)
    db.commit()
    for log in logs:
        db.refresh(log)
    return [_process_log_to_out(log) for log in logs]


@app.post("/api/ai/detect", response_model=DetectResponse)
def detect_anomaly(req: SecomDetectRequest, db: Session = Depends(get_db)):
    try:
        result = ml.predict(req.features)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = FaultRecord(
        model="ensemble",
        if_score=result["if_score"],
        xgb_proba=result["xgb_proba"],
        ensemble_score=result["ensemble_score"],
        is_anomaly=result["is_anomaly_ensemble"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return DetectResponse(**result, fault_id=record.id)


@app.get("/api/process/status", response_model=list[ProcessLogOut])
def process_status(db: Session = Depends(get_db)):
    logs = []
    for process in PROCESS_SPECS:
        latest = (
            db.query(ProcessLog)
            .filter(ProcessLog.process == process)
            .order_by(ProcessLog.created_at.desc())
            .first()
        )
        if latest is not None:
            logs.append(latest)
    return [_process_log_to_out(log) for log in logs]


@app.get("/api/process/history", response_model=list[ProcessLogOut])
def process_history(process: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(ProcessLog)
    if process is not None:
        query = query.filter(ProcessLog.process == process)
    logs = query.order_by(ProcessLog.created_at.desc()).limit(limit).all()
    return [_process_log_to_out(log) for log in logs]


@app.get("/api/fault/list", response_model=list[FaultRecordOut])
def fault_list(is_anomaly: bool | None = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(FaultRecord)
    if is_anomaly is not None:
        query = query.filter(FaultRecord.is_anomaly == is_anomaly)
    return query.order_by(FaultRecord.detected_at.desc()).limit(limit).all()


@app.get("/api/fault/{fault_id}", response_model=FaultRecordOut)
def fault_detail(fault_id: int, db: Session = Depends(get_db)):
    record = db.get(FaultRecord, fault_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Fault record not found")
    return record


@app.post("/api/alert/send", response_model=AlertSendResponse)
def alert_send(req: AlertSendRequest, db: Session = Depends(get_db)):
    record = db.get(FaultRecord, req.fault_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Fault record not found")
    record.alert_sent = True
    db.commit()
    return AlertSendResponse(fault_id=record.id, alert_sent=True)


@app.get("/api/stats/summary", response_model=StatsSummary)
def stats_summary(db: Session = Depends(get_db)):
    total_readings = db.query(func.count(ProcessLog.id)).scalar() or 0
    total_anomalies = (
        db.query(func.count(ProcessLog.id)).filter(ProcessLog.is_anomaly.is_(True)).scalar() or 0
    )
    total_faults = (
        db.query(func.count(FaultRecord.id)).filter(FaultRecord.is_anomaly.is_(True)).scalar() or 0
    )
    by_process = dict(
        db.query(ProcessLog.process, func.count(ProcessLog.id)).group_by(ProcessLog.process).all()
    )
    return StatsSummary(
        total_process_readings=total_readings,
        total_process_anomalies=total_anomalies,
        total_faults_detected=total_faults,
        readings_by_process=by_process,
    )


@app.get("/api/stats/yield", response_model=YieldStats)
def stats_yield(db: Session = Depends(get_db)):
    def yield_rate(process: str | None) -> float:
        query = db.query(ProcessLog)
        if process is not None:
            query = query.filter(ProcessLog.process == process)
        total = query.count()
        if total == 0:
            return 1.0
        anomalies = query.filter(ProcessLog.is_anomaly.is_(True)).count()
        return round(1 - anomalies / total, 4)

    return YieldStats(
        overall_yield=yield_rate(None),
        yield_by_process={process: yield_rate(process) for process in PROCESS_SPECS},
    )


@app.post("/api/model/retrain", response_model=RetrainResponse)
def model_retrain(db: Session = Depends(get_db)):
    try:
        metrics = training.retrain_and_evaluate()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    ml.reload_models()

    record = ModelMetric(**metrics)
    db.add(record)
    db.commit()
    db.refresh(record)

    return RetrainResponse(**metrics, trained_at=record.trained_at)


@app.get("/api/model/metrics", response_model=list[ModelMetricOut])
def model_metrics(limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(ModelMetric)
        .order_by(ModelMetric.trained_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/api/model/feature-importance", response_model=FeatureImportanceOut)
def model_feature_importance(top_n: int = 20):
    try:
        return ml.top_feature_importance(top_n)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", models_loaded=ml.models_available())
