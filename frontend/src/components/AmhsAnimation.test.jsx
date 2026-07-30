import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import AmhsAnimation from "./AmhsAnimation.jsx";

const STATIONS = [
  { name: "wafer_fabrication", name_ko: "웨이퍼 제조", index: 0 },
  { name: "oxidation", name_ko: "산화", index: 1 },
];

describe("AmhsAnimation fleet panel", () => {
  it("lists one fleet card per vehicle seen in events or maintenance events", () => {
    const events = [
      { foup_id: 0, from_station: "wafer_fabrication", to_station: "oxidation", requested_at: 0, completed_at: 40, vehicle_id: 0, is_hot_lot: false },
    ];
    const maintenanceEvents = [{ time: 0, vehicle_id: 1, event: "down" }];
    render(<AmhsAnimation stations={STATIONS} events={events} maintenanceEvents={maintenanceEvents} />);

    expect(screen.getByText("AGV #0")).toBeInTheDocument();
    expect(screen.getByText("AGV #1")).toBeInTheDocument();
    expect(screen.getByText("차량 현황 (2대)")).toBeInTheDocument();
  });

  it("shows a moving vehicle as 이동 중 and a broken-down vehicle as 고장 · 예지보전 at t=0", () => {
    const events = [
      { foup_id: 0, from_station: "wafer_fabrication", to_station: "oxidation", requested_at: 0, completed_at: 40, vehicle_id: 0, is_hot_lot: false },
    ];
    const maintenanceEvents = [{ time: 0, vehicle_id: 1, event: "down" }];
    const { container } = render(
      <AmhsAnimation stations={STATIONS} events={events} maintenanceEvents={maintenanceEvents} />,
    );

    const items = container.querySelectorAll(".amhs-fleet-item");
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain("이동 중");
    expect(items[1].textContent).toContain("고장 · 예지보전");
  });

  it("shows an idle vehicle when it has no active transport at the current time", () => {
    const events = [
      { foup_id: 0, from_station: "wafer_fabrication", to_station: "oxidation", requested_at: 100, completed_at: 140, vehicle_id: 0, is_hot_lot: false },
    ];
    render(<AmhsAnimation stations={STATIONS} events={events} />);

    expect(screen.getByText("대기 중")).toBeInTheDocument();
  });
});
