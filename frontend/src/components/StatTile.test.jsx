import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import StatTile from "./StatTile.jsx";

describe("StatTile", () => {
  it("renders the value and label", () => {
    render(<StatTile label="총 공정 판독 수" value={42} />);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("총 공정 판독 수")).toBeInTheDocument();
  });

  it("renders a placeholder value as-is", () => {
    render(<StatTile label="AI 이상 탐지 수" value="–" />);
    expect(screen.getByText("–")).toBeInTheDocument();
  });
});
