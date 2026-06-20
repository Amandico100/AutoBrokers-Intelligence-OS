// 43P4.2A — lista de corretoras (companies) para o seletor do master admin.
// Read-only, sanitizado (id/nome/status). Só responde a admin autenticado.
import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getPortalAdminContext, listCompaniesForAdmin } from '@/lib/attendance/portal-admin-context';

export const dynamic = 'force-dynamic';

export async function GET() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceKey) return NextResponse.json({ ok: false, error: 'supabase_not_configured' }, { status: 503 });
  const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false } });

  const ctx = await getPortalAdminContext(supabase);
  if (!ctx.userId) return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });

  const companies = await listCompaniesForAdmin(supabase);
  return NextResponse.json({
    ok: true,
    is_master: ctx.isMaster,
    current_company_id: ctx.companyId,
    company_scope_required: ctx.company_scope_required,
    companies,
  });
}
