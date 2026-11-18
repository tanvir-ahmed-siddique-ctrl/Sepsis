"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { accountApi, AccountRequestError } from "@/lib/account-api";
import { useSession } from "@/lib/session";

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

  if (loading) return <p role="status" className="py-12 text-sm text-slate">Loading vendor accounts…</p>;
  if (error === "Vendor account sign-in required") return <div className="border-l-2 border-forest bg-warm p-6"><p>Sign in with a vendor account to manage organization metadata.</p><Link href="/signin" className="mt-4 inline-block font-semibold text-forest underline">Open sign-in</Link></div>;
  if (error && organizations.length === 0) return <p role="alert" className="border-l-2 border-risk-watch bg-warm p-6">{error}</p>;

  return <div className="space-y-10">
    <header className="border-b border-border pb-7"><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal">Vendor Control Plane</p><h1 className="mt-3 font-display text-4xl font-semibold tracking-tight">Tenants & access</h1><p className="mt-3 text-sm text-muted">Customer account, site and support metadata. No patient chart or observation access.</p></header>
    <Link href="/platform/commercial" className="inline-block text-sm font-semibold text-forest underline underline-offset-2">Open CRM, quotations, contracts, licences, invoices and payments →</Link>
    <Link href="/platform/service" className="ml-5 inline-block text-sm font-semibold text-forest underline underline-offset-2">Open deployment, support, training and offboarding →</Link>
    <Link href="/platform/documents" className="ml-5 inline-block text-sm font-semibold text-forest underline underline-offset-2">Open private document centre →</Link>
    {error && <p role="alert" className="border-l-2 border-risk-watch bg-warm p-4 text-sm">{error}</p>}
    <section className="grid gap-7 lg:grid-cols-[1fr_1.2fr]"><div><h2 className="text-xl font-semibold">Organizations</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{organizations.map((org) => <p key={org.id} className="flex justify-between gap-3 py-3"><span>{org.name}</span><span className="font-mono text-xs text-slate">{org.id}</span></p>)}{!organizations.length && <p className="py-3 text-sm text-slate">No organizations registered.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/organizations", { organization_id: form.organization_id, name: form.organization_name }); }} className="grid content-start gap-3 text-sm"><h3 className="font-semibold">Register organization</h3><label>Organization ID<input value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value })} required pattern="[a-z0-9][a-z0-9-]{2,62}" className="mt-1 block w-full border p-2" /></label><label>Name<input value={form.organization_name} onChange={(event) => setForm({ ...form, organization_name: event.target.value })} required className="mt-1 block w-full border p-2" /></label><button className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Register</button></form></section>
    <section className="grid gap-7 border-t border-[#D6DCD8] pt-7 lg:grid-cols-[1fr_1.2fr]"><div><h2 className="text-xl font-semibold">Sites</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{sites.map((site) => <p key={site.id} className="flex justify-between gap-3 py-3"><span>{site.name} <small className="text-slate">{site.organization_id}</small></span><span className="font-mono text-xs text-slate">{site.id}</span></p>)}{!sites.length && <p className="py-3 text-sm text-slate">No sites registered.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/sites", { site_id: form.site_id, organization_id: form.organization_id, name: form.site_name }); }} className="grid content-start gap-3 text-sm"><h3 className="font-semibold">Register site</h3><label>Organization<select value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value })} required className="mt-1 block w-full border bg-white p-2"><option value="">Select organization</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label>Site ID<input value={form.site_id} onChange={(event) => setForm({ ...form, site_id: event.target.value })} required pattern="[a-z0-9][a-z0-9-]{2,62}" className="mt-1 block w-full border p-2" /></label><label>Name<input value={form.site_name} onChange={(event) => setForm({ ...form, site_name: event.target.value })} required className="mt-1 block w-full border p-2" /></label><button className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Register</button></form></section>
    <section className="grid gap-7 border-t border-[#D6DCD8] pt-7 lg:grid-cols-[1fr_1.2fr]"><div><h2 className="text-xl font-semibold">Customer access</h2><p className="mt-3 text-sm leading-6 text-slate">Invite an approved institutional contact. The one-time token expires after 48 hours; provide it through an approved secure channel. The contact chooses their own password before access begins.</p>{invitation && <p role="status" className="mt-4 break-all border-l-2 border-forest bg-warm p-3 text-xs">Copy once: <code>{invitation.token}</code><br />Expires: {invitation.expires_at}. Activation page: <code>/activate</code></p>}</div><form onSubmit={(event) => void inviteCustomer(event)} className="grid gap-3 text-sm"><label>Organization<select value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: event.target.value })} required className="mt-1 block w-full border bg-white p-2"><option value="">Select organization</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label>Work email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required className="mt-1 block w-full border p-2" /></label><label>Display name<input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} required className="mt-1 block w-full border p-2" /></label><label>Organization role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} className="mt-1 block w-full border bg-white p-2">{["customer_owner", "procurement_finance", "technical_contact", "customer_viewer"].map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label><label>Approval reason<input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} required minLength={3} className="mt-1 block w-full border p-2" /></label><button className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Create invitation</button></form></section>
    <section className="border-t border-[#D6DCD8] pt-7"><h2 className="text-xl font-semibold">Operational support queue</h2><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-[#D6DCD8] text-xs uppercase tracking-wide text-slate"><tr><th className="py-3">Organization</th><th>Site</th><th>Issue</th><th>Severity</th><th>SLA</th><th>Status</th></tr></thead><tbody className="divide-y divide-[#D6DCD8]">{tickets.map((ticket) => <tr key={ticket.id}><td className="py-3">{ticket.organization_id}</td><td className="font-mono text-xs">{ticket.site_id}</td><td>{ticket.issue_code.replaceAll("_", " ")}</td><td>{ticket.severity}</td><td>{ticket.sla_breached ? "breached" : ticket.sla_target_minutes ? `${ticket.sla_target_minutes} min` : "—"}{ticket.escalation_level ? ` · esc ${ticket.escalation_level}` : ""}</td><td><select aria-label={`Status for ${ticket.id}`} value={ticket.status} onChange={(event) => void updateTicket(ticket, event.target.value)} className="border bg-white p-1">{statuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></td></tr>)}</tbody></table>{!tickets.length && <p className="py-4 text-sm text-slate">No support requests.</p>}</div></section>
    {account?.role === "root_admin" && <section className="grid gap-8 border-t border-[#D6DCD8] pt-7 lg:grid-cols-2"><div><h2 className="text-xl font-semibold">Vendor team</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{staff.map((person) => <p key={person.id} className="py-3 text-sm">{person.display_name} · {person.role.replaceAll("_", " ")}<small className="block text-slate">{person.email}{person.must_change_password ? " · password change required" : ""}</small></p>)}</div></div><form onSubmit={(event) => void createStaff(event)} className="grid content-start gap-3 text-sm"><h3 className="font-semibold">Provision limited vendor access</h3><label>Work email<input required type="email" value={staffForm.email} onChange={(event) => setStaffForm({ ...staffForm, email: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Name<input required minLength={2} value={staffForm.display_name} onChange={(event) => setStaffForm({ ...staffForm, display_name: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Role<select value={staffForm.role} onChange={(event) => setStaffForm({ ...staffForm, role: event.target.value })} className="mt-1 block w-full border bg-white p-2">{["platform_admin", "deployment_engineer", "support_engineer", "finance_legal", "security_compliance"].map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label><label>Initial password<input required type="password" minLength={12} value={staffForm.password} onChange={(event) => setStaffForm({ ...staffForm, password: event.target.value })} className="mt-1 block w-full border p-2" /></label><button className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Provision staff</button>{provisioningUri && <p role="status" className="break-all border-l-2 border-forest p-3 text-xs">Copy this authenticator provisioning URI once through an approved channel: <code>{provisioningUri}</code></p>}</form></section>}
    <section className="grid gap-8 border-t border-[#D6DCD8] pt-7 lg:grid-cols-2"><div><h2 className="text-xl font-semibold">Managed edge assets</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8] text-sm">{assets.map((asset) => <div key={asset.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><p>{asset.asset_tag} · {asset.kind.replaceAll("_", " ")} · {asset.model}<small className="block text-slate">{asset.organization_id} / {asset.site_id} · {(asset.lifecycle_state || "commissioned").replaceAll("_", " ")}{asset.warranty_expired ? " · warranty expired" : ""}</small></p><select aria-label={`Lifecycle for ${asset.id}`} defaultValue="" onChange={(event) => { if (event.target.value) void advanceAsset(asset, event.target.value); event.target.value = ""; }} className="border bg-white p-1"><option value="">Advance lifecycle</option>{["received", "commissioned", "in_service", "maintenance", "retired", "disposed"].map((state) => <option key={state} value={state}>{state.replaceAll("_", " ")}</option>)}</select></div>)}{!assets.length && <p className="py-3 text-slate">No assets registered.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/assets", { ...assetForm, firmware: assetForm.firmware || null }); }} className="grid content-start gap-3 text-sm"><h3 className="font-semibold">Register deployed equipment</h3><label>Site<select required value={assetForm.site_id} onChange={(event) => setAssetForm({ ...assetForm, site_id: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="">Select site</option>{sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label>Asset tag<input required minLength={3} value={assetForm.asset_tag} onChange={(event) => setAssetForm({ ...assetForm, asset_tag: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Kind<select value={assetForm.kind} onChange={(event) => setAssetForm({ ...assetForm, kind: event.target.value })} className="mt-1 block w-full border bg-white p-2">{["edge_appliance", "network_gateway", "storage", "ups", "bedside_interface", "other"].map((kind) => <option key={kind} value={kind}>{kind.replaceAll("_", " ")}</option>)}</select></label><label>Model<input required minLength={2} value={assetForm.model} onChange={(event) => setAssetForm({ ...assetForm, model: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Firmware (if known)<input value={assetForm.firmware} onChange={(event) => setAssetForm({ ...assetForm, firmware: event.target.value })} className="mt-1 block w-full border p-2" /></label><button className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Register asset</button></form></section>
    <section className="grid gap-8 border-t border-[#D6DCD8] pt-7 lg:grid-cols-2"><div><h2 className="text-xl font-semibold">Regulatory coordination</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8] text-sm">{compliance.map((task) => <div key={task.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><span>{task.task_type.replaceAll("_", " ")}<small className="block text-slate">{task.organization_id} / {task.site_id} · {task.owner}{task.evidence_ref ? ` · ${task.evidence_ref}` : ""}</small></span><select aria-label={`Status for compliance task ${task.id}`} value={task.status} onChange={(event) => void updateCompliance(task, event.target.value)} className="border bg-white p-1">{complianceStates.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></div>)}{!compliance.length && <p className="py-3 text-slate">No coordination tasks.</p>}</div></div><form onSubmit={(event) => { event.preventDefault(); void submit("/v1/vendor/compliance-tasks", taskForm); }} className="grid content-start gap-3 text-sm"><h3 className="font-semibold">Create coordination task</h3><label>Site<select required value={taskForm.site_id} onChange={(event) => setTaskForm({ ...taskForm, site_id: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="">Select site</option>{sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label>Task type<input required minLength={3} value={taskForm.task_type} onChange={(event) => setTaskForm({ ...taskForm, task_type: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Responsible partner or owner<input required minLength={2} value={taskForm.owner} onChange={(event) => setTaskForm({ ...taskForm, owner: event.target.value })} className="mt-1 block w-full border p-2" /></label><button className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Create task</button></form></section>
    {account?.role === "root_admin" && <section className="border-t border-[#D6DCD8] pt-7"><h2 className="text-xl font-semibold">Account access</h2><p className="mt-2 text-sm text-slate">Disabling an account or changing organization membership immediately revokes its sessions.</p><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{accounts.map((person) => <div key={person.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"><div><strong>{person.display_name}</strong><span className="ml-2 text-slate">{person.role.replaceAll("_", " ")}</span><p className="text-xs text-slate">{person.email} · {Object.entries(person.organization_roles).map(([org, role]) => `${org}: ${role.replaceAll("_", " ")}`).join(", ") || "Vendor"} · {person.disabled ? "Disabled" : "Active"}</p></div>{person.role !== "root_admin" && <button type="button" onClick={() => void setAccountState(person)} className="border border-[#B9C6BF] px-3 py-1.5 text-sm">{person.disabled ? "Reactivate" : "Disable access"}</button>}</div>)}</div><form onSubmit={(event) => void saveMembership(event)} className="mt-6 grid gap-3 text-sm sm:grid-cols-2"><h3 className="sm:col-span-2 font-semibold">Assign or change customer membership</h3><label>Customer account<select required value={membership.account_id} onChange={(event) => setMembership({ ...membership, account_id: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="">Select account</option>{accounts.filter((person) => !person.vendor).map((person) => <option key={person.id} value={person.id}>{person.display_name} · {person.email}</option>)}</select></label><label>Organization<select required value={membership.organization_id} onChange={(event) => setMembership({ ...membership, organization_id: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="">Select organization</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label>Role<select value={membership.role} onChange={(event) => setMembership({ ...membership, role: event.target.value })} className="mt-1 block w-full border bg-white p-2">{["customer_owner", "procurement_finance", "technical_contact", "customer_viewer"].map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label><label>Audited reason<input required minLength={3} value={membership.reason} onChange={(event) => setMembership({ ...membership, reason: event.target.value })} className="mt-1 block w-full border bg-white p-2" /></label><div className="flex gap-3 sm:col-span-2"><button className="bg-forest px-4 py-2 font-semibold text-white">Save membership</button><button type="button" onClick={() => void revokeMembership()} disabled={!accounts.find((person) => person.id === membership.account_id)?.organization_roles[membership.organization_id]} className="border border-[#B9C6BF] px-4 py-2 disabled:opacity-40">Revoke membership</button></div></form></section>}
  </div>;
}
