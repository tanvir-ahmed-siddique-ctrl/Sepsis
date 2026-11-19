"use client";

import { useState } from "react";
import Link from "next/link";
import { Reveal } from "@/components/marketing/MotionPrimitives";
import { Icon } from "@/components/ui/Icon";

const PURPOSES = [
  { value: "site_readiness", label: "Site-readiness assessment" },
  { value: "clinical_workflow", label: "ICU clinical workflow discussion" },
  { value: "hospital_it", label: "HL7 / FHIR & hospital IT integration" },
  { value: "infrastructure", label: "Servers, network & device readiness" },
  { value: "deployment_planning", label: "Silent pilot & deployment planning" },
  { value: "managed_it", label: "Managed IT & support services" },
  { value: "commercial", label: "Commercial / procurement inquiry" },
  { value: "education", label: "Clinical training or seminar" },
] as const;

const empty = {
  organization: "",
  contact_name: "",
  work_email: "",
  job_title: "",
  department: "",
  country: "",
  location: "",
  hospital_type: "",
  organization_size: "unspecified",
  readiness_self_report: "unspecified",
  purpose: "site_readiness",
  preferred_dates: "",
  modality: "online",
  message: "",
  consent: false,
  website: "",
};

export default function ContactPage() {
  const [form, setForm] = useState(empty);
  const [state, setState] = useState<"idle" | "sending" | "recorded" | "error">("idle");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setState("sending");
    setError("");
    try {
      const response = await fetch("/api/consultations", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-Auralis-Request": "1" },
        body: JSON.stringify({
          ...form,
          department: form.department || null,
          message: form.message || null,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Request could not be recorded");
      setNote(typeof result.note === "string" ? result.note : "Preferred times are pending confirmation.");
      setState("recorded");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Consultation intake unavailable");
      setState("error");
    }
  }

  const field = "mt-1.5 block w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm text-ink focus:border-teal focus:outline-none";

  return (
    <div className="bg-[#FAFBFA] py-14 lg:py-20">
      <div className="auralis-container-public">
        <div className="grid gap-10 lg:grid-cols-[0.82fr_1.18fr] lg:items-start">
          <Reveal as="header" className="space-y-6">
            <div>
              <span className="auralis-eyebrow">Book a Consultation</span>
              <h1 className="mt-4 font-display text-4xl font-semibold leading-tight tracking-tight text-ink">
                Talk with our clinical & engineering team.
              </h1>
              <p className="mt-3 text-base leading-7 text-muted">
                Share your hospital details and preferred meeting times. Our team will confirm a slot with you directly.
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-white p-6">
              <p className="text-xs font-semibold uppercase tracking-wider text-teal">What to expect</p>
              <ul className="mt-3 space-y-2.5 text-sm text-muted">
                <li>• Preferred times stay pending until our team confirms.</li>
                <li>• Please do not include any patient data in this form.</li>
                <li>
                  • Want to try the software right now?{" "}
                  <Link href="/signin" className="font-semibold text-teal hover:underline">
                    Open the live ICU board
                  </Link>
                </li>
              </ul>
            </div>
          </Reveal>

          <Reveal delayMs={80} className="rounded-2xl border border-border bg-white p-6 shadow-sm sm:p-8">
            {state === "recorded" ? (
              <div role="status" className="py-6">
                <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal">Request Received</span>
                <h2 className="mt-3 font-display text-2xl font-semibold text-ink">Consultation request recorded</h2>
                <p className="mt-2 text-sm leading-6 text-muted">{note}</p>
              </div>
            ) : (
              <form onSubmit={(event) => void submit(event)} className="grid gap-4 text-sm sm:grid-cols-2">
                {state === "error" && (
                  <p role="alert" className="rounded-lg border border-risk-high/30 bg-risk-high/5 p-3 text-risk-high sm:col-span-2">
                    {error}
                  </p>
                )}

                <label className="sm:col-span-2">
                  <span className="text-xs font-semibold text-ink">Hospital / Institution Name *</span>
                  <input required minLength={2} maxLength={160} value={form.organization} onChange={(e) => setForm({ ...form, organization: e.target.value })} className={field} />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">Your Name *</span>
                  <input required minLength={2} maxLength={120} value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} className={field} />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">Work Email *</span>
                  <input required type="email" maxLength={254} value={form.work_email} onChange={(e) => setForm({ ...form, work_email: e.target.value })} className={field} />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">Job Title *</span>
                  <input required minLength={2} maxLength={120} value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} className={field} />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">Department</span>
                  <input maxLength={120} value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className={field} />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">Country *</span>
                  <input required minLength={2} maxLength={80} value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} className={field} />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">City *</span>
                  <input required minLength={2} maxLength={160} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className={field} />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">Hospital Type *</span>
                  <input required minLength={2} maxLength={80} value={form.hospital_type} onChange={(e) => setForm({ ...form, hospital_type: e.target.value })} className={field} placeholder="e.g. Tertiary, Private ICU" />
                </label>
                <label>
                  <span className="text-xs font-semibold text-ink">Meeting Format</span>
                  <select value={form.modality} onChange={(e) => setForm({ ...form, modality: e.target.value })} className={field}>
                    <option value="online">Online</option>
                    <option value="in_person">In person</option>
                    <option value="either">Either</option>
                  </select>
                </label>
                <label className="sm:col-span-2">
                  <span className="text-xs font-semibold text-ink">Topic *</span>
                  <select required value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} className={field}>
                    {PURPOSES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="sm:col-span-2">
                  <span className="text-xs font-semibold text-ink">Preferred Dates & Times *</span>
                  <textarea required minLength={3} maxLength={500} rows={2} value={form.preferred_dates} onChange={(e) => setForm({ ...form, preferred_dates: e.target.value })} className={field} placeholder="e.g. Next Tuesday 10:00–12:00" />
                </label>
                <label className="sm:col-span-2">
                  <span className="text-xs font-semibold text-ink">Optional Notes</span>
                  <textarea maxLength={2000} rows={2} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className={field} />
                </label>

                <div className="hidden" aria-hidden="true">
                  <input tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
                </div>

                <label className="flex items-start gap-2.5 text-xs text-muted sm:col-span-2">
                  <input required type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} className="mt-0.5" />
                  <span>I consent to be contacted regarding this request and confirm no patient data is included.</span>
                </label>

                <button disabled={state === "sending"} className="auralis-btn-primary justify-self-start px-7 disabled:opacity-50 sm:col-span-2">
                  {state === "sending" ? "Submitting…" : "Request consultation"}
                  {state !== "sending" && <Icon name="arrow-right" size={16} />}
                </button>
              </form>
            )}
          </Reveal>
        </div>
      </div>
    </div>
  );
}
