import { useState } from "react";
import { api } from "../api/client.js";
import { useAsync } from "../hooks/useAsync.js";

export default function History() {
  const [retraining, setRetraining] = useState(false);
  const [error, setError] = useState(null);
  const [sendingId, setSendingId] = useState(null);

  const { data: faults, reload: reloadFaults } = useAsync(() => api.faultList(30), []);
  const { data: processLogs } = useAsync(() => api.processHistory(undefined, 30), []);
  const { data: metrics, reload: reloadMetrics } = useAsync(() => api.modelMetrics(10), []);

  const sendAlert = async (faultId) => {
    setSendingId(faultId);
    setError(null);
    try {
      await api.sendAlert(faultId);
      reloadFaults();
    } catch (e) {
      setError(e.message);
    } finally {
      setSendingId(null);
    }
  };

  const retrain = async () => {
    setRetraining(true);
    setError(null);
    try {
      await api.retrainModel();
      reloadMetrics();
    } catch (e) {
      setError(e.message);
    } finally {
      setRetraining(false);
    }
  };

  return (
    <>
      <h2>이력 관리</h2>
      <p className="page-subtitle">이상 이력, 공정 이력, 모델 재학습 성능 지표를 확인합니다.</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <p className="card-title">SECOM 모델 이상 탐지 이력 (fault_records)</p>
        {!faults || faults.length === 0 ? (
          <div className="empty-state">이상 탐지 이력이 없습니다. 이상 탐지 결과 화면에서 탐지를 실행해 보세요.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th><th>시각</th><th>판정</th><th>IF score</th><th>XGB proba</th><th>알림</th>
              </tr>
            </thead>
            <tbody>
              {faults.map((f) => (
                <tr key={f.id}>
                  <td>{f.id}</td>
                  <td>{new Date(f.detected_at).toLocaleString("ko-KR")}</td>
                  <td>
                    <span className={`badge ${f.is_anomaly ? "badge-critical" : "badge-good"}`}>
                      {f.is_anomaly ? "이상" : "정상"}
                    </span>
                  </td>
                  <td>{f.if_score?.toFixed(4)}</td>
                  <td>{f.xgb_proba?.toFixed(4)}</td>
                  <td>
                    {f.is_anomaly && (
                      <button
                        className="secondary"
                        disabled={f.alert_sent || sendingId === f.id}
                        onClick={() => sendAlert(f.id)}
                      >
                        {f.alert_sent ? "발송됨" : sendingId === f.id ? "발송 중..." : "알림 발송"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <p className="card-title">공정 시뮬레이터 이력 (process_logs)</p>
        {!processLogs || processLogs.length === 0 ? (
          <div className="empty-state">공정 이력이 없습니다.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>시각</th><th>공정</th><th>판정</th>
              </tr>
            </thead>
            <tbody>
              {processLogs.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.created_at).toLocaleString("ko-KR")}</td>
                  <td>{log.process_name_ko}</td>
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

      <div className="card">
        <div className="toolbar" style={{ marginBottom: 12 }}>
          <p className="card-title" style={{ margin: 0 }}>모델 재학습 이력 (model_metrics)</p>
          <button onClick={retrain} disabled={retraining}>
            {retraining ? "재학습 중..." : "지금 재학습"}
          </button>
        </div>
        {!metrics || metrics.length === 0 ? (
          <div className="empty-state">재학습 이력이 없습니다. 위 버튼으로 재학습을 실행해 보세요.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>시각</th><th>모델</th><th>Precision</th><th>Recall</th><th>F1</th><th>AUROC</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.id}>
                  <td>{new Date(m.trained_at).toLocaleString("ko-KR")}</td>
                  <td>{m.model_name}</td>
                  <td>{m.precision.toFixed(4)}</td>
                  <td>{m.recall.toFixed(4)}</td>
                  <td>{m.f1.toFixed(4)}</td>
                  <td>{m.auroc.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
