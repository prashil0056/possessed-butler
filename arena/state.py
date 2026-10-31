import json
from datetime import datetime, timezone
from pathlib import Path


class ArenaState:
    """Shared state for the arena: current defense config, round timer, attack history."""

    def __init__(self, state_file: str = "arena/state.json"):
        self.state_file = Path(state_file)
        self.defense = self._load_defense()
        self.history = []
        self.round_start = None
        self.round_duration_seconds = 600  # 10 minutes

    def _load_defense(self) -> dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                pass
        return self._default_defense()

    def _default_defense(self) -> dict:
        return {
            "input_guard": True,
            "output_guard": True,
            "isolation": True,
            "hardened_butler": False,
            "extra_patterns": [],
        }

    def save_defense(self, new_defense: dict) -> None:
        self.defense = new_defense
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(new_defense, indent=2))

    def start_round(self) -> dict:
        self.round_start = datetime.now(timezone.utc)
        return self.round_info()

    def round_info(self) -> dict:
        if not self.round_start:
            return {"started": False, "elapsed": 0, "remaining": self.round_duration_seconds}
        elapsed = (datetime.now(timezone.utc) - self.round_start).total_seconds()
        remaining = max(0, self.round_duration_seconds - elapsed)
        return {
            "started": True,
            "elapsed": int(elapsed),
            "remaining": int(remaining),
            "duration": self.round_duration_seconds,
        }

    def add_attack(self, record: dict) -> None:
        self.history.append(record)
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def stats(self) -> dict:
        total = len(self.history)
        blocked = sum(1 for h in self.history if h.get("blocked"))
        breached = total - blocked
        return {
            "total": total,
            "blocked": blocked,
            "breached": breached,
            "block_rate": blocked / total if total else 0.0,
        }


arena_state = ArenaState()
