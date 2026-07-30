import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ProcessCard from "./ProcessCard.jsx";

const NORMAL_LOG = {
  process: "etching",
  process_name_ko: "식각",
  params: { pressure: 42.1, gas_flow: 100.5, power: 900.0 },
  is_anomaly: false,
};

const ANOMALY_LOG = { ...NORMAL_LOG, is_anomaly: true };

describe("ProcessCard", () => {
  it("shows process name and 정상 badge for a normal reading", () => {
    render(<ProcessCard log={NORMAL_LOG} />);
    expect(screen.getByText("식각")).toBeInTheDocument();
    expect(screen.getByText("정상")).toBeInTheDocument();
    expect(screen.queryByText("이상")).not.toBeInTheDocument();
  });

  it("shows 이상 badge and is-anomaly class for an anomalous reading", () => {
    const { container } = render(<ProcessCard log={ANOMALY_LOG} />);
    expect(screen.getByText("이상")).toBeInTheDocument();
    expect(container.querySelector(".process-card.is-anomaly")).toBeTruthy();
  });

  it("renders every param with its unit", () => {
    render(<ProcessCard log={NORMAL_LOG} />);
    expect(screen.getByText("pressure")).toBeInTheDocument();
    expect(screen.getByText(/42\.1 mTorr/)).toBeInTheDocument();
  });

  it("shows no root-cause diagnosis block when diagnoses is empty", () => {
    const { container } = render(<ProcessCard log={NORMAL_LOG} />);
    expect(container.querySelector(".diagnosis-block")).not.toBeInTheDocument();
  });

  it("shows root-cause label/cause/impact/action when diagnoses are present", () => {
    const logWithDiagnosis = {
      ...ANOMALY_LOG,
      params: { pressure: 150, gas_flow: 100.5, power: 900.0 },
      diagnoses: [
        {
          parameter: "pressure", value: 150, spec_low: 5, spec_high: 100, unit: "mTorr",
          direction: "high", label: "식각 압력 상한 초과",
          cause: "배기 펌프 성능 저하 또는 밸브 드리프트",
          impact: "식각 이방성 저하, CD 산포 증가",
          action: "펌프 점검, MFC 캘리브레이션",
        },
      ],
    };
    render(<ProcessCard log={logWithDiagnosis} />);
    expect(screen.getByText(/식각 압력 상한 초과/)).toBeInTheDocument();
    expect(screen.getByText("배기 펌프 성능 저하 또는 밸브 드리프트")).toBeInTheDocument();
    expect(screen.getByText("식각 이방성 저하, CD 산포 증가")).toBeInTheDocument();
    expect(screen.getByText("펌프 점검, MFC 캘리브레이션")).toBeInTheDocument();
  });

  it("shows no AI fault-prediction block when predicted_fault is absent", () => {
    const { container } = render(<ProcessCard log={NORMAL_LOG} />);
    expect(container.querySelector(".fault-prediction-block")).not.toBeInTheDocument();
  });

  it("shows the AI-predicted fault label, confidence, and probability bars", () => {
    const logWithPrediction = {
      ...ANOMALY_LOG,
      predicted_fault: {
        predicted_label: "mfc_drift",
        predicted_label_ko: "MFC 캘리브레이션 드리프트",
        confidence: 0.87,
        probabilities: { "정상": 0.05, "MFC 캘리브레이션 드리프트": 0.87, "RF 제너레이터 이상": 0.08 },
      },
    };
    render(<ProcessCard log={logWithPrediction} />);
    expect(screen.getByText("AI 예측 원인 (다중 파라미터 패턴 기반)")).toBeInTheDocument();
    expect(screen.getByText("확신도 87%")).toBeInTheDocument();
    expect(screen.getAllByText("MFC 캘리브레이션 드리프트").length).toBeGreaterThan(0);
    expect(screen.getByText("RF 제너레이터 이상")).toBeInTheDocument();
  });

  it("styles a normal AI prediction differently from a fault prediction", () => {
    const logWithNormalPrediction = {
      ...NORMAL_LOG,
      predicted_fault: {
        predicted_label: "normal",
        predicted_label_ko: "정상",
        confidence: 0.95,
        probabilities: { "정상": 0.95, "MFC 캘리브레이션 드리프트": 0.03, "RF 제너레이터 이상": 0.02 },
      },
    };
    const { container } = render(<ProcessCard log={logWithNormalPrediction} />);
    expect(container.querySelector(".fault-prediction-label.is-normal")).toBeTruthy();
  });
});
