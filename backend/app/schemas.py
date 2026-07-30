from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SimulateRequest(BaseModel):
    process: str = "all"  # PROCESS_SPECS의 키 하나, 또는 "all"(8개 전체 1건씩)
    anomaly_ratio: float = 0.1


class DiagnosisOut(BaseModel):
    parameter: str
    value: float
    spec_low: float
    spec_high: float
    unit: str
    direction: str  # "high" | "low"
    label: str
    cause: str
    impact: str
    action: str


class FaultPredictionOut(BaseModel):
    predicted_label: str
    predicted_label_ko: str
    confidence: float
    probabilities: dict[str, float]


class ProcessLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    process: str
    process_name_ko: str
    params: dict[str, float]
    is_anomaly: bool
    created_at: datetime
    diagnoses: list[DiagnosisOut] = []
    predicted_fault: FaultPredictionOut | None = None


class FaultDemoRequest(BaseModel):
    process: str


class FaultDemoResponse(BaseModel):
    process: str
    process_name_ko: str
    params: dict[str, float]
    injected_label: str  # 실제로 주입한 정답 ("normal" 또는 시나리오 영문 식별자)
    injected_label_ko: str
    predicted_fault: FaultPredictionOut


class ProcessExplainRequest(BaseModel):
    process: str
    params: dict[str, float]
    question: str


class ProcessExplainResponse(BaseModel):
    answer: str


class SecomDetectRequest(BaseModel):
    features: dict[str, float]  # feature_name -> value (models/feature_columns.joblib 기준)


class DetectResponse(BaseModel):
    is_anomaly_isolation_forest: bool
    is_anomaly_xgboost: bool
    is_anomaly_ensemble: bool
    if_score: float
    xgb_proba: float
    ensemble_score: float
    fault_id: int


class FaultRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str
    if_score: float | None
    xgb_proba: float | None
    ensemble_score: float | None
    is_anomaly: bool
    alert_sent: bool
    detected_at: datetime


class AlertSendRequest(BaseModel):
    fault_id: int


class AlertSendResponse(BaseModel):
    fault_id: int
    alert_sent: bool


class StatsSummary(BaseModel):
    total_process_readings: int
    total_process_anomalies: int
    total_faults_detected: int
    readings_by_process: dict[str, int]


class YieldStats(BaseModel):
    overall_yield: float
    yield_by_process: dict[str, float]


class RetrainResponse(BaseModel):
    model_name: str
    precision: float
    recall: float
    f1: float
    auroc: float
    trained_at: datetime


class ModelMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    precision: float
    recall: float
    f1: float
    auroc: float
    trained_at: datetime


class FeatureImportanceOut(BaseModel):
    features: list[str]
    importances: list[float]


class ShapContributor(BaseModel):
    feature: str
    shap_value: float
    feature_value: float


class ExplainResponse(BaseModel):
    base_value: float
    top_contributors: list[ShapContributor]


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool


class AmhsSimulateRequest(BaseModel):
    n_vehicles: int = 5
    n_foups: int = 20
    n_laps: int = 2
    foup_launch_interval_sec: float = 150.0
    stocker_capacity: int = 2
    hot_lot_ratio: float = 0.0
    policy: str = "nearest"  # "nearest" | "fcfs" | "zone" | "predictive"
    enable_maintenance: bool = False
    seed: int = 42


class AmhsSimulateResponse(BaseModel):
    policy: str
    n_vehicles: int
    completion_rate: float
    avg_cycle_time_sec: float
    p95_cycle_time_sec: float
    avg_vehicle_utilization: float
    avg_hot_lot_cycle_time_sec: float | None
    avg_normal_lot_cycle_time_sec: float | None
    max_queue_length: int
    completed_transports: int


class AmhsStationOut(BaseModel):
    name: str
    name_ko: str
    index: int


class AmhsTransportEvent(BaseModel):
    foup_id: int
    from_station: str
    to_station: str
    requested_at: float
    completed_at: float
    vehicle_id: int
    is_hot_lot: bool


class AmhsCongestionSample(BaseModel):
    time: float
    station: str
    queue_length: int
    busy_vehicles: int
    under_maintenance_vehicles: int


class AmhsMaintenanceEvent(BaseModel):
    time: float
    vehicle_id: int
    event: str  # "down" | "restored"


class AmhsReplayResponse(BaseModel):
    policy: str
    n_vehicles: int
    n_stations: int
    stocker_capacity: int
    sim_duration_sec: float
    stations: list[AmhsStationOut]
    events: list[AmhsTransportEvent]
    congestion: list[AmhsCongestionSample]
    maintenance_events: list[AmhsMaintenanceEvent]
