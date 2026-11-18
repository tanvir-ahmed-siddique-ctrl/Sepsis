"use client";

import { useState } from "react";
import Link from "next/link";

const PURPOSES = [
  { value: "clinical_workflow", label: "Clinical workflow discussion" },
  { value: "hospital_it", label: "Hospital IT and interoperability" },
  { value: "infrastructure", label: "Infrastructure and technology assessment" },
  { value: "equipment_connectivity", label: "Medical equipment connectivity" },
  { value: "site_readiness", label: "Site-readiness assessment" },
  { value: "deployment_planning", label: "Deployment planning" },
  { value: "managed_it", label: "Managed IT services" },
  { value: "commercial", label: "Commercial / procurement discussion" },
  { value: "education", label: "Education or institutional seminar" },
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

  const field = "mt-1 block w-full border border-[#C6CECA] bg-white p-3";

  return (
    <div className="mx-auto max-w-6xl py-12">
      <div className="grid gap-12 lg:grid-cols-[.85fr_1.15fr]">
        <header>
          <p className="text-xs font-semibold uppercase tracking-[.2em] text-forest">Auralis / contact</p>
          <h1 className="mt-5 font-display text-5xl leading-tight">Request a consultation.</h1>
          <p className="mt-6 text-base leading-8 text-slate">
            Tell us about your institution and preferred meeting windows. An Auralis owner will confirm, decline or reschedule — preferred times are not booked until confirmed.
          </p>
          <ul className="mt-6 space-y-2 text-sm leading-6 text-slate">
            <li>Do not enter patient data or clinical records.</li>
            <li>Self-reported readiness is optional and is not a clinical eligibility decision.</li>
            <li>See the <Link href="/for-hospitals" className="font-semibold text-forest underline underline-offset-2">hospital adoption journey</Link> for what happens after first contact.</li>
          </ul>
        </header>

        <div className="border-t-2 border-forest bg-warm p-6 sm:p-8">
          {state === "recorded" ? (
            <div role="status">
              <h2 className="text-xl font-semibold">Consultation request recorded</h2>
              <p className="mt-3 text-sm leading-6 text-slate">{note}</p>
              <p className="mt-3 text-sm leading-6 text-slate">No deployment, quote or clinical access is confirmed by this submission.</p>
            </div>
          ) : (
            <form onSubmit={(event) => void submit(event)} className="grid gap-4 text-sm sm:grid-cols-2">
              <h2 className="text-xl font-semibold sm:col-span-2">Book a Consultation</h2>
              {state === "error" && <p role="alert" className="border-l-2 border-risk-watch p-3 sm:col-span-2">{error}</p>}

              <label className="sm:col-span-2">Institution / hospital name
                <input required minLength={2} maxLength={160} value={form.organization} onChange={(e) => setForm({ ...form, organization: e.target.value })} className={field} />
              </label>
              <label>Contact name
                <input required minLength={2} maxLength={120} value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} className={field} />
              </label>
              <label>Institutional email
                <input required type="email" maxLength={254} value={form.work_email} onChange={(e) => setForm({ ...form, work_email: e.target.value })} className={field} />
              </label>
              <label>Job title
                <input required minLength={2} maxLength={120} value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} className={field} />
              </label>
              <label>Department
                <input maxLength={120} value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className={field} />
              </label>
              <label>Country
                <input required minLength={2} maxLength={80} value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} className={field} />
              </label>
              <label>Location / city
                <input required minLength={2} maxLength={160} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className={field} />
              </label>
              <label>Hospital type
                <input required minLength={2} maxLength={80} value={form.hospital_type} onChange={(e) => setForm({ ...form, hospital_type: e.target.value })} className={field} placeholder="e.g. district hospital, tertiary ICU" />
              </label>
              <label>Approximate organisation size
                <select value={form.organization_size} onChange={(e) => setForm({ ...form, organization_size: e.target.value })} className={field}>
                  <option value="unspecified">Prefer not to say</option>
                  <option value="clinic">Clinic / outpatient</option>
                  <option value="small">Small hospital</option>
                  <option value="medium">Medium hospital</option>
                  <option value="large">Large hospital</option>
                  <option value="tertiary">Tertiary</option>
                  <option value="academic">Academic</option>
                  <option value="specialist">Specialist</option>
                  <option value="group">Hospital group / multi-site</option>
                </select>
              </label>
              <label>Self-reported digital readiness
                <select value={form.readiness_self_report} onChange={(e) => setForm({ ...form, readiness_self_report: e.target.value })} className={field}>
                  <option value="unspecified">Not sure</option>
                  <option value="foundation">Foundation</option>
                  <option value="connected">Connected</option>
                  <option value="advanced">Advanced</option>
                </select>
              </label>
              <label className="sm:col-span-2">Meeting purpose
                <select required value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} className={field}>
                  {PURPOSES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
              <label className="sm:col-span-2">Preferred dates and times
                <textarea required minLength={3} maxLength={500} rows={3} value={form.preferred_dates} onChange={(e) => setForm({ ...form, preferred_dates: e.target.value })} className={field} placeholder="e.g. Week of 5 May, mornings BDT; or 12 May 10:00–12:00" />
              </label>
              <label>Meeting modality
                <select value={form.modality} onChange={(e) => setForm({ ...form, modality: e.target.value })} className={field}>
                  <option value="online">Online</option>
                  <option value="in_person">In person</option>
                  <option value="either">Either</option>
                </select>
              </label>
              <label className="sm:col-span-2">Optional message
                <textarea maxLength={2000} rows={3} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className={field} />
              </label>

              <div className="hidden" aria-hidden="true">
                <label>Website
                  <input tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
                </label>
              </div>

              <label className="flex items-start gap-3 sm:col-span-2">
                <input required type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} className="mt-1" />
                <span>I agree to be contacted about this consultation request. I understand that preferred times are pending confirmation and that no patient or clinical data belongs in this form.</span>
              </label>

              <button disabled={state === "sending"} className="justify-self-start bg-forest px-6 py-3 font-semibold text-white disabled:opacity-50 sm:col-span-2">
                {state === "sending" ? "Recording…" : "Submit consultation request"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
