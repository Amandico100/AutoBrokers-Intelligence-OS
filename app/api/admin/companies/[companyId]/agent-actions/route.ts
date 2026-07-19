// SPEC-013 FB-2 / SPEC-039 F3 — manutenção canônica (master): arquivar agente
// legado/teste. O NOME do atendimento é de cada corretora ("Even" é só o da
// Resulta) — o sistema NUNCA renomeia. Seguro: nunca arquiva Core/atendimento.
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, supabaseService, assertSameOrigin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const supabase = supabaseService();

  const body = await req.json().catch(() => ({}));
  const action = typeof body.action === 'string' ? body.action : '';
  const agentId = typeof body.agent_id === 'string' ? body.agent_id : '';
  if (!agentId) return NextResponse.json({ ok: false, error: 'agent_id_required' }, { status: 400 });

  const { data: agent } = await supabase.from('agents').select('id, company_id, agent_role, name, context_package').eq('id', agentId).maybeSingle();
  if (!agent?.id || agent.company_id !== companyId) return NextResponse.json({ ok: false, error: 'agente_fora_de_escopo' }, { status: 400 });

  if (action === 'archive_agent') {
    // NUNCA arquivar os canônicos.
    if (agent.agent_role === 'core' || agent.agent_role === 'attendance') {
      return NextResponse.json({ ok: false, error: 'canonico_nao_arquivavel' }, { status: 400 });
    }
    const cp = (agent.context_package && typeof agent.context_package === 'object' && !Array.isArray(agent.context_package))
      ? { ...(agent.context_package as Record<string, unknown>) } : {};
    cp.archived = { at: new Date().toISOString(), by: (auth.ctx as any)?.adminId ?? null, reason: 'legacy_test_data' };
    const { error } = await supabase.from('agents').update({ is_active: false, context_package: cp, updated_at: new Date().toISOString() }).eq('id', agentId).eq('company_id', companyId);
    if (error) return NextResponse.json({ ok: false, error: 'archive_failed' }, { status: 400 });
    return NextResponse.json({ ok: true, action, agent_id: agentId, archived: true });
  }

  return NextResponse.json({ ok: false, error: 'acao_invalida' }, { status: 400 });
}
