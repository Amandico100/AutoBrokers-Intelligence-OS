// SPEC-013 B2 — visão protegida (master) de Core+Even de uma corretora cliente.
// Even SEMPRE visível (mesmo inativa). Sanitizado; sem prompt protegido/segredo/slug legado
// como rótulo. A edição global vai pelo Blueprint Center; a local pelo Dashboard tenant.
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, supabaseService } from '@/lib/admin/admin-auth';
import { getTenantAgentConfig } from '@/lib/admin/tenant-agent-store';

export const dynamic = 'force-dynamic';

async function appliedRelease(supabase: any, companyId: string, blueprintKey: string) {
  try {
    const { data } = await supabase.from('agent_release_rollouts')
      .select('release_id, status, applied_at, agent_blueprint_releases(semantic_version)')
      .eq('company_id', companyId).eq('blueprint_key', blueprintKey).eq('status', 'active')
      .order('applied_at', { ascending: false }).limit(1).maybeSingle();
    if (!data) return null;
    return { version: (data as any).agent_blueprint_releases?.semantic_version ?? null, applied_at: (data as any).applied_at ?? null };
  } catch { return null; }
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const supabase = supabaseService();
  const [core, attendance] = await Promise.all([
    getTenantAgentConfig(supabase, companyId, 'core'),
    getTenantAgentConfig(supabase, companyId, 'attendance'),
  ]);
  const [coreRel, evenRel] = await Promise.all([
    appliedRelease(supabase, companyId, 'autobrokers-core-v1'),
    appliedRelease(supabase, companyId, 'even-attendance-v1'),
  ]);

  const shape = (label: string, type: string, blueprintKey: string, c: any, rel: any) => ({
    label, type, blueprint_key: blueprintKey,
    provisioned: c?.provisioned ?? false,
    is_active: c?.agent?.is_active ?? false,
    display_name: c?.config?.display_name ?? null,
    applied_release: rel,
    // edição técnica global é proibida nesta visão; aponta para os lugares certos
    edit_global_at: '/admin/blueprint-center',
  });

  return NextResponse.json({
    ok: true, company_id: companyId,
    core: shape('AutoBrokers', 'Chat Principal', 'autobrokers-core-v1', core, coreRel),
    even: shape('Even', 'Atendimento', 'even-attendance-v1', attendance, evenRel),
    real_action_allowed: false,
  });
}
