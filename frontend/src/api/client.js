const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),

  simulateProcess: (process = "all", anomalyRatio = 0.1) =>
    request("/api/process/simulate", {
      method: "POST",
      body: JSON.stringify({ process, anomaly_ratio: anomalyRatio }),
    }),
  processStatus: () => request("/api/process/status"),
  processHistory: (process, limit = 50) =>
    request(`/api/process/history?${new URLSearchParams({ ...(process && { process }), limit })}`),
  faultDemo: (process) =>
    request("/api/process/fault-demo", { method: "POST", body: JSON.stringify({ process }) }),
  processExplain: ({ process, params, question }) =>
    request("/api/process/explain", {
      method: "POST",
      body: JSON.stringify({ process, params, question }),
    }),

  detect: (features) =>
    request("/api/ai/detect", { method: "POST", body: JSON.stringify({ features }) }),
  explain: (features) =>
    request("/api/ai/explain", { method: "POST", body: JSON.stringify({ features }) }),
  faultList: (limit = 50) => request(`/api/fault/list?limit=${limit}`),
  faultDetail: (id) => request(`/api/fault/${id}`),
  sendAlert: (faultId) =>
    request("/api/alert/send", { method: "POST", body: JSON.stringify({ fault_id: faultId }) }),

  statsSummary: () => request("/api/stats/summary"),
  statsYield: () => request("/api/stats/yield"),

  retrainModel: () => request("/api/model/retrain", { method: "POST" }),
  modelMetrics: (limit = 20) => request(`/api/model/metrics?limit=${limit}`),
  featureImportance: (topN = 20) => request(`/api/model/feature-importance?top_n=${topN}`),

  amhsStations: () => request("/api/amhs/stations"),
  amhsSimulate: ({
    nVehicles = 5, nFoups = 20, nLaps = 2, foupLaunchIntervalSec = 150.0,
    stockerCapacity = 2, hotLotRatio = 0.0, policy = "nearest", seed = 42,
  }) =>
    request("/api/amhs/simulate", {
      method: "POST",
      body: JSON.stringify({
        n_vehicles: nVehicles, n_foups: nFoups, n_laps: nLaps,
        foup_launch_interval_sec: foupLaunchIntervalSec,
        stocker_capacity: stockerCapacity, hot_lot_ratio: hotLotRatio, policy, seed,
      }),
    }),
  amhsSimulateReplay: ({
    nVehicles = 5, nFoups = 8, nLaps = 1, foupLaunchIntervalSec = 150.0,
    stockerCapacity = 2, hotLotRatio = 0.0, policy = "nearest", enableMaintenance = false, seed = 42,
  }) =>
    request("/api/amhs/simulate/replay", {
      method: "POST",
      body: JSON.stringify({
        n_vehicles: nVehicles, n_foups: nFoups, n_laps: nLaps,
        foup_launch_interval_sec: foupLaunchIntervalSec,
        stocker_capacity: stockerCapacity, hot_lot_ratio: hotLotRatio, policy,
        enable_maintenance: enableMaintenance, seed,
      }),
    }),
};
