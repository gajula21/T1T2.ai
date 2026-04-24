/**
 * Typed API client for BandBoost backend.
 * Automatically injects Supabase JWT and parses quota headers.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────
export interface EvaluationScores {
  task_response: number;
  coherence: number;
  lexical: number;
  grammar: number;
  overall: number;
}

export interface EvaluationFeedback {
  task_response: string;
  coherence: string;
  lexical: string;
  grammar: string;
  improvements: string[];
}

export interface Evaluation {
  id: number;
  task_type: "task1" | "task2";
  status: "queued" | "processing" | "completed" | "failed";
  image_url: string | null;
  essay_text: string;
  word_count: number;
  scores: EvaluationScores | null;
  feedback: EvaluationFeedback | null;
  model_used: string;
  cache_hit: boolean;
  overall_band: number | null;
  error_message: string;
  task_question: string | null;
  created_at: string;
  updated_at: string;
}

export interface EvaluationListItem {
  id: number;
  task_type: "task1" | "task2";
  status: string;
  word_count: number;
  overall_band: number | null;
  essay_excerpt: string;
  created_at: string;
}

export interface QuotaStatus {
  limit: number;
  used: number;
  remaining: number;
  resets_in_seconds: number;
  resets_at_ist_midnight: boolean;
}

export interface EvaluationListResponse {
  count: number;
  page: number;
  page_size: number;
  results: EvaluationListItem[];
  stats: {
    total_evaluations: number;
    average_band: number | null;
    best_band: number | null;
  };
}

export interface SubmitResponse {
  id: number;
  status: string;
  quota_remaining: number;
}

// ─────────────────────────────────────────────
// Core fetch wrapper
// ─────────────────────────────────────────────
interface FetchOptions extends RequestInit {
  token?: string;
}

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  quota?: QuotaStatus;
}

async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<ApiResponse<T>> {
  const { token, ...fetchOpts } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOpts.headers as Record<string, string> ?? {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...fetchOpts,
      headers,
    });
  } catch (err) {
    return { data: null, error: "Network error. Please check your connection." };
  }

  // Parse quota headers if present
  const quota: QuotaStatus | undefined = response.headers.get("X-Quota-Limit")
    ? {
        limit: parseInt(response.headers.get("X-Quota-Limit") ?? "5"),
        used: parseInt(response.headers.get("X-Quota-Used") ?? "0"),
        remaining: parseInt(response.headers.get("X-Quota-Remaining") ?? "5"),
        resets_in_seconds: parseInt(response.headers.get("X-Quota-Resets-In") ?? "0"),
        resets_at_ist_midnight: true,
      }
    : undefined;

  if (!response.ok) {
    let errorMsg = `HTTP ${response.status}`;
    try {
      const errData = await response.json();
      errorMsg = errData.message ?? errData.detail ?? errorMsg;
    } catch {}

    if (response.status === 429) {
      errorMsg = errorMsg || "Rate limit exceeded. Please wait before trying again.";
    }
    return { data: null, error: errorMsg, quota };
  }

  // Handle empty responses (e.g., 204)
  if (response.status === 204) {
    return { data: null, error: null, quota };
  }

  // Handle binary (PDF)
  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/pdf")) {
    const blob = await response.blob();
    return { data: blob as unknown as T, error: null, quota };
  }

  const data = await response.json();
  return { data, error: null, quota };
}

// ─────────────────────────────────────────────
// API methods
// ─────────────────────────────────────────────
export const api = {
  submitTask1: (formData: FormData, token: string) =>
    fetch(`${API_BASE}/evaluate/task1`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) return { data: null, error: data.message ?? "Submission failed" };
      return { data: data as SubmitResponse, error: null };
    }),

  submitTask2: (essay: string, token: string, taskQuestion?: string) =>
    apiFetch<SubmitResponse>("/evaluate/task2", {
      method: "POST",
      body: JSON.stringify({ 
        essay_text: essay,
        task_question: taskQuestion 
      }),
      token,
    }),

  getEvaluation: (id: number, token: string) =>
    apiFetch<Evaluation>(`/evaluate/${id}`, { token }),

  listEvaluations: (page: number, token: string) =>
    apiFetch<EvaluationListResponse>(`/evaluations?page=${page}`, { token }),

  getQuota: (token: string) =>
    apiFetch<QuotaStatus>("/quota", { token }),

  exportPdf: async (id: number, token: string): Promise<Blob | null> => {
    const res = await apiFetch<Blob>(`/evaluations/${id}/export`, { token });
    return res.data;
  },
};

// ─────────────────────────────────────────────
// Polling utility
// ─────────────────────────────────────────────
export async function pollEvaluation(
  id: number,
  token: string,
  onUpdate: (evaluation: Evaluation) => void,
  intervalMs = 2000,
  maxAttempts = 60
): Promise<Evaluation | null> {
  let attempts = 0;

  return new Promise((resolve) => {
    const interval = setInterval(async () => {
      attempts++;
      const { data } = await api.getEvaluation(id, token);

      if (data) {
        onUpdate(data);

        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
          resolve(data);
        }
      }

      if (attempts >= maxAttempts) {
        clearInterval(interval);
        resolve(null);
      }
    }, intervalMs);
  });
}
