// SPEC-013 FB-2 — diagnóstico de runtime + divergências (master, read-only). Sem segredo.
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, supabaseService } from '@/lib/admin/admin-auth';
import { buildAgentDivergences, isHealthy, effectiveCoreModel, type AgentLite } from '@/lib/admin/agent-health';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const supabase = supabaseService();

  const { data: agentsRaw } = await supabase.from('agents')
    .select('id, name, agent_role, is_active, llm_provider, llm_model').eq('company_id', companyId);
  const agents = (agentsRaw ?? []) as any[];
  const lite: AgentLite[] = agents.map((a) => ({ id: a.id, name: a.name, agent_role: a.agent_role, is_active: a.is_active }));
  const divergences = buildAgentDivergences(lite);

  const core = agents.find((a) => a.agent_role === 'core');
  const even = agents.find((a) => a.agent_role === 'attendance');

  let balance_brl = 0;
  try { const { data } = await supabase.from('company_credits').select('balance_brl').eq('company_id', companyId).maybeSingle(); balance_brl = Number(data?.balance_brl ?? 0); } catch { /* 0 honesto */ }
  let knowledge_docs = 0;
  try { const { count } = await supabase.from('documents').select('id', { count: 'exact', head: true }).eq('company_id', companyId); knowledge_docs = count ?? 0; } catch { /* 0 */ }

  const diag = (a: any) => a ? {
    present: true, is_active: Boolean(a.is_active), provider: a.llm_provider ?? 'openai',
    model_stored: a.llm_model ?? null,
    model_effective: a.agent_role === 'core' ? effectiveCoreModel(a.llm_model) : (a.llm_model ?? null),
  } : { present: false };

  return NextResponse.json({
    ok: true, company_id: companyId,
    healthy: isHealthy(divergences),
    balance_brl, balance_ok: balance_brl > 0,
    knowledge: { private_docs: knowledge_docs, private_ready: knowledge_docs > 0 },
    core: diag(core), even: diag(even),
    divergences,
  });
}
