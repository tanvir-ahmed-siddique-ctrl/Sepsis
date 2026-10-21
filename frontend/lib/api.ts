export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const DEMO_UNIT = process.env.NEXT_PUBLIC_DEMO_UNIT_ID ?? "icu-demo-1";
export const API_UNIT = "icu-api";

export type RiskBand = "insufficient_data" | "stable" | "watch" | "high_risk";
export type TrustState = "alert" | "watch" | "verify_data" | "abstain";

export type TrustGateAssessment = {
  state: TrustState;
  reasons: string[];
  prediction_covered: boolean;
  input_shift_score: number;
  alert_stability: number | null;
  perturbation_max_delta: number | null;
  perturbations_evaluated: number;
  disagreement_validated: boolean;
};

export type Thresholds = {
  watch: number;
  high_risk: number;
};

export type ContributingFactor = {
  feature: string;
  organ_system: string;
  direction: "raises" | "lowers";
  magnitude: number;
  plain_language: string;
};

export type RiskPoint = {
  hour: number;
  index?: number;
  timestamp: string;
  probability: number | null;
  uncertainty: number | null;
  risk_band: RiskBand;
  data_quality: string;
  data_freshness_minutes: number | null;
  signal_freshness_minutes: Record<string, number | null>;
  vitals: Record<string, number | null>;
  alert_id: string | null;
  trustgate: TrustGateAssessment;
};

export type RiskCurrent = RiskPoint & {
  patient_id: string;
  encounter_key: string | null;
  unit_id: string | null;
  source_mode: "replay" | "api" | null;
  owner: string | null;
  horizon_hours: number;
  thresholds: Thresholds;
  contributing_factors: ContributingFactor[];
  model_version: string;
  disclaimer: string;
};

export type SiteMode = "demo" | "silent" | "live-disabled" | "live";

export type PatientOverview = {
  patient_id: string;
  display_name: string;
  risk_band: RiskBand;
  probability: number | null;
  uncertainty: number | null;
  hour: number;
  data_freshness_minutes: number | null;
  trust_state: TrustState;
  unresolved_alerts: number;
  trend: Array<number | null>;
  age: number | null;
  sex: string | null;
  source_mode: "replay" | "api";
  owner: string | null;
  oldest_open_alert_minutes: number | null;
  review_overdue: boolean;
  missing_required_signals: string[];
};

export type UnitOverview = {
  unit_id: string;
  patients: PatientOverview[];
  watch_count: number;
  high_risk_count: number;
  verify_count: number;
  abstain_count: number;
  open_alerts: number;
  overdue_reviews: number;
  model_version: string;
  thresholds: Thresholds;
  site_mode: SiteMode;
  interruptive_alerts_enabled: boolean;
  bedside_blinded: boolean;
  blinded_encounters: number;
  review_sla_minutes: number;
  disclaimer: string;
};

export type UserRole = "clinician" | "nurse" | "admin" | "operator";

export const ROLE_LABELS: Record<UserRole, string> = {
  clinician: "Doctor / clinician",
  nurse: "Nurse / ward staff",
  admin: "Hospital admin",
  operator: "Platform operator (no patient data)",
};

export type Me = {
  user_id: string;
  role: UserRole | "integration";
  roles: string[];
  units: string[] | null;
  auth_mode: string;
  demo_mode: boolean;
  site_mode: SiteMode;
  interruptive_alerts_enabled: boolean;
  bedside_blinded: boolean;
  display_name: string | null;
  must_change_password: boolean;
  totp_enabled: boolean;
};

export type CareUnit = {
  unit_id: string;
  label: string;
  kind: "icu" | "ward";
  news2_scale_default: 1 | 2;
};

export type News2 = {
  score: number | null;
  complete: boolean;
  missing: string[];
  scale: 1 | 2;
  components: Record<string, number | null>;
  inputs: Record<string, number | boolean | string | null>;
  urgency: "routine" | "low" | "urgent" | "emergency" | null;
  frequency_minutes: number | null;
  response: string | null;
  source_time: string;
  scored_at: string;
  due_at: string | null;
  source: string;
  disclaimer: string;
};

export type CensusEncounter = {
  encounter_key: string;
  patient_id: string;
  display_name: string;
  encounter_id: string;
  unit_id: string;
  bed_id: string | null;
  kind: "icu" | "ward";
  status: "admitted" | "discharged";
  hypercapnic_scale2: boolean;
  age: number | null;
  sex: string | null;
  admitted_at: string | null;
  missing_required: string[];
  stale_required: string[];
  complete_required: boolean;
  latest_news2: News2 | null;
  observations_due: boolean;
};

