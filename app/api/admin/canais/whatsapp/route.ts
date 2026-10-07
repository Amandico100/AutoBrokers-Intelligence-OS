// SPEC-133-A F4 (D-133A-10) — o QR do Quem Cobra Menos no portal ADMIN.
//
// O MESMO contrato da rota do hub das corretoras (`app/api/dashboard/whatsapp-channel`):
//   GET  ?action=status | qr | pairing&attempt_id= | diagnostics
//   POST {action: pairing (method qr|phone) | retry | cancel | disconnect | set-alert}
// e o MESMO caminho até o provedor: `lib/vault/whatsapp-channel-proxy.ts` →
// `backend/app/api/whatsapp_channel.py` → `pairing_orchestrator.py`. Nenhum
// cliente do Evolution nasce aqui.
//
// O que muda são DUAS coisas, e só elas:
//   QUEM pode   → só administrador da PLATAFORMA (`requireMasterAdmin`, a mesma
//                 trava de provisionamento — confere a sessão E a linha viva em
//                 `admin_users`). Corretora nenhuma pareia o canal.
//   QUAL empresa → a do canal, achada no banco pelo tipo `platform_canal`
//                 (`lib/admin/canal-da-plataforma.ts`). ⛔ Nunca um `company_id`
//                 vindo do corpo ou da query: é assim que um IDOR entra.
//
// O `purpose` é `observer` porque é o que o pareamento grava para tudo que não
// é auxiliar (`channel_identity.purpose_canonico`). Quem tira o canal do caminho
// do observador é o desvio por `company_kind` no webhook (F1), não esta rota.
import { NextRequest, NextResponse } from 'next/server';

import { assertSameOrigin, requireMasterAdmin } from '@/lib/admin/admin-auth';
import { resolverEmpresaDoCanal } from '@/lib/admin/canal-da-plataforma';
import { writeAudit } from '@/lib/vault/server';
import { backendRequest, correlationId, internalKey } from '@/lib/vault/whatsapp-channel-proxy';

export const dynamic = 'force-dynamic';

const PURPOSE = 'observer';

function negar(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status });
}

export async function GET(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return negar(auth.status, auth.error);
  const canal = await resolverEmpresaDoCanal(auth.supabase);
  if (!canal.ok) return negar(canal.status, canal.detail);
  const key = internalKey();
  if (!key) return negar(500, 'internal_key_not_configured');

  const correlation = correlationId(req);
  const action = req.nextUrl.searchParams.get('action') || 'status';
  const attemptId = req.nextUrl.searchParams.get('attempt_id');
  const company = encodeURIComponent(canal.companyId);

  if (action === 'pairing' && attemptId) {
    return backendRequest(
      `/api/whatsapp-channel/pairing/${encodeURIComponent(attemptId)}?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  if (action === 'qr') {
    return backendRequest(`/api/whatsapp-channel/qr?company_id=${company}&purpose=${PURPOSE}`, key, correlation);
  }
  if (action === 'diagnostics') {
    return backendRequest(
      `/api/admin/whatsapp-channel/diagnostics?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  return backendRequest(`/api/whatsapp-channel/status?company_id=${company}&purpose=${PURPOSE}`, key, correlation);
}

export async function POST(req: NextRequest) {
  const origem = assertSameOrigin(req);
  if (origem) return negar(origem.status, origem.error);
  const auth = await requireMasterAdmin();
  if (!auth.ok) return negar(auth.status, auth.error);
  const canal = await resolverEmpresaDoCanal(auth.supabase);
  if (!canal.ok) return negar(canal.status, canal.detail);
  const key = internalKey();
  if (!key) return negar(500, 'internal_key_not_configured');

  const correlation = correlationId(req);
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const action = String(body.action || 'pairing');
  const attemptId = typeof body.attempt_id === 'string' ? body.attempt_id : '';

  // A autorização de Auxiliar é um consentimento da CORRETORA sobre o número dela.
  // O canal não tem Auxiliares; aceitar a ação aqui seria gravar um sim que ninguém deu.
  if (action === 'set-auxiliary-authorization') return negar(400, 'nao_se_aplica_ao_canal');

  // ⛔ A auditoria guarda QUAL ação e QUEM — nunca o número, nunca o QR.
  // `actor_user_id` fica nulo: o id de `admin_users` não é um usuário de corretora.
  await writeAudit(auth.supabase, {
    company_id: canal.companyId,
    event_type: 'whatsapp_channel.write',
    action,
    status: 'ok',
    actor_user_id: null,
    metadata: { correlation_id: correlation, admin_id: auth.ctx.adminId, origem: 'admin_canal' },
  });

  const alertNumber = typeof body.alert_number === 'string' ? body.alert_number.replace(/\D/g, '') : '';
  if (alertNumber && (alertNumber.length < 10 || alertNumber.length > 15)) return negar(400, 'numero_invalido');

  if (action === 'set-alert') {
    return backendRequest('/api/whatsapp-channel/set-alert', key, correlation, {
      method: 'POST',
      body: JSON.stringify({
        company_id: canal.companyId,
        purpose: PURPOSE,
        mode: String(body.mode || ''),
        alert_number: alertNumber || null,
      }),
    });
  }

  if (action === 'disconnect') {
    return backendRequest('/api/whatsapp-channel/disconnect', key, correlation, {
      method: 'POST',
      body: JSON.stringify({ company_id: canal.companyId, purpose: PURPOSE }),
    });
  }

  if ((action === 'retry' || action === 'cancel') && !attemptId) return negar(400, 'attempt_id_required');
  if (action === 'retry' || action === 'cancel') {
    return backendRequest(
      `/api/whatsapp-channel/pairing/${encodeURIComponent(attemptId)}/${action}`,
      key,
      correlation,
      {
        method: 'POST',
        body: JSON.stringify({ company_id: canal.companyId, purpose: PURPOSE, correlation_id: correlation }),
      },
    );
  }

  if (action !== 'pairing') return negar(400, 'acao_desconhecida');
  const method = body.method === 'phone' ? 'phone' : 'qr';
  const phoneNumber = typeof body.phone_number === 'string' ? body.phone_number.replace(/\D/g, '') : '';
  if (method === 'phone' && (phoneNumber.length < 10 || phoneNumber.length > 15)) {
    return negar(400, 'invalid_phone_number');
  }
  return backendRequest('/api/whatsapp-channel/pairing', key, correlation, {
    method: 'POST',
    body: JSON.stringify({
      company_id: canal.companyId,
      purpose: PURPOSE,
      method,
      phone_number: phoneNumber || null,
      correlation_id: correlation,
    }),
  });
}
