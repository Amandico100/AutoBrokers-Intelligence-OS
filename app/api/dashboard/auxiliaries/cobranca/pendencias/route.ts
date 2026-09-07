import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * O que a cobrança REAL deixou pendente — SPEC-EXTRA-001 §6 (U3).
 *
 * Por que isto existe
 * -------------------
 * Nos modos reais (`equipe` e `cliente`) o ledger `billing_sent_log` deixa de
 * ser um carimbo de "enviado" e passa a ter ESTADOS: a parcela foi entregue à
 * equipe e ainda não chegou ao cliente; o texto saiu e o PDF não; o registro
 * falhou depois do envio e ninguém sabe se saiu. Nenhum desses estados se
 * resolve sozinho, e nenhum deles aparecia em tela — o relatório da rotina é
 * uma foto do dia, não uma fila de trabalho.
 *
 * Esta rota é a fila. Ela lê só o que **espera decisão humana** e devolve em
 * português; quem escreve a decisão são as rotas `encaminhado` e `liberar`.
 *
 * O que ela NUNCA faz
 * -------------------
 *   • não envia nada, não escreve no ledger, não liga agente;
 *   • não devolve telefone — só `to_last4`, os últimos 4 dígitos (CLAUDE.md §7);
 *   • não devolve linha de `send_mode='test'` (aquilo é simulação, não fila);
 *   • não devolve `canario` — a tela nunca expõe o canário.
 *
 * E o `.eq('company_id')` é obrigatório: o backend usa service role, RLS
 * sozinha não protege contra erro de filtro no código (CLAUDE.md §7).
 */

/** Os estados que PEDEM alguém — os demais não são pendência. */
const ESTADOS_PENDENTES = [
  'entregue_equipe',
  'parcial',
  'incerto',
  'contestado',
  'suprimido',
  'falhou',
  'adiado',
  // `liberado` fica na fila até a PRÓXIMA execução da rotina reenviar — senão a
  // liberação some da tela e, com a rotina pausada, ninguém mais a vê (painel
  // 07/09, lente produto+DADO P4).
  'liberado',
];

export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('billing_sent_log')
    .select(
      'id, status, modalidade, portal_key, recibo, cliente_nome, apolice_susep, to_last4, '
      + 'sent_at, updated_at, retorno_do_cliente, retorno_em, encaminhado_ao_cliente_em, motivo',
    )
    .eq('company_id', ctx.companyId)   // 🔴 NUNCA sem esta linha.
    .eq('send_mode', 'real')           // simulação não é fila de trabalho.
    .in('status', ESTADOS_PENDENTES)
    // `entregue_equipe` já encaminhado saiu da fila: a decisão foi tomada. Os
    // outros estados continuam pendentes tenham sido encaminhados ou não.
    .or('status.neq.entregue_equipe,encaminhado_ao_cliente_em.is.null')
    .order('updated_at', { ascending: false })
    .limit(100);

  if (error) {
    console.error('[COBRANCA pendencias]', ctx.companyId, error.message);
    return NextResponse.json(
      { ok: false, error: 'Não consegui carregar as pendências.', details: [error.message] },
      { status: 500 },
    );
  }

  return NextResponse.json({ ok: true, itens: data || [] });
}
