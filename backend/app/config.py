"""Runtime configuration – everything comes from env vars (ConfigMap on OpenShift)."""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # OpenAI-compatible endpoint exposed by vLLM on OpenShift AI, e.g.
    # http://<model>-predictor.<namespace>.svc.cluster.local:8080/v1
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
    llm_model: str = os.getenv("LLM_MODEL", "granite-8b")
    llm_api_key: str = os.getenv("LLM_API_KEY", "EMPTY")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "60"))
    llm_enabled: bool = _bool("LLM_ENABLED", True)
    # Second OpenAI-compatible endpoint, tried when the primary one fails (e.g. primary = llm-d gateway,
    # fallback = the plain vLLM InferenceService). Empty = no failover, same behaviour as before.
    llm_fallback_base_url: str = os.getenv("LLM_FALLBACK_BASE_URL", "")
    llm_fallback_model: str = os.getenv("LLM_FALLBACK_MODEL", "")
    # CA to trust for an https:// fallback inside the cluster (OpenShift service CA, mounted in every pod)
    llm_fallback_ca_file: str = os.getenv("LLM_FALLBACK_CA_FILE", "")
    # After the primary endpoint fails, go straight to the fallback for this many seconds.
    llm_failover_cooldown_s: float = float(os.getenv("LLM_FAILOVER_COOLDOWN_S", "30"))
    # When ALL endpoints fail (down / timeout), answer from canned data for this many seconds (0 = off).
    llm_breaker_s: float = float(os.getenv("LLM_BREAKER_S", "45"))
    # If the model is unreachable or returns garbage, use canned answers instead of failing the demo.
    demo_fallback: bool = _bool("DEMO_FALLBACK", True)

    data_dir: Path = Path(os.getenv("DATA_DIR", ROOT / "data"))
    static_dir: Path = Path(os.getenv("STATIC_DIR", ROOT / "static"))

    forecast_days: int = int(os.getenv("FORECAST_DAYS", "90"))
    # Fixed "today" keeps the demo deterministic. Set DEMO_TODAY="" to use the real date.
    demo_today: str = os.getenv("DEMO_TODAY", "2026-11-20")
    # Small pause between trace events so the audience can follow the agents.
    trace_delay_s: float = float(os.getenv("TRACE_DELAY_S", "0.4"))

    def today(self) -> date:
        return date.fromisoformat(self.demo_today) if self.demo_today else date.today()


settings = Settings()
