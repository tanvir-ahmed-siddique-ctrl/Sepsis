"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { accountApi, AccountRequestError } from "@/lib/account-api";

type Organization = { id: string; name: string };
type Site = { id: string; organization_id: string; name: string };
type Ticket = { id: string; site_id: string; issue_code: string; severity: string; status: string; sla_due_at?: string | null; sla_breached?: boolean; sla_target_minutes?: number | null; escalation_level?: number };
type Asset = { id: string; site_id: string; asset_tag: string; kind: string; model: string; firmware: string | null; lifecycle_state?: string; warranty_expired?: boolean };
type ComplianceTask = { id: string; site_id: string; task_type: string; owner: string; status: string; evidence_ref: string | null };
type Member = { id: string; email: string; display_name: string; role: string; disabled: boolean };
const issueCodes = ["feed_unavailable", "mapping_review", "edge_unavailable", "backup_check", "account_access", "training_request", "other_operational"];
const inviteRoles = ["technical_contact", "procurement_finance", "customer_viewer"] as const;

export function CustomerWorkspace() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [compliance, setCompliance] = useState<ComplianceTask[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [siteId, setSiteId] = useState("");
  const [issueCode, setIssueCode] = useState(issueCodes[0]);
  const [severity, setSeverity] = useState("routine");
  const [inviteOrgId, setInviteOrgId] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<(typeof inviteRoles)[number]>("technical_contact");
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [orgs, registered, requests, equipment, tasks] = await Promise.all([
        accountApi<{ organizations: Organization[] }>("/v1/organizations"),
        accountApi<{ sites: Site[] }>("/v1/sites"),
        accountApi<{ tickets: Ticket[] }>("/v1/tickets"),
        accountApi<{ assets: Asset[] }>("/v1/assets"),
        accountApi<{ tasks: ComplianceTask[] }>("/v1/compliance-tasks"),
      ]);
      setOrganizations(orgs.organizations); setSites(registered.sites); setTickets(requests.tickets);
      setAssets(equipment.assets); setCompliance(tasks.tasks);
      setSiteId((current) => current || registered.sites[0]?.id || "");
      setInviteOrgId((current) => current || orgs.organizations[0]?.id || "");
      const memberLists = await Promise.all(
        orgs.organizations.map((org) =>
          accountApi<{ members: Member[] }>(`/v1/portal/organizations/${encodeURIComponent(org.id)}/members`)
            .then((result) => result.members)
            .catch(() => [] as Member[]),
        ),
      );
      setMembers(memberLists.flat());
      setError(null);
    } catch (cause) {
      setError(cause instanceof AccountRequestError && cause.status === 401 ? "Organization sign-in required" : cause instanceof Error ? cause.message : "Account service unavailable");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function openTicket(event: React.FormEvent) {
    event.preventDefault();
    try {
      await accountApi("/v1/tickets", { method: "POST", body: JSON.stringify({ site_id: siteId, issue_code: issueCode, severity }) });
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not open request"); }
  }

  async function inviteMember(event: React.FormEvent) {
    event.preventDefault();
    if (!inviteOrgId) return;
    try {
      const result = await accountApi<{ token: string; expires_at: string; delivery: string }>(
        `/v1/portal/organizations/${encodeURIComponent(inviteOrgId)}/invitations`,
        {
          method: "POST",
          body: JSON.stringify({
            organization_id: inviteOrgId,
            email: inviteEmail,
            display_name: inviteName,
            role: inviteRole,
            reason: "Organization owner invitation",
          }),
        },
      );
      setInviteToken(result.token);
      setInviteEmail("");
      setInviteName("");
      setError(null);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Invitation could not be created");
    }
  }

  if (loading) return <p role="status" className="py-12 text-sm text-slate">Loading organization account…</p>;
  if (error === "Organization sign-in required") return <div className="border-l-2 border-forest bg-warm p-6"><p>Sign in with your organization account to view its sites and support requests.</p><Link href="/signin" className="mt-4 inline-block font-semibold text-forest underline">Open sign-in</Link></div>;
  if (error && organizations.length === 0) return <p role="alert" className="border-l-2 border-risk-watch bg-warm p-6">{error}</p>;

  return <div className="space-y-10">
    <header className="border-b border-border pb-7"><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal">Customer Portal</p><h1 className="mt-3 font-display text-4xl font-semibold tracking-tight">Organization home</h1><p className="mt-3 text-sm text-muted">Only records assigned to your organization appear here. Vendor control-plane and clinical chart actions stay unavailable unless separately authorized.</p></header>
    {error && <p role="alert" className="border-l-2 border-risk-watch bg-warm p-4 text-sm">{error}</p>}
    <section><h2 className="text-xl font-semibold">Organizations</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{organizations.length ? organizations.map((org) => <p key={org.id} className="flex justify-between py-4"><span>{org.name}</span><span className="font-mono text-xs text-slate">{org.id}</span></p>) : <p className="py-4 text-sm text-slate">No assigned organization.</p>}</div></section>
    <section><h2 className="text-xl font-semibold">Registered sites</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{sites.length ? sites.map((site) => <p key={site.id} className="flex justify-between py-4"><span>{site.name}</span><span className="font-mono text-xs text-slate">{site.id}</span></p>) : <p className="py-4 text-sm text-slate">No site is registered for this account.</p>}</div></section>
    <section className="grid gap-8 border-t border-[#D6DCD8] pt-7 lg:grid-cols-[1.1fr_1fr]"><div><h2 className="text-xl font-semibold">Organization members</h2><p className="mt-2 text-sm text-slate">Owners can invite technical, finance, or viewer contacts. The invitation token is shown once; deliver it through an institution-approved secure channel.</p><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8] text-sm">{members.map((member) => <p key={member.id} className="flex justify-between gap-3 py-3"><span>{member.display_name}<small className="block text-slate">{member.email} · {member.disabled ? "disabled" : "active"}</small></span><span className="text-xs uppercase tracking-wide text-slate">{member.role.replaceAll("_", " ")}</span></p>)}{!members.length && <p className="py-3 text-slate">No members visible for your organization role.</p>}</div></div><form onSubmit={(event) => void inviteMember(event)} className="grid content-start gap-3 text-sm"><h3 className="text-lg font-semibold">Invite a member</h3><label>Organization<select required value={inviteOrgId} onChange={(event) => setInviteOrgId(event.target.value)} className="mt-1 block w-full border border-[#C6CECA] bg-white p-2">{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label>Name<input required value={inviteName} onChange={(event) => setInviteName(event.target.value)} className="mt-1 block w-full border border-[#C6CECA] bg-white p-2" /></label><label>Work email<input required type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} className="mt-1 block w-full border border-[#C6CECA] bg-white p-2" /></label><label>Role<select value={inviteRole} onChange={(event) => setInviteRole(event.target.value as (typeof inviteRoles)[number])} className="mt-1 block w-full border border-[#C6CECA] bg-white p-2">{inviteRoles.map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label><button type="submit" className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Create invitation</button>{inviteToken && <p role="status" className="border-l-2 border-forest bg-warm p-3 text-xs">One-time token (copy now): <code className="break-all">{inviteToken}</code></p>}</form></section>
    <section className="grid gap-8 lg:grid-cols-[1fr_1.2fr]"><div><h2 className="text-xl font-semibold">Operational support</h2><p className="mt-3 text-sm leading-6 text-slate">Use coded requests for feed, edge, backup, access or training issues. No patient information is accepted here. Clinical decisions stay with the hospital.</p>{sites.length > 0 && <form onSubmit={(event) => void openTicket(event)} className="mt-6 grid gap-3 text-sm"><label>Site<select value={siteId} onChange={(event) => setSiteId(event.target.value)} className="mt-1 block w-full border border-[#C6CECA] bg-white p-2">{sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label>Issue<select value={issueCode} onChange={(event) => setIssueCode(event.target.value)} className="mt-1 block w-full border border-[#C6CECA] bg-white p-2">{issueCodes.map((code) => <option key={code} value={code}>{code.replaceAll("_", " ")}</option>)}</select></label><label>Severity<select value={severity} onChange={(event) => setSeverity(event.target.value)} className="mt-1 block w-full border border-[#C6CECA] bg-white p-2"><option value="routine">Routine</option><option value="degraded">Degraded</option><option value="urgent">Urgent</option></select></label><button type="submit" className="justify-self-start bg-forest px-4 py-2 font-semibold text-white">Open support request</button></form>}</div><div><h2 className="text-xl font-semibold">Requests</h2><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-[#D6DCD8] text-xs uppercase tracking-wide text-slate"><tr><th className="py-3">Site</th><th>Issue</th><th>Severity</th><th>Status</th><th>SLA</th></tr></thead><tbody className="divide-y divide-[#D6DCD8]">{tickets.map((ticket) => <tr key={ticket.id}><td className="py-3 font-mono text-xs">{ticket.site_id}</td><td>{ticket.issue_code.replaceAll("_", " ")}</td><td>{ticket.severity}</td><td>{ticket.status.replaceAll("_", " ")}</td><td>{ticket.sla_breached ? "breached" : ticket.sla_target_minutes ? `${ticket.sla_target_minutes} min` : "—"}{ticket.escalation_level ? ` · esc ${ticket.escalation_level}` : ""}</td></tr>)}</tbody></table>{tickets.length === 0 && <p className="py-4 text-sm text-slate">No support requests yet.</p>}</div></div></section>
    <section className="grid gap-8 border-t border-[#D6DCD8] pt-7 lg:grid-cols-2"><div><h2 className="text-xl font-semibold">Registered deployment assets</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8] text-sm">{assets.map((asset) => <p key={asset.id} className="flex justify-between gap-4 py-3"><span>{asset.kind.replaceAll("_", " ")} · {asset.model}<small className="block text-slate">{asset.site_id}{asset.firmware ? ` · firmware ${asset.firmware}` : ""}{asset.lifecycle_state ? ` · ${asset.lifecycle_state.replaceAll("_", " ")}` : ""}{asset.warranty_expired ? " · warranty expired" : ""}</small></span><span className="font-mono text-xs">{asset.asset_tag}</span></p>)}{!assets.length && <p className="py-3 text-slate">No deployment assets registered.</p>}</div></div><div><h2 className="text-xl font-semibold">Compliance coordination</h2><div className="mt-4 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8] text-sm">{compliance.map((task) => <p key={task.id} className="flex justify-between gap-4 py-3"><span>{task.task_type.replaceAll("_", " ")}<small className="block text-slate">{task.site_id} · owner {task.owner}</small></span><span>{task.status.replaceAll("_", " ")}{task.evidence_ref && <small className="block font-mono text-slate">{task.evidence_ref}</small>}</span></p>)}{!compliance.length && <p className="py-3 text-slate">No coordination tasks registered.</p>}</div></div></section>
    <div className="flex flex-wrap gap-5 border-t border-[#D6DCD8] pt-5 text-sm"><Link href="/portal/commercial" className="font-semibold text-forest underline underline-offset-2">Contracts, licences, invoices & payments →</Link><Link href="/portal/service" className="font-semibold text-forest underline underline-offset-2">Deployment, training & offboarding →</Link><Link href="/portal/documents" className="font-semibold text-forest underline underline-offset-2">Private documents →</Link></div>
  </div>;
}
