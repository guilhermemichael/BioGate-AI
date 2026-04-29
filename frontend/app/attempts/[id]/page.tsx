"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MissionShell } from "@/components/mission-shell";
import { StatusBadge } from "@/components/status-badge";
import { getAccessToken } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { formatDate, formatPercentage } from "@/lib/format";
import { SecurityLogDetail } from "@/lib/types";

export default function AttemptDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<SecurityLogDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getAccessToken();
    if (!token || !params.id) {
      router.replace("/login");
      return;
    }

    apiFetch<SecurityLogDetail>(`/logs/${params.id}`, undefined, token)
      .then((payload) => setDetail(payload))
      .catch((caughtError) => setError(caughtError instanceof Error ? caughtError.message : "Failed to load detail."));
  }, [params.id, router]);

  return (
    <MissionShell
      title="Attempt Detail"
      subtitle="Single-attempt forensic view with decision reasons, transport metadata and linked audit events."
    >
      {error ? <p className="error-text">{error}</p> : null}
      {detail ? (
        <>
          <div className="grid split-grid">
            <div className="panel">
              <div className="section-heading">
                <div>
                  <div className="brand-kicker">Decision Snapshot</div>
                  <h2>{detail.attempt.attempt_id}</h2>
                </div>
                <StatusBadge value={detail.attempt.status} />
              </div>
              <div className="grid metrics">
                <div className="panel metric-card">
                  <div className="metric-label">Final Confidence</div>
                  <div className="metric-value">{formatPercentage(detail.attempt.final_confidence)}</div>
                </div>
                <div className="panel metric-card">
                  <div className="metric-label">Risk Score</div>
                  <div className="metric-value">{formatPercentage(detail.attempt.risk_score)}</div>
                </div>
              </div>
              <div className="architecture-list" style={{ marginTop: 14 }}>
                {detail.attempt.reasons.map((reason) => (
                  <span className="tag" key={reason}>
                    {reason}
                  </span>
                ))}
              </div>
              <div className="architecture-list" style={{ marginTop: 10 }}>
                {detail.attempt.risk_reasons.map((reason) => (
                  <span className="tag" key={reason}>
                    {reason}
                  </span>
                ))}
              </div>
            </div>
            <div className="panel">
              <div className="section-heading">
                <div>
                  <div className="brand-kicker">Transport Context</div>
                  <h2>Metadata</h2>
                </div>
              </div>
              <div className="form-grid">
                <div>
                  <div className="metric-label">User</div>
                  <div>{detail.attempt.user_name ?? detail.attempt.user_email ?? "Unknown"}</div>
                </div>
                <div>
                  <div className="metric-label">IP</div>
                  <div className="mono">{detail.attempt.ip_address ?? "n/a"}</div>
                </div>
                <div>
                  <div className="metric-label">Device</div>
                  <div className="mono">{detail.attempt.device_fingerprint ?? "n/a"}</div>
                </div>
                <div>
                  <div className="metric-label">Request ID</div>
                  <div className="mono">{detail.attempt.request_id ?? "n/a"}</div>
                </div>
                <div>
                  <div className="metric-label">Created</div>
                  <div>{formatDate(detail.attempt.created_at)}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="panel" style={{ marginTop: 18 }}>
            <div className="section-heading">
              <div>
                <div className="brand-kicker">Explainability</div>
                <h2>Score Breakdown</h2>
              </div>
              <StatusBadge value={detail.attempt.replay_detected ? "replay_detected" : "clean"} />
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Factor</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(detail.attempt.score_breakdown ?? {}).map(([factor, value]) => (
                    <tr key={factor}>
                      <td className="mono">{factor}</td>
                      <td>{formatPercentage(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel" style={{ marginTop: 18 }}>
            <div className="section-heading">
              <div>
                <div className="brand-kicker">Audit Trail</div>
                <h2>Related Events</h2>
              </div>
            </div>
            {detail.related_audit_events.length ? (
              <div className="timeline">
                {detail.related_audit_events.map((event) => (
                  <div className="timeline-item" key={event.id}>
                    <StatusBadge value={event.severity} />
                    <div>
                      <strong>{event.action}</strong>
                      <div className="metric-trend">{formatDate(event.created_at)}</div>
                      <div className="mono">{event.event_hash?.slice(0, 18) ?? "no-hash"}</div>
                    </div>
                    <div className="mono">{event.ip_address ?? "n/a"}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">No related audit entries.</div>
            )}
          </div>
        </>
      ) : (
        <div className="empty-state">Loading attempt detail...</div>
      )}
    </MissionShell>
  );
}
