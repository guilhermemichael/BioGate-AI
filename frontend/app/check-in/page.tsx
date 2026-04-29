"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { MissionShell } from "@/components/mission-shell";
import { StatusBadge } from "@/components/status-badge";
import { getAccessToken } from "@/lib/auth";
import { apiFetch, getWebSocketUrl } from "@/lib/api";
import { formatPercentage } from "@/lib/format";
import { Attempt, RealtimeEvent } from "@/lib/types";

export default function CheckInPage() {
  const router = useRouter();
  const [spokenPhrase, setSpokenPhrase] = useState("I authorize this access.");
  const [expectedPhrase, setExpectedPhrase] = useState("I authorize this access.");
  const [faceQuality, setFaceQuality] = useState(0.91);
  const [voiceQuality, setVoiceQuality] = useState(0.84);
  const [livenessHint, setLivenessHint] = useState(0.88);
  const [deviceTrusted, setDeviceTrusted] = useState(true);
  const [networkTrusted, setNetworkTrusted] = useState(true);
  const [timeline, setTimeline] = useState<RealtimeEvent[]>([]);
  const [result, setResult] = useState<Attempt | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
    }
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getAccessToken();
    if (!token) {
      router.push("/login");
      return;
    }

    setTimeline([]);
    setResult(null);
    setError("");
    setLoading(true);

    const payload = {
      spoken_phrase: spokenPhrase,
      expected_phrase: expectedPhrase,
      face_capture_quality: faceQuality,
      voice_capture_quality: voiceQuality,
      liveness_hint: livenessHint,
      device_trusted: deviceTrusted,
      network_trusted: networkTrusted,
      device_fingerprint: navigator.userAgent,
    };

    const sessionId = `session-${Date.now()}`;
    const socket = new WebSocket(getWebSocketUrl(`/ws/biometric/check-in/${sessionId}`, token));

    socket.onmessage = async (eventData) => {
      const parsed = JSON.parse(eventData.data) as RealtimeEvent;
      setTimeline((current) => [...current, parsed]);

      if (parsed.event === "DECISION_READY") {
        try {
          const persisted = await apiFetch<Attempt>("/biometric/check-in", {
            method: "POST",
            body: JSON.stringify(payload),
          }, token);
          setResult(persisted);
        } catch (caughtError) {
          setError(caughtError instanceof Error ? caughtError.message : "Failed to persist check-in.");
        } finally {
          setLoading(false);
          socket.close();
        }
      }
    };

    socket.onerror = () => {
      setError("Realtime channel failed to initialize.");
      setLoading(false);
    };

    socket.onopen = () => {
      socket.send(JSON.stringify(payload));
    };
  }

  return (
    <MissionShell
      title="Biometric Check-in"
      subtitle="Simulate multimodal verification, stream operational events and persist the decision into the security ledger."
    >
      <div className="grid split-grid">
        <form className="panel form-grid" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="spokenPhrase">Spoken Phrase</label>
            <textarea id="spokenPhrase" value={spokenPhrase} onChange={(event) => setSpokenPhrase(event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="expectedPhrase">Expected Phrase</label>
            <input id="expectedPhrase" value={expectedPhrase} onChange={(event) => setExpectedPhrase(event.target.value)} />
          </div>
          <div className="inline-grid">
            <div className="field">
              <label htmlFor="faceQuality">Face Quality</label>
              <input id="faceQuality" type="number" min="0" max="1" step="0.01" value={faceQuality} onChange={(event) => setFaceQuality(Number(event.target.value))} />
            </div>
            <div className="field">
              <label htmlFor="voiceQuality">Voice Quality</label>
              <input id="voiceQuality" type="number" min="0" max="1" step="0.01" value={voiceQuality} onChange={(event) => setVoiceQuality(Number(event.target.value))} />
            </div>
            <div className="field">
              <label htmlFor="livenessHint">Liveness Hint</label>
              <input id="livenessHint" type="number" min="0" max="1" step="0.01" value={livenessHint} onChange={(event) => setLivenessHint(Number(event.target.value))} />
            </div>
          </div>
          <label className="checkbox-row">
            <input checked={deviceTrusted} onChange={(event) => setDeviceTrusted(event.target.checked)} type="checkbox" />
            Trusted device
          </label>
          <label className="checkbox-row">
            <input checked={networkTrusted} onChange={(event) => setNetworkTrusted(event.target.checked)} type="checkbox" />
            Trusted network
          </label>
          {error ? <p className="error-text">{error}</p> : null}
          <button className="button primary" disabled={loading} type="submit">
            {loading ? "Streaming verification..." : "Start Verification"}
          </button>
        </form>

        <div className="panel">
          <div className="section-heading">
            <div>
              <div className="brand-kicker">Realtime Feed</div>
              <h2>Verification Timeline</h2>
            </div>
            <div className="status-chip">{loading ? "Streaming" : "Idle"}</div>
          </div>
          {timeline.length ? (
            <div className="timeline">
              {timeline.map((entry, index) => (
                <div className="timeline-item" key={`${entry.event}-${index}`}>
                  <StatusBadge value={entry.event.toLowerCase()} />
                  <div>
                    <strong>{entry.event}</strong>
                    <div className="metric-trend">{entry.message}</div>
                  </div>
                  <div className="timeline-progress">{entry.progress}%</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">Start a verification to watch the WebSocket mission feed populate in real time.</div>
          )}
        </div>
      </div>

      {result ? (
        <div className="panel" style={{ marginTop: 18 }}>
          <div className="section-heading">
            <div>
              <div className="brand-kicker">Decision Engine</div>
              <h2>Persisted Result</h2>
            </div>
            <StatusBadge value={result.status} />
          </div>
          <div className="grid metrics">
            <div className="panel metric-card">
              <div className="metric-label">Face Score</div>
              <div className="metric-value">{formatPercentage(result.face_score)}</div>
            </div>
            <div className="panel metric-card">
              <div className="metric-label">Voice Score</div>
              <div className="metric-value">{formatPercentage(result.voice_score)}</div>
            </div>
            <div className="panel metric-card">
              <div className="metric-label">Phrase Score</div>
              <div className="metric-value">{formatPercentage(result.phrase_score)}</div>
            </div>
            <div className="panel metric-card">
              <div className="metric-label">Final Confidence</div>
              <div className="metric-value">{formatPercentage(result.final_confidence)}</div>
            </div>
          </div>
          <div className="panel" style={{ marginTop: 16 }}>
            <div className="metric-label">Decision Reasons</div>
            <div className="architecture-list" style={{ marginTop: 12 }}>
              {result.decision_reasons.map((reason) => (
                <span className="tag" key={reason}>
                  {reason}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </MissionShell>
  );
}
