import { describe, expect, it } from "vitest";
import type { Alert, Gate } from "@/lib/api";
import {
  attentionAlerts,
  connectorTone,
  formatGateValue,
  gateProgress,
  minutesLabel,
  reviewClock,
  siteModeBanner,
} from "@/lib/pilot";

function trustgate(state: Alert["trustgate"]["state"]): Alert["trustgate"] {
  return { state } as unknown as Alert["trustgate"];
}

function alert(overrides: Partial<Alert>): Alert {
  return {
    alert_id: "alert-1",
    patient_id: "pilot-a--e1",
    display_name: "Bed 1",
    risk_band: "high_risk",
    probability: 0.2,
    uncertainty: 0.02,
    threshold: 0.1,
    hour: 12,
    created_at: "2026-10-16T00:00:00Z",
    reason: "Risk crossed the high-risk threshold",
    factors: [],
    data_quality: "complete",
    trustgate: trustgate("alert"),
    model_version: "run4",
    status: "open",
    actions: [],
    review_minutes: 4,
    review_sla_minutes: 15,
    overdue: false,
    ...overrides,
  };
}

describe("siteModeBanner", () => {
  it("never describes silent or live-disabled sites as alerting clinicians", () => {
    for (const mode of ["silent", "live-disabled"] as const) {
      const banner = siteModeBanner(mode);
      expect(banner.body).toMatch(/silent pilot|blinded|No interruptive alerts/i);
      expect(banner.tone).not.toBe("success");
    }
  });

  it("labels evaluation replay data as non-patient data", () => {
    expect(siteModeBanner("demo").title).toContain("Evaluation replay");
    expect(siteModeBanner("demo").body).toContain("Nothing here is a real patient");
  });
});

describe("gateProgress", () => {
  const gate = (name: string, passed: boolean): Gate => ({ gate: name, passed, value: 1, target: 1, detail: "" });

  it("lists blocking gates and only allows live when all pass", () => {
    const progress = gateProgress([gate("minimum_days", true), gate("sensitivity", false)]);
    expect(progress).toEqual({ passed: 1, total: 2, blocking: ["sensitivity"], eligible: false });
    expect(gateProgress([gate("minimum_days", true)]).eligible).toBe(true);
  });

  it("treats an empty gate list as not eligible", () => {
    expect(gateProgress([]).eligible).toBe(false);
  });
});

describe("formatGateValue", () => {
  it("formats every value shape a gate can report", () => {
    expect(formatGateValue(null)).toBe("—");
    expect(formatGateValue(true)).toBe("yes");
    expect(formatGateValue(28)).toBe("28");
    expect(formatGateValue(0.61234)).toBe("0.612");
    expect(formatGateValue([])).toBe("none");
    expect(formatGateValue(["icu-a", "icu-b"])).toBe("icu-a, icu-b");
    expect(formatGateValue({ committee: "IRB" })).toBe("recorded");
    expect(formatGateValue("signed")).toBe("signed");
  });
});

describe("reviewClock", () => {
  it("shows replay alerts without a wall-clock SLA", () => {
    expect(reviewClock(alert({ review_minutes: null }))).toEqual({ label: "No wall-clock time (replay)", tone: "neutral" });
  });

  it("escalates tone as the review window runs out", () => {
    expect(reviewClock(alert({ review_minutes: 4 })).tone).toBe("info");
    expect(reviewClock(alert({ review_minutes: 11 })).tone).toBe("warning");
    expect(reviewClock(alert({ review_minutes: 22, overdue: true }))).toEqual({ label: "Overdue by 7 min", tone: "danger" });
  });

  it("reports time to first action once reviewed", () => {
    expect(reviewClock(alert({ status: "acknowledged", review_minutes: 9 })).label).toBe("First action after 9 min");
  });
});

describe("attentionAlerts", () => {
  it("interrupts only for unseen open alerts that TrustGate allows", () => {
    const alerts = [
      alert({ alert_id: "a" }),
      alert({ alert_id: "b", trustgate: trustgate("verify_data") }),
      alert({ alert_id: "f", trustgate: trustgate("watch") }),
      alert({ alert_id: "c", status: "silent" }),
      alert({ alert_id: "d", status: "acknowledged" }),
      alert({ alert_id: "e" }),
    ];
    expect(attentionAlerts(alerts, new Set(["e"])).map((item) => item.alert_id)).toEqual(["a"]);
  });
});

describe("connectorTone and minutesLabel", () => {
  it("maps feed health to tones", () => {
    expect(connectorTone("healthy")).toBe("success");
    expect(connectorTone("degraded")).toBe("warning");
    expect(connectorTone("stale")).toBe("danger");
    expect(connectorTone("circuit_open")).toBe("danger");
    expect(connectorTone("never_connected")).toBe("neutral");
  });

  it("chooses a readable unit", () => {
    expect(minutesLabel(null)).toBe("—");
    expect(minutesLabel(42.4)).toBe("42 min");
    expect(minutesLabel(150)).toBe("2.5 h");
    expect(minutesLabel(4320)).toBe("3.0 d");
  });
});
