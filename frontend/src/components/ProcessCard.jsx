import { useState } from "react";
import { api } from "../api/client.js";

const PARAM_UNITS = {
  temperature: "°C",
  oxygen_concentration: "ppb",
  resistivity: "Ω·cm",
  time: "min",
  oxide_thickness: "nm",
  exposure_energy: "mJ/cm²",
  focus_distance: "μm",
  pressure: "mTorr",
  gas_flow: "sccm",
  power: "W",
  deposition_rate: "nm/min",
  current_density: "mA/cm²",
  plating_time: "min",
  test_voltage: "V",
  test_current: "μA",
  dicing_speed: "mm/s",
  bonding_strength: "g",
};

export default function ProcessCard({ log }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState(null);

  const askQuestion = async () => {
    if (!question.trim() || asking) return;
    setAsking(true);
    setAskError(null);
    try {
      const result = await api.processExplain({ process: log.process, params: log.params, question });
      setAnswer(result.answer);
    } catch (e) {
      setAskError(e.message);
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className={`process-card${log.is_anomaly ? " is-anomaly" : ""}`}>
      <div className="process-title">
        <span>{log.process_name_ko}</span>
        <span className={`badge ${log.is_anomaly ? "badge-critical" : "badge-good"}`}>
          {log.is_anomaly ? "이상" : "정상"}
        </span>
      </div>
      {Object.entries(log.params).map(([key, value]) => (
        <div className="param-row" key={key}>
          <span className="param-name">{key}</span>
          <span>
            {value} {PARAM_UNITS[key] ?? ""}
          </span>
        </div>
      ))}
      {log.diagnoses?.length > 0 && (
        <div className="diagnosis-block">
          {log.diagnoses.map((d) => (
            <div className="diagnosis-item" key={d.parameter}>
              <div className="diagnosis-label">
                {d.label} ({d.direction === "high" ? "↑ 상한 초과" : "↓ 하한 미달"}: {d.value} {d.unit}, 규격 {d.spec_low}~{d.spec_high}{d.unit})
              </div>
              <div className="diagnosis-row"><span>원인 후보</span>{d.cause}</div>
              <div className="diagnosis-row"><span>영향</span>{d.impact}</div>
              <div className="diagnosis-row"><span>조치 제안</span>{d.action}</div>
            </div>
          ))}
        </div>
      )}
      {log.predicted_fault && (
        <div className="fault-prediction-block">
          <div className="fault-prediction-header">
            AI 예측 원인 (다중 파라미터 패턴 기반)
            <span className="fault-confidence">확신도 {(log.predicted_fault.confidence * 100).toFixed(0)}%</span>
          </div>
          <div className={`fault-prediction-label${log.predicted_fault.predicted_label === "normal" ? " is-normal" : ""}`}>
            {log.predicted_fault.predicted_label_ko}
          </div>
          {Object.entries(log.predicted_fault.probabilities)
            .sort(([, a], [, b]) => b - a)
            .map(([label, prob]) => (
              <div className="fault-prob-row" key={label}>
                <span className="fault-prob-label">{label}</span>
                <div className="fault-prob-bar-track">
                  <div className="fault-prob-bar-fill" style={{ width: `${prob * 100}%` }} />
                </div>
                <span className="fault-prob-value">{(prob * 100).toFixed(0)}%</span>
              </div>
            ))}
        </div>
      )}
      <div className="explain-block">
        <div className="explain-header">AI에게 질문하기 (Gemini — 위 규칙/AI 결과에 근거해서만 답변)</div>
        <div className="explain-input-row">
          <input
            type="text"
            placeholder="예: 이 상황을 좀 더 자세히 설명해줘"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && askQuestion()}
          />
          <button onClick={askQuestion} disabled={asking || !question.trim()}>
            {asking ? "..." : "질문"}
          </button>
        </div>
        {askError && <div className="explain-error">{askError}</div>}
        {answer && <div className="explain-answer">{answer}</div>}
      </div>
    </div>
  );
}
