import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client.js";

const POLICIES = [
  { key: "nearest", label: "최근접 차량" },
  { key: "fcfs", label: "FCFS" },
  { key: "zone", label: "구역기반" },
  { key: "predictive", label: "예측 기반(적응형)" },
];

const SENSITIVITY_VEHICLE_COUNTS = [2, 4, 6, 8, 10];

// notebooks/08_amhs_delay_prediction.ipynb / 09_amhs_predictive_maintenance.ipynb 결과 —
// 무거운 XGBoost/IsolationForest 재학습은 대시보드에서 실시간으로 돌리지 않고 참고용으로 고정 표시.
const DELAY_PREDICTION_RESULT = {
  mae_sec: 57.75, mae_pct_of_mean: 0.1879, r2: 0.9325,
  delay_f1: 0.9471, delay_precision: 0.9328, delay_recall: 0.9619, delay_auroc: 0.9957,
};
const VEHICLE_PM_RESULT = [
  { model: "Isolation Forest", precision: 0.950, recall: 1.000, f1: 0.974, auroc: 1.000 },
  { model: "XGBoost", precision: 1.000, recall: 0.989, f1: 0.995, auroc: 1.000 },
  { model: "Ensemble", precision: 0.950, recall: 1.000, f1: 0.974, auroc: 1.000 },
];

