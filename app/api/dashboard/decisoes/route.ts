/**
 * O diário de decisões da corretora — SPEC-123 F4.
 *
 * GET  → { items, cursor, has_more }   filtros: veredito, seguradora, classe, faixa, desde, ate, cursor
 * POST → { id, veredito: 'certo' | 'errado', o_certo_era?, sugere_regra? }
 *      → { acao: 'pausar_seguradora', seguradora, confirmar: true, motivo? }   (SPEC-125 S6, só admin)
 *
 * SPEC-125 S6: o GET da primeira página traz o PLACAR (`lib/diario/placar.ts`) e o modo do agente
 * por seguradora; as linhas trazem a fala/tela COMPLETA (`tela_completa`) — ordem do Founder: "o
 * diário pode vir completo para a corretora". Ela é lida aqui SÓ com o filtro da corretora dona.
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
import { assertSameOrigin, requireCompanyMember } from '@/lib/admin/admin-auth';
import { logSystemAction } from '@/lib/logger';
import { calcularPlacar, COLUNAS_DO_PLACAR } from '@/lib/diario/placar';

export const dynamic = 'force-dynamic';

const SELECT =
  'id, created_at, origem, seguradora, ramo, servico, classe, acao, nota, limiar, modo, ' +
  'explicacao_para_gente, tela_mascarada, valor_mascarado, segunda_opiniao, resultado, resultado_em, ' +
  'veredito, o_certo_era, sugere_regra, veredito_em, momento, tela_completa, valor_completo';
/** Janela do placar: 30 dias (a tendência compara os últimos 7 com os 7 anteriores). */
const JANELA_DO_PLACAR_DIAS = 30;
/** A chave da seguradora no `cerebro_modos` (CHECK `ck_cerebro_modos_insurer_minusculo`). */
const SEGURADORA = /^[a-z0-9_]{2,40}$/;

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

  // O PLACAR só na primeira página (o "carregar mais" não recalcula). Mesma corretora, sempre.
  let placar = null;
  const modos: Record<string, string> = {};
  if (!cursor) {
    const desde = new Date(Date.now() - JANELA_DO_PLACAR_DIAS * 86_400_000).toISOString();
    const { data: doPlacar } = await supabase
      .from('diario_de_decisoes')
      .select(COLUNAS_DO_PLACAR)
      .eq('company_id', ctx.companyId)
      .gte('created_at', desde)
      .limit(5000);
    placar = calcularPlacar((doPlacar || []) as any[], new Date(), JANELA_DO_PLACAR_DIAS);
    const { data: chaves } = await supabase
      .from('cerebro_modos')
      .select('insurer_key, ramo, modo')
      .eq('company_id', ctx.companyId);
    for (const c of (chaves || []) as any[]) {
      // pausada = TODAS as linhas daquela seguradora em `off` (uma linha `on` por ramo ainda age)
      const k = String(c.insurer_key);
      modos[k] = modos[k] === 'ligado' || c.modo !== 'off' ? 'ligado' : 'pausado';
    }
  }
  return NextResponse.json({
    placar,
    modos,
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
      // a corretora DONA lê o texto inteiro (o filtro `company_id` acima é o que garante "dona")
      tela_completa: l.tela_completa ?? null,
      valor_completo: l.valor_completo ?? null,
      momento: l.momento ?? null,
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
  if (body?.acao === 'pausar_seguradora') return pausarSeguradora(body);
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

/**
 * SPEC-125 S6 — "pausar esta seguradora": o agente PARA de decidir sozinho naquela seguradora,
 * SÓ nesta corretora. Escreve `cerebro_modos.modo='off'` em TODAS as linhas da seguradora (um ramo
 * `on` ainda decidiria — a precedência é ramo > `todos`) e garante a linha `todos`.
 *
 * 🔴 Só quem ADMINISTRA a corretora (`requireCompanyMember({ write: true })`, papel conferido no
 *    banco a cada pedido). 🔴 Toda escrita com `.eq('company_id', ctx.companyId)` — a outra
 *    corretora com a mesma seguradora continua como estava. 🔴 Confirmação explícita
 *    (`confirmar: true`) e REGISTRO: o motivo e quem pausou ficam na própria linha
 *    (`motivo`, `ligado_por`) e em `system_logs`.
 * ⚠️ Retomar não é desta tela: volta pelo master/Founder (a regra de LIGAR é a calibração, SPEC-123).
 */
async function pausarSeguradora(body: any) {
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) {
    const msg = auth.status === 403 ? 'Só quem administra a corretora pode pausar.' : 'Nao autorizado';
    return NextResponse.json({ error: msg }, { status: auth.status });
  }
  const seguradora = String(body?.seguradora || '').trim().toLowerCase();
  if (!SEGURADORA.test(seguradora)) {
    return NextResponse.json({ error: 'seguradora inválida' }, { status: 400 });
  }
  if (body?.confirmar !== true) {
    return NextResponse.json({ error: 'Confirme a pausa antes (confirmar: true).' }, { status: 400 });
  }
  const { ctx, supabase } = auth;
  const agora = new Date().toISOString();
  const motivo = `Pausado pela corretora em ${agora.slice(0, 10)}` +
    (String(body?.motivo || '').trim() ? `: ${String(body.motivo).trim().slice(0, 200)}` : '');
  const quem = `corretora:${ctx.userId}`;

  const { data: antes, error: erroAntes } = await supabase
    .from('cerebro_modos')
    .select('ramo, modo')
    .eq('company_id', ctx.companyId)
    .eq('insurer_key', seguradora);
  if (erroAntes) return NextResponse.json({ error: 'Não conseguimos pausar agora.' }, { status: 500 });

  const { error: erroUpd } = await supabase
    .from('cerebro_modos')
    .update({ modo: 'off', motivo, ligado_por: quem, updated_at: agora })
    .eq('company_id', ctx.companyId)
    .eq('insurer_key', seguradora);
  if (erroUpd) return NextResponse.json({ error: 'Não conseguimos pausar agora.' }, { status: 500 });
  if (!((antes || []) as any[]).some((l) => l.ramo === 'todos')) {
    const { error: erroIns } = await supabase.from('cerebro_modos').insert({
      company_id: ctx.companyId, insurer_key: seguradora, ramo: 'todos', modo: 'off', motivo, ligado_por: quem,
    });
    if (erroIns) return NextResponse.json({ error: 'Não conseguimos pausar agora.' }, { status: 500 });
  }
  await logSystemAction({
    userId: ctx.userId, companyId: ctx.companyId, actionType: 'COMPANY_UPDATED',
    resourceType: 'cerebro_modos', resourceId: seguradora,
    details: { acao: 'pausar_seguradora', seguradora, antes: antes || [], motivo }, status: 'success',
  }).catch(() => undefined);
  return NextResponse.json({ ok: true, seguradora, modo: 'off', linhas_antes: (antes || []).length });
}
