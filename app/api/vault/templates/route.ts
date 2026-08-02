import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * GET /api/vault/templates — os conectores que ESTA corretora conecta.
 *
 * SPEC-064 — não devolve os de `scope='platform'`.
 *
 * Firecrawl, Tavily e as fontes internas são infraestrutura do AutoBrokers: a
 * chave é nossa, todas as corretoras usam, e o consumo entra na conta delas.
 * Mostrar um card pedindo a chave do Firecrawl fazia a corretora achar que
 * precisava assinar um serviço para usar um Auxiliar que já funciona.
 *
 * O que aparece aqui é só o que tem dono do lado de lá: a conta da corretora
 * (InfoCap, portal da seguradora, Drive) e, no futuro, a conta da pessoa
 * (Outlook, Gmail). Ver docs/canon/CAMADAS-DE-CONEXAO.md.
 */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('connector_templates')
    .select('*')
    .eq('is_active', true)
    .neq('scope', 'platform');

  if (error) {
    console.error('[VAULT templates]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar templates' }, { status: 500 });
  }
  return NextResponse.json({ templates: data || [] });
}
