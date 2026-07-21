import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * SPEC-043 — Segurados atendidos: clientes derivados dos atendimentos reais
 * (conversas + observação). Cresce sozinho conforme os atendimentos acontecem.
 */

const digits = (v: unknown) => String(v || '').replace(/\D/g, '');

export async function GET(_req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();

  type Atendimento = { conversa_id: string; quando: string | null; preview: string | null };
  type Segurado = {
    telefone: string; nome: string | null; atendimentos: number;
    ultimo_contato: string | null; conversa_id: string | null;
    historico: Atendimento[];
  };
  const byPhone = new Map<string, Segurado>();

  const { data: convs } = await supabase
    .from('conversations')
    .select('id, user_phone, user_name, last_message_at, last_message_preview, created_at')
    .eq('company_id', ctx.companyId)
    .eq('channel', 'whatsapp')
    .order('last_message_at', { ascending: false, nullsFirst: false })
    .limit(500);

  for (const c of convs || []) {
    const phone = digits(c.user_phone);
    if (!phone) continue;
    const cur = byPhone.get(phone);
    const when = c.last_message_at || c.created_at || null;
    // SPEC-046: perfil leve — cada segurado carrega os últimos atendimentos
    // (cada um abre a FICHA correspondente).
    const entry: Atendimento = { conversa_id: c.id, quando: when, preview: c.last_message_preview || null };
    if (!cur) {
      byPhone.set(phone, {
        telefone: phone,
        nome: (c.user_name || '').trim() || null,
        atendimentos: 1,
        ultimo_contato: when,
        conversa_id: c.id,
        historico: [entry],
      });
    } else {
      cur.atendimentos += 1;
      if (!cur.nome && (c.user_name || '').trim()) cur.nome = (c.user_name || '').trim();
      if (when && (!cur.ultimo_contato || when > cur.ultimo_contato)) cur.ultimo_contato = when;
      if (cur.historico.length < 5) cur.historico.push(entry);
    }
  }

  // Observação humana (Espelho): segurados atendidos pela equipe (pós-pareamento)
  try {
    const { data: sess } = await supabase
      .from('attendance_sessions')
      .select('counterparty, last_event_at, started_at')
      .eq('company_id', ctx.companyId)
      .order('last_event_at', { ascending: false })
      .limit(500);
    for (const s of sess || []) {
      const phone = digits(s.counterparty);
      if (!phone) continue;
      const when = s.last_event_at || s.started_at || null;
      const cur = byPhone.get(phone);
      if (!cur) {
        byPhone.set(phone, {
          telefone: phone, nome: null, atendimentos: 1,
          ultimo_contato: when, conversa_id: null, historico: [],
        });
      } else {
        cur.atendimentos += 1;
        if (when && (!cur.ultimo_contato || when > cur.ultimo_contato)) cur.ultimo_contato = when;
      }
    }
  } catch {
    /* segue só com as conversas */
  }

  const segurados = Array.from(byPhone.values()).sort((a, b) =>
    String(b.ultimo_contato || '').localeCompare(String(a.ultimo_contato || '')),
  );
  return NextResponse.json({ segurados });
}
