import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="landing">
      <section className="landing-hero">
        <div className="panel hero-panel">
          <div className="eyebrow">Biometric Identity and Behavioral Risk Intelligence</div>
          <h1>BioGate AI secures access with face, voice, phrase and explainable risk.</h1>
          <p className="mission-copy">
            Modern biometric check-ins with mission-control visibility: authentication, confidence scoring, auditability,
            security logs, realtime feedback and operational dashboards in one SaaS platform.
          </p>
          <div className="button-row">
            <Link className="button primary" href="/register">
              Create Account
            </Link>
            <Link className="button" href="/login">
              Operator Login
            </Link>
            <Link className="button" href="/check-in">
              View Demo Check-in
            </Link>
          </div>
          <div className="hero-list">
            <div className="hero-list-item">
              <strong>Multimodal Trust Chain</strong>
              Email or code, face, voice, phrase, device context and risk signals converge into one decision.
            </div>
            <div className="hero-list-item">
              <strong>Explainable Security</strong>
              Every check-in stores reasons, confidence, risk level, recommended action and audit traces.
            </div>
            <div className="hero-list-item">
              <strong>Mission Control UX</strong>
              Live verification timeline, dashboards, security logs and operator-grade visuals.
            </div>
          </div>
        </div>
        <div className="panel">
          <div className="section-heading">
            <div>
              <div className="brand-kicker">System Stack</div>
              <h2>Operational Layers</h2>
            </div>
          </div>
          <div className="hero-list">
            <div className="hero-list-item">
              <strong>Identity Core</strong>
              Register, login, JWT, refresh, protected routes and account lockout.
            </div>
            <div className="hero-list-item">
              <strong>Biometric Core</strong>
              Demo face, voice, phrase and liveness scoring with explainable decision output.
            </div>
            <div className="hero-list-item">
              <strong>Security Operations</strong>
              Dashboard summary, attempts history, enterprise logs, reports and WebSocket telemetry.
            </div>
          </div>
        </div>
      </section>

      <section className="grid split-grid" style={{ marginTop: 24 }}>
        <div className="panel">
          <div className="section-heading">
            <div>
              <div className="brand-kicker">Why It Matters</div>
              <h2>Not just a password check</h2>
            </div>
          </div>
          <div className="tag-list">
            <span className="tag">Face verification</span>
            <span className="tag">Voice verification</span>
            <span className="tag">Dynamic phrase</span>
            <span className="tag">Contextual risk</span>
            <span className="tag">Audit logs</span>
            <span className="tag">Confidence dashboards</span>
          </div>
        </div>
        <div className="panel">
          <div className="section-heading">
            <div>
              <div className="brand-kicker">Product Positioning</div>
              <h2>Enterprise-ready narrative</h2>
            </div>
          </div>
          <p className="section-subcopy">
            BioGate AI is positioned as a biometric authentication and behavioral risk platform. It explicitly avoids
            pseudoscience and instead focuses on security-grade signals that can be audited, explained and improved.
          </p>
        </div>
      </section>
    </main>
  );
}
