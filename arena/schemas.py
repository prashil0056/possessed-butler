from pydantic import BaseModel, Field
from typing import List, Optional


class DefenseConfig(BaseModel):
    """Blue team's defense configuration. Toggles, not code."""
    input_guard: bool = True
    output_guard: bool = True
    isolation: bool = True
    hardened_butler: bool = False
    extra_patterns: List[str] = Field(default_factory=list)


class DefenseUpdateResponse(BaseModel):
    success: bool
    defense: DefenseConfig
    message: str


class AttackRequest(BaseModel):
    payload: str
    technique: str = "custom"


class AttackResponse(BaseModel):
    attack_id: str
    payload: str
    technique: str
    blocked: bool
    block_layer: Optional[str] = None
    reason: str
    response_snippet: str
    timestamp: str


class RoundInfo(BaseModel):
    started: bool
    elapsed: int = 0
    remaining: int = 600
    duration: int = 600


class StatsResponse(BaseModel):
    total: int
    blocked: int
    breached: int
    block_rate: float


class ArenaStatus(BaseModel):
    defense: DefenseConfig
    round: RoundInfo
    stats: StatsResponse
