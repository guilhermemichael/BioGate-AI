import { getAccessToken } from "./auth";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const wsBaseUrl = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

export function getApiBaseUrl() {
  return apiBaseUrl;
}

export function getWebSocketUrl(path: string, token?: string) {
  const url = new URL(path, wsBaseUrl.endsWith("/") ? wsBaseUrl : `${wsBaseUrl}/`);
  if (token) {
    url.searchParams.set("token", token);
  }
  return url.toString().replace("http://", "ws://").replace("https://", "wss://");
}

export async function apiFetch<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const resolvedToken = token ?? getAccessToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (resolvedToken) {
    headers.set("Authorization", `Bearer ${resolvedToken}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unexpected API error.");
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as T;
}
