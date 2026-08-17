import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

const BILLING_KIND = 'billing_collection';

function asObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function normalizeRoutineConfig(value: unknown): Record<string, unknown> {
  const cfg = asObject(value);
  if (String(cfg.kind || '') !== BILLING_KIND) return cfg;
  const portalKeys = Array.isArray(cfg.portal_keys)
    ? cfg.portal_keys.map((v) => String(v || '').trim()).filter(Boolean)
    : ['allianz_corretor'];
  const sendMode = ['test', 'approval', 'live', 'none'].includes(String(cfg.send_mode || ''))
    ? String(cfg.send_mode)
    : 'test';
  const maxBoletos = Number.isInteger(cfg.max_boletos_por_execucao)
    ? Math.max(1, Math.min(50, Number(cfg.max_boletos_por_execucao)))
    : 10;
  return {
    ...cfg,
    kind: BILLING_KIND,
    portal_keys: portalKeys.length ? portalKeys : ['allianz_corretor'],
    approval_required: cfg.approval_required !== false,
    send_mode: sendMode,
    test_number: String(cfg.test_number || '').replace(/\D/g, ''),
    max_boletos_por_execucao: maxBoletos,
    management_provider: String(cfg.management_provider || 'infocap').trim() || 'infocap',
    message_template: String(cfg.message_template || '').trim(),
  };
}

/**
 * Qual Auxiliar é dono desta rotina — SPEC-078 C.3.
 *
 * A ordem é a mesma do backfill da migration `20260817_03`, e ela importa:
 * jogar tudo em `tarefas-agendadas` seria rápido e erraria. Uma rotina de
 * cobrança pertence ao Auxiliar de Cobrança, que é onde o corretor procura por
 * ela. `tarefas-agendadas` é o destino de quem NÃO tem dono natural — não é
 * depósito de quem tem.
 *
 * 1. o slug que a tela mandou (a tela do Auxiliar sempre manda o dela)
 * 2. o `kind` da config — `billing_collection` → `cobranca-feita`
 * 3. `tarefas-agendadas`, o Auxiliar de plataforma
 */
const AUXILIAR_POR_KIND: Record<string, string> = {
  [BILLING_KIND]: 'cobranca-feita',
};
const AUXILIAR_DE_TAREFAS_SOLTAS = 'tarefas-agendadas';

type Dono =
  | { ok: true; id: string; slug: string }
  | { ok: false; error: string; details: string[] };

async function resolverDono(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  companyId: string,
  slugPedido: unknown,
  config: Record<string, unknown>,
): Promise<Dono> {
  const candidatos = [
    String(slugPedido || '').trim(),
    AUXILIAR_POR_KIND[String(config.kind || '')] || '',
    AUXILIAR_DE_TAREFAS_SOLTAS,
  ].filter(Boolean);

  // 🔴 O filtro por `company_id` é obrigatório e não é decorativo: o backend usa
  // service role, então RLS sozinho não protege (CLAUDE.md §7). Sem ele, uma
  // rotina poderia nascer apontando para o Auxiliar de outra corretora.
  const { data, error } = await supabase
    .from('tenant_auxiliaries')
    .select('id, slug, status')
    .eq('company_id', companyId)
    .in('slug', candidatos);

  if (error) {
    return { ok: false, error: 'Não foi possível identificar o Auxiliar dono.', details: [error.message] };
  }

  const porSlug = new Map((data ?? []).map((r) => [String(r.slug), r]));
  for (const slug of candidatos) {
    const achado = porSlug.get(slug);
    // Um Auxiliar arquivado/desinstalado não pode receber rotina nova — ele saiu
    // de cena. Os demais estados (inclusive `inactive` e `paused`) recebem: é
    // justamente pausado que a corretora configura antes de ligar.
    if (achado && achado.status !== 'archived') {
      return { ok: true, id: String(achado.id), slug };
    }
  }

  // Chegar aqui significa que nem o `tarefas-agendadas` existe nesta corretora —
  // a migration `20260817_03` instala em todas, então isso é corretora criada
  // depois dela sem passar pelo provisionamento. Falha explícita, não silenciosa.
  return {
    ok: false,
    error: 'Esta corretora ainda não tem um Auxiliar que possa ser dono desta rotina.',
    details: [`nenhum de: ${candidatos.join(', ')}`],
  };
}

