"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MissionShell } from "@/components/mission-shell";
import { StatusBadge } from "@/components/status-badge";
import { clearSession, getAccessToken } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { SessionList } from "@/lib/types";

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionList | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");

  async function loadSessions(token: string) {
    try {
      const payload = await apiFetch<SessionList>("/auth/sessions", undefined, token);
      setSessions(payload);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Failed to load sessions.";
      setError(message);
      if (message.includes("401")) {
        clearSession();
        router.replace("/login");
      }
    }
  }

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    loadSessions(token);
  }, [router]);

  async function revokeSession(sessionId: string) {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    setBusyId(sessionId);
    try {
      await apiFetch(`/auth/sessions/${sessionId}`, { method: "DELETE" }, token);
      await loadSessions(token);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to revoke session.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <MissionShell
      title="Active Sessions"
      subtitle="Inspect refresh rotation state, last activity and revoke sessions that should no longer be trusted."
    >
      {error ? <p className="error-text">{error}</p> : null}
      <div className="panel">
        <div className="section-heading">
          <div>
            <div className="brand-kicker">Session Control</div>
            <h2>Session Registry</h2>
          </div>
          <div className="status-chip">{sessions?.items.length ?? 0} sessions</div>
        </div>
        {sessions?.items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Status</th>
                  <th>Last Used</th>
                  <th>Expires</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sessions.items.map((session) => (
                  <tr key={session.id}>
                    <td>
                      <div className="mono">{session.id.slice(0, 12)}</div>
                      <div className="metric-trend">{session.user_agent ?? "Unknown device"}</div>
                    </td>
                    <td>
                      <StatusBadge value={session.revoked_at ? "revoked" : session.is_current ? "current" : "active"} />
                    </td>
                    <td>{formatDate(session.last_used_at)}</td>
                    <td>{formatDate(session.expires_at)}</td>
                    <td>
                      <button
                        className="button danger"
                        disabled={!!session.revoked_at || busyId === session.id}
                        onClick={() => revokeSession(session.id)}
                        type="button"
                      >
                        {busyId === session.id ? "Revoking..." : "Revoke"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No active sessions were found for this operator.</div>
        )}
      </div>
    </MissionShell>
  );
}
