from app.domain.decision import DecisionInput, DecisionOutcome


class DecisionService:
    def evaluate(self, payload: DecisionInput) -> DecisionOutcome:
        score_breakdown = {
            "face_component": round(payload.face_score * 0.35, 4),
            "voice_component": round(payload.voice_score * 0.25, 4),
            "phrase_component": round(payload.phrase_score * 0.20, 4),
            "liveness_component": round(payload.liveness_score * 0.10, 4),
            "context_component": round(payload.context_score * 0.10, 4),
            "risk_penalty": round(payload.risk_score * 0.05, 4),
        }
        weighted_core = (
            score_breakdown["face_component"]
            + score_breakdown["voice_component"]
            + score_breakdown["phrase_component"]
            + score_breakdown["liveness_component"]
            + score_breakdown["context_component"]
        )
        final_confidence = self._normalize_score(weighted_core - score_breakdown["risk_penalty"])
        status = self._resolve_status(final_confidence)
        recommended_action = self._recommended_action_for_status(status)
        decision_reasons = self._build_decision_reasons(payload)
        explanation = self._build_explanation(status=status, final_confidence=final_confidence, payload=payload)

        return DecisionOutcome(
            final_confidence=final_confidence,
            status=status,
            decision_reasons=decision_reasons,
            recommended_action=recommended_action,
            score_breakdown=score_breakdown,
            explanation=explanation,
        )

    def _resolve_status(self, final_confidence: float) -> str:
        if final_confidence >= 0.85:
            return "approved"
        if final_confidence >= 0.65:
            return "manual_review"
        return "denied"

    def _recommended_action_for_status(self, status_value: str) -> str:
        if status_value == "approved":
            return "grant_access"
        if status_value == "manual_review":
            return "require_additional_verification"
        return "deny_and_retry"

    def _build_decision_reasons(self, payload: DecisionInput) -> list[str]:
        reasons: list[str] = []

        if payload.face_score >= 0.90:
            reasons.append("face_match_strong")
        elif payload.face_score >= 0.75:
            reasons.append("face_match_acceptable")
        else:
            reasons.append("face_match_weak")

        if payload.voice_score >= 0.85:
            reasons.append("voice_match_strong")
        elif payload.voice_score >= 0.70:
            reasons.append("voice_match_acceptable")
        else:
            reasons.append("voice_match_weak")

        if payload.phrase_score >= 0.95:
            reasons.append("phrase_verified")
        elif payload.phrase_score >= 0.80:
            reasons.append("phrase_partially_verified")
        else:
            reasons.append("phrase_mismatch_detected")

        if payload.liveness_score >= 0.85:
            reasons.append("liveness_signal_stable")
        else:
            reasons.append("liveness_needs_review")

        reasons.extend(payload.risk_reasons)
        reasons.append(f"risk_{payload.risk_level}")

        deduplicated: list[str] = []
        for reason in reasons:
            if reason not in deduplicated:
                deduplicated.append(reason)
        return deduplicated

    def _build_explanation(self, *, status: str, final_confidence: float, payload: DecisionInput) -> str:
        if status == "approved":
            return (
                f"Confidence {final_confidence:.2f} approved the check-in because face, voice, phrase and "
                f"liveness stayed within policy while contextual risk remained {payload.risk_level}."
            )
        if status == "manual_review":
            return (
                f"Confidence {final_confidence:.2f} triggered manual review because biometric quality or "
                f"contextual risk signals need a second factor."
            )
        return (
            f"Confidence {final_confidence:.2f} denied the attempt because biometric confidence was weak "
            f"or contextual risk escalated to {payload.risk_level}."
        )

    def _normalize_score(self, raw_score: float) -> float:
        bounded = min(max(raw_score, 0.01), 0.99)
        return round(bounded, 4)
