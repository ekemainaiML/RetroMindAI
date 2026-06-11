from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://retromind:retromind@localhost:5432/retromind"
    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "retromind"
    r2_endpoint: str = "http://localhost:9000"
    r2_access_key: str = "minioadmin"
    r2_secret_key: str = "minioadmin"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    upload_dir: str = "/app/uploads"
    ai_model_path: str = str(
        Path(__file__).resolve().parent.parent / "ai" / "models" / "vehicle_classifier.onnx"
    )

    rate_limit: str = "1000/minute"
    sentry_dsn: str = ""
    environment: str = "development"
    encryption_key: str = ""
    otel_endpoint: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    api_key_expiry_days: int = 90
    google_client_id: str = ""
    google_client_secret: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant_id: str = ""

    admin_api_key: str = "dev-admin-key"
    jwt_secret: str = "retromind-dev-jwt-secret-change-in-prod"
    worker_concurrency: int = 1
    image_max_dimension: int = 1920
    poll_cache_ttl: int = 2
    daily_intake_limit: int = 50

    # Email / SMTP
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    email_from: str = "noreply@retromind.ai"
    email_from_name: str = "RetroMind AI"
    email_enabled: bool = True

    # Customer portal
    portal_base_url: str = "http://localhost:3000/portal/view"
    portal_token_expiry_hours: int = 72
    approval_reminder_days: int = 7

    # Audit trail
    audit_retention_days: int = 90
    audit_log_request_body: bool = False
    audit_log_response_body: bool = False

    # Phase 0: Feature flags for optional capabilities
    # All default to False — no new code path active out of the box
    enable_optuna: bool = False
    enable_pytorch: bool = False
    enable_rl_recommendations: bool = False
    enable_generative_design: bool = False
    enable_cad_export: bool = False

    # Paths for optional models / services
    torch_model_path: str = str(
        Path(__file__).resolve().parent.parent / "ai" / "models" / "vehicle_classifier.pt"
    )
    rllib_checkpoint_path: str = ""
    freecad_host: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env", "case_sensitive": False}

    # Runtime overrides for feature flags (set via admin UI)
    _feature_overrides: ClassVar[dict[str, bool]] = {}

    def __getattribute__(self, name):
        if name.startswith("enable_") and name != "model_config":
            overrides = type(self)._feature_overrides
            if name in overrides:
                return overrides[name]
        return super().__getattribute__(name)


settings = Settings()
