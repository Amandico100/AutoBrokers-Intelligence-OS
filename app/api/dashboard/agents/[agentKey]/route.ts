// TA2-A — config do agente (AutoBrokers/Even) para a corretora logada.
// company_id resolvido SERVER-SIDE (sessão → users_v2). Nunca confia em body/query.
// Resposta sanitizada (sem prompt protegido/segredo). company_admin edita a própria.
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { getTenantAgentConfig, patchTenantAgentConfig, roleForKey } from '@/lib/admin/tenant-agent-store';

export const dynamic = 'force-dynamic';

async function resolve(): Promise<{ companyId: string; supabase: any } | { error: string; status: number }> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
  if (!session.userId) return { error: 'Não autorizado', status: 401 };
  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!, { auth: { persistSession: false } });
  let companyId = session.companyId ?? null;
  if (!companyId) {
    const { data } = await supabase.from('users_v2').select('company_id').eq('id', session.userId).maybeSingle();
    companyId = data?.company_id ?? null;
  }
  if (!companyId) return { error: 'Empresa não encontrada', status: 404 };
  return { companyId, supabase };
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });
  const r = await resolve();
  if ('error' in r) return NextResponse.json({ ok: false, error: r.error }, { status: r.status });
  const out = await getTenantAgentConfig(r.supabase, r.companyId, role);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });
  const r = await resolve();
  if ('error' in r) return NextResponse.json({ ok: false, error: r.error }, { status: r.status });
  const body = await req.json().catch(() => ({}));
  const input = {
    variables: body.variables && typeof body.variables === 'object' ? body.variables : undefined,
    overrides: body.overrides && typeof body.overrides === 'object' ? body.overrides : undefined,
  };
  const out = await patchTenantAgentConfig(r.supabase, r.companyId, role, input);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
