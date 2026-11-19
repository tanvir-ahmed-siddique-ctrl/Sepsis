"use client";

import { useEffect, useMemo, useState } from "react";
import { accountApi, AccountRequestError } from "@/lib/account-api";
import { PageHeader } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";

type Organization = { id: string; name: string };
type Site = { id: string; organization_id: string; name: string };
type Consultation = {
  id: string; organization_name: string; contact_name: string; email: string; purpose: string;
  preferred_dates: string; modality: string; status: string; assigned_to: string | null;
  organization_id: string | null; next_action: string | null; follow_up_date: string | null;
};
type Opportunity = {
  id: string; name: string; stage: string; owner: string; organization_id: string | null;
  site_id: string | null; organization_size: string; readiness_tier: string; next_action: string; due_on: string | null;
};
type FdeProject = {
  id: string; title: string; category: string; status: string; organization_id: string; site_id: string;
  deployment_lead: string; next_action: string | null; blockers: string | null;
};
type ReadinessItem = { id: string; item_key: string; label: string; state: string; evidence_ref: string | null };
type Equipment = { id: string; site_id: string; category: string; model: string; quantity: number; ownership_model: string; procurement_status: string };
type EducationEvent = { id: string; title: string; event_type: string; event_on: string; status: string; audience: string };
type Proposal = { id: string; title: string; status: string; organization_id: string; site_id: string; version: number; valid_until: string };
type PartnershipPlan = { id: string; organization_id: string; horizon_years: number; status: string; year_1_focus: string };
type OrgProfile = { organization: Organization; profile: Record<string, string | null> | null; sites: Site[] };

const input = "auralis-input mt-1.5";

