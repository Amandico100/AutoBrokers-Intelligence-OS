import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * Conversas do atendimento (SPEC-017 S17-13) — lista da corretora logada.
 *
 * GET → { conversations: [...], dispatches: [...] }
 * - conversations: todas as conversas da company (aguardando humano primeiro),
 *   com claim (quem assumiu) e prévia da última mensagem.
 * - dispatches: acionamentos ATIVOS com a seguradora (espelho read-only,
 *   vindo do motor de dispatch no backend).
 */

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

export async function GET(_req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();

  const { data, error } = await supabase
    .from('conversations')
    .select(
      'id, session_id, channel, status, user_phone, user_name, unread_count, last_message_preview, last_message_at, claimed_by, claimed_by_name, claimed_at, created_at',
    )
    .eq('company_id', ctx.companyId)
    // Central de ATENDIMENTO: só canais externos (WhatsApp). As conversas do
    // Chat Principal (channel=web) vivem em Histórico — são outra coisa.
    .eq('channel', 'whatsapp')
    .order('last_message_at', { ascending: false, nullsFirst: false })
    .limit(200);

  if (error) {
    console.error('[CONVERSAS] list error:', error.message);
    return NextResponse.json({ error: 'Erro ao listar conversas' }, { status: 500 });
  }

  const conversations = (data || []).sort((a, b) => {
    const aH = a.status === 'HUMAN_REQUESTED' ? 1 : 0;
    const bH = b.status === 'HUMAN_REQUESTED' ? 1 : 0;
    if (aH !== bH) return bH - aH;
    return String(b.last_message_at || '').localeCompare(String(a.last_message_at || ''));
  });

  // Espelho dos acionamentos ativos (falha aqui nunca derruba a lista).
  let dispatches: unknown[] = [];
  const key = internalKey();
  if (key) {
    try {
      const backend = getBackendUrl();
      const res = await fetch(
        `${backend}/api/dispatch/active?company_id=${encodeURIComponent(ctx.companyId)}`,
        { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
      );
      if (res.ok) {
        const json = await res.json().catch(() => ({}));
        dispatches = Array.isArray(json?.dispatches) ? json.dispatches : [];
      }
    } catch (e) {
      if (!(e instanceof BackendUrlError)) console.error('[CONVERSAS] dispatch mirror error');
    }
  }

  return NextResponse.json({ conversations, dispatches, me: ctx.userId });
}
