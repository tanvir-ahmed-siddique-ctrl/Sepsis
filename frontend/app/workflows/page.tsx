import Link from "next/link";
import { Panel, Pill } from "@/components/ui";

const FLOWS = [
  {
    title: "Missing signal → safe next action",
    who: "Nurse + integration team",
    text: "Open a patient → Data provenance. Red gaps name the required vital. Chart it now, or use Integration Hub when the gap repeats across beds. TrustGate blocks interrupts while data is unsafe.",
    links: [["Open ICU", "/"], ["Chart vitals", "/chart"], ["Integration Hub", "/integration"]],
  },
  {
    title: "Open alert → treat without click burden",
    who: "Doctor",
    text: "The ICU card has Seen and Quiet 1h. Treat first; no patient-page round trip. Escalate or final-dismiss with a reason when appropriate. Every action is audited.",
    links: [["ICU board", "/"], ["Alert queue", "/alerts"]],
  },
  {
    title: "Bedside feedback → governance evidence",
    who: "Clinician + pilot admin",
    text: "Submit usefulness/workflow feedback on the patient page. It is stored in feedback_records, summarized in pilot metrics, shown in the feedback inbox, and included in pseudonymised exports.",
    links: [["Patients", "/"], ["Feedback inbox", "/pilot"]],
  },
  {
    title: "Current shift → accountable handoff",
    who: "Whole ICU",
    text: "The strip above shows the current doctor/nurse list and switches automatically by Dhaka shift time. Staff can view it; admins can add/edit/delete or import CSV.",
    links: [["On-shift team", "/staff"], ["Handoff", "/handoff"]],
  },
  {
    title: "Local HIS/LIS → PredictRx",
    who: "Hospital IT",
    text: "Use CSV, HL7 v2, FHIR, or the outbound Vendor Adapter. PredictRx does not write into billing/registration databases. Unknown code/unit rows quarantine before scoring.",
    links: [["Connection Ladder", "/connection"], ["Integration Hub", "/integration"], ["API reference", "/api-reference"]],
  },
  {
    title: "Mapping Copilot → analyst-approved mapping",
    who: "Integration analyst",
    text: "Type only a local field name and unit. The helper proposes a target; it never sees patient values and never changes the registry. A human edits and signs the registry SHA.",
    links: [["Open Copilot", "/integration"]],
  },
];

export default function WorkflowsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Product map</p>
        <h1 className="font-display text-4xl">What happens after I see something?</h1>
        <p className="mt-2 max-w-3xl text-sm text-ink/65">
          Every panel must lead to an action, owner, and evidence trail. This page is the frontend guide—not a hidden
          developer document.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {FLOWS.map((flow) => (
          <Panel key={flow.title} title={flow.title}>
            <Pill tone="info">{flow.who}</Pill>
            <p className="mt-3 text-sm text-ink/75">{flow.text}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {flow.links.map(([label, href]) => (
                <Link key={href} href={href} className="border border-ink/20 px-3 py-1.5 text-sm text-accent">
                  {label} →
                </Link>
              ))}
            </div>
          </Panel>
        ))}
      </div>
      <Panel title="TrustGate in one line">
        <p className="text-sm text-ink/75">
          It is a deterministic safety layer in the API—not a second AI model. The score remains visible, but only
          fresh, stable, locally governed scores may interrupt clinicians.
        </p>
        <Link href="/model" className="mt-3 inline-block text-sm text-accent underline">See model and safety evidence</Link>
      </Panel>
    </div>
  );
}
