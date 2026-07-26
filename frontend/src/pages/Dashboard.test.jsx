import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "./Dashboard.jsx";
import { api } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    processStatus: vi.fn(),
    statsSummary: vi.fn(),
    statsYield: vi.fn(),
    simulateProcess: vi.fn(),
  },
}));

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  it("shows an empty state before any process data exists", async () => {
    api.processStatus.mockResolvedValue([]);
    api.statsSummary.mockResolvedValue({
      total_process_readings: 0, total_process_anomalies: 0,
      total_faults_detected: 0, readings_by_process: {},
    });
    api.statsYield.mockResolvedValue({ overall_yield: 1, yield_by_process: {} });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getAllByText(/아직 공정 데이터가 없습니다/).length).toBeGreaterThan(0);
    });
  });

  it("renders process cards once status data arrives", async () => {
    api.processStatus.mockResolvedValue([
      {
        id: 1, process: "etching", process_name_ko: "식각",
        params: { pressure: 42.1, gas_flow: 100.5, power: 900.0 },
        is_anomaly: false, created_at: "2026-07-25T00:00:00Z",
      },
    ]);
    api.statsSummary.mockResolvedValue({
      total_process_readings: 1, total_process_anomalies: 0,
      total_faults_detected: 0, readings_by_process: { etching: 1 },
    });
    api.statsYield.mockResolvedValue({ overall_yield: 1, yield_by_process: { etching: 1 } });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("식각")).toBeInTheDocument();
    });
  });
});
