from dataclasses import dataclass


@dataclass(slots=True)
class DecisionInput:
    face_score: float
    voice_score: float
    phrase_score: float
    liveness_score: float
    context_score: float
    risk_score: float
    risk_level: str
    risk_reasons: list[str]


@dataclass(slots=True)
class DecisionOutcome:
    final_confidence: float
    status: str
    decision_reasons: list[str]
    recommended_action: str
