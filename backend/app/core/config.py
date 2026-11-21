from pathlib import Path
from typing import Literal

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_JWT_SECRET = "change-me-before-non-demo-use-32-bytes"
DEFAULT_EXPORT_SALT = "change-me-before-exporting-pilot-data"


class IntegrationKey(BaseModel):
    """A hashed, scoped connector credential. Only the SHA-256 of the secret is configured."""

    key_id: str
    sha256: str
    scopes: list[str] = ["ingest:json", "ingest:fhir", "ingest:hl7v2"]
    units: list[str] | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_name: str = "PredictRx Sentinel"
    disclaimer: str = (
        "Research prototype—not approved for clinical use. "
        "The risk score supports, but does not replace, clinical judgment."
    )
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    model_path: str = str(REPO_ROOT / "ml/artifacts/models/latest/model.joblib")
    model_registry_path: str = str(REPO_ROOT / "ml/artifacts/models/ACTIVE.json")
    use_model_registry: bool = True
    metrics_dir: str = str(REPO_ROOT / "ml/artifacts/models/latest")
    demo_cases_dir: str = str(REPO_ROOT / "demo/cases")
    evidence_graph_path: str = str(REPO_ROOT / "knowledge/evidence_graph.v1.json")
    guidelines_path: str = str(REPO_ROOT / "knowledge/guidelines.v1.json")
    fhir_mapping_path: str = str(REPO_ROOT / "knowledge/fhir_mapping.v1.json")
    passport_evidence_path: str = str(REPO_ROOT / "ml/configs/site_passport_public_setb.yaml")
    demo_unit_id: str = "icu-demo-1"
    api_unit_id: str = "icu-api"
    demo_mode: bool = True
    # Public congress demos intentionally share one replay database.  Locking
    # the operating mode prevents a visitor who chooses the demo-admin role
    # from blinding the shared board or attempting a live-mode transition.
    # Hospital installations leave this false and retain audited mode changes.
    public_demo_lockdown: bool = False
    public_simulation_enabled: bool = False
    public_simulation_interval_seconds: int = 30
    # Demo ICU board: advance PhysioNet replay one hour on this cadence (0 = off).
    # Runs inside the API process so the shared public board still moves even when
    # PUBLIC_DEMO_LOCKDOWN blocks visitor-triggered /demo/replay/step calls.
    demo_replay_auto_interval_seconds: int = 0
    evaluation_runtime: bool = False
    evaluation_admin_password: SecretStr | None = None
    database_url: str = f"sqlite:///{(REPO_ROOT / 'backend' / 'predictrx.db').as_posix()}"

    # Site operation. ``site_mode`` is the *requested* mode at first start; afterwards the
    # persisted, audited site configuration is authoritative.
    site_id: str = "predictrx-local-site"
    site_mode: str = "demo"
    licence_required: bool = False
    licence_public_keys_json: str = "{}"
    alert_review_sla_minutes: int = 15
    feed_stale_minutes: int = 120
    circuit_failure_threshold: int = 3
    circuit_cooldown_seconds: int = 60
    writer_lease_seconds: int = 300
    # A hospital deployment may have multiple API instances sharing one durable
    # database, so only one instance may mutate state. The public replay demo
    # runs one disposable container and deliberately disables this lease: an
    # abandoned SQLite lease must never make the shared judge board read-only.
    writer_lease_enabled: bool = True
    # The public deployment serves this API behind Next.js at /api. Keep the
    # OpenAPI document itself at /openapi.json, while allowing its Swagger UI
    # to request the correctly prefixed URL.
    docs_openapi_url: str = "/openapi.json"

    # Readiness gates for leaving silent mode.
    pilot_min_days: int = 28
    pilot_min_encounters: int = 100
    pilot_min_adjudicated: int = 30
    pilot_min_sensitivity: float = 0.5
    pilot_max_alerts_per_100h: float = 2.0
    label_onset_window_before_hours: int = 12
    label_onset_window_after_hours: int = 3

    # Authentication. ``local`` uses HS256 tokens issued by this API; ``oidc`` validates
    # hospital identity-provider tokens against the configured JWKS.
    auth_mode: str = "local"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_previous_secrets: list[str] = []
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "predictrx-sentinel"
    jwt_audience: str = "predictrx-api"
    access_token_minutes: int = 30
    account_encryption_key: str | None = None
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: list[str] = ["RS256", "ES256"]
    oidc_user_claim: str = "preferred_username"
    oidc_role_claim: str = "roles"
    oidc_units_claim: str = "icu_units"
    oidc_role_map: dict[str, str] = {
        "predictrx-clinician": "clinician",
        "predictrx-nurse": "nurse",
        "predictrx-admin": "admin",
        "predictrx-operator": "operator",
        "predictrx-integration": "integration",
    }
    integration_api_keys: list[IntegrationKey] = []

    # Data governance.
    retention_days: int = 365
    export_salt: str = DEFAULT_EXPORT_SALT
    metrics_token: str | None = None

    # Abuse protection. Budgets are per client per minute; integration payloads are
    # additionally capped at 10 MB after reading.
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 600
    rate_limit_login_per_minute: int = 20
    rate_limit_ingest_per_minute: int = 1200
    max_request_bytes: int = 12 * 1024 * 1024

    # Mapping copilot: optional LLM. ``ollama`` speaks the Ollama API on-premises;
    # ``openai`` speaks the OpenAI-compatible chat API (OpenAI, Gemini, Groq,
    # OpenRouter, vLLM, Ollama /v1…). Unset URL keeps the copilot deterministic.
    # Only field metadata is ever sent. Outside demo mode an endpoint beyond the
    # hospital network is refused unless the site explicitly approves it.
    copilot_llm_provider: Literal["ollama", "openai"] = "ollama"
    copilot_llm_url: str | None = None
    copilot_llm_model: str = "qwen3.5:4b"
    copilot_llm_api_key: SecretStr | None = None
    copilot_llm_timeout_seconds: float = 120.0
    copilot_embed_model: str | None = None
    copilot_external_llm_approved: bool = False
    copilot_llm_per_minute: int = 30

    # Fleet heartbeat: HMAC key shared with the vendor control plane. Heartbeats
    # carry an allowlisted, patient-free metadata payload only.
    fleet_signing_key: str | None = None
    release_version: str = "0.3.0"


settings = Settings()
