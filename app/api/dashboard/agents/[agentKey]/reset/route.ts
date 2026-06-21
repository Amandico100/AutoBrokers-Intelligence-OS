// TA2-A — reset da config do agente ao padrão do blueprint (preserva o resto).
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resetTenantAgentConfig, roleForKey } from '@/lib/admin/tenant-agent-store';

export const dynamic = 'force-dynamic';

export async function POST(_req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });

  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
  if (!session.userId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!, { auth: { persistSession: false } });
  let companyId = session.companyId ?? null;
  if (!companyId) {
    const { data } = await supabase.from('users_v2').select('company_id').eq('id', session.userId).maybeSingle();
    companyId = data?.company_id ?? null;
  }
  if (!companyId) return NextResponse.json({ ok: false, error: 'Empresa não encontrada' }, { status: 404 });

  const out = await resetTenantAgentConfig(supabase, companyId, role);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
