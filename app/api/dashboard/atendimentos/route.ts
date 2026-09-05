import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { getBackendUrl } from '@/lib/backend-url';
import { projetarCasos, type Caso } from '@/lib/atendimento/casos';
import {
  type Stage,
  dispatchStateMeta,
  stageFromDispatchState,
} from '@/lib/attendance/dispatch-states';

export const dynamic = 'force-dynamic';

/**
 * A FILA de atendimentos — o Quadro do que está acontecendo AGORA.
 *
 * GET → `{ items, counts, semana, indisponivel, cursor, has_more }`
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * 🔴 SPEC-097 · U1.1/U1.3/U5.2 — ESTA ROTA DEIXOU DE SER UM READ MODEL.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * Ela tinha 380 linhas e QUATRO fontes montadas à mão, e a tela de Casos tinha
 * as suas. 📊 Medido em 05/09/2026 (SPEC-097 §1), o preço de haver duas leituras:
 *
 *   §1.1  a cascata terminava em `else stage = 'concluido'`: 584 de 668
 *         conversas (87,4%) apareciam encerradas, com `resolvido_em` NULL em
 *         728/728. **Ninguém encerrou nada** — o relógio encerrava.
 *   §1.1  e o MESMO payload dizia `semana.terminaram: 0`, porque o contador
 *         lia `resolvido_em` e a lista lia o relógio. Duas verdades num JSON.
 *   §1.2  a cascata testava `status` ANTES de `claimed_by`, e o claim gravava
 *         os dois juntos: a coluna "com a equipe" era INALCANÇÁVEL.
 *   §1.5  `.limit(120)` sobre 448 conversas da AutoFleet — 73% invisível — e a
 *         busca de Casos era `.filter()` no cliente sobre esses 120.
 *   §1.4  a mesma pessoa aparecia DUAS vezes: uma como conversa, outra como
 *         "Atendimento da equipe (observado)", porque a sessão do Atlas não
 *         tinha elo com a conversa e ninguém deduplicava (`:247`).
 *
 * ⛔ R5: `lib/atendimento/casos.ts::projetarCasos` é a ÚNICA função de leitura
 * do BANCO. Uma consulta própria aqui recria as duas verdades — e é o que o
 * guarda `scripts/a-operacao-tem-uma-casa.test.mjs` [1] mede, comparando as
 * consultas desta rota com as da projeção.
 *
 * ⚠️ O que continua aqui, e por quê: o Redis NÃO é banco. Ele é a fonte QUENTE
 * do acionamento em voo (`ura`, `human_phase`, `monitoring`), e a SPEC-085 §E
 * já custou esta lição — **somar, não substituir**: a linha durável de
 * `work_runs` (que a projeção lê) só nasce em `needs_human`, então trocar uma
 * pela outra tiraria da tela todo acionamento que está indo BEM.
 */

interface Dispatch {
  insurer_phone: string; case_id: string | null; state: string | null;
  subservice: string | null; client_phone: string | null;
  captured: Record<string, unknown>; created_at: string | null; playbook_ref?: string | null;
}

const digits = (v: unknown) => String(v || '').replace(/\D/g, '');

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  let estagio: Stage | undefined;
  try {
    const p = new URL(req.url).searchParams;
    const pedido = p.get('estagio');
    if (pedido) estagio = pedido as Stage;
  } catch {
    /* sem query string — a Fila inteira */
  }

  // 1) A FONTE QUENTE, primeiro: o acionamento que está acontecendo agora só
  //    existe no Redis (TTL de 6h). Ela vem ANTES da leitura durável porque é
  //    com ela que a comparação abaixo é feita.
  let dispatches: Dispatch[] = [];
  const key = internalKey();
  if (key) {
    try {
      const res = await fetch(
        `${getBackendUrl()}/api/dispatch/active?company_id=${encodeURIComponent(ctx.companyId)}`,
        { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
      );
      if (res.ok) dispatches = (await res.json())?.dispatches || [];
    } catch {
      /* a Fila abre sem o estado vivo — fail-soft */
    }
  }
  const dispatchClientPhones = new Map<string, Dispatch>();
  for (const d of dispatches) {
    const telefone = digits(d.client_phone);
    if (telefone && !dispatchClientPhones.has(telefone)) dispatchClientPhones.set(telefone, d);
  }

  // 2) A leitura durável — uma função só (R5).
  const projecao = await projetarCasos(ctx, estagio ? { estagio } : {}, { group_by: 'stage' });

  // 3) O casamento das duas. O acionamento vivo REFINA o card do segurado em
  //    vez de virar um card ao lado — 📊 §1.4: era assim que a mesma pessoa
  //    aparecia duas vezes na Fila.
  //
  // ⛔ E ele nunca ENCERRA: um `resolvido` do motor sem `resolvido_em` escrito
  //    era exatamente como 584 atendimentos apareciam terminados sem que
  //    ninguém os tivesse terminado (R1).
  //
  // 🔴 Nem apaga um TRAVAMENTO ABERTO: um caso cujo `unblock_state` durável
  //    ainda é `'travado'` ou `assumido_por_humano` continua em "precisa de
  //    você" — a atendente DESTRAVA, ela não assume, e o estado quente de
  //    segundos atrás não sabe disso.
  const items: Caso[] = projecao.items.map((caso) => {
    const vivo = caso.telefone ? dispatchClientPhones.get(caso.telefone) : undefined;
    if (!vivo || caso.resolvido_em) return caso;
    if (caso.unblock_state === 'travado' || caso.unblock_state === 'assumido_por_humano') return caso;
    const doMotor = stageFromDispatchState(vivo.state);
    if (doMotor === 'concluido') return caso;
    const protocolo = String((vivo.captured || {}).protocol || '') || caso.protocolo;
    return {
      ...caso,
      stage: doMotor,
      protocolo,
      detalhe: dispatchStateMeta(vivo.state).detalhe,
      agora: { ...caso.agora, situacao: dispatchStateMeta(vivo.state).detalhe },
    };
  });

  // Os contadores acompanham o que a tela vai mostrar — senão a coluna diz 3 e
  // lista 4, que é a contradição que a §1.1 mediu, só que em outro campo.
  const counts = { ...(projecao.counts || {}) } as Record<Stage, number>;
  for (const s of Object.keys(counts) as Stage[]) counts[s] = 0;
  for (const i of items) counts[i.stage] = (counts[i.stage] || 0) + 1;

  return NextResponse.json({ ...projecao, items, counts });
}
