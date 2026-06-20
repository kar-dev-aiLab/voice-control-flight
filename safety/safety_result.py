# safety_result.py

from dataclasses import dataclass

@dataclass
class SafetyResult:
    allowed: bool
    reason: str
    risk_level: str  # LOW / MEDIUM / HIGH