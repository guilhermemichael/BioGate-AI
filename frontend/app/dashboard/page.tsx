"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { LineChart } from "@/components/line-chart";
import { MetricCard } from "@/components/metric-card";
import { MissionShell } from "@/components/mission-shell";
import { RiskBars } from "@/components/risk-bars";
import { StatusBadge } from "@/components/status-badge";
import { clearSession, getAccessToken } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { formatDate, formatPercentage } from "@/lib/format";
import { Attempt, DashboardSummary, DashboardTrend, RiskDistribution } from "@/lib/types";

type DashboardRecent = {
  items: Attempt[];
};

export default function DashboardPage() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recent, setRecent] = useState<DashboardRecent | null>(null);
  const [riskDistribution, setRiskDistribution] = useState<RiskDistribution | null>(null);
  const [trend, setTrend] = useState<DashboardTrend | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    startTransition(() => {
      Promise.all([
        apiFetch<DashboardSummary>("/dashboard/summary", undefined, token),
        apiFetch<DashboardRecent>("/dashboard/recent-attempts", undefined, token),
        apiFetch<RiskDistribution>("/dashboard/risk-distribution", undefined, token),
        apiFetch<DashboardTrend>("/dashboard/confidence-trend?days=7", undefined, token),
      ])
        .then(([summaryPayload, recentPayload, riskPayload, trendPayload]) => {
          setSummary(summaryPayload);
          setRecent(recentPayload);
          setRiskDistribution(riskPayload);
          setTrend(trendPayload);
        })
        .catch((caughtError) => {
          const message = caughtError instanceof Error ? caughtError.message : "Failed to load dashboard.";
          setError(message);
          if (message.includes("401")) {
            clearSession();
            router.replace("/login");
          }
        });
    });
  }, [router]);

  return (
    <MissionShell
      title="Security Dashboard"
      subtitle="Executive summary of biometric attempts, confidence evolution and risk distribution."
    >
      {error ? <p className="error-text">{error}</p> : null}
      <div className="grid metrics">
        <MetricCard label="Total Attempts" value={String(summary?.total_attempts ?? 0)} trend="All persisted biometric check-ins." />
        <MetricCard label="Approved" value={String(summary?.approved ?? 0)} trend="Confidence exceeded operational threshold." />
        <MetricCard label="Manual Review" value={String(summary?.manual_review ?? 0)} trend="Additional verification recommended." />
        <MetricCard label="Average Confidence" value={formatPercentage(summary?.average_confidence ?? 0)} trend="Weighted multimodal trust score." />
      </div>

      <div className="grid chart-grid" style={{ marginTop: 18 }}>
        <LineChart
          title="Confidence Trend"
          points={(trend?.items ?? []).map((item) => ({
            label: item.day,
            value: item.average_confidence,
            secondary: item.average_risk,
          }))}
        />
        <RiskBars items={riskDistribution?.items ?? []} />
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <div className="section-heading">
          <div>
            <div className="brand-kicker">Recent Activity</div>
            <h2>Latest Check-ins</h2>
          </div>
          <div className="status-chip">{pending ? "Refreshing..." : "Live Snapshot"}</div>
        </div>
        {recent?.items?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Attempt</th>
                  <th>Status</th>
                  <th>Risk</th>
                  <th>Confidence</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {recent.items.map((attempt) => (
                  <tr key={attempt.attempt_id}>
                    <td className="mono">
                      <Link href={`/attempts/${attempt.attempt_id}`}>{attempt.attempt_id.slice(0, 12)}</Link>
                    </td>
                    <td>
                      <StatusBadge value={attempt.status} />
                    </td>
                    <td>
                      <StatusBadge value={attempt.risk_level} />
                    </td>
                    <td>{formatPercentage(attempt.final_confidence)}</td>
                    <td>{formatDate(attempt.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No attempts available yet. Use the Check-in screen to generate live data.</div>
        )}
      </div>
    </MissionShell>
  );
}
