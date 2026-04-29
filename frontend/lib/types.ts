export type AuthPayload = {
  access_token: string;
  refresh_token: string;
  access_token_expires_in: number;
  refresh_token_expires_in: number;
  token_type: string;
  user: {
    id: string;
    full_name: string;
    email: string;
    role: string;
    status: string;
  };
};

export type Attempt = {
  attempt_id: string;
  user_id: string | null;
  email_attempted: string | null;
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
  recommended_action: string | null;
  denial_reason: string | null;
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
    user_id: string | null;
    user_name: string | null;
    user_email: string | null;
    status: string;
    risk_level: string | null;
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
    denial_reason: string | null;
    recommended_action: string | null;
    created_at: string;
  }>;
};

export type SecurityLogDetail = {
  attempt: SecurityLogsList["items"][number];
  related_audit_events: Array<{
    id: string;
    action: string;
    severity: string;
    created_at: string;
    ip_address: string | null;
    user_agent: string | null;
    new_data: Record<string, unknown> | null;
  }>;
};

export type RealtimeEvent = {
  session_id: string;
  event: string;
  progress: number;
  message: string;
  result?: Attempt;
};