export type LocalUser = {
  user_id: string;
  display_name: string;
  role: UserRole;
  units: string[] | null;
  disabled: boolean;
  must_change_password: boolean;
  totp_enabled: boolean;
  pin_set: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
};

export type Gate = {
  gate: string;
  passed: boolean;
  value: unknown;
  target: unknown;
  detail: string;
};

export type ConnectorHealth = {
  connector: string;
  label: string;
  standard: string;
  status: string;
  endpoint: string;
  state: "never_connected" | "healthy" | "degraded" | "stale" | "circuit_open";
  circuit: "closed" | "open" | "half_open";
  consecutive_failures: number;
  last_error: string | null;
  last_received_at: string | null;
  last_success_at: string | null;
  minutes_since_success: number | null;
  recent_received: number;
  recent_quarantined: number;
  quarantine_rate: number | null;
  median_source_lag_minutes: number | null;
  median_processing_ms: number | null;
  pending_spool: number;
  stale_after_minutes: number;
};

export type Provenance = {
  code: string;
  value: number;
  unit: string;
  source: string;
  connector: string;
  source_time: string;
  received_at: string | null;
  validation_warning: string | null;
  observations_total: number;
  required: boolean;
};

export type SignalMatrix = {
  hours: number[];
  window_hours: number;
  signals: { code: string; required: boolean; observed: boolean[]; observed_hours: number }[];
};

export type Citation = {
  title: string;
  publisher: string;
  version: string;
  published?: string;
  url?: string;
  doi?: string;
  section?: string;
  recommendation?: string;
  document_ref?: string;
  review_due: string;
  approved_by?: string;
};

export type GuidancePassage = {
  passage_id: string;
  source_type: "guideline" | "local_protocol";
  section: string;
  topic: string;
  text: string;
  strength?: string;
  evidence_quality?: string;
  matched_concepts?: string[];
  citation: Citation;
};

export type GuidanceResponse = {
  registry_version: string;
  site_approved: boolean;
  withheld_reason: string | null;
  passages: GuidancePassage[];
  disclaimer: string;
};

export type GuidanceSearch = {
  query: string;
  refused: boolean;
  refusal_reason?: string;
  matched_terms?: string[];
  withheld_reason?: string | null;
  results: GuidancePassage[];
  disclaimer: string;
};

export type AlertAction = {
  user_id: string;
  action: "acknowledged" | "dismissed" | "escalated";
  reason: string | null;
  at: string;
};

export type Alert = {
  alert_id: string;
  patient_id: string;
  display_name: string;
  risk_band: RiskBand;
  probability: number;
  uncertainty: number | null;
  threshold: number;
  hour: number;
  created_at: string;
  reason: string;
  factors: ContributingFactor[];
  data_quality: string;
  trustgate: TrustGateAssessment;
  model_version: string;
  status: "open" | "silent" | "acknowledged" | "dismissed" | "escalated" | "superseded" | string;
  disposition?: string;
  unit_id?: string;
  raised_at?: string;
  actions: AlertAction[];
  review_minutes: number | null;
  review_sla_minutes: number;
  overdue: boolean;
};

export type AuditEvent = {
  audit_id: string;
  event: string;
  at: string;
  model_version: string;
  patient_id?: string;
  alert_id?: string;
  hour?: number;
  risk_band?: RiskBand;
  user_id?: string;
  reason?: string | null;
};

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

const TOKEN_KEY = "predictrx-access-token";
export const SESSION_EVENT = "predictrx-session-changed";

export function readToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function writeToken(token: string | null): void {
  if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
  else window.sessionStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export async function api<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const token = readToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  } else if (!headers.has("Authorization")) {
    headers.set("X-Demo-User", process.env.NEXT_PUBLIC_DEMO_USER ?? "demo-clinician");
    headers.set("X-Demo-Role", process.env.NEXT_PUBLIC_DEMO_ROLE ?? "clinician");
  }
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail =
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : String(body || response.statusText);
    throw new ApiRequestError(detail, response.status);
  }
  return body as T;
}

export function isStatus(error: unknown, status: number): boolean {
  return error instanceof ApiRequestError && error.status === status;
}

export function pct(value: number | null | undefined, digits = 0): string {
  return value == null || !Number.isFinite(value) ? "—" : `${(value * 100).toFixed(digits)}%`;
}
