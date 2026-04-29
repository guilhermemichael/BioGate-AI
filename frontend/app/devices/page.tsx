"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MissionShell } from "@/components/mission-shell";
import { StatusBadge } from "@/components/status-badge";
import { clearSession, getAccessToken } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { TrustedDevicesList } from "@/lib/types";

export default function DevicesPage() {
  const router = useRouter();
  const [devices, setDevices] = useState<TrustedDevicesList | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");

  async function loadDevices(token: string) {
    try {
      const payload = await apiFetch<TrustedDevicesList>("/auth/devices", undefined, token);
      setDevices(payload);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Failed to load devices.";
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
    loadDevices(token);
  }, [router]);

  async function revokeDevice(deviceId: string) {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    setBusyId(deviceId);
    try {
      await apiFetch(`/auth/devices/${deviceId}`, { method: "DELETE" }, token);
      await loadDevices(token);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to revoke device.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <MissionShell
      title="Trusted Devices"
      subtitle="Track device trust state, recent activity and revoke endpoints that should trigger step-up verification next time."
    >
      {error ? <p className="error-text">{error}</p> : null}
      <div className="panel">
        <div className="section-heading">
          <div>
            <div className="brand-kicker">Device Trust Store</div>
            <h2>Registered Endpoints</h2>
          </div>
          <div className="status-chip">{devices?.items.length ?? 0} devices</div>
        </div>
        {devices?.items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Device</th>
                  <th>Trust</th>
                  <th>Last Seen</th>
                  <th>IP</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {devices.items.map((device) => (
                  <tr key={device.id}>
                    <td>
                      <strong>{device.display_name ?? "Unknown device"}</strong>
                      <div className="metric-trend mono">{device.fingerprint_preview ?? "no fingerprint"}</div>
                    </td>
                    <td>
                      <StatusBadge value={device.is_trusted ? "trusted" : "untrusted"} />
                    </td>
                    <td>{formatDate(device.last_seen_at)}</td>
                    <td className="mono">{device.last_ip_address ?? "n/a"}</td>
                    <td>
                      <button
                        className="button danger"
                        disabled={!device.is_trusted || busyId === device.id}
                        onClick={() => revokeDevice(device.id)}
                        type="button"
                      >
                        {busyId === device.id ? "Revoking..." : "Revoke Trust"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No devices have been registered yet for this operator.</div>
        )}
      </div>
    </MissionShell>
  );
}
