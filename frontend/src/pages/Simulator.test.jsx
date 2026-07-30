import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Simulator from "./Simulator.jsx";
import { api } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    simulateProcess: vi.fn(),
    processHistory: vi.fn(),
    faultDemo: vi.fn(),
  },
}));

const FAKE_FAULT_DEMO = {
  process: "etching", process_name_ko: "식각",
  params: { pressure: 130.4, gas_flow: 245.2, power: 950.1 },
  injected_label: "mfc_drift", injected_label_ko: "MFC 캘리브레이션 드리프트",
  predicted_fault: {
    predicted_label: "mfc_drift", predicted_label_ko: "MFC 캘리브레이션 드리프트",
    confidence: 0.94,
    probabilities: { "정상": 0.02, "MFC 캘리브레이션 드리프트": 0.94, "RF 제너레이터 이상": 0.04 },
  },
};

describe("Simulator page", () => {
  beforeEach(() => {
    api.processHistory.mockResolvedValue([]);
  });

  it("runs the AI fault-classification demo and shows injected vs predicted labels", async () => {
    api.faultDemo.mockResolvedValue(FAKE_FAULT_DEMO);
    const user = userEvent.setup();
    render(<Simulator />);

    await user.click(screen.getByRole("button", { name: "AI 원인 분류 데모 실행" }));

    await waitFor(() => {
      expect(api.faultDemo).toHaveBeenCalledWith("etching");
    });
    expect(screen.getAllByText("MFC 캘리브레이션 드리프트").length).toBeGreaterThan(0);
    expect(screen.getByText("일치")).toBeInTheDocument();
    expect(screen.getByText("RF 제너레이터 이상")).toBeInTheDocument();
  });

  it("shows an error banner when the fault-demo model is unavailable", async () => {
    api.faultDemo.mockRejectedValue(new Error("공정 원인 분류 모델이 없습니다."));
    const user = userEvent.setup();
    render(<Simulator />);

    await user.click(screen.getByRole("button", { name: "AI 원인 분류 데모 실행" }));

    await waitFor(() => {
      expect(screen.getByText(/공정 원인 분류 모델이 없습니다/)).toBeInTheDocument();
    });
  });

  it("splits generated readings into a 정상 column and an 이상 column", async () => {
    api.simulateProcess.mockResolvedValue([
      { id: 1, process: "etching", process_name_ko: "식각", params: { pressure: 50, gas_flow: 100, power: 1000 }, is_anomaly: false, created_at: "2026-07-30T00:00:00Z", diagnoses: [] },
      { id: 2, process: "oxidation", process_name_ko: "산화", params: { temperature: 1300 }, is_anomaly: true, created_at: "2026-07-30T00:00:00Z", diagnoses: [] },
    ]);
    const user = userEvent.setup();
    render(<Simulator />);

    await user.click(screen.getByRole("button", { name: "데이터 생성" }));

    await waitFor(() => {
      expect(screen.getAllByText("식각").length).toBeGreaterThan(0);
      expect(screen.getAllByText("산화").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("1건").length).toBe(2); // 정상 1건, 이상 1건 둘 다 "1건"
  });
});
