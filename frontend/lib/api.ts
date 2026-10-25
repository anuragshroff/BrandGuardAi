import type {
  Analytics,
  Finding,
  Guideline,
  Role,
  Scan,
  ScanListItem,
} from "./types";

const configured = process.env.NEXT_PUBLIC_API_URL;

// Next.js omits empty-string NEXT_PUBLIC_* vars from the client bundle, so the
// single-container build uses "/" as an explicit "same origin" marker. When the
// var is absent entirely, fall back to the local FastAPI dev server.
export const API_BASE =
  configured === undefined
    ? "http://localhost:8000"
    : configured === "/" || configured === "same-origin"
      ? ""
      : configured.replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function createScan(input: {
  title: string;
  content: string;
  channel: string;
  audience: string;
  region: string;
  campaign: string;
  actor: string;
  role: Role;
}): Promise<Scan> {
  return request<Scan>("/api/scans", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getScan(id: string): Promise<Scan> {
  return request<Scan>(`/api/scans/${id}`);
}

export function listScans(): Promise<{ items: ScanListItem[] }> {
  return request<{ items: ScanListItem[] }>("/api/scans?limit=20");
}

export function acceptFinding(
  scanId: string,
  finding: Finding,
  actor: string,
  role: Role,
): Promise<Scan> {
  return request<Scan>(`/api/scans/${scanId}/findings/${finding.id}/accept`, {
    method: "POST",
    body: JSON.stringify({ actor, role }),
  });
}

export function overrideFinding(
  scanId: string,
  findingId: string,
  note: string,
  actor: string,
  role: Role,
): Promise<Scan> {
  return request<Scan>(`/api/scans/${scanId}/findings/${findingId}/override`, {
    method: "POST",
    body: JSON.stringify({ actor, role, note }),
  });
}

export function addComment(
  scanId: string,
  body: string,
  actor: string,
  role: Role,
  findingId?: string,
): Promise<Scan> {
  return request<Scan>(`/api/scans/${scanId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body, author: actor, role, finding_id: findingId ?? null }),
  });
}

export function approveScan(scanId: string, actor: string, role: Role): Promise<Scan> {
  return request<Scan>(`/api/scans/${scanId}/approve`, {
    method: "POST",
    body: JSON.stringify({ actor, role }),
  });
}

export function publishScan(scanId: string, actor: string, role: Role): Promise<Scan> {
  return request<Scan>(`/api/scans/${scanId}/publish`, {
    method: "POST",
    body: JSON.stringify({ actor, role }),
  });
}

export function getAnalytics(): Promise<Analytics> {
  return request<Analytics>("/api/analytics");
}

export function getGuidelines(): Promise<{
  items: Guideline[];
  total_chunks: number;
  by_category: Record<string, number>;
}> {
  return request("/api/guidelines");
}

export function searchKnowledgeBase(
  query: string,
): Promise<{ query: string; items: Guideline[] }> {
  return request(`/api/knowledge-base/search?q=${encodeURIComponent(query)}&limit=6`);
}

export async function uploadGuideline(
  file: File,
  category: string,
  title: string,
): Promise<{ chunks: number }> {
  const form = new FormData();
  form.append("file", file);
  form.append("category", category);
  form.append("title", title);

  const response = await fetch(`${API_BASE}/api/guidelines/upload`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(`Upload failed (${response.status})`);
  }
  return response.json();
}

export function deleteGuideline(id: string): Promise<void> {
  return request<void>(`/api/guidelines/${id}`, { method: "DELETE" });
}
