// TA2-A/B — reset da config do agente ao padrão do blueprint (preserva o resto).
// Exige admin da própria corretora (company_id + papel resolvidos server-side).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { resetTenantAgentConfig, roleForKey } from '@/lib/admin/tenant-agent-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await resetTenantAgentConfig(auth.supabase, auth.ctx.companyId, role);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
