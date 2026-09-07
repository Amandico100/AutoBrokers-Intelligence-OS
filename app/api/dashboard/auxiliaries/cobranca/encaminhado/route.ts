import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * "Já encaminhei esta parcela ao cliente" — SPEC-EXTRA-001 §6 (U3).
 *
 * Por que isto existe
 * -------------------
 * No modo `equipe` o pacote pronto vai para a atendente, e é ELA que repassa ao
 * segurado. Entre uma coisa e outra o ledger fica em `entregue_equipe`: a
 * plataforma entregou, e não tem como saber se o cliente recebeu. Sem alguém
 * dizendo, esse estado ficaria pendurado para sempre — e a fila de pendências
 * viraria uma lista que só cresce, que é como uma fila deixa de ser lida.
 *
 * Esta rota é a decisão humana sendo registrada. Ela marca QUANDO e QUEM.
 *
 * O que ela NUNCA faz
 * -------------------
 *   • não envia mensagem nenhuma — só carimba o ledger;
 *   • não libera reenvio (isso é a rota `liberar`, e exige motivo);
 *   • não aceita `id` de outra corretora: o `.eq('company_id')` faz a busca
 *     devolver vazio e a resposta é 404 — nunca "não autorizado", que já
 *     confirmaria a existência da linha (IDOR, G18).
 *
 * `encaminhado_por` é o usuário da SESSÃO, nunca um id vindo do corpo: quem
 * pode dizer quem assinou a decisão é o cookie, não o cliente HTTP.
 */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const id = String(body.id || '').trim();
  const motivo = String(body.motivo || '').trim();
  if (!id) return NextResponse.json({ ok: false, error: 'Informe qual parcela foi encaminhada.' }, { status: 400 });

  const supabase = getSupabaseAdmin();

  // Primeiro conferir de quem é a linha e em que estado ela está. Sem esta
  // leitura, um UPDATE que não pega linha nenhuma não sabe dizer se o id é de
  // outra corretora (404) ou se o estado não permite a ação (409) — e as duas
  // respostas mandam a pessoa para lugares diferentes.
  const { data: linha, error: erroLeitura } = await supabase
    .from('billing_sent_log')
    .select('id, status, encaminhado_ao_cliente_em')
    .eq('id', id)
    .eq('company_id', ctx.companyId)   // 🔴 NUNCA sem esta linha.
    .eq('send_mode', 'real')
    .maybeSingle();

  if (erroLeitura) {
    console.error('[COBRANCA encaminhado] leitura', ctx.companyId, erroLeitura.message);
    return NextResponse.json(
      { ok: false, error: 'Não consegui abrir esta pendência.', details: [erroLeitura.message] },
      { status: 500 },
    );
  }
  if (!linha) {
    return NextResponse.json({ ok: false, error: 'Pendência não encontrada.' }, { status: 404 });
  }
  if (String(linha.status) !== 'entregue_equipe') {
    return NextResponse.json(
      {
        ok: false,
        error: 'Só dá para marcar como encaminhada uma parcela que foi entregue à equipe.',
      },
      { status: 409 },
    );
  }
  if (linha.encaminhado_ao_cliente_em) {
    return NextResponse.json(
      { ok: false, error: 'Esta parcela já estava marcada como encaminhada ao cliente.' },
      { status: 409 },
    );
  }

  const agora = new Date().toISOString();
  const { data: atualizadas, error } = await supabase
    .from('billing_sent_log')
    .update({
      encaminhado_ao_cliente_em: agora,
      encaminhado_por: ctx.userId,
      updated_at: agora,
      ...(motivo ? { motivo } : {}),
    })
    .eq('id', id)
    .eq('company_id', ctx.companyId)   // 🔴 NUNCA sem esta linha.
    .eq('send_mode', 'real')
    .eq('status', 'entregue_equipe')
    .is('encaminhado_ao_cliente_em', null)
    .select('id');

  if (error) {
    console.error('[COBRANCA encaminhado]', ctx.companyId, error.message);
    return NextResponse.json(
      { ok: false, error: 'Não consegui registrar o encaminhamento.', details: [error.message] },
      { status: 500 },
    );
  }
  // Zero linhas aqui significa que alguém mudou o estado entre a leitura e a
  // escrita. Não é erro do servidor — é a corrida perdida, e ela se resolve
  // recarregando a lista.
  if (!atualizadas || atualizadas.length === 0) {
    return NextResponse.json(
      { ok: false, error: 'Esta pendência mudou de situação enquanto você decidia. Recarregue a lista.' },
      { status: 409 },
    );
  }

  return NextResponse.json({
    ok: true,
    id,
    mensagem: 'Marcada como encaminhada ao cliente.',
  });
}
