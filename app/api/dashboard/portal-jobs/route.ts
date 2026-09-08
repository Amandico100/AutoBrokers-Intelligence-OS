import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { assertSameOrigin } from '@/lib/admin/admin-auth';
import {
  buildPortalJobRetryPatch,
  isRetryableHitlJob,
  motivoDeRecusaDeRetry,
  sanitizePortalJob,
} from '@/lib/portal/hitl';

export const dynamic = 'force-dynamic';

const JOB_SELECT = 'id, company_id, portal_key, journey, status, evidence, screenshots, attempts, created_at, started_at, finished_at, error';

// ---------------------------------------------------------------------------
// Nome humano do portal, com FALLBACK LOCAL.
//
// 📊 Medido em 08/09/2026: os jobs de vidro gravam `portal_key='vidros_lanternas'`,
// e essa chave NAO existe na tabela `portals` — o `.in('key', keys)` volta vazio
// e a tela mostrava a chave crua para o corretor. Um nome de coluna nao e
// linguagem humana (R11), entao o mapa do banco passa a ser a primeira escolha,
// nao a unica.
// ---------------------------------------------------------------------------
const PORTAL_NOMES_LOCAIS: Record<string, string> = {
  vidros_lanternas: 'Portal de Vidros',
  vidros_api: 'Portal de Vidros',
  allianz_corretor: 'Allianz',
  hdi_corretor: 'HDI',
  tokiomarine_corretor: 'Tokio Marine',
  yelum_corretor: 'Yelum',
  mapfre_corretor: 'Mapfre',
  zurich_corretor: 'Zurich',
};

/** Ultimo recurso: transforma `alguma_chave_corretor` em "Alguma Chave". */
// Nao exportar: `route.ts` so aceita os handlers e a config do Next — um export
// extra faz o build reclamar de "does not match the required types of a Route".
function nomeLegivelDeChave(key: string): string {
  const limpo = String(key || '')
    .replace(/_(corretor|portal|api|lanternas)$/i, '')
    .replace(/[_-]+/g, ' ')
    .trim();
  if (!limpo) return 'Portal';
  return limpo.replace(/\b\w/g, (c) => c.toUpperCase());
}

async function portalNameMap(supabase: ReturnType<typeof getSupabaseAdmin>, keys: string[]) {
  const out: Record<string, string> = {};
  for (const key of keys) out[key] = PORTAL_NOMES_LOCAIS[key] || nomeLegivelDeChave(key);
  if (!keys.length) return out;
  const { data } = await supabase.from('portals').select('key, name').in('key', keys);
  // O nome cadastrado pela corretora vence o fallback — o fallback so cobre o buraco.
  for (const row of data || []) {
    const nome = String(row.name || '').trim();
    if (nome) out[String(row.key)] = nome;
  }
  return out;
}

