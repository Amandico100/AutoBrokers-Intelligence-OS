import type { NextRequest } from 'next/server';

const LOCALHOST_PATTERN = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i;

function normalizeOrigin(value?: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().replace(/\/+$/, '');
  return trimmed || null;
}

export function getPublicAppUrl(request?: NextRequest): string {
  const explicitUrl =
    normalizeOrigin(process.env.NEXT_PUBLIC_APP_URL) ||
    normalizeOrigin(process.env.NEXT_PUBLIC_SITE_URL) ||
    normalizeOrigin(process.env.NEXT_PUBLIC_BASE_URL) ||
    normalizeOrigin(process.env.APP_URL) ||
    normalizeOrigin(process.env.FRONTEND_URL);

  if (explicitUrl && !LOCALHOST_PATTERN.test(explicitUrl)) return explicitUrl;

  const requestOrigin = normalizeOrigin(request?.nextUrl?.origin);
  if (requestOrigin && !LOCALHOST_PATTERN.test(requestOrigin)) {
    return requestOrigin;
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error(
      'PUBLIC_APP_URL_NOT_CONFIGURED: Set NEXT_PUBLIC_APP_URL or FRONTEND_URL to the public web URL.',
    );
  }

  return requestOrigin || 'http://localhost:3000';
}