/**
 * Quando a rotina roda pela primeira vez.
 *
 * 🔴 SPEC-078 D.6. A versão anterior calculava só "hoje ou amanhã no horário" e
 * **ignorava os dias da semana escolhidos**. Uma rotina "só segunda" criada num
 * sábado disparava no domingo — e só a partir da SEGUNDA execução o Python
 * (`routine_engine.compute_next_run`) passava a respeitar os dias.
 *
 * Aqui a regra é a mesma do motor, inclusive a convenção: `weekdays` usa
 * `datetime.weekday()` do Python, **0 = segunda … 6 = domingo**. O JavaScript
 * usa `getDay()` com 0 = domingo, então a conversão abaixo NÃO é decorativa —
 * sem ela a semana inteira anda um dia.
 */
function proximaExecucao(schedule: { kind?: string; time?: string; minutes?: number; weekdays?: number[] }): Date {
  if (String(schedule.kind || '').toLowerCase() === 'interval') {
    return new Date(Date.now() + Number(schedule.minutes) * 60000);
  }
  const [hh, mm] = String(schedule.time).split(':').map(Number);
  const dias = Array.isArray(schedule.weekdays) ? schedule.weekdays.map(Number).filter((d) => d >= 0 && d <= 6) : [];

  // America/Sao_Paulo é UTC-3 o ano inteiro desde o fim do horário de verão.
  // O motor Python usa ZoneInfo de verdade; aqui só o PRIMEIRO disparo é
  // calculado, e ele é recalculado com precisão logo depois.
  const agoraSp = new Date(Date.now() - 3 * 3600000);
  const alvo = new Date(Date.UTC(agoraSp.getUTCFullYear(), agoraSp.getUTCMonth(), agoraSp.getUTCDate(), hh + 3, mm));

  // Até 8 tentativas: cobre a semana inteira mais o caso de o horário de hoje
  // já ter passado. O mesmo laço de `routine_engine.py:125`.
  for (let i = 0; i < 8; i++) {
    if (alvo > new Date()) {
      if (!dias.length) return alvo;
      // getDay(): 0=domingo. weekday() do Python: 0=segunda. A conversão.
      const diaSp = new Date(alvo.getTime() - 3 * 3600000).getUTCDay();
      const comoPython = (diaSp + 6) % 7;
      if (dias.includes(comoPython)) return alvo;
    }
    alvo.setUTCDate(alvo.getUTCDate() + 1);
  }
  return alvo;
}

