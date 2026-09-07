import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * "Pode tentar de novo esta parcela" — SPEC-EXTRA-001 §6 (U3).
 *
 * Por que isto existe
 * -------------------
 * A identidade da obrigação real é `(company_id, portal_key, recibo)`, sem
 * janela de tempo: uma parcela é cobrada UMA vez. Isso é o comportamento certo
 * — e deixa sem saída os casos em que a cobrança precisa mesmo sair de novo (o
 * texto foi e o PDF não, a entrega falhou, o item ficou adiado, ou o cliente
 * respondeu algo que a equipe resolveu e agora quer reenviar).
 *
 * Liberar devolve a linha ao estado `liberado`, que a próxima execução pode
 * reclamar. Não é um botão de conveniência: é uma decisão que faz uma pessoa
 * receber de novo uma cobrança, então ela exige MOTIVO escrito, e o motivo
 * fica no ledger.
 *
 * O que ela NUNCA faz
 * -------------------
 *   • ⛔ não libera `suprimido`. O cliente pediu para não receber — a supressão
 *     é TERMINAL (WhatsApp Business Policy: opt-out não se desfaz por decisão
 *     de quem envia). Responde 409, sempre.
 *   • ⛔ não libera `incerto`. "Não sei se saiu" liberado vira "mandei duas
 *     vezes" — o único jeito honesto é alguém conferir antes.
 *   • não envia mensagem nenhuma: só muda o estado no ledger.
 *   • não aceita `id` de outra corretora — 404 (IDOR, G18).
 */

/** Os estados de onde dá para tentar de novo sem risco de duplicar entrega. */
const LIBERAVEIS = ['entregue_equipe', 'parcial', 'falhou', 'adiado', 'contestado'];

/** Por que cada estado bloqueado está bloqueado — em português, para a tela. */
const PORQUE_NAO_LIBERA: Record<string, string> = {
  suprimido: 'O cliente pediu para não receber. Essa decisão é dele e não se desfaz por aqui.',
  incerto: 'Não sabemos se esta cobrança saiu. Liberar agora pode fazer o cliente receber duas vezes — confira antes.',
  liberado: 'Esta parcela já está liberada para a próxima execução.',
  reservado: 'Esta parcela está sendo trabalhada agora pela rotina.',
};

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
  const motivo = String(body.motivo || '').trim().slice(0, 500);
  if (!id) return NextResponse.json({ ok: false, error: 'Informe qual parcela liberar.' }, { status: 400 });
  // 🔴 O motivo é obrigatório e não é burocracia: quem lê o ledger depois
  // precisa saber por que um segurado recebeu a mesma cobrança duas vezes.
  if (!motivo) {
    return NextResponse.json(
      { ok: false, error: 'Escreva o motivo da liberação — ele fica registrado junto com a parcela.' },
      { status: 400 },
    );
  }

  const supabase = getSupabaseAdmin();

  const { data: linha, error: erroLeitura } = await supabase
    .from('billing_sent_log')
    .select('id, status, reserved_at')
    .eq('id', id)
    .eq('company_id', ctx.companyId)   // 🔴 NUNCA sem esta linha.
    .eq('send_mode', 'real')
    .maybeSingle();

  if (erroLeitura) {
    console.error('[COBRANCA liberar] leitura', ctx.companyId, erroLeitura.message);
    return NextResponse.json(
      { ok: false, error: 'Não consegui abrir esta pendência.', details: [erroLeitura.message] },
      { status: 500 },
    );
  }
  if (!linha) {
    return NextResponse.json({ ok: false, error: 'Pendência não encontrada.' }, { status: 404 });
  }

  const status = String(linha.status || '');
  // 🔴 A RESERVA ÓRFÃ tem porta de saída (juiz fresco 07/09, P-J3): um processo
  // que morreu com a reserva na mão deixava a parcela "reservado" para sempre —
  // nunca reclamada pela rotina, nunca liberável aqui. Passada 1 h da reserva,
  // ninguém está "trabalhando nela agora": a pessoa pode liberar, com motivo.
  const reservadaHaMs = linha.reserved_at ? Date.now() - new Date(String(linha.reserved_at)).getTime() : 0;
  const reservaOrfa = status === 'reservado' && reservadaHaMs > 60 * 60 * 1000;
  if (!LIBERAVEIS.includes(status) && !reservaOrfa) {
    return NextResponse.json(
      {
        ok: false,
        error: PORQUE_NAO_LIBERA[status] || 'Esta parcela não pode ser liberada no estado em que está.',
      },
      { status: 409 },
    );
  }

  const agora = new Date().toISOString();
  const { data: atualizadas, error } = await supabase
    .from('billing_sent_log')
    .update({ status: 'liberado', motivo, updated_at: agora })
    .eq('id', id)
    .eq('company_id', ctx.companyId)   // 🔴 NUNCA sem esta linha.
    .eq('send_mode', 'real')
    .in('status', reservaOrfa ? ['reservado'] : LIBERAVEIS)   // a corrida perde aqui, não no banco.
    .select('id');

  if (error) {
    console.error('[COBRANCA liberar]', ctx.companyId, error.message);
    return NextResponse.json(
      { ok: false, error: 'Não consegui liberar esta parcela.', details: [error.message] },
      { status: 500 },
    );
  }
  if (!atualizadas || atualizadas.length === 0) {
    return NextResponse.json(
      { ok: false, error: 'Esta pendência mudou de situação enquanto você decidia. Recarregue a lista.' },
      { status: 409 },
    );
  }

  return NextResponse.json({
    ok: true,
    id,
    // Para onde vai o reenvio é a MODALIDADE da rotina (equipe ou cliente), não
    // esta tela: dizer isso aqui evita a atendente esperar que "liberar" mande
    // ao cliente quando a rotina está em "Encaminhar para minha equipe"
    // (painel 07/09, lente produto+DADO P4). Com a rotina pausada, nada sai.
    mensagem:
      'Liberada. A próxima execução da rotina tenta de novo — pela modalidade configurada nela '
      + '(para a equipe ou direto ao cliente). Se a rotina estiver pausada, nada sai até ela rodar.',
  });
}
