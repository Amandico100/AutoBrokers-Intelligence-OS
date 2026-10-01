/**
 * O diário de decisões da corretora — SPEC-123 F4.
 *
 * GET  → { items, cursor, has_more }   filtros: veredito, seguradora, classe, faixa, desde, ate, cursor
 * POST → { id, veredito: 'certo' | 'errado', o_certo_era?, sugere_regra? }
 *
 * ## O que é
 * Toda decisão que o agente tomou SOZINHO para destravar um atendimento vira uma
 * linha em `diario_de_decisoes` (escritor: `backend/app/services/diario_de_decisoes.py`).
 * A corretora lê a frase para gente e diz "certo" ou "errado" (+ "o certo era…").
 * "Errado" vira caso de bancada e, se for regra, rascunho de carta — o agente aprende.
 *
 * ## 🔴 A corretora vê SÓ as dela
 * Mesmo desenho de `acionamentos-travados/route.ts`: service role + `.eq('company_id', …)`
 * no REPOSITORY em toda leitura e escrita (CLAUDE.md §7 — a tabela tem RLS ligada e ZERO
 * policy: a RLS é rede, o filtro é este). O `middleware.ts` deixa `/api/` público: a rota
 * checa a sessão sozinha.
 *
 * ## 🔴 A tela lê o texto JÁ MASCARADO
 * `tela_mascarada` / `valor_mascarado` passaram por `higienizar_para_o_rastro` antes de
 * gravar. Não há coluna com o texto cru para pedir por engano.
 */
import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { assertSameOrigin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

const SELECT =
  'id, created_at, origem, seguradora, ramo, servico, classe, acao, nota, limiar, modo, ' +
  'explicacao_para_gente, tela_mascarada, valor_mascarado, segunda_opiniao, resultado, resultado_em, ' +
  'veredito, o_certo_era, sugere_regra, veredito_em';

/** As listas fechadas — as MESMAS dos CHECKs da migration `20260930_04`. */
const VEREDITOS = ['certo', 'errado'] as const;
const CLASSES = ['conduzir', 'responder_com_dado', 'deduzir', 'perguntar_ao_segurado', 'nunca_sozinho'];
/** Faixas de nota da calibração (D2): o limiar mínimo é 70, então as faixas começam nele. */
const FAIXAS: Record<string, [number, number]> = { '70-80': [70, 79], '80-90': [80, 89], '90-100': [90, 100] };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();
  const p = req.nextUrl.searchParams;
  const limit = Math.min(Math.max(Number(p.get('limit') || 30), 1), 50);

  let q = supabase
    .from('diario_de_decisoes')
    .select(SELECT)
    // 🔴 O filtro por corretora é do REPOSITORY, não da RLS (CLAUDE.md §7).
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false })
    .order('id', { ascending: false })
    .limit(limit + 1);

  // Por padrão, o que ainda espera avaliação — é o trabalho da pessoa nesta tela.
  const veredito = p.get('veredito') || 'sem';
  if (veredito === 'sem') q = q.is('veredito', null);
  else if ((VEREDITOS as readonly string[]).includes(veredito)) q = q.eq('veredito', veredito);

  const seguradora = (p.get('seguradora') || '').trim().toLowerCase();
  if (seguradora) q = q.eq('seguradora', seguradora);
  const classe = p.get('classe') || '';
  if (CLASSES.includes(classe)) q = q.eq('classe', classe);
  const faixa = FAIXAS[p.get('faixa') || ''];
  if (faixa) q = q.gte('nota', faixa[0]).lte('nota', faixa[1]);
  const desde = p.get('desde');
  if (desde && !Number.isNaN(Date.parse(desde))) q = q.gte('created_at', new Date(desde).toISOString());
  const ate = p.get('ate');
  if (ate && !Number.isNaN(Date.parse(ate))) q = q.lte('created_at', new Date(ate).toISOString());
  // Paginação por cursor — nunca um teto fixo que esconde o resto.
  const cursor = p.get('cursor');
  if (cursor && !Number.isNaN(Date.parse(cursor))) q = q.lt('created_at', cursor);

  const { data, error } = await q;
  if (error) {
    console.error('[decisoes] leitura falhou:', error.message);
    return NextResponse.json({ error: 'Não conseguimos carregar as decisões agora.' }, { status: 500 });
  }
  const linhas = (data || []) as any[];
  const temMais = linhas.length > limit;
  const pagina = linhas.slice(0, limit);
  return NextResponse.json({
    items: pagina.map((l) => ({
      id: l.id,
      quando: l.created_at,
      origem: l.origem,
      seguradora: l.seguradora,
      ramo: l.ramo,
      servico: l.servico,
      classe: l.classe,
      acao: l.acao,
      nota: l.nota,
      limiar: l.limiar,
      modo: l.modo,
      frase: l.explicacao_para_gente,
      tela: l.tela_mascarada,
      valor: l.valor_mascarado,
      segunda_opiniao_concordou:
        l.segunda_opiniao && typeof l.segunda_opiniao.concordou === 'boolean' ? l.segunda_opiniao.concordou : null,
      resultado: l.resultado,
      resultado_em: l.resultado_em,
      veredito: l.veredito,
      o_certo_era: l.o_certo_era,
      sugere_regra: Boolean(l.sugere_regra),
      avaliado_em: l.veredito_em,
    })),
    cursor: temMais ? pagina[pagina.length - 1]?.created_at ?? null : null,
    has_more: temMais,
  });
}

