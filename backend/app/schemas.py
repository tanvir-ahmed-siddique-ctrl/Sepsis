from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class RiskBand(str, Enum):
    insufficient_data = "insufficient_data"
    stable = "stable"
    watch = "watch"
    high_risk = "high_risk"


class AlertAction(str, Enum):
    acknowledged = "acknowledged"
    dismissed = "dismissed"
    escalated = "escalated"
    snoozed = "snoozed"


class ObservationIn(BaseModel):
    patient_id: str = Field(min_length=1, max_length=128)
    encounter_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime
    code: str = Field(min_length=1, max_length=64, description="PhysioNet variable code, e.g. HR, Lactate, SBP")
    value: float | None = Field(default=None, allow_inf_nan=False)
    unit: str | None = Field(default=None, max_length=64)
    source: str = Field(default="api", min_length=1, max_length=64)
    unit_id: str | None = Field(default=None, min_length=1, max_length=64, description="ICU unit; defaults to API unit")


class ObservationBatch(BaseModel):
    observations: list[ObservationIn]


class ContributingFactor(BaseModel):
    feature: str
    organ_system: str
    direction: str
    magnitude: float
    plain_language: str


class TrustGateAssessment(BaseModel):
    state: str
    reasons: list[str]
    prediction_covered: bool
    input_shift_score: float = Field(ge=0, le=1)
    alert_stability: float | None = Field(default=None, ge=0, le=1)
    perturbation_max_delta: float | None = Field(default=None, ge=0, le=1)
    perturbations_evaluated: int = Field(ge=0)
    disagreement_validated: bool = False


class RiskPoint(BaseModel):
    hour: int
    timestamp: datetime
    probability: float | None
    uncertainty: float | None
    risk_band: RiskBand
    data_quality: str
    data_freshness_minutes: int | None
    signal_freshness_minutes: dict[str, int | None] = Field(default_factory=dict)
    vitals: dict[str, float | None]
    alert_id: str | None = None
    trustgate: TrustGateAssessment


class RiskCurrentResponse(RiskPoint):
    patient_id: str
    encounter_id: str | None = None
    encounter_key: str | None = None
    unit_id: str | None = None
    source_mode: str | None = None
    owner: str | None = None
    horizon_hours: int = 6
    thresholds: dict[str, float]
    contributing_factors: list[ContributingFactor]
    model_version: str
    disclaimer: str


class RiskTimelineResponse(BaseModel):
    patient_id: str
    points: list[RiskPoint]
    thresholds: dict[str, float]
    disclaimer: str


class AlertAckRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    action: AlertAction
    reason: str | None = Field(default=None, max_length=500)
    timestamp: datetime | None = None
    quiet_minutes: int | None = Field(
        default=None,
        ge=5,
        le=240,
        description="For snoozed: hide interruptive banner this many minutes (bedside can keep treating).",
    )

    @model_validator(mode="after")
    def dismissal_requires_reason(self):
        if self.action == AlertAction.dismissed and not (self.reason or "").strip():
            raise ValueError("A dismissal reason is required.")
        if self.action == AlertAction.snoozed and self.quiet_minutes is None:
            self.quiet_minutes = 60
        return self


class ClinicalContextRequest(BaseModel):
    goals_of_care: str = Field(pattern="^(full_treatment|limited_escalation|comfort_care)$")
    conditions: list[str] = Field(default_factory=list, max_length=12)
    other_note: str | None = Field(default=None, max_length=160)
    reason: str = Field(min_length=3, max_length=300)
    review_hours: int = Field(default=72, ge=1, le=168)


class AlertAckResponse(BaseModel):
    alert_id: str
    action: AlertAction
    recorded_at: datetime
    audit_id: str


class PatientOverviewCard(BaseModel):
    patient_id: str
    encounter_id: str | None = None
    encounter_key: str | None = None
    display_name: str
    risk_band: RiskBand
    probability: float | None
    uncertainty: float | None
    hour: int
    scored_at: str | None = None
    data_freshness_minutes: int | None
    trust_state: str
    unresolved_alerts: int
    open_alert_id: str | None = None
    trend: list[float | None]
    age: int | None = None
    sex: str | None = None
    source_mode: str = "replay"
    owner: str | None = None
    oldest_open_alert_minutes: int | None = None
    review_overdue: bool = False
    missing_required_signals: list[str] = Field(default_factory=list)


class UnitOverviewResponse(BaseModel):
    unit_id: str
    patients: list[PatientOverviewCard]
    watch_count: int
    high_risk_count: int
    verify_count: int = 0
    abstain_count: int = 0
    open_alerts: int
    overdue_reviews: int = 0
    model_version: str
    thresholds: dict[str, float]
    site_mode: str = "demo"
    interruptive_alerts_enabled: bool = True
    bedside_blinded: bool = False
    blinded_encounters: int = 0
    review_sla_minutes: int = 15
    disclaimer: str


class SiteModeRequest(BaseModel):
    mode: str = Field(pattern="^(demo|silent|live)$")
    reason: str = Field(min_length=3, max_length=500)


class SoftLandingRequest(BaseModel):
    enabled: bool
    reason: str = Field(min_length=3, max_length=500)


