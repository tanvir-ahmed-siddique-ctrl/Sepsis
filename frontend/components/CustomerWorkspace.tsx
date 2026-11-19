"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { accountApi, AccountRequestError } from "@/lib/account-api";
import { EmptyState, PageHeader, Pill } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";

type Organization = { id: string; name: string };
type Site = { id: string; organization_id: string; name: string };
type Ticket = { id: string; site_id: string; issue_code: string; severity: string; status: string; sla_due_at?: string | null; sla_breached?: boolean; sla_target_minutes?: number | null; escalation_level?: number };
type Asset = { id: string; site_id: string; asset_tag: string; kind: string; model: string; firmware: string | null; lifecycle_state?: string; warranty_expired?: boolean };
type ComplianceTask = { id: string; site_id: string; task_type: string; owner: string; status: string; evidence_ref: string | null };
type Member = { id: string; email: string; display_name: string; role: string; disabled: boolean };
const issueCodes = ["feed_unavailable", "mapping_review", "edge_unavailable", "backup_check", "account_access", "training_request", "other_operational"];
const inviteRoles = ["technical_contact", "procurement_finance", "customer_viewer"] as const;
const input = "auralis-input mt-1.5";

function severityTone(severity: string) {
  if (severity === "urgent") return "danger" as const;
  if (severity === "degraded") return "warning" as const;
  return "neutral" as const;
}

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
      setOrganizations(orgs.organizations);
      setSites(registered.sites);
      setTickets(requests.tickets);
      setAssets(equipment.assets);
      setCompliance(tasks.tasks);
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
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function openTicket(event: React.FormEvent) {
    event.preventDefault();
    try {
      await accountApi("/v1/tickets", { method: "POST", body: JSON.stringify({ site_id: siteId, issue_code: issueCode, severity }) });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not open request");
    }
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

  if (loading) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading organization account">
        <div className="auralis-skeleton h-8 w-64" />
        <div className="auralis-skeleton h-40 w-full" />
      </div>
    );
  }

  if (error === "Organization sign-in required") {
    return (
      <div className="auralis-panel">
        <h2 className="text-base font-semibold text-ink">Organization account required</h2>
        <p className="mt-2 text-sm text-muted">
          This portal is for hospital organisation accounts (contracts and support), not clinical sample roles, fleet
          operator sessions, or vendor control-plane logins.
        </p>
        <Link href="/signin" className="auralis-btn-primary mt-4">
          <Icon name="arrow-right" size={16} />
          Open sign-in
        </Link>
      </div>
    );
  }

  if (error && organizations.length === 0) {
    return (
      <p role="alert" className="flex items-center gap-2 rounded-lg border border-risk-high/25 bg-risk-high/[0.05] px-3.5 py-2.5 text-sm text-risk-high">
        <Icon name="alert" size={16} />
        {error}
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Customer portal"
        title="Organization home"
        description="Only records assigned to your organization appear here. Vendor control-plane and clinical chart actions stay unavailable unless separately authorized."
      />

      {error && (
        <p role="alert" className="flex items-center gap-2 rounded-lg border border-risk-watch/25 bg-risk-watch/[0.05] px-3.5 py-2.5 text-sm text-risk-watch">
          <Icon name="alert" size={16} />
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-x-6 gap-y-2">
        <Link href="/portal/commercial" className="auralis-link">
          Contracts, licences, invoices and payments
          <Icon name="arrow-right" size={16} />
        </Link>
        <Link href="/portal/service" className="auralis-link">
          Deployment, training and offboarding
          <Icon name="arrow-right" size={16} />
        </Link>
        <Link href="/portal/documents" className="auralis-link">
          Private documents
          <Icon name="arrow-right" size={16} />
        </Link>
      </div>

      <section className="auralis-panel">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Organizations</h2>
          <span className="text-xs text-muted">{organizations.length} assigned</span>
        </div>
        {!organizations.length ? (
          <EmptyState icon="building" title="No assigned organization" body="Your account is not linked to an organization yet." />
        ) : (
          <ul className="divide-y divide-border">
            {organizations.map((org) => (
              <li key={org.id} className="flex justify-between gap-3 py-3 text-sm">
                <span className="font-medium text-ink">{org.name}</span>
                <span className="font-mono text-xs text-muted">{org.id}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="auralis-panel">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Registered sites</h2>
          <span className="text-xs text-muted">{sites.length} sites</span>
        </div>
        {!sites.length ? (
          <EmptyState icon="layers" title="No sites registered" body="No site is registered for this account." />
        ) : (
          <ul className="divide-y divide-border">
            {sites.map((site) => (
              <li key={site.id} className="flex justify-between gap-3 py-3 text-sm">
                <span className="font-medium text-ink">{site.name}</span>
                <span className="font-mono text-xs text-muted">{site.id}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="auralis-panel">
          <h2 className="text-base font-semibold text-ink">Organization members</h2>
          <p className="mt-1 text-sm text-muted">Owners can invite technical, finance, or viewer contacts. The invitation token is shown once; deliver it through an institution-approved secure channel.</p>
          <div className="mt-4 divide-y divide-border border-y border-border text-sm">
            {members.map((member) => (
              <p key={member.id} className="flex justify-between gap-3 py-3">
                <span>
                  {member.display_name}
                  <small className="block text-muted">
                    {member.email} · {member.disabled ? "disabled" : "active"}
                  </small>
                </span>
                <Pill>{member.role.replaceAll("_", " ")}</Pill>
              </p>
            ))}
            {!members.length && <p className="py-3 text-muted">No members visible for your organization role.</p>}
          </div>
        </div>
        <form onSubmit={(event) => void inviteMember(event)} className="auralis-panel grid content-start gap-3 text-sm">
          <h3 className="text-base font-semibold text-ink">Invite a member</h3>
          <label className="auralis-label">
            Organization
            <select required value={inviteOrgId} onChange={(event) => setInviteOrgId(event.target.value)} className={input}>
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>{org.name}</option>
              ))}
            </select>
          </label>
          <label className="auralis-label">
            Name
            <input required value={inviteName} onChange={(event) => setInviteName(event.target.value)} className={input} />
          </label>
          <label className="auralis-label">
            Work email
            <input required type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} className={input} />
          </label>
          <label className="auralis-label">
            Role
            <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value as (typeof inviteRoles)[number])} className={input}>
              {inviteRoles.map((role) => (
                <option key={role} value={role}>{role.replaceAll("_", " ")}</option>
              ))}
            </select>
          </label>
          <button type="submit" className="auralis-btn-primary justify-self-start">
            Create invitation
          </button>
          {inviteToken && (
            <p role="status" className="rounded-lg border border-risk-stable/25 bg-risk-stable/[0.05] px-3 py-2 text-xs text-ink">
              One-time token (copy now): <code className="break-all font-mono">{inviteToken}</code>
            </p>
          )}
        </form>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <div className="auralis-panel">
          <h2 className="text-base font-semibold text-ink">Operational support</h2>
          <p className="mt-1 text-sm text-muted">Use coded requests for feed, edge, backup, access or training issues. No patient information is accepted here. Clinical decisions stay with the hospital.</p>
          {sites.length > 0 && (
            <form onSubmit={(event) => void openTicket(event)} className="mt-5 grid gap-3 text-sm">
              <label className="auralis-label">
                Site
                <select value={siteId} onChange={(event) => setSiteId(event.target.value)} className={input}>
                  {sites.map((site) => (
                    <option key={site.id} value={site.id}>{site.name}</option>
                  ))}
                </select>
              </label>
              <label className="auralis-label">
                Issue
                <select value={issueCode} onChange={(event) => setIssueCode(event.target.value)} className={input}>
                  {issueCodes.map((code) => (
                    <option key={code} value={code}>{code.replaceAll("_", " ")}</option>
                  ))}
                </select>
              </label>
              <label className="auralis-label">
                Severity
                <select value={severity} onChange={(event) => setSeverity(event.target.value)} className={input}>
                  <option value="routine">Routine</option>
                  <option value="degraded">Degraded</option>
                  <option value="urgent">Urgent</option>
                </select>
              </label>
              <button type="submit" className="auralis-btn-primary justify-self-start">
                Open support request
              </button>
            </form>
          )}
        </div>
        <div className="auralis-panel">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink">Requests</h2>
            <span className="text-xs text-muted">{tickets.length} open or closed</span>
          </div>
          {!tickets.length ? (
            <EmptyState icon="lifebuoy" title="No support requests yet" body="Open a coded operational request when a site needs attention." />
          ) : (
            <div className="overflow-x-auto">
              <table className="auralis-table">
                <thead>
                  <tr>
                    <th>Site</th>
                    <th>Issue</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>SLA</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                    <tr key={ticket.id}>
                      <td className="font-mono text-xs">{ticket.site_id}</td>
                      <td className="capitalize">{ticket.issue_code.replaceAll("_", " ")}</td>
                      <td><Pill tone={severityTone(ticket.severity)}>{ticket.severity}</Pill></td>
                      <td className="capitalize text-muted">{ticket.status.replaceAll("_", " ")}</td>
                      <td className="text-muted">
                        {ticket.sla_breached ? "breached" : ticket.sla_target_minutes ? `${ticket.sla_target_minutes} min` : "—"}
                        {ticket.escalation_level ? ` · esc ${ticket.escalation_level}` : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="auralis-panel">
          <h2 className="text-base font-semibold text-ink">Registered deployment assets</h2>
          <div className="mt-4 divide-y divide-border border-y border-border text-sm">
            {assets.map((asset) => (
              <p key={asset.id} className="flex justify-between gap-4 py-3">
                <span>
                  {asset.kind.replaceAll("_", " ")} · {asset.model}
                  <small className="block text-muted">
                    {asset.site_id}
                    {asset.firmware ? ` · firmware ${asset.firmware}` : ""}
                    {asset.lifecycle_state ? ` · ${asset.lifecycle_state.replaceAll("_", " ")}` : ""}
                    {asset.warranty_expired ? " · warranty expired" : ""}
                  </small>
                </span>
                <span className="font-mono text-xs text-muted">{asset.asset_tag}</span>
              </p>
            ))}
            {!assets.length && <p className="py-3 text-muted">No deployment assets registered.</p>}
          </div>
        </div>
        <div className="auralis-panel">
          <h2 className="text-base font-semibold text-ink">Compliance coordination</h2>
          <div className="mt-4 divide-y divide-border border-y border-border text-sm">
            {compliance.map((task) => (
              <p key={task.id} className="flex justify-between gap-4 py-3">
                <span>
                  {task.task_type.replaceAll("_", " ")}
                  <small className="block text-muted">
                    {task.site_id} · owner {task.owner}
                  </small>
                </span>
                <span className="text-right">
                  <Pill>{task.status.replaceAll("_", " ")}</Pill>
                  {task.evidence_ref && <small className="mt-1 block font-mono text-muted">{task.evidence_ref}</small>}
                </span>
              </p>
            ))}
            {!compliance.length && <p className="py-3 text-muted">No coordination tasks registered.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
