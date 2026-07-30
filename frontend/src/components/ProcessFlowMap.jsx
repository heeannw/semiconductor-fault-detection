const PROCESS_LABELS = [
  { key: "wafer_fabrication", name: "웨이퍼 제조" },
  { key: "oxidation", name: "산화" },
  { key: "photolithography", name: "포토" },
  { key: "etching", name: "식각" },
  { key: "deposition", name: "증착" },
  { key: "metallization", name: "금속 배선" },
  { key: "eds", name: "EDS" },
  { key: "packaging", name: "패키징" },
];

// 8개 공정을 한 줄에 놓고 색으로 정상/이상을 즉시 구분되게 한다 — 카드를 하나씩 열어보지
// 않아도 "지금 어디에 문제가 있는지"가 한눈에 보이는 게 목적. 이상인 공정은 살짝 깜빡이는
// 테두리로 시선을 끌고, 실제 이유(규칙 기반 진단의 첫 번째 항목)를 노드 위에 바로 보여준다.
export default function ProcessFlowMap({ logs }) {
  const byProcess = Object.fromEntries((logs ?? []).map((log) => [log.process, log]));

  return (
    <div className="flow-map">
      {PROCESS_LABELS.map((p, i) => {
        const log = byProcess[p.key];
        const status = !log ? "empty" : log.is_anomaly ? "anomaly" : "normal";
        const topIssue = log?.diagnoses?.[0]?.label;

        return (
          <div className="flow-map-item" key={p.key}>
            <div className={`flow-node flow-node-${status}`}>
              <div className="flow-node-index">{i + 1}</div>
              <div className="flow-node-name">{p.name}</div>
              <div className="flow-node-status">
                {status === "empty" ? "대기 중" : status === "anomaly" ? (topIssue ?? "이상") : "정상"}
              </div>
            </div>
            {i < PROCESS_LABELS.length - 1 && <div className="flow-arrow">→</div>}
          </div>
        );
      })}
    </div>
  );
}