class GovernanceSignoffRequest(BaseModel):
    committee: str = Field(min_length=2, max_length=200)
    reference: str = Field(min_length=2, max_length=200)
    approver: str = Field(min_length=2, max_length=128)


class FeedbackUsefulness(str, Enum):
    helpful = "helpful"
    not_helpful = "not_helpful"
    unsure = "unsure"


class FeedbackRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=300)
    alert_id: str | None = Field(default=None, max_length=64)
    usefulness: FeedbackUsefulness
    workflow: list[str] = Field(default_factory=list, max_length=6)
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def known_workflow_tags(self):
        allowed = {"already_aware", "prompted_review", "data_issue", "alarm_fatigue", "wrong_patient_context", "other"}
        unknown = set(self.workflow) - allowed
        if unknown:
            raise ValueError(f"Unknown workflow tags: {sorted(unknown)}; allowed {sorted(allowed)}")
        return self


class Adjudication(str, Enum):
    sepsis = "sepsis"
    no_sepsis = "no_sepsis"
    indeterminate = "indeterminate"


class OutcomeRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=300)
    adjudication: Adjudication
    onset_time: datetime | None = None
    criteria: str = Field(default="sepsis-3", min_length=2, max_length=64)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def sepsis_requires_onset(self):
        if self.adjudication == Adjudication.sepsis:
            if self.onset_time is None:
                raise ValueError("A sepsis adjudication requires onset_time.")
            if self.onset_time.tzinfo is None:
                raise ValueError("onset_time must include a timezone.")
        return self


class HandoffNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=1000)


class OwnershipRequest(BaseModel):
    shift_label: str | None = Field(default=None, max_length=64)


class LocalProtocolRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    section: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=10, max_length=4000)
    topic: str = Field(pattern="^(screening|assessment|escalation|monitoring|governance)$")
    concepts: list[str] = Field(default_factory=lambda: ["*"], max_length=12)
    version: str = Field(min_length=1, max_length=64)
    document_ref: str = Field(min_length=1, max_length=200)
    review_due: str = Field(min_length=4, max_length=32)


class LocalLoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    totp_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class PinLoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    pin: str = Field(pattern=r"^\d{4,6}$")
    totp_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class LocalUserRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    role: str = Field(pattern="^(clinician|nurse|admin|clinical_it|clinical_viewer|operator)$")
    password: str = Field(min_length=12, max_length=256)
    units: list[str] | None = Field(default=None, max_length=50)


class LocalUserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    role: str | None = Field(default=None, pattern="^(clinician|nurse|admin|clinical_it|clinical_viewer|operator)$")
    units: list[str] | None = Field(default=None, max_length=50)
    disabled: bool | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class AdminPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=256)


class PinChangeRequest(BaseModel):
    pin: str = Field(pattern=r"^\d{4,6}$")


class TotpConfirmRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class CareUnitRequest(BaseModel):
    unit_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    kind: str = Field(pattern="^(icu|ward)$")
    news2_scale_default: int = Field(default=1, ge=1, le=1)


class AdmitRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=128)
    encounter_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)
    unit_id: str = Field(min_length=1, max_length=64)
    bed_id: str | None = Field(default=None, max_length=64)
    age: int | None = Field(default=None, ge=18, le=120)
    sex: str | None = Field(default=None, pattern="^(F|M|X|unknown)$")
    hypercapnic_scale2: bool = False


class TransferRequest(BaseModel):
    unit_id: str = Field(min_length=1, max_length=64)
    bed_id: str | None = Field(default=None, max_length=64)


class News2ScaleRequest(BaseModel):
    hypercapnic_scale2: bool
    reason: str = Field(min_length=3, max_length=500)


class MappingSignoffRequest(BaseModel):
    registry_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_system: str = Field(min_length=2, max_length=128)
    approver_name: str = Field(min_length=2, max_length=128)
    approver_role: str = Field(min_length=2, max_length=128)
    examples_verified: int = Field(ge=10, le=10000)
    notes: str = Field(min_length=3, max_length=1000)


class MappingSuggestRequest(BaseModel):
    local_code: str = Field(min_length=1, max_length=64)
    local_display: str = Field(min_length=1, max_length=120)
    local_unit: str | None = Field(default=None, max_length=32)
    sample_min: float | None = None
    sample_max: float | None = None
    use_llm: bool = True


class ChartVitalsRequest(BaseModel):
    measured_at: datetime
    heart_rate: float | None = None
    spo2: float | None = None
    temperature: float | None = None
    temperature_unit: str = Field(default="C", pattern="^(C|F)$")
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    mean_arterial_pressure: float | None = None
    respiration_rate: float | None = None
    on_oxygen: bool | None = None
    avpu: str | None = Field(default=None, pattern="^(A|V|P|U)$")
    lactate: float | None = None
    wbc: float | None = None
    creatinine: float | None = None
    platelets: float | None = None

    @model_validator(mode="after")
    def timestamp_and_values(self):
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at must include a timezone")
        fields = (
            self.heart_rate, self.spo2, self.temperature, self.systolic_bp,
            self.diastolic_bp, self.mean_arterial_pressure, self.respiration_rate,
            self.on_oxygen, self.avpu, self.lactate, self.wbc, self.creatinine,
            self.platelets,
        )
        if all(value is None for value in fields):
            raise ValueError("At least one measurement is required")
        return self
