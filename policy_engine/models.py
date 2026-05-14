"""
Policy rule data models.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import datetime
import uuid


@dataclass
class PolicyRule:
    name: str
    type: Literal["BLOCK_TOOL", "REQUIRE_APPROVAL", "VALIDATE_INPUT", "BLOCK_KEYWORD"]
    config: dict
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "PolicyRule":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
