// TA2-A/B — espelho (read-only) da Effective Configuration de uma empresa para o
// Portal Admin. MESMA fonte canônica do Dashboard (sem duplicar dados). Autorização
// real: master de plataforma OU company_admin da própria empresa (nunca só cookie).
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, supabaseService } from '@/lib/admin/admin-auth';
import { getTenantAgentConfig } from '@/lib/admin/tenant-agent-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const supabase = supabaseService();
  const core = await getTenantAgentConfig(supabase, companyId, 'core');
  const attendance = await getTenantAgentConfig(supabase, companyId, 'attendance');
  return NextResponse.json({ ok: true, company_id: companyId, core, attendance, real_action_allowed: false });
}
