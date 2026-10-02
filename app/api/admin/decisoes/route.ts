/**
 * O diário de decisões visto pelo MASTER — todas as corretoras. SPEC-123 F4.
 *
 * GET  → { items, cursor, has_more }  filtros: veredito, company_id, seguradora, classe, faixa, cursor
 * POST ?id=<decisão>  → "virar rascunho de carta": encaminha ao backend
 *      (`POST /api/admin/atlas/diario/{id}/carta`), que cria a carta com
 *      `status='proposta_diario'` pelo caminho do escritor oficial de cartas
 *      (`diario_de_decisoes.propor_carta_sync`) e grava `carta_rascunho_id`.
 *
 * 🔴 Só MASTER de plataforma (`requireMasterAdmin`, validado no banco). Ler de todas
 * as corretoras é o papel desta tela — e é por isso que ela não mora em `/dashboard`.
 * ⛔ A carta NUNCA nasce `pending_review`: esse status o destilador publica sozinho.
 */
import { NextRequest, NextResponse } from 'next/server';

import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { authenticatedProxy } from '@/lib/admin-proxy';
import { calcularPlacar, COLUNAS_DO_PLACAR } from '@/lib/diario/placar';

export const dynamic = 'force-dynamic';

const SELECT =
  'id, company_id, created_at, seguradora, ramo, classe, acao, nota, modo, explicacao_para_gente, ' +
  'resultado, veredito, o_certo_era, sugere_regra, veredito_em, virou_caso_em, caso_chave, carta_rascunho_id, ' +
  'momento, tela_completa, valor_completo';
const CLASSES = ['conduzir', 'responder_com_dado', 'deduzir', 'perguntar_ao_segurado', 'nunca_sozinho'];
const FAIXAS: Record<string, [number, number]> = { '70-80': [70, 79], '80-90': [80, 89], '90-100': [90, 100] };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const p = req.nextUrl.searchParams;
  const limit = Math.min(Math.max(Number(p.get('limit') || 40), 1), 100);

  // Por padrão, os ERRADOS — é o que vira caso de bancada e carta.
  const veredito = p.get('veredito') || 'errado';
  let q = auth.supabase
    .from('diario_de_decisoes')
    .select(SELECT)
    .order('created_at', { ascending: false })
    .order('id', { ascending: false })
    .limit(limit + 1);
  if (veredito === 'sem') q = q.is('veredito', null);
  else if (veredito === 'certo' || veredito === 'errado') q = q.eq('veredito', veredito);
  const empresa = p.get('company_id') || '';
  if (UUID.test(empresa)) q = q.eq('company_id', empresa);
  const seguradora = (p.get('seguradora') || '').trim().toLowerCase();
  if (seguradora) q = q.eq('seguradora', seguradora);
  const classe = p.get('classe') || '';
  if (CLASSES.includes(classe)) q = q.eq('classe', classe);
  const faixa = FAIXAS[p.get('faixa') || ''];
  if (faixa) q = q.gte('nota', faixa[0]).lte('nota', faixa[1]);
  const cursor = p.get('cursor');
  if (cursor && !Number.isNaN(Date.parse(cursor))) q = q.lt('created_at', cursor);

  const { data, error } = await q;
  if (error) return NextResponse.json({ error: 'Não conseguimos carregar o diário agora.' }, { status: 500 });
  const linhas = (data || []) as any[];
  const temMais = linhas.length > limit;
  const pagina = linhas.slice(0, limit);

  // O nome da corretora vem do BANCO, por id (CLAUDE.md §13.9) — nunca de constante.
  const ids = Array.from(new Set(pagina.map((l) => String(l.company_id))));
  const nomes: Record<string, string> = {};
  if (ids.length) {
    const { data: empresas } = await auth.supabase.from('companies').select('id, company_name').in('id', ids);
    for (const e of (empresas || []) as any[]) nomes[String(e.id)] = String(e.company_name || '');
  }
  // SPEC-125 S6 — o PLACAR do master: todas as corretoras, ou a escolhida (`company_id`).
  let placar = null;
  if (!cursor) {
    let qp = auth.supabase
      .from('diario_de_decisoes')
      .select(COLUNAS_DO_PLACAR)
      .gte('created_at', new Date(Date.now() - 30 * 86_400_000).toISOString())
      .limit(20000);
    if (UUID.test(empresa)) qp = qp.eq('company_id', empresa);
    const { data: doPlacar } = await qp;
    placar = calcularPlacar((doPlacar || []) as any[], new Date(), 30);
  }
  return NextResponse.json({
    placar,
    items: pagina.map((l) => ({ ...l, corretora: nomes[String(l.company_id)] || '' })),
    cursor: temMais ? pagina[pagina.length - 1]?.created_at ?? null : null,
    has_more: temMais,
  });
}

export async function POST(req: NextRequest) {
  const sameOrigin = assertSameOrigin(req);
  if (sameOrigin) return NextResponse.json({ error: sameOrigin.error }, { status: sameOrigin.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const id = req.nextUrl.searchParams.get('id') || '';
  if (!UUID.test(id)) return NextResponse.json({ error: 'id da decisão é obrigatório' }, { status: 400 });
  return authenticatedProxy(req, `/api/admin/atlas/diario/${id}/carta`);
}
