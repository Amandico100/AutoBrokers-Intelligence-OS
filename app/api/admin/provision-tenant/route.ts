// Tenant Activation 1 — provisiona Core (AutoBrokers) + Even para uma empresa.
// Idempotente. Master admin (validado no banco). Não instala corredores/auxiliares.
import { NextRequest, NextResponse } from 'next/server';
import { provisionTenant } from '@/lib/admin/provision-tenant';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const xo = assertSameOrigin(request);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  // TA2-C — master de plataforma validado na fonte canônica (admin_users), não só cookie.
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const supabase = auth.supabase;

  const body = await request.json().catch(() => ({}));
  const companyId = typeof body.companyId === 'string' ? body.companyId : (typeof body.company_id === 'string' ? body.company_id : '');
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });

  const { data: company } = await supabase.from('companies').select('id').eq('id', companyId).maybeSingle();
  if (!company?.id) return NextResponse.json({ ok: false, error: 'company_not_found' }, { status: 404 });

  const result = await provisionTenant(supabase, companyId);
  return NextResponse.json({ ...result, real_action_allowed: false });
}
