from __future__ import annotations

import asyncio
from pathlib import Path

from nova.core.event_loop import CortexApp


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    print("Project Nova Cortex starting")
    print(f"Workspace: {project_root}")
    asyncio.run(CortexApp(project_root=project_root).run())


if __name__ == "__main__":
    main()
