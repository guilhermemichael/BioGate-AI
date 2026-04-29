"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MissionShell } from "@/components/mission-shell";
import { StatusBadge } from "@/components/status-badge";
import { getAccessToken } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { formatDate, formatPercentage } from "@/lib/format";
import { SecurityLogsList } from "@/lib/types";

export default function SecurityLogsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [logs, setLogs] = useState<SecurityLogsList | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    const params = new URLSearchParams();
    if (statusFilter) {
      params.set("status", statusFilter);
    }
    if (riskFilter) {
      params.set("risk_level", riskFilter);
    }

    apiFetch<SecurityLogsList>(`/logs?${params.toString()}`, undefined, token)
      .then((payload) => setLogs(payload))
      .catch((caughtError) => setError(caughtError instanceof Error ? caughtError.message : "Failed to load logs."));
  }, [riskFilter, router, statusFilter]);

  return (
    <MissionShell
      title="Security Logs"
      subtitle="Filter biometric attempts by outcome and risk to inspect the security story behind every access decision."
    >
      <div className="panel">
        <div className="inline-grid">
          <div className="field">
            <label htmlFor="statusFilter">Status</label>
            <select id="statusFilter" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">All</option>
              <option value="approved">Approved</option>
              <option value="manual_review">Manual Review</option>
              <option value="denied">Denied</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="riskFilter">Risk Level</label>
            <select id="riskFilter" value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}>
              <option value="">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <div className="panel">
        <div className="section-heading">
          <div>
            <div className="brand-kicker">Enterprise Ledger</div>
            <h2>Attempt Records</h2>
          </div>
          <div className="status-chip">{logs?.total ?? 0} items</div>
        </div>
        {logs?.items?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Status</th>
                  <th>Risk</th>
                  <th>Confidence</th>
                  <th>IP</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {logs.items.map((item) => (
                  <tr key={item.attempt_id}>
                    <td>
                      <Link href={`/attempts/${item.attempt_id}`}>
                        <strong>{item.user_name ?? item.user_email ?? "Unknown"}</strong>
                      </Link>
                      <div className="metric-trend">{item.user_email}</div>
                    </td>
                    <td>
                      <StatusBadge value={item.status} />
                    </td>
                    <td>
                      <StatusBadge value={item.risk_level} />
                    </td>
                    <td>{formatPercentage(item.final_confidence)}</td>
                    <td className="mono">{item.ip_address ?? "n/a"}</td>
                    <td>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No records match the current filter set.</div>
        )}
      </div>
    </MissionShell>
  );
}