/**
 * Rotinas agendadas (F2) — escopo da corretora logada.
 * GET  → { routines: [...], runs: [...] }  (últimas 30 execuções)
 * POST → { id, action: 'pause' | 'activate' | 'delete' }
 */

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();

  // 🔴 SPEC-078 C.4 — `?auxiliar=<slug>` filtra pelo DONO.
  //
  // O painel agora vive dentro da tela de um Auxiliar e mostra só as rotinas
  // dele. Filtrar no navegador funcionaria e seria pior: a corretora baixaria
  // a lista inteira para exibir uma parte. Aqui o filtro é feito no banco, e o
  // `.eq('company_id')` continua sendo a trava que importa (CLAUDE.md §7).
  const auxiliarPedido = String(req.nextUrl.searchParams.get('auxiliar') || '').trim();
  let donoId: string | null = null;
  if (auxiliarPedido) {
    const { data: dono } = await supabase
      .from('tenant_auxiliaries')
      .select('id')
      .eq('company_id', ctx.companyId)
      .eq('slug', auxiliarPedido)
      .maybeSingle();
    // Auxiliar que não existe nesta corretora devolve lista vazia — nunca a
    // lista inteira. Um filtro que "falha para o aberto" mostraria as rotinas
    // de todos os Auxiliares por causa de um slug digitado errado.
    donoId = dono?.id ? String(dono.id) : '__inexistente__';
  }

  let consulta = supabase
    .from('routines')
    .select('id, name, instructions, schedule, delivery, knowledge, config, is_active, last_run_at, next_run_at, consecutive_failures, created_at, visibility, created_by, tenant_auxiliary_id')
    .eq('company_id', ctx.companyId);
  if (donoId) consulta = consulta.eq('tenant_auxiliary_id', donoId);
  const { data: allRoutines, error } = await consulta.order('created_at', { ascending: false });
  if (error) {
    console.error('[ROTINAS] list error:', error.message);
    return NextResponse.json({ error: 'Erro ao listar (a migration de rotinas já foi aplicada?)' }, { status: 500 });
  }
  // SPEC-044: rotina PESSOAL só aparece para o dono; da corretora, para todos.
  const routines = (allRoutines || [])
    .filter((r) => (r.visibility || 'company') !== 'personal' || r.created_by === ctx.userId)
    .map((r) => ({ ...r, mine: (r.visibility || 'company') === 'personal' }));

  const ids = routines.map((r) => r.id);
  let runs: unknown[] = [];
  if (ids.length) {
    const { data } = await supabase
      .from('routine_runs')
      .select('id, routine_id, started_at, finished_at, status, output_preview, error')
      .in('routine_id', ids)
      .order('started_at', { ascending: false })
      .limit(30);
    runs = data || [];
  }
  return NextResponse.json({ routines, runs });
}

