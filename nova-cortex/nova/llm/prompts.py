from __future__ import annotations

from nova.core.platform import SystemProfile
from nova.core.state import CortexState


def build_system_prompt(state: CortexState | None = None, system_profile: SystemProfile | None = None) -> str:
    profile_line = ""
    if system_profile is not None:
        profile_line = (
            f"System profile: {system_profile.distro_name} "
            f"(id={system_profile.distro_id}, like={system_profile.distro_like or 'unknown'})."
        )

    status_line = ""
    if state is not None:
        status_line = f"Runtime status: {state.render_status(system_profile)}."

    return " ".join(
        part
        for part in (
            "You are Nova Cortex, a local Linux assistant.",
            "Prefer safe, reversible actions and use tools when appropriate.",
            profile_line,
            status_line,
        )
        if part
    )
