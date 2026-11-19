"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { accountApi, AccountRequestError } from "@/lib/account-api";
import { useSession } from "@/lib/session";
import { PageHeader } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";

const input = "auralis-input mt-1.5";

type Organization = { id: string; name: string };
type Site = { id: string; organization_id: string; name: string };
type Ticket = { id: string; organization_id: string; site_id: string; issue_code: string; severity: string; status: string; updated_at: string; sla_breached?: boolean; sla_target_minutes?: number | null; escalation_level?: number };
type Staff = { id: string; email: string; display_name: string; role: string; must_change_password: number };
type Account = { id: string; email: string; display_name: string; role: string; disabled: number; vendor: number; organization_ids: string[]; organization_roles: Record<string, string> };
type Asset = { id: string; organization_id: string; site_id: string; asset_tag: string; kind: string; model: string; firmware: string | null; lifecycle_state?: string; warranty_expired?: boolean };
type ComplianceTask = { id: string; organization_id: string; site_id: string; task_type: string; owner: string; status: string; evidence_ref: string | null };
const statuses = ["open", "acknowledged", "in_progress", "waiting_for_hospital", "waiting_for_vendor", "resolved", "closed"];
const complianceStates = ["not_started", "in_progress", "awaiting_hospital", "awaiting_counsel", "submitted", "approved", "rejected", "expired", "needs_renewal"];