/** O que o corretor precisa ver de um acionamento, sem chave nem status cru. */
function detalhesDoAcionamento(row: any) {
  const ev = row.evidence && typeof row.evidence === 'object' && !Array.isArray(row.evidence)
    ? row.evidence
    : {};
  const passos = Array.isArray(ev.adaptive_steps) ? ev.adaptive_steps.length : 0;
  const provaBruta = ev.prova;
  const prova = typeof provaBruta === 'string'
    ? provaBruta
    : (provaBruta && typeof provaBruta === 'object' && !Array.isArray(provaBruta)
      ? String(provaBruta.url || provaBruta.href || '')
      : '');
  return {
    protocolo: String(ev.protocolo || '').trim() || null,
    resumo: String(ev.resumo || '').trim() || null,
    prova: prova.trim() || null,
    tem_screenshot: Array.isArray(row.screenshots) && row.screenshots.length > 0,
    passos,
  };
}

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();
  const status = req.nextUrl.searchParams.get('status') || 'needs_human';
  const limit = Math.min(Math.max(Number(req.nextUrl.searchParams.get('limit') || 20), 1), 50);
  const jobId = String(req.nextUrl.searchParams.get('job_id') || '').trim();

  let q = supabase
    .from('portal_jobs')
    .select(JOB_SELECT)
    // 🔴 O filtro de tenant nao muda: nenhum caminho novo (nem o `job_id`) le
    // linha de outra corretora. Uma prova e um protocolo sao dados de segurado.
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false })
    .limit(jobId ? 1 : limit);
  if (jobId) q = q.eq('id', jobId);
  else if (status !== 'all') q = q.eq('status', status);

  const { data, error } = await q;
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  const rows = (data || []) as any[];
  const keys: string[] = [];
  const seen: Record<string, true> = {};
  for (const row of rows) {
    const key = String(row.portal_key || '');
    if (key && !seen[key]) {
      seen[key] = true;
      keys.push(key);
    }
  }
  const names = await portalNameMap(supabase, keys);

  // 📊 Uma screenshot e base64 de PNG inteiro. Mandar 20 delas de uma vez faz a
  // listagem pesar dezenas de MB, e o corretor quase sempre quer ver UMA. Entao a
  // lista completa (`status=all`) diz apenas que a prova EXISTE; o botao "Ver
  // prova" busca a linha unica por `job_id`, que vem com a imagem.
  const listaCompleta = !jobId && status === 'all';
  const jobs = rows.map((row) => {
    const base = sanitizePortalJob(row, names);
    return {
      ...base,
      ...detalhesDoAcionamento(row),
      screenshot: listaCompleta ? null : base.screenshot,
    };
  });
  if (jobId) {
    if (!jobs.length) return NextResponse.json({ error: 'job_not_found' }, { status: 404 });
    return NextResponse.json({ job: jobs[0], jobs });
  }
  return NextResponse.json({ jobs });
}

export async function POST(req: NextRequest) {
  const sameOrigin = assertSameOrigin(req);
  if (sameOrigin) return NextResponse.json({ error: sameOrigin.error }, { status: sameOrigin.status });

  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();
  const body = await req.json().catch(() => ({}));
  const action = String(body.action || '');
  const jobId = String(body.job_id || '');
  if (!['retry', 'archive'].includes(action) || !jobId) {
    return NextResponse.json({ error: 'action=retry|archive e job_id sao obrigatorios' }, { status: 400 });
  }

  const { data: row, error: readError } = await supabase
    .from('portal_jobs')
    .select(JOB_SELECT)
    .eq('id', jobId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (readError) return NextResponse.json({ error: readError.message }, { status: 500 });
  if (!row) return NextResponse.json({ error: 'job_not_found' }, { status: 404 });

  if (action === 'archive') {
    if (row.status !== 'needs_human') {
      return NextResponse.json({ error: 'job_not_archivable' }, { status: 409 });
    }
    const evidence = row.evidence && typeof row.evidence === 'object' && !Array.isArray(row.evidence) ? row.evidence : {};
    const { error: archiveError } = await supabase
      .from('portal_jobs')
      .update({
        status: 'archived',
        finished_at: new Date().toISOString(),
        evidence: {
          ...evidence,
          archived_by_dashboard: true,
          archived_at: new Date().toISOString(),
        },
      })
      .eq('id', jobId)
      .eq('company_id', ctx.companyId)
      .eq('status', 'needs_human');
    if (archiveError) return NextResponse.json({ error: archiveError.message }, { status: 500 });
    return NextResponse.json({ ok: true });
  }

  if (!isRetryableHitlJob(row, ctx.companyId)) {
    // O codigo seco sozinho fazia o operador tentar de novo por outro caminho.
    // Quando a recusa e "o pedido ja existe", dizer isso E a informacao util.
    return NextResponse.json(
      { error: 'job_not_retryable', motivo: motivoDeRecusaDeRetry(row, ctx.companyId) },
      { status: 409 },
    );
  }

  const patch = buildPortalJobRetryPatch(new Date().toISOString(), row.evidence || {});
  const { error: updateError } = await supabase
    .from('portal_jobs')
    .update(patch)
    .eq('id', jobId)
    .eq('company_id', ctx.companyId)
    .eq('status', 'needs_human');
  if (updateError) return NextResponse.json({ error: updateError.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
