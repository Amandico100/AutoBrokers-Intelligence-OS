import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/auxiliaries/server';

export const dynamic = 'force-dynamic';

const LIMIT = 20;

type ConvRow = {
  id: string;
  title: string | null;
  last_message_preview: string | null;
  session_id: string | null;
  created_at: string | null;
  updated_at: string | null;
};

/**
 * GET /api/auxiliaries/resumo-atendimentos/conversations
 * Lista conversas RECENTES da empresa do usuário (escopo company_id, anti-IDOR),
 * com contagem de mensagens, para o seletor de atendimento do Auxiliar.
 */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();

  const baseQuery = () =>
    supabase
      .from('conversations')
      .select('id, title, last_message_preview, session_id, created_at, updated_at')
      .eq('company_id', ctx.companyId)
      .limit(LIMIT);

  // Ordenação robusta: updated_at -> created_at -> sem ordenação.
  let res = await baseQuery().order('updated_at', { ascending: false });
  if (res.error) res = await baseQuery().order('created_at', { ascending: false });
  if (res.error) res = await baseQuery();
  if (res.error) {
    console.error('[AUX conversations]', res.error.message);
    return NextResponse.json({ error: 'Erro ao listar conversas' }, { status: 500 });
  }

  const rows = (res.data || []) as ConvRow[];

  // Contagem de mensagens por conversa (HEAD count, sem trazer linhas).
  const withCounts = await Promise.all(
    rows.map(async (c) => {
      const { count } = await supabase
        .from('messages')
        .select('id', { count: 'exact', head: true })
        .eq('conversation_id', c.id);
      return { ...c, message_count: count ?? 0 };
    }),
  );

  // Preferir conversas com mensagens, depois mais recentes.
  withCounts.sort((a, b) => {
    const am = a.message_count > 0 ? 1 : 0;
    const bm = b.message_count > 0 ? 1 : 0;
    if (am !== bm) return bm - am;
    const ad = new Date(a.updated_at || a.created_at || 0).getTime();
    const bd = new Date(b.updated_at || b.created_at || 0).getTime();
    return bd - ad;
  });

  const conversations = withCounts.map((c) => ({
    id: c.id,
    title: c.title || 'Conversa sem título',
    last_message_preview: c.last_message_preview || undefined,
    session_id: c.session_id || undefined,
    created_at: c.created_at || undefined,
    updated_at: c.updated_at || undefined,
    message_count: c.message_count,
  }));

  return NextResponse.json({ conversations });
}
