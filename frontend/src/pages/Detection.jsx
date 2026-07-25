import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client.js";
import { useAsync } from "../hooks/useAsync.js";
import { SECOM_SAMPLES } from "../data/secomSamples.js";

const SAMPLE_OPTIONS = [
  { key: "normal", label: "정상 샘플 (실제 라벨: Pass)" },
  { key: "fail_caught", label: "불량 샘플 — 모델이 탐지한 케이스 (실제 라벨: Fail)" },
  { key: "fail_missed", label: "불량 샘플 — 모델이 놓친 케이스 (실제 라벨: Fail)" },
];

// notebooks/03_modeling.ipynb 테스트셋(313개) 최초 1회 평가 결과 — models/model_comparison.csv
const TEST_SET_COMPARISON = [
  { model: "Isolation Forest", precision: 0.214, recall: 0.143, f1: 0.171, auroc: 0.541 },
  { model: "XGBoost", precision: 0.155, recall: 0.429, f1: 0.228, auroc: 0.692 },
  { model: "Ensemble (투표)", precision: 0.156, recall: 0.476, f1: 0.235, auroc: 0.612 },
];

function ModelVerdict({ label, isAnomaly, score }) {
  return (
    <div className="card" style={{ flex: 1 }}>
      <p className="card-title">{label}</p>
      <span className={`badge ${isAnomaly ? "badge-critical" : "badge-good"}`}>
        {isAnomaly ? "이상 탐지" : "정상"}
      </span>
      <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-muted)" }}>
        score: {score.toFixed(4)}
      </div>
    </div>
  );
}

export default function Detection() {
  const [sampleKey, setSampleKey] = useState("normal");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const { data: importance } = useAsync(() => api.featureImportance(20), []);

  const runDetect = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.detect(SECOM_SAMPLES[sampleKey]);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const importanceData = importance
    ? importance.features.map((f, i) => ({ feature: f, importance: importance.importances[i] })).slice(0, 15)
    : [];

  return (
    <>
      <h2>이상 탐지 결과</h2>
      <p className="page-subtitle">
        SECOM 피처 형식 입력에 대해 학습된 Isolation Forest + XGBoost 앙상블을 실행합니다. 공정 시뮬레이터와는 별개의 피처 공간입니다.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div className="toolbar">
        <select value={sampleKey} onChange={(e) => setSampleKey(e.target.value)}>
          {SAMPLE_OPTIONS.map((o) => (
            <option key={o.key} value={o.key}>{o.label}</option>
          ))}
        </select>
        <button onClick={runDetect} disabled={running}>
          {running ? "탐지 중..." : "탐지 실행"}
        </button>
      </div>

      {result && (
        <div className="card">
          <p className="card-title">모델별 탐지 결과 비교 (fault_id: {result.fault_id})</p>
          <div style={{ display: "flex", gap: 16 }}>
            <ModelVerdict label="Isolation Forest" isAnomaly={result.is_anomaly_isolation_forest} score={result.if_score} />
            <ModelVerdict label="XGBoost" isAnomaly={result.is_anomaly_xgboost} score={result.xgb_proba} />
            <ModelVerdict label="Ensemble (투표)" isAnomaly={result.is_anomaly_ensemble} score={result.ensemble_score} />
          </div>
        </div>
      )}

      <div className="card">
        <p className="card-title">XGBoost 피처 중요도 (상위 15)</p>
        {importanceData.length === 0 ? (
          <div className="empty-state">불러오는 중...</div>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={importanceData} layout="vertical" margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--gridline)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} />
              <YAxis dataKey="feature" type="category" width={90} tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="importance" fill="var(--series-1)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="card">
        <p className="card-title">참고: 테스트셋 전체 성능 (모델별 비교, notebooks/03_modeling.ipynb 최초 1회 평가)</p>
        <table>
          <thead>
            <tr>
              <th>모델</th><th>Precision</th><th>Recall</th><th>F1</th><th>AUROC</th>
            </tr>
          </thead>
          <tbody>
            {TEST_SET_COMPARISON.map((row) => (
              <tr key={row.model}>
                <td>{row.model}</td>
                <td>{row.precision}</td>
                <td>{row.recall}</td>
                <td>{row.f1}</td>
                <td>{row.auroc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
