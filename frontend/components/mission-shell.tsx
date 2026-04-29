"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { clearSession, getStoredUser } from "@/lib/auth";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/check-in", label: "Check-in" },
  { href: "/security-logs", label: "Security Logs" },
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
            type="button"
            onClick={() => {
              clearSession();
              router.push("/login");
            }}
          >
            Logout
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
