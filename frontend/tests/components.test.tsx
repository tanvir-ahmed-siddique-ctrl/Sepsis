import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GatesPanel } from "@/components/pilot/PilotGovernance";
import { FileDrop, Pill, SiteModeBanner } from "@/components/ui";

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

describe("FileDrop", () => {
  function setup(maxBytes = 1000) {
    const onFile = vi.fn();
    const { container } = render(
      <FileDrop label="PDF document" accept="application/pdf,.pdf" acceptLabel="PDF" maxBytes={maxBytes} limitLabel="1 KB" file={null} onFile={onFile} />,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    return { onFile, input };
  }

  it("accepts a file that matches type and size", () => {
    const { onFile, input } = setup();
    const file = new File(["%PDF-1.4"], "contract.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onFile).toHaveBeenCalledWith(file);
  });

  it("rejects the wrong type with an accessible message", () => {
    const { onFile, input } = setup();
    fireEvent.change(input, { target: { files: [new File(["x"], "notes.txt", { type: "text/plain" })] } });
    expect(onFile).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toContain("Unsupported file type");
  });

  it("rejects files over the limit", () => {
    const { onFile, input } = setup(4);
    fireEvent.change(input, { target: { files: [new File(["%PDF-1.4"], "big.pdf", { type: "application/pdf" })] } });
    expect(onFile).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toContain("The limit is 1 KB");
  });
});
