import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * Libera o reenvio dos boletos JÁ ENVIADOS EM TESTE — SPEC-078 E.4.
 *
 * Por que isto existe
 * -------------------
 * 📊 Medido em 17/08/2026: a deduplicação da cobrança usa a chave
 * `(company_id, recibo, send_mode)` em `billing_sent_log`, **sem janela de
 * tempo e sem expurgo**. A query de leitura (`billing_collection.py:814-820`)
 * não filtra por data, e a tabela não tem nenhum `delete` em todo o backend.
 *
 * Isso é o comportamento CERTO em produção — o segurado não pode receber o
 * mesmo boleto duas vezes. Mas torna o teste um tiro só: os 4 recibos gravados
 * em 15/07 na Resulta nunca mais seriam enviados em modo `test`, e a única
 * saída era apagar linha à mão no banco.
 *
 * O que esta rota faz, e o que ela NUNCA faz
 * ------------------------------------------
 *     apaga  send_mode = 'test'    da corretora logada
 *     NÃO toca em 'live', 'approval' nem 'none'
 *
 * 🔴 A restrição a `test` não é conveniência, é a trava. Um botão que
 * limpasse `live` permitiria reenviar cobrança de verdade para um segurado que
 * já a recebeu — e a dedup permanente existe exatamente para impedir isso.
 * Errar aqui custa a confiança do segurado, não uma rodada de teste.
 *
 * E o `.eq('company_id')` é obrigatório: o backend usa service role, RLS
 * sozinho não protege (CLAUDE.md §7).
 */
export async function POST() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('billing_sent_log')
    .delete()
    .eq('company_id', ctx.companyId)
    .eq('send_mode', 'test')      // 🔴 NUNCA sem esta linha.
    .select('recibo');

  if (error) {
    console.error('[COBRANCA liberar-reenvio]', ctx.companyId, error.message);
    return NextResponse.json(
      { ok: false, error: 'Não foi possível liberar o reenvio.', details: [error.message] },
      { status: 500 },
    );
  }

  const quantos = (data || []).length;
  return NextResponse.json({
    ok: true,
    liberados: quantos,
    mensagem: quantos
      ? `${quantos} boleto(s) de teste liberado(s) — a próxima execução vai enviá-los de novo.`
      : 'Nenhum boleto de teste estava marcado como enviado. Nada a liberar.',
  });
}
