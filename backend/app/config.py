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
    llm_model: str = os.getenv("LLM_MODEL", "qwen25-7b-instruct")
    llm_api_key: str = os.getenv("LLM_API_KEY", "EMPTY")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "25"))
    llm_enabled: bool = _bool("LLM_ENABLED", True)
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
