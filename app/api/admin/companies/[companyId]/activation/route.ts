// TA2-B — rollup de ativação de uma empresa para o Portal Admin (master/company_admin
// da própria). MESMA fonte canônica do Dashboard (agentes + corredores + prontidão),
// sanitizada. Read-only: nenhuma ação externa.
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, supabaseService } from '@/lib/admin/admin-auth';
import { getTenantAgentConfig } from '@/lib/admin/tenant-agent-store';
import { listTenantCorridors } from '@/lib/admin/tenant-corridor-store';
import { gatherReadiness } from '@/lib/admin/tenant-readiness-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const supabase = supabaseService();
  const [core, attendance, corridors, readiness] = await Promise.all([
    getTenantAgentConfig(supabase, companyId, 'core'),
    getTenantAgentConfig(supabase, companyId, 'attendance'),
    listTenantCorridors(supabase, companyId),
    gatherReadiness(supabase, companyId),
  ]);

  let installed_auxiliaries = 0;
  try { const { count } = await supabase.from('tenant_auxiliaries').select('id', { count: 'exact', head: true }).eq('company_id', companyId); installed_auxiliaries = count ?? 0; } catch { /* honest 0 */ }

  return NextResponse.json({
    ok: true, company_id: companyId,
    agents: { core, attendance },
    corridors: { active: corridors.active, items: corridors.items },
    auxiliaries: { installed: installed_auxiliaries },
    readiness: { production_ready: readiness.production_ready, ready_count: readiness.ready_count, total: readiness.total, items: readiness.items },
    real_action_allowed: false,
  });
}
