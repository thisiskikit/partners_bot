import type { ApiErrorResponse } from './ai.types';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
}

export async function requestJson<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(url, {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  const payload = (await response.json().catch(() => null)) as T | ApiErrorResponse | null;

  if (!response.ok || !payload) {
    const maybeError = payload as ApiErrorResponse | null;
    const message = maybeError?.error?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }

  if ((payload as ApiErrorResponse).ok === false) {
    throw new Error((payload as ApiErrorResponse).error.message);
  }

  return payload as T;
}
