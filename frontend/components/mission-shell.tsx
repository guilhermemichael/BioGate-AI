"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { clearSession, getAccessToken, getStoredUser } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/check-in", label: "Check-in" },
  { href: "/security-logs", label: "Security Logs" },
  { href: "/sessions", label: "Sessions" },
  { href: "/devices", label: "Devices" },
];

export function MissionShell({
  children,
  title,
  subtitle,
}: {
  children: ReactNode;
  title: string;
  subtitle: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [userName, setUserName] = useState("Operator");
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    const user = getStoredUser<{ full_name?: string }>();
    if (user?.full_name) {
      setUserName(user.full_name);
    }
  }, []);

  return (
    <div className="page-shell">
      <aside className="sidebar">
        <div className="brand-kicker">BioGate AI</div>
        <h1 className="brand-title">Mission Control</h1>
        <p className="sidebar-copy">
          Identity verification, explainable risk scoring and security telemetry in one operational cockpit.
        </p>
        <div className="status-chip">
          <span className="status-dot" />
          Operational
        </div>
        <div className="panel" style={{ marginTop: 20 }}>
          <div className="metric-label">Active Operator</div>
          <div className="metric-value" style={{ fontSize: "1.2rem" }}>
            {userName}
          </div>
        </div>
        <nav className="nav-stack" style={{ marginTop: 20 }}>
          {links.map((link) => (
            <Link key={link.href} className={`nav-link ${pathname === link.href ? "active" : ""}`} href={link.href}>
              <span>{link.label}</span>
              <span className="mono">/</span>
            </Link>
          ))}
        </nav>
        <div className="button-row" style={{ marginTop: 20 }}>
          <Link className="button" href="/">
            Landing
          </Link>
          <button
            className="button danger"
            disabled={loggingOut}
            type="button"
            onClick={async () => {
              const token = getAccessToken();
              setLoggingOut(true);
              if (token) {
                try {
                  await apiFetch("/auth/logout", {
                    method: "POST",
                    body: JSON.stringify({ revoke_all: false }),
                  }, token);
                } catch {
                  // Local cleanup still happens even if the API call fails.
                }
              }
              clearSession();
              router.push("/login");
              setLoggingOut(false);
            }}
          >
            {loggingOut ? "Logging out..." : "Logout"}
          </button>
        </div>
      </aside>
      <main className="content-area">
        <section className="section-heading">
          <div>
            <div className="brand-kicker">Mission Feed</div>
            <h1>{title}</h1>
            <p className="section-subcopy">{subtitle}</p>
          </div>
          <div className="status-chip">
            <span className="status-dot" />
            Zero Trust Active
          </div>
        </section>
        {children}
      </main>
    </div>
  );
}
