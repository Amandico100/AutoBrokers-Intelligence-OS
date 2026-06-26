import { NextRequest, NextResponse } from 'next/server';

import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import { assertSameOrigin, requireMasterAdmin } from '@/lib/admin/admin-auth';
import { resolveSessionCompany } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * POST /api/attendance/connectors/infocap/probe
 *
 * Diagnostico read-only: delega ao backend, que decifra o segredo via Vault.
 * Os modos policy_chain_contract, official_document_source_audit e
 * policy_identity_integrity_audit sao master-only
 * e retornam apenas metadados seguros. Nunca retornam valores/PII/segredo.
 */
export async function POST(req: NextRequest) {
  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    return NextResponse.json({ ok: false, error: 'Chave interna do backend nao configurada.' }, { status: 500 });
  }

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  const mode =
    body.mode === 'policy_chain_contract' ||
    body.mode === 'official_document_source_audit' ||
    body.mode === 'policy_identity_integrity_audit'
      ? body.mode
      : undefined;
  const queryType = body.query_type === 'name' ? 'name' : 'cpf';
  const query = typeof body.query === 'string' ? body.query.trim() : '';
  const codfil = typeof body.codfil === 'number' ? body.codfil : 1;
  const policyRef = typeof body.policy_ref === 'string' ? body.policy_ref.trim() : '';
  if (!query && !(mode === 'official_document_source_audit' && policyRef)) {
    return NextResponse.json({ ok: false, error: 'query e obrigatoria (CPF ou nome).' }, { status: 400 });
  }

  let targetCompanyId: string;
  if (mode === 'policy_chain_contract' || mode === 'official_document_source_audit' || mode === 'policy_identity_integrity_audit') {
    const originFail = assertSameOrigin(req);
    if (originFail) return NextResponse.json({ ok: false, error: originFail.error }, { status: originFail.status });
    const auth = await requireMasterAdmin();
    if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
    targetCompanyId = typeof body.company_id === 'string' ? body.company_id.trim() : '';
    if (!targetCompanyId) {
      return NextResponse.json({ ok: false, error: 'company_id e obrigatorio no diagnostico master.' }, { status: 400 });
    }
  } else {
    const ctx = await resolveSessionCompany();
    if (!ctx) return NextResponse.json({ ok: false, error: 'Nao autorizado' }, { status: 401 });
    targetCompanyId = ctx.companyId;
  }

  const requestedConnectionId = typeof body.tenant_connection_id === 'string' ? body.tenant_connection_id.trim() : '';

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json({ ok: false, error: 'Backend de IA nao configurado.' }, { status: 500 });
    }
    throw error;
  }

  try {
    const backendHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-AutoBrokers-Internal-Key': internalKey,
    };
    if (mode === 'policy_chain_contract' || mode === 'official_document_source_audit' || mode === 'policy_identity_integrity_audit') {
      backendHeaders['X-AutoBrokers-Master-Admin'] = 'true';
    }
    const res = await fetch(`${backendUrl}/attendance/connectors/infocap/probe`, {
      method: 'POST',
      headers: backendHeaders,
      body: JSON.stringify({
        company_id: targetCompanyId,
        tenant_connection_id: requestedConnectionId || undefined,
        query_type: queryType,
        query,
        codfil,
        mode,
        policy_ref: policyRef || undefined,
      }),
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    try {
      data = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }
    if (!res.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : typeof data.error === 'string' ? data.error : undefined;
      return NextResponse.json({
        ok: false,
        error: detail || `Backend retornou ${res.status}`,
      }, { status: res.status });
    }
    console.log(`[INFOCAP PROBE] mode=${mode || 'endpoint_probe'} query_type=${queryType} winner=${Boolean((data as any).winner_endpoint)}`);
    return NextResponse.json(data);
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'erro desconhecido';
    return NextResponse.json({ ok: false, error: `Falha ao conectar ao backend: ${msg}` }, { status: 502 });
  }
}
