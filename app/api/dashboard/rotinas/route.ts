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
    .select('id, name, instructions, schedule, delivery, is_active, last_run_at, next_run_at, consecutive_failures, created_at')
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
  if (!id) return NextResponse.json({ error: 'id é obrigatório' }, { status: 400 });

  if (action === 'delete') {
    const { error } = await supabase.from('routines').delete().eq('id', id).eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao excluir' }, { status: 500 });
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
