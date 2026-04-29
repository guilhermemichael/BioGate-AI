"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { setSession } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { AuthPayload } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("guilherme@example.com");
  const [password, setPassword] = useState("StrongPass123");
  const [organizationSlug, setOrganizationSlug] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const payload = await apiFetch<AuthPayload>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, organization_slug: organizationSlug || null }),
      });
      setSession({
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
        sessionId: payload.session_id,
        user: payload.user,
      });
      router.push("/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="landing" style={{ maxWidth: 760 }}>
      <div className="panel hero-panel">
        <div className="eyebrow">Operator Access</div>
        <h1 style={{ fontSize: "3rem" }}>Authenticate into Mission Control.</h1>
        <p className="mission-copy">
          Sign in to review biometric attempts, stream check-in telemetry and inspect risk explanations.
        </p>
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="organizationSlug">Organization Slug</label>
            <input
              id="organizationSlug"
              value={organizationSlug}
              onChange={(event) => setOrganizationSlug(event.target.value)}
              placeholder="optional for globally unique emails"
            />
          </div>
          {error ? <p className="error-text">{error}</p> : null}
          <div className="button-row">
            <button className="button primary" disabled={loading} type="submit">
              {loading ? "Authenticating..." : "Login"}
            </button>
            <Link className="button" href="/register">
              Create account
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}
