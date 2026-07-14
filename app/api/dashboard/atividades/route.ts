// SPEC-036 — feed de Atividades da corretora (tempo real, escopo company).
import { NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

export async function GET() {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const { data } = await auth.supabase
    .from('agent_activities')
    .select('category, title, detail, created_at')
    .eq('company_id', auth.ctx.companyId)
    .order('created_at', { ascending: false })
    .limit(300);
  return NextResponse.json({ ok: true, activities: data || [] });
}
