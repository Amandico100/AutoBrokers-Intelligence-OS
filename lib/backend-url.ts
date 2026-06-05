import type { NextRequest } from 'next/server';

const LOCALHOST_PATTERN = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i;

function normalizeOrigin(value?: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().replace(/\/+$/, '');
  return trimmed || null;
}

export class BackendUrlError extends Error {
  code = 'BACKEND_URL_NOT_CONFIGURED';

  constructor(message = 'Backend URL is not configured for sandbox/production.') {
    super(message);
    this.name = 'BackendUrlError';
  }
}

export function getBackendUrl(_request?: NextRequest): string {
  const backendUrl =
    normalizeOrigin(process.env.NEXT_PUBLIC_API_URL) ||
    normalizeOrigin(process.env.NEXT_PUBLIC_BACKEND_URL) ||
    normalizeOrigin(process.env.BACKEND_URL) ||
    normalizeOrigin(process.env.API_URL);

  if (backendUrl && !LOCALHOST_PATTERN.test(backendUrl)) {
    return backendUrl;
  }

  if (process.env.NODE_ENV === 'production') {
    throw new BackendUrlError(
      'Backend URL is missing or points to localhost. Set NEXT_PUBLIC_API_URL or NEXT_PUBLIC_BACKEND_URL.',
    );
  }

  return backendUrl || 'http://localhost:8000';
}
