import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/** GET /api/vault/audit — eventos recentes de auditoria da empresa logada. */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('vault_audit_log')
    .select('*')
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false })
    .limit(100);

  if (error) {
    console.error('[VAULT audit list]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar auditoria' }, { status: 500 });
  }
  return NextResponse.json({ events: data || [] });
}
