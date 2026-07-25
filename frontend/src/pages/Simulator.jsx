import { useState } from "react";
import { api } from "../api/client.js";
import { useAsync } from "../hooks/useAsync.js";
import ProcessCard from "../components/ProcessCard.jsx";

const PROCESSES = [
  { key: "all", label: "전체 8대 공정" },
  { key: "wafer_fabrication", label: "① 웨이퍼 제조" },
  { key: "oxidation", label: "② 산화" },
  { key: "photolithography", label: "③ 포토" },
  { key: "etching", label: "④ 식각" },
  { key: "deposition", label: "⑤ 증착" },
  { key: "metallization", label: "⑥ 금속 배선" },
  { key: "eds", label: "⑦ EDS" },
  { key: "packaging", label: "⑧ 패키징" },
];

export default function Simulator() {
  const [process, setProcess] = useState("all");
  const [anomalyRatio, setAnomalyRatio] = useState(0.1);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [latest, setLatest] = useState([]);

  const historyProcess = process === "all" ? undefined : process;
  const { data: history, reload: reloadHistory } = useAsync(
    () => api.processHistory(historyProcess, 20),
    [historyProcess],
  );

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const logs = await api.simulateProcess(process, Number(anomalyRatio));
      setLatest(logs);
      reloadHistory();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <h2>공정 시뮬레이터</h2>
      <p className="page-subtitle">
        8대 공정 파라미터 기반 합성 데이터를 생성합니다. SECOM 학습 모델과는 별개로, 정상 범위 이탈 여부를 시뮬레이터 자체 로직으로 판정합니다.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div className="toolbar">
        <select value={process} onChange={(e) => setProcess(e.target.value)}>
          {PROCESSES.map((p) => (
            <option key={p.key} value={p.key}>{p.label}</option>
          ))}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)" }}>
          이상 비율
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={anomalyRatio}
            onChange={(e) => setAnomalyRatio(e.target.value)}
            style={{ width: 64, padding: "5px 8px", border: "1px solid var(--border)", borderRadius: 6, background: "var(--surface-2)", color: "var(--text-primary)" }}
          />
        </label>
        <button onClick={run} disabled={running}>
          {running ? "생성 중..." : "데이터 생성"}
        </button>
      </div>

      {latest.length > 0 && (
        <div className="card">
          <p className="card-title">방금 생성된 데이터</p>
          <div className="grid grid-process">
            {latest.map((log) => (
              <ProcessCard key={log.id} log={log} />
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <p className="card-title">최근 이력 {historyProcess ? `(${historyProcess})` : "(전체)"}</p>
        {!history || history.length === 0 ? (
          <div className="empty-state">이력이 없습니다. 위에서 데이터를 생성해 보세요.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>시각</th>
                <th>공정</th>
                <th>파라미터</th>
                <th>판정</th>
              </tr>
            </thead>
            <tbody>
              {history.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.created_at).toLocaleString("ko-KR")}</td>
                  <td>{log.process_name_ko}</td>
                  <td>
                    {Object.entries(log.params).map(([k, v]) => `${k}=${v}`).join(", ")}
                  </td>
                  <td>
                    <span className={`badge ${log.is_anomaly ? "badge-critical" : "badge-good"}`}>
                      {log.is_anomaly ? "이상" : "정상"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
