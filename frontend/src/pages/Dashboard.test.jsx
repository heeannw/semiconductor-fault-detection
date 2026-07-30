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

  it("splits process status cards into 정상/이상 columns", async () => {
    api.processStatus.mockResolvedValue([
      { id: 1, process: "etching", process_name_ko: "식각", params: { pressure: 42.1, gas_flow: 100.5, power: 900.0 }, is_anomaly: false, created_at: "2026-07-25T00:00:00Z", diagnoses: [] },
      { id: 2, process: "oxidation", process_name_ko: "산화", params: { temperature: 1300 }, is_anomaly: true, created_at: "2026-07-25T00:00:00Z", diagnoses: [] },
    ]);
    api.statsSummary.mockResolvedValue({
      total_process_readings: 2, total_process_anomalies: 1,
      total_faults_detected: 0, readings_by_process: { etching: 1, oxidation: 1 },
    });
    api.statsYield.mockResolvedValue({ overall_yield: 0.5, yield_by_process: { etching: 1, oxidation: 0 } });

    const { container } = renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("식각")).toBeInTheDocument();
      expect(screen.getByText("산화")).toBeInTheDocument();
    });
    const columns = container.querySelectorAll(".status-column");
    expect(columns.length).toBe(2);
    expect(columns[0].textContent).toContain("정상");
    expect(columns[0].textContent).toContain("식각");
    expect(columns[1].textContent).toContain("이상");
    expect(columns[1].textContent).toContain("산화");
  });
});
