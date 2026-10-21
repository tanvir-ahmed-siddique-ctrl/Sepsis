import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { GatesPanel } from "@/components/pilot/PilotGovernance";
import { Pill, SiteModeBanner } from "@/components/ui";

afterEach(cleanup);

describe("SiteModeBanner", () => {
  it("announces the silent pilot as a status region", () => {
    render(<SiteModeBanner mode="silent" detail="Site icu-pilot" />);
    const banner = screen.getByRole("status");
    expect(banner.textContent).toContain("Silent pilot.");
    expect(banner.textContent).toContain("Bedside staff are blinded");
    expect(banner.textContent).toContain("Site icu-pilot");
  });
});

describe("GatesPanel", () => {
  it("counts passed gates and marks failures accessibly", () => {
    render(
      <GatesPanel
        policy="Live mode needs every gate."
        gates={[
          { gate: "minimum_days", passed: true, value: 30, target: 28, detail: "Days of silent data" },
          { gate: "governance_signoff", passed: false, value: null, target: true, detail: "Committee approval" },
        ]}
      />,
    );
    expect(screen.getByText("Readiness gates — 1/2 passed")).toBeTruthy();
    expect(screen.getByText("minimum days")).toBeTruthy();
    expect(screen.getAllByLabelText("not passed")).toHaveLength(1);
    expect(screen.getByText("Live mode needs every gate.")).toBeTruthy();
  });
});

describe("Pill", () => {
  it("applies the tone class", () => {
    render(<Pill tone="danger">Overdue</Pill>);
    expect(screen.getByText("Overdue").className).toContain("risk-high");
  });
});
