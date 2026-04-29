"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { setSession } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { AuthPayload } from "@/lib/types";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("Guilherme Michael");
  const [email, setEmail] = useState("guilherme@example.com");
  const [password, setPassword] = useState("StrongPass123");
  const [organizationName, setOrganizationName] = useState("BioGate Labs");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const payload = await apiFetch<AuthPayload>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ full_name: fullName, email, password, organization_name: organizationName }),
      });
      setSession({
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
        sessionId: payload.session_id,
        user: payload.user,
      });
      router.push("/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="landing" style={{ maxWidth: 760 }}>
      <div className="panel hero-panel">
        <div className="eyebrow">Enrollment</div>
        <h1 style={{ fontSize: "3rem" }}>Create your BioGate AI operator account.</h1>
        <p className="mission-copy">
          The frontend is already wired to the FastAPI identity core, so a successful registration opens Mission Control immediately.
        </p>
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="fullName">Full name</label>
            <input id="fullName" value={fullName} onChange={(event) => setFullName(event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="organizationName">Organization</label>
            <input id="organizationName" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} />
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
          {error ? <p className="error-text">{error}</p> : null}
          <div className="button-row">
            <button className="button primary" disabled={loading} type="submit">
              {loading ? "Creating..." : "Register"}
            </button>
            <Link className="button" href="/login">
              Back to login
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}
