/**
 * Thin fetch wrapper for the AdsGenerator FastAPI backend.
 *
 * Reads the base URL from `import.meta.env.VITE_API_URL` (set in `.env`).
 * Surface a typed-ish `ApiError` so callers can show structured errors
 * (e.g. the orchestrator's `failed_part`/`completed` payload).
 */

import { auth } from './firebase';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '');

/** Custom error carrying HTTP status + parsed backend detail (string or object). */
export class ApiError extends Error {
  constructor(message, { status, detail } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function parseError(response) {
  let detail;
  try {
    const body = await response.json();
    detail = body?.detail ?? body;
  } catch {
    try {
      detail = await response.text();
    } catch {
      detail = response.statusText;
    }
  }

  let message = `Request failed (${response.status})`;
  if (typeof detail === 'string' && detail) {
    message = detail;
  } else if (detail && typeof detail === 'object' && detail.error) {
    message = detail.error;
  } else if (detail && typeof detail === 'object' && detail.failed_part) {
    message = `Pipeline failed at step "${detail.failed_part}"`;
  }

  return new ApiError(message, { status: response.status, detail });
}

async function request(path, { method = 'GET', body, headers, signal } = {}) {
  const isFormData = body instanceof FormData;
  const finalHeaders = { Accept: 'application/json', ...(headers || {}) };
  if (body && !isFormData && !finalHeaders['Content-Type']) {
    finalHeaders['Content-Type'] = 'application/json';
  }

  if (auth.currentUser) {
    try {
      const token = await auth.currentUser.getIdToken();
      finalHeaders['Authorization'] = `Bearer ${token}`;
    } catch (e) {
      console.warn("Could not get Firebase token", e);
    }
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: finalHeaders,
      body: isFormData ? body : body == null ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err?.name === 'AbortError') throw err;
    throw new ApiError(`Network error: cannot reach backend at ${API_BASE}`, {
      status: 0,
      detail: String(err?.message || err),
    });
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

/* ------------------------------------------------------------------ */
/* Phase A — POST /ads/strategies                                      */
/* ------------------------------------------------------------------ */

export async function fetchStrategies({ file, area, count = 2, signal } = {}) {
  if (!file) throw new ApiError('A CSV file is required.', { status: 400 });
  const fd = new FormData();
  fd.append('file', file);
  if (area) fd.append('area', area);
  if (count) fd.append('count', String(count));
  return request('/ads/strategies', { method: 'POST', body: fd, signal });
}

/* ------------------------------------------------------------------ */
/* Phase B — POST /ads/finalize                                        */
/* ------------------------------------------------------------------ */

export async function finalizeStrategy({
  selectedStrategy,
  riskAnalysis,
  liveContext,
  area,
  signal,
} = {}) {
  if (!selectedStrategy) {
    throw new ApiError('A selected strategy is required.', { status: 400 });
  }
  return request('/ads/finalize', {
    method: 'POST',
    body: {
      selected_strategy: selectedStrategy,
      risk_analysis: riskAnalysis,
      live_context: liveContext,
      area: area ?? null,
    },
    signal,
  });
}

export const __TESTING__ = { API_BASE };
