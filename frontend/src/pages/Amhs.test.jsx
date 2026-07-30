import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Amhs from "./Amhs.jsx";
import { api } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    amhsSimulate: vi.fn(),
    amhsSimulateReplay: vi.fn(),
  },
}));

const FAKE_REPLAY = {
  policy: "nearest", n_vehicles: 3, n_stations: 8, sim_duration_sec: 500,
  stations: Array.from({ length: 8 }, (_, i) => ({ name: `p${i}`, name_ko: `공정${i}`, index: i })),
  events: [
    { foup_id: 0, from_station: "p0", to_station: "p1", requested_at: 0, completed_at: 40, vehicle_id: 0, is_hot_lot: false },
    { foup_id: 0, from_station: "p1", to_station: "p2", requested_at: 40, completed_at: 80, vehicle_id: 1, is_hot_lot: true },
  ],
};

const FAKE_RESULT = {
  policy: "nearest", n_vehicles: 5, completion_rate: 1.0,
  avg_cycle_time_sec: 91.4, p95_cycle_time_sec: 197.8,
  avg_vehicle_utilization: 0.047, avg_hot_lot_cycle_time_sec: null,
  avg_normal_lot_cycle_time_sec: null, max_queue_length: 4, completed_transports: 70,
};

describe("Amhs page", () => {
  it("renders the parameter controls and both action buttons", () => {
    render(<Amhs />);
    expect(screen.getByRole("button", { name: "디스패칭 정책 비교 실행" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "차량 대수 민감도 실행" })).toBeInTheDocument();
  });

  it("shows the static reference tables for notebooks 08/09 without calling the API", () => {
    render(<Amhs />);
    expect(screen.getByText(/notebooks\/08_amhs_delay_prediction\.ipynb/)).toBeInTheDocument();
    expect(screen.getByText(/notebooks\/09_amhs_predictive_maintenance\.ipynb/)).toBeInTheDocument();
    expect(api.amhsSimulate).not.toHaveBeenCalled();
  });

  it("runs the dispatch comparison across all 4 policies on button click", async () => {
    api.amhsSimulate.mockResolvedValue(FAKE_RESULT);
    const user = userEvent.setup();
    render(<Amhs />);

    await user.click(screen.getByRole("button", { name: "디스패칭 정책 비교 실행" }));

    await waitFor(() => {
      expect(api.amhsSimulate).toHaveBeenCalledTimes(4);
    });
    const calledPolicies = api.amhsSimulate.mock.calls.map(([arg]) => arg.policy);
    expect(calledPolicies.sort()).toEqual(["fcfs", "nearest", "predictive", "zone"].sort());
  });

  it("shows hot/normal lot columns only after a non-zero hot lot ratio is set", async () => {
    api.amhsSimulate.mockResolvedValue({ ...FAKE_RESULT, avg_hot_lot_cycle_time_sec: 190, avg_normal_lot_cycle_time_sec: 276 });
    const user = userEvent.setup();
    render(<Amhs />);

    expect(screen.queryByText("Hot Lot 평균")).not.toBeInTheDocument();

    const hotLotInput = screen.getByLabelText("Hot Lot 비율");
    await user.clear(hotLotInput);
    await user.type(hotLotInput, "0.3");
    await user.click(screen.getByRole("button", { name: "디스패칭 정책 비교 실행" }));

    await waitFor(() => {
      expect(screen.getByText("Hot Lot 평균")).toBeInTheDocument();
      expect(screen.getAllByText("190초").length).toBeGreaterThan(0);
    });
  });

  it("runs the OHT replay animation on button click and renders the canvas", async () => {
    api.amhsSimulateReplay.mockResolvedValue(FAKE_REPLAY);
    const user = userEvent.setup();
    render(<Amhs />);

    await user.click(screen.getByRole("button", { name: "애니메이션 실행" }));

    await waitFor(() => {
      expect(api.amhsSimulateReplay).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByRole("img", { name: "OHT 반송 애니메이션" })).toBeInTheDocument();
  });

  it("shows a partial result and an error banner when one policy call fails", async () => {
    api.amhsSimulate.mockImplementation(({ policy }) =>
      policy === "predictive"
        ? Promise.reject(new Error("지연 예측 모델이 없습니다."))
        : Promise.resolve({ ...FAKE_RESULT, policy }),
    );
    const user = userEvent.setup();
    render(<Amhs />);

    await user.click(screen.getByRole("button", { name: "디스패칭 정책 비교 실행" }));

    await waitFor(() => {
      expect(screen.getByText(/일부 정책 실행 실패/)).toBeInTheDocument();
    });
  });
});