export function VendorPartnership() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [projects, setProjects] = useState<FdeProject[]>([]);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [events, setEvents] = useState<EducationEvent[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [plans, setPlans] = useState<PartnershipPlan[]>([]);
  const [stages, setStages] = useState<string[]>([]);
  const [selectedOrg, setSelectedOrg] = useState("");
  const [orgProfile, setOrgProfile] = useState<OrgProfile | null>(null);
  const [readiness, setReadiness] = useState<ReadinessItem[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [oppForm, setOppForm] = useState({ name: "", organization_id: "", site_id: "", primary_contact: "", owner: "", organization_size: "unspecified", readiness_tier: "unspecified", next_action: "Qualify inquiry" });
  const [fdeForm, setFdeForm] = useState({ organization_id: "", site_id: "", title: "", category: "site_readiness", deployment_lead: "", scope: "" });
  const [equipForm, setEquipForm] = useState({ organization_id: "", site_id: "", category: "monitor", model: "", quantity: 1, ownership_model: "hospital_owned", procurement_status: "identified" });
  const [eventForm, setEventForm] = useState({ title: "", event_type: "hospital_hosted_training", objectives: "", event_on: "", format: "in_person", audience: "clinical staff", included_complimentary: true });
  const [proposalForm, setProposalForm] = useState({ organization_id: "", site_id: "", title: "", executive_summary: "", assumptions: "Scope subject to site assessment", exclusions: "Regulatory approval not included", timeline_notes: "Planning assumptions only", valid_until: "" });
  const [planForm, setPlanForm] = useState({ organization_id: "", year_1_focus: "", years_2_3_focus: "", years_4_5_focus: "", years_6_8_focus: "" });
  const [profileForm, setProfileForm] = useState({ display_name: "", organization_size: "unspecified", readiness_tier: "unspecified", relationship_status: "prospect", country: "", reason: "Profile update" });

  async function scoped<T>(path: string, empty: T): Promise<T> {
    try { return await accountApi<T>(path); }
    catch (cause) { if (cause instanceof AccountRequestError && cause.status === 403) return empty; throw cause; }
  }

  async function load() {
    try {
      const [o, s, c, opp, p, e, ev, pr, pl, tax] = await Promise.all([
        accountApi<{ organizations: Organization[] }>("/v1/organizations"),
        accountApi<{ sites: Site[] }>("/v1/sites"),
        scoped<{ consultations: Consultation[] }>("/v1/vendor/consultations", { consultations: [] }),
        scoped<{ opportunities: Opportunity[]; stages?: string[] }>("/v1/vendor/opportunities", { opportunities: [] }),
        scoped<{ projects: FdeProject[] }>("/v1/fde-projects", { projects: [] }),
        scoped<{ equipment: Equipment[] }>("/v1/equipment", { equipment: [] }),
        scoped<{ events: EducationEvent[] }>("/v1/education-events", { events: [] }),
        scoped<{ proposals: Proposal[] }>("/v1/proposals", { proposals: [] }),
        scoped<{ plans: PartnershipPlan[] }>("/v1/vendor/partnership-plans", { plans: [] }),
        scoped<{ opportunity_stages: string[] }>("/v1/partnership/taxonomy", { opportunity_stages: [] }),
      ]);
      setOrgs(o.organizations); setSites(s.sites); setConsultations(c.consultations); setOpportunities(opp.opportunities);
      setProjects(p.projects); setEquipment(e.equipment); setEvents(ev.events); setProposals(pr.proposals); setPlans(pl.plans);
      setStages(opp.stages || tax.opportunity_stages || []);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Partnership workspace unavailable");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // Initial load only — subsequent mutations call load() explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedOrg) { setOrgProfile(null); return; }
    void accountApi<OrgProfile>(`/v1/organizations/${selectedOrg}/profile`).then(setOrgProfile).catch((cause) => setError(cause instanceof Error ? cause.message : "Profile unavailable"));
  }, [selectedOrg]);

  useEffect(() => {
    if (!selectedProject) { setReadiness([]); return; }
    void accountApi<{ items: ReadinessItem[] }>(`/v1/fde-projects/${selectedProject}/readiness`).then((r) => setReadiness(r.items)).catch(() => setReadiness([]));
  }, [selectedProject]);

  const filteredOpps = useMemo(
    () => opportunities.filter((item) => stageFilter === "all" || item.stage === stageFilter),
    [opportunities, stageFilter],
  );

  async function submit(path: string, body: object, success: string, method: "POST" | "PATCH" | "PUT" = "POST") {
    setNotice(null);
    try {
      await accountApi(path, { method, body: JSON.stringify(body) });
      setNotice(success);
      await load();
      if (selectedOrg) setOrgProfile(await accountApi(`/v1/organizations/${selectedOrg}/profile`));
      if (selectedProject) {
        const r = await accountApi<{ items: ReadinessItem[] }>(`/v1/fde-projects/${selectedProject}/readiness`);
        setReadiness(r.items);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Operation failed");
    }
  }

  if (loading) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading partnership workspace">
        <div className="auralis-skeleton h-8 w-64" />
        <div className="auralis-skeleton h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Vendor control plane"
        title="Hospital partnership & FDE"
        description="Consultation requests, opportunity pipeline, organisation profiles, readiness checklists, equipment coordination, education events and internal partnership plans. Empty state is expected until records exist. Pricing hypotheses remain internal and unpublished."
      />
      {error && <p role="alert" className="flex items-center gap-2 rounded-lg border border-risk-watch/25 bg-risk-watch/[0.05] px-3.5 py-2.5 text-sm text-risk-watch"><Icon name="alert" size={16} />{error}</p>}
      {notice && <p role="status" className="flex items-center gap-2 rounded-lg border border-risk-stable/25 bg-risk-stable/[0.05] px-3.5 py-2.5 text-sm text-risk-stable"><Icon name="check" size={16} />{notice}</p>}

      <section className="auralis-panel space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-base font-semibold text-ink">Consultation requests</h2>
          <span className="text-xs text-muted">{consultations.length} pending/managed · not auto-booked</span>
        </div>
        {consultations.length === 0 ? (
          <p className="mt-4 text-sm text-muted">No consultation requests yet.</p>
        ) : (
          <div className="mt-4 divide-y divide-border border-y border-border">
            {consultations.map((item) => (
              <article key={item.id} className="grid gap-3 py-4 lg:grid-cols-[1.2fr_1fr_auto]">
                <div>
                  <h3 className="text-sm font-semibold text-ink">{item.organization_name}</h3>
                  <p className="mt-1 text-sm text-muted">{item.contact_name} · {item.email}</p>
                  <p className="mt-1 text-xs text-muted">{item.purpose} · {item.modality} · {item.preferred_dates}</p>
                </div>
                <div className="text-sm">
                  <p>Status: <strong>{item.status}</strong></p>
                  <p className="text-muted">Owner: {item.assigned_to || "unassigned"}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {["assigned", "confirmed", "declined", "rescheduled", "completed"].map((status) => (
                    <button key={status} type="button" className="auralis-btn-secondary auralis-btn-sm" onClick={() => void submit(`/v1/vendor/consultations/${item.id}`, { status, assigned_to: "vendor-owner", confirmed_at: status === "confirmed" ? new Date().toISOString() : null, reason: `Marked ${status}` }, `Consultation ${status}`, "PATCH")}>{status}</button>
                  ))}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="auralis-panel space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-base font-semibold text-ink">Opportunity pipeline</h2>
          <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)} className="auralis-input h-9 w-auto py-0 text-[13px]">
            <option value="all">All stages</option>
            {stages.map((stage) => <option key={stage} value={stage}>{stage}</option>)}
          </select>
        </div>
        <form className="mt-4 grid gap-3 rounded-xl border border-border bg-muted-surface/60 p-4 sm:grid-cols-2 lg:grid-cols-4" onSubmit={(e) => { e.preventDefault(); void submit("/v1/vendor/opportunities", { ...oppForm, organization_id: oppForm.organization_id || null, site_id: oppForm.site_id || null }, "Opportunity created"); }}>
          <input required placeholder="Opportunity name" value={oppForm.name} onChange={(e) => setOppForm({ ...oppForm, name: e.target.value })} className={input} />
          <input required placeholder="Primary contact" value={oppForm.primary_contact} onChange={(e) => setOppForm({ ...oppForm, primary_contact: e.target.value })} className={input} />
          <input required placeholder="Owner" value={oppForm.owner} onChange={(e) => setOppForm({ ...oppForm, owner: e.target.value })} className={input} />
          <input required placeholder="Next action" value={oppForm.next_action} onChange={(e) => setOppForm({ ...oppForm, next_action: e.target.value })} className={input} />
          <select value={oppForm.organization_id} onChange={(e) => setOppForm({ ...oppForm, organization_id: e.target.value })} className={input}>
            <option value="">Organisation (optional)</option>
            {orgs.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
          </select>
          <select value={oppForm.site_id} onChange={(e) => setOppForm({ ...oppForm, site_id: e.target.value })} className={input}>
            <option value="">Site (optional)</option>
            {sites.filter((s) => !oppForm.organization_id || s.organization_id === oppForm.organization_id).map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
          </select>
          <select value={oppForm.organization_size} onChange={(e) => setOppForm({ ...oppForm, organization_size: e.target.value })} className={input}>
            {["unspecified", "clinic", "small", "medium", "large", "tertiary", "academic", "specialist", "group"].map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <select value={oppForm.readiness_tier} onChange={(e) => setOppForm({ ...oppForm, readiness_tier: e.target.value })} className={input}>
            {["unspecified", "foundation", "connected", "advanced"].map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <button className="auralis-btn-primary sm:col-span-2 lg:col-span-4">Create opportunity</button>
        </form>
        {filteredOpps.length === 0 ? <p className="mt-4 text-sm text-muted">No opportunities in this view.</p> : (
          <div className="mt-4 divide-y divide-border border-y border-border">
            {filteredOpps.map((item) => (
              <article key={item.id} className="grid gap-3 py-4 lg:grid-cols-[1.4fr_1fr_auto]">
                <div>
                  <h3 className="text-sm font-semibold text-ink">{item.name}</h3>
                  <p className="mt-1 text-sm text-muted">{item.stage} · {item.organization_size}/{item.readiness_tier}</p>
                  <p className="text-xs text-muted">Next: {item.next_action}</p>
                </div>
                <p className="text-sm text-muted">Owner {item.owner}</p>
                <select className="auralis-input h-9 w-auto py-0 text-[13px]" defaultValue={item.stage} onChange={(e) => void submit(`/v1/vendor/opportunities/${item.id}`, { stage: e.target.value, next_action: item.next_action, reason: `Stage → ${e.target.value}` }, "Stage updated", "PATCH")}>
                  {stages.map((stage) => <option key={stage} value={stage}>{stage}</option>)}
                </select>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="auralis-panel space-y-4">
        <h2 className="text-base font-semibold text-ink">Hospital organisation profile</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <select value={selectedOrg} onChange={(e) => setSelectedOrg(e.target.value)} className={input}>
            <option value="">Select organisation</option>
            {orgs.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
          </select>
        </div>
        {orgProfile && (
          <div className="mt-4 grid gap-6 lg:grid-cols-2">
            <div className="space-y-2 text-sm">
              <p><strong>{orgProfile.organization.name}</strong> ({orgProfile.organization.id})</p>
              <p>Sites: {orgProfile.sites.map((s) => s.name).join(", ") || "none"}</p>
              <p>Size: {orgProfile.profile?.organization_size || "unspecified"}</p>
              <p>Readiness: {orgProfile.profile?.readiness_tier || "unspecified"}</p>
              <p>Relationship: {orgProfile.profile?.relationship_status || "prospect"}</p>
            </div>
            <form className="grid gap-2" onSubmit={(e) => { e.preventDefault(); void submit(`/v1/vendor/organizations/${selectedOrg}/profile`, profileForm, "Organisation profile saved", "PUT"); }}>
              <input placeholder="Display name" value={profileForm.display_name} onChange={(e) => setProfileForm({ ...profileForm, display_name: e.target.value })} className={input} />
              <select value={profileForm.organization_size} onChange={(e) => setProfileForm({ ...profileForm, organization_size: e.target.value })} className={input}>
                {["unspecified", "clinic", "small", "medium", "large", "tertiary", "academic", "specialist", "group"].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
              <select value={profileForm.readiness_tier} onChange={(e) => setProfileForm({ ...profileForm, readiness_tier: e.target.value })} className={input}>
                {["unspecified", "foundation", "connected", "advanced"].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
              <select value={profileForm.relationship_status} onChange={(e) => setProfileForm({ ...profileForm, relationship_status: e.target.value })} className={input}>
                {["prospect", "discovery", "assessment", "technical_feasibility", "proposal", "contracted", "implementing", "evaluating", "governed_production", "managed_services", "suspended", "closed"].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
              <input placeholder="Country" value={profileForm.country} onChange={(e) => setProfileForm({ ...profileForm, country: e.target.value })} className={input} />
              <button className="auralis-btn-primary">Save profile</button>
            </form>
          </div>
        )}
      </section>

      <section className="auralis-panel space-y-4">
        <h2 className="text-base font-semibold text-ink">FDE delivery projects</h2>
        <form className="mt-4 grid gap-3 rounded-xl border border-border bg-muted-surface/60 p-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={(e) => { e.preventDefault(); void submit("/v1/vendor/fde-projects", fdeForm, "FDE project created"); }}>
          <select required value={fdeForm.organization_id} onChange={(e) => setFdeForm({ ...fdeForm, organization_id: e.target.value })} className={input}>
            <option value="">Organisation</option>
            {orgs.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
          </select>
          <select required value={fdeForm.site_id} onChange={(e) => setFdeForm({ ...fdeForm, site_id: e.target.value })} className={input}>
            <option value="">Site</option>
            {sites.filter((s) => s.organization_id === fdeForm.organization_id).map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
          </select>
          <input required placeholder="Title" value={fdeForm.title} onChange={(e) => setFdeForm({ ...fdeForm, title: e.target.value })} className={input} />
          <select value={fdeForm.category} onChange={(e) => setFdeForm({ ...fdeForm, category: e.target.value })} className={input}>
            {["site_readiness", "infrastructure_improvement", "equipment_connectivity", "hospital_it_implementation", "clinical_platform_integration", "clinical_intelligence_evaluation", "managed_technology_services"].map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <input required placeholder="Deployment lead" value={fdeForm.deployment_lead} onChange={(e) => setFdeForm({ ...fdeForm, deployment_lead: e.target.value })} className={input} />
          <input required placeholder="Scope" value={fdeForm.scope} onChange={(e) => setFdeForm({ ...fdeForm, scope: e.target.value })} className={input} />
          <button className="auralis-btn-primary lg:col-span-3">Create FDE project</button>
        </form>
        <div className="mt-4 space-y-3">
          {projects.length === 0 ? <p className="text-sm text-muted">No FDE projects yet.</p> : projects.map((project) => (
            <article key={project.id} className="rounded-xl border border-border bg-white p-4 shadow-soft">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-ink">{project.title}</h3>
                  <p className="text-sm text-muted">{project.category} · {project.status} · lead {project.deployment_lead}</p>
                </div>
                <button type="button" className="auralis-btn-secondary auralis-btn-sm" onClick={() => setSelectedProject(project.id)}>Open readiness checklist</button>
              </div>
            </article>
          ))}
        </div>
        {selectedProject && (
          <div className="mt-4 border border-border p-4">
            <h3 className="text-sm font-semibold text-ink">Site readiness passport</h3>
            <p className="mt-1 text-xs text-muted">Explicit checklist states only — no invented maturity score.</p>
            <div className="mt-3 divide-y divide-border">
              {readiness.map((item) => (
                <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-2 text-sm">
                  <span>{item.label}</span>
                  <select className="auralis-input h-9 w-auto py-0 text-[13px]" value={item.state} onChange={(e) => void submit(`/v1/vendor/fde-projects/${selectedProject}/readiness/${item.id}`, { state: e.target.value, reason: `Checklist → ${e.target.value}` }, "Checklist updated", "PATCH")}>
                    {["not_started", "in_progress", "requires_evidence", "blocked", "submitted", "approved", "rejected"].map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="auralis-panel space-y-4">
        <h2 className="text-base font-semibold text-ink">Equipment & proposals</h2>
        <div className="mt-4 grid gap-6 lg:grid-cols-2">
          <form className="grid gap-2 border border-border p-4" onSubmit={(e) => { e.preventDefault(); void submit("/v1/vendor/equipment", equipForm, "Equipment record created"); }}>
            <h3 className="text-sm font-semibold text-ink">Equipment inventory record</h3>
            <select required value={equipForm.organization_id} onChange={(e) => setEquipForm({ ...equipForm, organization_id: e.target.value })} className={input}>
              <option value="">Organisation</option>
              {orgs.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
            </select>
            <select required value={equipForm.site_id} onChange={(e) => setEquipForm({ ...equipForm, site_id: e.target.value })} className={input}>
              <option value="">Site</option>
              {sites.filter((s) => s.organization_id === equipForm.organization_id).map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
            </select>
            <input required placeholder="Model" value={equipForm.model} onChange={(e) => setEquipForm({ ...equipForm, model: e.target.value })} className={input} />
            <select value={equipForm.ownership_model} onChange={(e) => setEquipForm({ ...equipForm, ownership_model: e.target.value })} className={input}>
              {["hospital_owned", "supplier_provided", "partner_managed", "unspecified"].map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
            <button className="auralis-btn-primary">Add equipment record</button>
            <p className="text-xs text-muted">{equipment.length} recorded · not marked operational without acceptance evidence</p>
          </form>
          <form className="grid gap-2 border border-border p-4" onSubmit={(e) => { e.preventDefault(); void submit("/v1/vendor/proposals", { ...proposalForm, scope_json: JSON.stringify({ services: ["site_readiness"], note: "Editable draft proposal" }) }, "Draft proposal created"); }}>
            <h3 className="text-sm font-semibold text-ink">Hospital proposal (draft)</h3>
            <select required value={proposalForm.organization_id} onChange={(e) => setProposalForm({ ...proposalForm, organization_id: e.target.value })} className={input}>
              <option value="">Organisation</option>
              {orgs.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
            </select>
            <select required value={proposalForm.site_id} onChange={(e) => setProposalForm({ ...proposalForm, site_id: e.target.value })} className={input}>
              <option value="">Site</option>
              {sites.filter((s) => s.organization_id === proposalForm.organization_id).map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
            </select>
            <input required placeholder="Title" value={proposalForm.title} onChange={(e) => setProposalForm({ ...proposalForm, title: e.target.value })} className={input} />
            <textarea required placeholder="Executive summary" value={proposalForm.executive_summary} onChange={(e) => setProposalForm({ ...proposalForm, executive_summary: e.target.value })} className={input} />
            <input required type="date" value={proposalForm.valid_until} onChange={(e) => setProposalForm({ ...proposalForm, valid_until: e.target.value })} className={input} />
            <button className="auralis-btn-primary">Create draft proposal</button>
            <p className="text-xs text-muted">{proposals.length} proposals · drafts are not contracts</p>
          </form>
        </div>
      </section>

      <section className="auralis-panel space-y-4">
        <h2 className="text-base font-semibold text-ink">Education & internal partnership plans</h2>
        <div className="mt-4 grid gap-6 lg:grid-cols-2">
          <form className="grid gap-2 border border-border p-4" onSubmit={(e) => { e.preventDefault(); void submit("/v1/vendor/education-events", { ...eventForm, organization_id: selectedOrg || null }, "Education event planned"); }}>
            <h3 className="text-sm font-semibold text-ink">Education event</h3>
            <input required placeholder="Title" value={eventForm.title} onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })} className={input} />
            <select value={eventForm.event_type} onChange={(e) => setEventForm({ ...eventForm, event_type: e.target.value })} className={input}>
              {["internal_training", "hospital_hosted_training", "free_educational_seminar", "professional_workshop", "technical_workshop", "university_collaboration", "conference_participation"].map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
            <textarea required placeholder="Learning objectives" value={eventForm.objectives} onChange={(e) => setEventForm({ ...eventForm, objectives: e.target.value })} className={input} />
            <input required type="date" value={eventForm.event_on} onChange={(e) => setEventForm({ ...eventForm, event_on: e.target.value })} className={input} />
            <button className="auralis-btn-primary">Plan event</button>
            <p className="text-xs text-muted">{events.length} planned · no fabricated past seminars</p>
          </form>
          <form className="grid gap-2 border border-border p-4" onSubmit={(e) => { e.preventDefault(); void submit("/v1/vendor/partnership-plans", { ...planForm, horizon_years: 8 }, "Internal partnership plan saved"); }}>
            <h3 className="text-sm font-semibold text-ink">Internal 7–8 year planning horizon</h3>
            <p className="text-xs text-muted">Strategic planning only — not a binding contract duration.</p>
            <select required value={planForm.organization_id} onChange={(e) => setPlanForm({ ...planForm, organization_id: e.target.value })} className={input}>
              <option value="">Organisation</option>
              {orgs.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
            </select>
            <textarea required placeholder="Year 1 — Foundation" value={planForm.year_1_focus} onChange={(e) => setPlanForm({ ...planForm, year_1_focus: e.target.value })} className={input} />
            <textarea required placeholder="Years 2–3 — Connectivity" value={planForm.years_2_3_focus} onChange={(e) => setPlanForm({ ...planForm, years_2_3_focus: e.target.value })} className={input} />
            <textarea required placeholder="Years 4–5 — Intelligence" value={planForm.years_4_5_focus} onChange={(e) => setPlanForm({ ...planForm, years_4_5_focus: e.target.value })} className={input} />
            <textarea required placeholder="Years 6–8 — Partnership" value={planForm.years_6_8_focus} onChange={(e) => setPlanForm({ ...planForm, years_6_8_focus: e.target.value })} className={input} />
            <button className="auralis-btn-primary">Save internal plan</button>
            <p className="text-xs text-muted">{plans.length} internal plans</p>
          </form>
        </div>
      </section>
    </div>
  );
}
