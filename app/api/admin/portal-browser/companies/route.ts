// 43P4.2A.1 — lista de corretoras (companies) para o seletor.
// P1 multi-tenant: SÓ master enumera a lista global; tenant vê só a própria;
// sem escopo → lista vazia. Read-only, sanitizado (id/nome/status).
import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getPortalAdminContext, listCompaniesForAdmin, resolveCompanyListingMode } from '@/lib/attendance/portal-admin-context';

export const dynamic = 'force-dynamic';

export async function GET() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceKey) return NextResponse.json({ ok: false, error: 'supabase_not_configured' }, { status: 503 });
  const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false } });

  const ctx = await getPortalAdminContext(supabase);
  if (!ctx.userId) return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });

  // P1: decide o modo de enumeração (anti-vazamento entre corretoras).
  const mode = resolveCompanyListingMode({ is_master: ctx.isMaster, company_id: ctx.companyId });
  const companies =
    mode === 'all' ? await listCompaniesForAdmin(supabase)
    : mode === 'own' ? await listCompaniesForAdmin(supabase, ctx.companyId as string)
    : [];

  return NextResponse.json({
    ok: true,
    is_master: ctx.isMaster,
    current_company_id: ctx.companyId,
    company_scope_required: ctx.company_scope_required,
    listing_mode: mode,
    companies,
  });
}