export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const id = String(body.id || '');
  const action = String(body.action || '');
  if (!id && action !== 'create') return NextResponse.json({ error: 'id é obrigatório' }, { status: 400 });

  // SPEC-044: rotina PESSOAL de outro usuário é invisível e imutável para
  // terceiros — respondemos "não encontrada" (nem confirma que existe).
  if (id) {
    const { data: target } = await supabase
      .from('routines')
      .select('id, visibility, created_by')
      .eq('id', id)
      .eq('company_id', ctx.companyId)
      .maybeSingle();
    if (!target) return NextResponse.json({ error: 'Rotina não encontrada' }, { status: 404 });
    if ((target.visibility || 'company') === 'personal' && target.created_by !== ctx.userId) {
      return NextResponse.json({ error: 'Rotina não encontrada' }, { status: 404 });
    }
  }

  if (action === 'delete') {
    const { error } = await supabase.from('routines').delete().eq('id', id).eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao excluir' }, { status: 500 });
    return NextResponse.json({ ok: true });
  }
  if (action === 'create' || action === 'update') {
    // SPEC-019 B — criação/edição MANUAL (paridade Claude Rotinas).
    const name = String(body.name || '').trim().slice(0, 120);
    const instructions = String(body.instructions || '').trim();
    // SPEC-019 E — conhecimento por rotina (só envia se não-vazio: não referencia
    // a coluna antes da migration ser aplicada).
    const knowledge = typeof body.knowledge === 'string' ? body.knowledge.trim() : '';
    const schedule = (body.schedule || {}) as { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
    const delivery = (body.delivery || {}) as { channel?: string; number?: string };
    const config = normalizeRoutineConfig(body.config);

    const kind = String(schedule.kind || '').toLowerCase();
    if (kind === 'daily') {
      if (!/^\d{2}:\d{2}$/.test(String(schedule.time || ''))) {
        return NextResponse.json({ error: 'Horário inválido (use HH:MM)' }, { status: 400 });
      }
    } else if (kind === 'interval') {
      if (!Number.isInteger(schedule.minutes) || (schedule.minutes as number) < 5) {
        return NextResponse.json({ error: 'Intervalo mínimo: 5 minutos' }, { status: 400 });
      }
    } else {
      return NextResponse.json({ error: 'Agenda inválida' }, { status: 400 });
    }
    if (delivery.channel === 'whatsapp') {
      const digits = String(delivery.number || '').replace(/\D/g, '');
      if (digits.length < 10) return NextResponse.json({ error: 'Número WhatsApp inválido (DDI+DDD+número)' }, { status: 400 });
      delivery.number = digits;
    }
    if (config.kind === BILLING_KIND) {
      const portals = Array.isArray(config.portal_keys) ? config.portal_keys : [];
      if (!portals.length) return NextResponse.json({ error: 'Selecione ao menos um portal para a cobranca.' }, { status: 400 });
    }

    const nextRun = proximaExecucao(schedule);

    if (action === 'create') {
      if (name.length < 3 || instructions.length < 10) {
        return NextResponse.json({ error: 'Nome e instruções são obrigatórios' }, { status: 400 });
      }

      // 🔴 SPEC-078 C.3 — TODA ROTINA NASCE COM DONO.
      //
      // 📊 Medido em 17/08/2026: o repositório inteiro tem 42 linhas
      // mencionando `tenant_auxiliary_id`, e NENHUMA delas escrevia a coluna em
      // `routines`. Não era descuido de um caso — não existia caminho de código
      // no produto que desse dono a uma rotina nova. A rotina criada às 13:01
      // daquele dia nasceu órfã na mesma corretora onde `cobranca-feita` está
      // instalada, e o card do Auxiliar dizia "Nenhuma rotina ainda".
      //
      // Agora o banco também recusa (migration 20260817_03), mas a recusa lá é
      // a rede de baixo. Aqui é onde o dono é ESCOLHIDO — e escolher certo
      // importa: rotina de cobrança pertence ao Auxiliar de Cobrança, que é
      // onde o corretor espera vê-la.
      const dono = await resolverDono(supabase, ctx.companyId, body.auxiliar, config);
      if (!dono.ok) {
        return NextResponse.json({ error: dono.error, details: dono.details }, { status: 400 });
      }

      const { error } = await supabase.from('routines').insert({
        company_id: ctx.companyId,
        created_by: ctx.userId,
        tenant_auxiliary_id: dono.id,
        name, instructions, schedule, delivery, config,
        timezone: 'America/Sao_Paulo',
        is_active: true,
        next_run_at: nextRun.toISOString(),
        ...(knowledge ? { knowledge } : {}),
      });
      if (error) {
        // A mensagem do banco vai no `details` e a tela precisa lê-la. Devolver
        // só "Erro ao criar rotina" é o mesmo defeito do `install_failed` de
        // 17/08: duas telas de distância entre o sintoma e a causa.
        console.error('[ROTINA create]', ctx.companyId, error.message);
        return NextResponse.json({ error: 'Erro ao criar rotina', details: [error.message] }, { status: 500 });
      }
      return NextResponse.json({ ok: true });
    }
    // update
    const patch: Record<string, unknown> = { schedule, delivery, config, next_run_at: nextRun.toISOString() };
    if (name) patch.name = name;
    if (instructions) patch.instructions = instructions;
    if (knowledge) patch.knowledge = knowledge;
    const { error } = await supabase.from('routines').update(patch).eq('id', id).eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao atualizar rotina' }, { status: 500 });
    return NextResponse.json({ ok: true });
  }

  if (action === 'pause' || action === 'activate') {
    const patch: Record<string, unknown> = { is_active: action === 'activate' };
    if (action === 'activate') patch.consecutive_failures = 0;
    const { error } = await supabase.from('routines').update(patch).eq('id', id).eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao atualizar' }, { status: 500 });
    return NextResponse.json({ ok: true });
  }
  return NextResponse.json({ error: 'Ação inválida' }, { status: 400 });
}
