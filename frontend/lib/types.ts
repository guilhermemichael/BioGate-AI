export type Organization = {
  id: string;
  name: string;
  slug: string;
  plan: string;
  is_active: boolean;
};

export type AuthPayload = {
  access_token: string;
  refresh_token: string;
  access_token_expires_in: number;
  refresh_token_expires_in: number;
  session_id: string;
  token_type: string;
  user: {
    id: string;
    organization_id: string;
    full_name: string;
    email: string;
    role: string;
    status: string;
    permissions: string[];
    organization: Organization | null;
  };
};

export type Attempt = {
  attempt_id: string;
  organization_id: string | null;
  user_id: string | null;
  email_attempted: string | null;
  context_score: number | null;
  face_score: number | null;
  voice_score: number | null;
  phrase_score: number | null;
  liveness_score: number | null;
  risk_score: number | null;
  final_confidence: number | null;
  risk_level: string | null;
  status: string;
  reasons: string[];
  decision_reasons: string[];
  risk_reasons: string[];
  score_breakdown: Record<string, number>;
  recommended_action: string | null;
  denial_reason: string | null;
  replay_detected: boolean;
  ip_address: string | null;
  user_agent: string | null;
  device_fingerprint: string | null;
  created_at: string;
};

export type AttemptsList = {
  total: number;
  limit: number;
  offset: number;
  items: Attempt[];
};

export type DashboardSummary = {
  total_attempts: number;
  approved: number;
  denied: number;
  manual_review: number;
  average_confidence: number;
  average_risk: number;
};

export type DashboardTrend = {
  items: Array<{
    day: string;
    average_confidence: number;
    average_risk: number;
    total_attempts: number;
  }>;
};

export type RiskDistribution = {
  items: Array<{
    risk_level: string;
    count: number;
  }>;
};

export type SecurityLogsList = {
  total: number;
  limit: number;
  offset: number;
  items: Array<{
    attempt_id: string;
    organization_id: string | null;
    user_id: string | null;
    user_name: string | null;
    user_email: string | null;
    session_id: string | null;
    status: string;
    risk_level: string | null;
    context_score: number | null;
    face_score: number | null;
    voice_score: number | null;
    phrase_score: number | null;
    liveness_score: number | null;
    risk_score: number | null;
    final_confidence: number | null;
    ip_address: string | null;
    user_agent: string | null;
    device_fingerprint: string | null;
    reasons: string[];
    risk_reasons: string[];
    score_breakdown: Record<string, number> | null;
    denial_reason: string | null;
    recommended_action: string | null;
    replay_detected: boolean;
    request_id: string | null;
    trace_id: string | null;
    correlation_id: string | null;
    created_at: string;
  }>;
};

export type SecurityLogDetail = {
  attempt: SecurityLogsList["items"][number];
  related_audit_events: Array<{
    id: string;
    organization_id: string | null;
    action: string;
    severity: string;
    created_at: string;
    ip_address: string | null;
    user_agent: string | null;
    request_id: string | null;
    trace_id: string | null;
    correlation_id: string | null;
    previous_hash: string | null;
    event_hash: string | null;
    new_data: Record<string, unknown> | null;
  }>;
};

export type SessionList = {
  items: Array<{
    id: string;
    user_id: string;
    organization_id: string;
    rotation_counter: number;
    ip_address: string | null;
    user_agent: string | null;
    created_at: string;
    last_used_at: string;
    expires_at: string;
    revoked_at: string | null;
    revoked_reason: string | null;
    is_current: boolean;
  }>;
};

export type TrustedDevicesList = {
  items: Array<{
    id: string;
    user_id: string;
    organization_id: string;
    fingerprint_preview: string | null;
    display_name: string | null;
    is_trusted: boolean;
    first_seen_at: string;
    last_seen_at: string;
    last_ip_address: string | null;
    last_user_agent: string | null;
  }>;
};

export type RealtimeEvent = {
  session_id: string;
  event: string;
  progress: number;
  message: string;
  result?: Attempt;
};
