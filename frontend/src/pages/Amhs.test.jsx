import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Amhs from "./Amhs.jsx";
import { api } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    amhsSimulate: vi.fn(),
  },
}));

const FAKE_RESULT = {
  policy: "nearest", n_vehicles: 5, completion_rate: 1.0,
  avg_cycle_time_sec: 91.4, p95_cycle_time_sec: 197.8,
  avg_vehicle_utilization: 0.047, max_queue_length: 4, completed_transports: 70,
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
