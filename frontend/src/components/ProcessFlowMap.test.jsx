import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ProcessFlowMap from "./ProcessFlowMap.jsx";

describe("ProcessFlowMap", () => {
  it("renders all 8 stations even with no data, marked as 대기 중", () => {
    render(<ProcessFlowMap logs={[]} />);
    expect(screen.getByText("웨이퍼 제조")).toBeInTheDocument();
    expect(screen.getByText("패키징")).toBeInTheDocument();
    expect(screen.getAllByText("대기 중").length).toBe(8);
  });

  it("colors a station green/정상 when its latest reading is normal", () => {
    const { container } = render(
      <ProcessFlowMap logs={[{ process: "etching", is_anomaly: false, diagnoses: [] }]} />,
    );
    const node = container.querySelector(".flow-node-normal");
    expect(node).toBeTruthy();
    expect(node.textContent).toContain("식각");
    expect(node.textContent).toContain("정상");
  });

  it("flags a station as 이상 and surfaces the top diagnosis label when anomalous", () => {
    const { container } = render(
      <ProcessFlowMap
        logs={[{
          process: "etching",
          is_anomaly: true,
          diagnoses: [{ parameter: "pressure", label: "식각 압력 상한 초과" }],
        }]}
      />,
    );
    const node = container.querySelector(".flow-node-anomaly");
    expect(node).toBeTruthy();
    expect(node.textContent).toContain("식각 압력 상한 초과");
  });

  it("falls back to a generic 이상 label when no diagnosis is present", () => {
    const { container } = render(
      <ProcessFlowMap logs={[{ process: "etching", is_anomaly: true, diagnoses: [] }]} />,
    );
    const node = container.querySelector(".flow-node-anomaly");
    expect(node.textContent).toContain("이상");
  });
});
