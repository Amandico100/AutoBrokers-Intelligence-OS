import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * Rotinas agendadas (F2) — escopo da corretora logada.
 * GET  → { routines: [...], runs: [...] }  (últimas 30 execuções)
 * POST → { id, action: 'pause' | 'activate' | 'delete' }
 */

export async function GET(_req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();

  const { data: routines, error } = await supabase
    .from('routines')
    .select('id, name, instructions, schedule, delivery, knowledge, is_active, last_run_at, next_run_at, consecutive_failures, created_at')
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false });
  if (error) {
    console.error('[ROTINAS] list error:', error.message);
    return NextResponse.json({ error: 'Erro ao listar (a migration de rotinas já foi aplicada?)' }, { status: 500 });
  }

  const ids = (routines || []).map((r) => r.id);
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
  return NextResponse.json({ routines: routines || [], runs });
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

    // Próxima execução: agora + intervalo, ou hoje/amanhã no horário (aprox.
    // em UTC-3; o motor recalcula com precisão a cada execução).
    let nextRun = new Date();
    if (kind === 'interval') {
      nextRun = new Date(Date.now() + (schedule.minutes as number) * 60000);
    } else {
      const [hh, mm] = String(schedule.time).split(':').map(Number);
      const nowSp = new Date(Date.now() - 3 * 3600000);
      const target = new Date(Date.UTC(nowSp.getUTCFullYear(), nowSp.getUTCMonth(), nowSp.getUTCDate(), hh + 3, mm));
      if (target <= new Date()) target.setUTCDate(target.getUTCDate() + 1);
      nextRun = target;
    }

    if (action === 'create') {
      if (name.length < 3 || instructions.length < 10) {
        return NextResponse.json({ error: 'Nome e instruções são obrigatórios' }, { status: 400 });
      }
      const { error } = await supabase.from('routines').insert({
        company_id: ctx.companyId,
        created_by: ctx.userId,
        name, instructions, schedule, delivery,
        timezone: 'America/Sao_Paulo',
        is_active: true,
        next_run_at: nextRun.toISOString(),
        ...(knowledge ? { knowledge } : {}),
      });
      if (error) return NextResponse.json({ error: 'Erro ao criar rotina' }, { status: 500 });
      return NextResponse.json({ ok: true });
    }
    // update
    const patch: Record<string, unknown> = { schedule, delivery, next_run_at: nextRun.toISOString() };
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
