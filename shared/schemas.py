from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AttackResult:
    payload_hash: str
    technique: str
    target_config: str
    success: bool
    breach_type: str = "no_breach"
    response_snippet: str = ""
    timestamp: Optional[str] = None


@dataclass
class DefenseResult:
    payload_hash: str
    technique: str
    blocked: bool
    block_layer: Optional[str] = None
    reason: str = ""
    timestamp: Optional[str] = None


@dataclass
class Payload:
    technique: str
    payload: str
    notes: str = ""


@dataclass
class MetricsReport:
    attack_asr_overall: float = 0.0
    attack_asr_by_technique: dict = field(default_factory=dict)
    defense_block_rate: float = 0.0
    defense_block_rate_by_technique: dict = field(default_factory=dict)
    defense_fp_rate: float = 0.0
    defense_block_by_layer: dict = field(default_factory=dict)
    total_attack_payloads: int = 0
    total_defense_tests: int = 0