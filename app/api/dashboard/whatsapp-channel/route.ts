import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * Canal WhatsApp da corretora (SPEC-017 P1.3) — proxy autenticado por sessão.
 *
 * GET  ?action=status | qr      → estado da conexão / QR code (base64)
 * POST { action: 'setup', alert_number? } → cria/garante a instância Evolution
 *
 * O company_id vem SEMPRE da sessão (nunca do cliente). A chave interna
 * Next↔Backend nunca chega ao browser.
 */

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });
  const key = internalKey();
  if (!key) return NextResponse.json({ ok: false, error: 'Chave interna não configurada.' }, { status: 500 });

  const requested = req.nextUrl.searchParams.get('action');
  const action = requested === 'qr' ? 'qr' : requested === 'diagnostics' ? 'diagnostics' : 'status';
  try {
    const backend = getBackendUrl();
    const res = await fetch(
      `${backend}/api/whatsapp-channel/${action}?company_id=${encodeURIComponent(ctx.companyId)}`,
      { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
    );
    const json = await res.json().catch(() => ({}));
    return NextResponse.json(json, { status: res.status });
  } catch (e) {
    if (e instanceof BackendUrlError) {
      return NextResponse.json({ ok: false, error: 'Backend não configurado.' }, { status: 500 });
    }
    return NextResponse.json({ ok: false, error: 'Falha ao consultar o canal WhatsApp.' }, { status: 502 });
  }
}

export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });
  const key = internalKey();
  if (!key) return NextResponse.json({ ok: false, error: 'Chave interna não configurada.' }, { status: 500 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const alertNumber = typeof body.alert_number === 'string' ? body.alert_number.replace(/\D/g, '') : '';
  if (alertNumber && (alertNumber.length < 10 || alertNumber.length > 15)) {
    return NextResponse.json({ ok: false, error: 'Número de alerta inválido (use DDI+DDD+número).' }, { status: 400 });
  }

  // SPEC-049: configurar/editar o AVISO de queda a qualquer momento.
  if (body.action === 'set-alert') {
    const mode = String(body.mode || '');
    try {
      const backend = getBackendUrl();
      const res = await fetch(`${backend}/api/whatsapp-channel/set-alert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key },
        body: JSON.stringify({ company_id: ctx.companyId, mode, alert_number: alertNumber || null }),
        cache: 'no-store',
      });
      const json = await res.json().catch(() => ({}));
      return NextResponse.json(json, { status: res.status });
    } catch (e) {
      if (e instanceof BackendUrlError) {
        return NextResponse.json({ ok: false, error: 'Backend não configurado.' }, { status: 500 });
      }
      return NextResponse.json({ ok: false, error: 'Falha ao salvar o aviso.' }, { status: 502 });
    }
  }

  // Desconectar (founder 14/07): logout da instância Evolution pelo dashboard.
  if (body.action === 'disconnect') {
    try {
      const backend = getBackendUrl();
      const res = await fetch(`${backend}/api/whatsapp-channel/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key },
        body: JSON.stringify({ company_id: ctx.companyId }),
        cache: 'no-store',
      });
      const json = await res.json().catch(() => ({}));
      return NextResponse.json(json, { status: res.status });
    } catch (e) {
      if (e instanceof BackendUrlError) {
        return NextResponse.json({ ok: false, error: 'Backend não configurado.' }, { status: 500 });
      }
      return NextResponse.json({ ok: false, error: 'Falha ao desconectar o canal WhatsApp.' }, { status: 502 });
    }
  }

  try {
    const backend = getBackendUrl();
    const res = await fetch(`${backend}/api/whatsapp-channel/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key },
      body: JSON.stringify({
        company_id: ctx.companyId,
        alert_number: alertNumber || null,
      }),
      cache: 'no-store',
    });
    const json = await res.json().catch(() => ({}));
    return NextResponse.json(json, { status: res.status });
  } catch (e) {
    if (e instanceof BackendUrlError) {
      return NextResponse.json({ ok: false, error: 'Backend não configurado.' }, { status: 500 });
    }
    return NextResponse.json({ ok: false, error: 'Falha ao configurar o canal WhatsApp.' }, { status: 502 });
  }
}
