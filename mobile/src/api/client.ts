import { API_BASE_URL } from "../config";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  skipAuth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (!options.skipAuth && authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new ApiError(res.status, data.error ?? `Request failed (${res.status})`);
  }

  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export function videoFeedUrl(token: string, video?: string) {
  const params = new URLSearchParams({ token });
  if (video) params.set("video", video);
  return `${API_BASE_URL}/api/video_feed?${params.toString()}`;
}
