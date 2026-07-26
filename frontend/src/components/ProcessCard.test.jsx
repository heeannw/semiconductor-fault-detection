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
});
