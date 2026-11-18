// @vitest-environment jsdom
import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { usePoll } from "@/lib/usePoll";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

describe("clinical feed polling", () => {
  it("does not show a late response from the previous unit", async () => {
    const previous = deferred<string>();
    const current = deferred<string>();
    function View({ unit }: { unit: string }) {
      const { data } = usePoll(() => unit === "A" ? previous.promise : current.promise, 60000, [unit]);
      return <p>{data ?? "Waiting"}</p>;
    }
    const view = render(<View unit="A" />);
    view.rerender(<View unit="B" />);
    await act(async () => { previous.resolve("Patient from A"); await previous.promise; });
    expect(screen.queryByText("Patient from A")).toBeNull();
    expect(screen.getByText("Waiting")).toBeTruthy();
    await act(async () => { current.resolve("Patient from B"); await current.promise; });
    expect(screen.getByText("Patient from B")).toBeTruthy();
  });
});