export default function Amhs() {
  const [nVehicles, setNVehicles] = useState(5);
  const [nFoups, setNFoups] = useState(10);
  const [nLaps, setNLaps] = useState(1);
  const [stockerCapacity, setStockerCapacity] = useState(2);
  const [hotLotRatio, setHotLotRatio] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [policyResults, setPolicyResults] = useState(null);

  const [sensitivityRunning, setSensitivityRunning] = useState(false);
  const [sensitivityResults, setSensitivityResults] = useState(null);

  const runPolicyComparison = async () => {
    setRunning(true);
    setError(null);
    try {
      const settled = await Promise.allSettled(
        POLICIES.map((p) =>
          api.amhsSimulate({ nVehicles, nFoups, nLaps, stockerCapacity, hotLotRatio, policy: p.key }).then((r) => ({ ...r, label: p.label })),
        ),
      );
      const results = settled.filter((s) => s.status === "fulfilled").map((s) => s.value);
      const failed = settled.filter((s) => s.status === "rejected");
      if (failed.length > 0) {
        setError(`일부 정책 실행 실패: ${failed.map((f) => f.reason.message).join(", ")}`);
      }
      setPolicyResults(results);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const runSensitivity = async () => {
    setSensitivityRunning(true);
    setError(null);
    try {
      const results = await Promise.all(
        SENSITIVITY_VEHICLE_COUNTS.map((n) =>
          api.amhsSimulate({ nVehicles: n, nFoups, nLaps, stockerCapacity, policy: "nearest" }),
        ),
      );
      setSensitivityResults(results);
    } catch (e) {
      setError(e.message);
    } finally {
      setSensitivityRunning(false);
    }
  };

  return (
    <>
      <h2>AMHS 물류 시뮬레이션</h2>
      <p className="page-subtitle">
        OHT 반송 시뮬레이션(SimPy)을 실시간으로 실행해 디스패칭 정책과 차량 대수에 따른 반송 시간을 비교합니다.
        개념 설명은 <a href="https://github.com/heeannw/semiconductor-fault-detection/blob/master/docs/AMHS.md" target="_blank" rel="noreferrer">docs/AMHS.md</a> 참고.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <p className="card-title">시뮬레이션 파라미터</p>
        <div className="toolbar">
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            차량 대수
            <input type="number" min="1" max="20" value={nVehicles} onChange={(e) => setNVehicles(Number(e.target.value))} style={{ width: 56 }} />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            FOUP 개수
            <input type="number" min="1" max="100" value={nFoups} onChange={(e) => setNFoups(Number(e.target.value))} style={{ width: 56 }} />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            바퀴 수
            <input type="number" min="1" max="10" value={nLaps} onChange={(e) => setNLaps(Number(e.target.value))} style={{ width: 56 }} />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            스토커 용량
            <input type="number" min="1" max="20" value={stockerCapacity} onChange={(e) => setStockerCapacity(Number(e.target.value))} style={{ width: 56 }} />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            Hot Lot 비율
            <input type="number" min="0" max="1" step="0.1" value={hotLotRatio} onChange={(e) => setHotLotRatio(Number(e.target.value))} style={{ width: 56 }} />
          </label>
          <button onClick={runPolicyComparison} disabled={running}>
            {running ? "실행 중..." : "디스패칭 정책 비교 실행"}
          </button>
          <button className="secondary" onClick={runSensitivity} disabled={sensitivityRunning}>
            {sensitivityRunning ? "실행 중..." : "차량 대수 민감도 실행"}
          </button>
        </div>
      </div>

      {policyResults && (
        <div className="card">
          <p className="card-title">디스패칭 정책 비교 (실시간 실행 결과)</p>
          <div className="grid grid-4" style={{ marginBottom: 16 }}>
            {policyResults.map((r) => (
              <div className="card stat-tile" key={r.policy}>
                <div className="value">{r.avg_cycle_time_sec.toFixed(0)}초</div>
                <div className="label">{r.label} — 평균 반송 시간</div>
              </div>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={policyResults} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--gridline)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="avg_cycle_time_sec" name="평균 반송 시간(초)" fill="var(--series-1)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <table style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>정책</th><th>완료율</th><th>P95 반송 시간</th><th>평균 가동률</th><th>최대 큐 길이</th>
                {hotLotRatio > 0 && <><th>Hot Lot 평균</th><th>일반 Lot 평균</th></>}
              </tr>
            </thead>
            <tbody>
              {policyResults.map((r) => (
                <tr key={r.policy}>
                  <td>{r.label}</td>
                  <td>{(r.completion_rate * 100).toFixed(0)}%</td>
                  <td>{r.p95_cycle_time_sec.toFixed(0)}초</td>
                  <td>{(r.avg_vehicle_utilization * 100).toFixed(1)}%</td>
                  <td>{r.max_queue_length}</td>
                  {hotLotRatio > 0 && (
                    <>
                      <td>{r.avg_hot_lot_cycle_time_sec != null ? `${r.avg_hot_lot_cycle_time_sec.toFixed(0)}초` : "–"}</td>
                      <td>{r.avg_normal_lot_cycle_time_sec != null ? `${r.avg_normal_lot_cycle_time_sec.toFixed(0)}초` : "–"}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sensitivityResults && (
        <div className="card">
          <p className="card-title">차량 대수 민감도 (최근접 배정 고정, 실시간 실행 결과)</p>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart
              data={sensitivityResults.map((r, i) => ({ n_vehicles: SENSITIVITY_VEHICLE_COUNTS[i], ...r }))}
              margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--gridline)" />
              <XAxis dataKey="n_vehicles" tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} label={{ value: "차량 대수", position: "insideBottom", offset: -4, fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} width={48} />
              <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="avg_cycle_time_sec" name="평균 반송 시간(초)" stroke="var(--series-1)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card">
        <p className="card-title">참고: 반송 지연 예측 (notebooks/08_amhs_delay_prediction.ipynb)</p>
        <table>
          <thead>
            <tr><th>MAE</th><th>R²</th><th>지연 분류 F1</th><th>지연 분류 AUROC</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>{DELAY_PREDICTION_RESULT.mae_sec}초 ({(DELAY_PREDICTION_RESULT.mae_pct_of_mean * 100).toFixed(1)}%)</td>
              <td>{DELAY_PREDICTION_RESULT.r2}</td>
              <td>{DELAY_PREDICTION_RESULT.delay_f1}</td>
              <td>{DELAY_PREDICTION_RESULT.delay_auroc}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="card">
        <p className="card-title">참고: OHT 차량 예지보전 (notebooks/09_amhs_predictive_maintenance.ipynb)</p>
        <table>
          <thead>
            <tr><th>모델</th><th>Precision</th><th>Recall</th><th>F1</th><th>AUROC</th></tr>
          </thead>
          <tbody>
            {VEHICLE_PM_RESULT.map((row) => (
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
