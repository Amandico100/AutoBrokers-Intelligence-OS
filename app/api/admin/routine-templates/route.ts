import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

import { requireMasterAdmin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

/**
 * SPEC-019 C — CRUD master das Rotinas Prontas (routine_templates).
 * GET     → { templates: [...] } (todas, inclusive inativas)
 * POST    → cria (sem id) ou atualiza (com id)
 * DELETE  → ?id=<id>
 */
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

export async function GET() {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const { data, error } = await supabaseAdmin
    .from('routine_templates')
    .select('*')
    .order('sort_order', { ascending: true });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ templates: data || [] });
}

export async function POST(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  const name = String(body.name || '').trim().slice(0, 120);
  const instructions = String(body.instructions || '').trim();
  if (name.length < 3 || instructions.length < 10) {
    return NextResponse.json({ error: 'Nome (3+) e instruções (10+) são obrigatórios' }, { status: 400 });
  }

  const row = {
    name,
    description: String(body.description || '').slice(0, 400),
    category: String(body.category || 'Geral').slice(0, 60),
    instructions,
    schedule_default: (body.schedule_default || {}) as object,
    delivery_default: (body.delivery_default || { channel: 'whatsapp' }) as object,
    required: (body.required || {}) as object,
    is_active: body.is_active !== false,
    sort_order: Number.isFinite(Number(body.sort_order)) ? Number(body.sort_order) : 100,
    updated_at: new Date().toISOString(),
  };

  const id = String(body.id || '');
  if (id) {
    const { error } = await supabaseAdmin.from('routine_templates').update(row).eq('id', id);
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
    return NextResponse.json({ ok: true, id });
  }
  const { data, error } = await supabaseAdmin
    .from('routine_templates')
    .insert(row)
    .select('id')
    .single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, id: data?.id });
}

export async function DELETE(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const id = req.nextUrl.searchParams.get('id') || '';
  if (!id) return NextResponse.json({ error: 'id é obrigatório' }, { status: 400 });
  const { error } = await supabaseAdmin.from('routine_templates').delete().eq('id', id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
