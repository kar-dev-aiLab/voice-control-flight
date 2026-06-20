# command_result.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    command: str
    success: bool
    status: str
    state_reached: bool
    latency_ms: int
    ack_code: Optional[int] = None