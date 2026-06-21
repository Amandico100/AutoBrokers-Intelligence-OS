// Tenant Activation 1 — provisiona Core (AutoBrokers) + Even para uma empresa.
// Idempotente. Master admin. Não instala corredores/auxiliares; não liga canal.
import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { provisionTenant } from '@/lib/admin/provision-tenant';
import { requireMasterAdmin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  // TA2-B — apenas master de plataforma provisiona (valida papel, não só o cookie).
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceKey) return NextResponse.json({ ok: false, error: 'supabase_not_configured' }, { status: 503 });
  const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false } });

  const body = await request.json().catch(() => ({}));
  const companyId = typeof body.companyId === 'string' ? body.companyId : (typeof body.company_id === 'string' ? body.company_id : '');
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });

  const { data: company } = await supabase.from('companies').select('id').eq('id', companyId).maybeSingle();
  if (!company?.id) return NextResponse.json({ ok: false, error: 'company_not_found' }, { status: 404 });

  const result = await provisionTenant(supabase, companyId);
  return NextResponse.json({ ...result, real_action_allowed: false });
}
