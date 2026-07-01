"""Placeholder for LangGraph orchestrator — wired in later phases."""

from app.config import get_settings


def build_orchestrator():
    """Returns the LangGraph state machine (Phase 3+)."""
    settings = get_settings()
    raise NotImplementedError(
        f"Orchestrator not built yet. States: {settings.target_state_list}"
    )
