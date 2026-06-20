// 43P-FINAL-1 — seleção de corretora (tenant) pelo master admin.
// Grava cookie HttpOnly aj_company server-side (mais robusto que document.cookie),
// validando que o usuário é master e que a company existe. Tenant não-master NÃO
// pode selecionar/trocar de corretora.
import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getPortalAdminContext } from '@/lib/attendance/portal-admin-context';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceKey) return NextResponse.json({ ok: false, error: 'supabase_not_configured' }, { status: 503 });
  const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false } });

  const ctx = await getPortalAdminContext(supabase);
  if (!ctx.userId) return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });
  if (!ctx.isMaster) return NextResponse.json({ ok: false, error: 'only_master_can_select_tenant' }, { status: 403 });

  const body = await request.json().catch(() => ({}));
  const companyId = typeof body.company_id === 'string' ? body.company_id.trim() : '';
  if (!companyId) return NextResponse.json({ ok: false, error: 'company_id_required' }, { status: 400 });

  // Valida que a company existe (não confia no cliente).
  const { data: c } = await supabase.from('companies').select('id, company_name').eq('id', companyId).maybeSingle();
  if (!c?.id) return NextResponse.json({ ok: false, error: 'company_not_found' }, { status: 404 });

  const res = NextResponse.json({ ok: true, company_id: c.id, company_name: c.company_name ?? null });
  res.cookies.set('aj_company', c.id, {
    path: '/',
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 60 * 60 * 12, // 12h
  });
  return res;
}

/** Limpa a seleção (volta a exigir escopo). */
export async function DELETE() {
  const res = NextResponse.json({ ok: true, cleared: true });
  res.cookies.set('aj_company', '', { path: '/', httpOnly: true, maxAge: 0 });
  return res;
}
