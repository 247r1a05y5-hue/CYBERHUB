"""AI/ML model runner abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ModelMetadata:
    name: str
    version: str
    description: str
    framework: str = "custom"
    input_types: List[str] = field(default_factory=lambda: ["text", "json"])
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelHealth:
    is_healthy: bool
    status: str
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class ModelResult:
    predicted_class: str
    risk_score: float  # 0.0 to 100.0
    confidence: float  # 0.0 to 1.0
    probabilities: Dict[str, float] = field(default_factory=dict)
    feature_importances: Dict[str, float] = field(default_factory=dict)
    explanation: List[str] = field(default_factory=list)
    raw_output: Dict[str, Any] = field(default_factory=dict)


class ModelRunner(ABC):
    """Abstract base class for all AI/ML inference runners."""

    @abstractmethod
    def get_metadata(self) -> ModelMetadata:
        """Return metadata about the model."""
        pass

    @abstractmethod
    async def predict(self, features: Dict[str, Any]) -> ModelResult:
        """Run inference on the preprocessed feature dictionary."""
        pass

    @abstractmethod
    async def health_check(self) -> ModelHealth:
        """Check if model weights are loaded and ready."""
        pass
