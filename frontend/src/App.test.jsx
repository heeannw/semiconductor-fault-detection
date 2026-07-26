import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App.jsx";

vi.mock("./api/client.js", () => ({
  api: {
    processStatus: vi.fn().mockResolvedValue([]),
    statsSummary: vi.fn().mockResolvedValue({
      total_process_readings: 0, total_process_anomalies: 0,
      total_faults_detected: 0, readings_by_process: {},
    }),
    statsYield: vi.fn().mockResolvedValue({ overall_yield: 1, yield_by_process: {} }),
    simulateProcess: vi.fn().mockResolvedValue([]),
  },
}));

describe("App", () => {
  it("renders the sidebar with all 5 navigation links", () => {
    render(<App />);
    expect(screen.getByText("🏭 SemiSense")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "메인 대시보드" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "공정 시뮬레이터" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "이상 탐지 결과" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "이력 관리" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "AMHS 물류" })).toBeInTheDocument();
  });

  it("renders the dashboard (default route) heading", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "메인 대시보드" })).toBeInTheDocument();
  });
});
