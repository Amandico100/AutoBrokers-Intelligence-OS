import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { projetarCasos } from '@/lib/atendimento/casos';
import { type Stage } from '@/lib/attendance/dispatch-states';

export const dynamic = 'force-dynamic';

/**
 * CASOS — a lista por EPISÓDIO, com cursor e busca NO BANCO (SPEC-097 U5.2).
 *
 * GET ?busca=&cursor=&estagio=&limite=  →  `{ items, semana, indisponivel, cursor, has_more }`
 *
 * 🔴 Por que ela nasceu: a tela de Casos lia a rota da Fila e filtrava a busca
 * com `.filter()` no CLIENTE, sobre as 120 linhas que o `.limit(120)` deixava
 * passar. 📊 §1.5: 120 de 448 conversas da AutoFleet — 73% invisível — e um
 * protocolo de 60 dias devolvia "nada encontrado" **sem nunca perguntar ao
 * banco**. Um "nada encontrado" só vale quando quem disse zero foi o banco.
 *
 * ⛔ É a MESMA função da Fila (R5). O que muda é a LENTE: sem `group_by`, a
 * projeção lista episódios (`attendance_sessions`) com cursor
 * `(ultimo_evento_em, id)` — e o episódio sem conversa continua caso, rotulado
 * "sem conversa vinculada" (📊 E7: 42,2% das sessões).
 */
export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  let busca: string | undefined;
  let cursor: string | null = null;
  let estagio: Stage | undefined;
  let limite: number | undefined;
  try {
    const p = new URL(req.url).searchParams;
    busca = p.get('busca') || undefined;
    cursor = p.get('cursor');
    const pedido = p.get('estagio');
    if (pedido && pedido !== 'todos') estagio = pedido as Stage;
    const n = Number(p.get('limite'));
    if (Number.isFinite(n) && n > 0) limite = Math.min(n, 1000);
  } catch {
    /* sem query string — a primeira página, sem busca */
  }

  const projecao = await projetarCasos(ctx, estagio ? { estagio } : {}, { busca, cursor, limite });
  return NextResponse.json(projecao);
}
