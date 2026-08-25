// TA2-A/B — config do agente (AutoBrokers/Even) para a corretora logada.
// company_id + papel resolvidos SERVER-SIDE (sessão → users_v2). PATCH exige admin
// da própria corretora. Nunca confia em body/query. Resposta sanitizada.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { decidirPatchDeAgente } from '@/lib/admin/admin-auth-policy';
import { getTenantAgentConfig, patchTenantAgentConfig, roleForKey, setTenantAgentActive } from '@/lib/admin/tenant-agent-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getTenantAgentConfig(auth.supabase, auth.ctx.companyId, role);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  // 🔴 SPEC-093 BLOCO A — o portão é por CAMPO, e por isso a autorização
  // acontece DEPOIS de ler o corpo.
  //
  // `write: false` aqui resolve sessão, corretora e papel **sem** aplicar o
  // portão de escrita. Quem decide é o par (o que o corpo pede) × (o que o
  // papel pode) logo abaixo — e nenhum caminho fica sem portão.
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));

  // 🔴 SPEC-093 BLOCO A — a decisão mora em `decidirPatchDeAgente`, que é PURA
  // e é o que o gate testa. Aqui só se traduz o veredito em HTTP.
  const decisao = decidirPatchDeAgente({
    role: auth.ctx.role,
    isOwner: auth.ctx.isOwner,
    agentRole: role,
    camposDoCorpo: Object.keys(body ?? {}),
  });
  if (!decisao.permitido) {
    return NextResponse.json({ ok: false, error: decisao.motivo }, { status: 403 });
  }

  // SPEC-045: botão LIGAR/DESLIGAR (só attendance). Mutação isolada — não
  // mistura com variáveis/overrides.
  if (decisao.acao === 'toggle') {
    const toggled = await setTenantAgentActive(
      auth.supabase, auth.ctx.companyId, role, Boolean(body.is_active));
    return NextResponse.json(toggled, { status: toggled.ok ? 200 : 400 });
  }

  const input = {
    variables: body.variables && typeof body.variables === 'object' ? body.variables : undefined,
    overrides: body.overrides && typeof body.overrides === 'object' ? body.overrides : undefined,
  };
  const out = await patchTenantAgentConfig(auth.supabase, auth.ctx.companyId, role, input);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
