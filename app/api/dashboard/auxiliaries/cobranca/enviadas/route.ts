import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

import { LIMITE_DE_LINHAS, desdeDoPeriodo, paraATela, periodoValido, type LinhaDoLedger } from './leitura';

export const dynamic = 'force-dynamic';

/**
 * O que a Cobrança ENVIOU — SPEC-139 · L2 (a aba Cobranças da casca).
 *
 * 📊 BLOCO 0 B3 (15/10/2026): a fonte é `billing_sent_log` — uma linha por parcela, escrita pelo motor da cobrança e
 * pela porta de saída. A única leitura pronta por corretora era a de `pendencias` (só o que espera decisão, só
 * `send_mode='real'`); "tudo o que saiu, por dia" não existia. Esta rota é só LEITURA.
 *
 * O que ela NUNCA faz
 *   • não envia, não escreve no ledger, não liga agente;
 *   • não devolve telefone — nem pede `to_phone` ao banco; só os 4 últimos dígitos (CLAUDE.md §7);
 *   • não devolve o nome inteiro do segurado: só o primeiro nome e as iniciais;
 *   • não devolve `canario`.
 *
 * 🔴 O `.eq('company_id', ctx.companyId)` é obrigatório: o backend usa service role, e RLS sozinha não protege contra
 * erro de filtro no código (CLAUDE.md §7). O teste da fatia tira esta linha e exige VERMELHO.
 *
 * GET ?periodo=7|30|90 (padrão 30) → { ok, periodo, limite, itens: CobrancaQueSaiu[] } (a mais recente primeiro)
 */
export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  const periodo = periodoValido(req.nextUrl.searchParams.get('periodo'));
  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('billing_sent_log')
    .select('id, status, send_mode, modalidade, portal_key, recibo, cliente_nome, to_last4, sent_at, created_at, encaminhado_ao_cliente_em')
    .eq('company_id', ctx.companyId)
    .gte('created_at', desdeDoPeriodo(periodo, new Date()))
    .order('created_at', { ascending: false })
    .limit(LIMITE_DE_LINHAS);

  if (error) {
    console.error('[COBRANCA enviadas]', ctx.companyId, error.message);
    return NextResponse.json(
      { ok: false, error: 'Não consegui carregar as cobranças agora.', details: [error.message] },
      { status: 500 },
    );
  }

  const itens = ((data || []) as LinhaDoLedger[]).map(paraATela);
  return NextResponse.json({ ok: true, periodo, limite: LIMITE_DE_LINHAS, itens });
}
