"use client";

import { useEffect, useState } from "react";
import { accountApi } from "@/lib/account-api";

type Organization = { id: string; name: string };
type Site = { id: string; organization_id: string; name: string };
type Document = { id: string; organization_id: string; site_id: string | null; document_key: string; version: number; title: string; document_type: string; access: string; sha256: string; scan_status: string; approval_status: string; expires_on: string | null; lifecycle_status?: string; retention_until?: string | null; review_on?: string | null; retention_policy?: string; review_due?: boolean; retention_due?: boolean };
const types = ["agreement", "proposal", "invoice_support", "licence_record", "training", "deployment", "compliance", "other_commercial"];
const input = "mt-1 block w-full border border-[#C6CECA] bg-white p-2";

export function DocumentWorkspace({ vendor }: { vendor: boolean }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [form, setForm] = useState({ organization_id: "", site_id: "", document_key: "", version: 1, title: "", document_type: "agreement", access: "customer_visible", owner_role: "", expires_on: "", retention_policy: "contractual" });
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  async function load() {
    try {
      const [d, o, s] = await Promise.all([accountApi<{ documents: Document[] }>("/v1/documents"), accountApi<{ organizations: Organization[] }>("/v1/organizations"), accountApi<{ sites: Site[] }>("/v1/sites")]);
      setDocuments(d.documents); setOrgs(o.organizations); setSites(s.sites); setError(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Document register unavailable"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  async function upload(event: React.FormEvent) {
    event.preventDefault();
    if (!file || file.size > 1_000_000 || file.type !== "application/pdf") { setError("Choose a PDF below 1 MB"); return; }
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = ""; for (const byte of bytes) binary += String.fromCharCode(byte);
      await accountApi("/v1/vendor/documents", { method: "POST", body: JSON.stringify({ ...form, site_id: form.site_id || null, expires_on: form.expires_on || null, content_b64: btoa(binary) }) });
      setNotice("Encrypted PDF recorded as a draft. Customer access begins only after scan and approval."); setFile(null); await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Document upload failed"); }
  }
  async function approve(document: Document) {
    const reason = window.prompt("Approval reason and source reference"); if (!reason || reason.length < 3) return;
    try { await accountApi(`/v1/vendor/documents/${document.id}`, { method: "PATCH", body: JSON.stringify({ reason }) }); setNotice("Document approved for its configured audience."); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Approval failed"); }
  }
  async function updateLifecycle(document: Document, lifecycle_status: string) {
    const reason = window.prompt(`Reason to mark document ${lifecycle_status.replaceAll("_", " ")}`);
    if (!reason || reason.length < 3) return;
    try {
      await accountApi(`/v1/vendor/documents/${document.id}/lifecycle`, { method: "PATCH", body: JSON.stringify({ lifecycle_status, reason }) });
      setNotice(`Document lifecycle set to ${lifecycle_status.replaceAll("_", " ")}.`);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Lifecycle update failed"); }
  }
  if (loading) return <p role="status" className="py-8 text-sm text-slate">Loading documents…</p>;
  return <div className="space-y-9"><header className="border-b border-border pb-7"><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal">{vendor ? "Vendor Control Plane" : "Customer Portal"}</p><h1 className="mt-3 font-display text-4xl font-semibold tracking-tight">Document centre</h1><p className="mt-3 text-sm text-muted">Private commercial and governance PDFs only. No patient records or raw clinical exports belong in this vault.</p></header>{error && <p role="alert" className="border-l-2 border-risk-watch bg-warm p-4 text-sm">{error}</p>}{notice && <p role="status" className="border-l-2 border-forest bg-warm p-4 text-sm">{notice}</p>}<section><h2 className="text-xl font-semibold">Registered documents</h2><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-[#D6DCD8] text-xs uppercase tracking-wider text-slate"><th className="py-3">Title</th><th>Scope</th><th>Version</th><th>Type</th><th>Status</th><th>Retention</th><th>Action</th></tr></thead><tbody>{documents.map((d) => <tr key={d.id} className="border-b border-[#D6DCD8]"><td className="py-3 font-semibold">{d.title}<small className="block font-mono text-[11px] font-normal text-slate">SHA-256 {d.sha256.slice(0, 16)}…</small></td><td>{d.organization_id}{d.site_id ? ` / ${d.site_id}` : ""}</td><td>{d.version}</td><td>{d.document_type.replaceAll("_", " ")}</td><td>{d.approval_status.replaceAll("_", " ")} · {(d.lifecycle_status || "draft").replaceAll("_", " ")}</td><td>{d.retention_until || "—"}{d.review_due || d.retention_due ? " · due" : ""}</td><td className="space-x-2">{d.approval_status === "approved" && d.lifecycle_status !== "destroyed" ? <a href={`/api/account/v1/documents/${encodeURIComponent(d.id)}/download`} className="text-forest underline underline-offset-2">Download PDF ↓</a> : vendor && d.approval_status === "draft" ? <button type="button" onClick={() => void approve(d)} className="border px-3 py-1">Approve</button> : "—"}{vendor && d.approval_status === "approved" && d.lifecycle_status !== "destroyed" && <select aria-label={`Lifecycle for ${d.id}`} defaultValue="" onChange={(event) => { if (event.target.value) void updateLifecycle(d, event.target.value); event.target.value = ""; }} className="border bg-white p-1"><option value="">Lifecycle</option><option value="under_review">Under review</option><option value="archived">Archive</option><option value="destroyed">Destroy</option><option value="active">Active</option></select>}</td></tr>)}</tbody></table>{!documents.length && <p className="py-4 text-sm text-slate">No accessible document.</p>}</div></section>{vendor && <form onSubmit={(event) => void upload(event)} className="grid max-w-3xl gap-4 border-t border-[#D6DCD8] pt-7 text-sm sm:grid-cols-2"><h2 className="text-xl font-semibold sm:col-span-2">Register a PDF</h2><p className="text-xs text-slate sm:col-span-2">Production uploads fail closed unless encryption and an approved malware scanner are configured. Legal approval is a separate human decision.</p><label>Organization<select required value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value, site_id: "" })} className={input}><option value="">Select organization</option>{orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label><label>Site (optional)<select value={form.site_id} onChange={(event) => setForm({ ...form, site_id: event.target.value })} className={input}><option value="">Organization wide</option>{sites.filter((s) => s.organization_id === form.organization_id).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label>Stable document key<input required pattern="[a-z0-9][a-z0-9-]{2,79}" value={form.document_key} onChange={(event) => setForm({ ...form, document_key: event.target.value })} className={input} /></label><label>Version<input required type="number" min="1" value={form.version} onChange={(event) => setForm({ ...form, version: Number(event.target.value) })} className={input} /></label><label>Title<input required minLength={3} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} className={input} /></label><label>Type<select value={form.document_type} onChange={(event) => setForm({ ...form, document_type: event.target.value })} className={input}>{types.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}</select></label><label>Audience<select value={form.access} onChange={(event) => setForm({ ...form, access: event.target.value })} className={input}><option value="customer_visible">Customer visible after approval</option><option value="vendor_only">Vendor only</option></select></label><label>Owner role<input required minLength={2} value={form.owner_role} onChange={(event) => setForm({ ...form, owner_role: event.target.value })} className={input} /></label><label>Expiry (if applicable)<input type="date" value={form.expires_on} onChange={(event) => setForm({ ...form, expires_on: event.target.value })} className={input} /></label><label>Retention policy<select value={form.retention_policy} onChange={(event) => setForm({ ...form, retention_policy: event.target.value })} className={input}><option value="contractual">Contractual</option><option value="regulatory">Regulatory</option><option value="operational">Operational</option><option value="training">Training</option><option value="legal_hold">Legal hold</option></select></label><label>PDF (1 MB maximum)<input required type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} className={input} /></label><button className="justify-self-start bg-forest px-4 py-2 font-semibold text-white sm:col-span-2">Upload draft</button></form>}</div>;
}
