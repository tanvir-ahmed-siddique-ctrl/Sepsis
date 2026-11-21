"use client";

import { useEffect, useState } from "react";
import { accountApi } from "@/lib/account-api";
import { flash } from "@/components/FlashToast";
import { EmptyState, FileDrop, PageHeader, Pill } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";

type Organization = { id: string; name: string };
type Site = { id: string; organization_id: string; name: string };
type Document = { id: string; organization_id: string; site_id: string | null; document_key: string; version: number; title: string; document_type: string; access: string; sha256: string; scan_status: string; approval_status: string; expires_on: string | null; lifecycle_status?: string; retention_until?: string | null; review_on?: string | null; retention_policy?: string; review_due?: boolean; retention_due?: boolean };
const types = ["agreement", "proposal", "invoice_support", "licence_record", "training", "deployment", "compliance", "other_commercial"];
const input = "auralis-input mt-1.5";
const MAX_DOCUMENT_BYTES = 1_000_000;

function approvalTone(status: string) {
  if (status === "approved") return "success" as const;
  if (status === "rejected") return "danger" as const;
  return "warning" as const;
}

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
    const looksPdf = Boolean(file && (file.type === "application/pdf" || file.type === "application/x-pdf" || file.name.toLowerCase().endsWith(".pdf")));
    if (!file) {
      const msg = "Choose a PDF first.";
      setError(msg);
      flash(msg, "err");
      return;
    }
    if (file.size > MAX_DOCUMENT_BYTES || !looksPdf) {
      const msg = "Choose a PDF below 1 MB.";
      setError(msg);
      flash(msg, "err");
      return;
    }
    setError(null);
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = ""; for (const byte of bytes) binary += String.fromCharCode(byte);
      await accountApi("/v1/vendor/documents", { method: "POST", body: JSON.stringify({ ...form, site_id: form.site_id || null, expires_on: form.expires_on || null, content_b64: btoa(binary) }) });
      const ok = "Encrypted PDF recorded as a draft. Customer access begins only after scan and approval.";
      setNotice(ok);
      flash(ok);
      setFile(null);
      await load();
    } catch (cause) {
      const msg = cause instanceof Error ? cause.message : "Document upload failed";
      setError(msg);
      flash(msg, "err");
    }
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

  if (loading) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading documents">
        <div className="auralis-skeleton h-8 w-64" />
        <div className="auralis-skeleton h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={vendor ? "Vendor control plane" : "Customer portal"}
        title="Document centre"
        description="Private commercial and governance PDFs only. No patient records or raw clinical exports belong in this vault."
      />
      {error && (
        <p role="alert" className="flex items-center gap-2 rounded-lg border border-risk-high/25 bg-risk-high/[0.05] px-3.5 py-2.5 text-sm text-risk-high">
          <Icon name="alert" size={16} />
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="flex items-center gap-2 rounded-lg border border-risk-stable/25 bg-risk-stable/[0.05] px-3.5 py-2.5 text-sm text-risk-stable">
          <Icon name="check" size={16} />
          {notice}
        </p>
      )}

      <section className="auralis-panel">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Registered documents</h2>
          <span className="text-xs text-muted">{documents.length} accessible</span>
        </div>
        {!documents.length ? (
          <EmptyState
            icon="doc"
            title="No accessible documents"
            body={vendor ? "Register a PDF below. It stays a draft until it is scanned and approved." : "Documents shared with your organisation appear here after vendor approval."}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="auralis-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Scope</th>
                  <th>Version</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Retention</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <span className="font-medium text-ink">{d.title}</span>
                      <small className="block font-mono text-[11px] text-muted">SHA-256 {d.sha256.slice(0, 16)}…</small>
                    </td>
                    <td className="text-muted">
                      {d.organization_id}
                      {d.site_id ? ` / ${d.site_id}` : ""}
                    </td>
                    <td className="tabular-nums">v{d.version}</td>
                    <td className="capitalize">{d.document_type.replaceAll("_", " ")}</td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        <Pill tone={approvalTone(d.approval_status)}>{d.approval_status.replaceAll("_", " ")}</Pill>
                        <Pill>{(d.lifecycle_status || "draft").replaceAll("_", " ")}</Pill>
                      </div>
                    </td>
                    <td className="text-muted">
                      {d.retention_until || "—"}
                      {(d.review_due || d.retention_due) && <span className="ml-1 font-medium text-risk-watch">· due</span>}
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-2">
                        {d.approval_status === "approved" && d.lifecycle_status !== "destroyed" ? (
                          <a href={`/api/account/v1/documents/${encodeURIComponent(d.id)}/download`} className="auralis-btn-secondary auralis-btn-sm">
                            <Icon name="file" size={15} />
                            Download
                          </a>
                        ) : vendor && d.approval_status === "draft" ? (
                          <button type="button" onClick={() => void approve(d)} className="auralis-btn-secondary auralis-btn-sm">
                            Approve
                          </button>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                        {vendor && d.approval_status === "approved" && d.lifecycle_status !== "destroyed" && (
                          <select
                            aria-label={`Lifecycle for ${d.title}`}
                            defaultValue=""
                            onChange={(event) => {
                              if (event.target.value) void updateLifecycle(d, event.target.value);
                              event.target.value = "";
                            }}
                            className="auralis-input h-9 w-auto py-0 text-[13px]"
                          >
                            <option value="">Lifecycle</option>
                            <option value="under_review">Under review</option>
                            <option value="archived">Archive</option>
                            <option value="destroyed">Destroy</option>
                            <option value="active">Active</option>
                          </select>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {vendor && (
        <form onSubmit={(event) => void upload(event)} className="auralis-panel grid gap-4 text-sm sm:grid-cols-2">
          <div className="sm:col-span-2">
            <h2 className="text-base font-semibold text-ink">Register a PDF</h2>
            <p className="mt-1 text-sm text-muted">
              Production uploads fail closed unless encryption and an approved malware scanner are configured. Legal approval is a separate human decision.
            </p>
          </div>
          <label className="auralis-label">
            Organization
            <select required value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value, site_id: "" })} className={input}>
              <option value="">Select organization</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </label>
          <label className="auralis-label">
            Site (optional)
            <select value={form.site_id} onChange={(event) => setForm({ ...form, site_id: event.target.value })} className={input}>
              <option value="">Organization wide</option>
              {sites
                .filter((s) => s.organization_id === form.organization_id)
                .map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
            </select>
          </label>
          <label className="auralis-label">
            Stable document key
            <input required pattern="[a-z0-9][a-z0-9-]{2,79}" value={form.document_key} onChange={(event) => setForm({ ...form, document_key: event.target.value })} className={input} placeholder="e.g. master-services-agreement" />
          </label>
          <label className="auralis-label">
            Version
            <input required type="number" min="1" value={form.version} onChange={(event) => setForm({ ...form, version: Number(event.target.value) })} className={input} />
          </label>
          <label className="auralis-label">
            Title
            <input required minLength={3} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} className={input} />
          </label>
          <label className="auralis-label">
            Type
            <select value={form.document_type} onChange={(event) => setForm({ ...form, document_type: event.target.value })} className={input}>
              {types.map((type) => (
                <option key={type} value={type}>{type.replaceAll("_", " ")}</option>
              ))}
            </select>
          </label>
          <label className="auralis-label">
            Audience
            <select value={form.access} onChange={(event) => setForm({ ...form, access: event.target.value })} className={input}>
              <option value="customer_visible">Customer visible after approval</option>
              <option value="vendor_only">Vendor only</option>
            </select>
          </label>
          <label className="auralis-label">
            Owner role
            <input required minLength={2} value={form.owner_role} onChange={(event) => setForm({ ...form, owner_role: event.target.value })} className={input} />
          </label>
          <label className="auralis-label">
            Expiry (if applicable)
            <input type="date" value={form.expires_on} onChange={(event) => setForm({ ...form, expires_on: event.target.value })} className={input} />
          </label>
          <label className="auralis-label">
            Retention policy
            <select value={form.retention_policy} onChange={(event) => setForm({ ...form, retention_policy: event.target.value })} className={input}>
              <option value="contractual">Contractual</option>
              <option value="regulatory">Regulatory</option>
              <option value="operational">Operational</option>
              <option value="training">Training</option>
              <option value="legal_hold">Legal hold</option>
            </select>
          </label>
          <div className="sm:col-span-2">
            <FileDrop label="PDF document" accept="application/pdf,.pdf" acceptLabel="PDF" maxBytes={MAX_DOCUMENT_BYTES} limitLabel="1 MB" file={file} onFile={setFile} required />
          </div>
          <button type="submit" className="auralis-btn-primary justify-self-start sm:col-span-2">
            <Icon name="upload" size={16} />
            Upload draft
          </button>
        </form>
      )}
    </div>
  );
}