export function VendorAccounts() {
  const { account } = useSession();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [membership, setMembership] = useState({ account_id: "", organization_id: "", role: "customer_viewer", reason: "Institutional access review" });
  const [staffForm, setStaffForm] = useState({ email: "", display_name: "", role: "support_engineer", password: "" });
  const [provisioningUri, setProvisioningUri] = useState<string | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [compliance, setCompliance] = useState<ComplianceTask[]>([]);
  const [assetForm, setAssetForm] = useState({ site_id: "", asset_tag: "", kind: "edge_appliance", model: "", firmware: "" });
  const [taskForm, setTaskForm] = useState({ site_id: "", task_type: "", owner: "" });
  const [form, setForm] = useState({ organization_id: "", organization_name: "", site_id: "", site_name: "", email: "", display_name: "", role: "customer_owner", reason: "Institutional contact approved" });
  const [invitation, setInvitation] = useState<{ token: string; expires_at: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [orgs, registered, requests, equipment, tasks] = await Promise.all([
        accountApi<{ organizations: Organization[] }>("/v1/organizations"),
        accountApi<{ sites: Site[] }>("/v1/sites"),
        accountApi<{ tickets: Ticket[] }>("/v1/tickets"),
        accountApi<{ assets: Asset[] }>("/v1/assets"),
        accountApi<{ tasks: ComplianceTask[] }>("/v1/compliance-tasks"),
      ]);
      setOrganizations(orgs.organizations); setSites(registered.sites); setTickets(requests.tickets); setAssets(equipment.assets); setCompliance(tasks.tasks); setError(null);
      if (account?.role === "root_admin") { const [team, directory] = await Promise.all([accountApi<{ staff: Staff[] }>("/v1/vendor/staff"), accountApi<{ accounts: Account[] }>("/v1/vendor/accounts")]); setStaff(team.staff); setAccounts(directory.accounts); }
    } catch (cause) {
      setError(cause instanceof AccountRequestError && cause.status === 401 ? "Vendor account sign-in required" : cause instanceof Error ? cause.message : "Account service unavailable");
    } finally { setLoading(false); }
  }, [account]);
  useEffect(() => { void load(); }, [load]);

  async function submit(path: string, body: object) {
    try { await accountApi(path, { method: "POST", body: JSON.stringify(body) }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Operation failed"); }
  }
  async function updateTicket(ticket: Ticket, status: string) {
    try { await accountApi(`/v1/tickets/${encodeURIComponent(ticket.id)}`, { method: "PATCH", body: JSON.stringify({ status, escalate: status === "acknowledged" && Boolean(ticket.sla_breached) }) }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Ticket update failed"); }
  }
  async function advanceAsset(asset: Asset, lifecycle_state: string) {
    const reason = window.prompt(`Reason to move ${asset.asset_tag} to ${lifecycle_state.replaceAll("_", " ")}`);
    if (!reason || reason.trim().length < 3) return;
    const disposition_ref = ["retired", "disposed"].includes(lifecycle_state) ? window.prompt("Disposition reference") : null;
    if (["retired", "disposed"].includes(lifecycle_state) && (!disposition_ref || disposition_ref.trim().length < 3)) return;
    try {
      await accountApi(`/v1/vendor/assets/${encodeURIComponent(asset.id)}`, {
        method: "PATCH",
        body: JSON.stringify({ lifecycle_state, reason, disposition_ref: disposition_ref || null }),
      });
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Asset lifecycle update failed"); }
  }
  async function setAccountState(person: Account) {
    const reason = window.prompt(`Reason to ${person.disabled ? "reactivate" : "disable"} ${person.display_name}`);
    if (!reason || reason.trim().length < 3) return;
    try { await accountApi(`/v1/vendor/accounts/${encodeURIComponent(person.id)}/state`, { method: "PATCH", body: JSON.stringify({ disabled: !person.disabled, reason }) }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Account update failed"); }
  }
  async function saveMembership(event: React.FormEvent) {
    event.preventDefault();
    const person = accounts.find((entry) => entry.id === membership.account_id);
    if (!person || person.vendor) return;
    const assigned = Boolean(person.organization_roles[membership.organization_id]);
    const path = `/v1/vendor/accounts/${encodeURIComponent(person.id)}/memberships${assigned ? `/${encodeURIComponent(membership.organization_id)}` : ""}`;
    try { await accountApi(path, { method: assigned ? "PATCH" : "POST", body: JSON.stringify({ organization_id: membership.organization_id, role: membership.role, reason: membership.reason }) }); await load(); setError(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Membership update failed"); }
  }
  async function revokeMembership() {
    const person = accounts.find((entry) => entry.id === membership.account_id);
    if (!person || !person.organization_roles[membership.organization_id] || membership.reason.trim().length < 3) return;
    try { await accountApi(`/v1/vendor/accounts/${encodeURIComponent(person.id)}/memberships/${encodeURIComponent(membership.organization_id)}?reason=${encodeURIComponent(membership.reason)}`, { method: "DELETE" }); await load(); setError(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Membership removal failed"); }
  }
  async function updateCompliance(task: ComplianceTask, status: string) {
    const evidence_ref = status === "approved" ? window.prompt("Approved document reference", task.evidence_ref || "") : task.evidence_ref;
    if (status === "approved" && !evidence_ref) return;
    try { await accountApi(`/v1/vendor/compliance-tasks/${encodeURIComponent(task.id)}`, { method: "PATCH", body: JSON.stringify({ status, evidence_ref }) }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Task update failed"); }
  }
  async function createStaff(event: React.FormEvent) {
    event.preventDefault();
    try { const result = await accountApi<{ user_id: string; mfa_provisioning_uri: string | null }>("/v1/vendor/staff", { method: "POST", body: JSON.stringify(staffForm) }); setProvisioningUri(result.mfa_provisioning_uri); setStaffForm((current) => ({ ...current, password: "" })); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Staff provisioning failed"); }
  }
  async function inviteCustomer(event: React.FormEvent) {
    event.preventDefault();
    setInvitation(null);
    try {
      const result = await accountApi<{ token: string; expires_at: string }>("/v1/vendor/customer-invitations", { method: "POST", body: JSON.stringify({ organization_id: form.organization_id, email: form.email, display_name: form.display_name, role: form.role, reason: form.reason }) });
      setInvitation(result);
      setError(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Invitation failed"); }
  }

  if (loading) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading vendor accounts">
        <div className="auralis-skeleton h-8 w-64" />
        <div className="auralis-skeleton h-40 w-full" />
      </div>
    );
  }
  if (error === "Vendor account sign-in required") {
    return (
      <div className="auralis-panel">
        <p className="text-sm text-ink">Sign in with a vendor account to manage organization metadata.</p>
        <Link href="/signin" className="auralis-btn-primary mt-4"><Icon name="arrow-right" size={16} />Open sign-in</Link>
      </div>
    );
  }
  if (error && organizations.length === 0) {
    return <p role="alert" className="flex items-center gap-2 rounded-lg border border-risk-watch/25 bg-risk-watch/[0.05] px-3.5 py-2.5 text-sm text-risk-watch"><Icon name="alert" size={16} />{error}</p>;
  }

  return <div className="space-y-8">
    <PageHeader eyebrow="Vendor control plane" title="Tenants & access" description="Customer account, site and support metadata. No patient chart or observation access." />
    <div className="flex flex-wrap gap-x-6 gap-y-2"><Link href="/platform/commercial" className="auralis-link">CRM, quotations, contracts, licences and payments<Icon name="arrow-right" size={16} /></Link>
    <Link href="/platform/service" className="auralis-link">Deployment, support, training and offboarding<Icon name="arrow-right" size={16} /></Link>
    <Link href="/platform/documents" className="auralis-link">Private document centre<Icon name="arrow-right" size={16} /></Link></div>
    {error && <p role="alert" className="flex items-center gap-2 rounded-lg border border-risk-watch/25 bg-risk-watch/[0.05] px-3.5 py-2.5 text-sm text-risk-watch"><Icon name="alert" size={16} />{error}</p>}
    <section className="grid gap-6 lg:grid-cols-[1fr_1.2fr]"><div className="auralis-panel"><h2 className="text-base font-semibold text-ink">Organizations</h2><div className="mt-4 divide-y divide-border border-y border-border">{organizations.map((org) => <p key={org.id} className="flex justify-between gap-3 py-3"><span>{org.name}</span><span className="font-mono text-xs text-muted">{org.id}</span></p>)}{!organizations.length && <p className="py-3 text-sm text-muted">No organizations registered.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/organizations", { organization_id: form.organization_id, name: form.organization_name }); }} className="auralis-panel grid content-start gap-3 text-sm"><h3 className="text-sm font-semibold text-ink">Register organization</h3><label className="auralis-label">Organization ID<input value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value })} required pattern="[a-z0-9][a-z0-9-]{2,62}" className={input} /></label><label className="auralis-label">Name<input value={form.organization_name} onChange={(event) => setForm({ ...form, organization_name: event.target.value })} required className={input} /></label><button className="justify-self-start auralis-btn-primary">Register</button></form></section>
    <section className="grid gap-6 lg:grid-cols-[1fr_1.2fr]"><div className="auralis-panel"><h2 className="text-base font-semibold text-ink">Sites</h2><div className="mt-4 divide-y divide-border border-y border-border">{sites.map((site) => <p key={site.id} className="flex justify-between gap-3 py-3"><span>{site.name} <small className="text-muted">{site.organization_id}</small></span><span className="font-mono text-xs text-muted">{site.id}</span></p>)}{!sites.length && <p className="py-3 text-sm text-muted">No sites registered.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/sites", { site_id: form.site_id, organization_id: form.organization_id, name: form.site_name }); }} className="auralis-panel grid content-start gap-3 text-sm"><h3 className="text-sm font-semibold text-ink">Register site</h3><label className="auralis-label">Organization<select value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value })} required className={input}><option value="">Select organization</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label className="auralis-label">Site ID<input value={form.site_id} onChange={(event) => setForm({ ...form, site_id: event.target.value })} required pattern="[a-z0-9][a-z0-9-]{2,62}" className={input} /></label><label className="auralis-label">Name<input value={form.site_name} onChange={(event) => setForm({ ...form, site_name: event.target.value })} required className={input} /></label><button className="justify-self-start auralis-btn-primary">Register</button></form></section>
    <section className="grid gap-6 lg:grid-cols-[1fr_1.2fr]"><div className="auralis-panel"><h2 className="text-base font-semibold text-ink">Customer access</h2><p className="mt-3 text-sm leading-6 text-muted">Invite an approved institutional contact. The one-time token expires after 48 hours; provide it through an approved secure channel. The contact chooses their own password before access begins.</p>{invitation && <p role="status" className="mt-4 break-all flex items-center gap-2 rounded-lg border border-risk-stable/25 bg-risk-stable/[0.05] px-3.5 py-2.5 text-sm text-risk-stable text-xs">Copy once: <code>{invitation.token}</code><br />Expires: {invitation.expires_at}. Activation page: <code>/activate</code></p>}</div><form onSubmit={(event) => void inviteCustomer(event)} className="auralis-panel grid gap-3 text-sm"><label className="auralis-label">Organization<select value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value })} required className={input}><option value="">Select organization</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label className="auralis-label">Work email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required className={input} /></label><label className="auralis-label">Display name<input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} required className={input} /></label><label className="auralis-label">Organization role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} className={input}>{["customer_owner", "procurement_finance", "technical_contact", "customer_viewer"].map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label><label className="auralis-label">Approval reason<input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} required minLength={3} className={input} /></label><button className="justify-self-start auralis-btn-primary">Create invitation</button></form></section>
    <section className="auralis-panel"><h2 className="text-base font-semibold text-ink">Operational support queue</h2><div className="mt-4 overflow-x-auto"><table className="auralis-table"><thead className="border-b border-border text-xs uppercase tracking-wide text-muted"><tr><th className="py-3">Organization</th><th>Site</th><th>Issue</th><th>Severity</th><th>SLA</th><th>Status</th></tr></thead><tbody className="divide-y divide-border">{tickets.map((ticket) => <tr key={ticket.id}><td className="py-3">{ticket.organization_id}</td><td className="font-mono text-xs">{ticket.site_id}</td><td>{ticket.issue_code.replaceAll("_", " ")}</td><td>{ticket.severity}</td><td>{ticket.sla_breached ? "breached" : ticket.sla_target_minutes ? `${ticket.sla_target_minutes} min` : "—"}{ticket.escalation_level ? ` · esc ${ticket.escalation_level}` : ""}</td><td><select aria-label={`Status for ${ticket.id}`} value={ticket.status} onChange={(event) => void updateTicket(ticket, event.target.value)} className="auralis-input h-9 w-auto py-0 text-[13px]">{statuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></td></tr>)}</tbody></table>{!tickets.length && <p className="py-4 text-sm text-muted">No support requests.</p>}</div></section>
    {account?.role === "root_admin" && <section className="grid gap-6 lg:grid-cols-2"><div className="auralis-panel"><h2 className="text-base font-semibold text-ink">Vendor team</h2><div className="mt-4 divide-y divide-border border-y border-border">{staff.map((person) => <p key={person.id} className="py-3 text-sm">{person.display_name} · {person.role.replaceAll("_", " ")}<small className="block text-muted">{person.email}{person.must_change_password ? " · password change required" : ""}</small></p>)}</div></div><form onSubmit={(event) => void createStaff(event)} className="auralis-panel grid content-start gap-3 text-sm"><h3 className="text-sm font-semibold text-ink">Provision limited vendor access</h3><label className="auralis-label">Work email<input required type="email" value={staffForm.email} onChange={(event) => setStaffForm({ ...staffForm, email: event.target.value })} className={input} /></label><label className="auralis-label">Name<input required minLength={2} value={staffForm.display_name} onChange={(event) => setStaffForm({ ...staffForm, display_name: event.target.value })} className={input} /></label><label className="auralis-label">Role<select value={staffForm.role} onChange={(event) => setStaffForm({ ...staffForm, role: event.target.value })} className={input}>{["platform_admin", "deployment_engineer", "support_engineer", "finance_legal", "security_compliance"].map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label><label className="auralis-label">Initial password<input required type="password" minLength={12} value={staffForm.password} onChange={(event) => setStaffForm({ ...staffForm, password: event.target.value })} className={input} /></label><button className="justify-self-start auralis-btn-primary">Provision staff</button>{provisioningUri && <p role="status" className="break-all flex items-center gap-2 rounded-lg border border-risk-stable/25 bg-risk-stable/[0.05] px-3.5 py-2.5 text-sm text-risk-stable text-xs">Copy this authenticator provisioning URI once through an approved channel: <code>{provisioningUri}</code></p>}</form></section>}
    <section className="grid gap-6 lg:grid-cols-2"><div className="auralis-panel"><h2 className="text-base font-semibold text-ink">Managed edge assets</h2><div className="mt-4 divide-y divide-border border-y border-border text-sm">{assets.map((asset) => <div key={asset.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><p>{asset.asset_tag} · {asset.kind.replaceAll("_", " ")} · {asset.model}<small className="block text-muted">{asset.organization_id} / {asset.site_id} · {(asset.lifecycle_state || "commissioned").replaceAll("_", " ")}{asset.warranty_expired ? " · warranty expired" : ""}</small></p><select aria-label={`Lifecycle for ${asset.id}`} defaultValue="" onChange={(event) => { if (event.target.value) void advanceAsset(asset, event.target.value); event.target.value = ""; }} className="auralis-input h-9 w-auto py-0 text-[13px]"><option value="">Advance lifecycle</option>{["received", "commissioned", "in_service", "maintenance", "retired", "disposed"].map((state) => <option key={state} value={state}>{state.replaceAll("_", " ")}</option>)}</select></div>)}{!assets.length && <p className="py-3 text-muted">No assets registered.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/assets", { ...assetForm, firmware: assetForm.firmware || null }); }} className="auralis-panel grid content-start gap-3 text-sm"><h3 className="text-sm font-semibold text-ink">Register deployed equipment</h3><label className="auralis-label">Site<select required value={assetForm.site_id} onChange={(event) => setAssetForm({ ...assetForm, site_id: event.target.value })} className={input}><option value="">Select site</option>{sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label className="auralis-label">Asset tag<input required minLength={3} value={assetForm.asset_tag} onChange={(event) => setAssetForm({ ...assetForm, asset_tag: event.target.value })} className={input} /></label><label className="auralis-label">Kind<select value={assetForm.kind} onChange={(event) => setAssetForm({ ...assetForm, kind: event.target.value })} className={input}>{["edge_appliance", "network_gateway", "storage", "ups", "bedside_interface", "other"].map((kind) => <option key={kind} value={kind}>{kind.replaceAll("_", " ")}</option>)}</select></label><label className="auralis-label">Model<input required minLength={2} value={assetForm.model} onChange={(event) => setAssetForm({ ...assetForm, model: event.target.value })} className={input} /></label><label className="auralis-label">Firmware (if known)<input value={assetForm.firmware} onChange={(event) => setAssetForm({ ...assetForm, firmware: event.target.value })} className={input} /></label><button className="justify-self-start auralis-btn-primary">Register asset</button></form></section>
    <section className="grid gap-6 lg:grid-cols-2"><div className="auralis-panel"><h2 className="text-base font-semibold text-ink">Regulatory coordination</h2><div className="mt-4 divide-y divide-border border-y border-border text-sm">{compliance.map((task) => <div key={task.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><span>{task.task_type.replaceAll("_", " ")}<small className="block text-muted">{task.organization_id} / {task.site_id} · {task.owner}{task.evidence_ref ? ` · ${task.evidence_ref}` : ""}</small></span><select aria-label={`Status for compliance task ${task.id}`} value={task.status} onChange={(event) => void updateCompliance(task, event.target.value)} className="auralis-input h-9 w-auto py-0 text-[13px]">{complianceStates.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></div>)}{!compliance.length && <p className="py-3 text-muted">No coordination tasks.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/compliance-tasks", taskForm); }} className="auralis-panel grid content-start gap-3 text-sm"><h3 className="text-sm font-semibold text-ink">Create coordination task</h3><label className="auralis-label">Site<select required value={taskForm.site_id} onChange={(event) => setTaskForm({ ...taskForm, site_id: event.target.value })} className={input}><option value="">Select site</option>{sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label className="auralis-label">Task type<input required minLength={3} value={taskForm.task_type} onChange={(event) => setTaskForm({ ...taskForm, task_type: event.target.value })} className={input} /></label><label className="auralis-label">Responsible partner or owner<input required minLength={2} value={taskForm.owner} onChange={(event) => setTaskForm({ ...taskForm, owner: event.target.value })} className={input} /></label><button className="justify-self-start auralis-btn-primary">Create task</button></form></section>
    {account?.role === "root_admin" && <section className="auralis-panel"><h2 className="text-base font-semibold text-ink">Account access</h2><p className="mt-2 text-sm text-muted">Disabling an account or changing organization membership immediately revokes its sessions.</p><div className="mt-4 divide-y divide-border border-y border-border">{accounts.map((person) => <div key={person.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"><div><strong>{person.display_name}</strong><span className="ml-2 text-muted">{person.role.replaceAll("_", " ")}</span><p className="text-xs text-muted">{person.email} · {Object.entries(person.organization_roles).map(([org, role]) => `${org}: ${role.replaceAll("_", " ")}`).join(", ") || "Vendor"} · {person.disabled ? "Disabled" : "Active"}</p></div>{person.role !== "root_admin" && <button type="button" onClick={() => void setAccountState(person)} className="auralis-btn-secondary auralis-btn-sm">{person.disabled ? "Reactivate" : "Disable access"}</button>}</div>)}</div><form onSubmit={(event) => void saveMembership(event)} className="mt-6 grid gap-3 text-sm sm:grid-cols-2"><h3 className="sm:col-span-2 text-sm font-semibold text-ink">Assign or change customer membership</h3><label className="auralis-label">Customer account<select required value={membership.account_id} onChange={(event) => setMembership({ ...membership, account_id: event.target.value })} className={input}><option value="">Select account</option>{accounts.filter((person) => !person.vendor).map((person) => <option key={person.id} value={person.id}>{person.display_name} · {person.email}</option>)}</select></label><label className="auralis-label">Organization<select required value={membership.organization_id} onChange={(event) => setMembership({ ...membership, organization_id: event.target.value })} className={input}><option value="">Select organization</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label className="auralis-label">Role<select value={membership.role} onChange={(event) => setMembership({ ...membership, role: event.target.value })} className={input}>{["customer_owner", "procurement_finance", "technical_contact", "customer_viewer"].map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label><label className="auralis-label">Audited reason<input required minLength={3} value={membership.reason} onChange={(event) => setMembership({ ...membership, reason: event.target.value })} className={input} /></label><div className="flex gap-3 sm:col-span-2"><button className="auralis-btn-primary">Save membership</button><button type="button" onClick={() => void revokeMembership()} disabled={!accounts.find((person) => person.id === membership.account_id)?.organization_roles[membership.organization_id]} className="auralis-btn-secondary disabled:opacity-40">Revoke membership</button></div></form></section>}
  </div>;
}