export async function POST(req: NextRequest) {
  const sameOrigin = assertSameOrigin(req);
  if (sameOrigin) return NextResponse.json({ error: sameOrigin.error }, { status: sameOrigin.status });

  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const id = String(body?.id || '');
  const veredito = String(body?.veredito || '');
  const oCertoEra = String(body?.o_certo_era || '').trim();
  const sugereRegra = Boolean(body?.sugere_regra);

  // 🔴 DOIS BOTÕES, E NÃO MAIS QUE DOIS: certo ou errado.
  if (!UUID.test(id) || !(VEREDITOS as readonly string[]).includes(veredito)) {
    return NextResponse.json({ error: 'id e veredito=certo|errado sao obrigatorios' }, { status: 400 });
  }
  // "Errado" sem dizer o que era o certo não ensina nada (o banco recusa também:
  // `ck_diario_errado_tem_o_certo`). A tela pede antes; aqui é a segunda porta.
  if (veredito === 'errado' && oCertoEra.length < 3) {
    return NextResponse.json({ error: 'Diga o que era o certo (pelo menos 3 letras).' }, { status: 400 });
  }

  const supabase = getSupabaseAdmin();
  // Existe, e é DESTA corretora? Sem isto, uma decisão de outra corretora e uma já
  // avaliada dariam o mesmo 409 — e o 409 viraria oráculo de existência de id.
  const { data: dona, error: erroDona } = await supabase
    .from('diario_de_decisoes')
    .select('id')
    .eq('id', id)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (erroDona) return NextResponse.json({ error: 'Não conseguimos salvar agora.' }, { status: 500 });
  if (!dona) return NextResponse.json({ error: 'Decisão não encontrada.' }, { status: 404 });

  // 🔴 ATÔMICO: `.is('veredito', null)` impede duas pessoas de avaliarem a mesma
  // decisão ao mesmo tempo — quem chega depois recebe 409 e vê o que o outro disse.
  const { data, error } = await supabase
    .from('diario_de_decisoes')
    .update({
      veredito,
      o_certo_era: veredito === 'errado' ? oCertoEra.slice(0, 1000) : null,
      sugere_regra: veredito === 'errado' ? sugereRegra : false,
      veredito_por: ctx.userId ?? null,
      veredito_em: new Date().toISOString(),
    })
    .eq('id', id)
    .eq('company_id', ctx.companyId)
    .is('veredito', null)
    .select('id, veredito')
    .maybeSingle();
  if (error) {
    console.error('[decisoes] veredito NAO gravado:', error.message);
    return NextResponse.json({ error: 'Não conseguimos salvar agora.' }, { status: 500 });
  }
  if (!data) {
    return NextResponse.json({ error: 'Esta decisão já foi avaliada por outra pessoa.' }, { status: 409 });
  }
  return NextResponse.json({ ok: true, veredito: data.veredito });
}
