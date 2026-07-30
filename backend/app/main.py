import json
import random
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from simulator import (  # noqa: E402
    FAULT_SCENARIOS,
    PROCESS_NAMES_KO,
    PROCESS_SPECS,
    ProcessSimulator,
    diagnose,
    fault_classifier_available,
    generate_fault_sample,
    predict_fault,
    scenario_label_ko,
)

import amhs  # noqa: E402

from . import ml, training  # noqa: E402
from .database import Base, SessionLocal, engine, get_db  # noqa: E402
from .models import FaultRecord, ModelMetric, ProcessLog  # noqa: E402
from .schemas import (  # noqa: E402
    AlertSendRequest,
    AlertSendResponse,
    AmhsReplayResponse,
    AmhsSimulateRequest,
    AmhsSimulateResponse,
    AmhsStationOut,
    AmhsTransportEvent,
    DetectResponse,
    DiagnosisOut,
    ExplainResponse,
    FaultDemoRequest,
    FaultDemoResponse,
    FaultPredictionOut,
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

AMHS_POLICIES = {
    "nearest": amhs.nearest_vehicle_dispatch,
    "fcfs": amhs.fcfs_dispatch,
    "zone": amhs.zone_based_dispatch,
}

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
    params = json.loads(log.params_json)
    diagnoses = [
        DiagnosisOut(
            parameter=d.parameter, value=d.value, spec_low=d.spec_low, spec_high=d.spec_high,
            unit=d.unit, direction=d.direction, label=d.label, cause=d.cause,
            impact=d.impact, action=d.action,
        )
        for d in diagnose(log.process, params)
    ]
    fault_prediction = predict_fault(log.process, params)
    predicted_fault = (
        FaultPredictionOut(
            predicted_label=fault_prediction.predicted_label,
            predicted_label_ko=fault_prediction.predicted_label_ko,
            confidence=fault_prediction.confidence,
            probabilities=fault_prediction.probabilities,
        )
        if fault_prediction is not None
        else None
    )
    return ProcessLogOut(
        id=log.id,
        process=log.process,
        process_name_ko=log.process_name_ko,
        params=params,
        diagnoses=diagnoses,
        predicted_fault=predicted_fault,
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


@app.post("/api/process/fault-demo", response_model=FaultDemoResponse)
def process_fault_demo(req: FaultDemoRequest):
    """`POST /api/process/simulate`가 파라미터를 하나씩 독립적으로 무작위 이탈시키는 것과
    달리, 이 엔드포인트는 `simulator/fault_scenarios.py`가 정의한 **상관된 다중 파라미터
    패턴**(실제로 AI 원인 분류 모델을 학습시킨 바로 그 패턴)을 주입해, "AI 예측 원인" 기능이
    실제로 무엇을 잘 잡아내는지 보여준다. 독립 무작위 이탈은 학습된 어떤 패턴과도 안 맞아
    분류기가 대부분 '정상'으로 오판하므로(README에 정직하게 기록) 이 엔드포인트가 필요하다."""
    if req.process not in PROCESS_SPECS:
        raise HTTPException(status_code=400, detail=f"Unknown process: {req.process}. Valid: {list(PROCESS_SPECS)}")
    if not fault_classifier_available(req.process):
        raise HTTPException(
            status_code=503,
            detail="공정 원인 분류 모델이 없습니다. notebooks/12_fault_scenario_classification.ipynb를 먼저 실행하세요.",
        )

    rng = np.random.default_rng()
    scenarios = FAULT_SCENARIOS.get(req.process, [])
    scenario = random.choice([None, *scenarios])

    params = generate_fault_sample(req.process, scenario, rng)
    injected_label = scenario.name if scenario else "normal"

    prediction = predict_fault(req.process, params)

    return FaultDemoResponse(
        process=req.process,
        process_name_ko=PROCESS_NAMES_KO[req.process],
        params=params,
        injected_label=injected_label,
        injected_label_ko=scenario_label_ko(req.process, injected_label),
        predicted_fault=FaultPredictionOut(
            predicted_label=prediction.predicted_label,
            predicted_label_ko=prediction.predicted_label_ko,
            confidence=prediction.confidence,
            probabilities=prediction.probabilities,
        ),
    )


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


@app.post("/api/ai/explain", response_model=ExplainResponse)
def explain_detection(req: SecomDetectRequest):
    try:
        result = ml.explain(req.features)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ExplainResponse(**result)


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


@app.get("/api/amhs/stations", response_model=list[AmhsStationOut])
def amhs_stations():
    return [
        AmhsStationOut(name=s.name, name_ko=s.name_ko, index=s.index)
        for s in sorted(amhs.STATIONS.values(), key=lambda s: s.index)
    ]


def _validate_amhs_request(req: AmhsSimulateRequest) -> None:
    valid_policies = list(AMHS_POLICIES) + ["predictive"]
    if req.policy not in valid_policies:
        raise HTTPException(status_code=400, detail=f"Unknown policy: {req.policy}. Valid: {valid_policies}")
    if not (1 <= req.n_vehicles <= 20):
        raise HTTPException(status_code=400, detail="n_vehicles must be between 1 and 20")
    if not (1 <= req.n_foups <= 100):
        raise HTTPException(status_code=400, detail="n_foups must be between 1 and 100")
    if not (1 <= req.stocker_capacity <= 20):
        raise HTTPException(status_code=400, detail="stocker_capacity must be between 1 and 20")
    if not (0.0 <= req.hot_lot_ratio <= 1.0):
        raise HTTPException(status_code=400, detail="hot_lot_ratio must be between 0.0 and 1.0")


def _resolve_amhs_dispatch_policy(req: AmhsSimulateRequest):
    if req.policy == "predictive":
        if not amhs.delay_model_available():
            raise HTTPException(
                status_code=503,
                detail="지연 예측 모델이 없습니다. notebooks/08_amhs_delay_prediction.ipynb를 먼저 실행하세요.",
            )
        return amhs.make_predictive_dispatch(
            n_vehicles=req.n_vehicles, launch_interval_sec=req.foup_launch_interval_sec,
        )
    return AMHS_POLICIES[req.policy]


@app.post("/api/amhs/simulate", response_model=AmhsSimulateResponse)
def amhs_simulate(req: AmhsSimulateRequest):
    _validate_amhs_request(req)
    dispatch_policy = _resolve_amhs_dispatch_policy(req)

    result = amhs.run_simulation(
        n_vehicles=req.n_vehicles,
        n_foups=req.n_foups,
        n_laps=req.n_laps,
        foup_launch_interval_sec=req.foup_launch_interval_sec,
        stocker_capacity=req.stocker_capacity,
        hot_lot_ratio=req.hot_lot_ratio,
        dispatch_policy=dispatch_policy,
        seed=req.seed,
    )

    def _clean(value: float) -> float | None:
        return None if value != value else value  # NaN != NaN

    return AmhsSimulateResponse(
        policy=req.policy,
        n_vehicles=req.n_vehicles,
        completion_rate=result["completion_rate"],
        avg_cycle_time_sec=result["avg_cycle_time_sec"],
        p95_cycle_time_sec=result["p95_cycle_time_sec"],
        avg_vehicle_utilization=result["avg_vehicle_utilization"],
        avg_hot_lot_cycle_time_sec=_clean(result["avg_hot_lot_cycle_time_sec"]),
        avg_normal_lot_cycle_time_sec=_clean(result["avg_normal_lot_cycle_time_sec"]),
        max_queue_length=result["max_queue_length"],
        completed_transports=result["completed_transports"],
    )


@app.post("/api/amhs/simulate/replay", response_model=AmhsReplayResponse)
def amhs_simulate_replay(req: AmhsSimulateRequest):
    """정책 비교용 집계 결과 대신, 프론트엔드 2D 애니메이션이 재생할 수 있도록 개별 반송
    이벤트(FOUP별 출발/도착 스테이션과 시각) 전체를 반환한다."""
    _validate_amhs_request(req)
    dispatch_policy = _resolve_amhs_dispatch_policy(req)

    result = amhs.run_simulation(
        n_vehicles=req.n_vehicles,
        n_foups=req.n_foups,
        n_laps=req.n_laps,
        foup_launch_interval_sec=req.foup_launch_interval_sec,
        stocker_capacity=req.stocker_capacity,
        hot_lot_ratio=req.hot_lot_ratio,
        dispatch_policy=dispatch_policy,
        seed=req.seed,
    )

    log_df = result["transport_log"]
    events = [
        AmhsTransportEvent(
            foup_id=int(r["foup_id"]),
            from_station=r["from"],
            to_station=r["to"],
            requested_at=float(r["requested_at"]),
            completed_at=float(r["completed_at"]),
            vehicle_id=int(r["vehicle_id"]),
            is_hot_lot=bool(r["is_hot_lot"]),
        )
        for r in (log_df.to_dict("records") if len(log_df) else [])
    ]
    stations = [
        AmhsStationOut(name=s.name, name_ko=s.name_ko, index=s.index)
        for s in sorted(amhs.STATIONS.values(), key=lambda s: s.index)
    ]

    return AmhsReplayResponse(
        policy=req.policy,
        n_vehicles=req.n_vehicles,
        n_stations=len(stations),
        sim_duration_sec=result["sim_duration_sec"],
        stations=stations,
        events=events,
    )


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", models_loaded=ml.models_available())


# Hugging Face Spaces (Docker SDK) run a single container on a single port, so the
# built React app is served from the same FastAPI process rather than a separate
# nginx container. Only active when frontend/dist exists (produced by `npm run
# build`), so local `uvicorn` dev runs without a frontend build are unaffected —
# registered last so it never shadows the /api/* routes above.
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
