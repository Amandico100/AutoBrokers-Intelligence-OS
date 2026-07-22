import { NextRequest, NextResponse } from 'next/server';

import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import { resolveSessionCompany } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

const BACKEND_TIMEOUT_MS = 20_000;
const PURPOSE = 'observer';

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

function correlationId(req: NextRequest): string {
  return req.headers.get('X-Correlation-ID') || crypto.randomUUID();
}

async function backendRequest(
  path: string,
  key: string,
  correlation: string,
  init: RequestInit = {},
): Promise<NextResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);
  try {
    const backend = getBackendUrl();
    const res = await fetch(`${backend}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-AutoBrokers-Internal-Key': key,
        'X-Correlation-ID': correlation,
        ...(init.headers || {}),
      },
      cache: 'no-store',
      signal: controller.signal,
    });
    const json = await res.json().catch(() => ({ detail: `backend_http_${res.status}` }));
    return NextResponse.json(json, {
      status: res.status,
      headers: { 'X-Correlation-ID': correlation },
    });
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json(
        { detail: 'backend_not_configured', correlation_id: correlation },
        { status: 500, headers: { 'X-Correlation-ID': correlation } },
      );
    }
    if ((error as { name?: string })?.name === 'AbortError') {
      return NextResponse.json(
        { detail: 'backend_timed_out', correlation_id: correlation },
        { status: 504, headers: { 'X-Correlation-ID': correlation } },
      );
    }
    return NextResponse.json(
      { detail: 'backend_unavailable', correlation_id: correlation },
      { status: 502, headers: { 'X-Correlation-ID': correlation } },
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });
  const key = internalKey();
  if (!key) return NextResponse.json({ detail: 'internal_key_not_configured' }, { status: 500 });

  const correlation = correlationId(req);
  const action = req.nextUrl.searchParams.get('action') || 'status';
  const attemptId = req.nextUrl.searchParams.get('attempt_id');
  const company = encodeURIComponent(ctx.companyId);

  if (action === 'pairing' && attemptId) {
    return backendRequest(
      `/api/whatsapp-channel/pairing/${encodeURIComponent(attemptId)}?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  if (action === 'qr') {
    return backendRequest(
      `/api/whatsapp-channel/qr?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  if (action === 'diagnostics') {
    return backendRequest(
      `/api/admin/whatsapp-channel/diagnostics?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  return backendRequest(
    `/api/whatsapp-channel/status?company_id=${company}&purpose=${PURPOSE}`,
    key,
    correlation,
  );
}

export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });
  const key = internalKey();
  if (!key) return NextResponse.json({ detail: 'internal_key_not_configured' }, { status: 500 });

  const correlation = correlationId(req);
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const action = String(body.action || 'pairing');
  const attemptId = typeof body.attempt_id === 'string' ? body.attempt_id : '';
  const alertNumber = typeof body.alert_number === 'string' ? body.alert_number.replace(/\D/g, '') : '';

  if (alertNumber && (alertNumber.length < 10 || alertNumber.length > 15)) {
    return NextResponse.json({ detail: 'numero_invalido' }, { status: 400 });
  }

  if (action === 'set-alert') {
    return backendRequest('/api/whatsapp-channel/set-alert', key, correlation, {
      method: 'POST',
      body: JSON.stringify({
        company_id: ctx.companyId,
        purpose: PURPOSE,
        mode: String(body.mode || ''),
        alert_number: alertNumber || null,
      }),
    });
  }

  if (action === 'disconnect') {
    return backendRequest('/api/whatsapp-channel/disconnect', key, correlation, {
      method: 'POST',
      body: JSON.stringify({ company_id: ctx.companyId, purpose: PURPOSE }),
    });
  }

  if ((action === 'retry' || action === 'cancel') && !attemptId) {
    return NextResponse.json({ detail: 'attempt_id_required' }, { status: 400 });
  }
  if (action === 'retry' || action === 'cancel') {
    return backendRequest(
      `/api/whatsapp-channel/pairing/${encodeURIComponent(attemptId)}/${action}`,
      key,
      correlation,
      {
        method: 'POST',
        body: JSON.stringify({
          company_id: ctx.companyId,
          purpose: PURPOSE,
          correlation_id: correlation,
        }),
      },
    );
  }

  const method = body.method === 'phone' ? 'phone' : 'qr';
  const phoneNumber = typeof body.phone_number === 'string' ? body.phone_number.replace(/\D/g, '') : '';
  if (method === 'phone' && (phoneNumber.length < 10 || phoneNumber.length > 15)) {
    return NextResponse.json({ detail: 'invalid_phone_number' }, { status: 400 });
  }
  return backendRequest('/api/whatsapp-channel/pairing', key, correlation, {
    method: 'POST',
    body: JSON.stringify({
      company_id: ctx.companyId,
      purpose: PURPOSE,
      method,
      phone_number: phoneNumber || null,
      correlation_id: correlation,
    }),
  });
}
