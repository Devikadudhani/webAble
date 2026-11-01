import re
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class ScreenshotStorage(Protocol):
    def save(self, image: bytes) -> str:
        """Persist a screenshot and return a non-public storage reference."""

    def save_scenario(
        self,
        image: bytes,
        *,
        capture_id: str,
        viewport_name: str,
        scenario_id: str,
        width: int,
        height: int,
    ) -> str:
        """Persist a scenario screenshot under its capture and viewport identity."""


class LocalScreenshotStorage:
    def __init__(self, output_dir: Path) -> None:
        self._directory = output_dir / "screenshots"

    def save(self, image: bytes) -> str:
        self._directory.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.png"
        (self._directory / filename).write_bytes(image)
        return f"screenshots/{filename}"

    def save_scenario(
        self,
        image: bytes,
        *,
        capture_id: str,
        viewport_name: str,
        scenario_id: str,
        width: int,
        height: int,
    ) -> str:
        identifiers = (capture_id, viewport_name, scenario_id)
        if any(not re.fullmatch(r"[a-zA-Z0-9_-]+", value) for value in identifiers):
            raise ValueError("Scenario screenshot identifiers contain invalid characters.")
        if width <= 0 or height <= 0:
            raise ValueError("Scenario screenshot dimensions must be positive.")
        self._directory.mkdir(parents=True, exist_ok=True)
        filename = (
            f"scenario_{capture_id}_{viewport_name}_{scenario_id}_"
            f"{width}x{height}.png"
        )
        (self._directory / filename).write_bytes(image)
        return f"screenshots/{filename}"
