export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const TOKEN_STORAGE_KEY = 'tq_auth_token';
const MODE_STORAGE_KEY = 'tq_api_mode';

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(message: string, status = 0, detail = '') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail || message;
  }
}

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function isDemoPreviewToken(token: string | null = getStoredToken()): boolean {
  return Boolean(token?.startsWith('demo.preview.token.'));
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage errors in restricted contexts
  }
}

export function getApiMode(): 'auto' | 'live_only' {
  try {
    const val = localStorage.getItem(MODE_STORAGE_KEY);
    return val === 'live_only' ? 'live_only' : 'auto';
  } catch {
    return 'auto';
  }
}

export function setApiMode(mode: 'auto' | 'live_only'): void {
  try {
    localStorage.setItem(MODE_STORAGE_KEY, mode);
  } catch {
    // Ignore
  }
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { timeoutMs = 4000, headers, body, ...rest } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const token = getStoredToken();
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

  const mergedHeaders: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(token && !isDemoPreviewToken(token) ? { Authorization: `Bearer ${token}` } : {}),
    ...(headers as Record<string, string> | undefined),
  };

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: mergedHeaders,
      body,
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = response.statusText || `Request failed (${response.status})`;
      try {
        const errJson = await response.json();
        if (typeof errJson.detail === 'string' && errJson.detail.trim()) {
          detail = errJson.detail;
        } else if (Array.isArray(errJson.detail) && errJson.detail.length > 0) {
          detail = errJson.detail
            .map((e: { msg?: string }) => e.msg || '')
            .filter(Boolean)
            .join('; ');
        } else if (typeof errJson.message === 'string' && errJson.message.trim()) {
          detail = errJson.message;
        }
      } catch {
        // Non-JSON error body
      }
      throw new ApiError(detail, response.status, detail);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('Backend request timed out.', 0, 'Connection timed out');
    }
    throw new ApiError(
      'Unable to reach TerraQora FastAPI backend.',
      0,
      err instanceof Error ? err.message : 'Network error'
    );
  } finally {
    clearTimeout(timer);
  }
}
