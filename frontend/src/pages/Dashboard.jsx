import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client.js";
import { useAsync } from "../hooks/useAsync.js";
import ProcessCard from "../components/ProcessCard.jsx";
import StatTile from "../components/StatTile.jsx";

const PROCESS_ORDER = [
  "wafer_fabrication", "oxidation", "photolithography", "etching",
  "deposition", "metallization", "eds", "packaging",
];

export default function Dashboard() {
  const { data: status, loading: statusLoading, reload: reloadStatus } = useAsync(api.processStatus, []);
  const { data: summary, reload: reloadSummary } = useAsync(api.statsSummary, []);
  const { data: yieldStats, reload: reloadYield } = useAsync(api.statsYield, []);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const runTick = async () => {
    setRunning(true);
    setError(null);
    try {
      await api.simulateProcess("all", 0.1);
      reloadStatus();
      reloadSummary();
      reloadYield();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const yieldChartData = yieldStats
    ? PROCESS_ORDER.filter((p) => p in yieldStats.yield_by_process).map((p) => ({
        process: p,
        yield: Math.round(yieldStats.yield_by_process[p] * 1000) / 10,
      }))
    : [];

  const sortedStatus = status
    ? [...status].sort((a, b) => PROCESS_ORDER.indexOf(a.process) - PROCESS_ORDER.indexOf(b.process))
    : [];

  return (
    <>
      <h2>메인 대시보드</h2>
      <p className="page-subtitle">공정 상태, 이상 발생 현황, 수율 트렌드를 한눈에 확인합니다.</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="toolbar">
        <button onClick={runTick} disabled={running}>
          {running ? "실행 중..." : "공정 1틱 시뮬레이션 실행"}
        </button>
      </div>

      <div className="grid grid-4">
        <StatTile label="총 공정 판독 수" value={summary?.total_process_readings ?? "–"} />
        <StatTile label="공정 이상 발생 수" value={summary?.total_process_anomalies ?? "–"} />
        <StatTile label="AI 이상 탐지 수" value={summary?.total_faults_detected ?? "–"} />
        <StatTile
          label="전체 수율"
          value={yieldStats ? `${(yieldStats.overall_yield * 100).toFixed(1)}%` : "–"}
        />
      </div>

      <div className="card">
        <p className="card-title">공정별 수율 (%)</p>
        {yieldChartData.length === 0 ? (
          <div className="empty-state">아직 공정 데이터가 없습니다. 위 버튼으로 시뮬레이션을 실행해 보세요.</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={yieldChartData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--gridline)" vertical={false} />
              <XAxis dataKey="process" tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} width={36} />
              <Tooltip
                contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                formatter={(v) => [`${v}%`, "수율"]}
              />
              <Bar dataKey="yield" fill="var(--series-1)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="card">
        <p className="card-title">공정별 현재 상태 (최신 판독값)</p>
        {statusLoading ? (
          <div className="empty-state">불러오는 중...</div>
        ) : sortedStatus.length === 0 ? (
          <div className="empty-state">아직 공정 데이터가 없습니다.</div>
        ) : (
          <div className="grid grid-process">
            {sortedStatus.map((log) => (
              <ProcessCard key={log.process} log={log} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
